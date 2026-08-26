from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable


class QualityStatus(StrEnum):
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"


@dataclass(frozen=True)
class QualityResult:
    status: QualityStatus
    issues: tuple[str, ...] = field(default_factory=tuple)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def validate_candle(candle: dict[str, Any], now_ms: int | None = None) -> QualityResult:
    required = ("open_time", "close_time", "open", "high", "low", "close", "volume")
    missing = [field_name for field_name in required if field_name not in candle]
    if missing:
        return QualityResult(QualityStatus.INVALID, (f"missing:{','.join(missing)}",))

    timestamps = {field_name: _number(candle[field_name]) for field_name in ("open_time", "close_time")}
    prices = {field_name: _number(candle[field_name]) for field_name in ("open", "high", "low", "close", "volume")}
    invalid_numbers = [name for name, value in {**timestamps, **prices}.items() if value is None]
    if invalid_numbers:
        return QualityResult(QualityStatus.INVALID, (f"non_finite:{','.join(invalid_numbers)}",))

    open_time = int(timestamps["open_time"])
    close_time = int(timestamps["close_time"])
    open_price = prices["open"]
    high_price = prices["high"]
    low_price = prices["low"]
    close_price = prices["close"]
    volume = prices["volume"]
    assert open_price is not None and high_price is not None and low_price is not None
    assert close_price is not None and volume is not None

    issues: list[str] = []
    if open_time <= 0 or close_time <= open_time:
        issues.append("invalid_timestamp_order")
    if min(open_price, high_price, low_price, close_price) <= 0:
        issues.append("non_positive_price")
    if high_price < max(open_price, low_price, close_price):
        issues.append("high_below_ohlc")
    if low_price > min(open_price, high_price, close_price):
        issues.append("low_above_ohlc")
    if volume < 0:
        issues.append("negative_volume")
    if issues:
        return QualityResult(QualityStatus.INVALID, tuple(issues))

    current_time = int(time.time() * 1000) if now_ms is None else now_ms
    warnings: list[str] = []
    if close_time >= current_time:
        warnings.append("incomplete_candle")
    candle_range = (high_price - low_price) / close_price
    if candle_range > 0.25:
        warnings.append("extreme_range")
    return QualityResult(QualityStatus.WARNING if warnings else QualityStatus.VALID, tuple(warnings))


def validate_candle_series(candles: Iterable[dict[str, Any]], timeframe_ms: int | None = None) -> QualityResult:
    items = list(candles)
    issues: list[str] = []
    previous_time: int | None = None
    seen: set[int] = set()
    for candle in items:
        result = validate_candle(candle)
        issues.extend(result.issues)
        open_time = _number(candle.get("open_time"))
        if open_time is None:
            continue
        timestamp = int(open_time)
        if timestamp in seen:
            issues.append("duplicate_timestamp")
        seen.add(timestamp)
        if previous_time is not None:
            if timestamp < previous_time:
                issues.append("out_of_order")
            elif timeframe_ms and timestamp - previous_time > timeframe_ms:
                issues.append("timestamp_gap")
        previous_time = timestamp

    if any(issue.startswith(("missing:", "non_finite:")) or issue in {"invalid_timestamp_order", "non_positive_price", "high_below_ohlc", "low_above_ohlc", "negative_volume"} for issue in issues):
        return QualityResult(QualityStatus.INVALID, tuple(issues))
    return QualityResult(QualityStatus.WARNING if issues else QualityStatus.VALID, tuple(issues))


def candle_to_dict(candle: Any) -> dict[str, Any]:
    return {field_name: getattr(candle, field_name) for field_name in ("open_time", "close_time", "open", "high", "low", "close", "volume")}


def valid_candles(candles: Iterable[Any]) -> list[Any]:
    return [candle for candle in candles if validate_candle(candle_to_dict(candle)).status is not QualityStatus.INVALID]