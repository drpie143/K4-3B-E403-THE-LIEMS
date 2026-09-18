"""LLM giả để test và chạy không tốn tiền.

- Mặc định trả về `fallback` (quyết định/mẫu trả lời bằng luật) → kết quả xác định.
- `script` cho phép kịch bản hoá: {task: [obj | Exception, ...]} để giả lập LLM trả sai / lỗi.
"""
from __future__ import annotations

from collections import defaultdict

from .base import LLMError, Timer, Usage


class FakeLLM:
    provider = "fake"

    def __init__(self, script: dict | None = None):
        self.script = defaultdict(list, {k: list(v) for k, v in (script or {}).items()})
        self.calls: list[dict] = []

    def complete_json(self, task, system, user, schema, model, fallback=None):
        with Timer() as t:
            self.calls.append({"task": task, "system": system, "user": user, "model": model})
            if self.script.get(task):
                item = self.script[task].pop(0)
                if isinstance(item, Exception):
                    raise item
                obj = item if isinstance(item, schema) else schema.model_validate(item)
            elif fallback is not None:
                obj = fallback
            else:
                raise LLMError(f"FakeLLM: không có phản hồi cho {task}")
        return obj, Usage(task=task, model=model, latency_ms=t.ms, input_tokens=len(system + user) // 4, output_tokens=len(obj.model_dump_json()) // 4)
