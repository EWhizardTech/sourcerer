"""App configuration using Pydantic Settings.

Reads typed settings from environment variables / .env file.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Path to the Google service account JSON key file.
    GDRIVE_SERVICE_ACCOUNT_PATH: str

    # Qdrant configuration
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: str
    QDRANT_COLLECTION_NAME: str = "sourcerer_collection"
    QDRANT_VECTOR_SIZE: int = 2048  # Gemini Embeddings 2 truncated
    QDRANT_DISTANCE: str = "Cosine"

    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_BACKEND_URL: str = "redis://localhost:6380/1"

    # Tracking DB configuration
    DB_PATH: str = "data/sourcerer.db"

    # Groq configuration for tagging
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Gemini configuration for embedding
    GEMINI_API_KEY: Optional[str] = None
    MAX_IMAGE_EMBEDDING_SIZE: int = 10 * 1024 * 1024  # 10MB default

    # Tavily configuration for search (optional unless web search is used)
    TAVILY_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )


# Singleton instance imported by other modules.
settings = Settings()
