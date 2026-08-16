"""Chat endpoints: streaming (SSE) and blocking, with session memory."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.rag import memory
from app.rag.flow import run_chat, stream_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    query: str = Field(min_length=1)
    session_id: str | None = None


class ChatSource(BaseModel):
    """A retrieved source backing the answer."""

    id: int
    chunk_id: str
    text: str
    source: str
    page_number: int | None = None
    score: float | None = None
    course_code: str | None = None
    subject: str | None = None
    topic: str | None = None
    url: str | None = None
    type: str = "document"


class ChatResponse(BaseModel):
    """Blocking chat response."""

    answer: str
    sources: list[ChatSource]
    session_id: str
    condensed_query: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Single-shot chat with memory (non-streaming)."""
    try:
        result = run_chat(query=request.query, session_id=request.session_id)
    except Exception as exc:
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail="Chat failed") from exc
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Streaming chat via Server-Sent Events.

    Emits events: session, sources, token, done, error.
    """

    async def event_source():
        try:
            async for event in stream_chat(
                query=request.query, session_id=request.session_id
            ):
                name = event.pop("event")
                yield f"event: {name}\ndata: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface errors on the stream
            logger.exception("Chat stream failed")
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str) -> dict:
    """Clear a chat session's memory."""
    existed = memory.clear_history(session_id)
    return {"cleared": existed, "session_id": session_id}
