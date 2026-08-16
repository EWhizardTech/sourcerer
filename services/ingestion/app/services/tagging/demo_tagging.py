# app/services/tagging/demo_tagging.py

import json
from unittest.mock import MagicMock

from sourcerer_core.chunking_types import ImageChunk, TextChunk
from app.services.tagging.tagging_service import tag_chunk


def run_demo():
    # 1. Document Chunk
    doc_chunk: TextChunk = {
        "chunk_id": "file_123_text_0",
        "text": "The Quick Sort algorithm is a divide-and-conquer method for sorting arrays. It works by selecting a 'pivot' element and partitioning the other elements into two sub-arrays.",
        "metadata": {
            "file_id": "file_123",
            "content_type": "text",
            "source": "document",
            "course_code": "CS101",
            "year": "2024",
        },
    }

    # 2. Transcript Chunk
    transcript_chunk: TextChunk = {
        "chunk_id": "yt_abc_text_5",
        "text": "So today we're talking about photosynthesis. Specifically the light-dependent reactions where chlorophyll absorbs energy from sunlight.",
        "metadata": {
            "file_id": "yt_abc",
            "content_type": "text",
            "source": "transcript",
            "course_code": "BIO202",
            "year": "2023",
        },
    }

    # 3. Image Chunk
    image_chunk: ImageChunk = {
        "chunk_id": "file_123_image_2",
        "image": {"image_id": "img_456", "image_bytes": "base64_data_here"},
        "metadata": {
            "file_id": "file_123",
            "content_type": "image",
            "source": "document",
            "page_number": 3,
            "course_code": "CS101",
            "year": "2024",
        },
    }

    print("--- DOCUMENT CHUNK TAGGING ---")
    tagged_doc = tag_chunk(doc_chunk)
    print(json.dumps(tagged_doc, indent=2))

    print("\n--- TRANSCRIPT CHUNK TAGGING ---")
    tagged_transcript = tag_chunk(transcript_chunk)
    print(json.dumps(tagged_transcript, indent=2))

    print("\n--- IMAGE CHUNK TAGGING ---")
    tagged_image = tag_chunk(image_chunk)
    print(json.dumps(tagged_image, indent=2))


if __name__ == "__main__":
    # Mocking the client inside tagging_service for demo purposes if no API key
    from unittest.mock import patch

    import app.services.tagging.tagging_service as ts

    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps(
        {
            "subject": "Computer Science",
            "topic": "Sorting Algorithms",
            "keywords": ["Quick Sort", "Divide and Conquer", "Algorithms"],
            "difficulty": "Medium",
        }
    )

    mock_resp_bio = MagicMock()
    mock_resp_bio.choices[0].message.content = json.dumps(
        {
            "subject": "Biology",
            "topic": "Photosynthesis",
            "keywords": ["Chlorophyll", "Light Reactions", "Energy"],
            "difficulty": "Medium",
        }
    )

    with patch(
        "app.services.tagging.tagging_service.client.chat.completions.create"
    ) as mocked_create:
        mocked_create.side_effect = [mock_resp, mock_resp_bio]
        run_demo()
