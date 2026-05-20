"""Tests for the Redis sliding-window rate limiter.

We monkey-patch ``app.core.rate_limit.get_redis`` to return a fake
async Redis that records calls. The goal is to validate the logic
(limit check, fail-open on Redis errors), not Redis itself.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from redis.exceptions import RedisError

from app.core.rate_limit import check_rate_limit


class _FakePipe:
    def __init__(self, count: int) -> None:
        self._count = count
        self.calls: list[tuple[str, tuple, dict]] = []

    def zremrangebyscore(self, *args: Any, **kwargs: Any) -> _FakePipe:
        self.calls.append(("zremrangebyscore", args, kwargs))
        return self

    def zcard(self, *args: Any, **kwargs: Any) -> _FakePipe:
        self.calls.append(("zcard", args, kwargs))
        return self

    def zadd(self, *args: Any, **kwargs: Any) -> _FakePipe:
        self.calls.append(("zadd", args, kwargs))
        return self

    def expire(self, *args: Any, **kwargs: Any) -> _FakePipe:
        self.calls.append(("expire", args, kwargs))
        return self

    async def execute(self) -> list[Any]:
        # mirror the redis-py pipeline.execute() return order
        return [1, self._count, 1, True]

    async def __aenter__(self) -> _FakePipe:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _FakeRedis:
    def __init__(self, count_before: int = 0) -> None:
        self._count_before = count_before

    def pipeline(self, *, transaction: bool = True) -> _FakePipe:
        return _FakePipe(self._count_before)


class _BrokenRedis:
    def pipeline(self, *, transaction: bool = True) -> Any:
        raise RedisError("connection refused")


@pytest.mark.asyncio
async def test_allows_within_limit() -> None:
    fake = _FakeRedis(count_before=2)  # 2 already there, this would be the 3rd
    with patch("app.core.rate_limit.get_redis", return_value=fake):
        result = await check_rate_limit("user:42:analyses", limit=5, window_seconds=60)
    assert result.allowed is True
    assert result.remaining == 2  # 5 - 3 = 2
    assert result.retry_after_seconds == 0


@pytest.mark.asyncio
async def test_blocks_when_over_limit() -> None:
    fake = _FakeRedis(count_before=5)  # 5 already there, this is the 6th
    with patch("app.core.rate_limit.get_redis", return_value=fake):
        result = await check_rate_limit("user:42:analyses", limit=5, window_seconds=60)
    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after_seconds == 60


@pytest.mark.asyncio
async def test_fail_open_on_redis_error() -> None:
    """A broken Redis should NOT lock users out of the app."""
    with patch("app.core.rate_limit.get_redis", return_value=_BrokenRedis()):
        result = await check_rate_limit("user:42:analyses", limit=5, window_seconds=60)
    assert result.allowed is True
    assert result.remaining == 5  # full allowance reported on failure
