"""Cross-encoder reranking for retrieval results.

Overfetched hybrid-search candidates are rescored against the query with a
small local cross-encoder (ONNX via fastembed, no torch required). Falls
back to the original RRF order if the model is unavailable.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sourcerer_core.config import settings

logger = logging.getLogger(__name__)

_encoder = None
_encoder_failed = False
_lock = threading.Lock()


def _get_encoder():
    """Lazily load the cross-encoder once per process."""
    global _encoder, _encoder_failed
    if _encoder is not None or _encoder_failed:
        return _encoder
    with _lock:
        if _encoder is not None or _encoder_failed:
            return _encoder
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            _encoder = TextCrossEncoder(
                model_name=settings.RERANK_MODEL,
                cache_dir=settings.ML_CACHE_DIR,
            )
            logger.info("Loaded rerank model: %s", settings.RERANK_MODEL)
        except Exception as exc:  # noqa: BLE001 - reranking is best-effort
            _encoder_failed = True
            logger.warning(
                "Rerank model unavailable (%s); falling back to RRF order.", exc
            )
    return _encoder


def rerank(query: str, hits: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Rescore hits against the query and return the best top_k.

    Each hit is a dict with at least a "text" key; a "rerank_score" key is
    added to survivors. Hits without text keep their original position bias.
    """
    if not settings.RERANK_ENABLED or len(hits) <= 1:
        return hits[:top_k]

    encoder = _get_encoder()
    if encoder is None:
        return hits[:top_k]

    texts = [hit.get("text") or "" for hit in hits]
    try:
        scores = list(encoder.rerank(query, texts))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rerank failed (%s); falling back to RRF order.", exc)
        return hits[:top_k]

    for hit, score in zip(hits, scores):
        hit["rerank_score"] = float(score)

    ranked = sorted(hits, key=lambda h: h.get("rerank_score", float("-inf")), reverse=True)
    return ranked[:top_k]
