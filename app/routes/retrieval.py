import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, ToolMessage
from app.services.retrieval.graph import retrieval_graph

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
        # Initialize thread state with human message
        initial_state = {
            "messages": [HumanMessage(content=request.query)]
        }
        
        # Invoke graph (we may want to limit steps with recursion_limit, e.g. recursion_limit=10)
        final_state = retrieval_graph.invoke(initial_state, {"recursion_limit": 10})
        
        # The last message is the final response from the agent
        final_message = final_state["messages"][-1]
        
        # Extract chunks from ToolMessages
        chunks = ""
        for msg in final_state["messages"]:
            if isinstance(msg, ToolMessage):
                chunks += msg.content + "\n\n"
        
        return RetrievalResponse(
            answer=final_message.content, 
            chunks=chunks.strip() if chunks else None
        )
        
    except Exception as e:
        logger.error(f"Error during retrieval workflow: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during retrieval workflow")
