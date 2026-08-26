"""Deterministic strategy signals for causal paper backtests."""
from __future__ import annotations

from typing import Sequence


def _sma(values: Sequence[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return sum(float(value) for value in values[-period:]) / period


def _rsi(values: Sequence[float], period: int) -> float | None:
    if period <= 0 or len(values) <= period:
        return None
    changes = [float(values[index]) - float(values[index - 1]) for index in range(len(values) - period, len(values))]
    gains = sum(max(change, 0.0) for change in changes) / period
    losses = sum(max(-change, 0.0) for change in changes) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100.0 - (100.0 / (1.0 + gains / losses))


def generate_signal(strategy_type: str, closes: Sequence[float], index: int, params: dict[str, float | int]) -> int:
    """Return 1 LONG, -1 SHORT, or 0 NO_TRADE using data through index only."""
    values = closes[: index + 1]
    strategy = strategy_type.lower()
    if strategy == "moving_average":
        fast = int(params.get("fast_period", 20))
        slow = int(params.get("slow_period", 50))
        fast_value = _sma(values, fast)
        slow_value = _sma(values, slow)
        if fast_value is None or slow_value is None:
            return 0
        return 1 if fast_value > slow_value else -1 if fast_value < slow_value else 0
    if strategy == "rsi_mean_reversion":
        period = int(params.get("rsi_period", 14))
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
        value = _rsi(values, period)
        if value is None:
            return 0
        return 1 if value <= oversold else -1 if value >= overbought else 0
    if strategy == "breakout":
        period = int(params.get("breakout_period", 20))
        if len(values) <= period:
            return 0
        window = [float(value) for value in values[-period - 1 : -1]]
        current = float(values[-1])
        return 1 if current > max(window) else -1 if current < min(window) else 0
    raise ValueError(f"unsupported strategy_type: {strategy_type}")


def available_strategies() -> list[dict[str, object]]:
    return [
        {"id": "moving_average", "name": "Cruzamento de médias", "parameters": {"fast_period": 20, "slow_period": 50}},
        {"id": "rsi_mean_reversion", "name": "Reversão pelo RSI", "parameters": {"rsi_period": 14, "oversold": 30, "overbought": 70}},
        {"id": "breakout", "name": "Breakout de máxima/mínima", "parameters": {"breakout_period": 20}},
    ]
