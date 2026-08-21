from fastapi import APIRouter

from app.core.config import settings
from app.services.ai_provider import create_ai_provider

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
        "ai_provider": settings.ai_provider,
        "ai_model": service.model,
        "ai_connected": ollama_ok,
        "ollama_model": settings.ollama_model,
        "ollama_connected": ollama_ok if settings.ai_provider.lower() == "ollama" else False,
    }
