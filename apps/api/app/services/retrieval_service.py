"""Hybrid retrieval over the curated KB (PROJ-9).

Two parallel rankings get fused via Reciprocal Rank Fusion (RRF):

1. **Vector search** in Qdrant across the three source collections
   (``eu_claims``, ``regulation``, ``case_law``) with ``multilingual-e5-base``
   embeddings (ADR-0006). Catches semantic paraphrases.
2. **Keyword search** in Postgres ``kb_chunks`` via
   ``websearch_to_tsquery('german', …)``. Catches lexical matches that the
   embedding misses - e.g. "Apotheker", "Nebenwirkungen", "Heilung" - and
   reaches the smaller HWG / LFGB excerpts that the dominant 200 HCVO
   chunks would otherwise drown out in vector space.

Per ADR-0004 we deliberately skip a reranker - RRF on these two rankings
gives solid Top-8 quality at the KB size we have today (~ 420 entries).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any, cast

from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint

from app.config import settings
from app.schemas.claim import DetectedClaim
from app.schemas.retrieval import RetrievalHit, RetrievalResult, SourceType
from app.services import postgres_fts
from app.services.embedding_service import embed_one
from app.services.reranker import rerank

logger = logging.getLogger(__name__)


_RRF_K = 60


_SOURCE_COLLECTIONS: tuple[tuple[str, SourceType], ...] = (
    ("eu_claims", "eu_claim"),
    ("regulation", "regulation"),
    ("case_law", "case_law"),
    ("botanicals", "botanical"),
)


class RetrievalService:
    """Embeds the query once, searches both collections, fuses via RRF."""

    def __init__(
        self,
        *,
        qdrant_url: str | None = None,
        per_collection_top_k: int = 8,
        score_threshold: float = 0.45,
        rerank_pool_size: int = 16,
        rerank_min_score: float = 0.0,
        enable_rerank: bool = True,
    ) -> None:
        self._client = QdrantClient(url=qdrant_url or settings.qdrant_url)
        self._per_top_k = per_collection_top_k
        # Cosine pre-filter is intentionally loose - we let the cross-encoder
        # re-ranker do the relevance work, since multilingual-e5-base lands
        # almost everything in the 0.78-0.86 cosine band on German claims.
        self._score_threshold = score_threshold
        self._rerank_pool_size = rerank_pool_size
        # bge-reranker-v2-m3 raw logits: ~ 0 means irrelevant, > 1 means
        # related, > 3 means strong match. Anything below this cutoff is
        # dropped from the UI to spare the user from off-topic citations.
        self._rerank_min_score = rerank_min_score
        self._enable_rerank = enable_rerank

    def retrieve_for_claim(
        self,
        claim: DetectedClaim,
        *,
        top_k: int = 8,
    ) -> RetrievalResult:
        """Build the expanded query (claim + nutrient + substance) and search."""
        return self.retrieve(_build_query(claim), top_k=top_k)

    def retrieve(self, query: str, *, top_k: int = 8) -> RetrievalResult:
        started = time.perf_counter()
        if not query.strip():
            return RetrievalResult(query=query, hits=[], latency_ms=0)

        vector = embed_one(query, kind="query")
        per_source_hits: list[list[RetrievalHit]] = []
        for collection, source_type in _SOURCE_COLLECTIONS:
            try:
                response = self._client.query_points(
                    collection_name=collection,
                    query=vector,
                    limit=self._per_top_k,
                    score_threshold=self._score_threshold,
                    with_payload=True,
                )
                points = response.points
            except Exception as exc:
                logger.warning("Qdrant search failed on %s: %s", collection, exc)
                continue
            per_source_hits.append([_to_hit(p, source_type) for p in points])

        # FTS half - failure is non-fatal so a Postgres outage degrades
        # retrieval to vector-only instead of breaking the whole pipeline.
        try:
            fts_ranking = _fts_ranking(query, limit=self._per_top_k)
        except Exception as exc:
            logger.warning("Postgres FTS search failed: %s", exc)
            fts_ranking = []
        if fts_ranking:
            per_source_hits.append(fts_ranking)

        fused = _rrf_fuse(per_source_hits, k=_RRF_K)

        # Cross-encoder re-rank of the RRF candidate pool. The cosine /
        # ts_rank scores are too flat on legal German to use directly -
        # the cross-encoder reads (query, snippet) end-to-end and gives
        # a real relevance score we can threshold on.
        if self._enable_rerank and fused:
            pool = fused[: self._rerank_pool_size]
            passages = [f"{h.reference}\n{h.snippet}" for h in pool]
            try:
                rerank_scores = rerank(query, passages)
            except Exception as exc:
                logger.warning("Reranker failed, falling back to RRF order: %s", exc)
                rerank_scores = []
            if rerank_scores:
                ranked = sorted(
                    zip(pool, rerank_scores, strict=True),
                    key=lambda t: t[1],
                    reverse=True,
                )
                hits: list[RetrievalHit] = []
                for hit, raw in ranked:
                    if raw < self._rerank_min_score:
                        continue
                    new_meta = {**hit.metadata, "rerank_score": f"{raw:.3f}"}
                    hits.append(
                        hit.model_copy(
                            update={
                                "score": _confidence_from_rerank(raw),
                                "metadata": new_meta,
                            },
                        ),
                    )
                fused = hits

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return RetrievalResult(query=query, hits=fused[:top_k], latency_ms=elapsed_ms)


def _confidence_from_rerank(value: float) -> float:
    """Map a cross-encoder logit onto a 0..1 'confidence' chip for the UI.

    bge-reranker-v2-m3 emits roughly:
    - < 0.05  : irrelevant - we still keep it because the LLM may use it
                as context, but the chip should look low
    - 0.1-0.5 : loosely related
    - 0.7-1.0 : strong topical match
    - > 1     : near-paraphrase

    We just clip into 0..1 - it's an honest "how sure is the match" chip
    rather than a calibrated probability.
    """
    return max(0.0, min(1.0, value))


def _build_query(claim: DetectedClaim) -> str:
    """Concatenate claim text with nutrient/substance hints from PROJ-8."""
    parts = [claim.claim_text]
    if claim.nutrient:
        parts.append(claim.nutrient)
    if claim.substance and claim.substance != claim.nutrient:
        parts.append(claim.substance)
    return " — ".join(parts)


def _fts_ranking(query: str, *, limit: int) -> list[RetrievalHit]:
    """Run the Postgres FTS query and shape the result as RetrievalHits.

    The numeric ts_rank is normalised onto 0..1 within this query so it
    can be displayed alongside the vector cosine score, but RRF only
    cares about the position - so the absolute number is informational.
    """
    fts_hits = postgres_fts.search(query, limit=limit)
    if not fts_hits:
        return []
    max_rank = max((h.rank for h in fts_hits), default=1.0) or 1.0
    out: list[RetrievalHit] = []
    for hit in fts_hits:
        normalised = float(hit.rank) / max_rank
        meta = {k: _coerce_meta(v) for k, v in (hit.metadata or {}).items()}
        # Tag the hit so the display filter can let FTS results through
        # regardless of cosine threshold (FTS uses ts_rank, not cosine).
        meta["retrieval"] = "fts"
        out.append(
            RetrievalHit(
                chunk_id=hit.chunk_id,
                source_type=cast(SourceType, hit.source_type),
                score=normalised,
                snippet=hit.snippet[:600],
                reference=hit.reference,
                url=hit.url,
                metadata=meta,
            ),
        )
    return out


def _to_hit(point: ScoredPoint, source_type: SourceType) -> RetrievalHit:
    payload: dict[str, Any] = dict(point.payload or {})
    metadata = {
        k: v
        for k, v in payload.items()
        if k not in {"chunk_id", "source_type", "snippet", "reference", "url"}
    }
    return RetrievalHit(
        chunk_id=str(payload.get("chunk_id") or point.id),
        source_type=source_type,
        score=float(point.score or 0.0),
        snippet=str(payload.get("snippet") or "")[:600],
        reference=str(payload.get("reference") or ""),
        url=str(payload.get("url") or ""),
        metadata={k: _coerce_meta(v) for k, v in metadata.items()},
    )


def _coerce_meta(value: Any) -> str | int | None:
    if value is None or isinstance(value, (str, int)):
        return value
    return str(value)


def _rrf_fuse(
    per_source_hits: Iterable[list[RetrievalHit]],
    *,
    k: int,
) -> list[RetrievalHit]:
    """Reciprocal Rank Fusion: score = Σ 1 / (k + rank_i).

    Hits are dedup'd by chunk_id - the same legal source surfaced from two
    rankings should reinforce, not double-count.
    """
    fused: dict[str, RetrievalHit] = {}
    rrf_scores: dict[str, float] = {}

    for ranking in per_source_hits:
        for rank, hit in enumerate(ranking, start=1):
            contribution = 1.0 / (k + rank)
            if hit.chunk_id in fused:
                rrf_scores[hit.chunk_id] += contribution
                # Keep the higher-ranking hit's metadata for snippet/reference
                if hit.score > fused[hit.chunk_id].score:
                    fused[hit.chunk_id] = hit
            else:
                fused[hit.chunk_id] = hit
                rrf_scores[hit.chunk_id] = contribution

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
    # Sort by RRF score, but expose the *original* cosine / ts_rank score
    # to the UI - the user reads ``score`` as "confidence", not as
    # "rank-fusion artefact". RRF is kept as metadata for debugging.
    max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0
    result: list[RetrievalHit] = []
    for chunk_id in sorted_ids:
        hit = fused[chunk_id]
        rrf_norm = rrf_scores[chunk_id] / max_rrf if max_rrf else 0.0
        new_meta = {**hit.metadata, "rrf_score": f"{rrf_norm:.3f}"}
        result.append(hit.model_copy(update={"metadata": new_meta}))
    return result


_default: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _default
    if _default is None:
        _default = RetrievalService()
    return _default
