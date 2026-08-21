from __future__ import annotations

from collections.abc import Iterator

from groq import Groq


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
        self.client = Groq(api_key=api_key, base_url=self.base_url)

    def ping(self) -> bool:
        if not self.api_key:
            return False
        try:
            return any(model.id == self.model for model in self.client.models.list().data)
        except Exception:
            return False

    def chat_once(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        request = self._chat_payload(messages, False)
        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        response = self.client.chat.completions.create(**request)
        message = response.choices[0].message.model_dump(exclude_none=True)
        if "tool_calls" in message:
            message["tool_calls"] = [call.model_dump(exclude_none=True) for call in response.choices[0].message.tool_calls]
        return {"message": message, "provider": "groq", "raw": response.model_dump(exclude_none=True)}

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        for chunk in self.client.chat.completions.create(**self._chat_payload(messages, True)):
            content = chunk.choices[0].delta.content if chunk.choices else None
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
