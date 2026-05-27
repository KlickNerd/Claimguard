"""Holistic compliance audit over a finished marketing text.

The per-claim pipeline (detection -> retrieval -> evaluation -> smart-
apply) is great at single-sentence verdicts but blind to text-level
problems: broken Markdown tables after a row drop, topic drift in FAQ
answers, duplicate paragraphs, factual errors, UWG §5/§6 risks, HWG
vocabulary the per-claim pass missed, and implicit health claims that
only surface from surrounding context.

This service runs a single Opus 4.7 call over the entire text with a
holistic checklist and returns structured findings. It does NOT modify
the text - the user decides which findings to act on.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.schemas.final_audit import AuditFinding, FinalAuditResult
from app.services.anthropic_client import (
    AnthropicServiceError,
    create_message_with_tool,
)
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = logging.getLogger(__name__)


_FINAL_AUDIT_TOOL: dict[str, Any] = {
    "name": "record_final_audit",
    "description": (
        "Record the holistic compliance audit. Returns an executive "
        "summary, a shippable flag, and a list of findings (high-severity "
        "first). Findings cover broken tables, topic drift, duplicates, "
        "factual errors, UWG/HWG risks, and context-induced claims."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_assessment": {
                "type": "string",
                "description": (
                    "1-2 sentence German executive summary. Tells the "
                    "user whether the text is shippable or needs work."
                ),
            },
            "shippable": {
                "type": "boolean",
                "description": (
                    "True only when no findings are 'high' or 'critical'."
                ),
            },
            "findings": {
                "type": "array",
                "description": (
                    "List of issues, highest severity first, max 25 entries."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "broken-table",
                                "broken-list",
                                "duplicate-paragraph",
                                "orphaned-sentence",
                                "topic-drift",
                                "answer-misses-question",
                                "factual-error",
                                "circular-content",
                                "implicit-claim-by-context",
                                "context-disease-link",
                                "uwg-comparative",
                                "uwg-misleading",
                                "hwg-violation",
                                "lazy-disclaimer",
                                "other",
                            ],
                        },
                        "location_quote": {
                            "type": "string",
                            "description": (
                                "Verbatim quote from the audited text, "
                                "15-80 characters. Used to highlight."
                            ),
                        },
                        "finding": {
                            "type": "string",
                            "description": "1-3 sentence German description.",
                        },
                        "recommendation": {
                            "type": "string",
                            "description": "1-2 sentence German recommendation.",
                        },
                    },
                    "required": [
                        "severity",
                        "category",
                        "location_quote",
                        "finding",
                        "recommendation",
                    ],
                },
            },
        },
        "required": ["overall_assessment", "shippable", "findings"],
    },
}


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
    ) -> tuple[dict[str, Any], int, int]: ...


class FinalAuditService:
    """Single Opus-pass holistic review.

    Default model is the configured evaluator model (Opus 4.7); callers
    can pass a cheaper model in tests via the ``model`` constructor arg.
    """

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader | None = None,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
    ) -> None:
        self._loader = prompt_loader or get_prompt_loader()
        self._call = tool_caller or create_message_with_tool
        self._model = model or settings.anthropic_model_evaluation

    def audit(
        self,
        *,
        text: str,
        reformulated_from_original: bool = False,
    ) -> FinalAuditResult:
        if not text or not text.strip():
            return FinalAuditResult(
                overall_assessment=(
                    "Es wurde kein Text zum Auditen übergeben."
                ),
                shippable=False,
                findings=[],
                model=self._model,
                prompt_version="n/a",
                input_tokens=0,
                output_tokens=0,
                latency_ms=0,
            )

        template = self._loader.get("final_audit")
        rendered = self._loader.render(
            "final_audit",
            {
                "text": text,
                "reformulated_from_original": reformulated_from_original,
            },
            version=template.metadata.version,
        )

        started = time.perf_counter()
        try:
            tool_input, in_tok, out_tok = self._call(
                model=self._model,
                system=None,
                user_content=rendered.rendered,
                # Opus 4.7 output speed sits around ~30-40 tok/s for
                # structured tool calls. 4k tokens = ~2 minutes of
                # generation, which keeps us comfortably below Caddy's
                # 10-minute proxy timeout even on 30k-char pillar pages
                # with prompt caching warm. 4k is also plenty for ~25
                # findings of ~150 tokens each plus the executive
                # summary - we cap at 25 findings in the prompt anyway.
                tool=_FINAL_AUDIT_TOOL,
                max_tokens=4000,
            )
        except AnthropicServiceError as exc:
            logger.warning("Final audit Anthropic-side failure: %s", exc)
            raise
        except Exception as exc:
            logger.warning("Final audit unexpected failure: %s", exc)
            raise

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        findings_raw: list[dict[str, Any]] = list(tool_input.get("findings") or [])
        findings: list[AuditFinding] = []
        for raw in findings_raw:
            try:
                findings.append(AuditFinding.model_validate(raw))
            except (TypeError, ValueError) as exc:
                logger.warning("Dropping malformed audit finding: %s; raw=%r", exc, raw)
                continue

        # The LLM is told to sort by severity, but we re-sort defensively
        # in case the response drifted. Critical/high first.
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        findings.sort(key=lambda f: severity_rank.get(f.severity, 99))

        overall = str(tool_input.get("overall_assessment") or "").strip()
        if not overall:
            overall = (
                "Audit abgeschlossen. Bitte Findings einzeln prüfen."
                if findings
                else "Audit abgeschlossen. Keine Findings gefunden."
            )

        # Compute shippable flag from severities ourselves so we can't
        # be lied to by the model. shippable = no critical/high.
        has_blocking = any(f.severity in ("critical", "high") for f in findings)
        shippable_raw = tool_input.get("shippable")
        shippable = bool(shippable_raw) if isinstance(shippable_raw, bool) else not has_blocking
        # Reconcile: if the model said shippable=true but we have a
        # high/critical finding, the safer answer wins.
        if has_blocking:
            shippable = False

        logger.info(
            "final_audit: %d findings (shippable=%s) in %d ms, "
            "%d in/%d out tokens",
            len(findings),
            shippable,
            elapsed_ms,
            in_tok,
            out_tok,
        )

        return FinalAuditResult(
            overall_assessment=overall,
            shippable=shippable,
            findings=findings,
            model=self._model,
            prompt_version=template.metadata.version,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=elapsed_ms,
        )
