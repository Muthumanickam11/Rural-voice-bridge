import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

    APP_NAME: str = "rural-voice-bridge"
    APP_ENV: str = "local"
    APP_VERSION: str = "2.2.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    WORKERS: int = 1
    REQUEST_TIMEOUT_SECONDS: int = 40

    # Security
    SECRET_KEY: str = "development-secret-key-rural-voice-bridge-2026-secure"
    ADMIN_TOKEN: str = "dev-admin-token-rural-voice-bridge"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    RATE_LIMIT_PER_MINUTE: int = 60
    GLOBAL_DAILY_BUDGET_CALLS: int = 2000
    MAX_UPLOAD_MB: int = 10

    # Input Limits
    MAX_AUDIO_SECONDS: int = 60
    MAX_AUDIO_MB: int = 5
    MAX_TEXT_CHARS: int = 1000
    MAX_HISTORY_TURNS: int = 3
    TEMP_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")

    # Providers
    STT_PROVIDER_ORDER: str = "groq,local"
    STT_LANGUAGE_DEFAULT: str = "ta"
    GROQ_API_KEY: str = ""
    GROQ_WHISPER_MODEL: str = "whisper-large-v3-turbo"

    LLM_PROVIDER_ORDER: str = "groq,gemini,grounded_fallback"
    GROQ_MODEL_MAIN: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_FAST: str = "llama-3.1-8b-instant"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_TEXT: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 900

    # TTS
    TTS_PROVIDER_ORDER: str = "edge,browser"
    TTS_VOICE_TA: str = "ta-IN-PallaviNeural"
    TTS_SPEED_DEFAULT: float = 1.0

    # RAG
    KB_PATH: str = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "knowledge_base")
    )
    INDEX_PATH: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "artifacts", "index")
    )
    TOP_K_VECTOR: int = 6
    TOP_K_BM25: int = 6
    RERANK_TO: int = 5
    MIN_RETRIEVAL_SCORE: float = 0.25
    KB_VERSION: str = "2026-09-21-v2.2"

    # Privacy
    STORE_QUERY_TEXT: bool = False
    PII_REDACTION: bool = True
    LOG_USER_TEXT: bool = False

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> List[str]:
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def has_any_llm_key(self) -> bool:
        return bool(self.GROQ_API_KEY or self.GEMINI_API_KEY)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod") or not self.DEBUG

    def validate_production_config(self) -> List[str]:
        """Return a list of unsafe production settings. Empty list means safe to boot."""
        if not self.is_production:
            return []

        problems: List[str] = []

        if self.ADMIN_TOKEN == "dev-admin-token-rural-voice-bridge":
            problems.append("ADMIN_TOKEN is still the development default")
        if self.SECRET_KEY.startswith("development-"):
            problems.append("SECRET_KEY is still the development default")
        if self.DEBUG:
            problems.append("DEBUG must be False in production")
        if "*" in self.ALLOWED_ORIGINS:
            problems.append("ALLOWED_ORIGINS must not contain a wildcard")
        if not self.ALLOWED_HOSTS:
            problems.append("ALLOWED_HOSTS must be set so Host headers can be validated")
        if not self.has_any_llm_key:
            problems.append(
                "no LLM provider key is configured; production would serve "
                "deterministic fallback answers only"
            )
        if not self.PII_REDACTION:
            problems.append("PII_REDACTION must stay enabled in production")
        if self.STORE_QUERY_TEXT or self.LOG_USER_TEXT:
            problems.append(
                "STORE_QUERY_TEXT and LOG_USER_TEXT must stay disabled in production"
            )

        try:
            origins = self.cors_origins
        except Exception:
            origins = []
        if any(origin.startswith("http://") and origin not in ("http://localhost:3000", "http://127.0.0.1:3000") for origin in origins):
            problems.append("ALLOWED_ORIGINS must use https:// outside local development")

        return problems


settings = Settings()
