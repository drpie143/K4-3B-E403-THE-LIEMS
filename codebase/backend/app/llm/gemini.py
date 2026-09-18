"""Adapter Gemini (google-genai, response_schema = Pydantic).

Lưu ý: free tier có thể dùng dữ liệu để huấn luyện → chỉ gửi phần tối thiểu (đã giới hạn ở retrieval).
"""
from __future__ import annotations

import time

from .base import LLMError, Timer, Usage


class GeminiClient:
    provider = "gemini"

    def __init__(self, timeout: float = 20.0, max_retries: int = 2):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover
            raise LLMError("Chưa cài gói google-genai (pip install google-genai)") from exc
        self.types = types
        self.client = genai.Client(http_options=types.HttpOptions(timeout=int(timeout * 1000)))  # key từ GEMINI_API_KEY
        self.max_retries = max_retries

    def complete_json(self, task, system, user, schema, model, fallback=None):
        usage = Usage(task=task, model=model)
        config = self.types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.2,
            automatic_function_calling=self.types.AutomaticFunctionCallingConfig(disable=True),
        )
        last_exc: Exception | None = None
        resp = None
        with Timer() as t:
            for attempt in range(self.max_retries + 1):
                try:
                    resp = self.client.models.generate_content(model=model, contents=user, config=config)
                    break
                except Exception as exc:  # SDK không tự thử lại
                    last_exc = exc
                    msg = str(exc)
                    retryable = any(k in msg for k in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE", "timeout", "Timeout"))
                    if not retryable or attempt >= self.max_retries:
                        break  # lỗi key/model sai thì báo ngay, không chờ vô ích
                    # Free tier hay dính 429 (hết hạn mức phút) → chờ rồi thử lại.
                    time.sleep(5.0 * (attempt + 1) if "429" in msg or "RESOURCE_EXHAUSTED" in msg else 1.0)
        if resp is None:
            raise LLMError(f"gemini: {type(last_exc).__name__}: {last_exc}")
        usage.latency_ms = t.ms
        meta = getattr(resp, "usage_metadata", None)
        if meta:
            usage.input_tokens = meta.prompt_token_count or 0
            usage.output_tokens = meta.candidates_token_count or 0
            usage.cached_tokens = getattr(meta, "cached_content_token_count", 0) or 0
        parsed = resp.parsed
        if parsed is None:
            try:
                parsed = schema.model_validate_json(resp.text or "")
            except Exception as exc:
                raise LLMError(f"gemini: không có JSON hợp lệ: {exc}") from exc
        if isinstance(parsed, dict):
            parsed = schema.model_validate(parsed)
        return parsed, usage
