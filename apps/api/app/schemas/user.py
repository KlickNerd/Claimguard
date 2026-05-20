"""Auth-related Pydantic models for PROJ-1.

``CurrentUser`` is what the ``get_current_user`` dependency injects into
every authenticated endpoint - it bundles the Supabase ``auth.users``
identity with the ClaimGuard-specific ``profiles`` row.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class Profile(BaseModel):
    """Snapshot of the ClaimGuard-specific user data in ``public.profiles``."""

    id: UUID
    display_name: str | None = None
    avatar_url: str | None = None
    onboarding_completed: bool = False
    created_at: datetime
    updated_at: datetime


class CurrentUser(BaseModel):
    """Authenticated principal of the request.

    Carries the Supabase auth identity plus the ClaimGuard profile row.
    Endpoints should consume this via ``Depends(get_current_user)``
    rather than reading the raw JWT.
    """

    id: UUID
    email: EmailStr
    email_confirmed: bool
    profile: Profile | None = None


class ProfileUpdate(BaseModel):
    """Patch payload for ``PATCH /api/me/profile``.

    Only the fields the user is allowed to change live here. ``id`` and
    ``created_at`` are immutable; ``updated_at`` is touched by a DB
    trigger.
    """

    display_name: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    avatar_url: Annotated[str | None, Field(max_length=1024)] = None
    onboarding_completed: bool | None = None
