"""Supabase-Wrapper for projects / project_members / project_invites.

Authorisation lives in ``core.auth`` (``require_member``, ``require_role``);
this module only translates between Pydantic and the DB. All calls use
the service-role client and bypass RLS; the caller must have verified
the principal's right to perform the operation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.project import (
    Invite,
    InviteRole,
    Member,
    Project,
    ProjectColor,
    ProjectWithMeta,
    Role,
)
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# ---------- projects -----------------------------------------------------


def list_projects_for_user(user_id: UUID) -> list[ProjectWithMeta]:
    """All projects the user is a member of, with role + member_count."""
    try:
        supabase = get_supabase()
        memberships = (
            supabase.table("project_members")
            .select("project_id, role")
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("list_projects: membership lookup failed: %s", exc)
        return []
    rows = getattr(memberships, "data", None) or []
    if not rows:
        return []
    project_ids = [r["project_id"] for r in rows]
    roles: dict[str, str] = {r["project_id"]: r["role"] for r in rows}

    try:
        projects_result = (
            supabase.table("projects")
            .select("*")
            .in_("id", project_ids)
            .execute()
        )
        # Aggregate member_count via a second cheap query.
        counts_result = (
            supabase.table("project_members")
            .select("project_id", count="exact")
            .in_("project_id", project_ids)
            .execute()
        )
    except Exception as exc:
        logger.warning("list_projects: project fetch failed: %s", exc)
        return []

    member_count_map: dict[str, int] = {}
    for row in getattr(counts_result, "data", None) or []:
        pid = row["project_id"]
        member_count_map[pid] = member_count_map.get(pid, 0) + 1

    out: list[ProjectWithMeta] = []
    for project in getattr(projects_result, "data", None) or []:
        pid = project["id"]
        out.append(
            ProjectWithMeta(
                **project,
                role=roles[pid],  # type: ignore[arg-type]
                member_count=member_count_map.get(pid, 1),
            ),
        )
    # Default project first, then alphabetical.
    out.sort(key=lambda p: (not p.is_default, p.name.lower()))
    return out


def get_project(project_id: UUID) -> Project | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("get_project failed for %s: %s", project_id, exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return Project.model_validate(data)


def create_project(
    *,
    owner_id: UUID,
    name: str,
    color: ProjectColor,
    is_default: bool = False,
) -> Project | None:
    try:
        supabase = get_supabase()
        project_result = (
            supabase.table("projects")
            .insert({"name": name, "color": color, "is_default": is_default})
            .execute()
        )
        inserted = (getattr(project_result, "data", None) or [None])[0]
        if not inserted:
            return None
        # Owner-Mitgliedschaft anlegen (best effort, der Trigger erledigt
        # das fuer Default-Projekte schon, aber bei manuellen Anlagen
        # muessen wir es selber tun).
        supabase.table("project_members").insert(
            {
                "project_id": inserted["id"],
                "user_id": str(owner_id),
                "role": "owner",
            },
        ).execute()
        return Project.model_validate(inserted)
    except Exception as exc:
        logger.error("create_project failed: %s", exc)
        return None


def update_project(
    project_id: UUID,
    *,
    name: str | None = None,
    color: ProjectColor | None = None,
) -> Project | None:
    patch: dict[str, Any] = {}
    if name is not None:
        patch["name"] = name
    if color is not None:
        patch["color"] = color
    if not patch:
        return get_project(project_id)
    try:
        supabase = get_supabase()
        result = (
            supabase.table("projects")
            .update(patch)
            .eq("id", str(project_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("update_project failed for %s: %s", project_id, exc)
        return None
    rows = getattr(result, "data", None) or []
    if not rows:
        return None
    return Project.model_validate(rows[0])


def delete_project(project_id: UUID) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("projects")
            .delete()
            .eq("id", str(project_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("delete_project failed for %s: %s", project_id, exc)
        return False
    return bool(getattr(result, "data", None))


def count_projects_owned_by(user_id: UUID) -> int:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("project_id", count="exact")
            .eq("user_id", str(user_id))
            .eq("role", "owner")
            .execute()
        )
    except Exception as exc:
        logger.warning("count_projects_owned_by failed for %s: %s", user_id, exc)
        return 0
    return getattr(result, "count", 0) or 0


# ---------- members ------------------------------------------------------


def list_members(project_id: UUID) -> list[Member]:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("project_id, user_id, role, joined_at")
            .eq("project_id", str(project_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("list_members failed for %s: %s", project_id, exc)
        return []
    rows = getattr(result, "data", None) or []
    if not rows:
        return []

    user_ids = [r["user_id"] for r in rows]
    emails = _lookup_emails(user_ids)
    display_names = _lookup_display_names(user_ids)

    members: list[Member] = []
    for row in rows:
        uid = row["user_id"]
        members.append(
            Member(
                project_id=row["project_id"],
                user_id=uid,
                role=row["role"],
                joined_at=row["joined_at"],
                email=emails.get(uid),
                display_name=display_names.get(uid),
            ),
        )
    return members


def get_member(project_id: UUID, user_id: UUID) -> Member | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("get_member failed: %s", exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return Member.model_validate(data)


def add_member(project_id: UUID, user_id: UUID, role: Role) -> bool:
    try:
        supabase = get_supabase()
        supabase.table("project_members").insert(
            {
                "project_id": str(project_id),
                "user_id": str(user_id),
                "role": role,
            },
        ).execute()
        return True
    except Exception as exc:
        logger.warning("add_member failed: %s", exc)
        return False


def update_member_role(project_id: UUID, user_id: UUID, role: Role) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .update({"role": role})
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("update_member_role failed: %s", exc)
        return False
    return bool(getattr(result, "data", None))


def remove_member(project_id: UUID, user_id: UUID) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .delete()
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("remove_member failed: %s", exc)
        return False
    return bool(getattr(result, "data", None))


def count_members(project_id: UUID) -> int:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("user_id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("count_members failed: %s", exc)
        return 0
    return getattr(result, "count", 0) or 0


def count_owners(project_id: UUID) -> int:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("user_id", count="exact")
            .eq("project_id", str(project_id))
            .eq("role", "owner")
            .execute()
        )
    except Exception as exc:
        logger.warning("count_owners failed: %s", exc)
        return 0
    return getattr(result, "count", 0) or 0


# ---------- invites ------------------------------------------------------


def list_pending_invites(project_id: UUID) -> list[Invite]:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .order("invited_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.warning("list_pending_invites failed: %s", exc)
        return []
    rows = getattr(result, "data", None) or []
    return [Invite.model_validate(row) for row in rows]


def get_invite_by_token(token: UUID) -> Invite | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .select("*")
            .eq("token", str(token))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("get_invite_by_token failed: %s", exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return Invite.model_validate(data)


def find_pending_invite(project_id: UUID, email: str) -> Invite | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("email", email.lower())
            .eq("status", "pending")
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("find_pending_invite failed: %s", exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return Invite.model_validate(data)


def create_invite(
    *,
    project_id: UUID,
    email: str,
    role: InviteRole,
    invited_by: UUID,
) -> Invite | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .insert(
                {
                    "project_id": str(project_id),
                    "email": email.lower(),
                    "role": role,
                    "invited_by": str(invited_by),
                },
            )
            .execute()
        )
    except Exception as exc:
        logger.warning("create_invite failed: %s", exc)
        return None
    rows = getattr(result, "data", None) or []
    if not rows:
        return None
    return Invite.model_validate(rows[0])


def accept_invite(invite_id: UUID, *, accepted_at: datetime) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .update(
                {
                    "status": "accepted",
                    "accepted_at": accepted_at.isoformat(),
                },
            )
            .eq("id", str(invite_id))
            .eq("status", "pending")
            .execute()
        )
    except Exception as exc:
        logger.warning("accept_invite failed: %s", exc)
        return False
    return bool(getattr(result, "data", None))


def revoke_invite(invite_id: UUID) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_invites")
            .update({"status": "revoked"})
            .eq("id", str(invite_id))
            .eq("status", "pending")
            .execute()
        )
    except Exception as exc:
        logger.warning("revoke_invite failed: %s", exc)
        return False
    return bool(getattr(result, "data", None))


def count_invites_by_user_last_24h(user_id: UUID) -> int:
    try:
        supabase = get_supabase()
        from datetime import UTC, datetime, timedelta
        since = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        result = (
            supabase.table("project_invites")
            .select("id", count="exact")
            .eq("invited_by", str(user_id))
            .gte("invited_at", since)
            .execute()
        )
    except Exception as exc:
        logger.warning("count_invites_by_user_last_24h failed: %s", exc)
        return 0
    return getattr(result, "count", 0) or 0


# ---------- profile active_project ---------------------------------------


def set_active_project(user_id: UUID, project_id: UUID | None) -> bool:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("profiles")
            .update({"active_project_id": str(project_id) if project_id else None})
            .eq("id", str(user_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("set_active_project failed: %s", exc)
        return False
    return bool(getattr(result, "data", None))


def get_active_project_id(user_id: UUID) -> UUID | None:
    try:
        supabase = get_supabase()
        result = (
            supabase.table("profiles")
            .select("active_project_id")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("get_active_project_id failed: %s", exc)
        return None
    data = getattr(result, "data", None) or {}
    pid = data.get("active_project_id")
    return UUID(pid) if pid else None


def get_default_project_id(user_id: UUID) -> UUID | None:
    """The user's `is_default=true` project, if any."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("project_id, projects!inner(is_default)")
            .eq("user_id", str(user_id))
            .eq("projects.is_default", True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("get_default_project_id failed: %s", exc)
        return None
    rows = getattr(result, "data", None) or []
    if not rows:
        return None
    return UUID(rows[0]["project_id"])


# ---------- helpers ------------------------------------------------------


def _lookup_emails(user_ids: list[str]) -> dict[str, str]:
    """Resolve user_id -> email via auth.users (service role can read it)."""
    if not user_ids:
        return {}
    try:
        supabase = get_supabase()
        out: dict[str, str] = {}
        # supabase-py auth admin API: list_users with pagination.
        # For MVP project sizes (<=10 members), one round-trip per
        # listed-id is fine, but list-and-filter is cheaper.
        result = supabase.auth.admin.list_users()
        for user in getattr(result, "users", []) or []:
            uid = str(getattr(user, "id", ""))
            email = getattr(user, "email", None)
            if uid in user_ids and email:
                out[uid] = email
        return out
    except Exception as exc:
        logger.warning("email lookup failed: %s", exc)
        return {}


def _lookup_display_names(user_ids: list[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    try:
        supabase = get_supabase()
        result = (
            supabase.table("profiles")
            .select("id, display_name")
            .in_("id", user_ids)
            .execute()
        )
    except Exception as exc:
        logger.warning("display_name lookup failed: %s", exc)
        return {}
    rows = getattr(result, "data", None) or []
    return {row["id"]: row["display_name"] for row in rows if row.get("display_name")}
