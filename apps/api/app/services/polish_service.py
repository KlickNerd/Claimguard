"""Final-pass language polish for the rewritten marketing text.

After the user accepts a batch of rewrites, the resulting text often has
small seams: a leftover comma, a singular/plural mismatch, an awkward
transition where the original wording was punchier than the cleaned-up
version. This service runs Sonnet over the whole document with a tightly
scoped polish prompt - the goal is to fix language without revisiting
compliance.

Crucial guarantee: the polish step is *not allowed* to upgrade or
downgrade any claim. If the cleaned input says "Cranberry-Kapseln -
traditionell verwendet" the output may not say "Cranberry-Kapseln helfen
bei Blasenentzündungen" again. The system prompt is explicit about that
and tool-use forces a single-string return so we can't get accidental
reasoning chatter.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from app.config import settings
from app.services.anthropic_client import (
    AnthropicServiceError,
    create_message_with_tool,
)
from app.services.forbidden_terms import (
    find_forbidden_terms,
    forbidden_terms_summary,
    sperrliste_block_for_prompt,
)
from app.services.rewrite_service import detect_addressing_form

logger = logging.getLogger(__name__)


_POLISH_TOOL: dict[str, Any] = {
    "name": "record_polished_text",
    "description": (
        "Record the language-polished version of the user's marketing text. "
        "Fix grammar, spelling, punctuation and transitions only. Do not "
        "change the legal substance of any health claim, do not add new "
        "claims, do not remove the disclaimers."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "polished_text": {
                "type": "string",
                "description": (
                    "The cleaned-up text in German, preserving the original "
                    "Markdown structure (#, ##, *, **, lists, blockquotes). "
                    "Same paragraph order as input."
                ),
            },
            "change_summary": {
                "type": "string",
                "description": (
                    "One short sentence in German naming what kind of edits "
                    "were made (e.g. 'Korrigierte Pluralformen und glattere "
                    "Übergänge'). Empty string if nothing was changed."
                ),
            },
        },
        "required": ["polished_text", "change_summary"],
    },
}


_SPERRLISTE_BLOCK = sperrliste_block_for_prompt()


_PROMPT_TEMPLATE = """Du bist Senior-Werbetexter und Schluss-Lektor für ein
Supplement-Label. Du bekommst einen deutschen Marketing-Text, in dem
einzelne Health Claims durch HCVO-konforme EU-Register-Formulierungen
ersetzt wurden. Diese sitzen aktuell wie Fremdkörper im Werbetext:
hölzerne Phrasen ohne Übergang, drangeklatschte Sätze, Anführungszeichen
um den ganzen Satz, Compliance-Klammern, doppelte Pflanzenlisten,
Anrede springt.

**Anrede im Text: {addressing_form}** ({addressing_hint})

{sperrliste_block}
{retry_warning}

Deine Aufgabe ist nicht Mikrokorrektur, sondern echtes
**Re-Writing Absatz für Absatz**. Geh den Text Block für Block durch
und schreibe jeden Absatz so, wie ein guter Werbetexter ihn
aufgeschrieben hätte - mit den zugelassenen Wortlauten organisch
eingebaut, nicht angeflanscht.

## Was du behältst (NICHT antasten)

1. **Markdown-Struktur**: Headlines (`#`, `##`, `###`), Listen
   (`*`, `1.`), **fett**, _kursiv_, Tabellen, Blockquotes, Links.
2. **Exakte EU-Register-Formulierungen wortgetreu**, also Phrasen vom
   Typ:
   * „trägt zu einer normalen Funktion des Immunsystems bei"
   * „trägt zur Erhaltung einer normalen Gehirnfunktion bei"
   * „trägt zu einem normalen Energiestoffwechsel bei"
   * „trägt zur Verringerung von Müdigkeit und Ermüdung bei"
   * „trägt zur Aufrechterhaltung eines normalen Cholesterinspiegels"
   * „trägt zum Schutz der Zellen vor oxidativem Stress bei"
   * „trägt zu einer normalen Muskelfunktion bei"
   * „trägt dazu bei, die Einschlafzeit zu verkürzen"
   Diese exakten Wortfolgen darfst du NICHT umformulieren. Du darfst
   sie aber in einen flüssigen Satz einbetten, der davor oder dahinter
   etwas zur Marke / zum Produkt sagt.
