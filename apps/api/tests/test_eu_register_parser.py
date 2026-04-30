from datetime import date as Date
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.eu_register_parser import parse_excel, parse_rows


SAMPLE_HEADER = (
    "Claim ID",
    "Nutrient, substance, food or food category",
    "Claim",
    "Claim DE",
    "Conditions of use of the claim",
    "Health relationship",
    "Status",
    "Claim Type",
    "Regulation",
    "Entry Date",
)

SAMPLE_ROWS = [
    (
        "EU-1234",
        "Magnesium",
        "Magnesium contributes to normal muscle function",
        "Magnesium trägt zu einer normalen Muskelfunktion bei",
        "Source of magnesium (15% NRV per 100 g)",
        "Maintenance of normal muscle function",
        "Authorised",
        "Article 13(1)",
        "Commission Regulation (EU) No 432/2012",
        Date(2012, 5, 25),
    ),
    (
        "EU-9999",
        "Detox blend",
        "Helps detoxify the body",
        None,
        None,
        None,
        "Non-authorised",
        "Article 13(1)",
        None,
        Date(2014, 1, 1),
    ),
    (
        "EU-7777",
        "Echinacea",
        "Supports the immune system",
        None,
        None,
        None,
        "On-hold",
        "Article 13(1)",
        None,
        None,
    ),
    # Trailing blank row that should be skipped
    (None, None, None, None, None, None, None, None, None, None),
]


def test_parse_rows_maps_authorised_claim() -> None:
    claims = list(parse_rows(SAMPLE_ROWS, SAMPLE_HEADER))
    assert len(claims) == 3

    first = claims[0]
    assert first.id == "EU-1234"
    assert first.nutrient == "Magnesium"
    assert first.claim_en.startswith("Magnesium contributes")
    assert first.claim_de.startswith("Magnesium trägt")
    assert first.status == "authorised"
    assert first.claim_type == "art_13_1"
    assert first.regulation_reference == "Commission Regulation (EU) No 432/2012"
    assert first.entry_date == Date(2012, 5, 25)


def test_parse_rows_handles_status_aliases() -> None:
    claims = list(parse_rows(SAMPLE_ROWS, SAMPLE_HEADER))
    statuses = [c.status for c in claims]
    assert statuses == ["authorised", "non_authorised", "on_hold"]


def test_parse_rows_skips_completely_empty_rows() -> None:
    claims = list(parse_rows(SAMPLE_ROWS, SAMPLE_HEADER))
    # 4 source rows minus 1 blank
    assert len(claims) == 3


def test_parse_rows_tolerates_alternate_header_phrasing() -> None:
    alt_header = (
        "Claim Identifier",
        "Substance",
        "Wording",
        "Claim (DE)",
        "Conditions",
        "Health benefit",
        "Outcome",
        "Article",
        "EC Regulation",
        "Date of Entry",
    )
    claims = list(parse_rows(SAMPLE_ROWS, alt_header))
    assert len(claims) == 3
    assert claims[0].id == "EU-1234"


def test_parse_rows_raises_when_id_column_missing() -> None:
    bad_header = (
        "Foo",
        "Bar",
        "Baz",
        "Qux",
        "Conditions",
        "Health",
        "Status",
        "Type",
        "Reg",
        "Date",
    )
    with pytest.raises(ValueError, match="Claim id"):
        list(parse_rows(SAMPLE_ROWS, bad_header))


def test_parse_excel_round_trip(tmp_path: Path) -> None:
    workbook_path = tmp_path / "fixture.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(SAMPLE_HEADER)
    for row in SAMPLE_ROWS:
        sheet.append(row)
    workbook.save(workbook_path)

    claims = parse_excel(workbook_path)

    assert len(claims) == 3
    assert {c.status for c in claims} == {"authorised", "non_authorised", "on_hold"}
