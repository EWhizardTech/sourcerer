"""Retrieval endpoint (blocking, stateless). Kept for API compatibility;
richer chat lives under /chat."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.flow import run_chat
from app.routes.chat import ChatSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["retrieval"])


class RetrievalRequest(BaseModel):
    """Request body for the retrieval endpoint."""

    query: str = Field(min_length=1)


class RetrievalResponse(BaseModel):
    """Answer with structured sources."""

    answer: str
    sources: list[ChatSource]


@router.post("/", response_model=RetrievalResponse)
async def retrieve_answer(request: RetrievalRequest) -> RetrievalResponse:
    """Agentically search the knowledge base and return a cited answer."""
    logger.info("Received retrieval query: %s", request.query)
    try:
        result = run_chat(query=request.query, session_id=None)
    except Exception as exc:
        logger.exception("Retrieval workflow failed")
        raise HTTPException(
            status_code=500, detail="Internal Server Error during retrieval workflow"
        ) from exc

    return RetrievalResponse(answer=result["answer"], sources=result["sources"])
