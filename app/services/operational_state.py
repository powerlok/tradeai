"""Shared operational mode and kill switch backed by Redis."""
from __future__ import annotations

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

OPERATIONAL_STATES = {"PAPER", "TESTNET", "LIVE_DISABLED", "KILL_SWITCH"}
STATE_KEY = "trading:operational_state"


def entry_enabled(state: str) -> bool:
    return state.upper() in {"PAPER", "TESTNET"}


async def get_operational_state() -> str:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        value = await redis.get(STATE_KEY)
        return value if value in OPERATIONAL_STATES else settings.trading_mode.upper()
    except RedisError:
        return settings.trading_mode.upper()
    finally:
        await redis.aclose()


async def set_operational_state(state: str) -> str:
    normalized = state.upper()
    if normalized not in OPERATIONAL_STATES:
        raise ValueError(f"unsupported operational state: {state}")
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.set(STATE_KEY, normalized)
        return normalized
    finally:
        await redis.aclose()