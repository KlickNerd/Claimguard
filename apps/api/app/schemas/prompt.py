from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

PromptTask = Literal["claim_detection", "claim_evaluation"]


class PromptMetadata(BaseModel):
    """YAML frontmatter of a versioned prompt file."""

    task: PromptTask
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", description="SemVer version")
    model: str = Field(description="Anthropic model id, e.g. claude-sonnet-4-6")
    author: str
    created_at: date
    description: str


class PromptTemplate(BaseModel):
    """Loaded prompt: metadata + raw Jinja2 template body."""

    metadata: PromptMetadata
    body: str = Field(description="Raw Jinja2 template body without frontmatter")
    file_path: str

    @property
    def id(self) -> str:
        """Canonical identifier, e.g. `claim_detection@1.0.0`."""
        return f"{self.metadata.task}@{self.metadata.version}"


class RenderedPrompt(BaseModel):
    """Result of rendering a template with variables."""

    metadata: PromptMetadata
    rendered: str
    variables: dict[str, object]
