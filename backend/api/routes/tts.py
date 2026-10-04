from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.settings import settings
from providers.tts_provider import tts_provider

router = APIRouter()


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    speed: float = Field(default=settings.TTS_SPEED_DEFAULT, ge=0.5, le=2.0)


@router.post("")
async def generate_speech(req: TTSRequest):
    audio_b64 = await tts_provider.generate_speech_base64(req.text, speed=req.speed)
    return {
        "ok": bool(audio_b64),
        "audio_b64": audio_b64,
        # Only claim a format when audio actually exists.
        "format": "audio/mpeg" if audio_b64 else None,
        "speed": req.speed
    }
