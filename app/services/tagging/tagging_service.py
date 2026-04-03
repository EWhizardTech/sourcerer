# app/services/tagging/tagging_service.py

import json
import logging
import threading
import time
from typing import List, Optional

from groq import Groq

from app.core.config import settings
from app.services.chunking.types import Chunk, ImageChunk, TextChunk
from app.services.tagging.tagging_types import TaggedChunk, TagSchema

logger = logging.getLogger(__name__)

# Initialize Groq clients from comma-separated keys
_api_keys = [k.strip() for k in settings.GROQ_API_KEY.split(",") if k.strip()]
if not _api_keys:
    logger.error("No GROQ_API_KEY found in settings")
    clients = []
else:
    clients = [Groq(api_key=key) for key in _api_keys]

_current_client_idx = 0
_client_lock = threading.Lock()


def get_next_client() -> Optional[Groq]:
    """Get the next Groq client in a thread-safe round-robin fashion."""
    global _current_client_idx
    if not clients:
        return None
    with _client_lock:
        client = clients[_current_client_idx]
        _current_client_idx = (_current_client_idx + 1) % len(clients)
        return client


TAGGING_SYSTEM_PROMPT = """
You are an expert educator and academic librarian. Your task is to extract tagging metadata from a educational content chunk.

STRICT JSON OUTPUT:
{
  "subject": "Main academic subject (e.g., Computer Science, Biology, Finance)",
  "topic": "Specific topic (e.g., Data Structures, Mitosis, Options Trading)",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "difficulty": "Easy/Medium/Hard"
}

RULES:
- keywords should be 3-5 specific terms.
- Use academic, standardized terminology.
- If the content is vague, use the most likely context.
- Keep output concise and strictly follow the JSON structure.
"""


def create_empty_tags() -> TagSchema:
    """Return an empty tag schema."""
    return {"subject": "", "topic": "", "keywords": [], "difficulty": ""}


def _execute_tagging(
    client: Groq, text: str, chunk_id: str, metadata: dict
) -> TaggedChunk:
    """Helper to execute the Groq chat completion call."""
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": TAGGING_SYSTEM_PROMPT},
            {"role": "user", "content": f"Content to tag:\n\n{text}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "tag_schema",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "topic": {"type": "string"},
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "difficulty": {
                            "type": "string",
                            "enum": ["Easy", "Medium", "Hard"],
                        },
                    },
                    "required": ["subject", "topic", "keywords", "difficulty"],
                    "additionalProperties": False,
                },
            },
        },
        temperature=0.1,
    )

    raw_response = response.choices[0].message.content
    tags: TagSchema = json.loads(raw_response)

    return {
        "chunk_id": chunk_id,
        "text": text,
        "image": None,
        "metadata": metadata,
        "tags": tags,
    }


def is_rate_limit_error(e: Exception) -> bool:
    """Check if the exception is a 429 Rate Limit error."""
    err_str = str(e).lower()
    return "rate_limit_exceeded" in err_str or "429" in err_str


def tag_chunk(chunk: Chunk) -> TaggedChunk:
    """Tags an individual chunk using rotated Groq API keys.

    Args:
        chunk: A TextChunk or ImageChunk.

    Returns:
        A TaggedChunk with tags or fallback empty tags.
    """
    chunk_id = chunk.get("chunk_id", "unknown")

    # 1. Image detection
    if "image" in chunk:
        return {
            "chunk_id": chunk_id,
            "text": "",
            "image": chunk.get("image"),
            "metadata": chunk.get("metadata", {}),
            "tags": create_empty_tags(),
        }

    # 2. Text/Transcript extraction
    text = chunk.get("text", "")
    metadata = chunk.get("metadata", {})

    if not clients:
        logger.error(f"No Groq clients available to tag chunk {chunk_id}")
        return {
            "chunk_id": chunk_id,
            "text": text,
            "image": None,
            "metadata": metadata,
            "tags": create_empty_tags(),
        }

    num_keys = len(clients)

    # Attempt 1: Try all keys if 429 occurs
    for i in range(num_keys):
        client = get_next_client()
        try:
            return _execute_tagging(client, text, chunk_id, metadata)
        except Exception as e:
            if is_rate_limit_error(e):
                logger.warning(
                    f"Groq Rate Limit (429) hit for key {i+1}/{num_keys} on chunk {chunk_id}. Trying next key..."
                )
                continue
            
            
            logger.error(f"Failed to tag chunk {chunk_id} with non-rate-limit error: {str(e)}")
            # For other errors, we might want to try another key too, 
            # but user specifically asked for rotation on 429.
            # We'll return empty tags to keep the pipeline moving.
            return {
                "chunk_id": chunk_id,
                "text": text,
                "image": None,
                "metadata": metadata,
                "tags": create_empty_tags(),
            }

    # Attempt 2: If all keys failed with 429, wait 10s and try once more
    logger.warning(
        f"All {num_keys} Groq keys rate limited for chunk {chunk_id}. Waiting 10 seconds for final retry..."
    )
    time.sleep(10)

    client = get_next_client()
    try:
        return _execute_tagging(client, text, chunk_id, metadata)
    except Exception as e:
        logger.error(
            f"Final Groq retry failed for chunk {chunk_id} after 10s wait: {str(e)}"
        )
        return {
            "chunk_id": chunk_id,
            "text": text,
            "image": None,
            "metadata": metadata,
            "tags": create_empty_tags(),
        }


def tag_chunks(chunks: List[Chunk]) -> List[TaggedChunk]:
    """Process multiple chunks."""
    logger.info(f"Starting tagging for {len(chunks)} chunks")
    results = [tag_chunk(c) for c in chunks]
    logger.info(f"Completed tagging for {len(chunks)} chunks")
    return results
