"""Pydantic schemas for the hybrid retrieval stage (PROJ-9).

The retrieval service unifies hits from two Qdrant collections (eu_claims
and hcvo_chunks) so the evaluator only needs one homogeneous list. Each hit
carries enough metadata for the LLM to cite the source and for the UI to
deep-link back to Eur-Lex.
"""

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["eu_claim", "regulation", "case_law", "botanical"]


class RetrievalHit(BaseModel):
    """One retrieved knowledge-base entry, ready to feed into the LLM prompt."""

    chunk_id: str = Field(description="Stable id from the source JSON")
    source_type: SourceType
    score: float = Field(ge=0.0, le=1.0)
    snippet: str = Field(description="Up to 600 chars of the original text")
    reference: str = Field(description="Human-readable citation, e.g. 'VO 432/2012, Anhang'")
    url: str = Field(description="Deep-link to authoritative source")
    metadata: dict[str, str | int | None] = Field(
        default_factory=dict,
        description="Source-specific extras (article + paragraph, nutrient, EFSA ref, …).",
    )


class RetrievalResult(BaseModel):
    """Top-K results for a single claim."""

    query: str
    hits: list[RetrievalHit]
    latency_ms: int
