"""Enhanced question and MCQ generation service.

Builds MCQs from retrieved chunks using:
- T5 question generation model (ramsrigouthamg/t5_squad_v1)
- Advanced distractor generation (WordNet + corpus-based + NER)
- Question quality filtering and deduplication
- NLP-based answer extraction and validation
"""

import logging
import importlib
import os
import random
import re
import subprocess
import sys
from collections import Counter, OrderedDict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import nltk
from nltk.corpus import stopwords, wordnet
from nltk.tokenize import sent_tokenize, word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import settings


try:
    import spacy
except ImportError as exc:
    _SPACY_IMPORT_ERROR: ImportError | None = ImportError(
        "spaCy is required for enhanced quiz generation. "
        "Install with: pip install spacy && python -m spacy download en_core_web_sm"
    )
    _SPACY_IMPORT_ERROR.__cause__ = exc
    spacy = None
else:
    _SPACY_IMPORT_ERROR = None

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

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_setting_path(raw_value: str) -> str:
    """Resolve config path; relative values are anchored to project root."""
    candidate = Path(raw_value)
    if not candidate.is_absolute():
        candidate = _PROJECT_ROOT / candidate
    return str(candidate.resolve())


_ML_CACHE_DIR = _resolve_setting_path(settings.ML_CACHE_DIR)
_HF_HOME = _resolve_setting_path(settings.HF_HOME)
_HF_HUB_CACHE = _resolve_setting_path(settings.HUGGINGFACE_HUB_CACHE)
_TRANSFORMERS_CACHE = _resolve_setting_path(settings.TRANSFORMERS_CACHE)
_TORCH_HOME = _resolve_setting_path(settings.TORCH_HOME)
_NLTK_DATA_DIR = _resolve_setting_path(settings.NLTK_DATA_DIR)
_SPACY_MODEL_DIR = _resolve_setting_path(settings.SPACY_MODEL_DIR)
_SPACY_MODEL_NAME = settings.SPACY_MODEL_NAME

for path_str in [
    _ML_CACHE_DIR,
    _HF_HOME,
    _HF_HUB_CACHE,
    _TRANSFORMERS_CACHE,
    _TORCH_HOME,
    _NLTK_DATA_DIR,
    _SPACY_MODEL_DIR,
]:
    Path(path_str).mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = _HF_HOME
os.environ["HUGGINGFACE_HUB_CACHE"] = _HF_HUB_CACHE
os.environ["TRANSFORMERS_CACHE"] = _TRANSFORMERS_CACHE
os.environ["TORCH_HOME"] = _TORCH_HOME
os.environ["NLTK_DATA"] = _NLTK_DATA_DIR
if settings.HF_TOKEN:
    os.environ["HF_TOKEN"] = settings.HF_TOKEN

# Restrict NLTK lookup and downloads to the configured project-local path only.
nltk.data.path = [_NLTK_DATA_DIR]

_DEVICE = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
_STOP_WORDS: set[str] | None = None

# Global model instances
_QG_TOKENIZER: Any = None
_QG_MODEL: Any = None
_NLP_MODEL: Any = None
_NLTK_READY = False


def _ensure_nltk_data() -> None:
    """Download required NLTK artifacts into the configured local directory."""
    global _NLTK_READY
    if _NLTK_READY:
        return

    resources = [
        "wordnet",
        "stopwords",
        "punkt",
        "punkt_tab",
        "averaged_perceptron_tagger",
    ]
    for resource in resources:
        nltk.download(resource, quiet=True, download_dir=_NLTK_DATA_DIR)

    _NLTK_READY = True


def _get_stop_words() -> set[str]:
    """Lazily load stopwords after NLTK resources are available."""
    global _STOP_WORDS
    if _STOP_WORDS is None:
        _ensure_nltk_data()
        _STOP_WORDS = set(stopwords.words("english"))
    return _STOP_WORDS


