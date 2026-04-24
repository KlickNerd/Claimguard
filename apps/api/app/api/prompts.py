from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.prompt import PromptMetadata, RenderedPrompt
from app.services.prompt_loader import (
    PromptLoader,
    PromptNotFoundError,
    PromptRenderError,
    get_prompt_loader,
)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class TaskListResponse(BaseModel):
    tasks: dict[str, list[str]] = Field(
        description="Available tasks with their versions (newest first).",
    )


class RenderRequest(BaseModel):
    variables: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None


@router.get("", response_model=TaskListResponse)
async def list_tasks(loader: PromptLoader = Depends(get_prompt_loader)) -> TaskListResponse:
    return TaskListResponse(tasks=loader.list_tasks())


@router.get("/{task}/metadata", response_model=PromptMetadata)
async def get_metadata(
    task: str,
    version: str | None = None,
    loader: PromptLoader = Depends(get_prompt_loader),
) -> PromptMetadata:
    try:
        return loader.get(task, version).metadata
    except PromptNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/{task}/render", response_model=RenderedPrompt)
async def render_prompt(
    task: str,
    payload: RenderRequest,
    loader: PromptLoader = Depends(get_prompt_loader),
) -> RenderedPrompt:
    try:
        return loader.render(task, payload.variables, version=payload.version)
    except PromptNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PromptRenderError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
