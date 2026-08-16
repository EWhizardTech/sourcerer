"""LangChain tools for the retrieval agent.

search_documents returns BOTH a formatted context string for the LLM and the
structured chunks (with scores) as a tool artifact, so citations flow to the
API without any text parsing.
"""

import logging
from typing import List, Optional

from langchain_core.tools import tool
from tavily import TavilyClient

try:
    from tavily.errors import UsageLimitExceededError
except Exception:  # pragma: no cover - defensive import fallback
    UsageLimitExceededError = None

from sourcerer_core.config import settings
from sourcerer_core.embedding.embedding_service import embedding_service
from sourcerer_core.vector_store.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)


def _structure_hit(index: int, hit: dict) -> dict:
    """Normalize a scored vector-store hit into an API-facing source dict."""
    return {
        "id": index,
        "chunk_id": str(hit.get("point_id", index)),
        "text": hit.get("text", ""),
        "source": hit.get("source", "Unknown"),
        "page_number": hit.get("page_number"),
        "score": hit.get("rerank_score", hit.get("score")),
        "course_code": hit.get("course_code", ""),
        "subject": hit.get("subject", ""),
        "topic": hit.get("topic", ""),
        "type": "document",
    }


@tool(response_format="content_and_artifact")
def search_documents(
    query: str,
    k: int = 5,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
) -> tuple[str, list[dict]]:
    """
    Search the vector database for educational documents matching the query.

    Args:
        query: The search query string. Make it specific.
        k: The number of documents to retrieve. Typically between 3 and 10 based on how broad the query is.
        subject: Optional main academic subject to filter by (e.g., "Computer Science", "Biology").
        topic: Optional specific topic to filter by (e.g., "Data Structures", "Mitosis").
        keywords: Optional list of keywords to filter by.
        difficulty: Optional difficulty level ("Easy", "Medium", "Hard") to filter by.

    Returns:
        Numbered document excerpts. Cite them in your answer as [1], [2], ...
    """
    logger.info(
        "search_documents query=%r k=%s subject=%s topic=%s", query, k, subject, topic
    )
    try:
        query_vector = embedding_service.embed_query(query)
        if not query_vector:
            return "Error: Failed to generate embeddings for the query.", []

        hits = vector_store_service.search(
            query_vector=query_vector,
            query_text=query,
            k=k,
            subject=subject,
            topic=topic,
            keywords=keywords,
            difficulty=difficulty,
        )

        if not hits:
            return (
                "No relevant documents found. Please try modifying your search "
                "query or removing filters.",
                [],
            )

        sources = [_structure_hit(i + 1, hit) for i, hit in enumerate(hits)]

        formatted = []
        for src in sources:
            page = src["page_number"] if src["page_number"] is not None else "N/A"
            formatted.append(
                f"[{src['id']}] {src['source']} (Page {page})"
                + (f" — {src['subject']}" if src["subject"] else "")
                + f"\n{src['text']}\n"
            )

        return "\n".join(formatted), sources

    except Exception as e:
        logger.error("Error in search_documents tool: %s", e)
        return f"Error executing search: {e}", []


@tool(response_format="content_and_artifact")
def search_web(query: str, max_results: int = 5) -> tuple[str, list[dict]]:
    """Search the public web using Tavily for real-time information.

    Use this tool ONLY when the user has explicitly requested a web search
    in their message - for example, phrases like "refer web", "check online",
    "search the internet", "look it up online", or "from the web".

    Do NOT call this tool for general knowledge questions. Use search_documents
    for all knowledge base lookups.

    Args:
        query: The search query to look up on the web.
        max_results: Number of web results to retrieve. Default is 5.

    Returns:
        Numbered web results. Cite them in your answer as [1], [2], ...
    """
    logger.info("search_web query=%r max_results=%s", query, max_results)
    if not settings.TAVILY_API_KEY:
        return (
            "Web search is not configured. Please set TAVILY_API_KEY in the environment.",
            [],
        )

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query, search_depth="basic", max_results=max_results
        )

        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            return "No web results found for the query. Try rephrasing.", []

        sources = []
        formatted = []
        for i, result in enumerate(results, start=1):
            title = result.get("title", "Untitled")
            url = result.get("url", "Unknown")
            content = result.get("content", "")
            score = result.get("score")
            sources.append(
                {
                    "id": i,
                    "chunk_id": url,
                    "text": content,
                    "source": title,
                    "url": url,
                    "page_number": None,
                    "score": score,
                    "type": "web",
                }
            )
            formatted.append(f"[{i}] {title} — {url}\n{content}\n")

        return "\n".join(formatted), sources

    except Exception as e:
        if UsageLimitExceededError and isinstance(e, UsageLimitExceededError):
            logger.error("Tavily web search failed: %s", e)
            return "Error: Tavily usage limit exceeded. Please check your plan.", []

        logger.error("Tavily web search failed: %s", e)
        return "Error: Web search failed. Please try again later.", []
