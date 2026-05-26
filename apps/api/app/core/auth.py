"""FastAPI dependency that authenticates a request and returns the user.

Pattern: pull the Bearer token from the ``Authorization`` header, ask
Supabase to validate it via ``auth.get_user(jwt)``, then load the
matching ``profiles`` row. The endpoint that needs auth declares
``Depends(get_current_user)`` and receives a :class:`CurrentUser`.

Why not local JWT verification (faster, no roundtrip)?
We could verify the JWT signature locally with the Supabase JWT secret,
but that needs another env var to wire up and gives us less safety on
revoked sessions. ``auth.get_user`` adds ~30-80 ms per call and lets
Supabase revoke a session instantly (e.g. after a password change).
At MVP traffic the roundtrip is comfortably within budget; if it
becomes a hotspot, swap in local verification + a short Redis cache
on (jwt -> user) lookups.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from pydantic import ValidationError

from app.schemas.user import CurrentUser, Profile
from app.services.supabase_client import (
    SupabaseNotConfiguredError,
    get_supabase,
)

logger = logging.getLogger(__name__)


_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "unauthenticated", "message": "Bitte einloggen."},
    headers={"WWW-Authenticate": "Bearer"},
)


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise _UNAUTHENTICATED
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise _UNAUTHENTICATED
    token = parts[1].strip()
    if not token:
        raise _UNAUTHENTICATED
    return token


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Resolve the request's JWT to a :class:`CurrentUser`.

    Raises 401 on missing/invalid token. Profile lookup failures are
    not fatal - the endpoint still receives a ``CurrentUser`` with
    ``profile=None`` so it can at least know who the request is from.
    The :func:`require_profile` helper can be layered on top when the
    endpoint actually needs the profile row.
    """
    token = _extract_bearer(authorization)

    try:
        supabase = get_supabase()
    except SupabaseNotConfiguredError as exc:
        logger.error("Supabase client unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "auth_unavailable",
                "message": "Auth-Service ist gerade nicht erreichbar.",
            },
        ) from exc

    try:
        response = supabase.auth.get_user(token)
    except Exception as exc:  # gotrue raises a handful of error subclasses
        logger.info("JWT validation failed: %s", exc)
        raise _UNAUTHENTICATED from exc

    if response is None or getattr(response, "user", None) is None:
        raise _UNAUTHENTICATED

    user = response.user
    email = getattr(user, "email", None)
    if not email:
        # Supabase always returns email for password/OAuth users; if
        # missing, something is off (anonymous user?) and we refuse.
        raise _UNAUTHENTICATED

    profile = _load_profile(user.id)

    try:
        return CurrentUser(
            id=user.id,
            email=email,
            email_confirmed=getattr(user, "email_confirmed_at", None) is not None,
            profile=profile,
        )
    except ValidationError as exc:
        logger.warning("Failed to build CurrentUser: %s", exc)
        raise _UNAUTHENTICATED from exc


def _load_profile(user_id: str) -> Profile | None:
    """Best-effort profile lookup. ``None`` on failure - non-fatal."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("profiles")
            .select("*")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("Profile lookup failed for %s: %s", user_id, exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        logger.warning("Profile row failed validation for %s: %s", user_id, exc)
        return None


def require_profile(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """Stricter variant: refuses requests where the profile row is missing.

    Used by endpoints that need profile-driven data (plan, onboarding
    state, etc.). Most endpoints only need ``get_current_user``.
    """
    if current_user.profile is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "profile_missing",
                "message": "Profil ist noch nicht angelegt. Bitte Logout/Login.",
            },
        )
    return current_user


# ---------- PROJ-22 membership helpers -----------------------------------

from uuid import UUID  # noqa: E402

from app.schemas.project import Role  # noqa: E402


_PROJECT_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={
        "code": "project_forbidden",
        "message": "Du bist kein Mitglied dieses Projekts.",
    },
)


def _fetch_membership(project_id: UUID, user_id: UUID) -> str | None:
    """Return the user's role in the project or ``None`` if not a member."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("role")
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        logger.warning("membership lookup failed: %s", exc)
        return None
    data = getattr(result, "data", None)
    if not data:
        return None
    return data.get("role")


def list_member_project_ids(user_id: UUID) -> list[UUID]:
    """All project_ids the user is a member of."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("project_members")
            .select("project_id")
            .eq("user_id", str(user_id))
            .execute()
        )
    except Exception as exc:
        logger.warning("list_member_project_ids failed: %s", exc)
        return []
    rows = getattr(result, "data", None) or []
    return [UUID(row["project_id"]) for row in rows]


def require_member(project_id: UUID, current_user: CurrentUser) -> str:
    """Raise 403 unless the user is a member of ``project_id``.

    Returns the user's role for downstream role-gating without a second
    query.
    """
    role = _fetch_membership(project_id, current_user.id)
    if role is None:
        raise _PROJECT_FORBIDDEN
    return role


def require_role(
    project_id: UUID,
    current_user: CurrentUser,
    *,
    allowed: tuple[Role, ...],
) -> str:
    """Stricter than :func:`require_member` - role must be in ``allowed``."""
    role = require_member(project_id, current_user)
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "project_forbidden",
                "message": "Deine Rolle erlaubt diese Aktion nicht.",
            },
        )
    return role


async def get_active_project_id(
    x_active_project_id: Annotated[str | None, Header()] = None,
) -> UUID | None:
    """Parse the ``X-Active-Project-Id`` header, if present and valid."""
    if not x_active_project_id:
        return None
    try:
        return UUID(x_active_project_id)
    except (ValueError, AttributeError):
        return None


async def get_optional_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser | None:
    """Like ``get_current_user`` but returns ``None`` for anonymous calls.

    Used by endpoints that work for both demo (Landing-Widget) and
    authenticated app traffic - e.g. ``POST /api/analyses`` runs the
    pipeline either way and only persists when a user is present.
    """
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization)
    except HTTPException:
        return None
