import logging
from typing import List, Optional
from langchain_core.tools import tool

from app.services.embedding.embedding_service import embedding_service
from app.services.vector_store.vector_store_service import vector_store_service

logger = logging.getLogger(__name__)

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
