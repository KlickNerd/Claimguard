"""Bulk-rewrite service for the 'Alle automatisch umschreiben' UX.

The full evaluator (PROJ-10) already returns a ``rewrite_suggestion`` for
every borderline / forbidden claim it processed. Two cases produce empty
rewrites today:

1. Disease-shortcut bypasses the LLM entirely - we set
   ``rewrite_suggestion = None`` because removing a disease claim is
   often "drop the line", not "paraphrase".
2. The Opus call schema-violated or timed out, so the claim came back
   without an evaluation at all.

For the user-facing 'rewrite everything' button we want a guaranteed
rewrite per claim. This service runs Sonnet (cheap, fast) per claim in
parallel and returns ``{claim_id: rewrite}``. Existing rewrites are
returned unchanged so we never overwrite a verified Opus suggestion.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, Literal, Protocol

from app.config import settings
from app.schemas.claim import EvaluatedClaim
from app.services.anthropic_client import (
    AnthropicServiceError,
    create_message_with_tool,
)
from app.services.forbidden_terms import (
    find_forbidden_terms,
    forbidden_terms_summary,
    sperrliste_block_for_prompt,
)

AddressingForm = Literal["du", "sie", "neutral"]

logger = logging.getLogger(__name__)


_REWRITE_TOOL: dict[str, Any] = {
    "name": "record_rewrite",
    "description": (
        "Record one HCVO-compliant rewrite for a single health claim. "
        "Stay close to the marketing intent but remove anything that "
        "violates the HCVO, LMIV, LFGB or HWG."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rewrite": {
                "type": "string",
                "description": (
                    "German rewrite of the claim. Must itself be a "
                    "compliant claim - no disease references, no "
                    "unauthorised wordings. If a clean rewrite is not "
                    "possible, return a neutral product description "
                    "instead (e.g. ingredient name + sensory note)."
                ),
            },
        },
        "required": ["rewrite"],
    },
}


_SPERRLISTE_BLOCK = sperrliste_block_for_prompt()


_PROMPT_TEMPLATE = """Du bist ClaimGuard's Reformulierungs-Assistent. Du tauschst
einen einzelnen Health Claim 1:1 gegen eine HCVO-konforme Variante aus,
die nahtlos in den umgebenden Text passt **und natürlich klingt** -
wie von einem menschlichen Marketing-Texter, nicht wie eine Verordnung.

Original-Claim: «{claim_text}»
Endet der Original-Claim mit Satzzeichen (.,!?;:): {ends_with_punctuation}
Status laut Vorprüfung: {status} (Risiko: {risk_level})
Begründung: {reasoning}
Anrede im umgebenden Text: **{addressing_form}** (übernimm sie 1:1)
{nutrient_block}
Umgebender Kontext (Original, ±120 Zeichen, Claim selbst markiert mit «»):
{context}

