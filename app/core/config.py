"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "Tripp Work Style Assessment Engine"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # Database — full URL; falls back to local Postgres for dev
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tripp"
    )

    # Typeform webhook — used to verify the HMAC signature Typeform sends.
    # Set this to the same secret you configure in the Typeform webhook UI.
    typeform_webhook_secret: str = Field(default="")

    # Claude (Week 2 — interpretations). Stubbed for now.
    anthropic_api_key: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
