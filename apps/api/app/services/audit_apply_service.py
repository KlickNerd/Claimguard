"""Apply a list of holistic-audit findings to a marketing text.

The :class:`final_audit_service.FinalAuditService` returns a list of
``AuditFinding`` objects with ``recommendation`` + ``replacement``
fields. The per-claim panel can splice each ``replacement`` into the
text directly, but two cases warrant a single-LLM-call rewrite instead:

1. Findings without ``replacement`` (e.g. "restructure this whole
   section") - the deterministic splice can't handle them.
2. The user clicks "Audit-Befunde komplett umsetzen lassen" and wants
   *one* coherent rewrite instead of N independent splices.

This service is the second mode. It packages the text + findings into
a Sonnet prompt and returns the rewritten text in one shot.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.schemas.final_audit import AuditFinding
from app.services.anthropic_client import (
    AnthropicServiceError,
    create_message_with_tool,
)
from app.services.forbidden_terms import (
    find_forbidden_terms,
    forbidden_terms_summary,
)
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = logging.getLogger(__name__)


_APPLY_TOOL: dict[str, Any] = {
    "name": "record_text_rewrite",
    "description": (
        "Record the marketing text with all audit findings applied. "
        "The text is returned in full, with each location_quote "
        "replaced according to the corresponding finding's "
        "recommendation/replacement and unaffected sections kept "
        "verbatim. No prose, no metadata - just the body."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rewritten_text": {
                "type": "string",
                "description": (
                    "Full German marketing text with all findings "
                    "applied. Preserves Markdown structure (#, ##, "
                    "lists, tables, blockquotes, links)."
                ),
            },
        },
        "required": ["rewritten_text"],
    },
}

# Per-call SDK timeout. The apply pass operates on the full text and
# can emit up to ~30 k characters back; Sonnet at ~70 tok/s needs ~90-
# 150 s for that. 240 s gives a comfortable buffer and matches the
# final-audit budget so a stuck call still fails cleanly under the
# FastAPI 480 s and Caddy 600 s caps.
_APPLY_SDK_TIMEOUT_S = 240.0


class _ToolCaller(Protocol):
    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = ...,
        cache_system: bool = ...,
        timeout: float | None = ...,
    ) -> tuple[dict[str, Any], int, int]: ...


class AuditApplyService:
    """Single-LLM-call "apply all audit findings" rewrite."""

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader | None = None,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
    ) -> None:
        self._loader = prompt_loader or get_prompt_loader()
        self._call = tool_caller or create_message_with_tool
        # Sonnet 4.6 - same model the rest of the rewrite pipeline uses.
        self._model = model or settings.anthropic_model_detection

    def apply(
        self,
        *,
        text: str,
        findings: list[AuditFinding],
        overall_assessment: str = "",
    ) -> tuple[str, int]:
        """Return ``(rewritten_text, sdk_findings_applied)``.

        The "applied" count is the number of findings we passed to the
        LLM; we cannot reliably know how many it actually merged, but
        the LLM is prompted to address every entry. If the call fails
        (Anthropic outage, schema mismatch), we propagate the
        :class:`AnthropicServiceError` so the API layer can return a
        503 with a clean message instead of a partial result.

        Fallback for the customer-observed "0 findings + non-empty
        summary" case (2026-05-28): if ``findings`` is empty but
        ``overall_assessment`` contains prose describing what's wrong,
        the prompt switches to a summary-only mode and rewrites the
        text against the prose. Avoids leaving the user stranded when
        the auditor LLM declined to populate the structured list.
        """
        if not text or not text.strip():
            return text, 0
        # No findings AND no summary - nothing to do.
        if not findings and not overall_assessment.strip():
            return text, 0

        template = self._loader.get("apply_audit")
        findings_block = (
            _format_findings_block(findings)
            if findings
            else _format_summary_fallback_block(overall_assessment)
        )
        rendered = self._loader.render(
            "apply_audit",
            {"text": text, "findings_block": findings_block},
            version=template.metadata.version,
        )

        started = time.perf_counter()
        try:
            tool_input, in_tok, out_tok = self._call(
                model=self._model,
                system=None,
                user_content=rendered.rendered,
                tool=_APPLY_TOOL,
                # Long pillar pages can run 25-30 k characters of
                # output (=~8-10 k tokens). 16 k tokens leaves headroom
                # without truncating mid-call.
                max_tokens=16000,
                timeout=_APPLY_SDK_TIMEOUT_S,
            )
        except AnthropicServiceError:
            raise
        except Exception as exc:
            logger.warning("apply_audit unexpected failure: %s", exc)
            raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        rewritten = str(tool_input.get("rewritten_text") or "").strip()

        # Hard guardrail: the apply pass is the LAST chance before the
        # text hits the user. If the LLM somehow smuggled in HWG /
        # wellbeing terms despite the sperrliste in the prompt, refuse
        # the rewrite and surface the original text. The frontend then
        # sees an unchanged document plus our warning, instead of a
        # rewrite that fails its own compliance audit.
        hits = find_forbidden_terms(rewritten)
        if hits:
            offending = forbidden_terms_summary(hits)
            logger.warning(
                "apply_audit rewrite leaked sperrliste terms %r, "
                "returning original text unchanged",
                offending,
            )
            return text, 0

        applied = len(findings) if findings else 1
        logger.info(
            "apply_audit: %d findings applied (mode=%s), %d chars in -> "
            "%d chars out, %d in/%d out tokens, %d ms",
            applied,
            "findings" if findings else "summary_fallback",
            len(text),
            len(rewritten),
            in_tok,
            out_tok,
            elapsed_ms,
        )

        return rewritten or text, applied


def _format_findings_block(findings: list[AuditFinding]) -> str:
    """Render the findings as a readable Markdown list for the prompt."""
    lines: list[str] = []
    for idx, finding in enumerate(findings, start=1):
        replacement_part: str
        if finding.replacement is None:
            replacement_part = "_(kein konkreter Ersetzungs-Text - manuell formulieren)_"
        elif finding.replacement == "":
            replacement_part = "_(ersatzlos streichen)_"
        else:
            replacement_part = f"`{finding.replacement}`"
        lines.append(
            "\n".join(
                [
                    f"### Finding {idx} — {finding.severity} / {finding.category}",
                    f'**Original-Stelle:** "{finding.location_quote}"',
                    f"**Problem:** {finding.finding}",
                    f"**Empfehlung:** {finding.recommendation}",
                    f"**Ersetzungs-Text:** {replacement_part}",
                ],
            ),
        )
    return "\n\n".join(lines)


def _format_summary_fallback_block(overall_assessment: str) -> str:
    """Render a summary-only block when the audit didn't emit
    structured findings.

    Used when the auditor LLM returned a non-empty ``overall_assessment``
    but an empty findings list. The block tells the apply-LLM that it
    must read the prose summary, derive concrete fixes itself, and
    apply them to the text.
    """
    return (
        "### Hinweis — keine strukturierten Findings verfügbar\n\n"
        "Der vorherige Compliance-Audit hat keine strukturierte "
        "Finding-Liste geliefert, aber folgende **Executive Summary** "
        "abgegeben:\n\n"
        f"> {overall_assessment.strip()}\n\n"
        "Lies die Summary genau, identifiziere die genannten Probleme "
        "im Text **selbst** und wende konkrete Fixes an: HWG-Vokabular "
        "ersetzen oder streichen, kaputte Tabellen reparieren, Topic-"
        "Drifts auflösen, Sachfehler korrigieren, UWG-/HWG-Verstöße "
        "entschärfen. Die Sperrliste und Anti-Drift-Regeln aus dem "
        "Hauptprompt gelten weiterhin. Gib am Ende den vollständig "
        "überarbeiteten Text zurück."
    )
