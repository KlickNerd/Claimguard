from __future__ import annotations

import logging
from dataclasses import dataclass

from app.schemas.analysis import AnalysisResponse
from app.schemas.claim import DetectionResult
from app.services.claim_detector import ClaimDetector
from app.services.language_detector import is_german
from app.services.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class DetectionOnlyPipeline:
    """Stage-1 pipeline: text normalization + language check + LLM detection.

    Retrieval and evaluation are intentionally absent - they come with PROJ-9
    and PROJ-10. Output maps cleanly onto AnalysisResponse so the frontend
    doesn't need a second code path once further stages are added.
    """

    detector: ClaimDetector

    def run(
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

        result: DetectionResult = self.detector.detect(normalized)

        warnings: list[str] = []
        if len(result.claims) == 0:
            warnings.append(
                "Keine gesundheitsbezogenen Aussagen gefunden. Der Text wirkt compliance-neutral "
                "- prüfe trotzdem, ob implizite Claims in Bildsprache oder Keywords stecken.",
            )

        return AnalysisResponse(
            status="completed",
            source_type=source_type,  # type: ignore[arg-type]
            source_reference=source_reference,
            input_text=normalized,
            detected_claims=result.claims,
            prompt_version=result.prompt_version,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            warnings=warnings,
        )
