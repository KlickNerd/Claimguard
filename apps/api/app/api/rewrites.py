"""Endpoints for the 'Alle automatisch umschreiben' and 'Final glätten' UX."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.claim import DetectedClaim, EvaluatedClaim
from app.schemas.final_audit import FinalAuditResult
from app.services.anthropic_client import AnthropicServiceError
from app.services.claim_detector import ClaimDetector
from app.services.final_audit_service import FinalAuditService
from app.services.polish_service import PolishService
from app.services.rewrite_service import RewriteService
from app.services.smart_apply_service import SmartApplyService

router = APIRouter(prefix="/api/analyses", tags=["rewrites"])


class RewriteBatchRequest(BaseModel):
    claims: list[EvaluatedClaim] = Field(
        description="Evaluated claims that should be rewritten.",
    )
    input_text: str = Field(description="Original text the claims came from.")


class RewriteBatchResponse(BaseModel):
    rewrites: dict[str, str] = Field(
        description="Mapping ``claim_id -> rewrite_suggestion``.",
    )


def get_rewrite_service() -> RewriteService:
    return RewriteService()


@router.post(
    "/rewrite-batch",
    response_model=RewriteBatchResponse,
)
async def rewrite_batch(
    payload: RewriteBatchRequest,
    service: RewriteService = Depends(get_rewrite_service),
) -> RewriteBatchResponse:
    try:
        rewrites = await service.rewrite_all(
            claims=payload.claims,
            full_text=payload.input_text,
        )
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    return RewriteBatchResponse(rewrites=rewrites)


class PolishRequest(BaseModel):
    text: str = Field(description="Composed marketing text after rewrites have been applied.")


class PolishResponse(BaseModel):
    polished_text: str
    change_summary: str


def get_polish_service() -> PolishService:
    return PolishService()


@router.post(
    "/polish",
    response_model=PolishResponse,
)
async def polish(
    payload: PolishRequest,
    service: PolishService = Depends(get_polish_service),
) -> PolishResponse:
    try:
        polished, summary = await asyncio.to_thread(service.polish, payload.text)
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    return PolishResponse(polished_text=polished, change_summary=summary)


class SmartApplyRequest(BaseModel):
    input_text: str = Field(description="Original marketing text.")
    claims: list[EvaluatedClaim] = Field(
        description="All evaluated claims from the analysis run.",
    )


class SmartApplyResponse(BaseModel):
    rewritten_text: str
    residual_claims: list[DetectedClaim] = Field(
        default_factory=list,
        description=(
            "Claims still detected after the auto-rewrite (convergence "
            "check). Empty list = rewrite converged; non-empty = further "
            "manual review needed."
        ),
    )
    convergence_warning: str | None = Field(
        default=None,
        description=(
            "Human-readable warning if the convergence check itself "
            "failed (e.g. Anthropic outage during the re-detection). "
            "Null when the check succeeded, regardless of result."
        ),
    )


def get_smart_apply_service() -> SmartApplyService:
    # Wire a ClaimDetector for the convergence check so the user sees
    # immediately whether the rewrite still leaks claims. Construction
    # is cheap (no model load), so we instantiate per-request.
    return SmartApplyService(detector=ClaimDetector())


@router.post(
    "/smart-apply",
    response_model=SmartApplyResponse,
)
async def smart_apply(
    payload: SmartApplyRequest,
    service: SmartApplyService = Depends(get_smart_apply_service),
) -> SmartApplyResponse:
    try:
        result = await service.smart_apply(
            input_text=payload.input_text,
            evaluated_claims=payload.claims,
        )
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    return SmartApplyResponse(
        rewritten_text=result.rewritten_text,
        residual_claims=result.residual_claims,
        convergence_warning=result.convergence_warning,
    )


class FinalAuditRequest(BaseModel):
    text: str = Field(
        description=(
            "Marketing text to audit holistically. Usually the smart-"
            "apply output, but works on any input."
        ),
        min_length=10,
    )
    reformulated_from_original: bool = Field(
        default=False,
        description=(
            "True if the text just came out of smart-apply. Triggers an "
            "extra prompt note that nudges the auditor toward typical "
            "post-rewrite failure modes (broken tables, boilerplate)."
        ),
    )


def get_final_audit_service() -> FinalAuditService:
    return FinalAuditService()


@router.post(
    "/final-audit",
    response_model=FinalAuditResult,
)
async def final_audit(
    payload: FinalAuditRequest,
    service: FinalAuditService = Depends(get_final_audit_service),
) -> FinalAuditResult:
    """Single-call holistic compliance review with Opus 4.7.

    Catches what the per-claim pipeline misses: broken Markdown tables,
    topic drift in FAQ answers, duplicate paragraphs, factual errors,
    UWG §5/§6 risks, HWG vocabulary, and implicit health claims induced
    by surrounding context. Read-only - the user decides which findings
    to act on.
    """
    try:
        result = await asyncio.to_thread(
            service.audit,
            text=payload.text,
            reformulated_from_original=payload.reformulated_from_original,
        )
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    return result
