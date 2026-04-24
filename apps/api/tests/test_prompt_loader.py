from datetime import date
from pathlib import Path
from textwrap import dedent

import pytest

from app.services.prompt_loader import (
    PromptLoader,
    PromptNotFoundError,
    PromptRenderError,
)


def write_prompt(
    directory: Path,
    task: str,
    version: str,
    body: str,
    model: str = "claude-sonnet-4-6",
) -> Path:
    path = directory / f"{task}_v{version}.md"
    path.write_text(
        dedent(
            f"""\
            ---
            task: {task}
            version: {version}
            model: {model}
            author: test
            created_at: 2026-04-24
            description: test prompt
            ---
            {body}
            """
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "prompts"
    directory.mkdir()
    return directory


def test_loads_single_prompt(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "Hallo {{ name }}")
    loader = PromptLoader(prompts_dir)

    template = loader.get("claim_detection")

    assert template.metadata.version == "1.0.0"
    assert template.metadata.task == "claim_detection"
    assert template.metadata.created_at == date(2026, 4, 24)
    assert "{{ name }}" in template.body


def test_returns_latest_version_by_default(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "v1")
    write_prompt(prompts_dir, "claim_detection", "1.2.0", "v1.2")
    write_prompt(prompts_dir, "claim_detection", "1.10.0", "v1.10")
    loader = PromptLoader(prompts_dir)

    template = loader.get("claim_detection")

    # 1.10.0 > 1.2.0 numerically, not lexicographically
    assert template.metadata.version == "1.10.0"


def test_can_request_specific_version(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "v1")
    write_prompt(prompts_dir, "claim_detection", "2.0.0", "v2")
    loader = PromptLoader(prompts_dir)

    assert loader.get("claim_detection", "1.0.0").body.strip() == "v1"
    assert loader.get("claim_detection", "2.0.0").body.strip() == "v2"


def test_unknown_task_raises(prompts_dir: Path) -> None:
    loader = PromptLoader(prompts_dir)

    with pytest.raises(PromptNotFoundError):
        loader.get("not_a_task")


def test_unknown_version_raises(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "v1")
    loader = PromptLoader(prompts_dir)

    with pytest.raises(PromptNotFoundError):
        loader.get("claim_detection", "9.9.9")


def test_render_substitutes_variables(prompts_dir: Path) -> None:
    write_prompt(
        prompts_dir,
        "claim_detection",
        "1.0.0",
        "Analysiere: {{ input_text }}",
    )
    loader = PromptLoader(prompts_dir)

    result = loader.render("claim_detection", {"input_text": "Test"})

    assert result.rendered.strip() == "Analysiere: Test"
    assert result.metadata.version == "1.0.0"


def test_missing_variable_raises_strict(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "{{ missing_var }}")
    loader = PromptLoader(prompts_dir)

    with pytest.raises(PromptRenderError):
        loader.render("claim_detection", {})


def test_list_tasks_orders_versions_newest_first(prompts_dir: Path) -> None:
    write_prompt(prompts_dir, "claim_detection", "1.0.0", "v1")
    write_prompt(prompts_dir, "claim_detection", "1.2.0", "v12")
    write_prompt(prompts_dir, "claim_evaluation", "1.0.0", "e1")
    loader = PromptLoader(prompts_dir)

    tasks = loader.list_tasks()

    assert tasks["claim_detection"] == ["1.2.0", "1.0.0"]
    assert tasks["claim_evaluation"] == ["1.0.0"]


def test_real_bundled_prompts_parse() -> None:
    """Guard against broken YAML frontmatter in the actual prompt files."""
    prompts_dir = Path(__file__).resolve().parents[1] / "app" / "prompts"
    loader = PromptLoader(prompts_dir)

    detection = loader.get("claim_detection")
    evaluation = loader.get("claim_evaluation")

    assert detection.metadata.model == "claude-sonnet-4-6"
    assert evaluation.metadata.model == "claude-opus-4-7"
