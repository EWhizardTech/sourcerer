import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.retrieval_flow_service import run_retrieval_flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["Retrieval"])

class RetrievalRequest(BaseModel):
    query: str

class RetrievalResponse(BaseModel):
    answer: str
    chunks: str | None = None

@router.post("/", response_model=RetrievalResponse)
async def retrieve_answer(request: RetrievalRequest):
    """
    Given a user query, this endpoint uses LangGraph to agentically search the custom knowledge base
    and returns a summarized answer based on the retrieved documents.
    """
    logger.info(f"Received retrieval query: {request.query}")
    try:
        result = run_retrieval_flow(request.query, recursion_limit=10)
        return RetrievalResponse(
            answer=result["answer"],
            chunks=result["chunks_text"],
        )
        
    except Exception as e:
        logger.error(f"Error during retrieval workflow: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during retrieval workflow")
