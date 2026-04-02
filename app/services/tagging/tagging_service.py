# app/services/tagging/tagging_service.py

import json
import logging
from typing import List, Optional

from groq import Groq
from app.core.config import settings
from app.services.chunking.types import Chunk, TextChunk, ImageChunk
from app.services.tagging.tagging_types import TagSchema, TaggedChunk

logger = logging.getLogger(__name__)

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

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
    return {
        "subject": "",
        "topic": "",
        "keywords": [],
        "difficulty": ""
    }

def tag_chunk(chunk: Chunk) -> TaggedChunk:
    """Tags an individual chunk using Groq LLM.
    
    Args:
        chunk: A TextChunk or ImageChunk.
        
    Returns:
        A TaggedChunk with tags and standardized structure.
    """
    chunk_id = chunk.get("chunk_id", "unknown")
    
    # 1. Image detection
    if "image" in chunk:
        return {
            "chunk_id": chunk_id,
            "text": "",
            "image": chunk.get("image"),
            "metadata": chunk.get("metadata", {}),
            "tags": create_empty_tags()
        }

    # 2. Text/Transcript extraction
    text = chunk.get("text", "")
    metadata = chunk.get("metadata", {})
    
    # 3. Call Groq with exponential backoff
    max_retries = 5
    initial_delay = 1
    
    for i in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": TAGGING_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Content to tag:\n\n{text}"}
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
                                    "items": {"type": "string"}
                                },
                                "difficulty": {
                                    "type": "string",
                                    "enum": ["Easy", "Medium", "Hard"]
                                }
                            },
                            "required": ["subject", "topic", "keywords", "difficulty"],
                            "additionalProperties": False
                        }
                    }
                },
                temperature=0.1
            )
            
            raw_response = response.choices[0].message.content
            tags: TagSchema = json.loads(raw_response)
                    
            return {
                "chunk_id": chunk_id,
                "text": text,
                "image": None,
                "metadata": metadata,
                "tags": tags
            }
            
        except Exception as e:
            # Handle rate limiting (429) specifically if possible, 
            # otherwise check if it's in the error message
            if "rate_limit_exceeded" in str(e).lower() or "429" in str(e):
                delay = initial_delay * (2 ** i)
                logger.warning(f"Groq Rate Limit (429) hit for chunk {chunk_id}. Retrying in {delay}s... (Attempt {i+1}/{max_retries})")
                import time
                time.sleep(delay)
                continue
            
            logger.error(f"Failed to tag chunk {chunk_id}: {str(e)}")
            return {
                "chunk_id": chunk_id,
                "text": text,
                "image": None,
                "metadata": metadata,
                "tags": create_empty_tags()
            }

    # Final fallback if all retries fail
    logger.error(f"Failed to tag chunk {chunk_id} after {max_retries} attempts.")
    return {
        "chunk_id": chunk_id,
        "text": text,
        "image": None,
        "metadata": metadata,
        "tags": create_empty_tags()
    }

def tag_chunks(chunks: List[Chunk]) -> List[TaggedChunk]:
    """Process multiple chunks."""
    logger.info(f"Starting tagging for {len(chunks)} chunks")
    results = [tag_chunk(c) for c in chunks]
    logger.info(f"Completed tagging for {len(chunks)} chunks")
    return results
