"""Tests for the ``get_current_user`` FastAPI dependency.

Mocks Supabase via ``app.dependency_overrides`` so we never need a real
Auth server in CI. Each test wires a tiny FastAPI app with one endpoint
that just echoes the resolved ``CurrentUser``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from unittest.mock import patch
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.schemas.user import CurrentUser, Profile

# ---------- helpers --------------------------------------------------------

def _make_app() -> FastAPI:
    """Tiny app with a single ``/protected`` endpoint behind the dependency."""
    app = FastAPI()

    @app.get("/protected")
    def protected(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "email": user.email,
            "has_profile": user.profile is not None,
        }

    return app


class _StubAuth:
    """Mimics the ``supabase.auth.get_user`` return shape."""

    def __init__(self, user: Any) -> None:
        self._user = user
        self.last_token: str | None = None

    def get_user(self, jwt: str) -> Any:
        self.last_token = jwt
        if self._user is None:
            raise RuntimeError("invalid token")

        class _Resp:
            pass

        resp = _Resp()
        resp.user = self._user
        return resp


class _StubTable:
    """Mimics the supabase-py query builder for ``profiles``."""

    def __init__(self, profile_row: dict[str, Any] | None) -> None:
        self._row = profile_row

    def select(self, *_: Any, **__: Any) -> _StubTable:
        return self

    def eq(self, *_: Any, **__: Any) -> _StubTable:
        return self

    def maybe_single(self) -> _StubTable:
        return self

    def execute(self) -> Any:
        class _Resp:
            pass

        resp = _Resp()
        resp.data = self._row
        return resp


class _StubSupabase:
    def __init__(self, *, user: Any, profile_row: dict[str, Any] | None) -> None:
        self.auth = _StubAuth(user)
        self._profile_row = profile_row

    def table(self, name: str) -> _StubTable:
        assert name == "profiles"
        return _StubTable(self._profile_row)


def _make_user(email: str = "julia@apothera.de") -> Any:
    class _User:
        pass

    u = _User()
    u.id = uuid4()
    u.email = email
    u.email_confirmed_at = "2026-05-01T10:00:00+00:00"
    return u


def _make_profile_row(user_id: str) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "id": user_id,
        "display_name": "Julia",
        "avatar_url": None,
        "onboarding_completed": True,
        "created_at": now,
        "updated_at": now,
    }


# ---------- tests ----------------------------------------------------------

def test_returns_current_user_with_profile() -> None:
    user = _make_user()
    profile_row = _make_profile_row(str(user.id))
    stub = _StubSupabase(user=user, profile_row=profile_row)

    with patch("app.core.auth.get_supabase", return_value=stub):
        app = _make_app()
        client = TestClient(app)
        r = client.get(
            "/protected",
            headers={"Authorization": "Bearer some.jwt.token"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "julia@apothera.de"
    assert body["id"] == str(user.id)
    assert body["has_profile"] is True
    assert stub.auth.last_token == "some.jwt.token"


def test_returns_user_without_profile_if_lookup_fails() -> None:
    """Profile lookup is best-effort - missing profile yields ``profile=None``."""
    user = _make_user()
    stub = _StubSupabase(user=user, profile_row=None)

    with patch("app.core.auth.get_supabase", return_value=stub):
        app = _make_app()
        client = TestClient(app)
        r = client.get(
            "/protected",
            headers={"Authorization": "Bearer some.jwt.token"},
        )
    assert r.status_code == 200
    assert r.json()["has_profile"] is False


def test_missing_authorization_header_returns_401() -> None:
    app = _make_app()
    client = TestClient(app)
    r = client.get("/protected")
    assert r.status_code == 401
    body = r.json()
    assert body["detail"]["code"] == "unauthenticated"


def test_malformed_authorization_header_returns_401() -> None:
    app = _make_app()
    client = TestClient(app)
    for bad in ["Basic abc", "Bearer", "Bearer  ", "bearerabc"]:
        r = client.get("/protected", headers={"Authorization": bad})
        assert r.status_code == 401, f"expected 401 for {bad!r}, got {r.status_code}"


def test_invalid_jwt_returns_401() -> None:
    stub = _StubSupabase(user=None, profile_row=None)  # raises on get_user
    with patch("app.core.auth.get_supabase", return_value=stub):
        app = _make_app()
        client = TestClient(app)
        r = client.get(
            "/protected",
            headers={"Authorization": "Bearer fake.bad.token"},
        )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "unauthenticated"


def test_user_without_email_rejected() -> None:
    user = _make_user(email="")
    user.email = None  # type: ignore[assignment]
    stub = _StubSupabase(user=user, profile_row=None)
    with patch("app.core.auth.get_supabase", return_value=stub):
        app = _make_app()
        client = TestClient(app)
        r = client.get(
            "/protected",
            headers={"Authorization": "Bearer some.jwt.token"},
        )
    assert r.status_code == 401


def test_supabase_unconfigured_returns_503() -> None:
    """If env is missing, surface a 503 instead of crashing the request."""
    from app.services.supabase_client import SupabaseNotConfiguredError

    def _raise() -> None:
        raise SupabaseNotConfiguredError("not configured")

    with patch("app.core.auth.get_supabase", side_effect=_raise):
        app = _make_app()
        client = TestClient(app)
        r = client.get(
            "/protected",
            headers={"Authorization": "Bearer some.jwt.token"},
        )
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "auth_unavailable"


def test_profile_model_validates_round_trip() -> None:
    """``Profile`` model accepts the row shape returned by Supabase."""
    row = _make_profile_row(str(uuid4()))
    profile = Profile.model_validate(row)
    assert profile.onboarding_completed is True
    assert profile.display_name == "Julia"
