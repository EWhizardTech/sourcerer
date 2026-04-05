"""FastAPI router for quiz generation from retrieved chunks.

Enhanced with better error handling, validation, and logging.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

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
    num_questions: int = Field(default=5, ge=1, le=20)
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query is not empty."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class QuizItem(BaseModel):
    """Single MCQ response item."""

    question: str
    answer: str
    options: list[str]
    difficulty: str
    source_chunk_ids: list[str]


@router.post("/generate", response_model=list[QuizItem])
async def generate_quiz(request: QuizGenerateRequest) -> list[QuizItem]:
    """Generate MCQs from retrieval results.
    
    Enhanced pipeline with:
    - Better keyword extraction (NER + TF-IDF + noun phrases)
    - Multi-strategy distractor generation (WordNet + corpus + entity-based)
    - Question quality filtering
    - Deduplication of similar questions
    """
    try:
        logger.info(
            "Quiz generation requested: query=%s, filters=%s, num_questions=%d",
            request.query,
            request.filters.model_dump(),
            request.num_questions
        )
        
        # Retrieve relevant chunks (request more to account for filtering)
        retrieve_count = max(request.num_questions * 2, 10)
        chunks = retrieval_service.retrieve_chunks(
            query=request.query,
            filters=request.filters.model_dump(),
            top_k=retrieve_count,
        )
        
        if not chunks:
            logger.warning("No chunks retrieved for query: %s", request.query)
            raise HTTPException(
                status_code=404,
                detail="No relevant content found for the given query and filters"
            )
        
        logger.info("Retrieved %d chunks for quiz generation", len(chunks))
        
        # Generate MCQs using enhanced NLP pipeline
        mcqs = build_mcqs(chunks=chunks, num_questions=request.num_questions)
        
        if not mcqs:
            logger.warning(
                "Quiz generation failed - no valid questions generated from %d chunks",
                len(chunks)
            )
            raise HTTPException(
                status_code=422,
                detail="Unable to generate quiz questions from retrieved content. "
                       "Try adjusting your query or filters."
            )
        
        logger.info(
            "Successfully generated %d MCQs (requested %d)",
            len(mcqs),
            request.num_questions
        )
        
        return [QuizItem(**item) for item in mcqs]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except ValueError as exc:
        logger.error("Validation error during quiz generation: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(exc)}"
        ) from exc
        
    except Exception as exc:
        logger.exception("Unexpected error during quiz generation")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during quiz generation. "
                   "Please try again or contact support."
        ) from exc


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for quiz service."""
    try:
        # Quick validation that models can be loaded
        from app.services.quiz_service import _ensure_models_loaded
        _ensure_models_loaded()
        return {"status": "healthy", "service": "quiz_generation"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Quiz service unhealthy: {str(exc)}"
        ) from exc