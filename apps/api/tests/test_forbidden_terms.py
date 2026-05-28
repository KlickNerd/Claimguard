"""Tests for the deterministic forbidden-terms matcher.

The Ashwagandha-/Reishi-case from the customer report on 2026-05-26
listed concrete strings that must be caught: ``Heiltraditionen``,
``Anwendungsgebiete``, ``Symptom-Tagebuch``, ``Eindosierung``,
``mentales Wohlbefinden``, ``Förderung des Wohlbefindens``,
``Widerstandsfähigkeit`` etc. Each one has a regression test here.
"""

from __future__ import annotations

import pytest

from app.services.forbidden_terms import (
    find_forbidden_terms,
    forbidden_terms_summary,
    has_forbidden_terms,
    sperrliste_block_for_prompt,
)


@pytest.mark.parametrize(
    "text,expected_label",
    [
        # HWG hard hits from the customer report
        ("Eine alte Heiltradition aus Indien", "heil-stem"),
        ("...Pflanzen aus alten Heiltraditionen.", "heil-stem"),
        ("Anwendungsgebiete der Ashwagandha-Wurzel", "anwendungsgebiet-stem"),
        ("Ein klassisches Anwendungsbild", "anwendungsgebiet-stem"),
        ("Symptom-Tagebuch führen", "symptom-stem"),
        ("Beobachte deine Symptome", "symptom-stem"),
        ("Eindosierung schrittweise", "eindosierung-stem"),
        ("Ein therapeutischer Ansatz", "therapie-stem"),
        ("Reishi als Therapie bei Stress", "therapie-stem"),
        ("Indikation laut Beipackzettel", "indikation-stem"),
        ("Diagnose vom Arzt einholen", "diagnose-stem"),
        ("zur Linderung der Beschwerden", "lindern-stem"),
        ("Reishi zur Vorbeugung von Erkältungen.", "vorbeugen-stem"),
        ("eine vorbeugende Wirkung", "vorbeugen-stem"),
        ("Magenbeschwerden lindern", "beschwerde-medical"),
        ("Gelenkbeschwerden bekämpfen", "beschwerde-medical"),
        # v1.2: Pharma-Dosierungs-Vokabular (Lebensmittel sagt
        # Verzehrmenge / Tagesportion).
        ("Tagesdosis bei Kombination", "dosierung-stem"),
        ("die empfohlene Dosierung", "dosierung-stem"),
        ("Anfangsdosis schrittweise erhöhen", "dosierung-stem"),
        ("Dosierungsempfehlung beachten", "dosierung-stem"),
    ],
)
def test_hard_hits(text: str, expected_label: str) -> None:
    hits = find_forbidden_terms(text)
    assert any(h.pattern_label == expected_label for h in hits), (
        f"Expected to find {expected_label!r} in {text!r}, got {[h.pattern_label for h in hits]!r}"
    )
    assert all(h.severity == "hard" for h in hits if h.pattern_label == expected_label)


@pytest.mark.parametrize(
    "text,expected_label",
    [
        # HCVO Art. 10 Abs. 3 wellbeing soft hits from the customer report
        ("für mentales Wohlbefinden", "wohlbefinden"),
        ("zur Förderung des Wohlbefindens", "wohlbefinden"),
        ("körperliches Wohlbefinden steigern", "wohlbefinden"),
        ("zur allgemeinen Widerstandsfähigkeit", "widerstandsfaehigkeit"),
        ("stärkt die Widerstandskraft", "widerstandsfaehigkeit"),
        ("zur Unterstützung in Phasen mentaler Anspannung", "mentale-anspannung"),
        ("mehr Vitalität im Alltag", "vitalitaet"),
        ("Booster für die Immunabwehr", "boosten"),
        ("boostet deine Energie", "boosten"),
        ("für innere Entspannung", "entspannung-stem"),
        ("entspannend nach einem langen Tag", "entspannung-stem"),
        ("Abwehrkräfte stärken", "abwehrkraft"),
        # v1.2: Adaptogen als Begriff (OLG Celle / OLG München).
        ("klassische Adaptogene aus dem Ayurveda", "adaptogen-term"),
        ("hat adaptogene Eigenschaften", "adaptogen-term"),
        ("ein modernes Adaptogen", "adaptogen-term"),
    ],
)
def test_soft_hits(text: str, expected_label: str) -> None:
    hits = find_forbidden_terms(text)
    assert any(h.pattern_label == expected_label for h in hits), (
        f"Expected to find {expected_label!r} in {text!r}, got {[h.pattern_label for h in hits]!r}"
    )


