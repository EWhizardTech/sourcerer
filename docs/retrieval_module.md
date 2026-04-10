# Sourcerer — Retrieval Module Deep Dive

## Overview

The retrieval module is the **query-time brain** of Sourcerer. It takes a natural language question from a user, uses an LLM agent to intelligently search the knowledge base, and returns a grounded answer derived entirely from retrieved documents.

---

## File Structure

```
app/
├── routes/
│   └── retrieval.py              ← FastAPI endpoint
└── services/
    └── retrieval/
        ├── __init__.py
        ├── graph.py              ← LangGraph StateGraph definition
        └── tools.py              ← search_documents LangChain tool
```

**Dependency chain:**
```
retrieval.py  →  graph.py  →  tools.py
                               ├── embedding_service.py
                               └── vector_store_service.py
```

---

## API Endpoint

**File:** `app/routes/retrieval.py`

```
POST /api/v1/retrieve/
```

**Request:**
```json
{ "query": "What is Big-O notation?" }
```

**Response:**
```json
{ "answer": "Big-O notation is a mathematical notation that..." }
```

**What it does:**
1. Wraps the query in a `HumanMessage`
2. Calls `retrieval_graph.invoke(initial_state, {"recursion_limit": 10})`
3. Extracts the last message content from the final state
4. Returns it as the answer

**Error handling:** Returns HTTP 500 on any exception during the graph execution.

---

## LangGraph Agent (`graph.py`)

### Architecture: ReAct Loop

```
START
  │
  ▼
[ agent_node ]  ◄──────────────────────────┐
  │                                         │
  │ llm_with_tools.invoke(                  │
  │   [SystemMessage] + state["messages"])  │
  │                                         │
  ├── tool_call? ──YES──► [ ToolNode ]      │
  │                           │             │
  │                    executes tool         │
  │                           │             │
  │                    returns result ───────┘
  │
  └── no tool_call ──► END
```

### Nodes

| Node         | Type                   | What it does                                      |
|-------------|------------------------|---------------------------------------------------|
| `agent`     | Custom (`agent_node`)  | Invokes LLM with system prompt + message history  |
| `tools`     | `ToolNode` (prebuilt)  | Executes whatever tool the agent requested        |

### Edges

| From    | Condition                   | To       |
|---------|----------------------------|----------|
| START   | always                     | `agent`  |
| `agent` | `tools_condition` (tool call?) | `tools` or END |
| `tools` | always                     | `agent`  |

### LLM Configuration

```python
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.GROQ_API_KEY,
    temperature=0  # deterministic — critical for factual RAG
)

tools = [search_documents]
llm_with_tools = llm.bind_tools(tools)
```

**Why temperature=0?** Retrieval is a factual task. We want consistent, reproducible answers, not creative generation.

### System Prompt

```
You are a helpful educational assistant named Sourcerer.
Your goal is to answer the user's questions based on the documents
you can retrieve from the knowledge base.

INSTRUCTIONS:
1. You MUST call search_documents before answering.
2. Choose k (5-10) based on query breadth.
3. If retrieved docs don't contain the answer →
   respond EXACTLY: "Insufficient info"
4. Answer ONLY from retrieved documents. No prior knowledge.
```

**Critical rules:**
- The agent is **forced to use the tool first** — it cannot answer without searching
- "Insufficient info" is the exact string to return when nothing relevant is found
- Prior knowledge is explicitly forbidden — pure RAG

### Safety: `recursion_limit=10`
Prevents infinite tool-call loops. If the agent loops more than 10 times without reaching END, LangGraph raises an error. The route handler catches it and returns HTTP 500.

---

## search_documents Tool (`tools.py`)

### Signature

```python
@tool
def search_documents(
    query: str,
    k: int = 5,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
) -> str:
```

### How It Works

```
1. Embed query
   embedding_service.embed_query(query)
   → Gemini gemini-embedding-2-preview
   → config: task_type="RETRIEVAL_QUERY"
   → returns List[float] (2048 dimensions)

2. Search Qdrant
   vector_store_service.search(
     query_vector,   ← dense vector from step 1
     query_text,     ← original query string (for sparse BM25)
     k,
     subject, topic, keywords, difficulty
   )

3. Format results
   For each hit.payload:
   --- Document N ---
   Source: <file_path> (Page <num>)
   Subject: <subject>
   Content:
   <text>
```

### Filter Parameters

These are **optional** and extracted by the LLM from the user's query:

| Parameter    | Qdrant field | Match type    | Example value                    |
|-------------|--------------|---------------|----------------------------------|
| `subject`   | `subject`    | `MatchValue`  | `"Computer Science"`            |
| `topic`     | `topic`      | `MatchValue`  | `"Data Structures"`             |
| `keywords`  | `keywords`   | `MatchAny`    | `["binary tree", "traversal"]`  |
| `difficulty`| `difficulty` | `MatchValue`  | `"Medium"`                      |

**How the LLM knows what to filter by:**
The tool docstring explicitly instructs the LLM on when to set each filter. The LLM extracts these from the user's phrasing, e.g. "in Computer Science" → `subject="Computer Science"`.

**Filters not yet supported in tool:**
- `course_code` — stored in payload but not exposed as a filter parameter
- `year` — same

### Return Format

On success, a formatted string like:
```
--- Document 1 ---
Source: CS101 / 2024 / Lecture_01.pdf (Page 3)
Subject: Computer Science
Content:
Big-O notation describes the upper bound of an algorithm's time complexity...

--- Document 2 ---
...
```

On no results:
```
No relevant documents found. Please try modifying your search query or removing filters.
```

