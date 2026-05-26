"""Project + Member + Invite endpoints (PROJ-22).

Membership and role enforcement live in ``core.auth``; this module
expresses the higher-level business rules:
- a project must always have at least one owner
- the default project may not be deleted while it's the user's only
- per-user / per-project limits from ``schemas.project``
- invite spam guard (50 / user / 24 h)
"""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import (
    get_current_user,
    require_member,
    require_role,
)
from app.schemas.project import (
    Invite,
    InviteCreate,
    MAX_INVITES_PER_USER_PER_DAY,
    MAX_MEMBERS_PER_PROJECT,
    MAX_PROJECTS_PER_USER,
    Member,
    MemberRoleUpdate,
    ProjectCreate,
    ProjectUpdate,
    ProjectWithMeta,
)
from app.schemas.user import CurrentUser
from app.services import project_repo
from app.services.mailer import send_invite_mail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


# ---------- helpers ------------------------------------------------------


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "project_not_found", "message": "Projekt nicht gefunden."},
    )


# ---------- project CRUD -------------------------------------------------


@router.get("", response_model=list[ProjectWithMeta])
async def list_projects(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ProjectWithMeta]:
    return project_repo.list_projects_for_user(current_user.id)


@router.post("", response_model=ProjectWithMeta, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ProjectWithMeta:
    owned = project_repo.count_projects_owned_by(current_user.id)
    if owned >= MAX_PROJECTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "project_limit_reached",
                "message": (
                    f"Maximal {MAX_PROJECTS_PER_USER} Projekte pro Account."
                ),
            },
        )
    project = project_repo.create_project(
        owner_id=current_user.id,
        name=payload.name,
        color=payload.color,
        is_default=False,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Projekt konnte nicht angelegt werden."},
        )
    return ProjectWithMeta(
        **project.model_dump(),
        role="owner",
        member_count=1,
    )


@router.get("/{project_id}", response_model=ProjectWithMeta)
async def get_project_route(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ProjectWithMeta:
    role = require_member(project_id, current_user)
    project = project_repo.get_project(project_id)
    if project is None:
        raise _not_found()
    member_count = project_repo.count_members(project_id)
    return ProjectWithMeta(
        **project.model_dump(),
        role=role,  # type: ignore[arg-type]
        member_count=member_count,
    )


@router.patch("/{project_id}", response_model=ProjectWithMeta)
async def update_project_route(
    project_id: UUID,
    payload: ProjectUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ProjectWithMeta:
    require_role(project_id, current_user, allowed=("owner",))
    project = project_repo.update_project(
        project_id,
        name=payload.name,
        color=payload.color,
    )
    if project is None:
        raise _not_found()
    return ProjectWithMeta(
        **project.model_dump(),
        role="owner",
        member_count=project_repo.count_members(project_id),
    )


@router.delete("/{project_id}")
async def delete_project_route(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    require_role(project_id, current_user, allowed=("owner",))
    project = project_repo.get_project(project_id)
    if project is None:
        raise _not_found()
    if project.is_default:
        # Default-Projekt nur löschen, wenn der User weitere Projekte hat
        # (Spec: "darf nicht gelöscht werden, solange einziges Projekt").
        owned = project_repo.count_projects_owned_by(current_user.id)
        if owned <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "default_project_protected",
                    "message": "Das Default-Projekt kann nicht gelöscht werden, solange es dein einziges ist.",
                },
            )
    if not project_repo.delete_project(project_id):
        raise _not_found()
    return {"status": "deleted"}


# ---------- members ------------------------------------------------------


@router.get("/{project_id}/members", response_model=list[Member])
async def list_members_route(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[Member]:
    require_member(project_id, current_user)
    return project_repo.list_members(project_id)


@router.put("/{project_id}/members/{user_id}/role", response_model=Member)
async def update_member_role_route(
    project_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Member:
    require_role(project_id, current_user, allowed=("owner",))
    target = project_repo.get_member(project_id, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "member_not_found", "message": "Mitglied nicht gefunden."},
        )
    # Owner-Schutz: einziger Owner darf sich nicht degradieren.
    if (
        target.role == "owner"
        and payload.role != "owner"
        and project_repo.count_owners(project_id) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "last_owner",
                "message": "Du bist der einzige Owner. Promote zuerst jemand anderen.",
            },
        )
    if not project_repo.update_member_role(project_id, user_id, payload.role):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "member_not_found", "message": "Mitglied nicht gefunden."},
        )
    updated = project_repo.get_member(project_id, user_id)
    if updated is None:  # pragma: no cover
        raise HTTPException(500, detail={"code": "internal_error", "message": "Update fehlgeschlagen."})
    return updated


