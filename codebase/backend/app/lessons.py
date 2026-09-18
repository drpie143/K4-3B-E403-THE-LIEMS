"""Danh mục 6 buổi học + phần thân bài đọc trên giao diện.

Nguồn nội dung, theo thứ tự ưu tiên:
  1. Đoạn nguyên văn đã nạp sẵn trong Retriever (codebase/data/chunks.local.json — KHÔNG commit)
  2. Bảng `lecture_chunks` trên Supabase (nếu đã cấu hình SUPABASE_URL/KEY)
  3. Tóm tắt do nhóm tự viết trong cards/_sources.yaml (chế độ "summary" — dùng khi máy chưa có data pack)

Repo công khai nên tuyệt đối không commit nguyên văn: file này chỉ *đọc* dữ liệu lúc chạy.
"""
from __future__ import annotations

import re
from typing import Any

from .cards import CardStore
from .config import Settings

PARA_RE = re.compile(r"\[(T\d{2}-\d{3}(?:-\d+)?)\]\s*")
# Đoạn mở đầu của chunk là phần chồng lấn với chunk trước ("... …"), bỏ khi hiển thị.
OVERLAP_RE = re.compile(r"^\s*\.\.\..*?\.\.\.\s*", re.S)


def _file_of(source_id: str) -> str:
    """T03-105 → transcript-03-clean.md."""
    return f"transcript-{source_id[1:3]}-clean.md"


class LessonStore:
    def __init__(self, cards: CardStore, settings: Settings, retriever: Any = None, supabase: Any = None):
        self.cards = cards
        self.s = settings
        self.retriever = retriever
        self.sb = supabase
        self._cache: dict[str, list[dict]] = {}

    # ------------------------------------------------------------ danh mục
    @property
    def lesson_ids(self) -> list[str]:
        rows = [(v.get("order", 99), k) for k, v in self.cards.lessons.items() if v.get("order")]
        return [k for _, k in sorted(rows)]

    def catalog(self) -> list[dict]:
        out = []
        for lid in self.lesson_ids:
            meta = self.cards.lessons[lid]
            sections = self.cards.sections.get(lid, [])
            concepts = [c for c in meta.get("concepts", []) if self.cards.get(c)]
            out.append({
                "id": lid,
                "order": meta.get("order"),
                "title": meta.get("title", lid),
                "day": meta.get("day", ""),
                "subtitle": meta.get("subtitle", ""),
                "tags": meta.get("tags", []),
                "sections": [{"id": s["id"], "title": s["title"]} for s in sections],
                "concepts": [{"id": c, "term": self.cards.get(c).term, "vi_name": self.cards.get(c).vi_name} for c in concepts],
                "source": self.source_mode(lid),
            })
        return out

    def source_mode(self, lesson_id: str) -> str:
        """local | supabase | summary — để giao diện nói rõ đang đọc dữ liệu nào."""
        if self._local_paragraphs(lesson_id):
            return "local"
        if self._supabase_paragraphs(lesson_id):
            return "supabase"
        return "summary"

    # ------------------------------------------------------------- thân bài
    def lesson(self, lesson_id: str, section_id: str | None = None) -> dict:
        meta = self.cards.lessons.get(lesson_id)
        if not meta or not meta.get("order"):
            raise KeyError(lesson_id)
        paragraphs = self.paragraphs(lesson_id)
        sections = self._group(lesson_id, paragraphs)
        if section_id:
            sections = [s for s in sections if s["id"] == section_id]
        return {
            "id": lesson_id,
            "title": meta.get("title", lesson_id),
            "day": meta.get("day", ""),
            "subtitle": meta.get("subtitle", ""),
            "concepts": [c for c in meta.get("concepts", []) if self.cards.get(c)],
            "page_concept": next((c for c in meta.get("concepts", []) if self.cards.get(c)), None),
            "source": self.source_mode(lesson_id),
            "sections": sections,
        }

    def paragraphs(self, lesson_id: str) -> list[dict]:
        if lesson_id in self._cache:
            return self._cache[lesson_id]
        rows = self._local_paragraphs(lesson_id) or self._supabase_paragraphs(lesson_id) or self._summary_paragraphs(lesson_id)
        self._cache[lesson_id] = rows
        return rows

    # --------------------------------------------------------------- nguồn
    def _files(self, lesson_id: str) -> list[str]:
        return self.cards.lesson_files(lesson_id) or []

    def _local_paragraphs(self, lesson_id: str) -> list[dict]:
        r = self.retriever
        if not r or getattr(r, "mode", "") != "local":
            return []
        files = set(self._files(lesson_id))
        docs = [d for d in r.docs if d.file in files] if files else []
        return self._split(((d.id, d.text) for d in docs))

    def _supabase_paragraphs(self, lesson_id: str) -> list[dict]:
        if not (self.sb and self.sb.is_configured()):
            return []
        files = self._files(lesson_id)
        if not files:
            return []
        rows = self.sb.select("lecture_chunks", {"file": f"eq.{files[0]}", "select": "id,text,section", "order": "id.asc", "limit": "500"})
        return self._split((r["id"], r.get("text", "")) for r in rows)

    def _summary_paragraphs(self, lesson_id: str) -> list[dict]:
        files = set(self._files(lesson_id))
        out = []
        for sid, meta in self.cards.sources.items():
            if _file_of(sid) in files:
                out.append({"id": sid, "text": meta.get("summary", ""), "summary": True})
        return sorted(out, key=lambda r: r["id"])

    @staticmethod
    def _split(pairs) -> list[dict]:
        """Tách chunk thành các đoạn [Txx-NNN] rời, bỏ phần chồng lấn, bỏ trùng."""
        seen: dict[str, str] = {}
        order: list[str] = []
        for _cid, text in pairs:
            body = OVERLAP_RE.sub("", text or "")
            parts = PARA_RE.split(body)
            # parts = [phần trước mã đầu tiên, mã, nội dung, mã, nội dung, ...]
            for i in range(1, len(parts) - 1, 2):
                pid, ptext = parts[i], parts[i + 1].strip()
                if not ptext:
                    continue
                if pid not in seen or len(ptext) > len(seen[pid]):
                    if pid not in seen:
                        order.append(pid)
                    seen[pid] = ptext
        return [{"id": pid, "text": seen[pid]} for pid in sorted(order)]

    # --------------------------------------------------------------- mục
    def _group(self, lesson_id: str, paragraphs: list[dict]) -> list[dict]:
        sections = self.cards.sections.get(lesson_id, [])
        if not sections:
            return [{"id": "s1", "title": self.cards.lessons[lesson_id].get("title", ""), "paragraphs": paragraphs}]
        out = [{"id": s["id"], "title": s["title"], "paragraphs": []} for s in sections]
        starts = [str(s.get("from", "")) for s in sections]
        for p in paragraphs:
            idx = 0
            for i, lo in enumerate(starts):
                if lo and p["id"] >= lo:
                    idx = i
            out[idx]["paragraphs"].append(p)
        return [s for s in out if s["paragraphs"]] or out[:1]
