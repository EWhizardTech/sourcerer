"""Shared configuration for all Sourcerer services.

Reads typed settings from environment variables / .env file. Each service
consumes the subset it needs; unknown env vars are ignored.
"""

from typing import Optional

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# The committed dev default for PORTAL_SESSION_SECRET — usable locally, but
# refused when the portal runs in production (PORTAL_COOKIE_SECURE=true).
_INSECURE_SESSION_SECRET = "dev-insecure-change-me-dev-insecure-change-me"


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

    # --- Resource portal (services/portal) ---
    # Async SQLAlchemy URL for the portal's Postgres database.
    DATABASE_URL: str = (
        "postgresql+asyncpg://sourcerer:sourcerer@localhost:5433/sourcerer_portal"
    )
    # Google OAuth web client (sign-in with Google for the portal UI).
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    # Must match an authorized redirect URI on the OAuth client — the gateway URL.
    GOOGLE_CALLBACK_URL: str = "http://localhost:8001/api/v1/portal/auth/callback"
    # HS256 key for portal session JWTs. MUST be overridden in production; the
    # _validate_portal_production check below refuses this default when
    # PORTAL_COOKIE_SECURE is true.
    PORTAL_SESSION_SECRET: str = _INSECURE_SESSION_SECRET
    PORTAL_SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    # Comma-separated emails treated as portal admins (evaluated per request).
    ADMIN_EMAILS: str = ""
    # Drive folder the portal catalogs (metadata only — never file contents).
    # No default: the concrete ID belongs in .env / compose, so a deployment
    # never silently inherits someone else's library. Required in production.
    PORTAL_ROOT_FOLDER_ID: str = ""
    # Where the browser is sent after OAuth completes.
    PORTAL_FRONTEND_ORIGIN: str = "http://localhost:3001"
    # Origins allowed to send state-changing portal requests (CSRF guard).
    PORTAL_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    PORTAL_COOKIE_SECURE: bool = False  # true behind HTTPS in production
    PORTAL_COOKIE_SAMESITE: str = "lax"  # "none" for cross-domain deployments
    # Disk cache for office/gdoc -> PDF conversions.
    PORTAL_CACHE_DIR: str = ".cache/portal"
    PORTAL_SYNC_INTERVAL_MINUTES: int = 360
    # Comma-separated name globs skipped during catalog sync (junk dirs/files).
    PORTAL_SYNC_EXCLUDE: str = "__pycache__,node_modules,venv,.venv,*.pyc"
    PORTAL_CONVERT_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars gracefully.
    )

    @model_validator(mode="after")
    def _validate_portal_production(self) -> "Settings":
        """Fail closed on weak portal config in production. PORTAL_COOKIE_SECURE
        is only set behind HTTPS (the beta/prod deployments), so this never
        trips local dev but stops a real deployment from booting on the public
        default signing key or an unset root folder."""
        if self.PORTAL_COOKIE_SECURE:
            secret = self.PORTAL_SESSION_SECRET
            if (
                not secret
                or secret == _INSECURE_SESSION_SECRET
                or len(secret) < 32
            ):
                raise ValueError(
                    "PORTAL_SESSION_SECRET must be a strong (>=32 char) random "
                    "value in production; refusing to start on a weak or default "
                    "session key."
                )
            if not self.PORTAL_ROOT_FOLDER_ID:
                raise ValueError(
                    "PORTAL_ROOT_FOLDER_ID must be set in production."
                )
        return self


# Singleton instance imported by other modules.
settings = Settings()
