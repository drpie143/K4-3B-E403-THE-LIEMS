from __future__ import annotations

import json
import re
from functools import lru_cache
from app.service.agent.state import UserLevel
from app.config import repo_root

TEMPLATE_PATH = repo_root() / "app" / "fixtures" / "probe_templates.json"

BEGINNER_KW = re.compile(r"mới học|chưa biết|lần đầu|chưa từng|mới bắt đầu", re.I)
ADVANCED_KW = re.compile(r"production|đã deploy|vector search|đã dùng embedding", re.I)


@lru_cache
def load_templates() -> dict:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def get_probe_template(topic_key: str) -> dict:
    data = load_templates()
    return data.get(topic_key) or data["generic"]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def score_probe_answer(message: str, choices: list[dict] | None) -> dict:
    text = message or ""
    n = _norm(text)
    for ch in choices or []:
        if n == _norm(ch.get("text") or ""):
            return {
                "level": ch["maps_to_level"],
                "confidence": 0.9,
                "source": "choice_map",
                "reason": "exact choice text",
            }
        cid = str(ch.get("id") or "")
        if len(n) == 1 and n == cid.lower():
            return {
                "level": ch["maps_to_level"],
                "confidence": 0.9,
                "source": "choice_map",
                "reason": "choice id",
            }
    if BEGINNER_KW.search(text):
        return {
            "level": "beginner",
            "confidence": 0.85,
            "source": "keyword",
            "reason": "beginner keyword",
        }
    if ADVANCED_KW.search(text):
        return {
            "level": "advanced",
            "confidence": 0.8,
            "source": "keyword",
            "reason": "advanced keyword",
        }
    return {
        "level": "beginner",
        "confidence": 0.5,
        "source": "fallback_low_conf",
        "reason": "unscored free text → beginner",
    }


def band_raw(raw: int) -> UserLevel:
    if raw <= 4:
        return "beginner"
    if raw == 5:
        return "intermediate"
    return "advanced"