def _ensure_spacy_model_local() -> None:
    """Ensure spaCy model package exists inside the configured local directory."""
    spacy_target = Path(_SPACY_MODEL_DIR)
    if str(spacy_target) not in sys.path:
        sys.path.insert(0, str(spacy_target))

    if spacy is None:
        return

    local_package = spacy_target / _SPACY_MODEL_NAME
    if local_package.exists():
        return

    logger.info(
        "spaCy model %s not found in %s; downloading locally",
        _SPACY_MODEL_NAME,
        _SPACY_MODEL_DIR,
    )

    command = [
        sys.executable,
        "-m",
        "spacy",
        "download",
        _SPACY_MODEL_NAME,
        "--target",
        _SPACY_MODEL_DIR,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else str(exc)
        raise RuntimeError(
            f"Failed to install spaCy model {_SPACY_MODEL_NAME} into {_SPACY_MODEL_DIR}: {stderr}"
        ) from exc


def _load_spacy_model_from_local() -> Any:
    """Load spaCy model strictly from configured local model directory."""
    _ensure_spacy_model_local()
    try:
        model_pkg = importlib.import_module(_SPACY_MODEL_NAME)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"spaCy model package {_SPACY_MODEL_NAME} was not found in {_SPACY_MODEL_DIR}"
        ) from exc

    return model_pkg.load()


def _ensure_models_loaded() -> None:
    """Lazily initialize models exactly once."""
    global _QG_TOKENIZER, _QG_MODEL, _NLP_MODEL

    if _TRANSFORMERS_IMPORT_ERROR is not None:
        raise _TRANSFORMERS_IMPORT_ERROR

    if _SPACY_IMPORT_ERROR is not None:
        raise _SPACY_IMPORT_ERROR

    _ensure_nltk_data()

    if _QG_TOKENIZER is None or _QG_MODEL is None:
        model_id = "ramsrigouthamg/t5_squad_v1"
        try:
            _QG_TOKENIZER = T5Tokenizer.from_pretrained(
                model_id,
                cache_dir=_TRANSFORMERS_CACHE,
                local_files_only=True,
            )
            _QG_MODEL = T5ForConditionalGeneration.from_pretrained(
                model_id,
                cache_dir=_TRANSFORMERS_CACHE,
                local_files_only=True,
            )
        except OSError:
            logger.info(
                "T5 model not found in local cache; downloading into %s",
                _TRANSFORMERS_CACHE,
            )
            _QG_TOKENIZER = T5Tokenizer.from_pretrained(
                model_id,
                cache_dir=_TRANSFORMERS_CACHE,
            )
            _QG_MODEL = T5ForConditionalGeneration.from_pretrained(
                model_id,
                cache_dir=_TRANSFORMERS_CACHE,
            )
        _QG_MODEL = _QG_MODEL.to(_DEVICE)

    if _NLP_MODEL is None:
        _NLP_MODEL = _load_spacy_model_from_local()


def extract_named_entities(text: str) -> list[tuple[str, str]]:
    """Extract named entities with their types using spaCy."""
    _ensure_models_loaded()
    doc = _NLP_MODEL(text)
    return [(ent.text, ent.label_) for ent in doc.ents]


def extract_noun_phrases(text: str) -> list[str]:
    """Extract noun chunks using spaCy."""
    _ensure_models_loaded()
    doc = _NLP_MODEL(text)
    return [chunk.text for chunk in doc.noun_chunks]


def calculate_tfidf_scores(texts: list[str]) -> dict[str, float]:
    """Calculate TF-IDF scores for terms across all chunks."""
    if not texts:
        return {}
    
    try:
        vectorizer = TfidfVectorizer(
            max_features=100,
            stop_words="english",
            ngram_range=(1, 2)
        )
        vectorizer.fit(texts)
        
        # Get average TF-IDF scores
        tfidf_matrix = vectorizer.transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        scores = {}
        
        for idx, term in enumerate(feature_names):
            scores[term] = float(tfidf_matrix[:, idx].mean())
        
        return scores
    except Exception as e:
        logger.warning("TF-IDF calculation failed: %s", e)
        return {}


