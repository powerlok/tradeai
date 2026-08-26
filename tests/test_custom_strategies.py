from types import SimpleNamespace

from app.ml.backtester import run_strategy_backtest, run_strategy_walk_forward
from app.quant.opportunities import rank_opportunities
from app.quant.strategies import generate_signal
from app.services.groq_service import GroqService
from app.services.opportunity_alerts import build_viability_summary


def candle(index: int, close: float, high: float | None = None, low: float | None = None):
    return SimpleNamespace(open_time=index * 3600000, close_time=index * 3600000 + 3599000, open=close, high=high or close, low=low or close, close=close)


def test_moving_average_signal_uses_only_past_data():
    closes = list(range(1, 61))
    assert generate_signal("moving_average", closes, 10, {"fast_period": 3, "slow_period": 5}) == 1
    assert generate_signal("moving_average", closes, 2, {"fast_period": 3, "slow_period": 5}) == 0


def test_custom_strategy_backtest_returns_costs_and_exits():
    candles = [candle(index, 100 + index * 0.2) for index in range(80)]
    result = run_strategy_backtest(candles, "moving_average", {"fast_period": 3, "slow_period": 5}, max_holding_bars=3)
    assert result["mode"] == "deterministic_causal"
    assert result["strategy_type"] == "moving_average"
    assert set(result["exit_reasons"]) == {"stop_loss", "take_profit", "time_exit"}


def test_walk_forward_keeps_test_windows_temporally_separate():
    candles = [candle(index, 100 + index * 0.2) for index in range(500)]
    result = run_strategy_walk_forward(
        candles,
        "moving_average",
        {"fast_period": 3, "slow_period": 5},
        train_bars=100,
        validation_bars=50,
        test_bars=80,
        max_windows=3,
    )
    assert result["mode"] == "walk_forward_causal"
    assert result["window_count"] == 3
    assert all(window["test_start"] > window["validation_end"] for window in result["windows"])
    assert all(first["test_end"] < second["test_start"] for first, second in zip(result["windows"], result["windows"][1:]))
    assert "quality_gate" in result
    assert "passed" in result["quality_gate"]
    assert "checks" in result["quality_gate"]


def test_walk_forward_quality_gate_tracks_cost_regime_and_liquidity():
    candles = [candle(index, 100 + index * 0.2) for index in range(500)]
    result = run_strategy_walk_forward(
        candles,
        "moving_average",
        {"fast_period": 3, "slow_period": 5},
        train_bars=100,
        validation_bars=50,
        test_bars=80,
        max_windows=3,
    )
    required_checks = {"cost_efficiency", "regime_stability", "liquidity_filter"}
    assert required_checks.issubset(result["quality_gate"]["checks"].keys())


def test_rank_opportunities_rejects_weak_targets_after_costs_and_liquidity():
    decision = SimpleNamespace(
        state="BUY",
        direction="BUY",
        probability=0.72,
        score=0.8,
        risk=SimpleNamespace(
            entry=100.0,
            stop=99.0,
            target=100.6,
            reward_risk=2.0,
            risk_per_unit=1.0,
            valid=True,
        ),
    )
    opportunities = rank_opportunities([('BTCUSDT', '1h', decision)], fee_bps=10, slippage_bps=5, minimum_net_target_pct=0.0)
    assert opportunities == []


def test_groq_payload_uses_chat_compatible_fields():
    service = GroqService("https://api.groq.com", "test-key", "openai/gpt-oss-20b")
    payload = service._chat_payload([{"role": "user", "content": "Oi"}], False)
    assert "max_tokens" in payload
    assert "max_completion_tokens" not in payload
    assert "reasoning_effort" not in payload
    assert "include_reasoning" not in payload


def test_viability_summary_shows_net_target_and_required_move():
    summary = build_viability_summary(
        entry=100.0,
        stop=99.0,
        target=101.2,
        direction="BUY",
        fee_bps=10,
        slippage_bps=5,
    )
    assert "alvo líquido" in summary.lower()
    assert "mínimo exigido" in summary.lower()
    assert "margem" in summary.lower()
