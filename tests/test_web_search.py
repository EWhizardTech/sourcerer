"""Tests for Tavily web search integration.

Run with:
    uv run python tests/test_web_search.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

# Allow running this file directly via: uv run python tests/test_web_search.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import AIMessage, HumanMessage

from app.core.config import settings
from app.services.retrieval.graph import retrieval_graph
from app.services.retrieval.tools import search_web


def _iter_tool_call_names(messages: Iterable[Any]) -> list[str]:
    """Extract tool call names from a LangGraph message history.

    Args:
        messages: Iterable of messages from graph state.

    Returns:
        List of tool names called by the assistant.
    """
    names: list[str] = []
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in getattr(message, "tool_calls", []) or []:
                name = tool_call.get("name")
                if name:
                    names.append(name)

            # Compatibility path for model outputs that place tool calls in additional_kwargs.
            raw_tool_calls = message.additional_kwargs.get("tool_calls", [])
            for raw_call in raw_tool_calls:
                function_block = raw_call.get("function", {})
                name = function_block.get("name")
                if name:
                    names.append(name)

    return names


def test_search_web_direct() -> None:
    """Test direct search_web invocation and print output."""
    print("\n[TEST] Direct search_web call")
    result = search_web.invoke({"query": "decorator pattern in python", "max_results": 3})
    print(result)
    assert isinstance(result, str)
    assert result.strip()


def test_search_web_without_api_key() -> None:
    """Test that web search returns config warning when TAVILY_API_KEY is missing."""
    print("\n[TEST] search_web with missing TAVILY_API_KEY")
    original_key = settings.TAVILY_API_KEY
    try:
        settings.TAVILY_API_KEY = ""
        result = search_web.invoke({"query": "test query", "max_results": 1})
    finally:
        settings.TAVILY_API_KEY = original_key

    print(result)
    assert (
        result
        == "Web search is not configured. Please set TAVILY_API_KEY in the environment."
    )


def test_graph_with_web_signal() -> None:
    """Test graph behavior when explicit web signal is present."""
    print("\n[TEST] Graph query with explicit web signal")
    initial_state = {"messages": [HumanMessage(content="explain decorator pattern, refer web")]}
    final_state = retrieval_graph.invoke(initial_state, {"recursion_limit": 10})

    final_answer = final_state["messages"][-1].content
    print(final_answer)

    assert isinstance(final_answer, str)
    assert final_answer.strip()
    assert final_answer != "Insufficient info"


def test_graph_without_web_signal() -> None:
    """Test graph behavior when no explicit web signal is present."""
    print("\n[TEST] Graph query without web signal")
    initial_state = {"messages": [HumanMessage(content="explain binary search")]}
    final_state = retrieval_graph.invoke(initial_state, {"recursion_limit": 10})

    tool_names = _iter_tool_call_names(final_state["messages"])
    print(f"Tool calls observed: {tool_names}")

    assert "search_web" not in tool_names


def main() -> None:
    """Run all web-search integration tests as a standalone script."""
    test_search_web_direct()
    test_search_web_without_api_key()
    test_graph_with_web_signal()
    test_graph_without_web_signal()
    print("\nAll Tavily integration tests passed.")


if __name__ == "__main__":
    main()
