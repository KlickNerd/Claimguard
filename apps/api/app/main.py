import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.analyses import router as analyses_router
from app.api.extract import router as extract_router
from app.api.invites import router as invites_router
from app.api.me import router as me_router
from app.api.projects import router as projects_router
from app.api.prompts import router as prompts_router
from app.api.rewrites import router as rewrites_router
from app.config import settings
from app.services.prompt_loader import get_prompt_loader

# uvicorn's dictConfig wires handlers onto the ``uvicorn`` logger but
# leaves ``app.*`` with no handler at all, so logger.info() calls from
# our code propagate to root - and root defaults to WARNING. Attach an
# explicit StreamHandler at INFO and disable propagation so we get the
# per-stage pipeline logs in production without depending on uvicorn's
# default-handler quirks (and without double-printing through root).
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
if not _app_logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_h)
_app_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail-fast: parse all prompts on startup so broken YAML never reaches prod.
    get_prompt_loader()
    yield


app = FastAPI(
    title="ClaimGuard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompts_router)
app.include_router(analyses_router)
app.include_router(extract_router)
app.include_router(rewrites_router)
app.include_router(projects_router)
app.include_router(invites_router)
app.include_router(me_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Translate common schema errors into friendly German messages with
    stable error codes, so the frontend can switch on them instead of
    displaying raw Pydantic strings."""
    for error in exc.errors():
        location = error.get("loc", ())
        err_type = error.get("type", "")

        if location[:2] == ("body", "input_text"):
            if err_type == "string_too_long":
                max_len = error.get("ctx", {}).get("max_length", 20_000)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": {
                            "code": "input_too_long",
                            "message": (
                                f"Maximal {max_len:,} Zeichen erlaubt. "
                                "Bitte kürze den Text oder teile ihn in mehrere Analysen auf."
                            ).replace(",", "."),
                        },
                    },
                )
            if err_type == "string_too_short":
                min_len = error.get("ctx", {}).get("min_length", 50)
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "detail": {
                            "code": "input_too_short",
                            "message": (
                                f"Bitte mindestens {min_len} Zeichen eingeben, "
                                "damit eine sinnvolle Analyse möglich ist."
                            ),
                        },
                    },
                )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {
                "code": "schema_violation",
                "message": "Ungültige Eingabe.",
                "errors": exc.errors(),
            },
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
