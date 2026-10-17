from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Local browser origins: 5173 is a host-run `npm run dev`, 4173 is the port
    # the frontend service in docker-compose.yml publishes.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    ENABLE_LEGACY_ROUTES: bool = False
    # Authentication rate limiting: max failed attempts per email within the window.
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_WINDOW_MINUTES: int = 15

    # Where uploaded estate photos are written. Relative paths are resolved
    # against the process working directory (backend/ when run as documented).
    # The directory holds only re-encoded JPEGs named after each photo's random
    # public id - never an uploaded filename.
    UPLOAD_DIR: str = "uploads"

    # --- Outbound email -------------------------------------------------
    # Off by default: with EMAIL_ENABLED=false the app logs that a message would
    # have been sent and opens no socket, so the product works with no mail relay.
    # Turn it on by setting EMAIL_ENABLED=true and SMTP_HOST to a real relay.
    EMAIL_ENABLED: bool = False
    EMAIL_FROM: str = "no-reply@valora.local"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_USE_STARTTLS: bool = True
    # The public origin of the frontend, used to build links in notification
    # emails (for example the admin approval queue). Never derived from a request
    # header, which a client could forge.
    APP_BASE_URL: str = "http://localhost:5173"

    # Optional AI assist layer. Everything is off by default and the product must
    # work with AI off. See docs/ADR-004-AI-Assist-Layer.md.
    AI_ENABLED: bool = False
    AI_INSIGHTS_ENABLED: bool = False
    AI_TRIAGE_ENABLED: bool = False
    AI_PERSONAL_DATA_ALLOWED: bool = False
    AI_PROVIDER: Literal["gemini", "openai_compatible", "fake"] = "gemini"
    AI_MODEL: str | None = None
    # A real Gemini brief has taken 55 seconds; allow headroom for slower calls.
    AI_TIMEOUT_SECONDS: float = 75.0
    AI_MAX_INPUT_CHARS: int = 6000
    # Thinking tokens count against this cap on the models we use, so it has to
    # cover the reasoning *and* the answer. The old default of 600 was spent on
    # thoughts: the interaction came back ``incomplete`` with no text and looked
    # like a rejected key. 2048 is the measured floor for a brief with thinking
    # disabled-by-level; leave more room if you raise AI_THINKING_LEVEL.
    AI_MAX_OUTPUT_TOKENS: int = 2048
    # How hard the model is allowed to reason before answering. Every feature
    # here asks it to *write* from supplied FACTS, not to analyse, so the default
    # is deliberately low: it is cheaper, faster and leaves the output budget for
    # the answer. "default" omits the field entirely and lets the provider decide.
    # Accepted levels vary by model; an unsupported level is a provider 400.
    AI_THINKING_LEVEL: Literal["minimal", "low", "medium", "high", "default"] = "low"
    # Per-estate daily AI budget, enforced by GuardedLLMClient against the
    # append-only ai_call_events ledger (see docs/ADR-004-AI-Assist-Layer.md).
    AI_DAILY_CALL_CAP_PER_ESTATE: int = 200
    GEMINI_API_KEY: SecretStr | None = None
    AI_COMPAT_BASE_URL: str | None = None
    AI_COMPAT_API_KEY: SecretStr | None = None
    # External n8n intelligence webhook orchestrator
    N8N_INTELLIGENCE_URL: str | None = None
    N8N_SERVICE_KEY: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("CORS_ORIGINS must contain at least one explicit origin.")
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must not contain '*'.")
        return origins

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # In Pydantic v2, info.data contains validated fields so far
        env = info.data.get("ENVIRONMENT", "development")
        if env != "development":
            known_placeholders = {
                "test-secret-not-for-production",
                "replace-with-a-long-random-development-secret",
                "dev-secret-key-change-in-production-12345",
            }
            if len(v) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in non-development environments.")
            if v in known_placeholders:
                raise ValueError("SECRET_KEY must not be a known placeholder in non-development environments.")
        return v

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "Settings":
        if self.AI_PROVIDER == "fake" and self.ENVIRONMENT not in ("development", "test"):
            raise ValueError(
                "AI_PROVIDER=fake is only allowed when ENVIRONMENT is development or test."
            )

        if self.AI_PERSONAL_DATA_ALLOWED and not self.AI_ENABLED:
            raise ValueError(
                "AI_PERSONAL_DATA_ALLOWED requires AI_ENABLED=true."
            )

        if self.AI_ENABLED:
            if not self.AI_MODEL:
                raise ValueError("AI_MODEL is required when AI_ENABLED=true.")
            if self.AI_PROVIDER == "gemini" and self.GEMINI_API_KEY is None:
                raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini.")
            if self.AI_PROVIDER == "openai_compatible":
                if not self.AI_COMPAT_BASE_URL:
                    raise ValueError(
                        "AI_COMPAT_BASE_URL is required when AI_PROVIDER=openai_compatible."
                    )
                if self.AI_COMPAT_API_KEY is None:
                    raise ValueError(
                        "AI_COMPAT_API_KEY is required when AI_PROVIDER=openai_compatible."
                    )

        return self

    @model_validator(mode="after")
    def validate_email_configuration(self) -> "Settings":
        # Enabling email without somewhere to send it is a misconfiguration that
        # would silently drop every notification, so it is refused at startup.
        if self.EMAIL_ENABLED and not self.SMTP_HOST:
            raise ValueError("SMTP_HOST is required when EMAIL_ENABLED=true.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
