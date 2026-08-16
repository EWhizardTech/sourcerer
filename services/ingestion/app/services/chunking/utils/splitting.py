# app/services/chunking/utils/splitting.py


def split_words(text: str, chunk_size: int, overlap: int):
    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap

    return chunks
