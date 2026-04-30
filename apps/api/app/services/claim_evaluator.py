from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.schemas.claim import (
    DetectedClaim,
    EvaluatedClaim,
    EvaluationResult,
    LegalHint,
)
from app.services.anthropic_client import create_message_with_tool
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = logging.getLogger(__name__)


EVALUATION_TOOL: dict[str, Any] = {
    "name": "record_claim_evaluation",
    "description": (
        "Record the legal verdict for a single health claim. Use confidence "
        "below 0.6 to signal that the verdict is uncertain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["allowed", "borderline", "forbidden", "unclear"],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "reasoning": {
                "type": "string",
                "description": "2-4 sentence German explanation, accessible to non-lawyers.",
            },
            "rewrite_suggestion": {
                "type": "string",
                "description": (
                    "Alternative German formulation that preserves the marketing "
                    "intent without the legal risk. Null for allowed claims."
                ),
            },
            "legal_hints": {
                "type": "array",
                "description": "0-3 possibly-relevant legal references (not authoritative).",
                "items": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["reference", "rationale"],
                },
            },
        },
        "required": [
            "status",
            "confidence",
            "risk_level",
            "reasoning",
            "legal_hints",
        ],
    },
}

_CONTEXT_WINDOW_CHARS = 100


class _ToolCaller(Protocol):
    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = ...,
    ) -> tuple[dict[str, Any], int, int]: ...


class ClaimEvaluator:
    """Runs per-claim LLM evaluation without a curated knowledge base.

    This is the bridge between PROJ-8 (detection only) and the full
    PROJ-9 + PROJ-10 pipeline. Verdicts are presented in the UI with an
    explicit KI-Schätzung-disclaimer because legal_hints may be hallucinated
    until retrieval lands.
    """

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader | None = None,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
        max_concurrency: int = 8,
    ) -> None:
        self._loader = prompt_loader or get_prompt_loader()
        self._call = tool_caller or create_message_with_tool
        self._model = model or settings.anthropic_model_detection
        self._max_concurrency = max_concurrency

    async def evaluate_all(
        self,
        *,
        claims: list[DetectedClaim],
        full_text: str,
    ) -> EvaluationResult:
        if not claims:
            return EvaluationResult(
                evaluated_claims=[],
                total_input_tokens=0,
                total_output_tokens=0,
                latency_ms=0,
            )

        started = time.perf_counter()
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def bounded(claim: DetectedClaim) -> tuple[EvaluatedClaim | None, int, int]:
            async with semaphore:
                return await asyncio.to_thread(
                    self._evaluate_single,
                    claim,
                    full_text,
                )

        results = await asyncio.gather(*(bounded(c) for c in claims))

        evaluated: list[EvaluatedClaim] = []
        total_in = 0
        total_out = 0
        for ec, in_tok, out_tok in results:
            total_in += in_tok
            total_out += out_tok
            if ec is not None:
                evaluated.append(ec)

        # Preserve the original detection order so inline highlights line up
        # with the text left-to-right.
        evaluated.sort(key=lambda c: c.position_start)

        return EvaluationResult(
            evaluated_claims=evaluated,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _evaluate_single(
        self,
        claim: DetectedClaim,
        full_text: str,
    ) -> tuple[EvaluatedClaim | None, int, int]:
        template = self._loader.get("claim_evaluation_quick")
        context = self._surrounding_context(full_text, claim)

        try:
            rendered = self._loader.render(
                "claim_evaluation_quick",
                {
                    "claim": {
                        "claim_text": claim.claim_text,
                        "claim_type": claim.claim_type,
                        "nutrient": claim.nutrient,
                        "substance": claim.substance,
                        "implicitness": claim.implicitness,
                    },
                    "context": context,
                },
                version=template.metadata.version,
            )
            tool_input, in_tok, out_tok = self._call(
                model=self._model,
                system=None,
                user_content=rendered.rendered,
                tool=EVALUATION_TOOL,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Evaluation failed for claim %s: %s", claim.id, exc)
            return None, 0, 0

        try:
            evaluated = EvaluatedClaim(
                **claim.model_dump(),
                status=tool_input["status"],
                confidence=float(tool_input["confidence"]),
                risk_level=tool_input["risk_level"],
                reasoning=str(tool_input["reasoning"]).strip(),
                rewrite_suggestion=_nullable(tool_input.get("rewrite_suggestion")),
                legal_hints=[
                    LegalHint(**hint) for hint in tool_input.get("legal_hints", [])
                ],
                evaluation_model=self._model,
                evaluation_prompt_version=template.metadata.version,
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Schema violation in evaluation for %s: %s", claim.id, exc)
            return None, in_tok, out_tok

        # Enforce confidence threshold: below 0.6 downgrade to unclear so the
        # UI shows a manual-review hint regardless of what the model picked.
        if evaluated.confidence < 0.6 and evaluated.status != "unclear":
            evaluated = evaluated.model_copy(
                update={"status": "unclear", "rewrite_suggestion": None},
            )

        return evaluated, in_tok, out_tok

    def _surrounding_context(self, full_text: str, claim: DetectedClaim) -> str:
        start = max(0, claim.position_start - _CONTEXT_WINDOW_CHARS)
        end = min(len(full_text), claim.position_end + _CONTEXT_WINDOW_CHARS)
        snippet = full_text[start:end]
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(full_text) else ""
        return f"{prefix}{snippet}{suffix}"


def _nullable(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None
