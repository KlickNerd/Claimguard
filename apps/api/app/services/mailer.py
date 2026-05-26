"""Transactional email via Resend.

Wraps the HTTP API directly (no SDK dependency) - it's a handful of
POST calls and that's cheaper than another package on the dependency
tree. Templates live as Jinja2 files next to this module so non-
developers can tweak copy without touching Python.

Send is best-effort: a failure here returns ``False`` so the calling
route can decide how loud to fail. For invite mails the route already
falls back to "Link manuell kopieren" UX, so a 502 from Resend doesn't
block invite creation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

logger = logging.getLogger(__name__)


_RESEND_URL = "https://api.resend.com/emails"
_TEMPLATE_DIR = Path(__file__).parent / "mailer_templates"


_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
    keep_trailing_newline=True,
)


class MailerNotConfiguredError(RuntimeError):
    """RESEND_API_KEY missing - typical in dev / tests."""


def _from_address() -> str:
    name = settings.mail_from_name or "ClaimGuard"
    address = settings.mail_from_address or "noreply@claim-guard.de"
    return f"{name} <{address}>"


def _render(template_name: str, context: dict[str, Any]) -> str:
    template = _env.get_template(template_name)
    return template.render(**context)


def send_mail(
    *,
    to: str,
    subject: str,
    template: str,
    context: dict[str, Any],
) -> bool:
    """Render the Jinja2 template and POST to Resend.

    Returns ``True`` on 2xx, ``False`` otherwise. Doesn't raise so the
    caller can log + continue.
    """
    if not settings.resend_api_key:
        logger.info("RESEND_API_KEY not set; suppressing send to %s", to)
        return False

    html = _render(template, context)
    payload = {
        "from": _from_address(),
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        response = httpx.post(
            _RESEND_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("Resend POST failed for %s: %s", to, exc)
        return False
    if response.status_code >= 400:
        logger.warning(
            "Resend returned %s for %s: %s",
            response.status_code,
            to,
            response.text[:300],
        )
        return False
    return True


def send_invite_mail(
    *,
    to: str,
    project_name: str,
    inviter_name: str,
    role: str,
    token: str,
    base_url: str | None = None,
) -> bool:
    invite_url = f"{(base_url or settings.public_app_url).rstrip('/')}/invite/{token}"
    subject = "Einladung zum ClaimGuard-Projekt „" + project_name + "“"
    return send_mail(
        to=to,
        subject=subject,
        template="invite.html",
        context={
            "project_name": project_name,
            "inviter_name": inviter_name,
            "role": _role_label(role),
            "invite_url": invite_url,
        },
    )


def _role_label(role: str) -> str:
    return {"owner": "Owner", "editor": "Editor", "viewer": "Viewer"}.get(
        role,
        role,
    )
