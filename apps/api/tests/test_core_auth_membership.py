"""Tests for the PROJ-22 membership helpers added to ``core.auth``.

These functions wrap ``project_members`` lookups. We stub the Supabase
client so tests run without a live DB.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core import auth as auth_module
from app.schemas.user import CurrentUser


def _user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="user@example.com",
        email_confirmed=True,
        profile=None,
    )


class _MembershipQuery:
    """Minimal stand-in for the supabase-py query builder used in
    ``_fetch_membership``."""

    def __init__(self, role: str | None) -> None:
        self._role = role

    def select(self, *_args: Any) -> _MembershipQuery:
        return self

    def eq(self, *_args: Any) -> _MembershipQuery:
        return self

    def maybe_single(self) -> _MembershipQuery:
        return self

    def execute(self) -> Any:
        class _Resp:
            pass

        resp = _Resp()
        resp.data = {"role": self._role} if self._role else None
        return resp


class _StubSupabase:
    def __init__(self, role: str | None) -> None:
        self._role = role

    def table(self, _name: str) -> _MembershipQuery:
        return _MembershipQuery(self._role)


def test_require_member_returns_role_when_present() -> None:
    user = _user()
    project_id = uuid4()
    with patch.object(auth_module, "get_supabase", return_value=_StubSupabase("editor")):
        role = auth_module.require_member(project_id, user)
    assert role == "editor"


def test_require_member_raises_403_when_not_member() -> None:
    user = _user()
    project_id = uuid4()
    with patch.object(auth_module, "get_supabase", return_value=_StubSupabase(None)):
        with pytest.raises(HTTPException) as exc_info:
            auth_module.require_member(project_id, user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "project_forbidden"


def test_require_role_passes_when_allowed() -> None:
    user = _user()
    project_id = uuid4()
    with patch.object(auth_module, "get_supabase", return_value=_StubSupabase("owner")):
        role = auth_module.require_role(project_id, user, allowed=("owner",))
    assert role == "owner"


def test_require_role_rejects_when_role_not_allowed() -> None:
    user = _user()
    project_id = uuid4()
    with patch.object(auth_module, "get_supabase", return_value=_StubSupabase("viewer")):
        with pytest.raises(HTTPException) as exc_info:
            auth_module.require_role(
                project_id,
                user,
                allowed=("owner", "editor"),
            )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_active_project_id_parses_valid_uuid() -> None:
    token = uuid4()
    result = await auth_module.get_active_project_id(x_active_project_id=str(token))
    assert result == token


@pytest.mark.asyncio
async def test_get_active_project_id_returns_none_for_garbage() -> None:
    result = await auth_module.get_active_project_id(x_active_project_id="not-a-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_get_active_project_id_returns_none_for_missing_header() -> None:
    result = await auth_module.get_active_project_id(x_active_project_id=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_without_authorization() -> None:
    result = await auth_module.get_optional_user(authorization=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_user_swallows_auth_failure() -> None:
    async def _raising_get_current_user(authorization: str | None = None) -> CurrentUser:
        raise HTTPException(status_code=401, detail="nope")

    with patch.object(auth_module, "get_current_user", _raising_get_current_user):
        result = await auth_module.get_optional_user(authorization="Bearer broken")
    assert result is None
