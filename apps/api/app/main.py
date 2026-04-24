from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analyses import router as analyses_router
from app.api.prompts import router as prompts_router
from app.config import settings
from app.services.prompt_loader import get_prompt_loader


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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
