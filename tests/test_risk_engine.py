from types import SimpleNamespace

from app.quant.risk import RiskLimits, assess_portfolio_risk


def test_risk_engine_approves_position_inside_limits():
    assessment = assess_portfolio_risk([], 0, 1, 100, 99, RiskLimits())
    assert assessment.approved is True
    assert assessment.proposed_risk == 1


def test_risk_engine_blocks_trade_risk_limit():
    assessment = assess_portfolio_risk([], 0, 250, 100, 99, RiskLimits())
    assert assessment.approved is False
    assert "TRADE_RISK_LIMIT" in assessment.reason_codes


def test_risk_engine_blocks_aggregate_risk_and_daily_loss():
    current = SimpleNamespace(quantity=245, entry_price=100, stop=98)
    assessment = assess_portfolio_risk([current], -300, 11, 100, 99, RiskLimits(max_exposure_pct=2.0))
    assert assessment.approved is False
    assert "PORTFOLIO_RISK_LIMIT" in assessment.reason_codes
    assert "DAILY_LOSS_LIMIT" in assessment.reason_codes