{sperrliste_block}
{retry_warning}
Inhaltliche Vorgaben:
1. Bei zugelassener Wortwahl (z. B. „trägt zur normalen Funktion von X bei")
   bleibe so nah am EU-Register wie möglich.
2. Krankheitsbezogene Aussagen (Heilung, Linderung, Vorbeugung) sind
   verboten - durch neutrale Produkt-/Sinneswahrnehmung ersetzen
   („traditionell verwendet", „mit angenehmem Geschmack", o. ä.).
3. Allgemeine Wohlbefindens-Sätze (Art. 10 Abs. 3 HCVO) sind nur als
   Begleitung eines konkret zugelassenen Claims erlaubt. Wenn du einen
   Begleitclaim brauchst, wähle einen **konkret passenden Nährstoff
   aus dem Kontext** (z. B. Vitamin D, Vitamin C, B-Vitamine, Cholin,
   Magnesium, Zink) und nenne ihn mit dem zugelassenen Wortlaut. **Niemals
   Platzhalter wie ``[Nährstoff einsetzen]`` oder ``[konkreten Claim
   ergänzen]`` zurückgeben** - das ist ein klarer Fehler.
4. **Keine neuen Inhalte hinzufügen**, die im umgebenden Kontext schon
   stehen (z. B. nicht erneut die Pflanzen-/Pilzliste wiederholen, wenn
   der Satz davor sie bereits aufzählt).

Stil-Vorgaben (klingt der Output wie ein Mensch?):
* **Werbe-Ton bewahren**: keine bürokratische Stapelei aus
  Verordnungs-Wortlaut. Lieber knackig + verständlich.
* **Anrede konsistent**: Der umgebende Text {addressing_hint}.
  Verwende *exakt* diese Anrede in deinem Rewrite. **Nicht** zwischen
  „Sie/Ihnen" und „du/dir" mischen.
* **Verschachtelte Satzkonstruktionen vermeiden** - lieber zwei kurze
  Hauptsätze als ein Bandwurm.

Form-Vorgaben (kritisch für sauberes Replace):
A. **Genau das ersetzen, was zwischen den «»-Markierungen steht** -
   nicht mehr und nicht weniger. Der Output ersetzt den Original-Claim
   im umgebenden Satz, ohne dass dort davor oder dahinter etwas
   nachjustiert werden muss.
B. **Punktuation matchen**: Wenn ``ends_with_punctuation`` = false ist,
   darf dein Output **nicht** mit ``.``, ``!`` oder ``?`` enden.
   Wenn = true, übernimm das Satzzeichen vom Original.
C. **Keine Anführungszeichen** am Anfang oder Ende deines Outputs.
   Auch keine eckigen Klammern, keine ``[]``, keine ``{{}}``. Der
   Output ist sauberer Fließtext.
D. **Länge**: maximal 30 % länger als der Original-Claim. Lieber
   kürzer als länger.
E. **Großschreibung**: Wenn der Original-Claim mit Großbuchstaben
   beginnt (Satzanfang oder Markdown-Headline), beginne ebenfalls
   groß. Sonst klein.
F. **Keine eigenen Sätze hinzufügen**, keine Aufzählungen, keine
   Erklärungen. Nur die Reformulierung.

Rufe das Tool ``record_rewrite`` mit deiner Reformulierung auf. Gib
keine Prosa, keine Erklärung, keine Anführungszeichen, keine eckigen
Klammern zurück."""


_CONTEXT_WINDOW = 120


class _ToolCaller(Protocol):
    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = ...,
    ) -> tuple[dict[str, Any], int, int]: ...


class RewriteService:
    def __init__(
        self,
        *,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
        max_concurrency: int = 5,
    ) -> None:
        self._call = tool_caller or create_message_with_tool
        self._model = model or settings.anthropic_model_detection
        self._max_concurrency = max_concurrency

    async def rewrite_all(
        self,
        *,
        claims: list[EvaluatedClaim],
        full_text: str,
    ) -> dict[str, str]:
        if not claims:
            return {}
        started = time.perf_counter()
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def bounded(claim: EvaluatedClaim) -> tuple[str, str | None]:
            async with semaphore:
                return await asyncio.to_thread(self._rewrite_one, claim, full_text)

        results = await asyncio.gather(*(bounded(c) for c in claims))
        out: dict[str, str] = {}
        for claim_id, rewrite in results:
            if rewrite:
                out[claim_id] = rewrite

        logger.info(
            "rewrite_all: %d/%d claims rewritten in %d ms",
            len(out),
            len(claims),
            int((time.perf_counter() - started) * 1000),
        )
        return out

    def _rewrite_one(
        self,
        claim: EvaluatedClaim,
        full_text: str,
    ) -> tuple[str, str | None]:
        # Already-rewritten claims from the original evaluation are kept
        # as-is - we don't want to second-guess Opus.
        if claim.rewrite_suggestion:
            return str(claim.id), claim.rewrite_suggestion

        nutrient_line = ""
        if claim.nutrient or claim.substance:
            label = claim.nutrient or claim.substance
            nutrient_line = f"Nährstoff/Substanz: {label}\n"

        ends_with_punct = bool(
            claim.claim_text and claim.claim_text.rstrip()[-1:] in ".!?;:",
        )

        addressing = detect_addressing_form(full_text)
        addressing_hint = {
            "du": "duzt den Leser (du / dir / dein)",
            "sie": "siezt den Leser (Sie / Ihnen / Ihr)",
            "neutral": (
                "verwendet keine direkte Anrede - bleibe ebenfalls "
                "neutral oder im Imperativ"
            ),
        }[addressing]

        base_params: dict[str, Any] = {
            "claim_text": claim.claim_text,
            "ends_with_punctuation": "true" if ends_with_punct else "false",
            "status": claim.status,
            "risk_level": claim.risk_level,
            "reasoning": claim.reasoning,
            "addressing_form": addressing,
            "addressing_hint": addressing_hint,
            "nutrient_block": nutrient_line,
            "context": self._marked_context(full_text, claim),
            "sperrliste_block": _SPERRLISTE_BLOCK,
        }

        # First attempt - no retry warning.
        rewrite = self._invoke_llm(claim, base_params, retry_warning="")
        if rewrite is None:
            return str(claim.id), None

        # Deterministic post-write guard: if the LLM smuggled in any
        # forbidden vocabulary (HWG terms or wellbeing patterns), retry
        # once with an explicit "you used these, do it again without".
        hits = find_forbidden_terms(rewrite)
        if hits:
            forbidden_words = forbidden_terms_summary(hits)
            logger.info(
                "Rewrite for %s used forbidden terms %r, retrying once",
                claim.id,
                forbidden_words,
            )
            retry_warning = (
                "## ⚠️ Wiederholung: dein vorheriger Versuch enthielt "
                "Sperr-Begriffe\n\n"
                "Folgende Begriffe darfst du **auf keinen Fall** wieder "
                "verwenden (auch keine Synonyme/Wortvarianten):\n- "
                + "\n- ".join(forbidden_words)
                + "\n\nFalls eine konforme Reformulierung ohne diese "
                "Begriffe nicht möglich ist, gib einen rein "
                "produktbeschreibenden Satz zurück (Inhaltsstoff + "
                "Sinneswahrnehmung oder rein historisch-traditionell) "
                "statt einer Wirkungsaussage."
            )
            rewrite = self._invoke_llm(claim, base_params, retry_warning=retry_warning)
            if rewrite is None:
                return str(claim.id), None
            still_forbidden = find_forbidden_terms(rewrite)
            if still_forbidden:
                logger.warning(
                    "Rewrite for %s still contained forbidden terms after "
                    "retry %r, dropping: %r",
                    claim.id,
                    [h.term for h in still_forbidden],
                    rewrite[:160],
                )
                return str(claim.id), None

        return str(claim.id), rewrite or None

    def _invoke_llm(
        self,
        claim: EvaluatedClaim,
        base_params: dict[str, Any],
        *,
        retry_warning: str,
    ) -> str | None:
        """Render the prompt, call the LLM, sanitise the result.

        Returns ``None`` on a hard sanitiser drop (placeholder leak,
        compliance-meta leak, or Anthropic-side failure) so the caller
        can stop the rewrite cleanly.
        """
        prompt = _PROMPT_TEMPLATE.format(retry_warning=retry_warning, **base_params)
        try:
            tool_input, _, _ = self._call(
                model=self._model,
                system=None,
                user_content=prompt,
                tool=_REWRITE_TOOL,
                max_tokens=400,
            )
        except AnthropicServiceError as exc:
            logger.warning("Rewrite failed for %s: %s", claim.id, exc)
            return None
        except Exception as exc:
            logger.warning("Unexpected rewrite error for %s: %s", claim.id, exc)
            return None

        rewrite = str(tool_input.get("rewrite") or "").strip()
        rewrite = _aggressive_clean(rewrite)
        rewrite = _strip_wrapping_quotes(rewrite)
        rewrite = _match_terminal_punct(rewrite, claim.claim_text)
        if _looks_like_template_placeholder(rewrite):
            logger.warning(
                "Rewrite for %s contained a template placeholder, dropping: %r",
                claim.id,
                rewrite,
            )
            return None
        if _has_compliance_meta(rewrite):
            logger.warning(
                "Rewrite for %s leaked compliance meta-comments, dropping: %r",
                claim.id,
                rewrite[:160],
            )
            return None
        return rewrite or None

    @staticmethod
    def _context(full_text: str, claim: EvaluatedClaim) -> str:
        """Backwards-compatible alias used by older tests."""
        return RewriteService._marked_context(full_text, claim)

    @staticmethod
    def _marked_context(full_text: str, claim: EvaluatedClaim) -> str:
        """Return the surrounding text with the claim wrapped in ``« … »``
        so the LLM can see exactly which span to replace and what comes
        before/after - without having to count characters."""
        start = max(0, claim.position_start - _CONTEXT_WINDOW)
        end = min(len(full_text), claim.position_end + _CONTEXT_WINDOW)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(full_text) else ""
        before = full_text[start : claim.position_start]
        target = full_text[claim.position_start : claim.position_end]
        after = full_text[claim.position_end : end]
        return f"{prefix}{before}«{target}»{after}{suffix}"


_DU_TOKENS = {
    "du", "dir", "dich", "dein", "deine", "deinem", "deinen", "deiner",
    "deines",
}
_SIE_TOKENS = {
    # Capitalisation matters here: "sie" = third-person feminine, "Sie" = formal.
    # We only count actual occurrences with proper case.
    "Sie", "Ihnen", "Ihr", "Ihre", "Ihrem", "Ihren", "Ihrer", "Ihres",
}
_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def detect_addressing_form(text: str) -> AddressingForm:
    """Guess which form of address dominates ``text``.

    Heuristic only - we tokenise on word boundaries and count occurrences
    of unambiguous Du-/Sie-pronouns. The polite "Sie" only counts when
    capitalised so we don't misclassify the third-person "sie haben"
    ("they have"). When the signal is mixed or absent we fall back to
    neutral, which the rewrite prompt translates into "no direct address".
    """
    if not text:
        return "neutral"
    du = 0
    sie = 0
    for match in _WORD_RE.finditer(text):
        word = match.group(0)
        if word.lower() in _DU_TOKENS:
            du += 1
        elif word in _SIE_TOKENS:
            sie += 1
    if du == 0 and sie == 0:
        return "neutral"
    if du >= sie * 2:
        return "du"
    if sie >= du * 2:
        return "sie"
    return "neutral"


# Patterns that look like the LLM left a template placeholder behind
# instead of producing a finished rewrite. We catch the obvious German
# instruction verbs ("einsetzen", "ergänzen", "nennen", ...) plus generic
# square-bracket TODO syntax.
_PLACEHOLDER_RE = re.compile(
    r"\[[^\]]*?(?:einsetzen|ergänzen|erganzen|nennen|wählen|waehlen|"
    r"hinzufügen|hinzufuegen|TODO|placeholder|konkret|z\.\s*B\.)[^\]]*?\]",
    flags=re.IGNORECASE,
)

# Generic "[Word X]" pattern. Catches `[Nährstoff X]`, `[Produkt Y]`,
# `[Wort]`-style placeholders that a Marketing-text would never use as
# a real bracketed annotation. False-positive risk is small: dosage
# annotations like `[800 IE]` start with a digit and are excluded.
_GENERIC_PLACEHOLDER_RE = re.compile(
    r"\[[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\- ]{1,30}\]",
)


def _looks_like_template_placeholder(text: str) -> bool:
    if _PLACEHOLDER_RE.search(text):
        return True
    return bool(_GENERIC_PLACEHOLDER_RE.search(text))


# Compliance-reasoning that Sonnet sometimes leaks into the rewrite
# field instead of keeping it in the chain-of-thought. If we see any of
# these, the "rewrite" is actually a meta-comment and we throw the
# whole thing away rather than ship it into the user's marketing copy.
_META_ANNOTATION_RE = re.compile(
    r"\(\s*(?:hinweis|achtung|achten|wortlaut|rein\s+(?:historisch|"
    r"prozesstechnisch|sachlich|beschreibend)|sofern\s+|alternativ|"
    r"pflichtangabe|gemäß\s+VO|zugelassener\s+wortlaut|on-hold|"
    r"art\.\s*\d+\s+hcvo)[^)]*\)",
    flags=re.IGNORECASE,
)
_META_KEYWORDS_INLINE = (
    "EFSA-Antrag",
    "Übergangsregime",
    "VO 1924/2006",
    "VO 432/2012",
    "VO (EG) Nr.",
    "VO (EU) Nr.",
    "Pflichtangabe",
    "zugelassener Wortlaut",
)


def _has_compliance_meta(text: str) -> bool:
    """Return True if the text reads like a compliance memo rather than a
    rewrite. Two heuristics: parenthetical instruction (``(Hinweis: ...)``)
    or two+ regulatory keywords sprinkled through a single sentence."""
    if _META_ANNOTATION_RE.search(text):
        return True
    keyword_hits = sum(1 for kw in _META_KEYWORDS_INLINE if kw in text)
    return keyword_hits >= 2


# Aggressive prefix/suffix cleaner. The rewrite shouldn't start or end
# with quotes, semicolons, double dots, or colons - those are all
# artefacts from Sonnet wrapping its rewrite as a quote.
_LEADING_NOISE_RE = re.compile(r"""^[\s„"«»''‚‛‹›:;,]+""")  # noqa: RUF001
_TRAILING_NOISE_RE = re.compile(r"""[\s„"«»''‚‛‹›:;,]+$""")  # noqa: RUF001
_DOUBLE_DOTS_RE = re.compile(r"\.{2,}")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.!?;:])")


