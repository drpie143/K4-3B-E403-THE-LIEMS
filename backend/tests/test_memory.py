"""§7.4.8 — kiểm thử bộ nhớ dài hạn."""
from datetime import timedelta

from app.profile_store import utcnow
from app.schemas import ChatRequest, CheckAnswerRequest, FeedbackRequest


def ask(o, user, text, sid="m1"):
    return o.chat(ChatRequest(user_id=user, session_id=sid, text=text))


def test_worked_analogy_is_reused(orch):
    r = ask(orch, "demo-thu-vien", "self-attention là gì, mình chưa hiểu")
    assert r.decision.preferred_analogy == "thu_vien"
    assert r.answer.analogy_id == "thu_vien"
    assert "Thư viện" in r.decision.reason_for_user


def test_failed_style_is_avoided(orch):
    mem = orch.store.learner_memory("demo-thu-vien", "self_attention")
    assert "style:chi_tiet" in mem["failed"]
    orch.store.update_settings("demo-thu-vien", preferred_style="chi_tiet")
    r = ask(orch, "demo-thu-vien", "Self-attention là gì?")
    assert r.decision.style != "chi_tiet"


def test_stale_lowers_effective_level_and_confidence(orch):
    mem = orch.store.learner_memory("demo-lau-ngay", "self_attention")
    sa = mem["concepts"]["self_attention"]
    assert sa["stale"] and sa["level"] == "hieu_ro" and sa["effective_level"] == "biet_so"
    r = ask(orch, "demo-lau-ngay", "Self-attention là gì?")
    assert r.decision.level == "L3"  # chưa stale thì là L5
    fresh = orch.store.learner_memory("demo-vung", "self_attention")
    assert not fresh["stale_any"]


def test_no_inference_between_concepts(orch):
    orch.store.ensure_user("u-x")
    orch.store.apply_event("u-x", "multi_head", "manual", level="hieu_ro")
    mem = orch.store.learner_memory("u-x", "self_attention")
    assert "self_attention" not in mem["concepts"]


def test_memory_off_returns_empty_and_writes_nothing(orch):
    orch.store.update_settings("demo-moi", memory_on=False)
    assert orch.store.learner_memory("demo-moi", "self_attention")["concepts"] == {}
    before = len(orch.store.sb.select("person_events", {}))
    assert orch.store.apply_event("demo-moi", "self_attention", "check_correct") is None
    orch.store.record_strategy("demo-moi", "self_attention", ["style:vi_du"], "worked")
    assert len(orch.store.sb.select("person_events", {})) == before


def test_delete_all_clears_three_tables(orch):
    ask(orch, "demo-thu-vien", "Self-attention là gì?")
    orch.store.delete("demo-thu-vien")
    for table in ("person_profiles", "person_strategy_memory", "person_events"):
        assert orch.store.sb.select(table, {"user_id": "eq.demo-thu-vien"}) == []


def test_correct_after_up_records_worked(orch):
    r = ask(orch, "demo-moi", "self-attention mình chưa hiểu")
    orch.feedback(FeedbackRequest(user_id="demo-moi", session_id="m1", concept="self_attention", value="up"))
    orch.check_answer(CheckAnswerRequest(user_id="demo-moi", session_id="m1", concept="self_attention", question_id="SA-Q1", answer="B"))
    mem = orch.store.learner_memory("demo-moi", "self_attention")
    assert f"analogy:{r.answer.analogy_id}" in mem["worked"]


def test_level_rules_two_correct_then_raise_and_undo(orch):
    s = orch.store
    s.ensure_user("u1")
    s.apply_event("u1", "self_attention", "self_report", level="chua")
    n1 = s.apply_event("u1", "self_attention", "check_correct")
    assert s.profile("u1")["concepts"]["self_attention"]["level"] == "chua" and "thêm 1 lần" in n1.text
    n2 = s.apply_event("u1", "self_attention", "check_correct")
    assert s.profile("u1")["concepts"]["self_attention"]["level"] == "biet_so"
    assert s.undo("u1", n2.event_ids[0])
    assert s.profile("u1")["concepts"]["self_attention"]["level"] == "chua"


def test_wrong_resets_streak_and_confused_lowers(orch):
    s = orch.store
    s.ensure_user("u2")
    s.apply_event("u2", "self_attention", "self_report", level="biet_so")
    s.apply_event("u2", "self_attention", "check_correct")
    s.apply_event("u2", "self_attention", "check_wrong")
    s.apply_event("u2", "self_attention", "check_correct")
    assert s.profile("u2")["concepts"]["self_attention"]["level"] == "biet_so"
    s.apply_event("u2", "self_attention", "confused")
    assert s.profile("u2")["concepts"]["self_attention"]["level"] == "chua"


def test_strategy_ttl(orch):
    s = orch.store
    s.ensure_user("u3")
    old = utcnow() - timedelta(days=40)
    s.record_strategy("u3", "self_attention", ["analogy:thu_vien"], "worked", now=old)
    assert s.learner_memory("u3", "self_attention")["worked"] == []
