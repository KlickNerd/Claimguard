"""Unit tests for the rewrite output sanitizer.

The Vitalpilze case from 2026-05-04 surfaced two LLM-output quirks that
shipped straight into the user's marketing text:

1. Sonnet wrapped some rewrites in „german quotes", which then landed
   verbatim mid-paragraph.
2. Sonnet appended a full stop even when the original claim was a
   mid-sentence span - the splice produced "…einen festen Platz. und
   erleben heute…".

The sanitizer fixes both before the rewrite ever reaches the frontend.
"""

from __future__ import annotations

import pytest

from app.services.rewrite_service import (
    _aggressive_clean,
    _has_compliance_meta,
    _looks_like_template_placeholder,
    _match_terminal_punct,
    _strip_wrapping_quotes,
    detect_addressing_form,
)


@pytest.mark.parametrize(
    "given,expected",
    [
        ('"foo"', "foo"),
        ("„bar“", "bar"),
        ("«baz»", "baz"),
        ("'qux'", "qux"),
        ("‘quoted’", "quoted"),
        ("plain", "plain"),
        ('"  spaced  "', "spaced"),
    ],
)
def test_strip_wrapping_quotes(given: str, expected: str) -> None:
    assert _strip_wrapping_quotes(given) == expected


@pytest.mark.parametrize(
    "rewrite,original,expected",
    [
        # Mid-sentence original → strip the trailing period.
        (
            "einen festen Platz.",
            "seit Jahrhunderten geschätzt",
            "einen festen Platz",
        ),
        # Original ends with full stop → ensure rewrite ends the same way.
        (
            "Magnesium trägt zu einer normalen Muskelfunktion bei",
            "stärkt die Muskulauer.",
            "Magnesium trägt zu einer normalen Muskelfunktion bei.",
        ),
        # Already aligned → unchanged.
        (
            "Magnesium hilft.",
            "Was Magnesium tut.",
            "Magnesium hilft.",
        ),
        # No terminal punctuation either side → unchanged.
        (
            "frischer Geschmack",
            "leckerer Geschmack",
            "frischer Geschmack",
        ),
    ],
)
def test_match_terminal_punct(
    rewrite: str, original: str, expected: str
) -> None:
    assert _match_terminal_punct(rewrite, original) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        # Klar Du-Form
        ("Probiere unsere Pilze und entdecke deine Energie.", "du"),
        ("Du hast es verdient. Dir steht das Beste zu.", "du"),
        # Klar Sie-Form
        ("Erleben Sie unsere Vitalpilze. Ihre Gesundheit ist uns wichtig.", "sie"),
        ("Wir freuen uns auf Sie und Ihren Besuch.", "sie"),
        # Mixed - fällt auf neutral
        ("Sie können unsere Vitalpilze probieren, dann weißt du Bescheid.", "neutral"),
        # Keine direkte Anrede - neutral
        ("Vitalpilze sind faszinierende Naturprodukte.", "neutral"),
        # Lower-case "sie" zählt nicht (= 3rd person plural / fem.)
        ("Die Pilze, sie sind besonders.", "neutral"),
        # Empty / None handling
        ("", "neutral"),
    ],
)
def test_detect_addressing_form(given: str, expected: str) -> None:
    assert detect_addressing_form(given) == expected


@pytest.mark.parametrize(
    "given,is_placeholder",
    [
        ("[konkreten Nährstoff einsetzen]", True),
        ("Vitamin D, das [Claim ergänzen] beiträgt", True),
        ("Vitalpilze liefern [z. B. Vitamin D] für gute Stimmung", True),
        ("Eine [TODO: Wortwahl prüfen] Aussage", True),
        # Generic [Word] / [Word X] caught as well -- a marketing rewrite
        # with bracketed words is essentially always a placeholder leak.
        ("[Hinweis] mitten im Text", True),
        ("Vitalpilze liefern [Nährstoff X] aus dem Register", True),
        # Bracketed numeric units (dosage, etc.) start with a digit and
        # are *not* flagged.
        ("Vitamin D [800 IE] pro Tagesdosis", False),
        ("Sauberer Rewrite ohne Klammern", False),
    ],
)
def test_template_placeholder_detection(given: str, is_placeholder: bool) -> None:
    assert _looks_like_template_placeholder(given) is is_placeholder


@pytest.mark.parametrize(
    "given,is_meta",
    [
        # Compliance-Klammern, die das LLM im Rewrite leakt
        ("Cordyceps – traditionell verwendet (Hinweis: Verweise auf TCM entfernen).", True),
        ("Reishi-Tonikum (Achtung: nur im Übergangsregime nach Art. 28 HCVO).", True),
        ("Foo (rein historisch-kultureller Hinweis ohne Wirkungsversprechen).", True),
        ("Bar (Wortlaut eng an EFSA-Antrag 2183).", True),
        ("Baz (zugelassener Wortlaut gem. VO 432/2012).", True),
        # Mehrere Regulatorik-Keywords im selben Satz - auch verdächtig.
        (
            "Vitamin C trägt zu normaler Funktion bei VO 432/2012 EFSA-Antrag",
            True,
        ),
        # Legitimer Rewrite ohne Compliance-Notiz - bleibt durch.
        ("Magnesium trägt zu einer normalen Muskelfunktion bei.", False),
        ("Cordyceps - traditionell verwendet für aktive Menschen.", False),
        ("Vitamin C trägt zu einer normalen Funktion des Immunsystems bei.", False),
    ],
)
def test_compliance_meta_detection(given: str, is_meta: bool) -> None:
    assert _has_compliance_meta(given) is is_meta


@pytest.mark.parametrize(
    "given,expected",
    [
        # Quote noise stripped front; trailing period kept
        # (terminal punctuation handled by _match_terminal_punct).
        ('"Magnesium trägt zur Muskelfunktion bei.', "Magnesium trägt zur Muskelfunktion bei."),
        ('„Reishi"', "Reishi"),
        # Trailing colon / semicolon stripped
        ("Cordyceps:", "Cordyceps"),
        # Doubled dots collapsed to a single one
        ("Magnesium hilft..", "Magnesium hilft."),
        # `." ` mid-string collapsed to single period
        ('Foo." Bar', "Foo. Bar"),
        # Space before punctuation closed up
        ("Foo .", "Foo."),
        # Already clean -- unchanged
        ("Magnesium trägt zur Muskelfunktion bei", "Magnesium trägt zur Muskelfunktion bei"),
    ],
)
def test_aggressive_clean(given: str, expected: str) -> None:
    assert _aggressive_clean(given) == expected
