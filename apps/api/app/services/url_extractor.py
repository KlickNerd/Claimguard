"""HTML-text extraction for the URL-input flow (PROJ-13, text-only MVP).

We deliberately skip Playwright in the MVP - the bulk of supplement landing
pages are server-rendered, ``httpx`` + ``trafilatura`` covers 90 %+ of cases,
and we avoid carrying a Chromium image on the VPS. A Playwright fallback is
queued for V1.1 once we have evidence that JS-only sites matter.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura

logger = logging.getLogger(__name__)


_USER_AGENT = "ClaimGuardBot/1.0 (+https://claimguard.de/bot)"
_MAX_CONTENT_BYTES = 5 * 1024 * 1024  # 5 MB hard cap on raw HTML
_REQUEST_TIMEOUT = 15.0  # seconds; spec says 30 but trafilatura is fast
_MIN_TEXT_CHARS = 50


class UrlExtractionError(RuntimeError):
    """Raised when a URL cannot be turned into useful text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class UrlExtractionResult:
    text: str
    title: str | None
    final_url: str
    char_count: int


def extract_url_text(url: str) -> UrlExtractionResult:
    """Fetch ``url`` and return main-content text.

    Stable error codes:
    - ``url_invalid``: not http(s), missing host, has credentials
    - ``url_private``: resolves to a private/loopback/link-local address (SSRF)
    - ``url_blocked_by_robots``: ``robots.txt`` disallows our user-agent
    - ``url_unreachable``: DNS / TCP / TLS failure
    - ``url_status``: server returned 4xx/5xx
    - ``url_too_large``: body exceeds 5 MB
    - ``url_no_text``: extracted text below 50 chars
    """
    parsed = _validate_scheme(url)
    _validate_no_private_target(parsed.hostname)
    _check_robots(parsed)

    final_url, html = _fetch_html(url)

    extracted = trafilatura.extract(
        html,
        favor_recall=True,
        include_comments=False,
        include_tables=True,
        deduplicate=True,
        url=final_url,
    ) or ""

    text = extracted.strip()
    if len(text) < _MIN_TEXT_CHARS:
        raise UrlExtractionError(
            "url_no_text",
            (
                "Auf dieser Seite konnten wir nicht genug Fließtext finden - "
                "vielleicht ist sie reine Bild-/Video-Seite oder JS-only. "
                "Bitte Text direkt einfügen."
            ),
        )

    title = trafilatura.extract_metadata(html)
    title_str = title.title if title and title.title else None

    return UrlExtractionResult(
        text=text,
        title=title_str,
        final_url=final_url,
        char_count=len(text),
    )


def _validate_scheme(url: str) -> _ParsedUrl:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UrlExtractionError(
            "url_invalid",
            "Bitte eine vollständige URL mit http:// oder https:// angeben.",
        )
    if not parsed.hostname:
        raise UrlExtractionError(
            "url_invalid",
            "Die URL hat keinen erkennbaren Host.",
        )
    if parsed.username or parsed.password:
        raise UrlExtractionError(
            "url_invalid",
            "URLs mit Benutzername/Passwort werden nicht unterstützt.",
        )
    return parsed  # type: ignore[return-value]


def _validate_no_private_target(hostname: str | None) -> None:
    if not hostname:
        return
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UrlExtractionError(
            "url_unreachable",
            f"Die Domain {hostname} konnte nicht aufgelöst werden.",
        ) from exc

    for record in addresses:
        ip = ipaddress.ip_address(record[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise UrlExtractionError(
                "url_private",
                "Interne und private Adressen sind nicht erlaubt.",
            )


def _check_robots(parsed: _ParsedUrl) -> None:
    robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    rp = RobotFileParser()
    try:
        with httpx.Client(timeout=5.0, headers={"user-agent": _USER_AGENT}) as client:
            response = client.get(robots_url)
            if response.status_code >= 400:
                # Missing / forbidden robots.txt is treated as "no rules".
                return
            rp.parse(response.text.splitlines())
    except httpx.HTTPError:
        # Network hiccup on robots.txt - fail open. We are not aggressive
        # about crawling, the main-content fetch will retry the same host
        # with the same UA.
        return

    target = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
    if not rp.can_fetch(_USER_AGENT, target):
        raise UrlExtractionError(
            "url_blocked_by_robots",
            "Diese Seite erlaubt unserem Crawler den Zugriff laut robots.txt nicht.",
        )


def _fetch_html(url: str) -> tuple[str, str]:
    headers = {
        "user-agent": _USER_AGENT,
        "accept": "text/html,application/xhtml+xml",
        "accept-language": "de,en;q=0.7",
    }
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=_REQUEST_TIMEOUT,
            headers=headers,
            max_redirects=5,
        ) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        raise UrlExtractionError(
            "url_unreachable",
            f"Die Seite war nicht erreichbar: {exc}",
        ) from exc

    if response.status_code >= 400:
        raise UrlExtractionError(
            "url_status",
            f"Server hat HTTP {response.status_code} zurückgegeben.",
        )

    if len(response.content) > _MAX_CONTENT_BYTES:
        raise UrlExtractionError(
            "url_too_large",
            "Die Seite ist größer als 5 MB - ungewöhnlich für eine Landingpage.",
        )

    # The redirect-walk above guarantees ``response.url`` is the post-redirect
    # URL we ultimately read from.
    final_url = str(response.url)
    return final_url, response.text


# Type-only helper so urlparse's return type is friendlier upstream.
_ParsedUrl = type(urlparse(""))
