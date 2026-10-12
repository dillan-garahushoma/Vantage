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

    # Optional AI assist layer. Everything is off by default and the product must
    # work with AI off. See docs/ADR-004-AI-Assist-Layer.md.
    AI_ENABLED: bool = False
    AI_INSIGHTS_ENABLED: bool = False
    AI_TRIAGE_ENABLED: bool = False
    AI_PERSONAL_DATA_ALLOWED: bool = False
    AI_PROVIDER: Literal["gemini", "openai_compatible", "fake"] = "gemini"
    AI_MODEL: str | None = None
    AI_TIMEOUT_SECONDS: float = 15.0
    AI_MAX_INPUT_CHARS: int = 6000
    AI_MAX_OUTPUT_TOKENS: int = 600
    # Per-estate daily AI budget, enforced by GuardedLLMClient against the
    # append-only ai_call_events ledger (see docs/ADR-004-AI-Assist-Layer.md).
    AI_DAILY_CALL_CAP_PER_ESTATE: int = 200
    GEMINI_API_KEY: SecretStr | None = None
    AI_COMPAT_BASE_URL: str | None = None
    AI_COMPAT_API_KEY: SecretStr | None = None

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
