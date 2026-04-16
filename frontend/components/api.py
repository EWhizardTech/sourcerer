import requests
import streamlit as st

# Default to 8000, assuming backend runs locally on port 8000
BACKEND_URL = "http://localhost:8000"


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
