"""Pydantic schemas for the botanical / EFSA-on-hold knowledge base.

Botanicals are the elephant in DACH supplement marketing: most plant-based
ingredients (Curcuma, Ginkgo, Ashwagandha, …) sit in the EU register with
status ``on_hold`` because EFSA paused their scientific evaluation back in
2010. As long as the assessment is pending, the corresponding wording can
generally still be used (transitional regime under Art. 28 HCVO), but
companies must avoid disease-related framing and stay close to the
historic claim text. A small handful of botanicals (e.g. *Piper
methysticum* / Kava) are outright ``non_authorised``.

This schema captures just enough to let the retrieval pipeline cite a
botanical entry: scientific name, German common name, intended health
relationship that was originally pending, and status.

The seed dataset (``data/botanicals.json``) is a curated short-list of
the ~60 most-marketed substances in DACH supplements. The full ~1.500-
entry EU on-hold register can be imported via the existing
``import_eu_register`` script once the user provides the official XLSX
download.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BotanicalStatus = Literal[
    "on_hold",         # EFSA-Bewertung ausgesetzt, Übergangsregime greift
    "non_authorised",  # Endgültig abgelehnt
    "authorised",      # Vollständig zugelassener Health Claim (selten bei Botanicals)
]


class BotanicalEntry(BaseModel):
    """One entry in the curated botanical knowledge base."""

    id: str = Field(description="Stable slug, e.g. 'curcuma-longa-leber'.")
    scientific_name: str = Field(description="Latin / botanical name, e.g. 'Curcuma longa'.")
    common_name_de: str = Field(description="German common name shown in marketing.")
    common_names: list[str] = Field(
        default_factory=list,
        description="Alternative spellings / English names that retrieval should also catch.",
    )
    status: BotanicalStatus
    health_relationship: str = Field(
        description="What the pending or rejected claim was about, in our own words.",
    )
    pending_claim_de: str | None = Field(
        default=None,
        description="Wording of the originally pending claim, German, paraphrased.",
    )
    pending_claim_en: str | None = Field(
        default=None,
        description="Original English wording from the EFSA on-hold register.",
    )
    summary: str = Field(
        description=(
            "Two-sentence editorial note: what the on-hold status means for "
            "marketing, plus any specific risks (e.g. arzneimittelrechtliche "
            "Einordnung)."
        ),
        max_length=600,
    )
    risk_notes: list[str] = Field(
        default_factory=list,
        description=(
            "Free-form risk flags, e.g. 'arzneimittelnah', "
            "'BVL-Beanstandung möglich', 'Wechselwirkungen'."
        ),
    )
    source_url: str = Field(
        default="https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register",
        description="Public reference URL.",
    )


class BotanicalDataset(BaseModel):
    version: str
    note: str = ""
    entries: list[BotanicalEntry]
