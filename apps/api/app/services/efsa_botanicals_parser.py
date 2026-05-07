"""Parse the EFSA 'questions-on-hold-botanical-claims.xlsx' export.

Source file (downloaded once):
    https://www.efsa.europa.eu/sites/default/files/2021-06/questions-on-hold-botanical-claims.xlsx

That spreadsheet is the canonical EFSA on-hold list - 1548 rows, status
"Pending Risk Managers' decision". We map each row onto our
``BotanicalEntry`` schema (PROJ-19) so the retrieval pipeline can cite
each on-hold claim with a stable chunk_id of the form ``efsa-<applic_no>``.

Sheet layout (as of the 2024-11 publication):

| col index | header                                           |
|-----------|--------------------------------------------------|
| 0         | APPLIC. No                                       |
| 1         | MANDATE                                          |
| 2         | QUESTION No                                      |
| 3         | ORIGINAL FOOD AND HEALTH RELATIONSHIP            |
| 4         | REVISED FOOD                                     |
| 5         | REVISED HEALTH RELATIONSHIP                      |
| 6         | ORIGINAL WORDING                                 |
| 7         | REVISED WORDING                                  |
| 8         | RECEPTION DATE                                   |
| 9         | ACCEPTANCE DATE                                  |
| 10        | STATUS                                           |
| 11        | APPLICANT                                        |
| 12        | FOODSECTORAREA                                   |
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

logger = logging.getLogger(__name__)


_HEADER_ROW = 2  # header is on row 2; row 1 is a disclaimer banner
_DATA_START_ROW = 3


@dataclass(slots=True)
class EfsaBotanicalRow:
    applic_no: str
    food: str
    health_relationship: str
    original_wording: str
    revised_wording: str | None
    status_raw: str
    food_sector: str | None
    applicant: str | None


def _str(cell: Any) -> str:
    if cell is None:
        return ""
    return str(cell).strip()


def _split_food_and_relationship(combined: str) -> tuple[str, str]:
    """ORIGINAL FOOD AND HEALTH RELATIONSHIP looks like
    "693 - Evening Primrose Oil - Hormonal Health". Split off the leading
    application number, then return (food, health_relationship)."""
    if not combined:
        return ("", "")
    parts = [p.strip() for p in combined.split(" - ", maxsplit=2)]
    if len(parts) == 3:
        return (parts[1], parts[2])
    if len(parts) == 2:
        return (parts[0], parts[1])
    return (combined, "")


def _slug(value: str) -> str:
    """Best-effort URL slug for the chunk_id."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "x"


def parse_efsa_botanicals(xlsx_path: Path) -> list[EfsaBotanicalRow]:
    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    if "Sheet1" not in wb.sheetnames:
        raise ValueError(f"Sheet1 missing in {xlsx_path}; got {wb.sheetnames}")
    ws = wb["Sheet1"]

    rows: list[EfsaBotanicalRow] = []
    seen_ids: set[str] = set()
    for raw in ws.iter_rows(min_row=_DATA_START_ROW, values_only=True):
        applic_no = _str(raw[0])
        if not applic_no or not applic_no[0].isdigit():
            continue
        if applic_no in seen_ids:
            continue
        seen_ids.add(applic_no)

        food, hr = _split_food_and_relationship(_str(raw[3]))
        revised_food = _str(raw[4])
        revised_hr = _str(raw[5])
        if not food and revised_food:
            food = revised_food
        if not hr and revised_hr:
            hr = revised_hr

        rows.append(
            EfsaBotanicalRow(
                applic_no=applic_no,
                food=food,
                health_relationship=hr,
                original_wording=_str(raw[6]),
                revised_wording=_str(raw[7]) or None,
                status_raw=_str(raw[10]),
                food_sector=_str(raw[12]) or None,
                applicant=_str(raw[11]) or None,
            ),
        )
    wb.close()
    logger.info("Parsed %d EFSA on-hold rows from %s", len(rows), xlsx_path)
    return rows


def to_botanical_entry(row: EfsaBotanicalRow) -> dict:
    """Map a parsed row to a ``BotanicalEntry``-shaped dict.

    The full EFSA list is English; we keep ``common_name_de`` empty and let
    the embedding/FTS layer match on scientific/common-name strings. The
    summary is short by design - we only have what the spreadsheet gives
    us, so don't pretend to know more.
    """
    food = row.food or "Unbenanntes Botanical"
    relationship = row.health_relationship or "(keine Health-Relationship erfasst)"
    chunk_id = f"efsa-{row.applic_no}-{_slug(food)[:40]}"
    summary_parts = [
        f"EFSA-Antrag {row.applic_no}: {food} - {relationship}.",
    ]
    if row.original_wording:
        clipped = row.original_wording[:200]
        summary_parts.append(f"Beantragter Wortlaut: {clipped}.")
    summary_parts.append(
        "Status: EFSA on-hold, Übergangsregime nach Art. 28 HCVO. Werbung "
        "nahe am Original-Wortlaut bleiben, kein Krankheitsbezug.",
    )
    summary = " ".join(summary_parts)[:600]

    risk_notes: list[str] = []
    if row.food_sector:
        risk_notes.append(f"FoodSector: {row.food_sector}")
    if row.applicant:
        risk_notes.append(f"Antragsteller: {row.applicant}")

    return {
        "id": chunk_id,
        "scientific_name": food,
        "common_name_de": "",
        "common_names": [food, row.applic_no, row.original_wording[:80]],
        "status": "on_hold",
        "health_relationship": relationship,
        "pending_claim_de": None,
        "pending_claim_en": row.original_wording or None,
        "summary": summary,
        "risk_notes": risk_notes,
        "source_url": (
            "https://www.efsa.europa.eu/sites/default/files/2021-06/"
            "questions-on-hold-botanical-claims.xlsx"
        ),
    }
