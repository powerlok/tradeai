from __future__ import annotations

import json
from collections.abc import Iterator
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

    def generate_stream(self, prompt: str, system_prompt: str | None = None) -> Iterator[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
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
            for line in resp:
                if not line.strip():
                    continue
                result = json.loads(line.decode("utf-8"))
                content = result.get("response", "")
                if content:
                    yield content

    def chat_once(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._url("chat"),
            headers={"Content-Type": "application/json"},
            method="POST",
            data=body,
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._url("chat"),
            headers={"Content-Type": "application/json"},
            method="POST",
            data=body,
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as resp:
            for line in resp:
                if not line.strip():
                    continue
                result = json.loads(line.decode("utf-8"))
                content = result.get("message", {}).get("content", "")
                if content:
                    yield content

    def validate_signal(self, context: dict[str, object]) -> dict[str, object]:
        response = self.chat_once([{
            "role": "system",
            "content": "Retorne somente JSON válido com decision APPROVE, REJECT ou FLAG_CONFLICT; confidence entre 0 e 1; risk_level; reason_codes como lista. Não altere nenhum valor quantitativo.",
        }, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}])
        return _message_json(response)


def _message_json(response: dict) -> dict[str, object]:
    content = response.get("message", {}).get("content", "")
    if isinstance(content, dict):
        return content
    parsed = json.loads(str(content))
    if not isinstance(parsed, dict):
        raise ValueError("provider returned a non-object validation")
    return parsed
