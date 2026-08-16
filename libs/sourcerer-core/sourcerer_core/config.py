"""Shared configuration for all Sourcerer services.

Reads typed settings from environment variables / .env file. Each service
consumes the subset it needs; unknown env vars are ignored.
"""

from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Path to the Google service account JSON key file.
    GDRIVE_SERVICE_ACCOUNT_PATH: str = "secrets/acc.json"

    # Qdrant configuration
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "sourcerer_collection"
    QDRANT_VECTOR_SIZE: int = 2048  # Gemini Embeddings 2 truncated
    QDRANT_DISTANCE: str = "Cosine"

    # Redis (chat memory) + Celery (ingestion queue)
    REDIS_URL: str = "redis://localhost:6380/2"
    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_BACKEND_URL: str = "redis://localhost:6380/1"

    # Tracking DB configuration
    DB_PATH: str = "data/sourcerer.db"

    # Groq configuration (tagging + retrieval agent)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"  # query condensation etc.

    # Gemini configuration for embedding
    GEMINI_API_KEY: Optional[str] = None
    MAX_IMAGE_EMBEDDING_SIZE: int = 10 * 1024 * 1024  # 10MB default

    # Tavily configuration for search (optional unless web search is used)
    TAVILY_API_KEY: str = ""

    # Retrieval quality
    RERANK_ENABLED: bool = True
    RERANK_MODEL: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    RERANK_OVERFETCH: int = 3  # fetch k * overfetch candidates before reranking

    # Chat memory
    CHAT_HISTORY_TTL_SECONDS: int = 60 * 60 * 24  # 24h
    CHAT_HISTORY_MAX_MESSAGES: int = 20

    # Optional Hugging Face token for gated/private model downloads.
    HF_TOKEN: Optional[str] = None

    # Local cache directories for quiz NLP/ML assets.
    ML_CACHE_DIR: str = ".cache"
    HF_HOME: str = ".cache/huggingface"
    HUGGINGFACE_HUB_CACHE: str = ".cache/huggingface/hub"
    TRANSFORMERS_CACHE: str = ".cache/huggingface/transformers"
    TORCH_HOME: str = ".cache/torch"
    NLTK_DATA_DIR: str = ".cache/nltk_data"
    SPACY_MODEL_DIR: str = ".cache/spacy"
    SPACY_MODEL_NAME: str = "en_core_web_sm"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )


# Singleton instance imported by other modules.
settings = Settings()