@router.delete("/{project_id}/members/{user_id}")
async def remove_member_route(
    project_id: UUID,
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    # Eigentliche Mitglieder dürfen sich selbst entfernen; Owner dürfen
    # andere entfernen. Owner-Schutz greift weiter unten.
    role = require_member(project_id, current_user)
    is_self_removal = user_id == current_user.id
    if not is_self_removal and role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "project_forbidden",
                "message": "Nur Owner können andere Mitglieder entfernen.",
            },
        )
    target = project_repo.get_member(project_id, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "member_not_found", "message": "Mitglied nicht gefunden."},
        )
    if target.role == "owner" and project_repo.count_owners(project_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "last_owner",
                "message": "Du bist der einzige Owner. Promote zuerst jemand anderen, bevor du gehst.",
            },
        )
    if not project_repo.remove_member(project_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "member_not_found", "message": "Mitglied nicht gefunden."},
        )
    return {"status": "removed"}


# ---------- invites ------------------------------------------------------


@router.get("/{project_id}/invites", response_model=list[Invite])
async def list_invites_route(
    project_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[Invite]:
    require_role(project_id, current_user, allowed=("owner",))
    return project_repo.list_pending_invites(project_id)


@router.post(
    "/{project_id}/invites",
    response_model=Invite,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite_route(
    project_id: UUID,
    payload: InviteCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Invite:
    require_role(project_id, current_user, allowed=("owner",))

    # Rate-Limit Spam-Schutz.
    sent_today = project_repo.count_invites_by_user_last_24h(current_user.id)
    if sent_today >= MAX_INVITES_PER_USER_PER_DAY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "invite_rate_limit",
                "message": "Zu viele Einladungen in den letzten 24 Stunden.",
            },
        )

    # Member-Limit
    member_count = project_repo.count_members(project_id)
    if member_count >= MAX_MEMBERS_PER_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "member_limit_reached",
                "message": f"Maximal {MAX_MEMBERS_PER_PROJECT} Mitglieder pro Projekt.",
            },
        )

    email_lc = payload.email.lower()
    # Existing pending invite -> reuse.
    existing = project_repo.find_pending_invite(project_id, email_lc)
    if existing is not None:
        return existing

    invite = project_repo.create_invite(
        project_id=project_id,
        email=email_lc,
        role=payload.role,
        invited_by=current_user.id,
    )
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Einladung konnte nicht erstellt werden."},
        )

    project = project_repo.get_project(project_id)
    inviter_name = (
        current_user.profile.display_name if current_user.profile and current_user.profile.display_name
        else current_user.email
    )
    sent = send_invite_mail(
        to=email_lc,
        project_name=project.name if project else "ClaimGuard-Projekt",
        inviter_name=inviter_name,
        role=payload.role,
        token=str(invite.token),
    )
    if not sent:
        # Don't fail the invite - the link in the UI is still usable.
        logger.warning("Invite created but mail send failed for %s", email_lc)
    return invite


@router.delete("/{project_id}/invites/{invite_id}")
async def revoke_invite_route(
    project_id: UUID,
    invite_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, str]:
    require_role(project_id, current_user, allowed=("owner",))
    if not project_repo.revoke_invite(invite_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "invite_not_found", "message": "Einladung nicht gefunden."},
        )
    return {"status": "revoked"}
