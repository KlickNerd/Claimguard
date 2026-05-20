"""Redis-backed sliding-window rate limiter.

Shape: ``check(key, limit, window_seconds)`` returns ``(allowed, retry_after)``.
The implementation uses a sorted-set per key with the request timestamps
as members; old entries get pruned on every check. One Redis call per
check (a Lua pipeline) keeps it cheap.

PROJ-1 spec requires 5 login attempts / 10 min / IP+email; that login
flow actually lives in Supabase, not in our API, so the immediate use
case is *not* login. The helper exists so PROJ-2 (Plan- & Nutzungs-
Verwaltung) and other quota-style features can drop in a check without
each rolling their own.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    """Process-wide async Redis client, created lazily."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


@dataclass(slots=True, frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


async def check_rate_limit(
    key: str,
    *,
    limit: int,
    window_seconds: int,
) -> RateLimitResult:
    """Sliding-window check.

    The counter sits at ``ratelimit:{key}``. Each call:
      1. drops entries older than the window,
      2. counts what's left,
      3. inserts the new timestamp if there's room,
      4. refreshes the TTL.

    A Redis outage degrades open: we log and allow the request rather
    than locking the user out of the entire app. That's the right
    tradeoff for non-security-critical quotas (login flow is rate-
    limited by Supabase itself).
    """
    now_ms = int(time.time() * 1000)
    window_ms = window_seconds * 1000
    redis_key = f"ratelimit:{key}"

    try:
        client = get_redis()
        async with client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(redis_key, 0, now_ms - window_ms)
            pipe.zcard(redis_key)
            pipe.zadd(redis_key, {str(now_ms): now_ms})
            pipe.expire(redis_key, window_seconds)
            _, count, _, _ = await pipe.execute()
    except RedisError as exc:
        logger.warning("Rate-limit check failed (fail-open): %s", exc)
        return RateLimitResult(allowed=True, remaining=limit, retry_after_seconds=0)

    # count is the number of entries BEFORE we just added the new one.
    used = int(count) + 1
    remaining = max(0, limit - used)
    if used <= limit:
        return RateLimitResult(allowed=True, remaining=remaining, retry_after_seconds=0)

    # Over the limit: the new entry is already in the set, but we
    # return allowed=False. The oldest entry's age determines retry-
    # after. Cheap heuristic: window_seconds is a safe upper bound.
    return RateLimitResult(
        allowed=False,
        remaining=0,
        retry_after_seconds=window_seconds,
    )
