"""Pydantic schemas for PROJ-22 (Multi-Projekt-Workspaces).

Three resources: ``projects``, ``project_members``, ``project_invites``.
Schemas come in pairs: a DB-shape (``Project``, ``Member``, ``Invite``)
matching the Supabase row exactly, and a request-shape for the API
endpoints (``ProjectCreate``, ``InviteCreate``, ...).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "editor", "viewer"]
InviteRole = Literal["editor", "viewer"]
InviteStatus = Literal["pending", "accepted", "revoked", "expired"]
ProjectColor = Literal[
    "indigo", "emerald", "rose", "amber", "sky", "violet", "teal", "slate"
]

# Backend defaults; bound by the spec, switchable later via PROJ-2.
MAX_PROJECTS_PER_USER = 10
MAX_MEMBERS_PER_PROJECT = 10
MAX_INVITES_PER_USER_PER_DAY = 50


class Project(BaseModel):
    """Row shape of ``public.projects``."""

    id: UUID
    name: str
    color: ProjectColor
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ProjectWithMeta(Project):
    """``Project`` plus aggregated info we usually need together."""

    role: Role
    member_count: int


class ProjectCreate(BaseModel):
    name: Annotated[str, Field(min_length=3, max_length=60)]
    color: ProjectColor = "indigo"


class ProjectUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=3, max_length=60)] = None
    color: ProjectColor | None = None


class Member(BaseModel):
    """Row shape of ``public.project_members`` enriched with the user's email."""

    project_id: UUID
    user_id: UUID
    role: Role
    joined_at: datetime
    email: EmailStr | None = None
    display_name: str | None = None


class MemberRoleUpdate(BaseModel):
    role: Role


class Invite(BaseModel):
    """Row shape of ``public.project_invites``."""

    id: UUID
    token: UUID
    project_id: UUID
    email: EmailStr
    role: InviteRole
    status: InviteStatus
    invited_by: UUID | None
    invited_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None


class InviteCreate(BaseModel):
    email: EmailStr
    role: InviteRole = "editor"


class InvitePublic(BaseModel):
    """What a non-authenticated `/invite/[token]` page may see.

    Excludes IDs and audit fields; just enough to render the landing
    page with the project name and the inviter's display name.
    """

    project_name: str
    project_color: ProjectColor
    inviter_display_name: str | None
    inviter_email: EmailStr
    role: InviteRole
    status: InviteStatus
    expires_at: datetime
