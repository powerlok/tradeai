from app.quant.engines import build_risk_plan, decide_signal
from app.quant.feature_v2 import build_feature_v2
from app.quant.opportunities import rank_opportunities


def test_feature_v2_is_causal_and_price_relative():
    values = [100, 101, 102, 103, 104]
    result = build_feature_v2(values, [value + 1 for value in values], [value - 1 for value in values], values, [10, 10, 12, 10, 20])
    assert result["return_1"] > 0
    assert result["range_pct"] > 0
    assert result["volume_relative"] > 1


def test_opportunities_are_ranked_and_exclude_no_trade():
    risk = build_risk_plan("BUY", 100, 2)
    high = decide_signal(0.85, risk)
    low = decide_signal(0.52, risk)
    result = rank_opportunities([("btc", "1h", high), ("eth", "1h", low)])
    assert [item.symbol for item in result] == ["BTC"]
    assert result[0].status == "APPROVED"
    assert result[0].action == "PAPER_ENTRY"
    assert result[0].assessment_id
    assert "COST_VIABLE" in result[0].reason_codes


def test_opportunity_requires_positive_expected_value_after_costs():
    risk = build_risk_plan("BUY", 100, 2)
    strong = decide_signal(0.90, risk)
    result = rank_opportunities([("btc", "1h", strong)], fee_bps=10, slippage_bps=5)
    assert result[0].directional_probability == 0.90
    assert result[0].expected_value_pct > result[0].safety_buffer_pct
    assert result[0].required_move_pct > result[0].round_trip_cost_pct


def test_opportunity_rejects_levels_too_close_to_entry():
    risk = build_risk_plan("BUY", 100, 0.05)
    signal = decide_signal(0.90, risk)
    assert rank_opportunities([("trx", "1h", signal)]) == []


def test_opportunity_respects_minimum_net_target_percentage():
    risk = build_risk_plan("BUY", 100, 5, risk_reward=2)
    signal = decide_signal(0.90, risk)
    assert rank_opportunities([("btc", "1h", signal)], minimum_net_target_pct=0.10) == []
    assert rank_opportunities([("btc", "1h", signal)], minimum_net_target_pct=0.05)
