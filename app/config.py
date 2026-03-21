"""App configuration using Pydantic Settings.

Reads typed settings from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Path to the Google service account JSON key file.
    gdrive_service_account_path: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )


# Singleton instance imported by other modules.
settings = Settings()
