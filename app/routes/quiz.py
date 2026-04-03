"""FastAPI router for quiz generation from retrieved chunks."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.quiz_service import build_mcqs
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])


class QuizFilters(BaseModel):
    """Metadata filters used by retrieval."""

    course_code: str | None = None
    year: str | None = None
    tags: list[str] | None = None


class QuizGenerateRequest(BaseModel):
    """Request body for quiz generation."""

    query: str
    filters: QuizFilters
    num_questions: int = Field(default=5, ge=1)


class QuizItem(BaseModel):
    """Single MCQ response item."""

    question: str
    answer: str
    options: list[str]
    difficulty: str
    source_chunk_ids: list[str]


@router.post("/generate", response_model=list[QuizItem])
async def generate_quiz(request: QuizGenerateRequest) -> list[QuizItem]:
    """Generate MCQs from retrieval results."""
    try:
        chunks = retrieval_service.retrieve_chunks(
            query=request.query,
            filters=request.filters.model_dump(),
            top_k=request.num_questions,
        )
    except ValueError as exc:
        logger.error("Retrieval service integration failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = build_mcqs(chunks=chunks, num_questions=request.num_questions)
    return [QuizItem(**item) for item in result]
