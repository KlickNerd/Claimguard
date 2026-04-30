from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.schemas.claim import DetectedClaim, DetectionResult
from app.services.anthropic_client import create_message_with_tool
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
