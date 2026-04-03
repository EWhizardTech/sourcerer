"""FastAPI router for retrieval from Qdrant."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["retrieval"])


class RetrievalFilters(BaseModel):
    """Metadata filters for retrieval."""

    course_code: str | None = None
    year: str | None = None
    tags: list[str] | None = None


class RetrievalRequest(BaseModel):
    """Request schema for retrieval endpoint."""

    query: str
    filters: RetrievalFilters
    top_k: int = Field(default=5, ge=1)


class RetrievalResult(BaseModel):
    """Single retrieval result."""

    chunk_id: str
    text: str
    score: float | None = None
    metadata: dict
    tags: dict


@router.post("", response_model=list[RetrievalResult])
async def retrieve(request: RetrievalRequest) -> list[RetrievalResult]:
    """Retrieve top-k chunks with optional metadata filters."""
    try:
        results = retrieval_service.retrieve_chunks(
            query=request.query,
            filters=request.filters.model_dump(),
            top_k=request.top_k,
        )
    except ValueError as exc:
        logger.error("Retrieval failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [RetrievalResult(**item) for item in results]
