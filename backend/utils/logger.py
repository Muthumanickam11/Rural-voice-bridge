import os
import sys
import json
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from config.settings import settings

# IST timezone: UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit.jsonl")

LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_AUDIT_LOCK = threading.Lock()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(IST).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            log_data.update(extra_data)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str = "rural_voice_bridge") -> logging.Logger:
    log = logging.getLogger(name)
    level = LOG_LEVELS.get(settings.LOG_LEVEL.upper(), logging.INFO)
    log.setLevel(level)
    log.propagate = False

    if not log.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)-7s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        log.addHandler(console_handler)

        # File Handler (JSON structured log)
        try:
            file_handler = logging.FileHandler(APP_LOG_FILE, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(JSONFormatter())
            log.addHandler(file_handler)
        except OSError as exc:  # read-only volume etc.
            log.warning(f"File logging disabled: {exc}")

    return log


logger = setup_logger()


def log_audit_event(
    event_type: str,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    intent: Optional[str] = None,
    safety_level: str = "none",
    provider_used: Optional[str] = None,
    latency_ms: Optional[float] = None,
    status: str = "success",
    extra: Optional[Dict[str, Any]] = None
):
    """
    Appends one structured audit record to audit.jsonl.
    Stores metadata only - never the user's query text.
    """
    entry = {
        "timestamp": datetime.now(IST).isoformat(),
        "event_type": event_type,
        "request_id": request_id,
        "session_id": session_id,
        "endpoint": endpoint,
        # Never null: a missing intent is a data-quality problem downstream.
        "intent": intent or "UNKNOWN",
        "safety_level": safety_level,
        "provider_used": provider_used,
        "latency_ms": latency_ms,
        "status": status,
        "extra": extra or {}
    }

    line = json.dumps(entry, ensure_ascii=False) + "\n"
    try:
        # Serialised appends so concurrent requests cannot interleave a partial
        # line and corrupt the file for the admin metrics endpoint.
        with _AUDIT_LOCK:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        logger.error(f"Failed to write to audit log: {e}")

    logger.info(
        f"AUDIT | {event_type} | req={request_id} | intent={entry['intent']} | "
        f"safety={safety_level} | latency={latency_ms}ms | status={status}"
    )
