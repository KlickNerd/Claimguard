"""Analyses endpoints (PROJ-8/10 pipeline + PROJ-21 persistence + PROJ-22 scoping).

Surface area:
- ``POST /api/analyses``           run pipeline, persist when authed
- ``GET  /api/analyses``           list (project-scoped or across projects)
- ``GET  /api/analyses/{id}``      single, membership-checked
- ``DELETE /api/analyses/{id}``    soft-delete
- ``POST /api/analyses/{id}/restore`` un-soft-delete within 30 days
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import (
    get_active_project_id,
    get_current_user,
    get_optional_user,
    list_member_project_ids,
    require_member,
    require_role,
)
from app.pipelines.claim_detection import DetectionOnlyPipeline, PipelineError
from app.schemas.analysis import (
    AnalysisError,
    AnalysisListItem,
    AnalysisRequest,
    AnalysisResponse,
    StoredAnalysis,
)
from app.schemas.user import CurrentUser
from app.services.analysis_storage import (
    get_analysis,
    list_analyses,
    persist_analysis,
    restore_analysis,
    soft_delete_analysis,
)
from app.services.anthropic_client import AnthropicServiceError
from app.services.claim_detector import ClaimDetector
from app.services.claim_evaluator import ClaimEvaluator
from app.services.project_repo import (
    get_active_project_id as get_db_active_project,
    get_default_project_id,
)
from app.services.retrieval_service import get_retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


# Soft-delete window matches the pg_cron purge job (see migration step 9b).
_RESTORE_WINDOW = timedelta(days=30)


def get_pipeline() -> DetectionOnlyPipeline:
    return DetectionOnlyPipeline(
        detector=ClaimDetector(),
        evaluator=ClaimEvaluator(),
        retriever=get_retrieval_service(),
    )


def _resolve_target_project(
    *,
    current_user: CurrentUser,
    payload_project_id: UUID | None,
    header_project_id: UUID | None,
) -> UUID:
    """Return the project the analysis should land in.

    Precedence: payload > X-Active-Project-Id > profile.active > default.
    Membership is verified in the calling route via ``require_role``.
    """
    candidate = (
        payload_project_id
        or header_project_id
        or get_db_active_project(current_user.id)
        or get_default_project_id(current_user.id)
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "no_project",
                "message": "Kein Default-Projekt gefunden. Bitte erneut einloggen.",
            },
        )
    return candidate


@router.post(
    "",
    response_model=AnalysisResponse,
    responses={
        400: {"model": AnalysisError},
        403: {"model": AnalysisError},
        422: {"model": AnalysisError},
        503: {"model": AnalysisError},
    },
)
async def create_analysis(
    payload: AnalysisRequest,
    pipeline: Annotated[DetectionOnlyPipeline, Depends(get_pipeline)],
    current_user: Annotated[CurrentUser | None, Depends(get_optional_user)] = None,
    header_project_id: Annotated[UUID | None, Depends(get_active_project_id)] = None,
) -> AnalysisResponse:
    try:
        result = await pipeline.run(
            input_text=payload.input_text,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
        )
    except PipelineError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "schema_violation", "message": str(exc)},
        ) from exc

    # Anonymous / demo runs: hand the result back, skip persistence.
    if current_user is None:
        return result

    target_project_id = _resolve_target_project(
        current_user=current_user,
        payload_project_id=payload.project_id,
        header_project_id=header_project_id,
    )
    # Membership + role check: only editors / owners may write.
    require_role(target_project_id, current_user, allowed=("owner", "editor"))

    analysis_id = persist_analysis(
        user_id=current_user.id,
        project_id=target_project_id,
        response=result,
    )
    if analysis_id is None:
        # Persist failed but pipeline succeeded - hand the user their
        # result anyway, surface as a warning so the UI can hint.
        result.warnings = [
            *result.warnings,
            "Diese Analyse konnte nicht im Verlauf gespeichert werden.",
        ]
    else:
        result.analysis_id = analysis_id
        result.project_id = target_project_id
    return result


@router.get(
    "",
    response_model=list[AnalysisListItem],
)
async def list_analyses_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[AnalysisListItem]:
    member_projects = list_member_project_ids(current_user.id)
    if project_id is not None and project_id not in member_projects:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "project_forbidden",
                "message": "Du bist kein Mitglied dieses Projekts.",
            },
        )
    return list_analyses(
        project_id=project_id,
        user_id=current_user.id,
        member_project_ids=member_projects,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{analysis_id}",
    response_model=StoredAnalysis,
    responses={404: {"model": AnalysisError}, 403: {"model": AnalysisError}},
)
async def get_analysis_route(
    analysis_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StoredAnalysis:
    row = get_analysis(analysis_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "analysis_not_found",
                "message": "Analyse nicht gefunden.",
            },
        )
    require_member(row.project_id, current_user)
    return row


@router.delete(
    "/{analysis_id}",
    responses={404: {"model": AnalysisError}, 403: {"model": AnalysisError}},
)
async def delete_analysis_route(
    analysis_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    row = get_analysis(analysis_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "analysis_not_found",
                "message": "Analyse nicht gefunden.",
            },
        )
    require_role(row.project_id, current_user, allowed=("owner", "editor"))
    if not soft_delete_analysis(analysis_id, deleted_at=datetime.now(UTC)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "analysis_not_found",
                "message": "Analyse nicht gefunden oder bereits gelöscht.",
            },
        )
    return {"status": "deleted"}


@router.post(
    "/{analysis_id}/restore",
    response_model=StoredAnalysis,
    responses={404: {"model": AnalysisError}, 403: {"model": AnalysisError}},
)
async def restore_analysis_route(
    analysis_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StoredAnalysis:
    # We need to look up the row WITH the deleted_at filter off; reuse
    # storage call by fetching directly via service-role bypass of the
    # standard ``get_analysis`` (which filters deleted_at IS NULL).
    from app.services.supabase_client import get_supabase
    supabase = get_supabase()
    raw = (
        supabase.table("analyses")
        .select("*")
        .eq("id", str(analysis_id))
        .maybe_single()
        .execute()
    )
    data = getattr(raw, "data", None)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "analysis_not_found",
                "message": "Analyse nicht gefunden.",
            },
        )
    if data.get("deleted_at") is None:
        # Idempotent - already live.
        return StoredAnalysis.model_validate(data)
    deleted_at = datetime.fromisoformat(data["deleted_at"].replace("Z", "+00:00"))
    if datetime.now(UTC) - deleted_at > _RESTORE_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "analysis_not_found",
                "message": "Wiederherstellungsfenster (30 Tage) abgelaufen.",
            },
        )
    require_role(UUID(data["project_id"]), current_user, allowed=("owner", "editor"))
    if not restore_analysis(analysis_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "analysis_not_found",
                "message": "Analyse konnte nicht wiederhergestellt werden.",
            },
        )
    refreshed = get_analysis(analysis_id)
    if refreshed is None:  # pragma: no cover - paranoia
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Wiederherstellung fehlgeschlagen."},
        )
    return refreshed
