"""Tìm đoạn nguồn bằng BM25 (tự cài, không phụ thuộc thư viện).

Nguồn ưu tiên: codebase/data/chunks.local.json (nguyên văn, chỉ trên máy).
Thiếu file → dùng tóm tắt trong cards/_sources.yaml ("summary mode") để hệ thống
vẫn chạy được khi test / CI, và /health báo rõ chế độ này.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .cards import CardStore
from .textutil import tokens

STOPWORDS = set("la gi cua va co cho cac nhung mot the nao nay do thi de duoc khong trong khi nhu ve voi tu den o ra vao minh ban toi em anh chi a nhe a oi sao".split())


@dataclass
class Passage:
    id: str
    section: str
    text: str
    file: str
    score: float = 0.0


class Retriever:
    k1 = 1.5
    b = 0.75

    def __init__(self, cards: CardStore, chunks_path: Path):
        self.cards = cards
        self.mode = "local"
        docs: list[Passage] = []
        if Path(chunks_path).exists():
            for c in json.loads(Path(chunks_path).read_text(encoding="utf-8")):
                docs.append(Passage(id=c["id"], section=c.get("section", ""), text=c["text"], file=c.get("file", "")))
        if not docs:
            self.mode = "summary"
            for sid, meta in cards.sources.items():
                file = "transcript-04-clean.md" if sid.startswith("T04") else "transcript-06-clean.md"
                docs.append(Passage(id=sid, section=meta.get("section", ""), text=meta.get("summary", ""), file=file))
        self.docs = docs
        self.by_id = {d.id: d for d in docs}
        self._index()

    def _index(self) -> None:
        self.doc_tokens = [self._toks(f"{d.section} {d.text}") for d in self.docs]
        self.tf = [Counter(t) for t in self.doc_tokens]
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))
        df: Counter = Counter()
        for t in self.doc_tokens:
            df.update(set(t))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    @staticmethod
    def _toks(text: str) -> list[str]:
        return [t for t in tokens(text) if t not in STOPWORDS]

    def search(self, query: str, lesson_id: str, k: int = 5, boost_ids: list[str] | None = None) -> list[Passage]:
        allowed = set(self.cards.lesson_files(lesson_id))
        q = self._toks(query)
        boost = set(boost_ids or [])
        scored = []
        for i, d in enumerate(self.docs):
            if allowed and d.file not in allowed:
                continue
            tf, dl = self.tf[i], len(self.doc_tokens[i])
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf.get(w, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0 and d.id in boost:
                s = s * 1.5 + 0.5
            if s > 0:
                scored.append(Passage(d.id, d.section, d.text, d.file, round(s, 3)))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:k]

    def get(self, source_id: str) -> Passage | None:
        return self.by_id.get(source_id)

    def text_for(self, source_id: str, max_chars: int) -> str:
        p = self.by_id.get(source_id)
        if not p:
            return self.cards.summary(source_id)
        return p.text if len(p.text) <= max_chars else p.text[:max_chars].rsplit(" ", 1)[0] + " …"
