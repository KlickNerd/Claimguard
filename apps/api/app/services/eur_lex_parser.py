"""Parse Eur-Lex consolidated HTML into ``RegulationChunk`` objects.

Eur-Lex blocks programmatic fetching with HTTP 202 + anti-bot, so we expect
the user to save the consolidated HTML view from a browser:

    1. Open https://eur-lex.europa.eu/eli/reg/2006/1924/2014-12-13
    2. Save Page As… → "Webpage, complete" (Chrome) /
       Cmd+S → "Webseite, Quelltext" (Safari)
    3. Pass the saved .html to the import CLI

The parser is class-driven and tolerates missing optional structures (e.g.
articles with no subtitle, paragraphs without explicit numbering).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from lxml import html as lxml_html

from app.schemas.regulation import RegulationChunk

logger = logging.getLogger(__name__)


# Eur-Lex serves two different HTML layouts depending on the access path.
# OJ-style ("oj-*") shows up on the modern OJ-publication view, while the
# "consolidated text" view (the ELI URL we recommend) uses an older skin
# with shorter class names. We accept both by matching tokens that appear
# anywhere inside the class attribute.
_ARTICLE_TOKENS = (
    "oj-ti-art",
    "title-article-norm",
)
_ARTICLE_SUBTITLE_TOKENS = (
    "oj-sti-art",
    "stitle-article-norm",
)
_PARAGRAPH_TOKENS = (
    "oj-normal",
    "norm",  # consolidated view uses bare "norm"
)
_SECTION_TOKENS = (
    "oj-ti-section-1",
    "oj-ti-section-2",
    "oj-ti-section-3",
    "title-division-1",
    "title-division-2",
    "title-gr-seq-level-1",
)
_ANNEX_TOKENS = (
    "oj-doc-ti",
    "title-fam-member",
    "title-doc-last",
)


_ARTICLE_NUMBER_RE = re.compile(
    r"Artikel\s+(?P<num>\d+[a-z]?)",
    re.IGNORECASE,
)
_PARAGRAPH_PREFIX_RE = re.compile(
    r"^\s*\((?P<num>\d+)\)\s*",
)


def _has_class(element: object, tokens: Iterable[str]) -> bool:
    classes = (getattr(element, "get", lambda _k: None)("class") or "").lower()
    return any(token in classes for token in tokens)


def _normalise_whitespace(text: str) -> str:
    return " ".join(text.split())


def _extract_article_number(text: str) -> int | None:
    """„Artikel 7" → 7. Returns None if no number found."""
    match = _ARTICLE_NUMBER_RE.search(text)
    if not match:
        return None
    raw = match.group("num").rstrip("abcdefghijklmnopqrstuvwxyz")
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_paragraph_number(text: str) -> tuple[int | None, str]:
    """„(1) Diese Verordnung …" → (1, "Diese Verordnung …")."""
    match = _PARAGRAPH_PREFIX_RE.match(text)
    if match:
        return int(match.group("num")), text[match.end():].strip()
    return None, text


def parse_eur_lex_html(
    html_text: str,
    *,
    regulation_id: str,
    eur_lex_url: str,
) -> list[RegulationChunk]:
    """Parse a saved Eur-Lex HTML page into semantic regulation chunks."""
    if not html_text.strip():
        return []

    tree = lxml_html.fromstring(html_text)
    body_paragraphs = tree.xpath("//p[@class]")

    chunks: list[RegulationChunk] = []
    current_section: str | None = None
    current_article: int | None = None
    current_article_title: str | None = None
    auto_paragraph_counter = 0
    in_annex = False
    seen_paragraphs: set[tuple[int, int]] = set()

    for element in body_paragraphs:
        text = _normalise_whitespace(element.text_content() or "")
        if not text:
            continue

        if _has_class(element, _SECTION_TOKENS):
            current_section = text
            continue

        if _has_class(element, _ANNEX_TOKENS) and "anhang" in text.lower():
            in_annex = True
            current_article = None
            current_article_title = None
            current_section = text
            continue

        if _has_class(element, _ARTICLE_TOKENS):
            number = _extract_article_number(text)
            if number is None:
                continue
            current_article = number
            current_article_title = None
            auto_paragraph_counter = 0
            in_annex = False
            continue

        if _has_class(element, _ARTICLE_SUBTITLE_TOKENS) and current_article is not None:
            current_article_title = text
            continue

        if _has_class(element, _PARAGRAPH_TOKENS):
            if current_article is None and not in_annex:
                # Preamble / recital - skipped for MVP, retrieved nowhere.
                continue

            paragraph_number, body = _extract_paragraph_number(text)
            if paragraph_number is None:
                auto_paragraph_counter += 1
                paragraph_number = auto_paragraph_counter

            if current_article is not None:
                key = (current_article, paragraph_number)
                if key in seen_paragraphs:
                    # Eur-Lex sometimes duplicates paragraphs in nested divs;
                    # don't index them twice.
                    continue
                seen_paragraphs.add(key)
                chunk_id = f"{regulation_id}-art{current_article}-para{paragraph_number}"
            else:
                chunk_id = f"{regulation_id}-anhang-{len(chunks) + 1}"

            chunks.append(
                RegulationChunk(
                    regulation_id=regulation_id,
                    chunk_id=chunk_id,
                    article=current_article,
                    article_title=current_article_title,
                    paragraph=paragraph_number,
                    text=body,
                    section=current_section,
                    is_annex=in_annex,
                    eur_lex_url=eur_lex_url,
                ),
            )

    return chunks
