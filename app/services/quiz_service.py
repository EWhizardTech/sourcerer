"""Question and MCQ generation service.

Builds MCQs from retrieved chunks using:
- T5 summarization model (t5-base)
- T5 question generation model (ramsrigouthamg/t5_squad_v1)
- WordNet distractor generation
"""

import logging
import random
from collections import OrderedDict
from typing import Any

import nltk
from nltk.corpus import wordnet

try:
    import torch
    from transformers import T5ForConditionalGeneration, T5Tokenizer
except ImportError as exc:
    _TRANSFORMERS_IMPORT_ERROR: ImportError | None = ImportError(
        "transformers stack is required for quiz generation. "
        "Install with: pip install transformers>=4.30 sentencepiece nltk"
    )
    _TRANSFORMERS_IMPORT_ERROR.__cause__ = exc
    torch = None
    T5ForConditionalGeneration = None
    T5Tokenizer = None
else:
    _TRANSFORMERS_IMPORT_ERROR = None

logger = logging.getLogger(__name__)

nltk.download("wordnet", quiet=True)
nltk.download("stopwords", quiet=True)

_DEVICE = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"

_SUMMARIZER_TOKENIZER: T5Tokenizer | None = None
_SUMMARIZER_MODEL: T5ForConditionalGeneration | None = None
_QG_TOKENIZER: T5Tokenizer | None = None
_QG_MODEL: T5ForConditionalGeneration | None = None


def _ensure_models_loaded() -> None:
    """Lazily initialize model/tokenizer pairs exactly once."""
    global _SUMMARIZER_TOKENIZER
    global _SUMMARIZER_MODEL
    global _QG_TOKENIZER
    global _QG_MODEL

    if _TRANSFORMERS_IMPORT_ERROR is not None:
        raise _TRANSFORMERS_IMPORT_ERROR

    if _SUMMARIZER_TOKENIZER is None or _SUMMARIZER_MODEL is None:
        _SUMMARIZER_TOKENIZER = T5Tokenizer.from_pretrained("t5-base")
        _SUMMARIZER_MODEL = T5ForConditionalGeneration.from_pretrained("t5-base")
        _SUMMARIZER_MODEL = _SUMMARIZER_MODEL.to(_DEVICE)

    if _QG_TOKENIZER is None or _QG_MODEL is None:
        _QG_TOKENIZER = T5Tokenizer.from_pretrained("ramsrigouthamg/t5_squad_v1")
        _QG_MODEL = T5ForConditionalGeneration.from_pretrained(
            "ramsrigouthamg/t5_squad_v1"
        )
        _QG_MODEL = _QG_MODEL.to(_DEVICE)


def summarize(text: str) -> str:
    """Generate a summary for the input text."""
    if not text.strip():
        return ""

    _ensure_models_loaded()
    assert _SUMMARIZER_TOKENIZER is not None
    assert _SUMMARIZER_MODEL is not None

    model_input = f"summarize: {text}"
    input_ids = _SUMMARIZER_TOKENIZER.encode(model_input, return_tensors="pt").to(
        _DEVICE
    )
    summary_ids = _SUMMARIZER_MODEL.generate(
        input_ids,
        max_length=200,
        min_length=50,
        num_beams=4,
    )
    return _SUMMARIZER_TOKENIZER.decode(summary_ids[0], skip_special_tokens=True)


def get_keywords(chunk: dict[str, Any]) -> list[str]:
    """Read keyword tags already produced by the tagging service."""
    tags = chunk.get("tags", {})
    keywords = tags.get("keywords", []) if isinstance(tags, dict) else []
    if not isinstance(keywords, list):
        return []
    return [str(keyword) for keyword in keywords if str(keyword).strip()]


def generate_question(answer: str, context: str) -> str:
    """Generate a question from an answer and context."""
    _ensure_models_loaded()
    assert _QG_TOKENIZER is not None
    assert _QG_MODEL is not None

    prompt = f"answer: {answer} context: {context}"
    input_ids = _QG_TOKENIZER.encode(prompt, return_tensors="pt").to(_DEVICE)
    question_ids = _QG_MODEL.generate(
        input_ids,
        max_length=64,
        num_beams=4,
    )
    question = _QG_TOKENIZER.decode(question_ids[0], skip_special_tokens=True)
    if question.lower().startswith("question:"):
        question = question[len("question:") :].strip()
    return question


def get_distractors(word: str, n: int = 3) -> list[str]:
    """Generate distractors via WordNet hypernym -> hyponym traversal."""
    normalized_word = word.strip().lower().replace(" ", "_")
    if not normalized_word:
        return [""] * n

    distractors: OrderedDict[str, None] = OrderedDict()

    for synset in wordnet.synsets(normalized_word):
        for hypernym in synset.hypernyms():
            for hyponym in hypernym.hyponyms():
                for lemma in hyponym.lemma_names():
                    candidate = lemma.replace("_", " ").strip()
                    if not candidate:
                        continue
                    if candidate.lower() == word.strip().lower():
                        continue
                    if candidate.lower() in distractors:
                        continue
                    distractors[candidate.lower()] = candidate

    results = list(distractors.values())[:n]
    if len(results) < n:
        results.extend([""] * (n - len(results)))
    return results


def build_mcqs(chunks: list[dict[str, Any]], num_questions: int = 5) -> list[dict[str, Any]]:
    """Build MCQs from retrieved chunks and existing keyword tags."""
    if num_questions <= 0:
        return []

    texts = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]
    context_text = " ".join(texts)
    summary = summarize(context_text) if context_text else ""

    all_keywords: list[str] = []
    for chunk in chunks:
        all_keywords.extend(get_keywords(chunk))

    deduped_keywords = list(OrderedDict((kw.lower(), kw) for kw in all_keywords).values())
    selected_keywords = deduped_keywords[:num_questions]

    mcqs: list[dict[str, Any]] = []
    for keyword in selected_keywords:
        question = generate_question(keyword, summary)
        distractors = get_distractors(keyword, n=3)

        options = [keyword] + distractors
        random.shuffle(options)

        difficulty = "medium"
        source_chunk_ids: list[str] = []
        for chunk in chunks:
            chunk_tags = chunk.get("tags", {})
            chunk_keywords = chunk_tags.get("keywords", []) if isinstance(chunk_tags, dict) else []
            normalized_chunk_keywords = {str(item).lower() for item in chunk_keywords}

            if keyword.lower() in normalized_chunk_keywords:
                chunk_id = str(chunk.get("chunk_id", ""))
                if chunk_id:
                    source_chunk_ids.append(chunk_id)
                if difficulty == "medium":
                    tag_difficulty = chunk_tags.get("difficulty", "")
                    if isinstance(tag_difficulty, str) and tag_difficulty.strip():
                        difficulty = tag_difficulty

        mcqs.append(
            {
                "question": question,
                "answer": keyword,
                "options": options,
                "difficulty": difficulty,
                "source_chunk_ids": source_chunk_ids,
            }
        )

    logger.info("Generated %d MCQs from %d chunks", len(mcqs), len(chunks))
    return mcqs
