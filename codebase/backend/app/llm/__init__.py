"""Chọn adapter theo LLM_PROVIDER."""
from __future__ import annotations

from ..config import Settings
from .base import LLMClient, LLMError, Usage
from .fake import FakeLLM


def make_client(settings: Settings) -> LLMClient:
    p = settings.llm_provider
    if p == "fake":
        return FakeLLM()
    if p == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient(settings.llm_timeout, settings.llm_max_retries)
    if p == "claude":
        from .claude import ClaudeClient
        return ClaudeClient(settings.llm_timeout, settings.llm_max_retries)
    if p == "gemini":
        from .gemini import GeminiClient
        return GeminiClient(settings.llm_timeout, settings.llm_max_retries)
    raise LLMError(f"LLM_PROVIDER không hợp lệ: {p}")


__all__ = ["make_client", "LLMClient", "LLMError", "Usage", "FakeLLM"]
