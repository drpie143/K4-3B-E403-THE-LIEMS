"""Ghi vết mỗi lượt ra JSONL (thư mục traces/, không commit). Không bao giờ ghi key."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class Tracer:
    def __init__(self, directory: Path, keep_text: bool = False, keep_prompts: bool = True):
        self.dir = Path(directory)
        self.keep_text = keep_text
        self.keep_prompts = keep_prompts
        self.lock = threading.Lock()

    def text_fields(self, text: str) -> dict:
        out = {"text_len": len(text), "text_hash": hashlib.sha256(text.encode()).hexdigest()[:12]}
        if self.keep_text:
            out["text"] = text
        return out

    def prompt(self, request_id: str, task: str, model: str, system: str, user: str,
               raw: dict | None, error: str | None) -> None:
        """Ghi prompt đầu vào + phản hồi thô của mô hình (xác minh kỹ thuật ở các mốc).

        Chỉ nằm trên máy: traces/prompts/ đã bị .gitignore chặn.
        """
        if not self.keep_prompts:
            return
        path = self.dir / "prompts" / f"{request_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "task": task, "model": model,
               "system": system, "user": user, "raw_response": raw, "error": error}
        with self.lock, path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    def write(self, record: dict) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
        with self.lock, path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
