# scripts/test_pipeline.py

import os
import sys
import json
import logging

# Ensure the root directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.parsing.factory import ParserFactory
from app.services.chunking.chunker import chunk_document
from app.services.tagging.tagging_service import tag_chunks

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_full_pipeline(file_path: str):
    """Runs the pipeline synchronously for a local file: Parse -> Chunk -> Tag."""
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    file_name = os.path.basename(file_path)
    # Simple mime detection for testing
    if file_path.endswith('.pdf'):
        mime_type = 'application/pdf'
    elif file_path.endswith('.txt'):
        mime_type = 'text/plain'
    elif file_path.endswith('.docx'):
        mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        mime_type = 'text/plain'
    
    print(f"\n--- [1] PARSING: {file_name} ---")
    with open(file_path, 'rb') as f:
        content = f.read()
    
    parser = ParserFactory.get_parser(mime_type)
    parsed_doc = parser.parse(content, file_name)
    print(f"Parsed metadata: {json.dumps(parsed_doc.get('metadata'), indent=2)}")

    print(f"\n--- [2] CHUNKING ---")
    mock_metadata = {
        "course_code": "TEST101",
        "year": "2024",
        "source": "document"
    }
    chunks = chunk_document(parsed_doc, mock_metadata, "test_file_id")
    print(f"Generated {len(chunks)} chunks.")

    print(f"\n--- [3] TAGGING ---")
    tagged_chunks = tag_chunks(chunks)
    
    # Show results for the first few chunks
    for i, chunk in enumerate(tagged_chunks[:3]):
        print(f"\nChunk {i+1} Result:")
        print(json.dumps(chunk, indent=2))
    
    if len(tagged_chunks) > 3:
        print(f"\n... and {len(tagged_chunks)-3} more chunks.")

    print(f"\nPipeline test complete for {file_name}.")

if __name__ == "__main__":
    # You can pass a file path as an argument or let it use the sample
    sample_file = "tests/samples/txts/sample.txt"
    if len(sys.argv) > 1:
        sample_file = sys.argv[1]
    
    test_full_pipeline(sample_file)
