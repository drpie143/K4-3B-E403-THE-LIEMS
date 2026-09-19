"""Danh mục 6 buổi học + phần thân bài đọc trên giao diện.

Nguồn nội dung, theo thứ tự ưu tiên:
  1. Bảng `lecture_chunks` trên Supabase.
  2. Đoạn local trong Retriever chỉ khi chưa cấu hình Supabase.
  3. Tóm tắt do nhóm tự viết trong cards/_sources.yaml.

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

# ------------------------------------------------------------------ dọn transcript
# Transcript là lời nói: có ghi chú hiện trường, chỗ nghe không rõ, và từ đệm.
# Bản "đọc được" bỏ những thứ đó đi; nguyên văn vẫn giữ nguyên để đối chiếu.
ACTIVITY_RE = re.compile(r"\[\s*Hoạt động lớp\s*:\s*(.+?)\]", re.S | re.I)
INAUDIBLE_RE = re.compile(r"\[\s*(?:không nghe rõ|nghe không rõ|không rõ)\s*\]", re.I)
# Từ đệm cuối câu, chỉ bỏ khi đứng ngay trước dấu chấm/phẩy — tránh cắt nhầm giữa câu.
FILLER_TAIL_RE = re.compile(
    r"[,\s]*\b(?:đúng không|phải không|nhé|nhá|nha|ạ|à|ha|hen|đấy|ấy mà|các bạn nhé|"
    r"các bạn ạ|nói chung là|kiểu như là|thế thôi)\b(?=\s*[.,;!?]|\s*$)", re.I)
FILLER_LEAD_RE = re.compile(r"^(?:ừm|ờ|à|ôkê|ok|okay|đấy|thế|thì|và|rồi|vâng)[,\s]+", re.I)
MULTI_DOT_RE = re.compile(r"(?:\s*…\s*){2,}")
SPACE_RE = re.compile(r"[ \t]{2,}")


def _file_of(source_id: str) -> str:
    """T03-105 → transcript-03-clean.md."""
    return f"transcript-{source_id[1:3]}-clean.md"


def clean_paragraph(raw: str) -> tuple[str, list[str]]:
    """Lời nói → câu đọc được. Trả về (nội dung đã dọn, các ghi chú hoạt động lớp).

    Chỉ bỏ thứ không mang nghĩa: ghi chú hiện trường, chỗ nghe không rõ, từ đệm đầu/cuối câu.
    Không tóm tắt, không viết lại — nguyên văn vẫn giữ nguyên ở trường `raw`.
    """
    activities = [" ".join(m.split()) for m in ACTIVITY_RE.findall(raw or "")]
    text = ACTIVITY_RE.sub(" ", raw or "")
    text = INAUDIBLE_RE.sub("…", text)
    parts = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        s = FILLER_LEAD_RE.sub("", sentence.strip())
        prev = None
        while prev != s:                      # "…, đúng không nhé." → bóc từng lớp từ đệm
            prev = s
            s = FILLER_TAIL_RE.sub("", s)
        s = s.strip(" ,;")
        # Câu chỉ còn dấu câu hoặc một chữ thì không còn nội dung gì để đọc.
        if len(s) > 2:
            s = s[0].upper() + s[1:]            # bỏ "Và/Thì" đầu câu xong phải viết hoa lại
            parts.append(s if s[-1] in ".!?…" else s + ".")
    out = " ".join(parts)
    out = MULTI_DOT_RE.sub(" … ", out)
    return SPACE_RE.sub(" ", out).strip(), activities


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
        if self._supabase_paragraphs(lesson_id):
            return "supabase"
        if self.sb and self.sb.is_configured() and not getattr(self.sb, "allow_local_fallback", False):
            return "supabase_empty"
        if self._local_paragraphs(lesson_id):
            return "local"
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
            "pdf_url": meta.get("pdf_url"),
            "source": self.source_mode(lesson_id),
            "sections": sections,
        }

    def paragraphs(self, lesson_id: str) -> list[dict]:
        if lesson_id in self._cache:
            return self._cache[lesson_id]
        rows = self._supabase_paragraphs(lesson_id)
        strict_supabase = self.sb and self.sb.is_configured() and not getattr(self.sb, "allow_local_fallback", False)
        if not rows and not strict_supabase:
            rows = self._local_paragraphs(lesson_id) or self._summary_paragraphs(lesson_id)
        self._cache[lesson_id] = rows
        return rows

    # --------------------------------------------------------------- nguồn
    def _files(self, lesson_id: str) -> list[str]:
        return self.cards.lesson_files(lesson_id) or []

    def _local_paragraphs(self, lesson_id: str) -> list[dict]:
        r = self.retriever
        if self.sb and self.sb.is_configured() and not getattr(self.sb, "allow_local_fallback", False):
            return []
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
            out = [{"id": "s1", "title": self.cards.lessons[lesson_id].get("title", ""), "paragraphs": paragraphs}]
        else:
            out = [{"id": s["id"], "title": s["title"], "paragraphs": []} for s in sections]
            starts = [str(s.get("from", "")) for s in sections]
            for p in paragraphs:
                idx = 0
                for i, lo in enumerate(starts):
                    if lo and p["id"] >= lo:
                        idx = i
                out[idx]["paragraphs"].append(p)
            out = [s for s in out if s["paragraphs"]] or out[:1]
        for s in out:
            self._enrich(s)
        return out

    def _enrich(self, section: dict) -> None:
        """Thêm phần đọc được cho một mục: bản đã dọn, ghi chú hoạt động lớp, ý chính.

        Ý chính lấy từ core_claims của các thẻ khái niệm có nguồn nằm trong mục này — đều là
        câu đã được TA/giảng viên duyệt, không phải máy tóm tắt, nên hiển thị được yên tâm.
        """
        activities: list[str] = []
        for p in section["paragraphs"]:
            if "raw" in p:                      # đã dọn rồi (mục được gọi hai lần)
                continue
            clean, acts = clean_paragraph(p["text"])
            rest = ACTIVITY_RE.sub(" ", p["text"] or "")
            only_activity = bool(acts) and not re.search(r"\w", rest)
            p["raw"] = p["text"]
            # Đoạn chỉ có ghi chú hiện trường → không phải lời giảng, hiện riêng ở phần "hoạt động lớp".
            # Ngược lại, nếu dọn xong mà trắng thì giữ nguyên văn còn hơn để trống.
            p["text"] = "" if only_activity else (clean or p["text"])
            p["empty"] = not p["text"]
            activities += acts
        section["activities"] = list(dict.fromkeys(activities))

        ids = {p["id"] for p in section["paragraphs"]}
        concepts, points, seen = [], [], set()
        for pid in sorted(ids):
            for card in self.cards.by_source(pid):
                if card.id in seen:
                    continue
                seen.add(card.id)
                concepts.append({"id": card.id, "term": card.term, "vi_name": card.vi_name})
                for claim in card.core_claims:
                    points.append({"text": claim["text"], "src": claim.get("src", []), "concept": card.id})
        section["concepts"] = concepts
        section["key_points"] = points[:5]      # đủ để nắm mục, không biến slide thành bài đọc thứ hai
