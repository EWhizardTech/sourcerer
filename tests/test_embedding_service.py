# tests/test_embedding_service.py

import base64
from unittest.mock import MagicMock, patch
import pytest
from google.genai import types
from app.services.embedding.embedding_service import EmbeddingService

@pytest.fixture
def mock_genai_client():
    with patch("google.genai.Client") as mock_client:
        yield mock_client

def test_embed_text_chunks_combined(mock_genai_client):
    # Setup
    service = EmbeddingService()
    mock_response = MagicMock()
    # Mocking single embedding response for each call
    mock_response.embeddings = [MagicMock(values=[0.1]*3072)]
    service.client.models.embed_content.return_value = mock_response

    chunks = [
        {
            "chunk_id": "txt1",
            "text": "Hello world",
            "image": None,
            "metadata": {},
            "tags": {"subject": "Math", "topic": "Algebra"}
        }
    ]

    # Execute
    results = service.embed_chunks(chunks)

    # Verify
    assert len(results) == 1
    assert len(results[0]["dense_vector"]) == 3072
    # Check if tags were prepended
    args, kwargs = service.client.models.embed_content.call_args
    content_parts = kwargs["contents"]
    assert "Subject: Math | Topic: Algebra" in content_parts[0]
    assert "Hello world" in content_parts[0]

def test_embed_image_chunks_combined(mock_genai_client):
    # Setup
    service = EmbeddingService()
    mock_response = MagicMock()
    mock_response.embeddings = [MagicMock(values=[0.9]*3072)]
    service.client.models.embed_content.return_value = mock_response

    # Base64 encoded dummy image
    img_bytes = base64.b64encode(b"fake_image_data").decode("utf-8")
    chunks = [
        {
            "chunk_id": "img1",
            "text": "",
            "image": {
                "image_bytes": img_bytes
            },
            "metadata": {},
            "tags": {"subject": "Physics", "keywords": ["Newton"]}
        }
    ]

    # Execute
    results = service.embed_chunks(chunks)

    # Verify
    assert len(results) == 1
    assert len(results[0]["dense_vector"]) == 3072
    # Check parts
    args, kwargs = service.client.models.embed_content.call_args
    content_parts = kwargs["contents"]
    # Part 0 should be description because text is empty
    assert "Subject: Physics | Keywords: Newton" in content_parts[0]
    # Part 1 should be the image part
    assert any(isinstance(p, types.Part) for p in content_parts)

def test_embed_no_content_skips(mock_genai_client):
    service = EmbeddingService()
    chunks = [
        {"chunk_id": "empty", "text": "", "image": None, "tags": {}}
    ]
    results = service.embed_chunks(chunks)
    assert len(results) == 0
