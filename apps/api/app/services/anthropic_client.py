from __future__ import annotations

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
) -> tuple[dict[str, Any], int, int]:
    """Force a tool call and return ``(tool_input, input_tokens, output_tokens)``.

    Tool-use gives harder schema enforcement than JSON mode; we set
    ``tool_choice`` so the model cannot refuse to call the tool.
    """
    client = get_anthropic_client()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system or "",
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
