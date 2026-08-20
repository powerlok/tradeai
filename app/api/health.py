from fastapi import APIRouter

from app.core.config import settings
from app.services.ollama_service import OllamaService

router = APIRouter()

@router.get("/health")
async def health():
    service = OllamaService(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )

    try:
        ollama_ok = service.ping()
    except Exception:
        ollama_ok = False

    return {
        "status": "ok",
        "ollama_model": settings.ollama_model,
        "ollama_connected": ollama_ok,
    }
