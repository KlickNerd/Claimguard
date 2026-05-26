"""Endpoints scoped to the current user's profile (PROJ-1 + PROJ-22).

Currently only ``POST /api/me/active-project`` which persists the
active-project pick so it survives across devices (see PROJ-22 Tech
Design 'Aktive-Projekt-Synchronisation').
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user, require_member
from app.schemas.user import CurrentUser
from app.services import project_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/me", tags=["me"])


class ActiveProjectPayload(BaseModel):
    project_id: UUID


@router.post("/active-project")
async def set_active_project_route(
    payload: ActiveProjectPayload,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    require_member(payload.project_id, current_user)
    if not project_repo.set_active_project(current_user.id, payload.project_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "internal_error",
                "message": "Aktives Projekt konnte nicht gespeichert werden.",
            },
        )
    return {"status": "ok"}


@router.get("/active-project")
async def get_active_project_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str | None]:
    active = project_repo.get_active_project_id(current_user.id)
    if active is None:
        active = project_repo.get_default_project_id(current_user.id)
    return {"project_id": str(active) if active else None}
