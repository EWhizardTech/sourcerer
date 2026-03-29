# tests/test_parser_chunker.py

from pathlib import Path

from app.services.parsing.factory import ParserFactory
from app.services.chunking.chunker import chunk_document


SAMPLES_DIR = Path(__file__).parent / "samples"


def load_file_bytes(file_path: Path) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def test_txt_parser_and_chunker():
    file_path = SAMPLES_DIR / "sample.txt"

    content = load_file_bytes(file_path)

    parser = ParserFactory.get_parser("text/plain")
    parsed = parser.parse(content, file_path.name)

    # Parser assertions
    assert parsed["text"] != ""
    assert isinstance(parsed["sections"], list)

    # Chunking
    chunks = chunk_document(parsed, {}, "txt_file")

    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]
    assert "text" in chunks[0]


def test_md_parser_and_chunker():
    file_path = SAMPLES_DIR / "sample.md"

    content = load_file_bytes(file_path)

    parser = ParserFactory.get_parser("text/markdown")
    parsed = parser.parse(content, file_path.name)

    # Parser assertions
    assert parsed["text"] != ""
    assert len(parsed["sections"]) > 0
    assert "obsidian_links" in parsed["metadata"]

    # Chunking (should auto-use section chunker)
    chunks = chunk_document(parsed, {}, "md_file")

    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]

    # Ensure sections influence chunking
    assert len(chunks) >= len(parsed["sections"])