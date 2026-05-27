"""Tests for the DROP_ROW / DELETE marker handling in smart_apply_service.

Customer report 2026-05-27: when the per-claim pipeline couldn't find a
compliant rewrite for table cells like "Schilddrüse | Pflanze X aus
ayurvedischer Tradition", the rewrite was still inserted verbatim,
destroying the table semantics. The new contract: LLM may return
``[DROP_ROW]`` (or ``[DELETE]``) and the service strips that row /
sentence entirely rather than filling it with a fallback.
"""

from __future__ import annotations

import pytest

from app.services.smart_apply_service import (
    _looks_like_table,
    _strip_drop_markers,
)


@pytest.mark.parametrize(
    "paragraph,expected",
    [
        ("| Header A | Header B |\n| --- | --- |\n| cell A | cell B |", True),
        ("| Schilddrüse | Vorsicht bei Schilddrüsenerkrankungen |", True),
        ("Plain prose without pipes.", False),
        ("This has | one pipe but no row structure", False),
        ("", False),
        # A non-table paragraph with a pipe but no row pattern stays
        # classified as prose.
        ("Pipe-char | in middle, not a table", False),
    ],
)
def test_looks_like_table(paragraph: str, expected: bool) -> None:
    assert _looks_like_table(paragraph) is expected


@pytest.mark.parametrize(
    "given,expected",
    [
        # Plain sentence, no markers - returned verbatim.
        (
            "Reishi hat eine lange Tradition.",
            "Reishi hat eine lange Tradition.",
        ),
        # Bare DROP_ROW marker - returns empty (signal: drop paragraph).
        ("[DROP_ROW]", ""),
        ("[DELETE]", ""),
        # Mixed case still recognised.
        ("[drop_row]", ""),
        ("[Delete]", ""),
        # Table row where the cell-content was DROP_ROW - the leftover
        # pipes-only line is treated as empty.
        ("| Schilddrüse | [DROP_ROW] |", ""),
        ("| [DROP_ROW] | [DROP_ROW] |", ""),
        # Markdown table separators are not "meaningful content".
        ("| --- | --- |", ""),
        # Cleanup must preserve normal content alongside the marker
        # being removed. Here the marker disappears, the header stays.
        (
            "Wichtig: bitte beachten. [DELETE]",
            "Wichtig: bitte beachten. ",
        ),
    ],
)
def test_strip_drop_markers(given: str, expected: str) -> None:
    assert _strip_drop_markers(given) == expected


def test_strip_drop_markers_preserves_real_table_rows() -> None:
    """A table row with real content on both sides must come back intact."""
    given = "| Schilddrüse | Bei Schilddrüsenerkrankungen Arzt fragen |"
    assert _strip_drop_markers(given) == given


def test_strip_drop_markers_handles_multiline_table() -> None:
    """A two-row table where one row has DROP_ROW: that row vanishes,
    the other survives."""
    given = (
        "| Bereich | Hinweis |\n"
        "| --- | --- |\n"
        "| Schilddrüse | [DROP_ROW] |\n"
        "| Allergie | Bei Allergie testen |"
    )
    out = _strip_drop_markers(given)
    assert "[DROP_ROW]" not in out
    # Row with real content stays.
    assert "Bei Allergie testen" in out
    # The header row's content is preserved (not the separator).
    assert "Bereich" in out
    assert "Hinweis" in out
