from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.schemas.claim import ClaimType, DetectedClaim, DetectionResult
from app.services.anthropic_client import create_message_with_tool
from app.services.forbidden_terms import (
    ForbiddenTermHit,
    claim_type_for_hit,
    find_forbidden_terms,
)
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = logging.getLogger(__name__)


DETECTION_TOOL: dict[str, Any] = {
    "name": "record_detected_claims",
    "description": (
        "Record every health claim found in the input text. Only include "
        "claims that appear verbatim in the input - never invent wording."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "claims": {
                "type": "array",
                "description": "List of every detected health claim.",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_text": {
                            "type": "string",
                            "description": "Exact wording as it appears in the input.",
                        },
                        "claim_type": {
                            "type": "string",
                            "enum": [
                                "nutrient_based",
                                "health_based",
                                "reduction_based",
                                "wellbeing_based",
                                "disease_based",
                            ],
                        },
                        "nutrient": {
                            "type": "string",
                            "description": "Nutrient name if applicable (e.g. 'Vitamin C').",
                        },
                        "substance": {
                            "type": "string",
                            "description": "Other substance if applicable (e.g. 'Ashwagandha').",
                        },
                        "implicitness": {
                            "type": "string",
                            "enum": ["explicit", "implicit"],
                        },
                    },
                    "required": ["claim_text", "claim_type", "implicitness"],
                },
            },
        },
        "required": ["claims"],
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
    ) -> tuple[dict[str, Any], int, int]: ...


class ClaimDetector:
    """Runs claim-detection via Anthropic tool use.

    ``tool_caller`` is injectable so unit tests can supply a stub without
    hitting the network; production wiring uses :func:`create_message_with_tool`.
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
        self._model = model or settings.anthropic_model_detection

    def detect(self, input_text: str) -> DetectionResult:
        template = self._loader.get("claim_detection")
        rendered = self._loader.render(
            "claim_detection",
            {"input_text": input_text},
            version=template.metadata.version,
        )

        started = time.perf_counter()
        # Long marketing pages can yield 40+ claims; the default 4096-token
        # budget gets truncated mid-tool-call, leaving us with an empty
        # claims list. 8192 covers ~80 claims comfortably.
        tool_input, in_tok, out_tok = self._call(
            model=self._model,
            system=None,
            user_content=rendered.rendered,
            tool=DETECTION_TOOL,
            max_tokens=8192,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "claim_detection: %d claims raw, %d in/%d out tokens, %d ms",
            len(tool_input.get("claims", [])),
            in_tok,
            out_tok,
            elapsed_ms,
        )

        raw_claims: list[dict[str, Any]] = list(tool_input.get("claims", []))
        claims: list[DetectedClaim] = []
        for raw in raw_claims:
            claim_text = raw.get("claim_text", "").strip()
            if not claim_text:
                continue
            start = input_text.find(claim_text)
            if start < 0:
                # Hallucination guard: LLM paraphrased instead of quoting.
                logger.warning(
                    "Dropping hallucinated claim not present in input: %r",
                    claim_text,
                )
                continue
            claims.append(
                DetectedClaim(
                    claim_text=claim_text,
                    claim_type=raw["claim_type"],
                    nutrient=_nullable(raw.get("nutrient")),
                    substance=_nullable(raw.get("substance")),
                    implicitness=raw["implicitness"],
                    position_start=start,
                    position_end=start + len(claim_text),
                ),
            )

        # Deterministic safety net: add HWG / wellbeing terms that the
        # LLM may have skipped. Customer feedback from 2026-05-26 showed
        # terms like ``Heiltradition``, ``Anwendungsgebiete``,
        # ``Symptom-Tagebuch`` getting through detection unflagged - the
        # regex matcher catches those reproducibly.
        deterministic = _deterministic_claims(input_text)
        added = _merge_deterministic(claims, deterministic)
        if added:
            logger.info(
                "Detection: %d deterministic HWG/wellbeing hits added "
                "after LLM pass",
                len(added),
            )
            claims.extend(added)

        return DetectionResult(
            claims=claims,
            prompt_version=template.metadata.version,
            model=self._model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=elapsed_ms,
        )


def _nullable(value: Any) -> str | None:
    """Treat empty strings from the LLM as missing, not as real values."""
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _deterministic_claims(input_text: str) -> list[DetectedClaim]:
    """Build synthetic ``DetectedClaim``s from forbidden-term hits.

    Each unique span produces one claim - if two rules fire on the same
    span (e.g. ``mentales Wohlbefinden`` triggers both ``wohlbefinden``
    and ``mentales-wohlbefinden``) we keep the longer span so the UI
    highlights the more meaningful phrase.
    """
    raw_hits = find_forbidden_terms(input_text)
    if not raw_hits:
        return []

    # When multiple rules fire on overlapping spans, prefer the widest
    # one for the user-facing claim. We bucket by approximate position
    # (same start) and keep the longest hit per bucket.
    by_start: dict[int, ForbiddenTermHit] = {}
    for hit in raw_hits:
        existing = by_start.get(hit.start)
        if existing is None or (hit.end - hit.start) > (
            existing.end - existing.start
        ):
            by_start[hit.start] = hit

    out: list[DetectedClaim] = []
    for hit in by_start.values():
        claim_type: ClaimType = claim_type_for_hit(hit)  # type: ignore[assignment]
        out.append(
            DetectedClaim(
                claim_text=input_text[hit.start : hit.end],
                claim_type=claim_type,
                nutrient=None,
                substance=None,
                implicitness="explicit",
                position_start=hit.start,
                position_end=hit.end,
            ),
        )
    return out


def _merge_deterministic(
    llm_claims: list[DetectedClaim],
    deterministic_claims: list[DetectedClaim],
) -> list[DetectedClaim]:
    """Return the deterministic hits that the LLM did not already cover.

    A deterministic hit is considered covered when its span sits inside
    (or matches exactly) any LLM-detected claim - in that case the
    evaluation pass will already see the term as part of the larger
    claim sentence and we don't want to duplicate it as its own card.
    """
    if not deterministic_claims:
        return []
    out: list[DetectedClaim] = []
    for det in deterministic_claims:
        covered = any(
            llm.position_start <= det.position_start
            and det.position_end <= llm.position_end
            for llm in llm_claims
        )
        if not covered:
            out.append(det)
    return out
