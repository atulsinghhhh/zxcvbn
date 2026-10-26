"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
