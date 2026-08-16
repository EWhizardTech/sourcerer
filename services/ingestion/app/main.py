"""Ingestion service entry point.

Handles Google Drive intake and dispatches the processing pipeline
(parse -> chunk -> tag -> embed -> store) to Celery workers.
"""

import logging

from fastapi import FastAPI

from app.routes.ingestion import router as ingestion_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sourcerer Ingestion Service",
    description="Google Drive ingestion and document processing pipeline.",
    version="1.0.0",
)

app.include_router(ingestion_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "ingestion"}
