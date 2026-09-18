"""Nạp prompt từ file .md và điền biến {{ten_bien}}."""
from __future__ import annotations

import json
from pathlib import Path


class Prompts:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.version = (self.dir / "VERSION").read_text(encoding="utf-8").strip()
        self._cache: dict[str, str] = {}

    def raw(self, name: str) -> str:
        if name not in self._cache:
            self._cache[name] = (self.dir / f"{name}.md").read_text(encoding="utf-8")
        return self._cache[name]

    def render(self, name: str, **values) -> str:
        text = self.raw(name)
        for key, val in values.items():
            if not isinstance(val, str):
                val = json.dumps(val, ensure_ascii=False, indent=1)
            text = text.replace("{{" + key + "}}", val)
        return text

    @property
    def system(self) -> str:
        return self.raw("system")
