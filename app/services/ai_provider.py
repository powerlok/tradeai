from __future__ import annotations

from typing import Protocol

from app.core.config import settings
from app.services.groq_service import GroqService
from app.services.ollama_service import OllamaService


class AIProvider(Protocol):
    model: str

    def ping(self) -> bool: ...
    def chat_once(self, messages: list[dict], tools: list[dict] | None = None) -> dict: ...
    def chat_stream(self, messages: list[dict]): ...


def create_ai_provider(timeout_seconds: int = 120) -> AIProvider:
    provider = settings.ai_provider.strip().lower()
    if provider == "groq":
        return GroqService(
            base_url=settings.groq_url,
            api_key=settings.groq_api_key or "",
            model=settings.groq_model,
            timeout_seconds=timeout_seconds,
        )
    return OllamaService(
        base_url=settings.ollama_url,
        model=settings.ollama_model,
        timeout_seconds=timeout_seconds,
    )
