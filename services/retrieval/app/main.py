"""Retrieval service entry point.

Agentic RAG over the Qdrant knowledge base: streaming chat with memory,
reranked hybrid retrieval, and grounded, cited answers.
"""

import logging

from fastapi import FastAPI

from app.routes.chat import router as chat_router
from app.routes.retrieval import router as retrieval_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sourcerer Retrieval Service",
    description="Agentic RAG chat: streaming, memory, reranking, citations.",
    version="1.0.0",
)

app.include_router(retrieval_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "retrieval"}
