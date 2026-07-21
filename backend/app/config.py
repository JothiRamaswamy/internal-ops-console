from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/internal_ops"
    )
    session_secret: str = "dev-insecure-session-secret-change-me"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    # Placeholder provider credentials (unused by mock adapters).
    persona_api_key: str = ""
    stripe_identity_api_key: str = ""
    stripe_api_key: str = ""
    adyen_api_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
