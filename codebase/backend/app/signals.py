"""Tín hiệu từ câu hỏi (port từ mock/js/engine.js → detect). Không phải quyết định AI."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from .cards import CardStore
from .textutil import norm

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

    def find_concept(self, text: str) -> str | None:
        n = norm(text)
        for cid, rx in self.patterns:
            if rx.search(n):
                return cid
        return None

    def detect(self, text: str, selection: str, session: dict, page_concept: str | None, now: float | None = None) -> Signals:
        now = now or time.time()
        nq = norm(text)
        confused = bool(CONFUSED.search(nq))
        in_question = self.find_concept(text)
        concept = in_question or (self.find_concept(selection) if selection else None)
        from_page = False
        if not concept and (confused or selection):
            concept = session.get("last_concept") or page_concept
            from_page = True
        last = session.get("answered", {}).get(concept or "", 0)
        reask = bool(last and not confused and now - last < self.reask_seconds)
        return Signals(
            text=text, concept=concept, concept_from_page=from_page, confused=confused,
            reask=reask, weighted_sum=bool(WEIGHTED_SUM.search(nq)), vague=confused and not in_question,
        )
