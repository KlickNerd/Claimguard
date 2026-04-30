"""Pydantic schemas for entries in the EU Register of Health Claims.

The register lists every health claim that is authorised, rejected, or
on-hold under EU Regulation 1924/2006. Each entry has a stable claim-id
that we keep as our primary key so re-imports stay idempotent.

Reference: https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register
"""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field

EuClaimStatus = Literal[
    "authorised",      # Approved health claim
    "non_authorised",  # Rejected by EFSA / Commission
    "on_hold",         # Botanical claims awaiting EFSA assessment
]

EuClaimType = Literal[
    "art_13_1",        # General function claims (most common)
    "art_13_5",        # New function claims based on proprietary data
    "art_14_1_a",      # Disease risk reduction claims
    "art_14_1_b",      # Children's development claims
    "unknown",
]


class EuClaim(BaseModel):
    """A single entry from the EU Register of Health Claims."""

    id: str = Field(description="Stable EU register identifier (claim_id)")
    nutrient: str | None = Field(
        default=None,
        description="Nutrient, substance, food or food category the claim refers to.",
    )
    claim_de: str | None = Field(
        default=None,
        description="Claim wording in German.",
    )
    claim_en: str | None = Field(
        default=None,
        description="Claim wording in English (always present in the register).",
    )
    conditions: str | None = Field(
        default=None,
        description="Conditions under which the claim may be used (e.g. minimum nutrient amount).",
    )
    health_relationship: str | None = Field(
        default=None,
        description="Health relationship the claim establishes (e.g. 'maintenance of normal bone').",
    )
    status: EuClaimStatus
    claim_type: EuClaimType = "unknown"
    regulation_reference: str | None = Field(
        default=None,
        description="e.g. 'Commission Regulation (EU) No 432/2012'.",
    )
    commission_regulation: str | None = Field(
        default=None,
        description="Authorising or rejecting Commission Regulation number.",
    )
    entry_date: Date | None = Field(
        default=None,
        description="Date the entry was added to the register.",
    )
    source_url: str | None = Field(
        default="https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register",
    )


class EuRegisterImport(BaseModel):
    """Output of a single EU-register import run."""

    kb_version: str = Field(description="ISO date of the source file, e.g. '2026-04-19'")
    source_file: str
    imported_at: Date
    total: int
    by_status: dict[EuClaimStatus, int]
    by_type: dict[EuClaimType, int]
    claims: list[EuClaim]
