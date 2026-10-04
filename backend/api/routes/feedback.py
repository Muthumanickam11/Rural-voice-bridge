from fastapi import APIRouter, Request
from typing import Any, Dict, List

from api.schemas import FeedbackRequest
from privacy.redactor import redact_pii
from utils.logger import logger, log_audit_event

router = APIRouter()

# Bounded in-memory ring so the endpoint is not an unbounded memory leak.
FEEDBACK_STORE: List[Dict[str, Any]] = []
MAX_STORED_FEEDBACK = 500
VALID_REASONS = {"wrong", "outdated", "confusing", "too_long", "audio_bad", "other"}


@router.post("")
def submit_feedback(req: FeedbackRequest, request: Request):
    # Prefer the body value so a rating can be correlated back to the answer the
    # user actually saw. The middleware mints/overwrites a request id header on
    # every request, so preferring request.state first always discarded the id
    # the client carried over from the original answer.
    req_id = req.request_id or getattr(request.state, "request_id", None) or "unknown"
    sess_id = getattr(request.state, "session_id", "unknown")

    clean_comment = redact_pii(req.comment or "")
    reason = req.reason if req.reason in VALID_REASONS else None

    entry = {
        "request_id": req_id,
        "session_id": sess_id,
        "rating": req.rating,
        "reason": reason,
        "comment": clean_comment
    }
    FEEDBACK_STORE.append(entry)
    if len(FEEDBACK_STORE) > MAX_STORED_FEEDBACK:
        del FEEDBACK_STORE[:len(FEEDBACK_STORE) - MAX_STORED_FEEDBACK]

    log_audit_event(
        event_type="user_feedback",
        request_id=req_id,
        session_id=sess_id,
        intent="FEEDBACK",
        status="recorded",
        extra={"rating": req.rating, "reason": reason}
    )

    return {"ok": True, "message_ta": "உங்கள் கருத்துக்கு நன்றி!"}
