"""Endpoint tests for /api/invites (PROJ-22).

Covers the four token-acceptance branches:
- valid match -> 200 accept
- email mismatch -> 403
- expired token -> 404
- revoked -> 404
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.schemas.project import Invite
from app.schemas.user import CurrentUser

client = TestClient(app)


def _user(email: str = "invitee@example.com") -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email=email,
        email_confirmed=True,
        profile=None,
    )


def _invite(
    *,
    status: str = "pending",
    email: str = "invitee@example.com",
    expires_in_days: int = 5,
) -> Invite:
    return Invite(
        id=uuid4(),
        token=uuid4(),
        project_id=uuid4(),
        email=email,
        role="editor",
        status=status,
        invited_by=uuid4(),
        invited_at=datetime.now(UTC) - timedelta(days=1),
        expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
        accepted_at=None,
    )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def test_accept_invite_succeeds_for_matching_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invite = _invite()
    user = _user(email=invite.email)
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        "app.api.invites.project_repo.get_invite_by_token",
        lambda token: invite,
    )
    monkeypatch.setattr(
        "app.api.invites.project_repo.get_member",
        lambda pid, uid: None,
    )
    monkeypatch.setattr(
        "app.api.invites.project_repo.add_member",
        lambda pid, uid, role: True,
    )
    monkeypatch.setattr(
        "app.api.invites.project_repo.accept_invite",
        lambda iid, accepted_at: True,
    )

    response = client.post(f"/api/invites/{invite.token}/accept")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["project_id"] == str(invite.project_id)


def test_accept_invite_email_mismatch_returns_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invite = _invite(email="other@example.com")
    user = _user(email="mismatch@example.com")
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        "app.api.invites.project_repo.get_invite_by_token",
        lambda token: invite,
    )

    response = client.post(f"/api/invites/{invite.token}/accept")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "invite_email_mismatch"


def test_accept_invite_expired_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invite = _invite(expires_in_days=-1)
    user = _user(email=invite.email)
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        "app.api.invites.project_repo.get_invite_by_token",
        lambda token: invite,
    )

    response = client.post(f"/api/invites/{invite.token}/accept")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "invite_not_found"


def test_accept_invite_revoked_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invite = _invite(status="revoked")
    user = _user(email=invite.email)
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        "app.api.invites.project_repo.get_invite_by_token",
        lambda token: invite,
    )

    response = client.post(f"/api/invites/{invite.token}/accept")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "invite_not_found"


def test_accept_invite_already_accepted_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invite = _invite(status="accepted")
    user = _user(email=invite.email)
    app.dependency_overrides[get_current_user] = lambda: user

    monkeypatch.setattr(
        "app.api.invites.project_repo.get_invite_by_token",
        lambda token: invite,
    )

    response = client.post(f"/api/invites/{invite.token}/accept")
    assert response.status_code == 200
    assert response.json()["status"] == "already_accepted"
