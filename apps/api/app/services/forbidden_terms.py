"""Deterministic vocabulary checks for HWG and HCVO violations.

This module is the safety net behind the LLM-based detection/rewrite
pipeline. It encodes terms that customer feedback (and German case law)
has flagged repeatedly:

- HWG (Heilmittelwerbegesetz) terms - medical/pharma vocabulary that
  must never appear in food / supplement marketing because it implies
  a medicinal product. Examples: ``Heiltradition``, ``Anwendungsgebiet``,
  ``Symptom-Tagebuch``, ``Eindosierung``.

- HCVO Art. 10 Abs. 3 wellbeing patterns - allgemeine
  Wohlbefindens-/Vitalitäts-Aussagen that are only permitted when
  accompanied by a concretely authorised health claim. In a *rewrite*
  context we treat them as forbidden by default: the rewrite must not
  re-introduce them, because the original violation is exactly what
  we're trying to remove.

The matcher is used in two places:

1. ``claim_detector`` merges deterministic hits with the LLM output so
   the LLM can't silently miss this vocabulary.
2. ``rewrite_service`` / ``smart_apply_service`` / ``polish_service``
   run the matcher on the LLM's output. If the LLM produced new hits
   the rewrite is retried with an explicit ``Sperrliste`` block, and
   if it still leaks the rewrite is dropped.

Severity ``hard`` violations should never appear in any marketing
copy; ``soft`` violations are only acceptable when bound to an
authorised substance claim, which we conservatively treat as
disallowed for rewrites.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Severity = Literal["hard", "soft"]


@dataclass(frozen=True, slots=True)
class ForbiddenTermHit:
    """One match of a forbidden term in a text."""

    term: str
    pattern_label: str
    severity: Severity
    category: str
    start: int
    end: int

    @property
    def matched_text(self) -> str:
        return self.term


@dataclass(frozen=True, slots=True)
class _Rule:
    label: str
    pattern: re.Pattern[str]
    severity: Severity
    category: str
    # Human-readable example used in the LLM-facing block.
    example: str


def _w(pattern: str) -> re.Pattern[str]:
    """Compile with case-insensitive flag and Unicode word semantics."""
    return re.compile(pattern, flags=re.IGNORECASE | re.UNICODE)


# ---------------------------------------------------------------------------
# HARD rules - HWG / medicinal vocabulary. These imply a medicinal product
# and are never compatible with a supplement / food marketing context.
# ---------------------------------------------------------------------------

_HARD_RULES: tuple[_Rule, ...] = (
    _Rule(
        label="heil-stem",
        # Catches Heilung, Heiltradition, heilen, Heilkraft, Heilpraktiker,
        # heilkundlich, Heilversprechen, … but excludes the unrelated
        # "Heiligabend" / "Heilig…" stem explicitly.
        pattern=_w(r"\bheil(?!ig\b|ig[a-zäöüß])[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Heilversprechen",
        example="Heiltradition, Heilkraft, heilen, Heilpraktiker",
    ),
    _Rule(
        label="symptom-stem",
        # Symptom, Symptome, Symptom-Tagebuch, symptomatisch.
        pattern=_w(r"\bsymptom[a-zäöüß-]*\b"),
        severity="hard",
        category="HWG-Krankheitsbezug",
        example="Symptom, Symptom-Tagebuch, symptomatisch",
    ),
    _Rule(
        label="anwendungsgebiet-stem",
        # Anwendungsgebiet(e) / Anwendungsbild - pharma-Begriff aus dem
        # Beipackzettel. "Anwendung" allein bleibt erlaubt (vielfältige
        # Bedeutungen).
        pattern=_w(r"\banwendungs(?:gebiet|bild)[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Indikation",
        example="Anwendungsgebiet, Anwendungsbild",
    ),
    _Rule(
        label="indikation-stem",
        pattern=_w(r"\bindikation[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Indikation",
        example="Indikation, indikationsbezogen",
    ),
    _Rule(
        label="eindosierung-stem",
        pattern=_w(r"\beindosier[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Pharma-Vokabular",
        example="Eindosierung, eindosieren",
    ),
    _Rule(
        label="dosierung-stem",
        # Dosierung / Dosierungsempfehlung / Tagesdosis / Anfangsdosis -
        # arzneimittelrechtliche Begriffe. Lebensmittel/NEMs sprechen
        # von Verzehrmenge / Tagesportion / Verzehrempfehlung.
        pattern=_w(
            r"\b(?:"
            r"dosierung[a-zäöüß]*|"
            r"tagesdosis|tagesdosen|"
            r"anfangsdosis|"
            r"einnahmedosis|"
            r"höchstdosis|hoechstdosis|"
            r"dosis-empfehlung|dosisempfehlung"
            r")\b",
        ),
        severity="hard",
        category="HWG-Pharma-Vokabular",
        example=(
            "Dosierung, Tagesdosis, Anfangsdosis, "
            "Dosierungsempfehlung"
        ),
    ),
    _Rule(
        label="therapie-stem",
        # Therapie, therapeutisch, Therapieansatz. Allow "Aromatherapie"
        # only if you really want to - we keep it strict for now.
        pattern=_w(r"\b(?:therapie[a-zäöüß]*|therapeutisch[a-zäöüß]*)\b"),
        severity="hard",
        category="HWG-Therapiebezug",
        example="Therapie, therapeutisch, Therapieansatz",
    ),
    _Rule(
        label="diagnose-stem",
        pattern=_w(r"\bdiagnos[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Krankheitsbezug",
        example="Diagnose, diagnostizieren",
    ),
    _Rule(
        label="lindern-stem",
        pattern=_w(r"\b(?:linder[a-zäöüß]*|linderung[a-zäöüß]*)\b"),
        severity="hard",
        category="HWG-Krankheitsbezug",
        example="lindern, Linderung",
    ),
    _Rule(
        label="vorbeugen-stem",
        # Vorbeugung / vorbeugen - klassische "reduction_based" Sprache
        # ohne EFSA-Zulassung.
        pattern=_w(r"\bvorbeug[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Krankheitsvorbeugung",
        example="vorbeugen, Vorbeugung",
    ),
    _Rule(
        label="heilanzeige-stem",
        pattern=_w(r"\bheilanzeige[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Indikation",
        example="Heilanzeige",
    ),
    _Rule(
        label="beschwerde-medical",
        # "Beschwerde" im medizinischen Sinn (Magenbeschwerden, Beschwerden
        # lindern). Wir flaggen nur das Substantiv mit den klassischen
        # Komposita, nicht z. B. "Beschwerdeführer".
        pattern=_w(
            r"\b(?:magen|darm|gelenk|kopf|menstruations|verdauungs|"
            r"prostata|periode[n]?)beschwerde[a-zäöüß]*\b",
        ),
        severity="hard",
        category="HWG-Krankheitsbezug",
        example="Magenbeschwerden, Gelenkbeschwerden",
    ),
    _Rule(
        label="wirkmechanismus",
        # "Wirkmechanismus" / "wirkt gegen X" sind Wirkversprechen.
        pattern=_w(r"\bwirkmechanism[a-zäöüß]*\b"),
        severity="hard",
        category="HWG-Wirkversprechen",
        example="Wirkmechanismus",
    ),
)


# ---------------------------------------------------------------------------
# SOFT rules - HCVO Art. 10 Abs. 3 wellbeing / vitality patterns. Allowed
# in a finished marketing text *only* when bound to an authorised claim.
# In a rewrite output we treat them as forbidden because the rewrite is
# supposed to *remove* the original violation, not re-skin it.
# ---------------------------------------------------------------------------

_SOFT_RULES: tuple[_Rule, ...] = (
    _Rule(
        label="wohlbefinden",
        # "Wohlbefinden" in jeder Form (mentales/körperliches/allgemeines
        # Wohlbefinden, zum Wohlbefinden beitragen, …).
        pattern=_w(r"\bwohlbefinden[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Art10Abs3-Wohlbefinden",
        example="Wohlbefinden, zum Wohlbefinden beitragen",
    ),
    _Rule(
        label="entspannung-stem",
        # Entspannung, entspannend, zur Entspannung beitragen. Allgemeine
        # Entspannungs-Werbung ist HCVO-pflichtig (keine EFSA-Zulassung
        # für Botanicals).
        pattern=_w(r"\bentspann(?:ung|end|t|en)[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Art10Abs3-Wohlbefinden",
        example="Entspannung, entspannend, zur Entspannung beitragen",
    ),
    _Rule(
        label="widerstandsfaehigkeit",
        # Widerstandskraft / Widerstandsfähigkeit - Synonym für
        # Immunsystem ohne EFSA-Wortlaut.
        pattern=_w(r"\bwiderstands(?:kraft|fähigkeit|faehigkeit)[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Synonym-Immunsystem",
        example="Widerstandskraft, Widerstandsfähigkeit",
    ),
    _Rule(
        label="abwehrkraft",
        # Abwehrkraft / Abwehrkräfte - klassisches Synonym für
        # Immunsystem.
        pattern=_w(r"\babwehrkr(?:aft|äfte|aefte)[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Synonym-Immunsystem",
        example="Abwehrkräfte, Abwehrkraft stärken",
    ),
    _Rule(
        label="vitalitaet",
        pattern=_w(r"\bvitalit(?:ät|aet)[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Art10Abs3-Wohlbefinden",
        example="Vitalität",
    ),
    _Rule(
        label="boosten",
        # "boostet", "Booster" - Marketing-Slang, oft Wirkversprechen.
        pattern=_w(r"\bboost(?:e[nrst]?|er[a-zäöüß]*)\b"),
        severity="soft",
        category="HCVO-Wirkversprechen-Slang",
        example="boosten, Booster",
    ),
    _Rule(
        label="mentale-anspannung",
        # "Phasen mentaler Anspannung", "mentale Anspannung" - Stress-
        # Synonyme ohne Zulassung.
        pattern=_w(r"\bmentale[rmns]?\s+anspannung[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Stresskontext",
        example="mentale Anspannung",
    ),
    _Rule(
        label="koerperliche-anspannung",
        pattern=_w(
            r"\bkörperliche[rmns]?\s+anspannung[a-zäöüß]*\b"
            r"|\bkoerperliche[rmns]?\s+anspannung[a-zäöüß]*\b",
        ),
        severity="soft",
        category="HCVO-Stresskontext",
        example="körperliche Anspannung",
    ),
    _Rule(
        label="mentales-wohlbefinden",
        # Auch wenn "wohlbefinden" schon greift - dieses Pattern ist
        # spezifisch genug, dass wir es eigenständig labeln, damit die
        # Sperrliste-Erklärung im LLM-Retry gezielter wird.
        pattern=_w(r"\bmental(?:e[srn]?)?\s+wohlbefinden[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Art10Abs3-Wohlbefinden",
        example="mentales Wohlbefinden",
    ),
    _Rule(
        label="foerderung-wohlbefinden",
        pattern=_w(
            r"\bf(?:ö|oe)rderung\s+(?:de[srn]?\s+)?wohlbefinden[a-zäöüß]*\b",
        ),
        severity="soft",
        category="HCVO-Art10Abs3-Wohlbefinden",
        example="Förderung des Wohlbefindens",
    ),
    _Rule(
        label="adaptogen-term",
        # "Adaptogen" / "adaptogene Eigenschaft" - OLG Celle und OLG
        # München werten den Begriff als unzulässige gesundheitsbezogene
        # Angabe. Soft (nicht hart), weil eine bewusste, eingeordnete
        # Erwähnung als Tradition manchmal akzeptabel ist - aber im
        # Werbe-Kontext alleinstehend riskant.
        pattern=_w(r"\badaptogen[a-zäöüß]*\b"),
        severity="soft",
        category="HCVO-Adaptogen-Begriff",
        example="Adaptogen, Adaptogene, adaptogene Eigenschaft",
    ),
)


_ALL_RULES: tuple[_Rule, ...] = _HARD_RULES + _SOFT_RULES


def find_forbidden_terms(
    text: str,
    *,
    severities: tuple[Severity, ...] = ("hard", "soft"),
) -> list[ForbiddenTermHit]:
    """Return every forbidden-term hit in ``text``.

    Matches are returned in order of occurrence. Overlapping rules can
    each contribute a hit (e.g. ``mentales Wohlbefinden`` produces hits
    from both ``wohlbefinden`` and ``mentales-wohlbefinden``); de-dup
    happens in :func:`forbidden_terms_summary`.
    """
    if not text:
        return []
    hits: list[ForbiddenTermHit] = []
    for rule in _ALL_RULES:
        if rule.severity not in severities:
            continue
        for match in rule.pattern.finditer(text):
            hits.append(
                ForbiddenTermHit(
                    term=match.group(0),
                    pattern_label=rule.label,
                    severity=rule.severity,
                    category=rule.category,
                    start=match.start(),
                    end=match.end(),
                ),
            )
    hits.sort(key=lambda h: (h.start, h.end, h.pattern_label))
    return hits


def forbidden_terms_summary(hits: list[ForbiddenTermHit]) -> list[str]:
    """Return a deduplicated list of human-readable hit strings.

    Used in LLM retry prompts ("Du hast folgende Sperr-Begriffe verwendet:
    …"). Deduplicated case-insensitively so we don't repeat the same
    word ten times.
    """
    seen: set[str] = set()
    out: list[str] = []
    for hit in hits:
        key = hit.term.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(hit.term)
    return out


def sperrliste_block_for_prompt() -> str:
    """Return a static markdown block listing all forbidden vocabulary.

    Embedded verbatim into every reformulation prompt so the LLM is
    aware of the deterministic guardrail before it generates anything.
    Updating this list is the single source of truth - the regex rules
    and this human-readable list live together.
    """
    hard_examples = sorted({rule.example for rule in _HARD_RULES})
    soft_examples = sorted({rule.example for rule in _SOFT_RULES})
    lines: list[str] = [
        "## Sperrliste - diese Begriffe darfst du NIE neu in den Text "
        "einbauen",
        "",
        "**HWG-/Medizin-Vokabular (hart verboten, niemals verwenden):**",
    ]
    lines.extend(f"- {ex}" for ex in hard_examples)
    lines.append("")
    lines.append(
        "**HCVO-Wohlbefinden-/Stress-/Vitalitäts-Sprache (in Rewrites "
        "ebenfalls tabu, weil der Original-Verstoß genau hier liegt):**",
    )
    lines.extend(f"- {ex}" for ex in soft_examples)
    lines.append("")
    lines.append(
        "Wenn du den Original-Verstoß ohne diese Begriffe nicht "
        "neutral umformulieren kannst, schreibe einen rein "
        "produktbeschreibenden Satz ohne gesundheitliche Aussage "
        "(z. B. Inhaltsstoff + sensorische Beschreibung oder rein "
        "traditionell-historisch).",
    )
    return "\n".join(lines)


def has_forbidden_terms(
    text: str,
    *,
    severities: tuple[Severity, ...] = ("hard", "soft"),
) -> bool:
    """Fast boolean variant of :func:`find_forbidden_terms`."""
    if not text:
        return False
    for rule in _ALL_RULES:
        if rule.severity not in severities:
            continue
        if rule.pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Claim-type mapping for deterministic hits. When the LLM-based detector
# misses a hit, the pipeline adds it as a synthetic DetectedClaim - this
# mapping tells the evaluation layer which HCVO category to treat the hit
# as. The defaults (``disease_based`` for hard, ``wellbeing_based`` for
# soft) cover anything not explicitly mapped.
# ---------------------------------------------------------------------------

_CLAIM_TYPE_FOR_LABEL: dict[str, str] = {
    "vorbeugen-stem": "reduction_based",
    "wirkmechanismus": "health_based",
    # Soft / wellbeing hits all map to wellbeing_based.
    "wohlbefinden": "wellbeing_based",
    "mentales-wohlbefinden": "wellbeing_based",
    "foerderung-wohlbefinden": "wellbeing_based",
    "entspannung-stem": "wellbeing_based",
    "widerstandsfaehigkeit": "wellbeing_based",
    "abwehrkraft": "wellbeing_based",
    "vitalitaet": "wellbeing_based",
    "boosten": "wellbeing_based",
    "mentale-anspannung": "wellbeing_based",
    "koerperliche-anspannung": "wellbeing_based",
    "adaptogen-term": "wellbeing_based",
}


def claim_type_for_hit(hit: ForbiddenTermHit) -> str:
    """Map a hit to a ``ClaimType`` literal (see ``schemas.claim``).

    Returns ``"disease_based"`` for unknown ``hard`` hits and
    ``"wellbeing_based"`` for unknown ``soft`` hits - matching how the
    HCVO categorises medicinal vs. general-wellbeing language.
    """
    mapped = _CLAIM_TYPE_FOR_LABEL.get(hit.pattern_label)
    if mapped:
        return mapped
    return "disease_based" if hit.severity == "hard" else "wellbeing_based"
