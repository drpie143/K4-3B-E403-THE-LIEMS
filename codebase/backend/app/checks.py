"""Câu kiểm tra hiểu bài (ngân hàng câu trong thẻ, người duyệt)."""
from __future__ import annotations

from .cards import Card
from .schemas import CheckOption, CheckQuestion


def pick(card: Card, attempt: int) -> CheckQuestion | None:
    if not card.checks:
        return None
    q = card.checks[min(attempt, len(card.checks) - 1)]
    return CheckQuestion(
        id=q["id"], concept=card.id, question=q["question"],
        options=[CheckOption(k=o["k"], text=str(o["text"])) for o in q["options"]], src=q.get("src", []),
    )


def grade(card: Card, question_id: str, answer: str) -> dict | None:
    q = next((x for x in card.checks if x["id"] == question_id), None)
    if not q:
        return None
    right = next(o for o in q["options"] if o.get("correct"))
    chosen = next((o for o in q["options"] if o["k"] == answer), None)
    if chosen is None:
        return None
    if chosen.get("correct"):
        return {"correct": True, "right": right["k"], "src": q.get("src", [])}
    mis = next((m for m in card.misconceptions if m["id"] == chosen.get("misconception")), None)
    return {
        "correct": False, "right": right["k"],
        "misconception": mis["id"] if mis else None,
        "fix_html": mis["fix"] if mis else f"Đáp án đúng là {right['k']}: {right['text']}.",
        "src": (mis or {}).get("src") or q.get("src", []),
    }
