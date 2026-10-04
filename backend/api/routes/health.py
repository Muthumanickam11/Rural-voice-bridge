from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from config.settings import settings
from rag.retriever import retriever
from api.schemas import HealthResponse, ReadyResponse

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


@router.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "kb_version": settings.KB_VERSION,
        "time": datetime.now(IST).isoformat()
    }


@router.get("/ready", response_model=ReadyResponse)
@router.get("/health/ready", response_model=ReadyResponse, include_in_schema=False)
def readiness_check():
    rag_ready = len(retriever.chunks) > 0
    # The deterministic grounded fallback is always available, so the service is
    # usable with no API keys at all. Report each provider honestly rather than
    # claiming a cloud provider is configured.
    llm_ready = bool(settings.GEMINI_API_KEY or settings.GROQ_API_KEY)

    return {
        "ok": rag_ready,
        "providers": {
            "stt_groq": bool(settings.GROQ_API_KEY),
            "llm_gemini": bool(settings.GEMINI_API_KEY),
            "llm_groq": bool(settings.GROQ_API_KEY),
            "llm_cloud_available": llm_ready,
            "grounded_fallback": True,
            "tts_edge": True,
            "rag_chunks_loaded": len(retriever.chunks)
        }
    }
