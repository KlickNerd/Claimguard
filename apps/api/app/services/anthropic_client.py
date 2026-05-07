from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic, APIConnectionError, APIStatusError, APITimeoutError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings


class AnthropicServiceError(RuntimeError):
    """Non-retryable failure talking to Anthropic."""


@dataclass(slots=True)
class TokenUsage:
    """Per-call token accounting, including prompt-cache hit/miss split.

    Anthropic prompt caching gives a 90 % discount on input tokens that
    are re-read from the cache. We track ``cache_read_input_tokens`` and
    ``cache_creation_input_tokens`` separately so the report-level cost
    estimate can apply the right rate.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0

    def add(self, other: TokenUsage) -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_read_input_tokens += other.cache_read_input_tokens
        self.cache_creation_input_tokens += other.cache_creation_input_tokens


_client: Anthropic | None = None


def get_anthropic_client() -> Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise AnthropicServiceError(
                "ANTHROPIC_API_KEY is not configured. Set it in apps/api/.env.",
            )
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


_RETRYABLE = (APIConnectionError, APITimeoutError)


def _is_retryable_status(exc: BaseException) -> bool:
    """Retry on 429 (rate limit) and 5xx server errors, not on 4xx client errors."""
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=9),
    retry=retry_if_exception_type(_RETRYABLE) | retry_if_exception_type(APIStatusError),
    retry_error_callback=lambda state: state.outcome.result()
    if state.outcome and not state.outcome.failed
    else None,
)
def create_message_with_tool(
    *,
    model: str,
    system: str | None,
    user_content: str,
    tool: dict[str, Any],
    max_tokens: int = 4096,
    cache_system: bool = False,
) -> tuple[dict[str, Any], int, int]:
    """Force a tool call and return ``(tool_input, input_tokens, output_tokens)``.

    Tool-use gives harder schema enforcement than JSON mode; we set
    ``tool_choice`` so the model cannot refuse to call the tool.

    When ``cache_system`` is true and the system prompt is non-empty,
    the system block is annotated with ``cache_control: ephemeral``.
    Anthropic then caches it for ~5 minutes, charging only 10 % of the
    normal input rate on every subsequent call that re-reads the same
    prompt - which is exactly what happens when we evaluate N claims of
    the same analysis with the same HCVO system prompt.
    """
    client = get_anthropic_client()

    system_param: str | list[dict[str, Any]]
    if cache_system and system:
        system_param = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            },
        ]
    else:
        system_param = system or ""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_content}],
        )
    except APIStatusError as exc:
        if not _is_retryable_status(exc):
            raise AnthropicServiceError(
                f"Anthropic API error {exc.status_code}: {exc.message}",
            ) from exc
        raise

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            return (
                dict(block.input),
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

    raise AnthropicServiceError(
        f"Model did not invoke required tool '{tool['name']}'",
    )


def create_message_with_tool_detailed(
    *,
    model: str,
    system: str | None,
    user_content: str,
    tool: dict[str, Any],
    max_tokens: int = 4096,
    cache_system: bool = False,
) -> tuple[dict[str, Any], TokenUsage]:
    """Same as :func:`create_message_with_tool` but returns full token
    accounting incl. the prompt-cache breakdown.

    This is the call shape the evaluator uses going forward; the older
    3-tuple wrapper is kept so existing callers (rewrite, polish,
    detection) don't all change at once.
    """
    client = get_anthropic_client()

    system_param: str | list[dict[str, Any]]
    if cache_system and system:
        system_param = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            },
        ]
    else:
        system_param = system or ""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
            messages=[{"role": "user", "content": user_content}],
        )
    except APIStatusError as exc:
        if not _is_retryable_status(exc):
            raise AnthropicServiceError(
                f"Anthropic API error {exc.status_code}: {exc.message}",
            ) from exc
        raise

    usage = response.usage
    detailed = TokenUsage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    )

    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            return dict(block.input), detailed

    raise AnthropicServiceError(
        f"Model did not invoke required tool '{tool['name']}'",
    )
