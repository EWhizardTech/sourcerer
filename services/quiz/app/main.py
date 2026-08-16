"""Quiz service entry point.

Generates multiple-choice questions from retrieved course content using
a local NLP pipeline (T5 question generation + keyword extraction).
"""

import logging

from fastapi import FastAPI

from app.routes.quiz import router as quiz_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sourcerer Quiz Service",
    description="MCQ generation from retrieved educational content.",
    version="1.0.0",
)

app.include_router(quiz_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "quiz"}
