"""Parse the Annex of Verordnung (EU) Nr. 432/2012 from its Eur-Lex PDF.

The PDF carries the regulation text on the first ~6 pages and then a
multi-page table of authorised health claims (Annex). The table has four
columns:

    1. Angabe (claim wording, DE)
    2. Bedingungen für die Verwendung der Angabe (conditions)
    3. Bedingungen und/oder Beschränkungen hinsichtlich der Verwendung
       (additional restrictions, often empty)
    4. Nummer im EFSA Journal (EFSA Journal reference)

Page breaks repeat the column header, which we filter out. Cells contain
soft hyphens (U+00AD) and intra-cell newlines that we collapse before
returning structured EuClaim objects.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from app.schemas.eu_claim import EuClaim

logger = logging.getLogger(__name__)


def _clean_cell(raw: str | None) -> str | None:
    """Drop soft hyphens, collapse intra-cell newlines, trim. Empty → None.

    Order matters: ``\\xad\\n`` (a soft hyphen at end-of-line - the EU PDF's
    way to mark word-breaks) must be collapsed to an empty string *before*
    we convert remaining newlines to spaces, otherwise hyphenated words like
    "Verrin\\xad\\ngerung" become "Verrin gerung" instead of "Verringerung".
    """
    if raw is None:
        return None
    # Step 1: end-of-line hyphenations - both soft (\xad) and visible "- \n"
    text = raw.replace("\xad\n", "").replace("­\n", "")
    text = text.replace("- \n", "").replace("-\n", "")
    # Step 2: remaining stray soft hyphens
    text = text.replace("\xad", "").replace("­", "")
    # Step 3: real intra-cell line breaks - those are word boundaries
    text = text.replace("\n", " ")
    # Step 4: collapse runs of whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _is_header_row(row: list[str | None]) -> bool:
    """Detect the column-header row, which repeats on every page.

    Column 0 is exactly "Angabe" on header rows, but the literal phrase
    "Die Angabe..." appears in column 1 of every body row, so we match
    only the trimmed first cell.
    """
    if not row:
        return True
    first = (row[0] or "").strip().lower()
    return first == "angabe"


def _looks_like_claim_row(row: list[str | None]) -> bool:
    """A real claim row has at least a claim text in the first column."""
    if not row or row[0] is None:
        return False
    cleaned = _clean_cell(row[0])
    return bool(cleaned and len(cleaned) > 10)


def _merge_conditions(primary: str | None, restrictions: str | None) -> str | None:
    """Bedingungen + (optional) Beschränkungen as one structured field."""
    parts: list[str] = []
    if primary:
        parts.append(primary)
    if restrictions:
        parts.append(f"Beschränkungen: {restrictions}")
    return " — ".join(parts) if parts else None


def parse_vo432_pdf(path: Path) -> list[EuClaim]:
    """Extract the Annex table from the VO 432/2012 PDF as EuClaim objects.

    Returns claims in document order with synthetic stable ids
    ``vo432-{seq}`` so re-imports stay deterministic.
    """
    claims: list[EuClaim] = []
    sequence = 0

    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    if _is_header_row(row) or not _looks_like_claim_row(row):
                        continue
                    sequence += 1

                    claim_text = _clean_cell(row[0])
                    conditions = _clean_cell(row[1] if len(row) > 1 else None)
                    restrictions = _clean_cell(row[2] if len(row) > 2 else None)
                    efsa_ref = _clean_cell(row[3] if len(row) > 3 else None)

                    claims.append(
                        EuClaim(
                            id=f"vo432-{sequence:03d}",
                            nutrient=_extract_nutrient_hint(claim_text or ""),
                            claim_de=claim_text,
                            claim_en=None,
                            conditions=_merge_conditions(conditions, restrictions),
                            health_relationship=efsa_ref,
                            status="authorised",
                            claim_type="art_13_1",
                            regulation_reference="Verordnung (EU) Nr. 432/2012",
                            commission_regulation="432/2012",
                        ),
                    )

    return claims


_NUTRIENT_HINT_RE = re.compile(
    r"^([A-ZÄÖÜ][\wÄäÖöÜüß \-]{2,40}?)\s+(?:trägt|hat|hilft|fördert|unterstützt|kann|ist)",
)


def _extract_nutrient_hint(claim_text: str) -> str | None:
    """Heuristic: take the first nominal phrase before the verb as nutrient hint.

    Not a full NER step — just a quick anchor for retrieval queries. The
    real nutrient mapping comes with PROJ-9 once Qdrant indexes the claims
    by embedding.
    """
    match = _NUTRIENT_HINT_RE.match(claim_text)
    if match:
        return match.group(1).strip()
    return None
