"""Paragraph-aware compliance rewrite of an entire marketing text.

The previous "rewrite each claim, then string-replace" pipeline produced
nonsense whenever a claim sat inside a longer sentence: the Span-Replace
spliced a self-contained "Vitamin C trägt zu …" sentence into the middle
of a "Dabei werden unter anderem die …" wrapper, and the surrounding
grammar fell apart.

This service flips the model: instead of doing a span replace, we hand
each paragraph to Sonnet together with the **list of claims that touch
this paragraph** and their compliance status, and ask the model to
rewrite the *whole paragraph* such that the problematic statements are
neutralised in context. Paragraphs without claims pass through unchanged.

The unit of work is a paragraph (separated by ``\\n\\n``). Each paragraph
that contains at least one claim of status ``borderline``, ``forbidden``
or ``unclear`` is rewritten in a single Sonnet call, in parallel across
paragraphs.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

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
from app.services.rewrite_service import detect_addressing_form

logger = logging.getLogger(__name__)


_PARAGRAPH_TOOL: dict[str, Any] = {
    "name": "record_paragraph_rewrite",
    "description": (
        "Record the rewritten paragraph. The output replaces the original "
        "paragraph 1:1 - same paragraph boundary, same Markdown, but the "
        "problematic statements have been neutralised and the rest reads "
        "as natural marketing copy."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "rewritten_paragraph": {
                "type": "string",
                "description": (
                    "The full rewritten paragraph in German. Preserves any "
                    "leading Markdown markers (#, *, 1., >). No surrounding "
                    "explanation, no quotes, no compliance brackets."
                ),
            },
        },
        "required": ["rewritten_paragraph"],
    },
}


_SPERRLISTE_BLOCK = sperrliste_block_for_prompt()


_PROMPT_TEMPLATE = """Du bist Senior-Werbetexter mit Compliance-Wissen. Du
bekommst einen einzelnen Absatz aus einem deutschen Marketing-Text und
eine Liste der gesundheitsbezogenen Aussagen, die in diesem Absatz
rechtlich problematisch sind.

**Anrede im Gesamttext: {addressing_form}** ({addressing_hint})

## Original-Absatz

```
{paragraph}
```

## Problematische Aussagen in diesem Absatz

{claim_list}

{sperrliste_block}
{retry_warning}
## Was du tust

Schreibe den **gesamten Absatz** neu, sodass die oben genannten
problematischen Aussagen rechtlich konform werden. Du baust die
Reformulierungs-Vorschläge **als Inspiration** in den Fließtext ein -
**nicht 1:1**, sondern grammatikalisch und stilistisch passend zum
umgebenden Satz.

### Wichtige Regeln

1. **Nur den Inhalt umformulieren, der im Original steht.** Keine
   neuen Werbeaussagen erfinden, keine zusätzlichen Vorteile. Was im
   Original-Absatz nicht steht, kommt nicht in den Output.
2. **Markdown-Marker am Anfang erhalten**: Wenn der Absatz mit ``#``,
   ``##``, ``- ``, ``* `` oder ``1. `` beginnt, fängt dein Output
   exakt mit dem gleichen Marker an.
3. **Anrede konsistent halten**: {addressing_form}.
4. **Exakte EU-Register-Wortlaute wortgetreu übernehmen**, wenn ein
   Reformulierungs-Vorschlag einen enthält - z. B. „trägt zu einer
   normalen Funktion des Immunsystems bei". Diese Wortfolgen sind
   rechtlich pflichtig und dürfen nicht umformuliert werden, du baust
   sie aber organisch in den Satz ein.
5. **Kein Krankheitsbezug, keine Heilversprechen**, keine
   wissenschaftlichen Behauptungen über Wirkmechanismen, die nicht
   bereits durch einen zugelassenen Claim gedeckt sind.
6. **Anführungszeichen, Compliance-Klammern, Platzhalter** wie
   ``[Nährstoff X]`` oder ``(Hinweis: …)`` aus dem Reformulierungs-
   Vorschlag heraushalten - sie gehören nicht in den finalen Text.
7. **Werbe-Ton wahren**: Der Absatz soll gut lesbar sein, nicht wie
   eine Verordnung klingen.
