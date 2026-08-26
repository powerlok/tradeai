import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import require_user
from app.core.config import settings
from app.services.ai_provider import create_ai_provider
from app.services.context_validator import validate_quantitative_signal

router = APIRouter()


class ContextValidationRequest(BaseModel):
    symbol: str
    timeframe: str
    direction: str
    probability: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=100.0)
    risk: dict[str, object]
    evidence: list[str] = []


@router.post("/signals/validate-context")
async def validate_context(payload: ContextValidationRequest, user: dict = Depends(require_user)):
    provider = create_ai_provider(timeout_seconds=settings.ollama_timeout_seconds)
    result = await asyncio.to_thread(validate_quantitative_signal, provider, payload.model_dump())
    return {
        "provider": settings.ai_provider,
        "validation": result.model_dump(),
        "quantitative_decision_unchanged": True,
    }