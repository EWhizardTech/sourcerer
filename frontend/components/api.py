import os

import requests
import streamlit as st

# Default to 8000 (local uvicorn); the dockerized API is published on 8001.
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def get_health() -> bool:
    """Check if backend is healthy."""
    try:
        response = requests.get(f"{BACKEND_URL}/health")
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def ingest_gdrive(
    folder_id: str,
    course_code: str = None,
    year: str = None,
    include_root: bool = False,
):
    """Call Google Drive ingestion endpoint."""
    url = f"{BACKEND_URL}/api/v1/ingest/gdrive"
    payload = {
        "folder_id": folder_id,
        "course_code": course_code,
        "year": year,
        "include_root_as_tag": include_root,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling backend: {e}")
        return None

def retrieve_answer(query: str):
    """Call the retrieval endpoint."""
    url = f"{BACKEND_URL}/api/v1/retrieve/"
    payload = {"query": query}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling backend: {e}")
        return None


def generate_quiz(
    query: str,
    course_code: str | None = None,
    year: str | None = None,
    tags: list[str] | None = None,
    num_questions: int = 5,
    allow_unfiltered_fallback: bool = True,
):
    """Call the quiz generation endpoint."""
    url = f"{BACKEND_URL}/api/v1/quiz/generate"
    payload = {
        "query": query,
        "filters": {
            "course_code": course_code,
            "year": year,
            "tags": tags,
        },
        "num_questions": num_questions,
        "allow_unfiltered_fallback": allow_unfiltered_fallback,
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        detail = None
        if e.response is not None:
            try:
                detail = e.response.json().get("detail")
            except ValueError:
                detail = e.response.text
        if detail:
            st.error(f"Error calling backend: {detail}")
        else:
            st.error(f"Error calling backend: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling backend: {e}")
        return None
