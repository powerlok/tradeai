from app.services.context_validator import validate_quantitative_signal
from app.quant.llm_guard import ValidationDecision


class Provider:
    def validate_signal(self, context):
        assert context["probability"] == 0.8
        return {"decision": "APPROVE", "confidence": 0.9, "risk_level": "medium", "reason_codes": ["aligned"]}


class BrokenProvider:
    def validate_signal(self, context):
        raise RuntimeError("unavailable")


def test_validation_is_provider_agnostic():
    result = validate_quantitative_signal(Provider(), {"probability": 0.8, "score": 80})
    assert result.decision is ValidationDecision.APPROVE


def test_provider_failure_is_safe_and_non_authoritative():
    result = validate_quantitative_signal(BrokenProvider(), {"probability": 0.8})
    assert result.decision is ValidationDecision.UNAVAILABLE