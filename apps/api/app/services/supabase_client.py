"""Server-side Supabase client (singleton).

Uses the service-role key so the backend can read across RLS for
operations that authenticate the user separately (e.g. resolving a JWT
to the matching profile row). Application code is still expected to
gate every operation behind an authenticated principal - the service
key is *not* an excuse to skip authorization.

The client is created lazily on first use so tests can run without a
real Supabase URL configured.
"""

from __future__ import annotations

from threading import Lock

from supabase import Client, create_client

from app.config import settings


class SupabaseNotConfiguredError(RuntimeError):
    """Raised when the backend tries to talk to Supabase before env is set."""


_client: Client | None = None
_lock = Lock()


def get_supabase() -> Client:
    """Return a process-wide Supabase client.

    Initialised lazily on first call so that ``import app.main`` works
    in environments where SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are
    not set yet (e.g. unit tests that mock everything).
    """
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is not None:
            return _client
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise SupabaseNotConfiguredError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
                "for the backend to talk to Supabase.",
            )
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
        return _client


def reset_supabase_client_for_tests() -> None:
    """Drop the cached client so tests can re-init with a different config."""
    global _client
    with _lock:
        _client = None
