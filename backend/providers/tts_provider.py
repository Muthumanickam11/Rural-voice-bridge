import base64
from typing import Optional

from config.settings import settings
from utils.logger import logger

MAX_TTS_CHARS = 600
MIN_TTS_RATE = "-50%"
MAX_TTS_RATE = "+100%"


def _rate_string(speed: Optional[float]) -> str:
    """Map a 1.0x-style multiplier onto edge-tts percentage syntax."""
    if speed is None:
        return "+0%"
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        return "+0%"
    speed = max(0.5, min(2.0, speed))
    pct = int(round((speed - 1.0) * 100))
    pct = max(-50, min(100, pct))
    return f"{pct:+d}%"


class TTSProvider:
    def _providers(self) -> list[str]:
        order = [p.strip().lower() for p in settings.TTS_PROVIDER_ORDER.split(",") if p.strip()]
        seen = set()
        chain = []
        for p in order:
            if p not in seen:
                seen.add(p)
                chain.append(p)
        return chain

    async def generate_speech_base64(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> Optional[str]:
        if not text or not text.strip():
            return None

        tts_text = text.strip()[:MAX_TTS_CHARS]
        selected_voice = voice or settings.TTS_VOICE_TA
        rate = _rate_string(speed if speed is not None else settings.TTS_SPEED_DEFAULT)

        for provider in self._providers():
            if provider == "edge":
                audio = await self._edge_tts(tts_text, selected_voice, rate)
                if audio:
                    return audio
            elif provider == "browser":
                # Client-side synthesis; nothing to do server-side.
                return None
            else:
                # Unknown/unsupported provider (e.g. gtts): fall through to next.
                continue

        return None

    async def _edge_tts(self, text: str, voice: str, rate: str) -> Optional[str]:
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            audio_data = bytearray()
            async for chunk in communicate.stream():
                if chunk.get("type") == "audio":
                    audio_data.extend(chunk["data"])
            if audio_data:
                return base64.b64encode(audio_data).decode("utf-8")
        except Exception as e:
            logger.warning(f"edge-tts generation failed: {e}. Client browser TTS will be used.")
        return None


tts_provider = TTSProvider()
