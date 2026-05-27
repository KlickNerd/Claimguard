"""Schemas for the final holistic compliance audit (Opus 4.7).

The per-claim pipeline (detection -> retrieval -> evaluation -> smart-
apply) is great at single-sentence verdicts but blind to text-level
issues: broken Markdown tables after a row drop, topic drift in FAQ
answers, duplicate paragraphs, factual errors in citations, comparative-
advertising risks under UWG, and implicit health claims that only
emerge from the surrounding context.

The final audit runs a single Opus 4.7 call over the entire (rewritten)
text with a holistic checklist and returns structured findings. It does
NOT modify the text - the user decides which findings to act on.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AuditSeverity = Literal["low", "medium", "high", "critical"]

AuditCategory = Literal[
    # Structural failures from the previous rewrite passes
    "broken-table",
    "broken-list",
    "duplicate-paragraph",
    "orphaned-sentence",
    # Topic / semantic
    "topic-drift",
    "answer-misses-question",
    "factual-error",
    "circular-content",
    # Compliance categories not always caught by the per-claim pipeline
    "implicit-claim-by-context",
    "context-disease-link",
    "uwg-comparative",
    "uwg-misleading",
    "hwg-violation",
    "lazy-disclaimer",
    # Catch-all for anything else
    "other",
]


class AuditFinding(BaseModel):
    """One issue found by the holistic audit.

    ``location_quote`` is the verbatim text snippet (15-80 chars) so the
    frontend can highlight it without recomputing positions. ``finding``
    is the human-readable problem statement, ``recommendation`` is what
    the user should do about it, ``replacement`` is the concrete fix
    text that the frontend can splice into the document on "Übernehmen".
    """

    severity: AuditSeverity = Field(description="Risk level for this finding.")
    category: AuditCategory = Field(
        description="High-level classification of the issue.",
    )
    location_quote: str = Field(
        description=(
            "Verbatim quote from the audited text (15-80 chars). The "
            "frontend uses this to scroll to the finding."
        ),
        min_length=3,
        max_length=240,
    )
    finding: str = Field(
        description="1-3 sentence German description of what is wrong.",
        min_length=10,
        max_length=1200,
    )
    recommendation: str = Field(
        description="1-2 sentence German recommendation for the fix.",
        min_length=5,
        max_length=600,
    )
    replacement: str | None = Field(
        default=None,
        description=(
            "Concrete fix text. If set, the frontend can replace "
            "``location_quote`` in the document with this string in "
            "one click. Empty string means 'delete the location_quote'. "
            "Null means the finding is not a single-shot text edit "
            "(e.g. 'restructure this entire section') and must be "
            "handled manually."
        ),
        max_length=2000,
    )


class FinalAuditResult(BaseModel):
    """Output of one ``FinalAuditService.audit`` run.

    ``overall_assessment`` is a 1-2 sentence executive summary that
    answers the question "Is this text shippable?". The verbose
    findings list backs that summary up.
    """

    overall_assessment: str = Field(
        description=(
            "Executive summary, 1-2 sentences. Tells the user whether "
            "the text can ship as-is or needs further work."
        ),
    )
    shippable: bool = Field(
        description=(
            "True when no findings are 'high' or 'critical'. Allows the "
            "frontend to render a clear green/red banner."
        ),
    )
    findings: list[AuditFinding] = Field(
        default_factory=list,
        description="Detailed findings, newest/highest severity first.",
    )
    model: str = Field(description="Model id used for the audit.")
    prompt_version: str = Field(description="Prompt version used for the audit.")
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
