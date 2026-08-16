# Quiz Service

`services/quiz` — multiple-choice question generation from retrieved course content.

## Endpoint

### `POST /api/v1/quiz/generate`

```json
{
  "query": "what is information retrieval?",
  "filters": { "course_code": "20XW81", "year": "2026", "tags": ["retrieval"] },
  "num_questions": 5,
  "allow_unfiltered_fallback": true
}
```

Response — a list of MCQs:

```json
[
  {
    "question": "What does TF-IDF stand for?",
    "answer": "Term Frequency–Inverse Document Frequency",
    "options": ["…", "…", "…", "…"],
    "difficulty": "Medium",
    "source_chunk_ids": ["6f6c…"]
  }
]
```

### `GET /api/v1/quiz/health`

Verifies the NLP models load (T5, spaCy).

## How it works

1. **Retrieve** — `sourcerer_core.retrieval_service` performs filtered hybrid search directly against Qdrant (course/year/tag filters **do** apply). If filters return nothing and `allow_unfiltered_fallback` is true, it retries unfiltered.
2. **Generate** — for each chunk: multi-strategy keyword extraction (NER + TF-IDF + noun phrases), T5 (`ramsrigouthamg/t5_squad_v1`) question generation, distractor mining (WordNet + corpus + entities), quality validation, and near-duplicate removal.

## Model assets

Models and corpora are cached under `.cache/` (mounted into the container):

- Hugging Face: T5 question-generation model
- spaCy: `en_core_web_sm`
- NLTK: wordnet, punkt, stopwords

First run downloads them; subsequent runs are warm.
