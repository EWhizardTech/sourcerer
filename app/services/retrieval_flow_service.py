"""Shared retrieval flow service used by retrieval and quiz endpoints.

Runs the LangGraph retrieval workflow and exposes both:
- A formatted chunks string for UI/debug parity with retrieval endpoint.
- Structured chunk objects suitable for quiz generation.
"""

from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage

from app.services.retrieval.graph import retrieval_graph


def _parse_document_blocks(content: str, start_index: int) -> list[dict[str, Any]]:
    """Parse formatted search_documents tool output into structured chunks."""
    pattern = re.compile(
        r"--- Document\s+\d+\s+---\s*\n"
        r"Source:\s*(?P<source>.*?)\n"
        r"(?:Subject:\s*(?P<subject>.*?)\n)?"
        r"Content:\s*\n"
        r"(?P<text>[\s\S]*?)(?=\n--- Document\s+\d+\s+---|\Z)",
        re.MULTILINE,
    )

    chunks: list[dict[str, Any]] = []
    match_count = 0
    for match in pattern.finditer(content):
        source = (match.group("source") or "Unknown").strip()
        subject = (match.group("subject") or "").strip()
        text = (match.group("text") or "").strip()
        if not text:
            continue

        match_count += 1
        chunks.append(
            {
                "chunk_id": f"graph_chunk_{start_index + match_count}",
                "text": text,
                "source": source,
                "tags": {
                    "subject": subject,
                    "topic": "",
                    "keywords": [],
                    "difficulty": "Medium",
                },
            }
        )

    if match_count == 0:
        fallback_text = content.strip()
        if fallback_text:
            chunks.append(
                {
                    "chunk_id": f"graph_chunk_{start_index + 1}",
                    "text": fallback_text,
                    "source": "tool_output",
                    "tags": {
                        "subject": "",
                        "topic": "",
                        "keywords": [],
                        "difficulty": "Medium",
                    },
                }
            )

    return chunks


def run_retrieval_flow(query: str, recursion_limit: int = 10) -> dict[str, Any]:
    """Execute LangGraph retrieval flow and return answer + chunk payloads."""
    initial_state = {"messages": [HumanMessage(content=query)]}
    final_state = retrieval_graph.invoke(initial_state, {"recursion_limit": recursion_limit})

    final_message = final_state["messages"][-1]

    chunks_text_parts: list[str] = []
    structured_chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for msg in final_state["messages"]:
        if isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            content = content.strip()
            if not content:
                continue
            chunks_text_parts.append(content)
            parsed_chunks = _parse_document_blocks(content, chunk_index)
            structured_chunks.extend(parsed_chunks)
            chunk_index += len(parsed_chunks)

    return {
        "answer": final_message.content,
        "chunks_text": "\n\n".join(chunks_text_parts) if chunks_text_parts else None,
        "structured_chunks": structured_chunks,
    }
