"""Unit tests for the URL extractor (PROJ-13).

Network-touching paths use respx so we never hit the real internet, while
input-validation paths run pure-Python.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.url_extractor import UrlExtractionError, extract_url_text

_VALID_HTML = """<!doctype html>
<html lang="de">
<head><title>Magnesium-Komplex 400</title></head>
<body>
  <main>
    <h1>Magnesium-Komplex 400 — für deine Muskeln</h1>
    <p>Magnesium trägt zu einer normalen Muskelfunktion bei und unterstützt
       das Nervensystem. Vitamin D stärkt zusätzlich das Immunsystem.</p>
    <p>Bei nachlassender Energie kann eine Tagesdosis Magnesium den
       Energiestoffwechsel ankurbeln.</p>
  </main>
</body>
</html>
"""


def test_rejects_non_http_scheme() -> None:
    with pytest.raises(UrlExtractionError) as exc:
        extract_url_text("ftp://example.com/page")
    assert exc.value.code == "url_invalid"


def test_rejects_url_with_credentials() -> None:
    with pytest.raises(UrlExtractionError) as exc:
        extract_url_text("https://user:pw@example.com/page")
    assert exc.value.code == "url_invalid"


def test_rejects_private_ip() -> None:
    # 127.0.0.1 is loopback, must be blocked before any HTTP request.
    with pytest.raises(UrlExtractionError) as exc:
        extract_url_text("http://127.0.0.1/")
    assert exc.value.code == "url_private"


def test_extract_returns_main_content() -> None:
    """Skip robots + fetch and verify trafilatura yields the body text."""
    with (
        patch(
            "app.services.url_extractor._validate_no_private_target",
            return_value=None,
        ),
        patch("app.services.url_extractor._check_robots", return_value=None),
        patch(
            "app.services.url_extractor._fetch_html",
            return_value=("https://example.com/produkte/magnesium", _VALID_HTML),
        ),
    ):
        result = extract_url_text("https://example.com/produkte/magnesium")
    assert result.final_url == "https://example.com/produkte/magnesium"
    assert "Muskelfunktion" in result.text
    assert result.char_count == len(result.text)


def test_robots_disallow_blocks_extraction() -> None:
    def boom(*_args, **_kwargs):
        raise UrlExtractionError(
            "url_blocked_by_robots",
            "Diese Seite erlaubt unserem Crawler den Zugriff laut robots.txt nicht.",
        )

    with (
        patch(
            "app.services.url_extractor._validate_no_private_target",
            return_value=None,
        ),
        patch("app.services.url_extractor._check_robots", side_effect=boom),
    ):
        with pytest.raises(UrlExtractionError) as exc:
            extract_url_text("https://example.com/")
    assert exc.value.code == "url_blocked_by_robots"