def get_enhanced_keywords(
    chunks: list[dict[str, Any]], top_n: int = 20
) -> list[tuple[str, float]]:
    """Extract and rank keywords using multiple NLP strategies."""
    stop_words = _get_stop_words()
    all_keywords: dict[str, float] = {}
    texts = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]
    
    if not texts:
        return []
    
    # Strategy 1: Use existing tagged keywords
    for chunk in chunks:
        tags = chunk.get("tags", {})
        keywords = tags.get("keywords", []) if isinstance(tags, dict) else []
        for kw in keywords:
            if isinstance(kw, str) and kw.strip():
                all_keywords[kw.lower()] = all_keywords.get(kw.lower(), 0) + 2.0
    
    # Strategy 2: Extract named entities
    full_text = " ".join(texts)
    entities = extract_named_entities(full_text)
    for entity, entity_type in entities:
        if len(entity.split()) <= 3:  # Keep short entities
            all_keywords[entity.lower()] = all_keywords.get(entity.lower(), 0) + 1.5
    
    # Strategy 3: Extract important noun phrases
    noun_phrases = extract_noun_phrases(full_text)
    for phrase in noun_phrases:
        if len(phrase.split()) <= 3 and phrase.lower() not in stop_words:
            all_keywords[phrase.lower()] = all_keywords.get(phrase.lower(), 0) + 1.0
    
    # Strategy 4: TF-IDF scoring
    tfidf_scores = calculate_tfidf_scores(texts)
    for term, score in tfidf_scores.items():
        all_keywords[term] = all_keywords.get(term, 0) + score
    
    # Sort by score and return top_n
    ranked = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


def find_answer_sentences(answer: str, text: str, max_sentences: int = 3) -> str:
    """Find sentences containing the answer for better context."""
    sentences = sent_tokenize(text)
    answer_lower = answer.lower()
    
    # Find sentences containing the answer
    matching_sentences = [
        sent for sent in sentences
        if answer_lower in sent.lower()
    ]
    
    if matching_sentences:
        return " ".join(matching_sentences[:max_sentences])
    
    # Fallback: return first few sentences
    return " ".join(sentences[:max_sentences]) if sentences else text


def generate_question(answer: str, context: str) -> str:
    """Generate a question from an answer and context."""
    _ensure_models_loaded()
    assert _QG_TOKENIZER is not None
    assert _QG_MODEL is not None

    # Use answer-specific context for better questions
    focused_context = find_answer_sentences(answer, context)
    
    prompt = f"answer: {answer} context: {focused_context}"
    input_ids = _QG_TOKENIZER.encode(
        prompt, 
        return_tensors="pt",
        max_length=512,
        truncation=True
    ).to(_DEVICE)
    
    question_ids = _QG_MODEL.generate(
        input_ids,
        max_length=64,
        num_beams=4,
        early_stopping=True
    )
    
    question = _QG_TOKENIZER.decode(question_ids[0], skip_special_tokens=True)
    
    # Clean up question formatting
    if question.lower().startswith("question:"):
        question = question[len("question:"):].strip()
    
    # Ensure it ends with question mark
    if question and not question.endswith("?"):
        question += "?"
    
    return question


def get_wordnet_distractors(word: str, n: int = 3) -> list[str]:
    """Generate distractors via WordNet using multiple strategies."""
    normalized_word = word.strip().lower().replace(" ", "_")
    if not normalized_word:
        return []

    distractors: OrderedDict[str, None] = OrderedDict()

    # Strategy 1: Synonyms
    for synset in wordnet.synsets(normalized_word):
        for lemma in synset.lemmas():
            candidate = lemma.name().replace("_", " ").strip()
            if candidate.lower() != word.strip().lower():
                distractors[candidate.lower()] = None
    
    # Strategy 2: Hypernyms -> Hyponyms
    for synset in wordnet.synsets(normalized_word):
        for hypernym in synset.hypernyms():
            for hyponym in hypernym.hyponyms():
                for lemma in hyponym.lemma_names():
                    candidate = lemma.replace("_", " ").strip()
                    if candidate.lower() != word.strip().lower():
                        distractors[candidate.lower()] = None
    
    # Strategy 3: Sibling terms (same hypernym)
    for synset in wordnet.synsets(normalized_word):
        for hypernym in synset.hypernyms():
            for sibling in hypernym.hyponyms():
                for lemma in sibling.lemma_names():
                    candidate = lemma.replace("_", " ").strip()
                    if candidate.lower() != word.strip().lower():
                        distractors[candidate.lower()] = None

    return list(distractors.keys())[:n]


