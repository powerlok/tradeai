import os

from app.core.config import Settings


def test_settings_exposes_default_ollama_model(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434/api")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:latest")

    settings = Settings()

    assert settings.ollama_url == "http://localhost:11434/api"
    assert settings.ollama_model == "llama3.2:latest"
