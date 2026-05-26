"""Endpoint tests for /api/projects (PROJ-22).

We mock auth (get_current_user) and the project_repo service so the
tests run without a live Supabase. Each test sets up the exact stubs
it needs and tears them down via the autouse fixture.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import projects as projects_module
from app.core.auth import get_current_user
from app.main import app
from app.schemas.project import (
    Invite,
    Member,
    Project,
    ProjectWithMeta,
)
from app.schemas.user import CurrentUser

client = TestClient(app)


# ---------- fixtures -----------------------------------------------------


def _user() -> CurrentUser:
    return CurrentUser(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email="owner@example.com",
        email_confirmed=True,
        profile=None,
    )


def _project(name: str = "Demo", is_default: bool = False) -> Project:
    return Project(
        id=uuid4(),
        name=name,
        color="indigo",
        is_default=is_default,
        created_at="2026-05-25T10:00:00Z",
        updated_at="2026-05-25T10:00:00Z",
    )


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    """Reset all DI overrides between tests."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def authed_owner(monkeypatch: pytest.MonkeyPatch) -> CurrentUser:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user
    # require_member / require_role stubs to return "owner" by default.
    monkeypatch.setattr(
        "app.api.projects.require_member",
        lambda project_id, current_user: "owner",
    )
    monkeypatch.setattr(
        "app.api.projects.require_role",
        lambda project_id, current_user, allowed: "owner",
    )
    return user


# ---------- list / create / get -----------------------------------------


def test_list_projects_returns_user_projects(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default = _project(name="Mein Workspace", is_default=True)
    other = _project(name="Acme GmbH")

    def fake_list_projects_for_user(user_id: UUID) -> list[ProjectWithMeta]:
        return [
            ProjectWithMeta(
                **default.model_dump(),
                role="owner",
                member_count=1,
            ),
            ProjectWithMeta(
                **other.model_dump(),
                role="owner",
                member_count=3,
            ),
        ]

    monkeypatch.setattr(
        "app.api.projects.project_repo.list_projects_for_user",
        fake_list_projects_for_user,
    )

    response = client.get("/api/projects")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["name"] == "Mein Workspace"
    assert body[1]["member_count"] == 3


def test_create_project_succeeds(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.projects.project_repo.count_projects_owned_by",
        lambda user_id: 1,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.create_project",
        lambda **kwargs: _project(name=kwargs["name"]),
    )

    response = client.post(
        "/api/projects",
        json={"name": "Kunde X", "color": "emerald"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Kunde X"
    assert response.json()["role"] == "owner"


def test_create_project_rejects_when_limit_reached(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.project import MAX_PROJECTS_PER_USER

    monkeypatch.setattr(
        "app.api.projects.project_repo.count_projects_owned_by",
        lambda user_id: MAX_PROJECTS_PER_USER,
    )

    response = client.post(
        "/api/projects",
        json={"name": "Eins zu viel", "color": "rose"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "project_limit_reached"


def test_create_project_validates_name_length(authed_owner: CurrentUser) -> None:
    # With auth stubbed, the request reaches Pydantic validation, which
    # rejects a 2-character name (min_length=3) with 422.
    response = client.post(
        "/api/projects",
        json={"name": "xy", "color": "indigo"},
    )
    assert response.status_code == 422


# ---------- delete -------------------------------------------------------


def test_delete_default_project_protected_when_only_project(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    default = _project(is_default=True)
    monkeypatch.setattr(
        "app.api.projects.project_repo.get_project",
        lambda pid: default,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.count_projects_owned_by",
        lambda user_id: 1,
    )

    response = client.delete(f"/api/projects/{default.id}")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "default_project_protected"


def test_delete_non_default_project_succeeds(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj = _project(is_default=False)
    monkeypatch.setattr(
        "app.api.projects.project_repo.get_project",
        lambda pid: proj,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.delete_project",
        lambda pid: True,
    )

    response = client.delete(f"/api/projects/{proj.id}")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}


# ---------- members ------------------------------------------------------


def test_remove_member_requires_owner_for_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user()
    app.dependency_overrides[get_current_user] = lambda: user

    # User is just a viewer, not an owner.
    monkeypatch.setattr(
        "app.api.projects.require_member",
        lambda project_id, current_user: "viewer",
    )

    other_user_id = uuid4()
    response = client.delete(f"/api/projects/{uuid4()}/members/{other_user_id}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "project_forbidden"


def test_remove_member_last_owner_blocked(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj_id = uuid4()
    target = Member(
        project_id=proj_id,
        user_id=authed_owner.id,
        role="owner",
        joined_at="2026-05-25T10:00:00Z",
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.get_member",
        lambda pid, uid: target,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.count_owners",
        lambda pid: 1,
    )

    # Self-removal of the only owner.
    response = client.delete(f"/api/projects/{proj_id}/members/{authed_owner.id}")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "last_owner"


# ---------- invites ------------------------------------------------------


def test_create_invite_rate_limited(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.schemas.project import MAX_INVITES_PER_USER_PER_DAY

    monkeypatch.setattr(
        "app.api.projects.project_repo.count_invites_by_user_last_24h",
        lambda user_id: MAX_INVITES_PER_USER_PER_DAY,
    )

    response = client.post(
        f"/api/projects/{uuid4()}/invites",
        json={"email": "new@example.com", "role": "editor"},
    )
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "invite_rate_limit"


def test_create_invite_reuses_pending(
    authed_owner: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj_id = uuid4()
    pending = Invite(
        id=uuid4(),
        token=uuid4(),
        project_id=proj_id,
        email="new@example.com",
        role="editor",
        status="pending",
        invited_by=authed_owner.id,
        invited_at="2026-05-25T10:00:00Z",
        expires_at="2026-06-01T10:00:00Z",
        accepted_at=None,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.count_invites_by_user_last_24h",
        lambda user_id: 0,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.count_members",
        lambda pid: 2,
    )
    monkeypatch.setattr(
        "app.api.projects.project_repo.find_pending_invite",
        lambda pid, email: pending,
    )
    # Should NOT call create_invite because we reuse pending.
    monkeypatch.setattr(
        "app.api.projects.project_repo.create_invite",
        lambda **_kwargs: pytest.fail("create_invite should not be called"),  # type: ignore[arg-type]
    )

    response = client.post(
        f"/api/projects/{proj_id}/invites",
        json={"email": "new@example.com", "role": "editor"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
