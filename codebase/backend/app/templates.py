"""Chọn mẫu trả lời đã duyệt theo quyết định (port composeAnswer của mock).

Dùng cho: FakeLLM, dự phòng khi LLM lỗi/validator rớt, và reference_answer trong prompt.
"""
from __future__ import annotations

from .cards import CardStore
from .schemas import LEVELS, Answer, Block, Decision

DEFAULT_ANALOGY = {"L1": "con_meo", "L2": "thu_vien"}


def rank(level: str) -> int:
    return LEVELS.index(level)


def step(level: str, delta: int) -> str:
    return LEVELS[max(0, min(len(LEVELS) - 1, rank(level) + delta))]


def pick_analogy(card, d: Decision) -> str | None:
    ids = card.analogy_ids
    if not ids:
        return None
    base = d.preferred_analogy if d.preferred_analogy in ids else DEFAULT_ANALOGY.get(d.level, ids[0])
    if base not in ids:
        base = ids[0]
    if d.alt_example and len(ids) > 1:
        base = next(a for a in ids if a != base)
    return base


def template_key(card, d: Decision) -> tuple[str, str | None]:
    if "first" in card.templates and len(card.templates) == 1:
        return "first", None
    r = rank(d.level)
    if r >= 3:
        return d.level, None
    if r == 2:
        return ("L3" if d.full else "L3_first"), None
    if d.full and d.style == "vi_du":
        analogy = pick_analogy(card, d)
        key = f"{d.level}_vi_du_{analogy}"
        if key in card.templates:
            return key, analogy
    return f"{d.level}_ngan_gon", None


def build_answer(cards: CardStore, d: Decision) -> Answer:
    card = cards.get(d.concept)
    key, analogy = template_key(card, d)
    blocks = card.template(key) or card.template("first") or next(iter([card.template(k) for k in card.templates]))
    blocks = list(blocks)
    if d.prereq_first:
        pre = cards.get(d.prereq_first)
        if pre and pre.primer:
            blocks.insert(0, Block(t="prereq", title=f"Trước hết: {pre.term}", html=pre.primer["html"], src=pre.primer.get("src", [])))
    if d.weighted_sum and rank(d.level) <= 2:
        extra = card.extra("weighted_sum")
        if extra:
            blocks.append(extra)
    return Answer(key=key, blocks=blocks, analogy_id=analogy, summary_for_next_turn=f"{key}")
