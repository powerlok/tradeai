"""Deterministic quantitative engines used by analysis and paper workflows."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log, sqrt
from statistics import mean, pstdev
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True)
class TimeframeView:
    timeframe: str
    close: float
    timestamp: int
    return_pct: float
    trend: str


@dataclass(frozen=True)
class MicrostructureView:
    spread: float
    spread_bps: float
    imbalance: float
    bid_pressure: float
    ask_pressure: float


@dataclass(frozen=True)
class RegimeView:
    regime: str
    volatility: float
    trend_strength: float
    confidence: float


@dataclass(frozen=True)
class RiskPlan:
    direction: str
    entry: float
    stop: float
    target: float
    risk_per_unit: float
    reward_risk: float
    valid: bool
    reason: str


@dataclass(frozen=True)
class SignalDecision:
    direction: str
    state: str
    score: float
    probability: float
    confidence: float
    evidence: tuple[str, ...]
    risk: RiskPlan


def _finite(value: float, fallback: float = 0.0) -> float:
    return float(value) if isfinite(float(value)) else fallback


def build_multi_timeframe_view(candles_by_timeframe: Mapping[str, Sequence[object]]) -> list[TimeframeView]:
    """Summarize aligned candle series without looking beyond each series end."""
    result: list[TimeframeView] = []
    for timeframe in ("1d", "4h", "1h", "15m", "5m"):
        candles = candles_by_timeframe.get(timeframe, ())
        if not candles:
            continue
        latest = candles[-1]
        previous = candles[-2] if len(candles) > 1 else latest
        close = float(latest.close)
        previous_close = float(previous.close)
        return_pct = close / previous_close - 1.0 if previous_close else 0.0
        result.append(TimeframeView(
            timeframe=timeframe,
            close=close,
            timestamp=int(latest.close_time),
            return_pct=return_pct,
            trend="UP" if return_pct > 0 else "DOWN" if return_pct < 0 else "FLAT",
        ))
    return result


def calculate_microstructure(
    bids: Iterable[Sequence[float | str]], asks: Iterable[Sequence[float | str]]
) -> MicrostructureView:
    bids_list = [(float(price), float(quantity)) for price, quantity in bids]
    asks_list = [(float(price), float(quantity)) for price, quantity in asks]
    if not bids_list or not asks_list:
        return MicrostructureView(0.0, 0.0, 0.0, 0.0, 0.0)
    best_bid = max(price for price, _ in bids_list)
    best_ask = min(price for price, _ in asks_list)
    mid = (best_bid + best_ask) / 2.0
    bid_volume = sum(quantity for _, quantity in bids_list)
    ask_volume = sum(quantity for _, quantity in asks_list)
    total = bid_volume + ask_volume
    imbalance = (bid_volume - ask_volume) / total if total else 0.0
    return MicrostructureView(
        spread=max(best_ask - best_bid, 0.0),
        spread_bps=(max(best_ask - best_bid, 0.0) / mid * 10000.0) if mid else 0.0,
        imbalance=imbalance,
        bid_pressure=bid_volume,
        ask_pressure=ask_volume,
    )


def classify_regime(closes: Sequence[float], lookback: int = 20) -> RegimeView:
    if len(closes) < 3:
        return RegimeView("UNKNOWN", 0.0, 0.0, 0.0)
    window = [float(value) for value in closes[-lookback:]]
    returns = [window[index] / window[index - 1] - 1.0 for index in range(1, len(window)) if window[index - 1]]
    volatility = pstdev(returns) if len(returns) > 1 else 0.0
    trend_strength = abs(window[-1] / window[0] - 1.0) if window[0] else 0.0
    direction = window[-1] / window[0] - 1.0 if window[0] else 0.0
    if volatility > 0.03:
        regime = "VOLATILE"
    elif trend_strength < 0.01:
        regime = "SIDEWAYS"
    elif direction > 0:
        regime = "TREND_UP"
    else:
        regime = "TREND_DOWN"
    confidence = min(1.0, trend_strength / max(volatility, 0.001))
    return RegimeView(regime, volatility, trend_strength, confidence)


def build_risk_plan(direction: str, entry: float, atr: float, risk_reward: float = 2.0) -> RiskPlan:
    direction = direction.upper()
    entry = float(entry)
    atr = float(atr)
    if direction not in {"BUY", "SELL"} or entry <= 0 or atr <= 0 or risk_reward <= 0:
        return RiskPlan(direction, entry, 0.0, 0.0, 0.0, 0.0, False, "invalid risk inputs")
    risk = atr
    if direction == "BUY":
        stop, target = entry - risk, entry + risk * risk_reward
    else:
        stop, target = entry + risk, entry - risk * risk_reward
    if stop <= 0 or target <= 0:
        return RiskPlan(direction, entry, stop, target, risk, risk_reward, False, "stop or target is non-positive")
    return RiskPlan(direction, entry, stop, target, risk, risk_reward, True, "ok")


def decide_signal(
    probability: float,
    risk: RiskPlan,
    regime: RegimeView | None = None,
    microstructure: MicrostructureView | None = None,
) -> SignalDecision:
    probability = min(1.0, max(0.0, float(probability)))
    direction = "BUY" if probability >= 0.60 else "SELL" if probability <= 0.40 else "WATCH"
    evidence: list[str] = []
    if probability >= 0.60 or probability <= 0.40:
        evidence.append("model_confidence")
    if regime and regime.regime in {"TREND_UP", "TREND_DOWN"}:
        evidence.append(regime.regime.lower())
        if (direction == "BUY" and regime.regime == "TREND_DOWN") or (direction == "SELL" and regime.regime == "TREND_UP"):
            direction = "WATCH"
            evidence.append("regime_conflict")
    if microstructure and direction in {"BUY", "SELL"}:
        aligned = microstructure.imbalance > 0.10 if direction == "BUY" else microstructure.imbalance < -0.10
        evidence.append("orderbook_aligned" if aligned else "orderbook_neutral")
        if not aligned:
            direction = "WATCH"
            evidence.append("microstructure_conflict")
    confidence = abs(probability - 0.5) * 2.0
    score = min(100.0, max(0.0, confidence * 70.0 + (20.0 if risk.valid else 0.0) + (10.0 if evidence else 0.0)))
    state = "NO_TRADE" if direction == "WATCH" or not risk.valid else "HIGH_CONVICTION" if score >= 75 else "SETUP"
    return SignalDecision(direction, state, score, probability, confidence, tuple(evidence), risk)


def calculate_returns(closes: Sequence[float]) -> list[float]:
    return [float(closes[index] / closes[index - 1] - 1.0) for index in range(1, len(closes)) if closes[index - 1]]


def performance_summary(returns: Sequence[float]) -> dict[str, float]:
    values = [_finite(value) for value in returns]
    if not values:
        return {"return": 0.0, "volatility": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    equity = 1.0
    peak = equity
    drawdown = 0.0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity / peak - 1.0)
    volatility = pstdev(values) if len(values) > 1 else 0.0
    return {"return": equity - 1.0, "volatility": volatility, "sharpe": mean(values) / volatility * sqrt(252) if volatility else 0.0, "max_drawdown": drawdown}
