"""PDF-text extraction for the upload endpoint (PROJ-12).

Uses pdfplumber, which is already in the dep tree from the VO 432 importer
and handles the German Eur-Lex layouts well. We deliberately do not OCR -
scanned PDFs are out of scope for the MVP and the user gets a friendly
hint to paste the text manually.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

import pdfplumber

logger = logging.getLogger(__name__)


MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB hard cap, matches PROJ-12 spec
_MIN_TEXT_CHARS = 50  # below this we treat the PDF as scanned/empty


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be turned into useful text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(slots=True)
class PdfExtractionResult:
    text: str
    page_count: int
    char_count: int


def extract_pdf_text(content: bytes) -> PdfExtractionResult:
    """Return extracted text or raise ``PdfExtractionError`` with a stable code.

    Error codes the frontend can switch on:
    - ``pdf_too_large``: file exceeds 10 MB
    - ``pdf_invalid``: not a real PDF (magic bytes wrong, parser refuses)
    - ``pdf_encrypted``: password-protected
    - ``pdf_no_text``: empty or scanned (text below ``_MIN_TEXT_CHARS``)
    """
    if len(content) > MAX_PDF_BYTES:
        raise PdfExtractionError(
            "pdf_too_large",
            "Die Datei ist größer als 10 MB. Bitte kürze die PDF oder lade einen Auszug hoch.",
        )

    # Magic-byte sanity check - keeps the parser from working on garbage and
    # gives us a friendly error before pdfplumber's stack trace.
    if not content[:5].startswith(b"%PDF-"):
        raise PdfExtractionError(
            "pdf_invalid",
            "Die Datei sieht nicht wie eine PDF aus. Bitte lade eine echte PDF-Datei hoch.",
        )

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            page_count = len(pdf.pages)
            parts: list[str] = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text.strip())
    except Exception as exc:
        message = str(exc).lower()
        if "encrypted" in message or "password" in message:
            raise PdfExtractionError(
                "pdf_encrypted",
                (
                    "Diese PDF ist passwortgeschützt. Bitte entschlüssele "
                    "sie zuerst und lade sie erneut hoch."
                ),
            ) from exc
        logger.warning("PDF parse failed: %s", exc)
        raise PdfExtractionError(
            "pdf_invalid",
            "Die PDF konnte nicht gelesen werden. Möglicherweise ist sie beschädigt.",
        ) from exc

    text = "\n\n".join(parts).strip()
    if len(text) < _MIN_TEXT_CHARS:
        raise PdfExtractionError(
            "pdf_no_text",
            (
                "Diese PDF scheint gescannt oder bildbasiert zu sein. "
                "OCR wird im MVP nicht unterstützt - bitte füge den Text manuell ein."
            ),
        )

    return PdfExtractionResult(
        text=text,
        page_count=page_count,
        char_count=len(text),
    )
