"""Cross-encoder re-ranker for the hybrid retrieval pipeline (PROJ-9).

The bi-encoder (multilingual-e5-base, ADR-0006) is fast but not very
discriminative on short German legal claims - a typical query lands every
relevant entry in the 0.78-0.86 cosine band, mixed with topical false
positives at the same level. RRF only fixes the ordering of *those* candidates,
not the relevance of each one.

A cross-encoder reads the (query, passage) pair end-to-end and produces a
proper relevance score, which is far more diagnostic. We feed it the
RRF-fused top candidates and keep only the strongest.

ADR-0004 had this scheduled for V1.1; we pulled it forward because users
saw obviously irrelevant entries in the report's "Belege aus der
Wissensbasis" section.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


# bge-reranker-v2-m3 is multilingual, Apache-2.0, ~568 MB. Good German
# performance and known to work well as a generic re-ranker for legal-
# adjacent text.
_DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"


class _RerankerHolder:
    """Lazy-loaded process-level cross-encoder; same pattern as embedding_service."""

    _model: CrossEncoder | None = None
    _lock = threading.Lock()

    @classmethod
    def get(cls, name: str = _DEFAULT_MODEL) -> CrossEncoder:
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    from sentence_transformers import CrossEncoder
                    logger.info("Loading cross-encoder %s …", name)
                    cls._model = CrossEncoder(name, max_length=512)
                    logger.info("Cross-encoder loaded.")
        return cls._model


def rerank(query: str, passages: list[str]) -> list[float]:
    """Return one relevance score per passage, in the same order as the input.

    Empty passages list returns an empty list. The cross-encoder output
    range varies; bge-reranker-v2-m3 emits raw logits where ~ 0 means
    "irrelevant" and 5+ means "very relevant". We squash with sigmoid in
    the caller if it wants a 0..1 score.
    """
    if not passages:
        return []
    model = _RerankerHolder.get()
    pairs = [(query, p) for p in passages]
    scores = model.predict(
        pairs,
        show_progress_bar=False,
        convert_to_numpy=True,
        batch_size=16,
    )
    return [float(s) for s in scores]
