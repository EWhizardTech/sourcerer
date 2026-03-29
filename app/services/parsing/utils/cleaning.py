# app/services/parsing/utils/cleaning.py


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [line.strip() for line in text.split("\n")]

    # remove excessive empty lines
    cleaned = []
    prev_empty = False

    for line in lines:
        if not line:
            if not prev_empty:
                cleaned.append("")
            prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False

    return "\n".join(cleaned).strip()


def split_paragraphs(text: str):
    return [
        {"type": "paragraph", "content": p.strip()}
        for p in text.split("\n\n")
        if p.strip()
    ]
