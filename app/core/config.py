"""App configuration using Pydantic Settings.

Reads typed settings from environment variables / .env file.
"""

from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Path to the Google service account JSON key file.
    GDRIVE_SERVICE_ACCOUNT_PATH: str

    # Qdrant configuration
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: str
    QDRANT_COLLECTION_NAME: str
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )

    ML_CACHE_DIR: str = ".cache"
    HF_HOME: str = ".cache/huggingface"
    HUGGINGFACE_HUB_CACHE: str = ".cache/huggingface/hub"
    TRANSFORMERS_CACHE: str = ".cache/huggingface/transformers"
    TORCH_HOME: str = ".cache/torch"
    NLTK_DATA_DIR: str = ".cache/nltk_data"
    SPACY_MODEL_DIR: str = ".cache/spacy"
    SPACY_MODEL_NAME: str = "en_core_web_sm"
    HF_TOKEN: Optional[str] = None


# Singleton instance imported by other modules.
settings = Settings()
