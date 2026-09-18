"""Soạn sẵn câu hỏi cho TA. Không kèm tên học viên, không tự gửi."""
from __future__ import annotations

from .cards import Card
from .schemas import STYLE_LABEL


def draft(card: Card | None, session: dict, lesson_title: str) -> str:
    term = card.term if card else "nội dung này"
    question = session.get("last_question") or term
    tried = list(dict.fromkeys(session.get("tried", {}).get(card.id if card else "", [])))
    tried_txt = ", ".join(STYLE_LABEL.get(t, t) for t in tried)
    text = f"Mình đang học {term} ({lesson_title}). Mình chưa hiểu: “{question}”."
    if tried_txt:
        text += f" Trợ giảng AI đã giải thích theo kiểu: {tried_txt}."
    return text + " Mình cần được giải thích thêm phần này."
