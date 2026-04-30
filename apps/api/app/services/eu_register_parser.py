"""Parse the EU Register of Health Claims from its official Excel export.

The EU Commission publishes the register on
https://ec.europa.eu/food/food-feed-portal/screen/health-claims-register
- click "Download all" to get an .xlsx file. There is no stable CSV/JSON
download endpoint, so this parser is built around the Excel column layout
the portal has used since 2020.

The parser is column-name driven (matches headers, not positions) so the
EU can swap column order without breaking us. New columns are tolerated -
they're simply ignored.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.schemas.eu_claim import EuClaim, EuClaimStatus, EuClaimType

# Header aliases - the EU portal has used several phrasings over the years.
# We match case-insensitively, trim whitespace, and drop punctuation.
_HEADER_ALIASES: dict[str, set[str]] = {
    "id": {"claim id", "id", "claim identifier", "register id"},
    "nutrient": {
        "nutrient, substance, food or food category",
        "nutrient",
        "substance",
    },
    "claim_en": {"claim", "claim text", "claim wording", "wording"},
    "claim_de": {"claim de", "claim (de)", "claim_de", "claim german"},
    "conditions": {
        "conditions of use of the claim",
        "conditions",
        "conditions of use",
    },
    "health_relationship": {
        "health relationship",
        "health benefit",
        "health relationship of the claim",
    },
    "status": {"status", "claim status", "outcome"},
    "claim_type": {
        "claim type",
        "type of claim",
        "article",
        "regulation article",
    },
    "regulation_reference": {
        "regulation",
        "commission regulation",
        "ec regulation",
        "eu regulation",
    },
    "entry_date": {
        "entry date",
        "date",
        "date of entry",
        "publication date",
    },
}

_STATUS_MAP: dict[str, EuClaimStatus] = {
    "authorised": "authorised",
    "authorized": "authorised",
    "approved": "authorised",
    "non-authorised": "non_authorised",
    "non authorised": "non_authorised",
    "non-authorized": "non_authorised",
    "rejected": "non_authorised",
    "not authorised": "non_authorised",
    "on-hold": "on_hold",
    "on hold": "on_hold",
    "pending": "on_hold",
}


def _normalize_header(raw: Any) -> str:
    if raw is None:
        return ""
    text = str(raw).strip().lower()
    for ch in (".", ",", ":", "(", ")", "/"):
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _resolve_column_map(headers: list[str]) -> dict[str, int]:
    """Return ``{schema_field: column_index}`` for every header we recognise."""
    normalized = [_normalize_header(h) for h in headers]
    mapping: dict[str, int] = {}
    for field, aliases in _HEADER_ALIASES.items():
        normalized_aliases = {_normalize_header(a) for a in aliases}
        for idx, header in enumerate(normalized):
            if header in normalized_aliases:
                mapping[field] = idx
                break
    return mapping


def _coerce_status(raw: Any) -> EuClaimStatus:
    if raw is None:
        return "non_authorised"
    key = _normalize_header(raw)
    return _STATUS_MAP.get(key, "non_authorised")


def _coerce_claim_type(raw: Any) -> EuClaimType:
    """Map free-form 'Article 13(1)' / '14.1.a' / etc. to our enum."""
    if raw is None:
        return "unknown"
    text = str(raw).lower().replace(" ", "")
    if "13(1)" in text or "13.1" in text or "13_1" in text:
        return "art_13_1"
    if "13(5)" in text or "13.5" in text:
        return "art_13_5"
    if "14(1)(a)" in text or "14.1.a" in text or "diseaseriskreduction" in text:
        return "art_14_1_a"
    if "14(1)(b)" in text or "14.1.b" in text or "children" in text:
        return "art_14_1_b"
    return "unknown"


def _coerce_date(raw: Any) -> Date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, Date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _str_or_none(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def parse_rows(
    rows: Iterable[tuple[Any, ...]],
    header_row: tuple[Any, ...],
) -> Iterator[EuClaim]:
    """Yield ``EuClaim`` objects from raw rows + header row.

    Rows missing both ``id`` and ``claim`` text are skipped silently - the EU
    Excel file occasionally has trailing blank rows or section dividers.
    """
    columns = _resolve_column_map(list(header_row))
    if "id" not in columns:
        raise ValueError(
            "EU register Excel is missing the 'Claim id' column. "
            f"Found headers: {[h for h in header_row if h]}",
        )

    def cell(row: tuple[Any, ...], field: str) -> Any:
        idx = columns.get(field)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    for row in rows:
        claim_id = _str_or_none(cell(row, "id"))
        claim_en = _str_or_none(cell(row, "claim_en"))
        claim_de = _str_or_none(cell(row, "claim_de"))
        if not claim_id and not claim_en and not claim_de:
            continue
        if not claim_id:
            # Synthesize a stable ID so the entry doesn't get dropped silently
            claim_id = f"unknown-{abs(hash((claim_en or '') + (claim_de or ''))) % 10**9}"

        yield EuClaim(
            id=claim_id,
            nutrient=_str_or_none(cell(row, "nutrient")),
            claim_de=claim_de,
            claim_en=claim_en,
            conditions=_str_or_none(cell(row, "conditions")),
            health_relationship=_str_or_none(cell(row, "health_relationship")),
            status=_coerce_status(cell(row, "status")),
            claim_type=_coerce_claim_type(cell(row, "claim_type")),
            regulation_reference=_str_or_none(cell(row, "regulation_reference")),
            commission_regulation=_str_or_none(cell(row, "regulation_reference")),
            entry_date=_coerce_date(cell(row, "entry_date")),
        )


def parse_excel(path: Path) -> list[EuClaim]:
    """Load every ``EuClaim`` from the Excel workbook at ``path``."""
    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    sheet = workbook.active
    if sheet is None:
        raise ValueError(f"No worksheet found in {path}")

    iterator = sheet.iter_rows(values_only=True)
    try:
        header_row = next(iterator)
    except StopIteration:
        return []

    return list(parse_rows(iterator, header_row))
