"""FastAPI application entry point for Sourcerer backend.

Registers all routers and configures logging.
"""

import logging

from fastapi import FastAPI

from app.routes.ingestion import router as ingestion_router
from app.routes.quiz import router as quiz_router
from app.routes.retrieval import router as retrieval_router

# Configure basic logging for all stages.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sourcerer Backend",
    description="AI-powered RAG backend — ingestion, chunking, embedding, retrieval.",
    version="0.1.0",
)

# Stage 1: Google Drive ingestion.
app.include_router(ingestion_router)
app.include_router(quiz_router)
app.include_router(retrieval_router)


@app.get("/health")
async def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
