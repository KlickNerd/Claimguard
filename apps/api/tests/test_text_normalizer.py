from app.services.text_normalizer import normalize_text


def test_strips_html_tags() -> None:
    raw = '<p>Magnesium <strong>stärkt</strong> <em>das Immunsystem</em>.</p>'
    assert normalize_text(raw) == "Magnesium stärkt das Immunsystem."


def test_fixes_mojibake() -> None:
    # "fÃ¼r" is the classic double-encoded utf-8 artefact for "für"
    assert normalize_text("Unser Produkt fÃ¼r jeden Tag.") == "Unser Produkt für jeden Tag."


def test_replaces_typographic_quotes_with_ascii() -> None:
    raw = "„Detox-Kur“ für alle"
    assert normalize_text(raw) == '"Detox-Kur" für alle'


def test_normalizes_crlf_to_lf() -> None:
    assert normalize_text("Zeile 1\r\nZeile 2\rZeile 3") == "Zeile 1\nZeile 2\nZeile 3"


def test_preserves_paragraph_breaks() -> None:
    text = "Absatz 1.\n\nAbsatz 2."
    assert normalize_text(text) == text
