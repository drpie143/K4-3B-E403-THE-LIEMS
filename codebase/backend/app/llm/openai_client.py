"""Adapter OpenAI (Chat Completions + structured output qua Pydantic)."""
from __future__ import annotations

from .base import LLMError, Timer, Usage


class OpenAIClient:
    provider = "openai"

    def __init__(self, timeout: float = 20.0, max_retries: int = 2):
        try:
            import openai  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise LLMError("Chưa cài gói openai (pip install openai)") from exc
        from openai import OpenAI

        self._openai = __import__("openai")
        self.client = OpenAI(timeout=timeout, max_retries=max_retries)  # key đọc từ OPENAI_API_KEY

    def complete_json(self, task, system, user, schema, model, fallback=None):
        kwargs = {}
        # Model suy luận (gpt-5*, o*) không nhận temperature tuỳ ý; dùng mức suy luận thấp.
        if model.startswith(("gpt-5", "o1", "o3", "o4")):
            kwargs["reasoning_effort"] = "low"
        else:
            kwargs["temperature"] = 0.2
        usage = Usage(task=task, model=model)
        with Timer() as t:
            try:
                resp = self.client.chat.completions.parse(
                    model=model,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format=schema,
                    **kwargs,
                )
            except self._openai.APIError as exc:
                raise LLMError(f"openai: {type(exc).__name__}: {exc}") from exc
            except Exception as exc:  # lỗi kiểm tra schema phía SDK
                raise LLMError(f"openai: {type(exc).__name__}: {exc}") from exc
        usage.latency_ms = t.ms
        if resp.usage:
            usage.input_tokens = resp.usage.prompt_tokens
            usage.output_tokens = resp.usage.completion_tokens
            details = getattr(resp.usage, "prompt_tokens_details", None)
            usage.cached_tokens = getattr(details, "cached_tokens", 0) or 0
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise LLMError(f"openai: từ chối — {msg.refusal}")
        if msg.parsed is None:
            raise LLMError("openai: không có JSON hợp lệ")
        return msg.parsed, usage
