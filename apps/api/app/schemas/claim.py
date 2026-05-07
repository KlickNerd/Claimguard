from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.schemas.retrieval import RetrievalHit

ClaimType = Literal[
    "nutrient_based",
    "health_based",
    "reduction_based",
    "wellbeing_based",
    "disease_based",
]

Implicitness = Literal["explicit", "implicit"]


class DetectedClaim(BaseModel):
    """A single health claim detected in the input text.

    Position indices are filled in by the pipeline, not by the LLM, so we can
    rely on them being consistent. The LLM is only responsible for returning
    ``claim_text`` verbatim from the input.
    """

    id: UUID = Field(default_factory=uuid4)
    claim_text: str
    claim_type: ClaimType
    nutrient: str | None = None
    substance: str | None = None
    implicitness: Implicitness
    position_start: int = Field(ge=0)
    position_end: int = Field(ge=0)

    @model_validator(mode="after")
    def _positions_valid(self) -> "DetectedClaim":
        if self.position_end < self.position_start:
            raise ValueError("position_end must be >= position_start")
        return self


class DetectionResult(BaseModel):
    """Output of the claim-detection pipeline stage."""

    claims: list[DetectedClaim]
    prompt_version: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


EvaluationStatus = Literal["allowed", "borderline", "forbidden", "unclear"]
RiskLevel = Literal["low", "medium", "high"]


class LegalHint(BaseModel):
    """A tentative legal reference suggested by the LLM without a curated KB.

    When ``verified`` is True the hint was validated against the curated
    knowledge base via PROJ-9 retrieval; chunk_id and url then point at the
    actual KB entry. When False, the hint is a Sonnet-only suggestion - the
    frontend keeps the "KI-Schätzung"-disclaimer for those.
    """

    reference: str = Field(description="e.g. 'Art. 7 LMIV' or 'BGH, I ZR 252/16'")
    rationale: str = Field(description="Why this reference applies, 1 sentence")
    verified: bool = Field(
        default=False,
        description="True when the reference matches a chunk in the curated KB.",
    )
    chunk_id: str | None = Field(
        default=None,
        description="Stable id of the KB chunk this hint cites, when verified.",
    )
    url: str | None = Field(
        default=None,
        description="Deep link to the source (Eur-Lex or EU Register), when verified.",
    )


class EvaluatedClaim(DetectedClaim):
    """A detected claim enriched with a first-pass legal verdict.

    The verdict is produced by Sonnet without retrieval, so it carries more
    risk of hallucinated citations. The UI must keep the "KI-Schätzung,
    Rechtsquellen-DB folgt"-disclaimer visible.
    """

    status: EvaluationStatus
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    reasoning: str
    rewrite_suggestion: str | None = None
    legal_hints: list[LegalHint] = Field(default_factory=list)
    evidence: list[RetrievalHit] = Field(
        default_factory=list,
        description="Top-K curated KB hits attached by PROJ-9 retrieval.",
    )
    evaluation_model: str
    evaluation_prompt_version: str


class EvaluationResult(BaseModel):
    """Output of the quick-evaluation pipeline stage."""

    evaluated_claims: list[EvaluatedClaim]
    total_input_tokens: int
    total_output_tokens: int
    latency_ms: int
