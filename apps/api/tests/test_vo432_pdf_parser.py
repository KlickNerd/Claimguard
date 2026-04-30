from app.services.vo432_pdf_parser import (
    _clean_cell,
    _is_header_row,
    _looks_like_claim_row,
    _merge_conditions,
    _extract_nutrient_hint,
)


# ----------------------------------------------------------------------------
# _clean_cell
# ----------------------------------------------------------------------------


def test_clean_cell_dehyphenates_word_breaks() -> None:
    raw = "Aktivkohle trägt zur Verrin\xad\ngerung übermäßiger Blähun\xad\ngen nach dem Essen bei"
    assert _clean_cell(raw) == (
        "Aktivkohle trägt zur Verringerung übermäßiger Blähungen nach dem Essen bei"
    )


def test_clean_cell_keeps_normal_word_breaks() -> None:
    raw = "Eine Zeile\nund noch eine"
    assert _clean_cell(raw) == "Eine Zeile und noch eine"


def test_clean_cell_handles_visible_dash_at_eol() -> None:
    raw = "Cholesterin- \nSpiegel"
    assert _clean_cell(raw) == "CholesterinSpiegel"


def test_clean_cell_collapses_double_spaces() -> None:
    assert _clean_cell("Foo   bar") == "Foo bar"


def test_clean_cell_returns_none_for_empty() -> None:
    assert _clean_cell(None) is None
    assert _clean_cell("") is None
    assert _clean_cell("   \n  ") is None


# ----------------------------------------------------------------------------
# _is_header_row
# ----------------------------------------------------------------------------


def test_is_header_row_detects_repeated_header() -> None:
    assert _is_header_row(["Angabe", "Bedingungen", None, "EFSA"])
    assert _is_header_row(["angabe", "anything", None, None])


def test_is_header_row_does_not_match_body_row_with_die_angabe() -> None:
    body = [
        "Calcium hat eine Funktion",
        "Die Angabe darf nur für Lebensmittel verwendet werden",
        None,
        "2010;8(10):1725",
    ]
    assert not _is_header_row(body)


def test_is_header_row_handles_empty_row() -> None:
    # The completely empty row case - claim_row filter handles None-rows separately
    assert _is_header_row([])


# ----------------------------------------------------------------------------
# _looks_like_claim_row
# ----------------------------------------------------------------------------


def test_looks_like_claim_row_requires_first_column_text() -> None:
    assert _looks_like_claim_row(["Vitamin C trägt zur ...", "Die Angabe ..."])
    assert not _looks_like_claim_row([None, "anything"])
    assert not _looks_like_claim_row(["", "anything"])
    # Too short to be a claim
    assert not _looks_like_claim_row(["abc", "anything"])


# ----------------------------------------------------------------------------
# _merge_conditions
# ----------------------------------------------------------------------------


def test_merge_conditions_combines_with_separator() -> None:
    merged = _merge_conditions("Mindestmenge 15 % NRV", "Nicht für Kinder unter 3 Jahren")
    assert merged is not None
    assert "Mindestmenge" in merged
    assert "Beschränkungen: Nicht für Kinder" in merged


def test_merge_conditions_returns_primary_only_when_no_restrictions() -> None:
    assert _merge_conditions("Mindestmenge", None) == "Mindestmenge"


def test_merge_conditions_returns_none_when_both_empty() -> None:
    assert _merge_conditions(None, None) is None


# ----------------------------------------------------------------------------
# _extract_nutrient_hint
# ----------------------------------------------------------------------------


def test_extract_nutrient_hint_picks_subject() -> None:
    assert _extract_nutrient_hint("Vitamin C trägt zur normalen Funktion bei") == "Vitamin C"
    assert _extract_nutrient_hint("Magnesium hat eine Funktion") == "Magnesium"


def test_extract_nutrient_hint_returns_none_for_complex_sentences() -> None:
    text = "Die Aufnahme von Arabinoxylan als Bestandteil einer Mahlzeit trägt dazu bei…"
    # Begins with article, not a nutrient name - return None rather than guess.
    assert _extract_nutrient_hint(text) is None
