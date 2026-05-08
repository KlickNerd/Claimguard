from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.schemas.analysis import AnalysisResponse
from app.schemas.claim import DetectedClaim, DetectionResult
from app.schemas.retrieval import RetrievalHit
from app.config import settings
from app.services.claim_detector import ClaimDetector
from app.services.claim_evaluator import ClaimEvaluator
from app.services.cost_estimator import estimate_cost_usd
from app.services.language_detector import is_german
from app.services.retrieval_service import RetrievalService
from app.services.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


class PipelineError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class DetectionOnlyPipeline:
    """Stage-2 pipeline: normalize → detect → retrieve → evaluate.

    ``retriever`` and ``evaluator`` are optional so unit tests can omit
    stages. When the retriever is present, evidence is collected per claim
    before evaluation and fed into the LLM prompt (PROJ-10 design); the
    evaluator's hallucination check uses those chunk_ids.
    """

    detector: ClaimDetector
    evaluator: ClaimEvaluator | None = None
    retriever: RetrievalService | None = None
    # Three is enough now that the cosine threshold filters out weak
    # rank-padded hits; five let too many rank-3+ entries through that
    # didn't actually fit the claim.
    retrieval_top_k: int = 3

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

        logger.info("Pipeline: starting detection (%d chars)", len(normalized))
        detection: DetectionResult = await asyncio.to_thread(
            self.detector.detect,
            normalized,
        )
        logger.info(
            "Pipeline: detection done (%d claims, %d ms)",
            len(detection.claims),
            detection.latency_ms,
        )

        warnings: list[str] = []
        evidence_per_claim: dict[str, list[RetrievalHit]] = {}
        if self.retriever is not None and detection.claims:
            logger.info("Pipeline: starting retrieval for %d claims", len(detection.claims))
            evidence_per_claim, retrieval_warning = await self._gather_evidence(
                detection.claims,
            )
            logger.info("Pipeline: retrieval done")
            if retrieval_warning:
                warnings.append(retrieval_warning)

        evaluated_claims = []
        evaluation_latency_ms = 0
        evaluation_tokens_in = 0
        evaluation_tokens_out = 0

        if self.evaluator is not None and detection.claims:
            logger.info("Pipeline: starting evaluation for %d claims", len(detection.claims))
            try:
                # Hard cap on the entire evaluation phase. Per-claim
                # timeouts already exist inside evaluate_all; this is a
                # belt-and-braces bound so the request always returns
                # something well under Caddy's 300 s budget, even if
                # a flurry of slow calls + retries stack up.
                evaluation = await asyncio.wait_for(
                    self.evaluator.evaluate_all(
                        claims=detection.claims,
                        full_text=normalized,
                        evidence_per_claim=evidence_per_claim,
                    ),
                    timeout=220.0,
                )
                evaluated_claims = evaluation.evaluated_claims
                evaluation_latency_ms = evaluation.latency_ms
                evaluation_tokens_in = evaluation.total_input_tokens
                evaluation_tokens_out = evaluation.total_output_tokens
                logger.info(
                    "Pipeline: evaluation done (%d/%d evaluated, %d ms)",
                    len(evaluated_claims),
                    len(detection.claims),
                    evaluation_latency_ms,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Pipeline: evaluation phase exceeded 220 s budget, returning detection-only.",
                )
                warnings.append(
                    "Bewertung wurde abgebrochen (Zeitlimit erreicht). Erkannte Claims sind sichtbar - "
                    "bitte erneut versuchen oder Text in kleinere Abschnitte teilen.",
                )

            if (
                len(evaluated_claims) < len(detection.claims)
                and len(evaluated_claims) > 0
            ):
                warnings.append(
                    "Einige Claims konnten nicht bewertet werden (Timeout oder Anthropic-Fehler). "
                    "Erkannte Claims sind sichtbar; bitte erneut versuchen für die fehlenden Bewertungen.",
                )

        if len(detection.claims) == 0:
            warnings.append(
                "Keine gesundheitsbezogenen Aussagen gefunden. Der Text wirkt compliance-neutral "
                "- prüfe trotzdem, ob implizite Claims in Bildsprache oder Keywords stecken.",
            )

        # Cost estimate is intentionally an upper bound - prompt caching
        # in the evaluator drops the real bill, but we don't get the
        # cache-split through the simple call path so we report the
        # nominal-rate sum here. Better to over-estimate than surprise
        # the user with a bigger Anthropic bill at month end.
        cost_estimate = (
            estimate_cost_usd(
                detection.model,
                detection.input_tokens,
                detection.output_tokens,
            )
            + estimate_cost_usd(
                settings.anthropic_model_evaluation,
                evaluation_tokens_in,
                evaluation_tokens_out,
            )
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
            estimated_cost_usd=round(cost_estimate, 4),
            latency_ms=detection.latency_ms + evaluation_latency_ms,
            warnings=warnings,
        )

    async def _gather_evidence(
        self,
        claims: list[DetectedClaim],
    ) -> tuple[dict[str, list[RetrievalHit]], str | None]:
        """Run retrieval per claim in parallel; tolerate KB outages."""
        assert self.retriever is not None

        async def fetch(claim: DetectedClaim) -> tuple[str, list[RetrievalHit] | None]:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.retriever.retrieve_for_claim,
                        claim,
                        top_k=self.retrieval_top_k,
                    ),
                    timeout=20.0,
                )
                return str(claim.id), result.hits
            except asyncio.TimeoutError:
                logger.warning("Retrieval timed out for claim %s after 20 s", claim.id)
                return str(claim.id), None
            except Exception as exc:
                logger.warning("Retrieval failed for claim %s: %s", claim.id, exc)
                return str(claim.id), None

        results = await asyncio.gather(*(fetch(c) for c in claims))

        any_failed = any(hits is None for _, hits in results)
        evidence: dict[str, list[RetrievalHit]] = {
            cid: (hits or []) for cid, hits in results
        }
        warning = (
            "Wissensbasis aktuell eingeschränkt erreichbar - einige Belege fehlen."
            if any_failed
            else None
        )
        return evidence, warning
