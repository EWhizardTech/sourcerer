You are helping me build a production-grade backend for an AI-powered RAG system called "Sourcerer".

Tech stack:
- Python + FastAPI
- Qdrant (vector DB)
- Gemini Embeddings (Vertex AI)
- Google Drive API (for ingestion)
- Optional: LangChain / LangGraph (only if needed, avoid overuse)
- LLM from ....

Architecture stages:
1. Ingestion (Google Drive)
2. Incremental Check   
   - NEW → continue
   - SKIP → stop
   - UPDATE → delete + continue
3. Metadata extraction
4. Parsing (+ transcripts)
5. Chunking (deterministic IDs)
6. Tagging
7. Embedding
8. Qdrant storage (with file_id)
9. Retrieval
2. Metadata extraction (folder-based)
3. Parsing (+ YouTube transcript extraction)
4. Chunking
5. Tagging (LLM + metadata merge)
6. Embedding
7. Vector storage (Qdrant)
8. Retrieval

Constraints:
- Keep code modular and production-ready
- Use uv for package management
- Use google coding convention
- Use clear folder structure
- Avoid overengineering
- Add comments explaining key decisions
- Each feature must be independently testable
- Prefer simple working version first, then improve
- Ensure tracking store updated ONLY after successful pipeline completion
- Log each stage

Important:
- Always include:
  - folder structure
  - minimal working code
  - how to test the feature