def get_corpus_distractors(
    answer: str, 
    all_keywords: list[str], 
    chunks: list[dict[str, Any]], 
    n: int = 3
) -> list[str]:
    """Generate distractors from the corpus based on similar entities/terms."""
    distractors = []
    answer_lower = answer.lower()
    
    # Get answer entity type if it's an entity
    full_text = " ".join([c.get("text", "") for c in chunks if c.get("text")])
    entities = extract_named_entities(full_text)
    answer_entity_type = None
    
    for entity, ent_type in entities:
        if entity.lower() == answer_lower:
            answer_entity_type = ent_type
            break
    
    # Find similar entities or keywords
    for keyword in all_keywords:
        if keyword.lower() == answer_lower:
            continue
        
        # If answer is an entity, prefer same entity type
        if answer_entity_type:
            for entity, ent_type in entities:
                if (entity.lower() == keyword.lower() and 
                    ent_type == answer_entity_type):
                    distractors.append(keyword)
                    break
        else:
            # Use similar length terms as distractors
            if abs(len(keyword.split()) - len(answer.split())) <= 1:
                distractors.append(keyword)
        
        if len(distractors) >= n:
            break
    
    return distractors[:n]


def get_enhanced_distractors(
    answer: str,
    all_keywords: list[str],
    chunks: list[dict[str, Any]],
    n: int = 3
) -> list[str]:
    """Generate high-quality distractors using multiple strategies."""
    distractors: OrderedDict[str, None] = OrderedDict()
    
    # Strategy 1: WordNet
    wordnet_distractors = get_wordnet_distractors(answer, n=n*2)
    for d in wordnet_distractors:
        if d.strip():
            distractors[d] = None
    
    # Strategy 2: Corpus-based
    corpus_distractors = get_corpus_distractors(answer, all_keywords, chunks, n=n*2)
    for d in corpus_distractors:
        if d.strip():
            distractors[d] = None
    
    # Strategy 3: Fallback - similar keywords by length
    if len(distractors) < n:
        answer_len = len(answer.split())
        for kw in all_keywords:
            if kw.lower() != answer.lower():
                kw_len = len(kw.split())
                if abs(kw_len - answer_len) <= 1:
                    distractors[kw] = None
    
    result = list(distractors.keys())[:n]
    
    # Ensure we have exactly n distractors (pad with generic ones if needed)
    while len(result) < n:
        generic = f"Option {len(result) + 1}"
        if generic not in result:
            result.append(generic)
    
    return result


def is_valid_question(question: str, answer: str) -> bool:
    """Check if generated question meets quality criteria."""
    if not question or not answer:
        return False
    
    # Must have minimum length
    if len(question) < 10:
        return False
    
    # Should end with question mark
    if not question.endswith("?"):
        return False
    
    # Should contain question words or be properly formatted
    question_words = ["what", "which", "who", "where", "when", "why", "how", "is", "are", "do", "does"]
    has_question_word = any(qw in question.lower() for qw in question_words)
    
    if not has_question_word:
        return False
    
    # Answer shouldn't appear verbatim in question
    if answer.lower() in question.lower():
        return False
    
    return True


