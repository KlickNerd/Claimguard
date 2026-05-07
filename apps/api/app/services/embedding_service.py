"""In-process embedding service for ClaimGuard's knowledge base (PROJ-9).

We use ``intfloat/multilingual-e5-base`` because:
- 440 MB - small enough to load in-process without a separate container
- Solid German performance on MTEB (top-tier among open multi-lingual models)
- Apache-2.0 license, native ARM64 support, no custom transformer code
- Stable since 2023, widely used in production retrieval stacks

ADR-0003 prefers jina-v3 self-hosted; if recall@8 turns out below 0.85 on
the eval set we'll switch via env var. e5 stays the safe default for now
because it doesn't need ``trust_remote_code`` and loads cleanly on first
boot without docker pulls.

E5 expects an instruction prefix on every input - "query: " for retrieval
queries, "passage: " for indexed documents. The wrapper adds it for you so
callers don't have to remember.
"""

from __future__ import annotations

import logging
import threading
from typing import Literal

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


_DEFAULT_MODEL = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768  # e5-base output

_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "

EmbedKind = Literal["query", "passage"]


class _ModelHolder:
    """Lazy singleton so the 440 MB model is loaded once per process."""

    _model: SentenceTransformer | None = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> SentenceTransformer:
        if cls._model is None:
            with cls._lock:
                if cls._model is None:
                    name = getattr(
                        settings,
                        "embedding_model",
                        _DEFAULT_MODEL,
                    ) or _DEFAULT_MODEL
                    logger.info("Loading embedding model %s …", name)
                    cls._model = SentenceTransformer(name)
                    dim_fn = getattr(
                        cls._model,
                        "get_embedding_dimension",
                        cls._model.get_sentence_embedding_dimension,
                    )
                    logger.info("Embedding model loaded: dim=%d", dim_fn())
        return cls._model


def embed(texts: list[str], *, kind: EmbedKind = "passage") -> list[list[float]]:
    """Return one embedding per input text. Inputs are prefixed for E5."""
    if not texts:
        return []
    prefix = _QUERY_PREFIX if kind == "query" else _PASSAGE_PREFIX
    prefixed = [f"{prefix}{text}" for text in texts]
    model = _ModelHolder.get()
    vectors: np.ndarray = model.encode(
        prefixed,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()


def embed_one(text: str, *, kind: EmbedKind = "query") -> list[float]:
    return embed([text], kind=kind)[0]
