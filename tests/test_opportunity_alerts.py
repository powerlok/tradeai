from app.services.opportunity_alerts import _near_level


def test_alert_near_level_uses_risk_based_tolerance():
    assert _near_level(99.85, 100, 110, 1) is True
    assert _near_level(98, 100, 110, 1) is False
