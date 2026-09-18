"""Bộ nhớ đệm câu trả lời đã qua kiểm tra (cũng dùng cho chế độ phát lại REPLAY=1)."""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from .schemas import Answer, FidelityReport


class AnswerCache:
    def __init__(self, directory: Path):
        self.path = Path(directory) / "answers.json"
        self.lock = threading.Lock()
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = {}

    @staticmethod
    def key(**parts) -> str:
        raw = json.dumps(parts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, key: str) -> tuple[Answer, FidelityReport] | None:
        hit = self.data.get(key)
        if not hit:
            return None
        return Answer(**hit["answer"]), FidelityReport(**hit["fidelity"])

    def put(self, key: str, answer: Answer, fidelity: FidelityReport) -> None:
        with self.lock:
            self.data[key] = {"answer": answer.model_dump(), "fidelity": fidelity.model_dump()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")
