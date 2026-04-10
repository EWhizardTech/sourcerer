import logging
from typing import List, Optional
from langchain_core.tools import tool
from tavily import TavilyClient

try:
    from tavily.errors import UsageLimitExceededError
except Exception:  # pragma: no cover - defensive import fallback
    UsageLimitExceededError = None

from app.core.config import settings
from app.services.embedding.embedding_service import embedding_service
from app.services.vector_store.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)


@tool
def search_web(query: str, max_results: int = 5) -> str:
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
        A formatted string of web search results, or an error message.
    """
    logger.info("Tool search_web called with query='%s', max_results=%s", query, max_results)
    if not settings.TAVILY_API_KEY:
        return "Web search is not configured. Please set TAVILY_API_KEY in the environment."

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
        )

        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            return "No web results found for the query. Try rephrasing."

        formatted_results = []
        for i, result in enumerate(results):
            title = result.get("title", "Untitled")
            url = result.get("url", "Unknown")
            content = result.get("content", "")
            formatted_results.append(
                f"--- Web Result {i+1} ---\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Content:\n{content}\n"
            )

        return "\n".join(formatted_results)
    except Exception as e:
        if UsageLimitExceededError and isinstance(e, UsageLimitExceededError):
            logger.error("Tavily web search failed: %s", e)
            return "Error: Tavily usage limit exceeded. Please check your plan."

        logger.error("Tavily web search failed: %s", e)
        return "Error: Web search failed. Please try again later."

@tool
def search_documents(
    query: str,
    k: int = 5,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
) -> str:
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
        A formatted string containing the retrieved document chunks and their metadata,
        or a message indicating insufficient information if no results are found.
    """
    print(f"Tool search_documents called with query='{query}', k={k}, filters=(subject={subject}, topic={topic})")
    try:
        # Embed the query
        query_vector = embedding_service.embed_query(query)
        if not query_vector:
            return "Error: Failed to generate embeddings for the query."

        # Search the vector store
        results = vector_store_service.search(
            query_vector=query_vector,
            query_text=query,
            k=k,
            subject=subject,
            topic=topic,
            keywords=keywords,
            difficulty=difficulty,
        )

        if not results:
            return "No relevant documents found. Please try modifying your search query or removing filters."

        # Format the results
        formatted_results = []
        for i, payload in enumerate(results):
            content = payload.get("text", "Image or non-text content")
            source = payload.get("source", "Unknown")
            page = payload.get("page_number", "N/A")
            subj = payload.get("subject", "")
            
            formatted_results.append(
                f"--- Document {i+1} ---\n"
                f"Source: {source} (Page {page})\n"
                f"Subject: {subj}\n"
                f"Content:\n{content}\n"
            )
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error in search_documents tool: {str(e)}")
        return f"Error executing search: {str(e)}"