@pytest.mark.parametrize(
    "text",
    [
        # Allowed: authorised EU register wording stays clean.
        "Vitamin C trägt zu einer normalen Funktion des Immunsystems bei.",
        "Magnesium trägt zu einer normalen Muskelfunktion bei.",
        "Vitamin B6 trägt zu einer normalen Funktion des Nervensystems bei.",
        # Allowed: pure product / sensory description.
        "Reishi-Extrakt mit fein-erdigem Geschmack.",
        "Hochwertige Ashwagandha-Wurzel aus biologischem Anbau.",
        # Allowed: explicit traditional / historical framing without
        # "Heil"-stem.
        "Wird in der ayurvedischen Tradition seit Jahrhunderten geschätzt.",
        # Edge: "Heiligabend" is not a HWG term and must not match.
        "Lieferung garantiert vor Heiligabend.",
        # Edge: "Anwendung" alone is allowed; only Anwendungsgebiet /
        # Anwendungsbild are pharma-coded.
        "Die Anwendung ist denkbar einfach: 1 Kapsel pro Tag.",
        # Edge: "beschwerden" without medical compound stays neutral.
        "Beschwerden bitte per Mail an support@example.com.",
        # Edge: "Heilig" / Heiliger should not match Heil-stem.
        "Heiliger Strohsack",
    ],
)
def test_clean_texts_have_no_hits(text: str) -> None:
    hits = find_forbidden_terms(text)
    assert hits == [], (
        f"Expected zero hits for {text!r}, got "
        f"{[(h.term, h.pattern_label) for h in hits]!r}"
    )


def test_severity_filter_hard_only() -> None:
    """When asking for hard severity only, soft hits are filtered out."""
    text = "Eine alte Heiltradition für mentales Wohlbefinden."
    hard_only = find_forbidden_terms(text, severities=("hard",))
    assert all(h.severity == "hard" for h in hard_only)
    assert any(h.pattern_label == "heil-stem" for h in hard_only)
    assert not any(h.pattern_label == "wohlbefinden" for h in hard_only)


def test_summary_dedups_repeated_terms() -> None:
    """A term that appears multiple times shows up once in the summary."""
    text = (
        "Heiltradition aus Indien. Eine echte Heiltradition. "
        "Diese Heiltradition ist alt."
    )
    hits = find_forbidden_terms(text)
    summary = forbidden_terms_summary(hits)
    # Case-insensitive dedup: one entry for the lemma.
    assert len(summary) == 1
    assert summary[0].lower() == "heiltradition"


def test_has_forbidden_terms_boolean() -> None:
    assert has_forbidden_terms("für mentales Wohlbefinden") is True
    assert has_forbidden_terms("Vitamin C unterstützt das Immunsystem") is False
    # Soft-only severity check
    assert (
        has_forbidden_terms(
            "Eine alte Heiltradition",
            severities=("soft",),
        )
        is False
    )
    assert (
        has_forbidden_terms(
            "Eine alte Heiltradition",
            severities=("hard",),
        )
        is True
    )


def test_sperrliste_block_is_non_empty_markdown() -> None:
    block = sperrliste_block_for_prompt()
    assert "Sperrliste" in block
    # Hard examples present.
    assert "Heiltradition" in block or "Heil" in block
    assert "Anwendungsgebiet" in block
    assert "Symptom" in block
    # Soft examples present.
    assert "Wohlbefinden" in block
    # Concrete advice on what to do instead - the LLM needs an exit
    # door, otherwise it'll just paraphrase around the list.
    assert "traditionell" in block or "sensorisch" in block.lower()


def test_hits_are_sorted_by_position() -> None:
    text = "Erst Wohlbefinden, dann Heiltradition, dann Symptom."
    hits = find_forbidden_terms(text)
    positions = [h.start for h in hits]
    assert positions == sorted(positions)


def test_overlapping_rules_both_fire() -> None:
    """``mentales Wohlbefinden`` triggers both the wohlbefinden stem
    rule and the specific compound rule. Both should appear so the
    retry prompt can be more specific."""
    text = "für mentales Wohlbefinden im Alltag"
    hits = find_forbidden_terms(text)
    labels = {h.pattern_label for h in hits}
    assert "wohlbefinden" in labels
    assert "mentales-wohlbefinden" in labels
