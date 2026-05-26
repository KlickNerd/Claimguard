from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.schemas.claim import DetectedClaim, EvaluatedClaim


def _utcnow() -> datetime:
    return datetime.now(UTC)

AnalysisStatus = Literal["pending", "running", "completed", "failed"]
SourceType = Literal["text", "url", "pdf"]


class AnalysisRequest(BaseModel):
    source_type: SourceType = "text"
    source_reference: str | None = None
    input_text: str = Field(min_length=50, max_length=50_000)
    # Optional explicit project; if omitted, the route falls back to the
    # X-Active-Project-Id header (and finally to the user's default).
    project_id: UUID | None = None


class AnalysisResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: AnalysisStatus
    source_type: SourceType
    source_reference: str | None = None
    input_text: str
    detected_claims: list[DetectedClaim]
    evaluated_claims: list[EvaluatedClaim] = Field(default_factory=list)
    prompt_version: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float = Field(
        default=0.0,
        description=(
            "Conservative upper-bound cost estimate in USD - prompt caching "
            "in the evaluator usually drops the real bill below this number."
        ),
    )
    latency_ms: int
    created_at: datetime = Field(default_factory=_utcnow)
    warnings: list[str] = Field(default_factory=list)
    # Set when the analysis was persisted to the DB (PROJ-21). Remains
    # ``None`` for anonymous demo runs and when the persist step failed.
    analysis_id: UUID | None = None
    project_id: UUID | None = None


class StoredAnalysis(BaseModel):
    """Row shape of ``public.analyses`` as returned by list/get endpoints."""

    id: UUID
    user_id: UUID
    project_id: UUID
    source_type: SourceType
    source_reference: str | None
    input_text: str
    detected_claims: list[DetectedClaim]
    evaluated_claims: list[EvaluatedClaim]
    warnings: list[str]
    prompt_version: str
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: int
    created_at: datetime
    deleted_at: datetime | None = None


class AnalysisListItem(BaseModel):
    """Slim shape for the History list (no full JSONB payloads)."""

    id: UUID
    project_id: UUID
    source_type: SourceType
    source_reference: str | None
    input_text_preview: str = Field(
        description="First ~120 characters of the input text for list rendering.",
    )
    risk_score: float | None = Field(
        default=None,
        description="0-1 aggregate over evaluated_claims; null for empty analyses.",
    )
    created_at: datetime


class AnalysisError(BaseModel):
    code: Literal[
        "input_too_short",
        "language_not_supported",
        "anthropic_unavailable",
        "schema_violation",
        "internal_error",
        "project_forbidden",
        "analysis_not_found",
    ]
    message: str
