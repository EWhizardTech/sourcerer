# Retrieval Service

`services/retrieval` — agentic RAG chat. See [RAG Pipeline](../rag-pipeline.md) for the full flow.

## Endpoints

### `POST /api/v1/chat/stream` — SSE streaming chat

```json
{ "query": "What is an inverted index?", "session_id": null }
```

Streams `session` → `sources` → `token`* → `done` events. Pass the returned `session_id` on the next request for conversational follow-ups.

### `POST /api/v1/chat` — blocking chat

Same request; returns `{answer, sources, session_id, condensed_query}` in one response.

### `DELETE /api/v1/chat/{session_id}`

Clears a session's memory.

### `POST /api/v1/retrieve/` — legacy stateless retrieval

Returns `{answer, sources}` without memory.

## Source objects

```json
{
  "id": 1,
  "chunk_id": "6f6c…",
  "text": "…retrieved chunk…",
  "source": "lecture-3.pdf",
  "page_number": 12,
  "score": 4.21,
  "subject": "Information Retrieval",
  "type": "document"
}
```

`score` is the cross-encoder rerank score when reranking is enabled, otherwise the RRF fusion score. Web results (`type: "web"`) carry a `url`.

## Key modules

| Module | Role |
|---|---|
| `app/rag/graph.py` | LangGraph agent (model from `GROQ_MODEL`), grounded citation prompt, web-signal tool gating |
| `app/rag/tools.py` | `search_documents` / `search_web` as `content_and_artifact` tools |
| `app/rag/flow.py` | Orchestration: memory load, query condensation, sync + streaming runners |
| `app/rag/memory.py` | Redis session history (TTL + cap) |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Answering agent model |
| `GROQ_FAST_MODEL` | `llama-3.1-8b-instant` | Query condensation |
| `RERANK_ENABLED` | `true` | Cross-encoder reranking |
| `RERANK_MODEL` | `Xenova/ms-marco-MiniLM-L-6-v2` | fastembed cross-encoder |
| `RERANK_OVERFETCH` | `3` | Candidate multiplier before rerank |
| `REDIS_URL` | `redis://localhost:6380/2` | Chat memory store |
| `CHAT_HISTORY_TTL_SECONDS` | `86400` | Session lifetime |
| `CHAT_HISTORY_MAX_MESSAGES` | `20` | History cap per session |
