"""Root entrypoint — delegates to the FastAPI app in app/main.py."""

import uvicorn

if __name__ == "__main__":
    # Run with: uv run python main.py
    # Or directly: uv run uvicorn app.main:app --reload
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
