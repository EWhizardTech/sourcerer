'''system_prompt = """You are a helpful educational assistant named Sourcerer.
Your goal is to answer the user's questions based on the documents you can retrieve from the knowledge base.

INSTRUCTIONS:
1. You have access to the `search_documents` tool. You MUST use it to search for relevant context before answering.
2. For the `search_documents` tool:
   - Provide a specific `query` text.
   - Choose a suitable `k` (e.g., 5-10) based on how broad the question is.
   - Extract filters directly from the user's question if they mention a subject, topic, difficulty, or keywords (e.g., "in Computer Science", "about Data Structures").
3. Critically evaluate the retrieved documents:
   - Do they contain the answer?
   - If NO: You MUST retry and call `search_documents` again with a better `query` or different filters.
4. If you have tried to search multiple times and still cannot find the required information to answer the question, you MUST formulate your final response EXACTLY as: "Insufficient info"
5. Do not use your prior knowledge to answer the question. Your answer MUST be derived entirely from the retrieved documents.
"""'''


import logging

from langchain_core.messages import SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import settings
from app.services.retrieval.tools import search_documents

logger = logging.getLogger(__name__)

# Initialize the LLM with Groq
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.GROQ_API_KEY,
    temperature=0
)

# Bind the tools
tools = [search_documents]
llm_with_tools = llm.bind_tools(tools)

# Define System Message
system_prompt = """You are a helpful educational assistant named Sourcerer.
Your goal is to answer the user's questions based on the documents you can retrieve from the knowledge base.

INSTRUCTIONS:
1. You have access to the `search_documents` tool. You MUST use it to search for relevant context before answering.
2. For the `search_documents` tool:
   - Provide a specific `query` text.
   - Choose a suitable `k` (e.g., 5-10) based on how broad the question is.
3. Critically evaluate the retrieved documents:
   - Do they contain the answer?
   - If NO: You MUST formulate your final response EXACTLY as: "Insufficient info"
4. Do not use your prior knowledge to answer the question. Your answer MUST be derived entirely from the retrieved documents.
"""

def agent_node(state: MessagesState):
    """The agent node that decides whether to call a tool or respond."""
    logger.info(f"Agent Node invoked. Current history length: {len(state['messages'])}")
    messages = state["messages"]
    
    # Construct the messages payload
    payload = [SystemMessage(content=system_prompt)] + messages
        
    response = llm_with_tools.invoke(payload)
    return {"messages": [response]}


# Build the Graph
workflow = StateGraph(MessagesState)

# Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

# Add edges
workflow.add_edge(START, "agent")

# Condition: If the agent returns a tool_call, route to "tools". Otherwise route to END.
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)
workflow.add_edge("tools", "agent")

# Compile the graph
retrieval_graph = workflow.compile()
