"""Supabase-Wrapper for the ``public.analyses`` table (PROJ-21).

All reads / writes go through the service-role client. Authorisation is
*not* done here - the calling endpoint is expected to have verified
membership in the target project via ``core.auth.require_member``.
This module just translates between Pydantic and the DB.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.analysis import (
    AnalysisListItem,
    AnalysisResponse,
    StoredAnalysis,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


_LIST_PREVIEW_LIMIT = 120
_LIST_DEFAULT_LIMIT = 20
_LIST_MAX_LIMIT = 100


def _aggregate_risk(evaluated_claims: list[dict[str, Any]]) -> float | None:
    """0-1 score derived from per-claim risk_level. ``None`` if no claims."""
    if not evaluated_claims:
        return None
    weights = {"low": 0.2, "medium": 0.55, "high": 0.9}
    scores = [
        weights.get(claim.get("risk_level", "low"), 0.2)
        for claim in evaluated_claims
    ]
    return sum(scores) / len(scores)


def _preview(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= _LIST_PREVIEW_LIMIT:
        return cleaned
    return cleaned[: _LIST_PREVIEW_LIMIT - 1].rstrip() + "…"


def persist_analysis(
    *,
    user_id: UUID,
    project_id: UUID,
    response: AnalysisResponse,
) -> UUID | None:
    """Write a completed analysis to the DB and return its row id.

    Never raises - on failure we log and return ``None`` so the caller
    can still hand the user their result (Acceptance Criterion: pipeline
    success must not depend on storage success).
    """
    try:
        supabase = get_supabase()
        row = {
            "user_id": str(user_id),
            "project_id": str(project_id),
            "source_type": response.source_type,
            "source_reference": response.source_reference,
            "input_text": response.input_text,
            "detected_claims": [c.model_dump(mode="json") for c in response.detected_claims],
            "evaluated_claims": [c.model_dump(mode="json") for c in response.evaluated_claims],
            "warnings": response.warnings,
            "prompt_version": response.prompt_version,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "estimated_cost_usd": response.estimated_cost_usd,
            "latency_ms": response.latency_ms,
        }
        result = (
            supabase.table("analyses")
            .insert(row)
            .execute()
        )
        inserted = (getattr(result, "data", None) or [None])[0]
        if not inserted:
            logger.warning("analyses insert returned no data")
            return None
        return UUID(str(inserted["id"]))
    except Exception as exc:  # pragma: no cover - storage is best-effort
        logger.warning("Failed to persist analysis: %s", exc)
        return None


def get_analysis(analysis_id: UUID) -> StoredAnalysis | None:
    """Load a single (non-soft-deleted) analysis. Membership check is the
    caller's job.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("analyses")
            .select("*")
            .eq("id", str(analysis_id))
            .is_("deleted_at", "null")
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("get_analysis failed for %s: %s", analysis_id, exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return StoredAnalysis.model_validate(data)


def list_analyses(
    *,
    project_id: UUID | None,
    user_id: UUID,
    member_project_ids: list[UUID],
    limit: int = _LIST_DEFAULT_LIMIT,
    offset: int = 0,
) -> list[AnalysisListItem]:
    """List analyses for the History page.

    Either scoped to a single ``project_id`` (must be in
    ``member_project_ids``) or, when ``project_id`` is None, across all
    projects the user is a member of.
    """
    if limit > _LIST_MAX_LIMIT:
        limit = _LIST_MAX_LIMIT
    if limit < 1:
        limit = _LIST_DEFAULT_LIMIT
    if offset < 0:
        offset = 0

    if project_id is not None and project_id not in member_project_ids:
        # Hidden membership check - caller may have skipped it.
        return []

    target_projects = (
        [project_id] if project_id is not None else member_project_ids
    )
    if not target_projects:
        return []

    try:
        supabase = get_supabase()
        result = (
            supabase.table("analyses")
            .select(
                "id, project_id, source_type, source_reference, "
                "input_text, evaluated_claims, created_at"
            )
            .in_("project_id", [str(p) for p in target_projects])
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as exc:
        logger.warning("list_analyses failed for user %s: %s", user_id, exc)
        return []

    rows = getattr(result, "data", None) or []
    items: list[AnalysisListItem] = []
    for row in rows:
        items.append(
            AnalysisListItem(
                id=row["id"],
                project_id=row["project_id"],
                source_type=row["source_type"],
                source_reference=row.get("source_reference"),
                input_text_preview=_preview(row.get("input_text") or ""),
                risk_score=_aggregate_risk(row.get("evaluated_claims") or []),
                created_at=row["created_at"],
            ),
        )
    return items


def soft_delete_analysis(analysis_id: UUID, *, deleted_at: datetime) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("analyses")
            .update({"deleted_at": deleted_at.isoformat()})
            .eq("id", str(analysis_id))
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        logger.warning("soft_delete_analysis failed for %s: %s", analysis_id, exc)
        return False
    rows = getattr(result, "data", None) or []
    return len(rows) > 0


def restore_analysis(analysis_id: UUID) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("analyses")
            .update({"deleted_at": None})
            .eq("id", str(analysis_id))
            .not_.is_("deleted_at", "null")
            .execute()
        )
    except Exception as exc:
        logger.warning("restore_analysis failed for %s: %s", analysis_id, exc)
        return False
    rows = getattr(result, "data", None) or []
    return len(rows) > 0