3. **Disclaimer / Hinweise**, die der User absichtlich gesetzt hat
   (z. B. „kein Ersatz für eine ausgewogene Ernährung").
4. **Faktenstand**: keine neuen Wirkungsversprechen, kein
   Krankheitsbezug, keine Übersteigerungen erfinden. Du schreibst nur
   den vorhandenen Inhalt geschmeidig.

## Was du aktiv aufräumst

5. **Anführungszeichen entfernen**, die ganze Werbesätze einrahmen.
   Im Marketing-Fließtext gehören keine Sätze in „…". Das ist immer
   Replace-Artefakt.
6. **Klammer-Anmerkungen ersatzlos streichen**, sobald sie nach
   Compliance-Memo aussehen:
   * `(Hinweis: …)`
   * `(Achtung: …)`
   * `(Rein historisch-kultureller Hinweis …)`
   * `(Wortlaut eng an EFSA-Antrag …)`
   * `(Pflichtangabe …)`
   * `(zugelassener Wortlaut gem. VO …)`
   * Auch wenn alternativ-Formulierungen in der Klammer stehen:
     **alles in der Klammer raus**, nur den Satz davor behalten.
7. **Platzhalter** wie `[Nährstoff X]`, `[Produkt Y]` durch eine
   passende konkrete Aussage ersetzen, die aus dem Kontext schlüssig
   ist. Wenn nichts Sinnvolles ableitbar ist, **streiche den ganzen
   Satz**.
8. **Code-Suffix-Müll** (`bei."r`, `…m)`, `…n)`, `..`) wegwerfen.
9. **Redundanzen reduzieren**: wenn dieselbe Pflanzenliste,
   Eigenschaft oder Aussage zwei- oder dreimal in zwei
   aufeinanderfolgenden Sätzen steht, behalte nur die stärkste
   Variante und ersetze die Wiederholungen durch Pronomen oder
   streiche sie.
10. **Anrede vereinheitlichen** auf {addressing_form}.

## Wie du formulierst

11. **Werbe-Ton, nicht Verordnung.** EU-Register-Wortlaute eingebaut,
    aber drumherum lebendig. Beispiel:
    - Schlecht: `Vitamin C trägt zu einer normalen Funktion des
      Immunsystems bei. Magnesium trägt zu einer normalen
      Muskelfunktion bei.`
    - Gut: `Wir setzen auf Vitamin C - es trägt zu einer normalen
      Funktion des Immunsystems bei - und auf Magnesium für eine
      normale Muskelfunktion.`
12. **Übergänge bauen**, wo Replace eine Lücke gerissen hat.
    Konjunktionen tauschen, Pronomen einsetzen, Sätze mergen, wenn
    sinnvoll.
13. **Kürzer ist besser.** Wenn ein Absatz nach Aufräumen nur noch
    aus drei statt sechs Sätzen besteht und stärker liest -
    perfekt.
14. **Pro Absatz im Original = ein Absatz im Output** (Markdown-Block-
    Grenze, also `\\n\\n`). Nicht Absätze zusammenwerfen, nicht
    aufteilen, außer ein Absatz war reine Wiederholung des
    vorherigen.

## Was du NICHT tust

- Keine neuen Compliance-Behauptungen oder Health Claims erfinden.
- Keine Krankheits-/Heilungsversprechen einschmuggeln, auch nicht
  versehentlich.
- Keine bereits zugelassenen Claims abschwächen oder ihre exakte
  Wortwahl ändern.
- Keine Disclaimer löschen.

==== TEXT ====
{text}
==== ENDE ====

Schreibe den Text Absatz für Absatz neu wie oben beschrieben. Rufe
dann das Tool ``record_polished_text`` mit dem fertigen Ergebnis auf.
``change_summary`` enthält 1-2 Sätze auf Deutsch, was du substanziell
geändert hast. Gib keine Prosa außerhalb des Tool-Calls."""


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


class PolishService:
    def __init__(
        self,
        *,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
    ) -> None:
        self._call = tool_caller or create_message_with_tool
        self._model = model or settings.anthropic_model_detection

    def polish(self, text: str) -> tuple[str, str]:
        """Return ``(polished_text, change_summary)``.

        Falls back to the input on Anthropic-side failures so the user
        never loses their composed document.
        """
        if not text or not text.strip():
            return text, ""
        started = time.perf_counter()
        addressing = detect_addressing_form(text)
        addressing_hint = {
            "du": "duzt den Leser durchgehend (du / dir / dein)",
            "sie": "siezt den Leser durchgehend (Sie / Ihnen / Ihr)",
            "neutral": (
                "verwendet keine direkte Anrede - bleibe ebenfalls "
                "neutral oder im Imperativ"
            ),
        }[addressing]
        base_params = {
            "text": text,
            "addressing_form": addressing,
            "addressing_hint": addressing_hint,
            "sperrliste_block": _SPERRLISTE_BLOCK,
        }

        polished, summary = self._call_polish_llm(base_params, retry_warning="")
        if polished is None:
            return text, ""

        # Polish is forbidden from introducing new claims (it's the
        # explicit promise of the service). Compare forbidden-term hits
        # in the polished output against the input. Anything NEW means
        # the polish smuggled in a wellbeing / HWG term that wasn't
        # there before - retry once, then fall back to the input so the
        # user never sees a polish that worsens their compliance.
        new_hits = _new_forbidden_hits(before=text, after=polished)
        if new_hits:
            forbidden_words = forbidden_terms_summary(new_hits)
            logger.info(
                "Polish introduced forbidden terms %r, retrying once",
                forbidden_words,
            )
            retry_warning = (
                "## ⚠️ Wiederholung: dein vorheriger Output hat neue "
                "Sperr-Begriffe eingebaut\n\n"
                "Folgende Begriffe waren im Input nicht enthalten und "
                "dürfen auch in deiner Politur nicht vorkommen:\n- "
                + "\n- ".join(forbidden_words)
                + "\n\nPolitur ist Sprach-Korrektur, **nicht** "
                "Marketing-Aufpeppen. Wenn der Input nüchtern war, "
                "bleibt er nüchtern."
            )
            polished, summary = self._call_polish_llm(
                base_params, retry_warning=retry_warning,
            )
            if polished is None:
                return text, ""
            still_new = _new_forbidden_hits(before=text, after=polished)
            if still_new:
                logger.warning(
                    "Polish still introduced forbidden terms after "
                    "retry %r, returning unpolished input",
                    [h.term for h in still_new],
                )
                return text, ""

        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Polish: %d chars in -> %d chars out (%d ms)",
            len(text),
            len(polished),
            elapsed,
        )
        return polished or text, summary

    def _call_polish_llm(
        self,
        base_params: dict[str, Any],
        *,
        retry_warning: str,
    ) -> tuple[str | None, str]:
        prompt = _PROMPT_TEMPLATE.format(retry_warning=retry_warning, **base_params)
        try:
            tool_input, _, _ = self._call(
                model=self._model,
                system=None,
                user_content=prompt,
                tool=_POLISH_TOOL,
                # Long pillar pages can run 4-6k tokens of input; the
                # rewritten paragraph-by-paragraph output may still be
                # roughly the same length minus redundancies, so we give
                # the model plenty of room rather than truncating the
                # tail of the page.
                max_tokens=16000,
            )
        except AnthropicServiceError as exc:
            logger.warning("Polish failed (anthropic): %s", exc)
            return None, ""
        except Exception as exc:
            logger.warning("Polish failed (unexpected): %s", exc)
            return None, ""
        polished = str(tool_input.get("polished_text") or "").strip()
        summary = str(tool_input.get("change_summary") or "").strip()
        return polished or None, summary


def _new_forbidden_hits(*, before: str, after: str) -> list[Any]:
    """Return forbidden-term hits from ``after`` whose lemma was not
    already present in ``before``.

    The polish service is allowed to keep pre-existing forbidden
    vocabulary untouched - the user may have intentionally left a
    contested term in their copy, and asking the polish step to
    "fix compliance" goes beyond its scope. We only flag NEW additions.
    """
    after_hits = find_forbidden_terms(after)
    if not after_hits:
        return []
    before_terms_lower = {
        h.term.lower() for h in find_forbidden_terms(before)
    }
    return [
        h for h in after_hits
        if h.term.lower() not in before_terms_lower
    ]
