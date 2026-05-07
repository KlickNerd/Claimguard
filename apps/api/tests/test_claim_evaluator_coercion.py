"""Unit tests for the LLM-output coercion helpers in claim_evaluator.

The Vitalpilze case from 2026-05-04 surfaced runs where every claim came
back ``status="unclear"-but-not-quite``: the LLM returned synonyms like
``permitted`` or German-language enums like ``unzulässig``, which the
strict Pydantic literal then rejected. The coercion layer is the safety
net that keeps those evaluations on the screen instead of producing
"Schema-Fehler" cards.
"""

from __future__ import annotations

import pytest

from app.services.claim_evaluator import (
    _coerce_confidence,
    _coerce_reasoning,
    _coerce_risk,
    _coerce_status,
)


@pytest.mark.parametrize(
    "given,expected",
    [
        ("allowed", "allowed"),
        ("Allowed", "allowed"),
        ("permitted", "allowed"),
        ("zulässig", "allowed"),
        ("Borderline", "borderline"),
        ("grenzwertig", "borderline"),
        ("forbidden", "forbidden"),
        ("verboten", "forbidden"),
        ("unzulässig", "forbidden"),
        ("uncertain", "unclear"),
        ("unklar", "unclear"),
        ("", "unclear"),
        (None, "unclear"),
        (42, "unclear"),
        ("something_unexpected", "unclear"),
    ],
)
def test_status_coercion(given: object, expected: str) -> None:
    assert _coerce_status(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        ("low", "low"),
        ("HIGH", "high"),
        ("hoch", "high"),
        ("mittel", "medium"),
        ("moderate", "medium"),
        (None, "medium"),
        ("nonsense", "medium"),
    ],
)
def test_risk_coercion(given: object, expected: str) -> None:
    assert _coerce_risk(given) == expected


@pytest.mark.parametrize(
    "given,expected",
    [
        (0.5, 0.5),
        (1.0, 1.0),
        (0.0, 0.0),
        ("0.7", 0.7),
        (1.5, 1.0),
        (-0.2, 0.0),
        (None, 0.5),
        ("not-a-number", 0.5),
    ],
)
def test_confidence_coercion(given: object, expected: float) -> None:
    assert _coerce_confidence(given) == pytest.approx(expected)


def test_reasoning_falls_back_when_missing() -> None:
    assert "manuell prüfen" in _coerce_reasoning(None)
    assert "manuell prüfen" in _coerce_reasoning("")
    assert _coerce_reasoning(" Ein Begründungstext.  ") == "Ein Begründungstext."
