from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings
from utils.logger import logger
from api.middleware import RequestTracingAndSecurityMiddleware
from api.errors import AppError, format_error_response
from rag.retriever import retriever

# Import all routers
from api.routes.health import router as health_router
from api.routes.text import router as text_router
from api.routes.voice import router as voice_router
from api.routes.tts import router as tts_router
from api.routes.schemes import router as schemes_router
from api.routes.rti import router as rti_router
from api.routes.rights import router as rights_router
from api.routes.helpcenters import router as helpcenters_router
from api.routes.feedback import router as feedback_router
from api.routes.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Rural Voice Bridge Backend...")
    logger.info(
        f"Loaded {len(retriever.chunks)} Knowledge Base chunks "
        f"across {len({c.get('file_id') for c in retriever.chunks})} documents."
    )
    logger.info(f"Backend environment: {settings.APP_ENV} | Debug: {settings.DEBUG}")

    production_problems = settings.validate_production_config()
    if production_problems:
        detail = "; ".join(production_problems)
        raise RuntimeError(f"Refusing to start with an unsafe production configuration: {detail}")

    if not settings.GROQ_API_KEY and not settings.GEMINI_API_KEY:
        logger.warning(
            "No cloud LLM/STT API keys configured. Running on the deterministic "
            "grounded-fallback engine; voice input transcription will be unavailable."
        )
    yield
    logger.info("Shutting down Rural Voice Bridge Backend.")


app = FastAPI(
    title="Rural Voice Bridge API (கிராம குரல் பாலம்)",
    description="Free, voice-first, Tamil-first guide to rights and government schemes for rural Tamil Nadu",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# TrustedHost: reject unexpected Host headers (host-header poisoning).
# Skipped in DEBUG so `http://<LAN-IP>:8000` still works for field testing.
if settings.is_production and settings.allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# Request tracing must sit INSIDE CORS so security headers are applied to
# CORS responses too, and so preflight requests are not rate-limited as API calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-Id", "X-Session-Id", "X-Admin-Token"],
    expose_headers=["X-Request-Id", "X-Session-Id"]
)
app.add_middleware(RequestTracingAndSecurityMiddleware)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    req_id = getattr(request.state, "request_id", "")
    return format_error_response(exc.code, request_id=req_id, status_code=exc.status_code)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Normalise FastAPI/Starlette HTTPExceptions into the same error envelope
    used by the rest of the API, so clients always find `error.message_ta`.
    """
    req_id = getattr(request.state, "request_id", "")
    status = exc.status_code
    code = {
        400: "E_UNKNOWN_Q",
        401: "E_INTERNAL",
        403: "E_INTERNAL",
        404: "E_UNKNOWN_Q",
        413: "E_FILE_TOO_LARGE",
        422: "E_LIMIT",
        429: "E_LIMIT",
    }.get(status, "E_INTERNAL")
    return format_error_response(code, request_id=req_id, status_code=status)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", "")
    # Report which fields failed, but never echo the submitted values back:
    # this route can carry Aadhaar numbers and addresses.
    fields = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query")]
        fields.append({"field": ".".join(loc), "issue": err.get("msg", "")})
    logger.warning(f"Validation failed on {request.url.path}: {fields}")
    return format_error_response(
        "E_INVALID", request_id=req_id, status_code=422, extra={"fields": fields}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "")
    logger.error(f"Internal error: {exc}", exc_info=True)
    return format_error_response("E_INTERNAL", request_id=req_id, status_code=500)


# Register Routers under /api/v1
prefix = settings.API_PREFIX
app.include_router(health_router, prefix=prefix, tags=["Health"])
app.include_router(text_router, prefix=f"{prefix}/text", tags=["Text Q&A"])
app.include_router(voice_router, prefix=f"{prefix}/voice", tags=["Voice Q&A"])
app.include_router(tts_router, prefix=f"{prefix}/tts", tags=["TTS"])
app.include_router(schemes_router, prefix=f"{prefix}/schemes", tags=["Schemes"])
app.include_router(rti_router, prefix=f"{prefix}/rti", tags=["RTI & Grievances"])
app.include_router(rights_router, prefix=f"{prefix}/rights", tags=["Know Your Rights"])
app.include_router(helpcenters_router, prefix=f"{prefix}/helpcenters", tags=["Help Centers"])
app.include_router(feedback_router, prefix=f"{prefix}/feedback", tags=["Feedback"])
app.include_router(admin_router, prefix=f"{prefix}/admin", tags=["Admin & Observability"])


@app.get("/")
def root():
    return {
        "app": "Rural Voice Bridge (கிராம குரல் பாலம்)",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG, workers=1)
