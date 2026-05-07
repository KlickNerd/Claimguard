"""Endpoints for the 'Alle automatisch umschreiben' and 'Final glätten' UX."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.claim import EvaluatedClaim
from app.services.anthropic_client import AnthropicServiceError
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


def get_smart_apply_service() -> SmartApplyService:
    return SmartApplyService()


@router.post(
    "/smart-apply",
    response_model=SmartApplyResponse,
)
async def smart_apply(
    payload: SmartApplyRequest,
    service: SmartApplyService = Depends(get_smart_apply_service),
) -> SmartApplyResponse:
    try:
        rewritten = await service.smart_apply(
            input_text=payload.input_text,
            evaluated_claims=payload.claims,
        )
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    return SmartApplyResponse(rewritten_text=rewritten)
