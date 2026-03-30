# tests/test_parser_chunker.py

import json
from collections import Counter
from pathlib import Path

import pytest

from app.services.chunking.chunker import chunk_document
from app.services.parsing.factory import ParserFactory

SAMPLES_DIR = Path(__file__).parent / "samples"
RESULTS_FILE = Path(__file__).parent / "results" / "results.txt"


# -------------------------------
# Setup: clear results file once
# -------------------------------
@pytest.fixture(scope="session", autouse=True)
def clear_results_file():
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write("==== TEST RESULTS ====\n\n")


def load_file_bytes(file_path: Path) -> bytes:
    with open(file_path, "rb") as f:
        return f.read()


def append_results(test_name: str, file_name: str, parsed: dict, chunks: list[dict]):
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"TEST: {test_name}\n")
        f.write(f"FILE: {file_name}\n")
        f.write(f"{'-'*60}\n")

        # summary
        f.write(f"Total chunks: {len(chunks)}\n\n")

        # parsed counts
        parsed_counts = {
            "sections": len(parsed.get("sections", [])),
            "tables": len(parsed.get("tables", [])),
            "images": len(parsed.get("images", [])),
            "lists": len(parsed.get("lists", [])),
        }

        f.write("Parsed Items:\n")
        for k, v in parsed_counts.items():
            f.write(f"  {k}: {v}\n")

        # chunk distribution
        chunk_types = Counter(c["metadata"]["content_type"] for c in chunks)

        f.write("\nChunk Types:\n")
        for k, v in chunk_types.items():
            f.write(f"  {k}: {v}\n")

        # optional: dump full data (can comment if too big)
        f.write("\n--- PARSED ---\n")
        f.write(json.dumps(parsed, indent=2, ensure_ascii=True))

        f.write("\n\n--- CHUNKS ---\n")
        f.write(json.dumps(chunks, indent=2, ensure_ascii=True))
        f.write("\n")


# -------------------------------
# TXT
# -------------------------------
@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "txts").glob("*.txt")))
def test_txt_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser("text/plain")

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["text"] != ""
    assert isinstance(parsed["sections"], list)

    chunks = chunk_document(parsed, {}, file_path.stem)

    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]

    append_results("test_txt_parser_and_chunker", file_path.name, parsed, chunks)


# -------------------------------
# MD
# -------------------------------
@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "mds").glob("*.md")))
def test_md_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser("text/markdown")

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["text"] != ""
    assert len(parsed["sections"]) > 0

    chunks = chunk_document(parsed, {}, file_path.stem)

    assert len(chunks) > 0

    append_results("test_md_parser_and_chunker", file_path.name, parsed, chunks)


# -------------------------------
# PDF
# -------------------------------
@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "pdfs").glob("*.pdf")))
def test_pdf_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser("application/pdf")

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["text"].strip() != ""

    chunks = chunk_document(parsed, {}, file_path.stem)

    assert len(chunks) > 0

    append_results("test_pdf_parser_and_chunker", file_path.name, parsed, chunks)


# -------------------------------
# PPT
# -------------------------------
@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "ppts").glob("*.pptx")))
def test_ppt_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["metadata"]["parser"] == "ppt"

    chunks = chunk_document(parsed, {}, file_path.stem)

    assert len(chunks) > 0

    append_results("test_ppt_parser_and_chunker", file_path.name, parsed, chunks)


# -------------------------------
# DOCX
# -------------------------------
@pytest.mark.parametrize("file_path", list((SAMPLES_DIR / "docx").glob("*.docx")))
def test_docx_parser_and_chunker(file_path: Path):
    parser = ParserFactory.get_parser(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    content = load_file_bytes(file_path)
    parsed = parser.parse(content, file_path.name)

    assert parsed["metadata"]["parser"] == "docx"

    chunks = chunk_document(parsed, {}, file_path.stem)

    assert len(chunks) > 0

    append_results("test_docx_parser_and_chunker", file_path.name, parsed, chunks)

# {
#   "folder_id": "1_3t3KGlDTwQypF8LO-mHKVv5n2bp3ZRg",
#   "course_code": "TEST101",
#   "year": "2026",
#   "include_root_as_tag": true
# }
# 1rBUfr0TNWevkIoYhJ1k9lcoJb9xTXzTD
