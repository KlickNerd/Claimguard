from textwrap import dedent

from app.services.eur_lex_parser import parse_eur_lex_html


SAMPLE_HCVO_HTML = dedent("""
    <!DOCTYPE html>
    <html lang="de">
    <body>
      <p class="oj-doc-ti">VERORDNUNG (EG) Nr. 1924/2006</p>
      <p class="oj-ti-section-1">KAPITEL I</p>
      <p class="oj-ti-section-2">Allgemeine Bestimmungen</p>

      <p class="oj-ti-art">Artikel 1</p>
      <p class="oj-sti-art">Gegenstand und Anwendungsbereich</p>
      <p class="oj-normal">(1) Diese Verordnung harmonisiert die Rechts- und
        Verwaltungsvorschriften der Mitgliedstaaten über nährwert- und
        gesundheitsbezogene Angaben.</p>
      <p class="oj-normal">(2) Diese Verordnung gilt für nährwert- und
        gesundheitsbezogene Angaben, die in kommerziellen Mitteilungen gemacht werden.</p>

      <p class="oj-ti-art">Artikel 7</p>
      <p class="oj-sti-art">Nährwertdeklaration</p>
      <p class="oj-normal">Eine Nährwertdeklaration ist nach den Bestimmungen
        der Richtlinie 90/496/EWG verpflichtend, sofern eine nährwert- oder
        gesundheitsbezogene Angabe gemacht wird.</p>

      <p class="oj-ti-art">Artikel 10</p>
      <p class="oj-sti-art">Spezielle Bedingungen</p>
      <p class="oj-normal">(1) Gesundheitsbezogene Angaben sind verboten,
        sofern sie nicht den allgemeinen Anforderungen in Kapitel II und
        den speziellen Anforderungen in diesem Kapitel entsprechen.</p>
      <p class="oj-normal">(3) Verweise auf allgemeine, nicht spezifische Vorteile
        sind nur zulässig, wenn ihnen eine zugelassene gesundheitsbezogene Angabe
        beigefügt ist.</p>

      <p class="oj-doc-ti">ANHANG I</p>
      <p class="oj-normal">Liste der zugelassenen Angaben gemäß Artikel 13.</p>
    </body>
    </html>
""")


def parse() -> list:
    return parse_eur_lex_html(
        SAMPLE_HCVO_HTML,
        regulation_id="1924/2006",
        eur_lex_url="https://eur-lex.europa.eu/eli/reg/2006/1924/2014-12-13",
    )


def test_extracts_articles_with_paragraphs() -> None:
    chunks = parse()
    articles = sorted({c.article for c in chunks if c.article is not None})
    assert articles == [1, 7, 10]


def test_paragraph_numbering_preserves_eu_lex_numbers() -> None:
    chunks = parse()
    art10 = sorted(
        (c for c in chunks if c.article == 10),
        key=lambda c: c.paragraph or 0,
    )
    assert [c.paragraph for c in art10] == [1, 3]
    assert "verboten" in art10[0].text


def test_article_with_unnumbered_paragraph_falls_back_to_counter() -> None:
    chunks = parse()
    art7 = [c for c in chunks if c.article == 7]
    assert len(art7) == 1
    assert art7[0].paragraph == 1


def test_article_titles_are_attached() -> None:
    chunks = parse()
    art10_first = next(c for c in chunks if c.article == 10 and c.paragraph == 1)
    assert art10_first.article_title == "Spezielle Bedingungen"


def test_chunk_ids_are_stable_and_unique() -> None:
    chunks = parse()
    ids = [c.chunk_id for c in chunks if c.article is not None]
    assert len(ids) == len(set(ids))
    assert "1924/2006-art10-para1" in ids


def test_eur_lex_url_propagated() -> None:
    chunks = parse()
    assert all(c.eur_lex_url.startswith("https://eur-lex.europa.eu/") for c in chunks)


def test_annex_chunks_marked() -> None:
    chunks = parse()
    annex = [c for c in chunks if c.is_annex]
    assert len(annex) == 1
    assert "Liste der zugelassenen" in annex[0].text


def test_section_label_propagated() -> None:
    chunks = parse()
    art1_para1 = next(c for c in chunks if c.article == 1 and c.paragraph == 1)
    assert art1_para1.section == "Allgemeine Bestimmungen"


def test_empty_html_returns_no_chunks() -> None:
    assert parse_eur_lex_html("", regulation_id="x", eur_lex_url="https://example") == []
