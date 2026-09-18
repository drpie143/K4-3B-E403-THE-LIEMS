from __future__ import annotations

from typing import Literal, TypedDict
from uuid import uuid4

from app.service.agent.intent import (
    is_length_only,
    is_new_concept_question,
    match_regex_intent,
)
from app.service.agent.state import AgentState, RouteKey, UserLevel

LEVEL_ORDER: tuple[str, ...] = ("beginner", "intermediate", "advanced")
KNOWLEDGE_INTENTS = frozenset(
    {
        "ask_concept",
        "clarify_harder",
        "ask_deeper",
        "answer_probe",
        "refuse_probe",
    }
)
FEEDBACK_INTENTS = frozenset(
    {
        "answer_probe",
        "refuse_probe",
        "clarify_harder",
        "ask_deeper",
    }
)
SCORE_THR = 0.25
COOLDOWN_TURNS = 3


class RouteFlags(TypedDict):
    DUMP_FIRST: bool
    ADAPTIVE_PROBES: bool


def next_cooldown(turn_index: int) -> int:
    return turn_index + COOLDOWN_TURNS


def apply_delta(level: UserLevel, delta: int) -> UserLevel:
    if level == "unknown":
        if delta > 0:
            return "intermediate"
        return "beginner"
    idx = LEVEL_ORDER.index(level)
    return LEVEL_ORDER[max(0, min(len(LEVEL_ORDER) - 1, idx + delta))]  # type: ignore[return-value]


def is_knowledge_miss(state: AgentState) -> bool:
    intent = state.get("intent")
    if intent not in KNOWLEDGE_INTENTS:
        return False
    if state.get("retrieval_skipped"):
        return True
    docs = state.get("retrieved_docs") or []
    if not docs:
        return True
    if max(d.get("score", 0) for d in docs) < SCORE_THR:
        return True
    lec = state.get("context_lecture_id")
    if lec and not any(d.get("lecture_id") == lec for d in docs):
        return True
    return False


def assign_explain_persona(level: UserLevel) -> tuple[UserLevel, str]:
    if level == "unknown":
        return "beginner", "eli5"
    mode = {
        "beginner": "eli5",
        "intermediate": "slide_short",
        "advanced": "technical",
    }[level]
    return level, mode


def apply_abandon_if_needed(state: dict) -> dict:
    ri = state.get("regex_intent") or state.get("intent")
    if ri == "ask_concept" and state.get("awaiting_probe_answer"):
        state["awaiting_probe_answer"] = False
        state["probe_asked_this_episode"] = False
        state["pending_original_query"] = state.get("user_message")
        state["pending_topic"] = None
        state["episode_id"] = str(uuid4())
        state["route_reason"] = "abandon_probe_new_question"
    return state


def regex_prepass(state: AgentState) -> dict:
    text = (state.get("user_message") or "").lower()
    raw = state.get("user_message") or ""
    ri = match_regex_intent(raw)
    awaiting = bool(state.get("awaiting_probe_answer"))
    last_kind = state.get("last_kind")

    if awaiting and last_kind == "probe":
        if ri is None:
            ri = "ask_concept" if is_new_concept_question(raw) else "answer_probe"
        elif ri not in ("refuse_probe", "meta", "off_topic", "ask_concept"):
            pass
    elif ri is None:
        ri = "ask_concept"

    patch = {**state, "regex_intent": ri}
    apply_abandon_if_needed(patch)
    return {
        "regex_intent": patch["regex_intent"],
        "awaiting_probe_answer": patch.get("awaiting_probe_answer"),
        "probe_asked_this_episode": patch.get("probe_asked_this_episode"),
        "pending_original_query": patch.get("pending_original_query"),
        "pending_topic": patch.get("pending_topic"),
        "episode_id": patch.get("episode_id"),
        "route_reason": patch.get("route_reason") or "",
        "length_only": is_length_only(raw) or bool(state.get("length_only")),
    }


def select_retrieval_query(state: AgentState) -> str | None:
    ri = state.get("regex_intent") or state.get("intent")
    if ri in ("meta", "off_topic"):
        return None
    if ri == "ask_concept":
        return state.get("highlighted_text") or state.get("user_message") or None
    if state.get("awaiting_probe_answer") or ri in FEEDBACK_INTENTS:
        return (
            state.get("last_retrieval_query")
            or state.get("pending_original_query")
            or state.get("highlighted_text")
            or None
        )
    return state.get("highlighted_text") or state.get("user_message") or None


def _as_ask_concept(state: AgentState, flags: RouteFlags) -> RouteKey:
    shadow = {**state, "intent": "ask_concept", "awaiting_probe_answer": False}
    return route_after_intent(shadow, flags)


def route_after_intent(state: AgentState, flags: RouteFlags) -> RouteKey:
    intent = state["intent"]
    L: UserLevel = state["user_level"]
    P = bool(state.get("awaiting_probe_answer"))
    asked = bool(state.get("probe_asked_this_episode"))
    length_only = bool(state.get("length_only"))
    dump_first = bool(flags["DUMP_FIRST"])
    adaptive = bool(flags["ADAPTIVE_PROBES"])

    if intent in ("meta", "off_topic"):
        return "redirect"

    if is_knowledge_miss(state):
        return "miss"

    if not adaptive:
        if intent == "answer_probe" and P:
            return "score"
        if intent in ("refuse_probe", "clarify_harder", "ask_deeper") and (
            P or not length_only
        ):
            if intent == "clarify_harder" and length_only and not P:
                return "adapt"
            return "persist_then_adapt"
        return "adapt"

    if dump_first and intent == "ask_concept" and not P:
        return "standard"

    if intent == "answer_probe":
        return "score" if P else _as_ask_concept(state, flags)

    if intent == "refuse_probe":
        return "persist_then_adapt" if P else _as_ask_concept(state, flags)

    if intent == "ask_concept":
        if L == "unknown":
            return "probe"
        if L == "advanced":
            return "standard"
        return "adapt"

    if intent == "clarify_harder":
        if P:
            return "persist_then_adapt"
        if length_only:
            return "adapt"
        if not asked:
            return "probe"
        return "persist_then_adapt"

    if intent == "ask_deeper":
        return "persist_then_adapt"

    return "redirect"


def route_after_validator(
    state: AgentState,
) -> Literal["rewrite_adaptive", "rewrite_standard", "done"]:
    if (
        state.get("response_kind") == "explanation"
        and not state.get("validator_ok", True)
        and int(state.get("rewrite_count") or 0) < 1
    ):
        return (
            "rewrite_standard"
            if state.get("tutor_node") == "tutor_standard"
            else "rewrite_adaptive"
        )
    return "done"
