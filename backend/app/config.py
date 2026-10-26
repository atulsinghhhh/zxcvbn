"""Application configuration loaded from environment variables."""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WINDSIGHT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"

    # Total wall-clock timeout for a single HTTP request (seconds)
    http_timeout_seconds: float = 30.0

    # Maximum number of retry attempts for transient failures (excludes first attempt)
    http_max_retries: int = 3

    # Initial backoff between retries (seconds); doubles each attempt
    http_retry_wait_seconds: float = 1.0

    # Accepts a JSON array (e.g. '["https://a.com"]') or a plain
    # comma-separated string (e.g. 'https://a.com,https://b.com').
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            import json

            return json.loads(text)
        return [origin.strip() for origin in text.split(",") if origin.strip()]


settings = Settings()
