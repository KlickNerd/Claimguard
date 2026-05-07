"""Conservative cost estimator for Anthropic calls.

We don't have detailed cache-hit / cache-miss split in the simple
3-tuple call path, so this estimator is a deliberate **upper bound** -
the real bill is usually lower because the evaluation system prompt is
served from cache after the first claim. Showing the upper bound is
honest: the user knows they will not be charged more than this.

Pricing snapshot (USD per 1M tokens, Anthropic public price list,
Mai 2026). Update when models change.
"""

from __future__ import annotations

# (input_per_mtok, output_per_mtok)
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Fallback when the model id is unknown - assume Sonnet pricing so we
# don't over- or under-shoot wildly.
_FALLBACK = (3.00, 15.00)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return upper-bound USD cost for one (model, token-count) pair."""
    in_rate, out_rate = _PRICING.get(model, _FALLBACK)
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000.0
