import os
import json
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Header, HTTPException, Query

from config.settings import settings
from utils.logger import AUDIT_LOG_FILE, logger

router = APIRouter()

RECENT_WINDOW = 50


def require_admin_token(x_admin_token: str = Header(default="")) -> None:
    """
    Admin observability endpoints expose every session_id and request_id.
    They must not be public.
    """
    expected = (settings.ADMIN_TOKEN or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN is not configured on the server")
    if not x_admin_token or x_admin_token != expected:
        logger.warning("Rejected unauthenticated admin request.")
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Token")


def _read_audit_entries() -> List[Dict[str, Any]]:
    """
    Parse audit.jsonl defensively: a single truncated line (possible with
    concurrent appends) must not discard every other entry.
    """
    entries: List[Dict[str, Any]] = []
    if not os.path.exists(AUDIT_LOG_FILE):
        return entries
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    entries.append(parsed)
    except OSError as exc:
        logger.error(f"Failed to read audit log: {exc}")
    return entries


@router.get("/metrics", dependencies=[Depends(require_admin_token)])
def get_metrics():
    audit_entries = _read_audit_entries()

    emergencies = sum(1 for e in audit_entries if e.get("safety_level") == "emergency")
    intents: Dict[str, int] = {}
    latencies: List[float] = []

    for e in audit_entries:
        raw_intent = e.get("intent")
        key = raw_intent if isinstance(raw_intent, str) and raw_intent else "UNKNOWN"
        intents[key] = intents.get(key, 0) + 1
        latency = e.get("latency_ms")
        if isinstance(latency, (int, float)) and latency:
            latencies.append(float(latency))

    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    return {
        "total_events": len(audit_entries),
        "emergency_events": emergencies,
        "avg_latency_ms": avg_latency,
        "intent_breakdown": intents,
        "recent_audit_count": min(len(audit_entries), RECENT_WINDOW)
    }


@router.get("/logs", dependencies=[Depends(require_admin_token)])
def get_recent_logs(limit: int = Query(default=50, ge=1, le=500)):
    """Recent structured audit entries for developer monitoring and transparency."""
    entries = _read_audit_entries()
    return {"count": len(entries), "logs": list(reversed(entries[-limit:]))}
