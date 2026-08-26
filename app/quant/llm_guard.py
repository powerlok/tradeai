"""Structured, non-authoritative LLM validation contract."""
from __future__ import annotations

from enum import StrEnum
from pydantic import BaseModel, Field


class ValidationDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FLAG_CONFLICT = "FLAG_CONFLICT"
    UNAVAILABLE = "UNAVAILABLE"


class SignalValidation(BaseModel):
    decision: ValidationDecision
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: str
    reason_codes: list[str]


def parse_validation(payload: object) -> SignalValidation:
    if not isinstance(payload, dict):
        raise ValueError("LLM validation must be a JSON object")
    return SignalValidation.model_validate(payload)
