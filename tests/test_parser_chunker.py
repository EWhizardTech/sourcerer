# tests/test_parser_chunker.py

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.services.chunking.chunker import chunk_document
from app.services.parsing.factory import ParserFactory

SAMPLES_DIR = Path(__file__).parent / "samples"
RESULTS_DIR = Path(__file__).parent / "results"


def load_file_bytes(file_path: Path) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def write_parsed_and_chunks(file_name: str, parsed: dict, chunks: list[dict]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = Path(file_name).suffix.lstrip(".") or "file"
    out_file = RESULTS_DIR / f"{Path(file_name).stem}_{suffix}_{timestamp}.txt"

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"file_name: {file_name}\n")
        f.write(f"generated_at: {timestamp}\n\n")
        f.write("=== PARSED OUTPUT ===\n")
        f.write(json.dumps(parsed, indent=2, ensure_ascii=True))
        f.write("\n\n=== CHUNKS ===\n")
        f.write(json.dumps(chunks, indent=2, ensure_ascii=True))
        f.write("\n")

    return out_file


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
    out_file = write_parsed_and_chunks(file_path.name, parsed, chunks)

    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]
    assert "text" in chunks[0]
    assert out_file.exists()


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
    out_file = write_parsed_and_chunks(file_path.name, parsed, chunks)

    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]

    # Ensure sections influence chunking
    assert len(chunks) >= len(parsed["sections"])
    assert out_file.exists()


@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "pdfs").glob("*.pdf")))
def test_pdf_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser("application/pdf")

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["text"].strip() != ""
    assert isinstance(parsed["sections"], list)

    chunks = chunk_document(parsed, {}, file_path.stem)

    out_file = write_parsed_and_chunks(file_path.name, parsed, chunks)

    assert len(chunks) > 0
    assert out_file.exists()


# {
#   "folder_id": "1_3t3KGlDTwQypF8LO-mHKVv5n2bp3ZRg",
#   "course_code": "TEST101",
#   "year": "2026",
#   "include_root_as_tag": true
# }
