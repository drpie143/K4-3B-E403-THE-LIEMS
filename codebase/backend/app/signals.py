"""Tín hiệu từ câu hỏi (port từ mock/js/engine.js → detect). Không phải quyết định AI."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .cards import CardStore
from .textutil import norm

# Khía cạnh học viên hỏi — thứ tự dò từ hẹp đến rộng.
ASK_TYPES = [
    ("ung_dung", re.compile(r"ung dung|dung de lam gi|de lam gi|lam duoc gi|ap dung|dung o dau|co tac dung gi|loi ich|giai quyet duoc gi")),
    ("so_sanh", re.compile(r"khac gi|khac nhau|so voi|so sanh|hon kem|thay vi")),
    ("vi_du", re.compile(r"vi du|minh hoa|cho mot case|truong hop cu the")),
    ("co_che", re.compile(r"hoat dong|van hanh|co che|cach (no |)chay|tinh (nhu )?the nao|buoc \d|quy trinh|lam sao (no |)")),
    ("khai_niem", re.compile(r"la gi|la sao|dinh nghia|nghia la|hieu the nao")),
]

CONFUSED = re.compile(r"chua hieu|khong hieu|ko hieu|\bk hieu|kho hieu|giai thich lai|chua ro|roi qua|don gian hon|de hieu hon|khong hieu gi")
WEIGHTED_SUM = re.compile(r"cong trong so|cong vao dau|tong co trong so|weighted sum")
# Thứ tự dò: khái niệm hẹp trước, rộng sau.
CONCEPT_ORDER = ["multi_head", "similarity", "vector", "self_attention", "token"]


@dataclass
class Signals:
    text: str
    concept: str | None
    concept_from_page: bool
    confused: bool
    reask: bool
    weighted_sum: bool
    vague: bool
    ask_type: str  # ung_dung | so_sanh | vi_du | co_che | khai_niem | khac


def _alias_regex(aliases: list[str]) -> re.Pattern:
    parts = []
    for a in aliases:
        a = norm(a)
        a = re.escape(a).replace(r"\ ", r"\s*").replace(",", ",?")
        parts.append(rf"(?<![a-z0-9]){a}(?![a-z0-9])")
    return re.compile("|".join(parts)) if parts else re.compile(r"$^")


class SignalDetector:
    def __init__(self, cards: CardStore, reask_seconds: int = 180):
        self.cards = cards
        self.reask_seconds = reask_seconds
        order = [c for c in CONCEPT_ORDER if c in cards.cards] + [c for c in cards.cards if c not in CONCEPT_ORDER]
        self.patterns = [(cid, _alias_regex(cards.cards[cid].aliases + [cards.cards[cid].term])) for cid in order]

    def find_concept(self, text: str, lesson_concepts: list[str] | None = None) -> str | None:
        """Tìm khái niệm được nhắc tới. Khái niệm của buổi đang mở được ưu tiên
        (tránh bắt nhầm sang thẻ của buổi khác khi hai thẻ có từ khoá gần nhau)."""
        n = norm(text)
        hits = [cid for cid, rx in self.patterns if rx.search(n)]
        if not hits:
            return None
        if lesson_concepts:
            in_lesson = [c for c in hits if c in lesson_concepts]
            if in_lesson:
                return in_lesson[0]
        return hits[0]

    def detect(self, text: str, selection: str, session: dict, page_concept: str | None, now: float | None = None,
               lesson_concepts: list[str] | None = None) -> Signals:
        now = now or time.time()
        nq = norm(text)
        confused = bool(CONFUSED.search(nq))
        in_question = self.find_concept(text, lesson_concepts)
        concept = in_question or (self.find_concept(selection, lesson_concepts) if selection else None)
        from_page = False
        if not concept and (confused or selection):
            concept = session.get("last_concept") or page_concept
            from_page = True
        ask_type = next((name for name, rx in ASK_TYPES if rx.search(nq)), "khac")
        last = session.get("answered", {}).get(concept or "", 0)
        # Hỏi lại = hỏi cùng một khía cạnh trong thời gian ngắn. Hỏi khía cạnh khác là câu hỏi mới.
        # Phiên cũ (trước khi có ask_type) không ghi khía cạnh → chỉ coi là hỏi lại nếu câu mới cũng chung chung.
        prev_ask = session.get("last", {}).get(concept or "", {}).get("ask_type")
        same_aspect = prev_ask == ask_type if prev_ask else ask_type in ("khai_niem", "khac")
        reask = bool(last and not confused and same_aspect and now - last < self.reask_seconds)
        return Signals(
            text=text, concept=concept, concept_from_page=from_page, confused=confused,
            reask=reask, weighted_sum=bool(WEIGHTED_SUM.search(nq)), vague=confused and not in_question,
            ask_type=ask_type,
        )
