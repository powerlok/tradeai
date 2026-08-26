"""Provider-agnostic contextual validation; never changes quantitative signals."""
from app.quant.llm_guard import SignalValidation, ValidationDecision, parse_validation
from app.core.config import settings
from app.observability.metrics import inc_llm_validation


def validate_quantitative_signal(provider, quantitative_context: dict[str, object]) -> SignalValidation:
    try:
        result = parse_validation(provider.validate_signal(quantitative_context))
        inc_llm_validation(settings.ai_provider, result.decision.value)
        return result
    except Exception as error:
        result = SignalValidation(
            decision=ValidationDecision.UNAVAILABLE,
            confidence=0.0,
            risk_level="unknown",
            reason_codes=[type(error).__name__],
        )
        inc_llm_validation(settings.ai_provider, result.decision.value)
        return result