On embedding failure:
```
Error: Failed to generate embeddings for the query.
```

---

## Hybrid Search in Qdrant (`vector_store_service.py`)

### `search()` method

```python
def search(
    query_vector: List[float],
    query_text: str,
    k: int = 5,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    difficulty: Optional[str] = None,
) -> List[dict]:
```

### Qdrant Query API call

```python
results = self.client.query_points(
    collection_name=self.collection_name,
    prefetch=[
        models.Prefetch(
            query=query_vector,    # dense embedding
            using="dense",
            limit=k,
        ),
        models.Prefetch(
            query=models.Document(text=query_text, model="Qdrant/bm25"),
            using="sparse",        # BM25 via fastembed
            limit=k,
        ),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),  # Reciprocal Rank Fusion
    query_filter=query_filter,     # Optional metadata filters
    limit=k,
)
```

### Why this architecture?

| Approach                  | Dense | Sparse | Combined |
|--------------------------|-------|--------|----------|
| Semantic matching         | ✅    | ❌     | ✅       |
| Exact keyword matching    | ❌    | ✅     | ✅       |
| Technical terms/acronyms  | Weak  | ✅     | ✅       |
| Near-duplicate paraphrases| ✅    | Weak   | ✅       |

**RRF (Reciprocal Rank Fusion):**
- Ranks each result by its position in both dense and sparse result lists
- Score = 1/(rank_dense + k) + 1/(rank_sparse + k)
- Does NOT require manual weight tuning (no 0.7/0.3 magic numbers)

**CRITICAL design constraint from `.prompts/7-retrieval.md`:**
```
- DO NOT manually combine scores
- DO NOT use weighted sum (0.7/0.3)
- MUST use Qdrant Query API
```

---

## Embedding at Query Time (`embedding_service.py`)

```python
def embed_query(self, query: str) -> List[float]:
    response = self.client.models.embed_content(
        model="gemini-embedding-2-preview",
        contents=query,
        config=types.EmbedContentConfig(
            output_dimensionality=2048,  # must match collection config
            task_type="RETRIEVAL_QUERY"  # tells model this is a search query
        ),
    )
    return response.embeddings[0].values
```

**Why `task_type="RETRIEVAL_QUERY"`?**
Gemini Embeddings 2 is a bi-encoder model optimized for asymmetric retrieval. Chunks are indexed with `RETRIEVAL_DOCUMENT` task type (implicit during ingestion). Queries use `RETRIEVAL_QUERY`. This asymmetry improves retrieval accuracy vs. using the same task type for both.

---

## Data Flow: End-to-End Retrieval

```
User: "What are the applications of dynamic programming in CS?"
         │
         ▼
POST /api/v1/retrieve/
HumanMessage("What are the applications...")
         │
         ▼
agent_node:
  LLM decides to call search_documents(
    query="dynamic programming applications",
    k=7,
    subject="Computer Science"
  )
         │
         ▼
search_documents tool:
  embed_query("dynamic programming applications")
  → [0.023, -0.11, ..., 0.084]  (2048 floats)
         │
         ▼
vector_store.search():
  Prefetch: dense(query_vector, k=7) + sparse(BM25("dynamic programming applications"), k=7)
  Fusion: RRF → top 7 points
  Filter: subject = "Computer Science"
         │
         ▼
Formatted result string:
  --- Document 1 ---
  Source: CS101 / Lecture_08_DP.pdf (Page 2)
  ...
         │
         ▼
agent_node:
  Evaluates results → sufficient
  Formulates answer grounded in docs
         │
         ▼
{ "answer": "Dynamic programming is widely used in optimization problems such as..." }
```

---

## What's Planned (Not Yet Built)

### Reranking (`.prompts/8-rerank.md`)
After Qdrant returns top-k results, a cross-encoder reranker would reorder them by true relevance. Currently results go directly to the agent without reranking.

**Planned location:** `app/services/retrieval/reranker.py`

### course_code / year Filters
The Qdrant payload has `course_code` and `year` fields populated during ingestion, but the `search_documents` tool doesn't expose them as parameters yet. Adding them would allow queries like "only search in CS101 2024 materials."

### Conversational Memory
Currently the retrieval graph resets state per request (no persistent thread/session). Future: add thread_id-scoped checkpointing via LangGraph's built-in checkpointer.

---

## Testing the Retrieval Module

```bash
# Quick API test (assumes server is running)
curl -X POST http://localhost:8000/api/v1/retrieve/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Big-O notation?"}'

# Check via Swagger UI
open http://localhost:8000/docs#/Retrieval/retrieve_answer_api_v1_retrieve__post
```

**What to verify:**
1. `search_documents` is actually being called (check logs for `Tool search_documents called with...`)
2. The answer references source documents, not hallucinated content
3. For unknown topics → response is `"Insufficient info"` (exact string)
4. The graph terminates within `recursion_limit=10`

---

## Common Issues & Debugging

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Error: Failed to generate embeddings` | Invalid/missing `GEMINI_API_KEY` | Check `.env` |
| `Failed to perform search` | Qdrant unreachable or wrong URL | Check `QDRANT_URL` + Qdrant status |
| Agent loops 10 times and crashes | LLM keeps calling tool but docs are empty | Ingest content first |
| Always returns `"Insufficient info"` | Collection empty or wrong `QDRANT_COLLECTION_NAME` | Run `setup_qdrant.py` and ingest |
| Filters return no results | LLM is setting wrong filter values | Try removing filters in direct tool call |
| `recursion_limit` hit | Agent loop not terminating | Check system prompt, verify tool return format |
