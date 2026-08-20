from __future__ import annotations

import json
from urllib import request, error


class OllamaService:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def ping(self) -> bool:
        try:
            req = request.Request(
                self._url("tags"),
                headers={"Content-Type": "application/json"},
                method="GET",
            )
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = resp.read()
                if not payload:
                    return False
                data = json.loads(payload.decode("utf-8"))
                if isinstance(data, dict) and "models" in data:
                    models = data.get("models", [])
                    return any(item.get("name") == self.model for item in models if isinstance(item, dict))
                return True
        except (error.URLError, error.HTTPError, ValueError, json.JSONDecodeError):
            return False

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._url("generate"),
            headers={"Content-Type": "application/json"},
            method="POST",
            data=body,
        )

        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "")
