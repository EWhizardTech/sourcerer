"""Redis-backed conversation memory for the chat endpoints.

History is stored per session as a JSON list of {role, content} entries,
capped to the most recent N messages with a TTL, so follow-up questions
carry context without unbounded growth.
"""

from __future__ import annotations

import json
import logging
import uuid

import redis
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def _key(session_id: str) -> str:
    return f"chat:{session_id}"


def new_session_id() -> str:
    return uuid.uuid4().hex


def load_history(session_id: str) -> list[BaseMessage]:
    """Load conversation history as LangChain messages (oldest first)."""
    try:
        raw = _redis().get(_key(session_id))
    except redis.RedisError as exc:
        logger.warning("Chat memory unavailable (%s); continuing stateless.", exc)
        return []
    if not raw:
        return []

    messages: list[BaseMessage] = []
    for entry in json.loads(raw):
        if entry.get("role") == "user":
            messages.append(HumanMessage(content=entry.get("content", "")))
        elif entry.get("role") == "assistant":
            messages.append(AIMessage(content=entry.get("content", "")))
    return messages


def append_exchange(session_id: str, user_text: str, assistant_text: str) -> None:
    """Append a user/assistant exchange and persist with TTL + cap."""
    try:
        client = _redis()
        raw = client.get(_key(session_id))
        history = json.loads(raw) if raw else []
        history.extend(
            [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text},
            ]
        )
        history = history[-settings.CHAT_HISTORY_MAX_MESSAGES :]
        client.set(
            _key(session_id),
            json.dumps(history),
            ex=settings.CHAT_HISTORY_TTL_SECONDS,
        )
    except redis.RedisError as exc:
        logger.warning("Failed to persist chat history (%s).", exc)


def clear_history(session_id: str) -> bool:
    """Delete a session's history. Returns True if a session existed."""
    try:
        return bool(_redis().delete(_key(session_id)))
    except redis.RedisError as exc:
        logger.warning("Failed to clear chat history (%s).", exc)
        return False
