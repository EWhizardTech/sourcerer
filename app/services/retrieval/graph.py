import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import settings
from app.services.retrieval.tools import search_documents, search_web

logger = logging.getLogger(__name__)

# Initialize the LLM with Groq.
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)

# Keep a combined binding for parity and future extensibility.
tools = [search_documents, search_web]
llm_with_tools = llm.bind_tools(tools)

# Deterministic routing bindings to prevent wrong-tool drift.
llm_documents_only = llm.bind_tools([search_documents])
llm_web_only = llm.bind_tools([search_web])

system_prompt = """You are a helpful educational assistant named Sourcerer.
Your goal is to answer the user's questions accurately and honestly.

You have two tools available:

1. search_documents - searches the internal knowledge base of course materials.
   Use this for ALL questions by default.

2. search_web - searches the public internet using Tavily.
   Use this ONLY when the user explicitly asks for a web search.
   Explicit web search signals include phrases such as:
     - "refer web"
     - "check online"
     - "search the internet"
     - "look it up online"
     - "from the web"
     - "web search"
     - "search online"
   If the user's message does NOT contain an explicit web search signal,
   do NOT call search_web under any circumstances.

INSTRUCTIONS:
1. You MUST call at least one tool before answering.
2. If the user explicitly requests a web search -> call search_web.
   Otherwise -> call search_documents.
3. Choose k (5-10) for search_documents based on query breadth.
4. If retrieved content does not contain the answer ->
   respond EXACTLY: "Insufficient info"
5. Answer ONLY from the content returned by the tools.
   Do NOT use your prior knowledge.
6. When answering from web results, always cite the source URL.
"""

WEB_SIGNAL_PHRASES = (
    "refer web",
    "check online",
    "search the internet",
    "look it up online",
    "from the web",
    "web search",
    "search online",
)


def _extract_latest_user_query(messages: list[Any]) -> str:
    """Extract the latest user query text from message history.

    Args:
        messages: Full LangGraph message history.

    Returns:
        Latest user message content if present, otherwise an empty string.
    """
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = getattr(message, "content", "")
            return content if isinstance(content, str) else str(content)
    return ""


def _has_explicit_web_signal(query: str) -> bool:
    """Check whether the user query explicitly asks for web search.

    Args:
        query: User query text.

    Returns:
        True if query contains any explicit web-search trigger phrase.
    """
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in WEB_SIGNAL_PHRASES)


def agent_node(state: MessagesState):
    """Decide whether to call a tool or respond based on message history."""
    logger.info("Agent Node invoked. Current history length: %s", len(state["messages"]))
    messages = state["messages"]

    payload = [SystemMessage(content=system_prompt)] + messages

    user_query = _extract_latest_user_query(messages)
    if _has_explicit_web_signal(user_query):
        logger.info("Explicit web signal detected. Restricting tools to search_web.")
        response = llm_web_only.invoke(payload)
    else:
        logger.info("No web signal detected. Restricting tools to search_documents.")
        response = llm_documents_only.invoke(payload)

    return {"messages": [response]}


# Build graph topology.
workflow = StateGraph(MessagesState)
tool_node = ToolNode([search_documents, search_web])

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", tools_condition)
workflow.add_edge("tools", "agent")

retrieval_graph = workflow.compile()
