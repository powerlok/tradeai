from fastapi import APIRouter

from app.core.config import settings
from app.services.ai_provider import create_ai_provider
from app.services.operational_state import get_operational_state

router = APIRouter()

@router.get("/health")
async def health():
    service = create_ai_provider(timeout_seconds=settings.ollama_timeout_seconds)

    try:
        ollama_ok = service.ping()
    except Exception:
        ollama_ok = False

    return {
        "status": "ok",
        "operational_state": await get_operational_state(),
        "ai_provider": settings.ai_provider,
        "ai_model": service.model,
        "ai_connected": ollama_ok,
        "ai_error": getattr(service, "last_error", None),
        "ollama_model": settings.ollama_model,
        "ollama_connected": ollama_ok if settings.ai_provider.lower() == "ollama" else False,
    }
