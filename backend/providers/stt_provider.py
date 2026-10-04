import os
import uuid
from typing import Dict, Any
from config.settings import settings
from utils.logger import logger

ALLOWED_EXTENSIONS = {".webm", ".ogg", ".oga", ".mp3", ".wav", ".m4a", ".mp4", ".aac", ".opus", ".flac"}
FALLBACK_EXT = ".webm"


class STTProvider:
    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm", language: str = "ta") -> Dict[str, Any]:
        if not audio_bytes:
            return self._empty(language)

        max_bytes = settings.MAX_AUDIO_MB * 1024 * 1024
        if len(audio_bytes) > max_bytes:
            return {
                "transcript": "",
                "confidence": 0.0,
                "language": language,
                "fallback_used": True,
                "error": "E_FILE_TOO_LARGE"
            }

        if not settings.GROQ_API_KEY:
            return self._empty(language)

        safe_name = self._safe_filename(filename)
        temp_file = os.path.join(settings.TEMP_DIR, safe_name)

        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.REQUEST_TIMEOUT_SECONDS)

            os.makedirs(settings.TEMP_DIR, exist_ok=True)
            try:
                with open(temp_file, "wb") as f:
                    f.write(audio_bytes)
                with open(temp_file, "rb") as af:
                    transcription = client.audio.transcriptions.create(
                        file=(safe_name, af.read()),
                        model=settings.GROQ_WHISPER_MODEL,
                        language=language,
                        response_format="json"
                    )
            finally:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass

            transcript_text = (transcription.text or "").strip()
            if not transcript_text:
                return self._empty(language)

            return {
                "transcript": transcript_text,
                "confidence": 0.92,
                "language": language,
                "fallback_used": False
            }
        except Exception as e:
            logger.warning(f"Groq Whisper transcription failed: {e}")
            return self._empty(language)

    async def transcribe_async(self, audio_bytes: bytes, filename: str = "audio.webm", language: str = "ta") -> Dict[str, Any]:
        """Async wrapper so the blocking HTTP call does not stall the event loop."""
        import asyncio
        return await asyncio.to_thread(self.transcribe, audio_bytes, filename, language)

    def _empty(self, language: str) -> Dict[str, Any]:
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "fallback_used": True
        }

    @staticmethod
    def _safe_filename(filename: str) -> str:
        """
        Never trust a client-supplied filename. Derive the extension from it
        (so the provider gets a sane content type) but generate the actual
        on-disk name, so no caller can escape TEMP_DIR.
        """
        ext = os.path.splitext(os.path.basename(filename or ""))[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = FALLBACK_EXT
        return f"{uuid.uuid4().hex}{ext}"


stt_provider = STTProvider()
