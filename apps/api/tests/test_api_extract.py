"""HTTP-level tests for /api/extract/pdf (PROJ-12)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_PDF = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "CELEX_32012R0432_DE_TXT.pdf"
)


@pytest.fixture(scope="module")
def sample_bytes() -> bytes:
    if not SAMPLE_PDF.exists():
        pytest.skip(f"Sample PDF missing at {SAMPLE_PDF}")
    return SAMPLE_PDF.read_bytes()


def test_extract_returns_text_and_page_count(sample_bytes: bytes) -> None:
    response = client.post(
        "/api/extract/pdf",
        files={"file": ("vo432.pdf", sample_bytes, "application/pdf")},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["page_count"] > 0
    assert data["char_count"] >= 1_000
    assert data["source_reference"] == "vo432.pdf"
    assert len(data["text"]) >= 1_000


def test_rejects_non_pdf_mime() -> None:
    response = client.post(
        "/api/extract/pdf",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "pdf_invalid_mime"


def test_rejects_garbage_payload() -> None:
    response = client.post(
        "/api/extract/pdf",
        files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "pdf_invalid"
