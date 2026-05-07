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


class AnalysisError(BaseModel):
    code: Literal[
        "input_too_short",
        "language_not_supported",
        "anthropic_unavailable",
        "schema_violation",
        "internal_error",
    ]
    message: str
