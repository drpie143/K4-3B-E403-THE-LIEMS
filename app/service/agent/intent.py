from __future__ import annotations

import re

from app.service.agent.state import ExplanationMode, Intent, ResponseKind

LENGTH_ONLY_RE = re.compile(r"^(ngắn lại|ngắn hơn|rút ngắn)[\s.!]*$", re.IGNORECASE)
HARDER_RE = re.compile(
    r"khó hiểu|giải thích lại|đơn giản hơn|không hiểu|rối quá|phức tạp|dễ hiểu hơn|\beli5\b",
    re.IGNORECASE,
)
DEEPER_RE = re.compile(r"nâng cao hơn|chi tiết kỹ thuật|sâu hơn", re.IGNORECASE)
REFUSE_RE = re.compile(r"không biết|bỏ qua|cứ giải thích|trả lời đi|\bskip\b", re.IGNORECASE)
META_RE = re.compile(r"bạn là ai|who are you|system prompt", re.IGNORECASE)
OFF_RE = re.compile(r"kể chuyện cười|hát một bài|kể joke", re.IGNORECASE)
AMBIGUOUS_DETAIL_RE = re.compile(r"giải thích chi tiết hơn|chi tiết hơn", re.IGNORECASE)
NEW_QUESTION_RE = re.compile(
    r"là gì|là sao|như thế nào|khác gì|how does|what is|giải thích .+ là",
    re.IGNORECASE,
)


def match_regex_intent(text: str) -> Intent | None:
    t = (text or "").strip()
    if not t:
        return None
    low = t.lower()
    if LENGTH_ONLY_RE.match(low):
        return "clarify_harder"
    if DEEPER_RE.search(low):
        return "ask_deeper"
    if REFUSE_RE.search(low):
        return "refuse_probe"
    if META_RE.search(low):
        return "meta"
    if OFF_RE.search(low):
        return "off_topic"
    if HARDER_RE.search(low):
        return "clarify_harder"
    return None


def is_length_only(text: str) -> bool:
    return bool(LENGTH_ONLY_RE.match((text or "").strip().lower()))


def is_new_concept_question(text: str) -> bool:
    t = (text or "").strip()
    if NEW_QUESTION_RE.search(t):
        return True
    if t.endswith("?") and len(t) > 8:
        return True
    return False


def is_ambiguous_detail(text: str) -> bool:
    t = (text or "").strip()
    if not AMBIGUOUS_DETAIL_RE.search(t):
        return False
    if DEEPER_RE.search(t) or HARDER_RE.search(t):
        return False
    return True


def resolve_ambiguous_detail(
    last_kind: ResponseKind | None,
    last_mode: ExplanationMode | None,
    sentences: int,
) -> Intent:
    if last_kind == "probe":
        return "answer_probe"
    if last_kind == "explanation":
        if last_mode == "eli5":
            return "ask_deeper"
        if last_mode == "slide_short":
            return "ask_deeper" if sentences <= 5 else "clarify_harder"
        if last_mode == "technical":
            return "clarify_harder"
        if sentences <= 3:
            return "ask_deeper"
    return "clarify_harder"
