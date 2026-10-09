from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    ENABLE_LEGACY_ROUTES: bool = False

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
