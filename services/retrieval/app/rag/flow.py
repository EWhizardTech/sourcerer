"""Chat/retrieval flow orchestration.

Wraps the LangGraph agent with:
- Redis conversation memory (session-scoped follow-ups)
- Query condensation (follow-ups rewritten standalone for better retrieval)
- Structured sources pulled from ToolMessage artifacts (no text parsing)
- Both a blocking runner and an async token-streaming runner
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq

from sourcerer_core.config import settings

from app.rag import memory
from app.rag.graph import retrieval_graph

logger = logging.getLogger(__name__)

_condenser: ChatGroq | None = None


def _get_condenser() -> ChatGroq:
    global _condenser
    if _condenser is None:
        _condenser = ChatGroq(
            model=settings.GROQ_FAST_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )
    return _condenser


def condense_query(query: str, history: list[BaseMessage]) -> str:
    """Rewrite a follow-up question as a standalone query using history."""
    if not history:
        return query

    transcript = "\n".join(
        f"{'User' if m.type == 'human' else 'Assistant'}: {m.content}"
        for m in history[-6:]
    )
    prompt = (
        "Given this conversation and a follow-up question, rewrite the follow-up "
        "as a single standalone question that contains all context needed to "
        "search a knowledge base. Return ONLY the rewritten question.\n\n"
        f"Conversation:\n{transcript}\n\nFollow-up question: {query}"
    )
    try:
        response = _get_condenser().invoke(prompt)
        rewritten = (response.content or "").strip()
        if rewritten:
            logger.info("Condensed query: %r -> %r", query, rewritten)
            return rewritten
    except Exception as exc:  # noqa: BLE001 - condensation is best-effort
        logger.warning("Query condensation failed (%s); using original.", exc)
    return query


def _collect_sources(messages: list[Any]) -> list[dict]:
    """Gather structured sources from tool artifacts, deduped by chunk_id."""
    sources: list[dict] = []
    seen: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
            for src in msg.artifact:
                key = str(src.get("chunk_id"))
                if key not in seen:
                    seen.add(key)
                    sources.append({**src, "id": len(sources) + 1})
    return sources


def _final_answer(messages: list[Any]) -> str:
    """Last assistant message without pending tool calls."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def _build_state(query: str, session_id: str | None) -> tuple[list[BaseMessage], str, str]:
    """Load history, condense the query, and build the initial message list."""
    sid = session_id or memory.new_session_id()
    history = memory.load_history(sid) if session_id else []
    effective_query = condense_query(query, history)
    messages = [*history, HumanMessage(content=effective_query)]
    return messages, sid, effective_query


def run_chat(
    query: str,
    session_id: str | None = None,
    recursion_limit: int = 10,
) -> dict[str, Any]:
    """Blocking chat run: returns answer, structured sources, session id."""
    messages, sid, effective_query = _build_state(query, session_id)

    final_state = retrieval_graph.invoke(
        {"messages": messages}, {"recursion_limit": recursion_limit}
    )

    answer = _final_answer(final_state["messages"])
    sources = _collect_sources(final_state["messages"])

    memory.append_exchange(sid, query, answer)

    return {
        "answer": answer,
        "sources": sources,
        "session_id": sid,
        "condensed_query": effective_query if effective_query != query else None,
    }


async def stream_chat(
    query: str,
    session_id: str | None = None,
    recursion_limit: int = 10,
) -> AsyncIterator[dict[str, Any]]:
    """Async chat run yielding events:

    {"event": "session", ...}  once, immediately (session id)
    {"event": "sources", ...}  when a tool returns retrieved chunks
    {"event": "token", ...}    for each answer token
    {"event": "done", ...}     final answer + all sources
    """
    messages, sid, effective_query = _build_state(query, session_id)

    yield {"event": "session", "session_id": sid}

    collected_sources: list[dict] = []
    seen_chunks: set[str] = set()
    answer_parts: list[str] = []

    async for mode, payload in retrieval_graph.astream(
        {"messages": messages},
        {"recursion_limit": recursion_limit},
        stream_mode=["updates", "messages"],
    ):
        if mode == "messages":
            chunk, _meta = payload
            if (
                isinstance(chunk, AIMessageChunk)
                and chunk.content
                and not chunk.tool_call_chunks
            ):
                text = (
                    chunk.content
                    if isinstance(chunk.content, str)
                    else "".join(
                        part.get("text", "")
                        for part in chunk.content
                        if isinstance(part, dict)
                    )
                )
                if text:
                    answer_parts.append(text)
                    yield {"event": "token", "text": text}

        elif mode == "updates":
            for node_output in payload.values():
                for msg in node_output.get("messages", []):
                    if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
                        fresh = []
                        for src in msg.artifact:
                            key = str(src.get("chunk_id"))
                            if key not in seen_chunks:
                                seen_chunks.add(key)
                                fresh.append(
                                    {**src, "id": len(collected_sources) + len(fresh) + 1}
                                )
                        if fresh:
                            collected_sources.extend(fresh)
                            yield {"event": "sources", "sources": fresh}

    answer = "".join(answer_parts).strip()
    memory.append_exchange(sid, query, answer)

    yield {
        "event": "done",
        "answer": answer,
        "sources": collected_sources,
        "session_id": sid,
        "condensed_query": effective_query if effective_query != query else None,
    }
