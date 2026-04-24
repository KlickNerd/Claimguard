from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

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