def _aggressive_clean(text: str) -> str:
    """Strip noise that the LLM occasionally leaves at the boundaries
    or inside the rewrite (`..`, `." `, leading colons, etc.)."""
    text = text.strip()
    text = _LEADING_NOISE_RE.sub("", text)
    text = _TRAILING_NOISE_RE.sub("", text)
    text = _DOUBLE_DOTS_RE.sub(".", text)
    text = _SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    # Collapse internal `". "` sequences ("Satzende-Quote-Punkt-Quote")
    # back to a single space - it's never legitimate in a single-sentence
    # rewrite.
    text = re.sub(r'["„""«»]\s*\.', '.', text)
    text = re.sub(r'\.\s*["„""«»]', '.', text)
    return text.strip()


# Curly / typographic quote pairs the LLM might wrap a rewrite in.
# Ruff RUF001 sees these as ambiguous strings; that's exactly the point -
# we want to detect and strip them.
_QUOTE_PAIRS = [
    ("„", "“"),
    ("“", "”"),
    ("«", "»"),
    ("'", "'"),
    ("‘", "’"),  # noqa: RUF001
    ("‹", "›"),  # noqa: RUF001
    ('"', '"'),
]


def _strip_wrapping_quotes(text: str) -> str:
    """Drop matching quote pairs that the LLM occasionally wraps the
    rewrite in - those break the inline replace and look like garbage in
    the rendered text."""
    cleaned = text.strip()
    while cleaned:
        first, last = cleaned[:1], cleaned[-1:]
        match = next(
            ((o, c) for o, c in _QUOTE_PAIRS if first == o and last == c),
            None,
        )
        if not match:
            break
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _match_terminal_punct(rewrite: str, original: str) -> str:
    """Make the rewrite end with the same terminal punctuation as the
    original claim. Stops the classic '…einen festen Platz. und erleben…'
    bug that happens when the original is mid-sentence but the LLM
    closes its rewrite with a full stop."""
    if not rewrite:
        return rewrite
    end_punct = ".!?"
    original_terminal = original.rstrip()[-1:] if original.rstrip() else ""
    rewrite_terminal = rewrite.rstrip()[-1:]
    if original_terminal in end_punct:
        if rewrite_terminal not in end_punct:
            return rewrite.rstrip() + original_terminal
        return rewrite
    # Original mid-sentence - strip a trailing period the LLM added.
    if rewrite_terminal in end_punct:
        return rewrite.rstrip().rstrip(end_punct).rstrip()
    return rewrite
