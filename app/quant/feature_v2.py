"""Additional causal features for Feature Engine 2.0."""
from __future__ import annotations

from math import log
from statistics import mean, pstdev
from typing import Sequence


def build_feature_v2(opens: Sequence[float], highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], volumes: Sequence[float], period: int = 14) -> dict[str, float]:
    if not closes or not (len(opens) == len(highs) == len(lows) == len(closes) == len(volumes)):
        raise ValueError("OHLCV sequences must be non-empty and have equal length")
    close = float(closes[-1])
    if close <= 0:
        raise ValueError("close must be positive")
    returns = [float(closes[index] / closes[index - 1] - 1.0) for index in range(1, len(closes)) if closes[index - 1] > 0]
    window_returns = returns[-period:]
    volume_window = [float(value) for value in volumes[-period:]]
    typical = [(float(high) + float(low) + float(close_value)) / 3.0 for high, low, close_value in zip(highs[-period:], lows[-period:], closes[-period:])]
    volume_total = sum(volume_window)
    vwap = sum(price * volume for price, volume in zip(typical, volume_window)) / volume_total if volume_total else close
    up_move = max(0.0, close / float(closes[max(0, len(closes) - period - 1)]) - 1.0) if closes[max(0, len(closes) - period - 1)] else 0.0
    down_move = max(0.0, float(closes[max(0, len(closes) - period - 1)]) / close - 1.0)
    direction = 1.0 if up_move >= down_move else -1.0
    return {
        "return_1": returns[-1] if returns else 0.0,
        "return_period": close / float(closes[max(0, len(closes) - period)]) - 1.0 if closes[max(0, len(closes) - period)] else 0.0,
        "range_pct": (float(highs[-1]) - float(lows[-1])) / close,
        "body_pct": (close - float(opens[-1])) / close,
        "upper_wick_pct": (float(highs[-1]) - max(float(opens[-1]), close)) / close,
        "lower_wick_pct": (min(float(opens[-1]), close) - float(lows[-1])) / close,
        "volatility": pstdev(window_returns) if len(window_returns) > 1 else 0.0,
        "volume_relative": float(volumes[-1]) / (mean(volume_window) or 1.0),
        "vwap_distance": close / vwap - 1.0 if vwap else 0.0,
        "trend_direction": direction,
        "trend_strength": abs(up_move - down_move),
    }
