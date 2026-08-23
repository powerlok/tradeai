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
        self.last_error: str | None = None

    def ping(self) -> bool:
        if not self.api_key:
            self.last_error = "missing_api_key"
            return False
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Respond only with OK."}],
                max_completion_tokens=10,
                temperature=0,
                stream=False,
            )
            available = bool(response.choices)
            self.last_error = None if available else "empty_response"
            return available
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            self.last_error = f"http_{status_code}" if status_code else type(exc).__name__
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
        payload = self._chat_payload(messages, True)
        payload["tool_choice"] = "none"
        for chunk in self.client.chat.completions.create(**payload):
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
            "include_reasoning": False,
            "stream": stream,
        }
