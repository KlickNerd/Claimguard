"""Pydantic schemas for chunks of EU food-law regulations (PROJ-5).

The chunking strategy is semantic - one chunk per (Artikel, Absatz) pair -
rather than token-based, so that retrieval (PROJ-9) and citation in the
report (PROJ-14) hit complete legal units. Annexes are kept as their own
chunks with ``is_annex=True`` so the prompt can decide how to weight them.
"""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field


class RegulationChunk(BaseModel):
    """One semantic unit of a regulation - typically Article + Absatz."""

    regulation_id: str = Field(
        description="Short identifier, e.g. '1924/2006' or '432/2012'.",
    )
    chunk_id: str = Field(
        description="Stable composite id: '<regulation>-art<n>-para<m>'.",
    )
    article: int | None = Field(
        default=None,
        description="Article number (Artikel 7 → 7). Null for preamble / annex header.",
    )
    article_title: str | None = Field(
        default=None,
        description="Article subtitle, e.g. 'Allgemeine Grundsätze'.",
    )
    paragraph: int | None = Field(
        default=None,
        description="Paragraph number within the article (Absatz 1 → 1).",
    )
    subparagraph: str | None = Field(
        default=None,
        description="Letter sub-paragraph (a, b, c, …), if any.",
    )
    text: str = Field(description="Full paragraph text in German.")
    section: str | None = Field(
        default=None,
        description="Chapter / Kapitel / Abschnitt label this chunk belongs to.",
    )
    is_annex: bool = False
    language: Literal["de"] = "de"
    eur_lex_url: str = Field(description="Direct deep-link to Eur-Lex.")


class RegulationImport(BaseModel):
    """Output of a single regulation import run."""

    kb_version: str = Field(description="ISO date of the source file or consolidated version.")
    regulation_id: str
    regulation_title: str
    consolidated_date: Date | None = None
    source_file: str
    imported_at: Date
    total: int
    by_article: dict[int, int] = Field(
        default_factory=dict,
        description="Number of chunks per article (article_number → count).",
    )
    chunks: list[RegulationChunk]
