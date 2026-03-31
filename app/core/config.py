"""App configuration using Pydantic Settings.

Reads typed settings from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Path to the Google service account JSON key file.
    gdrive_service_account_path: str

    # Qdrant configuration
    qdrant_api_key: str
    qdrant_cluster_endpoint: str
    qdrant_collection_name: str = "sourcerer_collection"
    qdrant_vector_size: int = 768  # Gemini Embeddings default
    qdrant_distance: str = "Cosine"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_BACKEND_URL: str = "redis://localhost:6379/1"

    # Tracking DB configuration
    db_path: str = "data/sourcerer.db"

    # Groq configuration for tagging
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )


# Singleton instance imported by other modules.
settings = Settings()
