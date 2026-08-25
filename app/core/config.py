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
    interpretation_model: str = Field(default="claude-sonnet-4-6")
    interpretation_max_tokens: int = Field(default=8000)

    # Portal — single shared password (Tripp is the only user, so no user
    # table/registration flow needed). Session cookies are signed with
    # secret_key; set both in .env before deploying anywhere real.
    portal_password: str = Field(default="changeme")
    secret_key: str = Field(default="dev-only-insecure-secret-change-in-env")

    # Cloudflare R2 (PDF storage in production). Leave all blank for local
    # dev — storage.py automatically falls back to local disk when these
    # aren't set, so nothing extra is required to keep testing locally.
    r2_account_id: str = Field(default="")
    r2_access_key_id: str = Field(default="")
    r2_secret_access_key: str = Field(default="")
    r2_bucket_name: str = Field(default="")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
