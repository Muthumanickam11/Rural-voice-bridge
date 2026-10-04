import time
import uuid
import threading
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.settings import settings
from utils.logger import logger
from api.errors import format_error_response

# Simple in-memory rate limiter per IP.
# Bounded: stale IPs are evicted so the map cannot grow without limit.
IP_RATE_MAP: Dict[str, List[float]] = {}
_RATE_LOCK = threading.Lock()
MAX_TRACKED_IPS = 10000
WINDOW_SECONDS = 60

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# Swagger UI ships inline scripts plus assets from these CDN hosts. Under the API's
# default-src 'none' policy the page loads but the browser refuses to execute them,
# so these routes get a policy that actually permits what the page needs.
DOCS_PATH_PREFIXES = ("/docs", "/redoc")
DOCS_CSP = "; ".join([
    "default-src 'none'",
    "script-src 'unsafe-inline' https://cdn.jsdelivr.net",
    "style-src 'unsafe-inline' https://cdn.jsdelivr.net https://fastapi.tiangolo.com",
    "img-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com data:",
    "font-src 'self' https://cdn.jsdelivr.net data:",
    "connect-src 'self'",
    "frame-ancestors 'none'",
])


def is_docs_path(path: str) -> bool:
    if not path:
        return False
    return path in ("/docs", "/redoc") or path.startswith(("/docs/", "/redoc/"))


def _prune(now: float) -> None:
    for ip in list(IP_RATE_MAP.keys()):
        kept = [ts for ts in IP_RATE_MAP[ip] if now - ts < WINDOW_SECONDS]
        if kept:
            IP_RATE_MAP[ip] = kept
        else:
            del IP_RATE_MAP[ip]


def apply_security_headers(
    response: Response, request_id: str, session_id: str, path: str = ""
) -> Response:
    """Applied to EVERY response, including 429/500 and CORS preflights."""
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Session-Id"] = session_id
    for key, value in SECURITY_HEADERS.items():
        response.headers[key] = value
    if is_docs_path(path):
        # Same protections, minus the asset block that would break the page itself.
        response.headers["Content-Security-Policy"] = DOCS_CSP
    return response


def check_rate_limit(client_ip: str) -> bool:
    """Returns True if the request is allowed."""
    now = time.time()
    with _RATE_LOCK:
        if len(IP_RATE_MAP) > MAX_TRACKED_IPS:
            _prune(now)
        timestamps = IP_RATE_MAP.setdefault(client_ip, [])
        kept = [ts for ts in timestamps if now - ts < WINDOW_SECONDS]
        if len(kept) >= settings.RATE_LIMIT_PER_MINUTE:
            IP_RATE_MAP[client_ip] = kept
            return False
        kept.append(now)
        IP_RATE_MAP[client_ip] = kept
        return True


def is_rate_limit_exempt(path: str) -> bool:
    """Health/readiness probes and the API docs are never rate limited."""
    if not path:
        return False
    if path in ("/api/v1/health", "/api/v1/ready", "/api/v1/health/ready", "/openapi.json"):
        return True
    return is_docs_path(path)


def rate_limit_headers(client_ip: str) -> Dict[str, str]:
    """Lets a client back off politely instead of hammering into a 429."""
    now = time.time()
    with _RATE_LOCK:
        used = len([ts for ts in IP_RATE_MAP.get(client_ip, []) if now - ts < WINDOW_SECONDS])
    limit = settings.RATE_LIMIT_PER_MINUTE
    remaining = max(0, limit - used)
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(WINDOW_SECONDS)
    }


class RequestTracingAndSecurityMiddleware(BaseHTTPMiddleware):
    async def _safe_call(self, request, call_next, request_id, session_id) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
            return apply_security_headers(
                format_error_response("E_INTERNAL", request_id=request_id, status_code=500),
                request_id, session_id, request.url.path
            )

    async def dispatch(self, request: Request, call_next):
        # 1. Request ID and Session ID
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        session_id = request.headers.get("X-Session-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.session_id = session_id

        # 2. Rate limiting
        # Liveness probes are exempt: a monitoring poll must never consume a
        # user's quota or be answered with 429, because that would mask a real
        # outage. Docs are exempt too, since they are static and read-only.
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        if is_rate_limit_exempt(path):
            response = await self._safe_call(request, call_next, request_id, session_id)
            apply_security_headers(response, request_id, session_id, path)
            for k, v in rate_limit_headers(client_ip).items():
                response.headers[k] = v
            return response

        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            limited = apply_security_headers(
                format_error_response("E_LIMIT", request_id=request_id, status_code=429),
                request_id, session_id, path
            )
            for k, v in rate_limit_headers(client_ip).items():
                limited.headers[k] = v
            return limited

        t_start = time.time()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
            return apply_security_headers(
                format_error_response("E_INTERNAL", request_id=request_id, status_code=500),
                request_id, session_id, request.url.path
            )

        duration_ms = round((time.time() - t_start) * 1000, 2)

        # 3. Security headers (always)
        apply_security_headers(response, request_id, session_id, path)
        for k, v in rate_limit_headers(client_ip).items():
            response.headers[k] = v

        # 4. Request logging
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) [req={request_id}]"
        )

        return response
