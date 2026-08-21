from __future__ import annotations

import json
from collections.abc import Iterator
from urllib import error, request


class GroqService:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: int = 120, temperature: float = 1.0, max_completion_tokens: int = 2048, top_p: float = 1.0, reasoning_effort: str = "medium"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.top_p = top_p
        self.reasoning_effort = reasoning_effort

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _request(self, endpoint: str, payload: dict | None = None, method: str = "GET"):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(
            self._url(endpoint),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method=method,
            data=body,
        )
        return request.urlopen(req, timeout=self.timeout_seconds)

    def ping(self) -> bool:
        if not self.api_key:
            return False
        try:
            with self._request("models") as response:
                payload = json.loads(response.read().decode("utf-8"))
                return any(item.get("id") == self.model for item in payload.get("data", []))
        except (error.URLError, error.HTTPError, ValueError, json.JSONDecodeError):
            return False

    def chat_once(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        payload = self._chat_payload(messages, False)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        with self._request("chat/completions", payload, "POST") as response:
            result = json.loads(response.read().decode("utf-8"))
            choice = result.get("choices", [{}])[0]
            message = choice.get("message", {})
            return {"message": message, "provider": "groq", "raw": result}

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        payload = self._chat_payload(messages, True)
        with self._request("chat/completions", payload, "POST") as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                result = json.loads(data)
                content = result.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content

    def _chat_payload(self, messages: list[dict], stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens,
            "top_p": self.top_p,
            "reasoning_effort": self.reasoning_effort,
            "stream": stream,
        }
