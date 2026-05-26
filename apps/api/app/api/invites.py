"""Public invite endpoints (PROJ-22).

Separate from ``/api/projects`` because of different auth semantics:
- ``GET /api/invites/{token}`` works WITHOUT a logged-in user (it powers
  the public ``/invite/[token]`` landing page).
- ``POST /api/invites/{token}/accept`` requires a logged-in user whose
  email matches the invite.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.schemas.project import InvitePublic
from app.schemas.user import CurrentUser
from app.services import project_repo
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invites", tags=["invites"])


def _invite_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "invite_not_found",
            "message": "Einladung nicht gefunden oder abgelaufen.",
        },
    )


@router.get("/{token}", response_model=InvitePublic)
async def get_invite(token: UUID) -> InvitePublic:
    invite = project_repo.get_invite_by_token(token)
    if invite is None:
        raise _invite_not_found()
    # Sanity: hide accepted/revoked invites behind the same 404 so a
    # leaked token can't enumerate state.
    if invite.status in ("revoked", "expired"):
        raise _invite_not_found()

    project = project_repo.get_project(invite.project_id)
    if project is None:
        raise _invite_not_found()

    # Resolve inviter info best-effort.
    inviter_email = ""
    inviter_display_name = None
    if invite.invited_by:
        try:
            supabase = get_supabase()
            admin = supabase.auth.admin
            user_resp = admin.get_user_by_id(str(invite.invited_by))
            user_obj = getattr(user_resp, "user", None)
            if user_obj is not None:
                inviter_email = getattr(user_obj, "email", "") or ""
            profile = (
                supabase.table("profiles")
                .select("display_name")
                .eq("id", str(invite.invited_by))
                .maybe_single()
                .execute()
            )
            data = getattr(profile, "data", None)
            if data:
                inviter_display_name = data.get("display_name")
        except Exception as exc:  # pragma: no cover - resolution is best-effort
            logger.warning("inviter lookup failed: %s", exc)

    return InvitePublic(
        project_name=project.name,
        project_color=project.color,
        inviter_display_name=inviter_display_name,
        inviter_email=inviter_email or "noreply@claim-guard.de",
        role=invite.role,
        status=invite.status,
        expires_at=invite.expires_at,
    )


@router.post("/{token}/accept")
async def accept_invite(
    token: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str | UUID]:
    invite = project_repo.get_invite_by_token(token)
    if invite is None:
        raise _invite_not_found()

    # Idempotent: token already redeemed.
    if invite.status == "accepted":
        return {"status": "already_accepted", "project_id": invite.project_id}

    if invite.status in ("revoked", "expired"):
        raise _invite_not_found()

    if invite.expires_at < datetime.now(UTC):
        raise _invite_not_found()

    # Email-match check (case-insensitive).
    if current_user.email.lower() != invite.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "invite_email_mismatch",
                "message": "Diese Einladung ist nicht für dein Konto bestimmt.",
            },
        )

    # Member-Schutz: schon Mitglied?
    existing = project_repo.get_member(invite.project_id, current_user.id)
    if existing is None:
        added = project_repo.add_member(
            invite.project_id,
            current_user.id,
            invite.role,
        )
        if not added:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "internal_error",
                    "message": "Mitgliedschaft konnte nicht angelegt werden.",
                },
            )

    project_repo.accept_invite(invite.id, accepted_at=datetime.now(UTC))
    return {"status": "accepted", "project_id": invite.project_id}
