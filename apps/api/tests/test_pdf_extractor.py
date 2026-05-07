"""Tests for the PDF text extractor used by /api/extract/pdf (PROJ-12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.pdf_extractor import (
    MAX_PDF_BYTES,
    PdfExtractionError,
    extract_pdf_text,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SAMPLE_PDF = DATA_DIR / "CELEX_32012R0432_DE_TXT.pdf"


@pytest.fixture(scope="module")
def sample_pdf_bytes() -> bytes:
    if not SAMPLE_PDF.exists():
        pytest.skip(f"Sample PDF missing at {SAMPLE_PDF}")
    return SAMPLE_PDF.read_bytes()


def test_real_pdf_extracts_german_text(sample_pdf_bytes: bytes) -> None:
    result = extract_pdf_text(sample_pdf_bytes)
    assert result.page_count > 0
    assert result.char_count >= 1_000
    # The Eur-Lex VO 432/2012 must contain at least one of these German tokens.
    lowered = result.text.lower()
    assert any(needle in lowered for needle in ("verordnung", "eu", "claim"))


def test_rejects_oversized_files() -> None:
    with pytest.raises(PdfExtractionError) as exc:
        extract_pdf_text(b"%PDF-1.4\n" + b"\x00" * (MAX_PDF_BYTES + 1))
    assert exc.value.code == "pdf_too_large"


def test_rejects_non_pdf_payload() -> None:
    with pytest.raises(PdfExtractionError) as exc:
        extract_pdf_text(b"hallo welt, ich bin kein pdf")
    assert exc.value.code == "pdf_invalid"


def test_rejects_corrupt_pdf_with_valid_header() -> None:
    # Magic bytes match but the content is garbage - pdfplumber should fail
    # and we surface ``pdf_invalid``.
    payload = b"%PDF-1.4\n" + b"not actually a pdf body"
    with pytest.raises(PdfExtractionError) as exc:
        extract_pdf_text(payload)
    assert exc.value.code == "pdf_invalid"
