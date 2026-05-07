from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import AnyHttpUrl, BaseModel, Field

from app.services.pdf_extractor import (
    MAX_PDF_BYTES,
    PdfExtractionError,
    extract_pdf_text,
)
from app.services.url_extractor import UrlExtractionError, extract_url_text

router = APIRouter(prefix="/api/extract", tags=["extract"])


class UrlExtractRequest(BaseModel):
    url: AnyHttpUrl = Field(description="Public http(s) URL of the page to analyse.")


class UrlExtractResponse(BaseModel):
    text: str
    title: str | None
    final_url: str
    char_count: int
    source_reference: str


class PdfExtractResponse(BaseModel):
    text: str
    page_count: int
    char_count: int
    source_reference: str


@router.post(
    "/pdf",
    response_model=PdfExtractResponse,
)
async def extract_pdf(file: UploadFile = File(...)) -> PdfExtractResponse:
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "pdf_invalid_mime",
                "message": "Bitte eine PDF-Datei hochladen.",
            },
        )

    content = await file.read()
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "pdf_too_large",
                "message": "Die Datei ist größer als 10 MB.",
            },
        )

    try:
        result = extract_pdf_text(content)
    except PdfExtractionError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    return PdfExtractResponse(
        text=result.text,
        page_count=result.page_count,
        char_count=result.char_count,
        source_reference=file.filename or "Unbenannte Datei.pdf",
    )


@router.post(
    "/url",
    response_model=UrlExtractResponse,
)
async def extract_url(payload: UrlExtractRequest) -> UrlExtractResponse:
    try:
        result = extract_url_text(str(payload.url))
    except UrlExtractionError as exc:
        status_code = (
            status.HTTP_403_FORBIDDEN
            if exc.code == "url_blocked_by_robots"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    return UrlExtractResponse(
        text=result.text,
        title=result.title,
        final_url=result.final_url,
        char_count=result.char_count,
        source_reference=result.final_url,
    )
