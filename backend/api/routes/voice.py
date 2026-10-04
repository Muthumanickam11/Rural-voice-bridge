from fastapi import APIRouter, Request, UploadFile, File, Form
from typing import Optional

from agents.graph import agent_graph
from agents.state import AgentState
from config.settings import settings
from providers.stt_provider import stt_provider
from api.errors import format_error_response
from api.routes.text import build_agent_response
from utils.logger import logger

router = APIRouter()

READ_CHUNK_SIZE = 64 * 1024


async def read_upload_limited(upload: UploadFile, max_bytes: int) -> tuple[Optional[bytes], bool]:
    """
    Stream the upload with a running byte budget instead of buffering the whole
    body, so an oversized upload cannot exhaust memory before it is rejected.
    Returns (data, too_large).
    """
    buffer = bytearray()
    total = 0
    while True:
        chunk = await upload.read(READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            return None, True
        buffer.extend(chunk)
    return bytes(buffer), False


@router.post("/process")
async def process_voice_query(
    request: Request,
    audio: Optional[UploadFile] = File(None),
    transcript: Optional[str] = Form(None),
    language: str = Form("ta")
):
    req_id = getattr(request.state, "request_id", "req-unknown")
    sess_id = getattr(request.state, "session_id", "sess-unknown")

    user_query = ""
    stt_conf = 1.0

    if transcript and transcript.strip():
        user_query = transcript.strip()
    elif audio and audio.filename:
        max_bytes = settings.MAX_AUDIO_MB * 1024 * 1024
        audio_bytes, too_large = await read_upload_limited(audio, max_bytes)
        if too_large:
            return format_error_response("E_FILE_TOO_LARGE", request_id=req_id, status_code=413)
        if not audio_bytes:
            return format_error_response("E_NO_SPEECH", request_id=req_id, status_code=400)

        stt_result = await stt_provider.transcribe_async(
            audio_bytes,
            filename=audio.filename or "voice.webm",
            language=language
        )
        if stt_result.get("error") == "E_FILE_TOO_LARGE":
            return format_error_response("E_FILE_TOO_LARGE", request_id=req_id, status_code=413)

        user_query = (stt_result.get("transcript") or "").strip()
        stt_conf = stt_result.get("confidence", 0.0)

        if not user_query:
            return format_error_response("E_NO_SPEECH", request_id=req_id, status_code=400)
    else:
        return format_error_response("E_NO_SPEECH", request_id=req_id, status_code=400)

    initial_state: AgentState = {
        "session_id": sess_id,
        "request_id": req_id,
        "channel": "voice",
        "user_text_raw": user_query,
        "user_text_clean": "",
        "language": language,
        "history": [],
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
    return build_agent_response(
        final_state,
        request,
        transcript=user_query,
        transcript_confidence=stt_conf
    )