8. **Länge**: Roughly so lang wie das Original, eher kürzer.
9. **Keine eigene Erklärung beifügen**, keine Meta-Kommentare. Nur
   der neu geschriebene Absatz im Tool-Call.

### Beispiel für die richtige Integration

Falsches Vorgehen: ``Dabei werden unter anderem die "Vitamin D trägt
zu einer normalen Funktion des Immunsystems bei." beschrieben…``
(Vollsatz mitten im Wrapper-Satz.)

Richtiges Vorgehen: ``Wir setzen auf eine Vitamin-D-Versorgung -
Vitamin D trägt zu einer normalen Funktion des Immunsystems bei.``
(EU-Wortlaut organisch eingewoben.)

Jetzt los: Schreibe den Absatz neu und rufe das Tool
``record_paragraph_rewrite`` mit dem Ergebnis auf."""


@dataclass(slots=True)
class _ParagraphSlice:
    """One paragraph from the source text plus the claims that touch it."""

    text: str
    start: int
    end: int
    claims: list[EvaluatedClaim]


_PARAGRAPH_SPLIT_RE = re.compile(r"\n{2,}")


def _split_paragraphs(text: str) -> list[tuple[str, int, int]]:
    """Return ``[(paragraph, start, end), …]`` keeping byte offsets so we
    can map ``EvaluatedClaim.position_start/end`` to a paragraph."""
    out: list[tuple[str, int, int]] = []
    cursor = 0
    for match in _PARAGRAPH_SPLIT_RE.finditer(text):
        para = text[cursor : match.start()]
        out.append((para, cursor, match.start()))
        cursor = match.end()
    if cursor <= len(text):
        out.append((text[cursor:], cursor, len(text)))
    return out


def _assign_claims_to_paragraphs(
    paragraphs: list[tuple[str, int, int]],
    claims: list[EvaluatedClaim],
    only_problematic: bool = True,
) -> list[_ParagraphSlice]:
    slices: list[_ParagraphSlice] = []
    for text, start, end in paragraphs:
        relevant: list[EvaluatedClaim] = []
        for claim in claims:
            if only_problematic and claim.status == "allowed":
                continue
            if claim.position_start >= start and claim.position_end <= end:
                relevant.append(claim)
        slices.append(
            _ParagraphSlice(text=text, start=start, end=end, claims=relevant),
        )
    return slices


class _ToolCaller(Protocol):
    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = ...,
        cache_system: bool = ...,
    ) -> tuple[dict[str, Any], int, int]: ...


class SmartApplyService:
    def __init__(
        self,
        *,
        tool_caller: _ToolCaller | None = None,
        model: str | None = None,
        max_concurrency: int = 4,
    ) -> None:
        self._call = tool_caller or create_message_with_tool
        self._model = model or settings.anthropic_model_detection
        self._max_concurrency = max_concurrency

    async def smart_apply(
        self,
        *,
        input_text: str,
        evaluated_claims: list[EvaluatedClaim],
    ) -> str:
        """Rewrite the input text paragraph by paragraph so that the
        ``borderline`` / ``forbidden`` / ``unclear`` claims are
        neutralised in context. Returns the joined rewritten text."""
        if not input_text.strip() or not evaluated_claims:
            return input_text

        paragraphs = _split_paragraphs(input_text)
        slices = _assign_claims_to_paragraphs(paragraphs, evaluated_claims)
        addressing = detect_addressing_form(input_text)

        started = time.perf_counter()
        sem = asyncio.Semaphore(self._max_concurrency)

        async def maybe_rewrite(slc: _ParagraphSlice) -> str:
            if not slc.claims:
                return slc.text
            async with sem:
                return await asyncio.to_thread(
                    self._rewrite_one_paragraph,
                    slc,
                    addressing,
                )

        rewritten = await asyncio.gather(
            *(maybe_rewrite(slc) for slc in slices),
        )

        # Re-stitch with the original paragraph separator. Two newlines is
        # the canonical Markdown paragraph break; we lose any wider
        # separator the user may have used, but that's a fair price for
        # consistent output.
        joined = "\n\n".join(p.rstrip() for p in rewritten if p.rstrip())
        logger.info(
            "smart_apply: %d paragraphs (%d rewritten) in %d ms",
            len(slices),
            sum(1 for s in slices if s.claims),
            int((time.perf_counter() - started) * 1000),
        )
        return joined

    def _rewrite_one_paragraph(
        self,
        slc: _ParagraphSlice,
        addressing: str,
    ) -> str:
        addressing_hint = {
            "du": "duzt den Leser durchgehend (du / dir / dein)",
            "sie": "siezt den Leser durchgehend (Sie / Ihnen / Ihr)",
            "neutral": "verwendet keine direkte Anrede",
        }[addressing]

        claim_list = self._format_claims(slc.claims)
        base_params = {
            "paragraph": slc.text,
            "claim_list": claim_list,
            "addressing_form": addressing,
            "addressing_hint": addressing_hint,
            "sperrliste_block": _SPERRLISTE_BLOCK,
        }

        rewritten = self._call_paragraph_llm(base_params, retry_warning="")
        if rewritten is None:
            return slc.text

        # Deterministic guard: any forbidden-term hit in the rewrite is
        # a failure - the whole point of smart_apply is to PRODUCE a
        # clean paragraph. Retry once with the offending terms named
        # explicitly; if it still fails, drop back to the original so
        # the user at least sees the unchanged paragraph (and the
        # corresponding claim card is still flagged for them).
        hits = find_forbidden_terms(rewritten)
        if hits:
            forbidden_words = forbidden_terms_summary(hits)
            logger.info(
                "smart_apply paragraph contained forbidden terms %r, "
                "retrying once",
                forbidden_words,
            )
            retry_warning = (
                "## ⚠️ Wiederholung: dein vorheriger Absatz enthielt "
                "Sperr-Begriffe\n\n"
                "Folgende Begriffe darfst du **auf keinen Fall** "
                "verwenden (auch keine Synonyme/Wortvarianten):\n- "
                + "\n- ".join(forbidden_words)
                + "\n\nFalls eine konforme Variante ohne diese Begriffe "
                "nicht möglich ist, streiche die problematische "
                "Wirkungsaussage komplett und beschreibe stattdessen "
                "nur Inhaltsstoff/Tradition/Sinneswahrnehmung."
            )
            rewritten = self._call_paragraph_llm(
                base_params, retry_warning=retry_warning,
            )
            if rewritten is None:
                return slc.text
            still_hits = find_forbidden_terms(rewritten)
            if still_hits:
                logger.warning(
                    "smart_apply paragraph still contained forbidden "
                    "terms after retry %r, keeping original paragraph",
                    [h.term for h in still_hits],
                )
                return slc.text

        return rewritten or slc.text

    def _call_paragraph_llm(
        self,
        base_params: dict[str, Any],
        *,
        retry_warning: str,
    ) -> str | None:
        prompt = _PROMPT_TEMPLATE.format(retry_warning=retry_warning, **base_params)
        try:
            tool_input, _, _ = self._call(
                model=self._model,
                system=None,
                user_content=prompt,
                tool=_PARAGRAPH_TOOL,
                max_tokens=2000,
            )
        except AnthropicServiceError as exc:
            logger.warning("smart_apply paragraph failed: %s", exc)
            return None
        except Exception as exc:
            logger.warning("smart_apply unexpected error: %s", exc)
            return None

        rewritten = str(tool_input.get("rewritten_paragraph") or "").strip()
        return rewritten or None

    @staticmethod
    def _format_claims(claims: list[EvaluatedClaim]) -> str:
        if not claims:
            return "(keine)"
        lines: list[str] = []
        for idx, claim in enumerate(claims, start=1):
            rewrite = (
                claim.rewrite_suggestion
                or "(kein Vorschlag - selbst sinnvoll umformulieren)"
            )
            block = (
                f"{idx}. Aussage: {claim.claim_text}\n"
                f"   - Status: {claim.status} (Risiko: {claim.risk_level})\n"
                f"   - Begründung: {claim.reasoning}\n"
                f"   - Reformulierungs-Vorschlag (als Inspiration, "
                f"nicht 1:1 einsetzen): {rewrite}"
            )
            lines.append(block)
        return "\n\n".join(lines)
