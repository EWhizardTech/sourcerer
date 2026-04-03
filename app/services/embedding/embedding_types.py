# app/services/embedding/embedding_types.py

from typing import List, Optional, TypedDict

from app.services.tagging.tagging_types import TaggedChunk


class EmbeddedChunk(TaggedChunk):
    """Output of the embedding stage.

    Preserves all fields from TaggedChunk and adds the dense vector.
    """

    dense_vector: List[float]
