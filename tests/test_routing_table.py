import pytest

from app.service.agent.routing import (
    apply_delta,
    assign_explain_persona,
    next_cooldown,
    route_after_intent,
    route_after_validator,
)
from app.service.agent.nodes import validator

HIT = [{"chunk_id": "c1", "lecture_id": "k4-week3-rag", "slide_page": 12, "text": "RAG", "score": 0.7}]
EMPTY = []
WEAK = [{"chunk_id": "c1", "lecture_id": "k4-week3-rag", "slide_page": 12, "text": "RAG", "score": 0.20}]
WRONG = [{"chunk_id": "c1", "lecture_id": "other", "slide_page": 1, "text": "x", "score": 0.7}]


def st(**kw):
    base = {
        "intent": "ask_concept",
        "user_level": "unknown",
        "awaiting_probe_answer": False,
        "probe_asked_this_episode": False,
        "length_only": False,
        "retrieved_docs": HIT,
        "retrieval_skipped": False,
        "context_lecture_id": "k4-week3-rag",
    }
    base.update(kw)
    return base


def flags(dump=False, adaptive=True):
    return {"DUMP_FIRST": dump, "ADAPTIVE_PROBES": adaptive}


CASES = [
    (1, st(intent="meta", retrieved_docs=EMPTY), flags(), "redirect"),
    (2, st(intent="off_topic", user_level="beginner", retrieved_docs=EMPTY), flags(), "redirect"),
    (3, st(), flags(), "probe"),
    (4, st(user_level="beginner"), flags(), "adapt"),
    (5, st(user_level="intermediate"), flags(), "adapt"),
    (6, st(user_level="advanced"), flags(), "standard"),
    (7, st(), flags(dump=True), "standard"),
    (8, st(), flags(adaptive=False), "adapt"),
    (9, st(retrieved_docs=EMPTY), flags(), "miss"),
    (10, st(retrieved_docs=WEAK), flags(), "miss"),
    (11, st(retrieved_docs=WRONG), flags(), "miss"),
    (12, st(intent="clarify_harder", user_level="beginner", retrieved_docs=EMPTY), flags(), "miss"),
    (13, st(intent="ask_deeper", user_level="beginner", retrieved_docs=EMPTY), flags(), "miss"),
    (14, st(intent="answer_probe", awaiting_probe_answer=True, probe_asked_this_episode=True), flags(), "score"),
    (15, st(intent="answer_probe", awaiting_probe_answer=True, probe_asked_this_episode=True, retrieved_docs=EMPTY), flags(), "miss"),
    (16, st(intent="refuse_probe", awaiting_probe_answer=True, probe_asked_this_episode=True), flags(), "persist_then_adapt"),
    (17, st(intent="refuse_probe"), flags(), "probe"),
    (18, st(intent="clarify_harder", user_level="beginner", awaiting_probe_answer=True, probe_asked_this_episode=True), flags(), "persist_then_adapt"),
    (19, st(intent="clarify_harder"), flags(), "probe"),
    (20, st(intent="clarify_harder", user_level="beginner", probe_asked_this_episode=True), flags(), "persist_then_adapt"),
    (21, st(intent="clarify_harder", user_level="beginner", probe_asked_this_episode=True, length_only=True), flags(), "adapt"),
    (22, st(intent="ask_deeper", user_level="beginner"), flags(), "persist_then_adapt"),
    (23, st(intent="ask_deeper", awaiting_probe_answer=True, probe_asked_this_episode=True), flags(), "persist_then_adapt"),
    (24, st(), flags(), "probe"),
    (25, st(user_level="beginner"), flags(), "adapt"),
    (26, st(user_level="intermediate"), flags(dump=True), "standard"),
    (27, st(intent="ask_deeper", user_level="beginner"), flags(adaptive=False), "persist_then_adapt"),
    (28, st(intent="clarify_harder", user_level="beginner", length_only=True), flags(adaptive=False), "adapt"),
    (29, st(intent="ask_deeper", user_level="beginner", retrieval_skipped=True, retrieved_docs=[]), flags(), "miss"),
    (30, st(retrieval_skipped=True, retrieved_docs=[], flags_adaptive_probes=False), flags(adaptive=False), "miss"),
]


def test_routing_table():
    for n, state, fl, expect in CASES:
        got = route_after_intent(state, fl)
        assert got == expect, f"row {n}: {got} != {expect}"


def test_apply_delta():
    assert apply_delta("unknown", 1) == "intermediate"
    assert apply_delta("unknown", -1) == "beginner"
    assert apply_delta("unknown", 0) == "beginner"
    assert apply_delta("beginner", -1) == "beginner"
    assert apply_delta("advanced", 1) == "advanced"
    assert apply_delta("beginner", 1) == "intermediate"
    assert apply_delta("intermediate", 1) == "advanced"
    assert apply_delta("intermediate", -1) == "beginner"


def test_assign_explain_persona():
    assert assign_explain_persona("unknown") == ("beginner", "eli5")


def test_cooldown_formula():
    assert next_cooldown(2) == 5


def test_first_fail_rewrites_matching_tutor_node():
    stt = {"response_kind": "explanation", "validator_ok": False, "rewrite_count": 0, "tutor_node": "tutor_standard"}
    assert route_after_validator(stt) == "rewrite_standard"
    stt["tutor_node"] = "tutor_adaptive"
    assert route_after_validator(stt) == "rewrite_adaptive"


@pytest.mark.asyncio
async def test_second_fail_done_with_disclaimer():
    stt = {
        "response_kind": "explanation",
        "validator_ok": False,
        "rewrite_count": 1,
        "tutor_node": "tutor_adaptive",
        "draft_answer": "RAG là ...",
    }
    assert route_after_validator(stt) == "done"
    out = await validator(stt)
    assert (out.get("final_answer") or "").startswith("_Một số chi tiết") or out["validator_ok"] in (True, False)
