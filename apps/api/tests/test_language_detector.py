from app.services.language_detector import detect_primary_language, is_german


def test_detects_german() -> None:
    text = (
        "Unser Magnesium-Komplex unterstützt eine normale Muskelfunktion und "
        "sorgt für einen energiegeladenen Tag."
    )
    assert detect_primary_language(text) == "de"
    assert is_german(text)


def test_rejects_english() -> None:
    text = "Our magnesium complex supports healthy muscle function all day long."
    assert detect_primary_language(text) == "en"
    assert not is_german(text)


def test_empty_string_handled() -> None:
    # langdetect raises on empty; our wrapper must not leak that.
    assert detect_primary_language("") == "unknown"
    assert not is_german("")
