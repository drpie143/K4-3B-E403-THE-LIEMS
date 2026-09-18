"""Adapter Claude (Anthropic SDK, messages.parse với Pydantic)."""
from __future__ import annotations

from .base import LLMError, Timer, Usage


class ClaudeClient:
    provider = "claude"

    def __init__(self, timeout: float = 20.0, max_retries: int = 2):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError("Chưa cài gói anthropic (pip install anthropic)") from exc
        self._anthropic = anthropic
        self.client = anthropic.Anthropic(timeout=timeout, max_retries=max_retries)  # key từ ANTHROPIC_API_KEY

    def complete_json(self, task, system, user, schema, model, fallback=None):
        usage = Usage(task=task, model=model)
        with Timer() as t:
            try:
                resp = self.client.messages.parse(
                    model=model,
                    max_tokens=4000,
                    # Phần cố định để trước, đánh dấu cache.
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user}],
                    output_format=schema,
                )
            except self._anthropic.APIError as exc:
                raise LLMError(f"claude: {type(exc).__name__}: {exc}") from exc
            except Exception as exc:
                raise LLMError(f"claude: {type(exc).__name__}: {exc}") from exc
        usage.latency_ms = t.ms
        if resp.usage:
            usage.input_tokens = resp.usage.input_tokens
            usage.output_tokens = resp.usage.output_tokens
            usage.cached_tokens = getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        if resp.stop_reason == "refusal":
            raise LLMError("claude: refusal")
        if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
            raise LLMError(f"claude: không có JSON hợp lệ (stop_reason={resp.stop_reason})")
        return resp.parsed_output, usage
