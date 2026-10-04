from fastapi import APIRouter, Request
from typing import Any, Dict

from api.schemas import TextQueryRequest
from agents.graph import agent_graph, follow_ups_for
from agents.state import AgentState
from utils.logger import logger

router = APIRouter()


def build_agent_response(
    state: AgentState,
    request: Request,
    transcript: str = None,
    transcript_confidence: float = None
) -> Dict[str, Any]:
    """
    Single source of truth for the Q&A response shape so that
    POST /text/query and POST /voice/process can never drift apart.
    """
    request_id = getattr(request.state, "request_id", "req-unknown")
    session_id = getattr(request.state, "session_id", "sess-unknown")
    intent = state.get("intent", "")

    response: Dict[str, Any] = {
        "request_id": request_id,
        "session_id": session_id,
        "channel": state.get("channel", "text"),
        "transcript": transcript,
        "transcript_confidence": transcript_confidence,
        "answer": state.get("answer"),
        "audio_b64": state.get("audio_base64"),
        "follow_ups": follow_ups_for(intent),
        "safety": state.get("safety"),
        "verification": state.get("verification"),
        "timings_ms": state.get("timings_ms"),
        "intent": intent,
        "intent_confidence": state.get("intent_confidence"),
        "sources_used": state.get("retrieved", []),
        "provider_used": state.get("provider_used"),
    }
    if state.get("errors"):
        response["warnings"] = state["errors"]
    return response


@router.post("/query")
async def process_text_query(req: TextQueryRequest, request: Request):
    req_id = getattr(request.state, "request_id", "req-unknown")
    sess_id = getattr(request.state, "session_id", "sess-unknown")

    if not req.text or not req.text.strip():
        from api.errors import format_error_response
        return format_error_response("E_UNKNOWN_Q", request_id=req_id, status_code=400)

    initial_state: AgentState = {
        "session_id": sess_id,
        "request_id": req_id,
        "channel": "text",
        "user_text_raw": req.text,
        "user_text_clean": "",
        "language": req.language,
        "history": req.history or [],
        "safety": {},
        "intent": "",
        "intent_confidence": 0.0,
        "retrieved": [],
        "answer": None,
        "verification": {},
        "audio_base64": None,
        "timings_ms": {},
        "errors": []
    }

    final_state = await agent_graph.execute(initial_state)
    return build_agent_response(final_state, request)
