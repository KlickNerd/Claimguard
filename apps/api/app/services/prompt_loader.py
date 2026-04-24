from __future__ import annotations

from pathlib import Path
from threading import Lock

import frontmatter
from jinja2 import Environment, StrictUndefined, TemplateError

from app.schemas.prompt import PromptMetadata, PromptTemplate, RenderedPrompt


class PromptNotFoundError(LookupError):
    """No template registered for the requested task/version."""


class PromptRenderError(RuntimeError):
    """Jinja2 rendering failed (missing variable, syntax error)."""


class PromptLoader:
    """Loads versioned prompts from disk once at start, keeps them in memory.

    File layout: one Markdown file per prompt version under ``prompts_dir``,
    named ``<task>_v<semver>.md`` with YAML frontmatter that must pass
    :class:`PromptMetadata`. Jinja2 runs with ``StrictUndefined`` so a missing
    variable fails loudly instead of producing an empty LLM input.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._prompts_dir = prompts_dir
        self._templates: dict[str, PromptTemplate] = {}
        self._by_task: dict[str, list[str]] = {}
        self._lock = Lock()
        self._env = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        self._load_all()

    def _load_all(self) -> None:
        with self._lock:
            self._templates.clear()
            self._by_task.clear()
            for path in sorted(self._prompts_dir.glob("*.md")):
                template = self._load_file(path)
                self._templates[template.id] = template
                self._by_task.setdefault(template.metadata.task, []).append(
                    template.metadata.version,
                )
            # Sort versions descending so "latest" is index 0
            for versions in self._by_task.values():
                versions.sort(reverse=True, key=_semver_key)

    def _load_file(self, path: Path) -> PromptTemplate:
        post = frontmatter.load(path)
        metadata = PromptMetadata.model_validate(post.metadata)
        return PromptTemplate(
            metadata=metadata,
            body=post.content,
            file_path=str(path),
        )

    def list_tasks(self) -> dict[str, list[str]]:
        """Return ``{task: [versions...]}`` with newest version first per task."""
        return {task: list(versions) for task, versions in self._by_task.items()}

    def get(self, task: str, version: str | None = None) -> PromptTemplate:
        """Fetch a template. ``version=None`` returns the newest version of ``task``."""
        if version is None:
            versions = self._by_task.get(task)
            if not versions:
                raise PromptNotFoundError(f"No prompts registered for task '{task}'")
            version = versions[0]
        template_id = f"{task}@{version}"
        if template_id not in self._templates:
            raise PromptNotFoundError(f"Unknown prompt '{template_id}'")
        return self._templates[template_id]

    def render(
        self,
        task: str,
        variables: dict[str, object],
        version: str | None = None,
    ) -> RenderedPrompt:
        template = self.get(task, version)
        try:
            rendered = self._env.from_string(template.body).render(**variables)
        except TemplateError as exc:
            raise PromptRenderError(
                f"Render failed for {template.id}: {exc}",
            ) from exc
        return RenderedPrompt(
            metadata=template.metadata,
            rendered=rendered,
            variables=variables,
        )


def _semver_key(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


_default_loader: PromptLoader | None = None


def get_prompt_loader() -> PromptLoader:
    """Lazily create the module-level loader rooted at ``app/prompts``."""
    global _default_loader
    if _default_loader is None:
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        _default_loader = PromptLoader(prompts_dir)
    return _default_loader
