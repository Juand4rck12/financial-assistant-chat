from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── WhatsApp Cloud API ──────────────────────────────────────────────
    whatsapp_token: str = ""
    """Bearer token for WhatsApp Graph API (system user or user token)."""

    whatsapp_phone_number_id: str = ""
    """Business phone number ID linked to the WABA."""

    whatsapp_waba_id: str = ""
    """WhatsApp Business Account ID."""

    whatsapp_api_version: str = "v22.0"
    """Graph API version (e.g. v22.0)."""

    whatsapp_webhook_verify_token: str = ""
    """Custom token for WhatsApp webhook challenge verification."""

    # ── Database ────────────────────────────────────────────────────────
    database_url: str = ""
    """PostgreSQL connection string (async, e.g. postgresql+asyncpg://user:pass@localhost:5432/finance_db)."""

    redis_url: str = ""
    """Redis connection string for session state."""

    # ── LLM (Mistral AI) ────────────────────────────────────────────────
    mistral_api_key: str = ""
    """Mistral AI API key."""

    mistral_model: str = "mistral-small-latest"
    """Mistral AI model identifier for orchestrator and extraction."""

    gemini_api_key: str = ""
    """Optional Google Gemini API key (fallback or secondary)."""

    # ── Financial / Localization ────────────────────────────────────────
    default_currency: str = "COP"
    """Default ISO currency code (Colombian Peso)."""

    # ── Environment ─────────────────────────────────────────────────────
    env: str = "development"
    """Runtime environment: development | production"""

    stt_model: str = ""
    """Speech-to-text model identifier for audio transcription."""


settings = Settings()
