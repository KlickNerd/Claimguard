"""Pydantic schemas for the case-law knowledge base (PROJ-6).

Each entry is a redactional paraphrase of a published German or EU court
decision relevant to health-claim advertising. We never store verbatim
court text - that would conflict with the original publishers' rights
(juris/beck-online). Paraphrases stay in our own words and link back to a
public source for verification.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

CaseDecision = Literal["allowed", "borderline", "forbidden", "overruled"]
CaseClaimType = Literal[
    "nutrient_based",
    "health_based",
    "reduction_based",
    "wellbeing_based",
    "disease_based",
    "general_health",
]
# Provenance of a case entry. "verified" = manually checked by Dominik
# (or read from the original ruling). "ai_curated_pending" = added by
# an AI assistant from training data, Aktenzeichen + Zusammenfassung
# need a human review before commercial use. Audit-pipeline surfaces
# both; the frontend can render pending entries with a "🤖 KI-kuratiert,
# zu prüfen"-badge.
VerificationStatus = Literal["verified", "ai_curated_pending"]
AiConfidence = Literal["high", "medium", "low"]


class CaseLawEntry(BaseModel):
    """One court decision paraphrased into ClaimGuard's own wording."""

    id: str = Field(description="Stable slug, e.g. 'bgh-i-zr-252-16-detox'.")
    court: str = Field(description="Court that decided, e.g. 'BGH', 'OLG Frankfurt', 'EuGH'.")
    case_number: str = Field(description="Aktenzeichen, e.g. 'I ZR 252/16'.")
    decision_date: date = Field(description="Date the ruling was issued.")
    title: str = Field(description="Short headline for the case, e.g. 'Detox-Slogan'.")
    claim_type: CaseClaimType
    decision: CaseDecision = Field(
        description="How the court ruled: allowed, borderline, forbidden, or overruled.",
    )
    summary: str = Field(
        description=(
            "Redactional paraphrase of the relevant reasoning, in our own words. "
            "<= 600 characters."
        ),
        max_length=600,
    )
    legal_basis: list[str] = Field(
        default_factory=list,
        description="Norms applied, e.g. ['VO 1924/2006 Art. 10', 'UWG § 5'].",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Keywords for search filters (nutrient, substance, marketing topic).",
    )
    source_url: str = Field(description="Public URL where the full text can be verified.")
    verification_status: VerificationStatus = Field(
        default="verified",
        description=(
            "Provenance of this entry. Pending entries need a human "
            "double-check before commercial use - the AI may have "
            "guessed the Aktenzeichen wrong."
        ),
    )
    ai_confidence: AiConfidence | None = Field(
        default=None,
        description=(
            "When verification_status='ai_curated_pending', how sure the "
            "AI is about the Aktenzeichen + decision date. High = "
            "BGH-Klassiker from training data; medium = OLG/KG ruling I "
            "remember by topic; low = topic plausible, exact Aktenzeichen "
            "guessed."
        ),
    )


class CaseLawDataset(BaseModel):
    version: str = Field(description="Free-form revision marker, e.g. '2026-05-01'.")
    note: str = Field(
        default="",
        description="Editorial note shown to admins; not surfaced in retrieval output.",
    )
    cases: list[CaseLawEntry]
