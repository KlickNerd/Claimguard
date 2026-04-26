from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.schemas.analysis import AnalysisResponse
from app.schemas.claim import DetectionResult
from app.services.claim_detector import ClaimDetector
from app.services.claim_evaluator import ClaimEvaluator
from app.services.language_detector import is_german
from app.services.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class DetectionOnlyPipeline:
    """Stage-2 pipeline: normalize → language-check → detect → quick-evaluate.

    The evaluator is optional so tests that only care about detection can
    pass ``evaluator=None``. Retrieval (PROJ-9) and the full Opus-based
    evaluation (PROJ-10) replace the evaluator here once they land.
    """

    detector: ClaimDetector
    evaluator: ClaimEvaluator | None = None

    async def run(
        self,
        *,
        input_text: str,
        source_type: str = "text",
        source_reference: str | None = None,
    ) -> AnalysisResponse:
        normalized = normalize_text(input_text)

        if len(normalized) < 50:
            raise PipelineError(
                "input_too_short",
                "Bitte mindestens 50 Zeichen eingeben, damit eine sinnvolle Analyse möglich ist.",
            )

        if not is_german(normalized):
            raise PipelineError(
                "language_not_supported",
                "ClaimGuard unterstützt im MVP nur deutschsprachige Texte.",
            )

        detection: DetectionResult = await asyncio.to_thread(
            self.detector.detect,
            normalized,
        )

        evaluated_claims = []
        evaluation_latency_ms = 0
        evaluation_tokens_in = 0
        evaluation_tokens_out = 0

        if self.evaluator is not None and detection.claims:
            evaluation = await self.evaluator.evaluate_all(
                claims=detection.claims,
                full_text=normalized,
            )
            evaluated_claims = evaluation.evaluated_claims
            evaluation_latency_ms = evaluation.latency_ms
            evaluation_tokens_in = evaluation.total_input_tokens
            evaluation_tokens_out = evaluation.total_output_tokens

        warnings: list[str] = []
        if len(detection.claims) == 0:
            warnings.append(
                "Keine gesundheitsbezogenen Aussagen gefunden. Der Text wirkt compliance-neutral "
                "- prüfe trotzdem, ob implizite Claims in Bildsprache oder Keywords stecken.",
            )

        return AnalysisResponse(
            status="completed",
            source_type=source_type,  # type: ignore[arg-type]
            source_reference=source_reference,
            input_text=normalized,
            detected_claims=detection.claims,
            evaluated_claims=evaluated_claims,
            prompt_version=detection.prompt_version,
            model=detection.model,
            input_tokens=detection.input_tokens + evaluation_tokens_in,
            output_tokens=detection.output_tokens + evaluation_tokens_out,
            latency_ms=detection.latency_ms + evaluation_latency_ms,
            warnings=warnings,
        )
