import pytest

from app.quant.llm_guard import ValidationDecision, parse_validation
from app.quant.news import enrich_news


def test_news_enrichment_is_structured_and_deterministic():
    result = enrich_news("Bitcoin ETF approval brings rally", "BTC gains after approval")
    assert result.assets == ("BTC",)
    assert result.event_type == "ETF"
    assert result.sentiment == "POSITIVE"
    assert result.impact == "HIGH"


def test_llm_validation_rejects_unstructured_or_invalid_output():
    result = parse_validation({"decision": "APPROVE", "confidence": 0.8, "risk_level": "medium", "reason_codes": ["aligned"]})
    assert result.decision is ValidationDecision.APPROVE
    with pytest.raises((ValueError, TypeError)):
        parse_validation({"decision": "BUY"})
