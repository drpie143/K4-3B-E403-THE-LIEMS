"""Giao diện chung cho mọi provider: complete_json(task, system, user, schema) → (obj, Usage)."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Lỗi gọi LLM (mạng, hạn mức, từ chối, JSON sai). Orchestrator bắt lỗi này để dùng dự phòng."""


@dataclass
class Usage:
    task: str
    model: str
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class LLMClient(Protocol):
    provider: str

    def complete_json(self, task: str, system: str, user: str, schema: type[T], model: str,
                      fallback: T | None = None) -> tuple[T, Usage]:
        ...


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = int((time.perf_counter() - self.start) * 1000)