def calculate_question_similarity(q1: str, q2: str) -> float:
    """Calculate similarity between two questions."""
    # Token-based similarity
    tokens1 = set(word_tokenize(q1.lower()))
    tokens2 = set(word_tokenize(q2.lower()))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)
    
    # Sequence similarity
    seq_sim = SequenceMatcher(None, q1.lower(), q2.lower()).ratio()
    
    # Combined score
    return (jaccard + seq_sim) / 2


def deduplicate_mcqs(mcqs: list[dict[str, Any]], threshold: float = 0.7) -> list[dict[str, Any]]:
    """Remove duplicate or very similar questions."""
    if not mcqs:
        return []
    
    unique_mcqs = []
    
    for mcq in mcqs:
        is_duplicate = False
        current_q = mcq["question"]
        
        for existing_mcq in unique_mcqs:
            similarity = calculate_question_similarity(current_q, existing_mcq["question"])
            if similarity >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_mcqs.append(mcq)
    
    return unique_mcqs


def build_mcqs(
    chunks: list[dict[str, Any]], num_questions: int = 5
) -> list[dict[str, Any]]:
    """Build high-quality MCQs from retrieved chunks using enhanced NLP pipeline."""
    if num_questions <= 0:
        return []
    
    if not chunks:
        logger.warning("No chunks provided for quiz generation")
        return []
    
    # Extract and rank keywords
    ranked_keywords = get_enhanced_keywords(chunks, top_n=num_questions * 3)
    if not ranked_keywords:
        logger.warning("No keywords extracted from chunks")
        return []
    
    # Get all keyword strings for distractor generation
    all_keyword_strings = [kw for kw, _ in ranked_keywords]
    
    # Build full context
    texts = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]
    full_context = " ".join(texts)
    
    if not full_context.strip():
        logger.warning("No text content in chunks")
        return []
    
    mcqs: list[dict[str, Any]] = []
    attempted = 0
    max_attempts = num_questions * 3  # Try more to account for filtering
    
    for keyword, score in ranked_keywords:
        if attempted >= max_attempts or len(mcqs) >= num_questions * 2:
            break
        
        attempted += 1
        
        # Validate answer appears in context
        if keyword.lower() not in full_context.lower():
            continue
        
        # Generate question
        question = generate_question(keyword, full_context)
        
        # Validate question quality
        if not is_valid_question(question, keyword):
            logger.debug("Question failed validation: %s", question)
            continue
        
        # Generate distractors
        distractors = get_enhanced_distractors(
            keyword, 
            all_keyword_strings, 
            chunks, 
            n=3
        )
        
        # Ensure we have valid distractors
        if not distractors or len([d for d in distractors if d.strip()]) < 3:
            logger.debug("Insufficient distractors for answer: %s", keyword)
            continue
        
        # Build options and shuffle
        options = [keyword] + distractors
        random.shuffle(options)
        
        # Determine difficulty and source chunks
        difficulty = "medium"
        source_chunk_ids: list[str] = []
        
        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            if keyword.lower() in chunk_text:
                chunk_id = str(chunk.get("chunk_id", ""))
                if chunk_id:
                    source_chunk_ids.append(chunk_id)
                
                # Get difficulty from chunk tags
                if difficulty == "medium":
                    chunk_tags = chunk.get("tags", {})
                    tag_difficulty = chunk_tags.get("difficulty", "")
                    if isinstance(tag_difficulty, str) and tag_difficulty.strip():
                        difficulty = tag_difficulty
        
        mcqs.append({
            "question": question,
            "answer": keyword,
            "options": options,
            "difficulty": difficulty,
            "source_chunk_ids": source_chunk_ids,
        })
    
    # Deduplicate similar questions
    mcqs = deduplicate_mcqs(mcqs, threshold=0.7)
    
    # Return requested number
    final_mcqs = mcqs[:num_questions]
    
    logger.info(
        "Generated %d unique MCQs from %d chunks (attempted %d, filtered %d)",
        len(final_mcqs), len(chunks), attempted, len(mcqs) - len(final_mcqs)
    )
    
    return final_mcqs