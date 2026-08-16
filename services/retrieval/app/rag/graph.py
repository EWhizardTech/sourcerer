"""LangGraph agent for retrieval-augmented chat.

Tool-calling agent over the Qdrant knowledge base (and optional web search),
with grounded, citation-annotated answers. Model comes from settings.
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from sourcerer_core.config import settings

from app.rag.tools import search_documents, search_web

logger = logging.getLogger(__name__)

# Primary answer model — configured, not hardcoded.
llm = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)

# Deterministic routing bindings to prevent wrong-tool drift.
llm_documents_only = llm.bind_tools([search_documents])
llm_web_only = llm.bind_tools([search_web])

system_prompt = """You are Sourcerer, an educational assistant that answers strictly from retrieved course material.

You have two tools:

1. search_documents — searches the internal knowledge base of course materials.
   Use this for ALL questions by default.

2. search_web — searches the public internet using Tavily.
   Use this ONLY when the user explicitly asks for a web search
   (phrases like "refer web", "check online", "search the internet",
   "look it up online", "from the web", "web search", "search online").
   Without such an explicit signal, NEVER call search_web.

RULES:
1. You MUST call a tool before answering a question. If a search errors or
   returns nothing, retry AT MOST ONCE with a rephrased query, then answer
   from whatever you have (or say the knowledge base has nothing relevant).
   Never call tools more than twice for one question.
2. Retrieved excerpts are numbered [1], [2], [3]... Ground every claim in them and
   cite inline using those numbers, e.g. "A stack is LIFO [1]." Cite only numbers
   that exist in the retrieved excerpts.
3. Answer ONLY from tool output — never from prior knowledge.
4. If the retrieved content does not answer the question, say so plainly:
   briefly state that the knowledge base has no relevant material for this
   question and suggest rephrasing or ingesting the relevant course documents.
   Do not invent an answer.
5. When answering from web results, cite the same way; the source URLs are
   attached to each numbered result.
6. Be concise and well-structured: short paragraphs, bullet lists where natural,
   Markdown formatting.
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
    """Extract the latest user query text from message history."""
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = getattr(message, "content", "")
            return content if isinstance(content, str) else str(content)
    return ""


def _has_explicit_web_signal(query: str) -> bool:
    """Check whether the user query explicitly asks for web search."""
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in WEB_SIGNAL_PHRASES)


MAX_TOOL_ROUNDS = 3


def agent_node(state: MessagesState):
    """Decide whether to call a tool or respond based on message history."""
    messages = state["messages"]
    logger.info("Agent node invoked. History length: %s", len(messages))

    payload = [SystemMessage(content=system_prompt)] + messages

    # Hard guard: after several tool rounds (e.g. search errors or empty
    # results), force a final answer instead of looping to the recursion limit.
    tool_rounds = sum(1 for m in messages if getattr(m, "type", "") == "tool")
    if tool_rounds >= MAX_TOOL_ROUNDS:
        logger.info("Tool-round cap reached (%s); forcing final answer.", tool_rounds)
        forced = payload + [
            SystemMessage(
                content=(
                    "Search is unavailable right now. Do NOT call any tools. "
                    "Give your final answer from the tool results above, or "
                    "tell the user the knowledge base returned nothing relevant."
                )
            )
        ]
        try:
            response = llm.invoke(forced)
        except Exception as exc:  # noqa: BLE001 - never loop to recursion limit
            logger.warning("Forced-answer invoke failed (%s); using fallback.", exc)
            from langchain_core.messages import AIMessage

            response = AIMessage(
                content=(
                    "I couldn't reach the knowledge base for this question. "
                    "Please try again in a moment."
                )
            )
        return {"messages": [response]}

    user_query = _extract_latest_user_query(messages)
    if _has_explicit_web_signal(user_query):
        logger.info("Explicit web signal detected. Restricting tools to search_web.")
        response = llm_web_only.invoke(payload)
    else:
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
