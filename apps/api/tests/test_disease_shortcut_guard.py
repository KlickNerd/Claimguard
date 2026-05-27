"""Regression tests for the `_is_obvious_disease_action` guard.

Customer feedback 2026-05-27: the old "any disease_based claim is auto-
forbidden" shortcut destroyed table cells like "Schilddrüse",
"Autoimmunerkrankungen", "Leberfunktion" - they were tagged as
disease_based by detection (because they name organs/conditions) and
then bypassed the LLM evaluator. Result: every safety hint became a
"Unzulässig: Hoch" verdict.

The new guard restricts the shortcut to claim texts that contain
explicit disease-action language (heilt, lindert, vorbeugt, …). Bare
nouns must go through the LLM evaluator with full surrounding context.
"""

from __future__ import annotations

import pytest

from app.services.claim_evaluator import _is_obvious_disease_action


@pytest.mark.parametrize(
    "claim_text",
    [
        # Explicit disease-action verbs - shortcut SHOULD fire.
        "Reishi heilt Erkältungen",
        "Ashwagandha lindert Stress-Symptome",
        "zur Vorbeugung von Osteoporose",
        "vorbeugend gegen Magenbeschwerden",
        "kuriert Schlaflosigkeit",
        "behandelt Schilddrüsen-Probleme",
        "verhindert Erkältungen",
        "hilft bei Schlaflosigkeit",
        "hilft gegen Sodbrennen",
        "wirkt gegen Erkältungen",
        "wirkt bei chronischer Müdigkeit",
        "reduziert das Risiko von Osteoporose",
        "Reishi schützt vor Erkältungen",
        # Trennbare Verben mit Lücke
        "Reishi beugt Erkältungen vor",
    ],
)
def test_obvious_disease_action_triggers_shortcut(claim_text: str) -> None:
    assert _is_obvious_disease_action(claim_text) is True


@pytest.mark.parametrize(
    "claim_text",
    [
        # Customer-report cases - all of these were FALSELY shortcutted
        # before the fix. They must now flow through the LLM evaluator.
        "Schilddrüse",
        "Autoimmunerkrankungen",
        "Leberfunktion",
        "Sedierende und beruhigende Medikamente",
        "Blutzucker und Blutdruck",
        "nicht ohne ärztliche Rücksprache nehmen sollte",
        # Neutral safety hints
        "Bei bestehenden Schilddrüsenerkrankungen Arzt fragen",
        "Vor der Einnahme ärztlich abklären lassen",
        "Wer auf Nachtschattengewächse sensibel reagiert",
        # Benign tradition/description that detection MAY tag as
        # disease_based (HWG-stem fallback) but is contextually OK.
        "Anwendungsgebiet",
        "Heiltradition",
        "Symptom-Tagebuch",
        # Empty / nonsense edge cases
        "",
        "   ",
        "Heilig",  # Heilig is excluded from "heil-" by lookahead
    ],
)
def test_neutral_text_does_not_trigger_shortcut(claim_text: str) -> None:
    assert _is_obvious_disease_action(claim_text) is False


def test_action_verb_is_case_insensitive() -> None:
    """The regex must catch capitalized starts of sentences."""
    assert _is_obvious_disease_action("Reishi HEILT Erkältungen") is True
    assert _is_obvious_disease_action("Heilt Erkältungen") is True


def test_action_verb_inside_longer_sentence() -> None:
    """The action verb anywhere in a sentence triggers the shortcut."""
    assert (
        _is_obvious_disease_action(
            "Untersucht wird, ob Reishi bei Erkältungen hilft, und wirkt gegen "
            "chronische Müdigkeit."
        )
        is True
    )
