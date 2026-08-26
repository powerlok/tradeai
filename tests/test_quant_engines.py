from types import SimpleNamespace

from app.quant.engines import (
    build_multi_timeframe_view,
    build_risk_plan,
    calculate_microstructure,
    classify_regime,
    decide_signal,
)


def candle(close, timestamp):
    return SimpleNamespace(close=close, close_time=timestamp)


def test_multi_timeframe_view_is_ordered_and_causal():
    result = build_multi_timeframe_view({
        "5m": [candle(100, 1), candle(101, 2)],
        "1h": [candle(100, 1), candle(99, 2)],
    })
    assert [item.timeframe for item in result] == ["1h", "5m"]
    assert result[0].trend == "DOWN"
    assert result[1].trend == "UP"


def test_microstructure_calculates_spread_and_imbalance():
    result = calculate_microstructure([[100, 3], [99, 2]], [[101, 1], [102, 1]])
    assert result.spread == 1.0
    assert result.imbalance > 0
    assert result.spread_bps > 0


def test_regime_and_risk_are_deterministic():
    regime = classify_regime([100 + index for index in range(25)])
    risk = build_risk_plan("BUY", 120, 4)
    assert regime.regime == "TREND_UP"
    assert risk.stop == 116
    assert risk.target == 128
    assert risk.valid is True


def test_signal_blocks_conflicting_regime():
    risk = build_risk_plan("BUY", 100, 2)
    decision = decide_signal(0.8, risk, classify_regime([100 - index for index in range(25)]))
    assert decision.direction == "WATCH"
    assert decision.state == "NO_TRADE"
    assert "regime_conflict" in decision.evidence
