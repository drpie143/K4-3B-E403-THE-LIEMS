"""Supabase-only long-term memory behavior."""
from datetime import timedelta

from app.profile_store import utcnow


def rows(orch, table, **eq):
    return orch.store.sb.select(table, {k: f"eq.{v}" for k, v in eq.items()})


def test_ghi_thang_len_supabase(orch):
    orch.store.apply_event("u1", "self_attention", "confused")
    assert rows(orch, "person_profiles", user_id="u1", concept="self_attention")
    assert rows(orch, "person_events", user_id="u1", concept="self_attention")


def test_khong_phinh_profile_cung_khai_niem(orch):
    for _ in range(5):
        orch.store.apply_event("u2", "self_attention", "confused")
    assert len(rows(orch, "person_profiles", user_id="u2", concept="self_attention")) == 1


def test_nen_bo_nho_giu_toi_da_n_cach_giai_thich(orch):
    orch.s.memory_max_strategies = 3
    for i in range(6):
        orch.store.record_strategy("u3", "self_attention", [f"style:cach_{i}"], "worked")
    orch.store.compact("u3")
    assert len(rows(orch, "person_strategy_memory", user_id="u3")) == 3


def test_nen_bo_cach_giai_thich_qua_han(orch):
    old = utcnow() - timedelta(days=orch.s.strategy_ttl_days + 5)
    orch.store.record_strategy("u4", "self_attention", ["analogy:thu_vien"], "worked", now=old)
    orch.store.record_strategy("u4", "self_attention", ["style:ngan_gon"], "worked")
    orch.store.compact("u4")
    left = [r["strategy"] for r in rows(orch, "person_strategy_memory", user_id="u4")]
    assert left == ["style:ngan_gon"]


def test_nen_cat_nhat_ky_su_kien(orch):
    orch.s.memory_max_events = 5
    for _ in range(9):
        orch.store.apply_event("u5", "self_attention", "confused")
    orch.store.compact("u5")
    assert len(rows(orch, "person_events", user_id="u5")) <= 5


def test_trang_thai_phien_khong_phinh(orch):
    state = {"tried": {"self_attention": [f"style_{i}" for i in range(30)]},
             "last_question": "x" * 2000, "last": {}, "answered": {}}
    trimmed = orch.store.trim_session(state)
    assert len(trimmed["tried"]["self_attention"]) <= orch.s.session_max_tried
    assert len(trimmed["last_question"]) <= 500


def test_nap_lai_ho_so_tu_supabase(orch):
    orch.store.sb.upsert("person_settings", {"user_id": "u6", "memory_on": 1, "preferred_style": "vi_du"})
    orch.store.sb.upsert("person_profiles", {
        "user_id": "u6", "concept": "self_attention", "level": "hieu_ro",
        "streak": 2, "source": "kiem_tra",
    })
    orch.store.sb.upsert("person_strategy_memory", {
        "user_id": "u6", "concept": "self_attention", "strategy": "analogy:thu_vien",
        "worked": 2, "failed": 0,
    })
    prof = orch.store.profile("u6")
    assert prof["concepts"]["self_attention"]["level"] == "hieu_ro"
    assert prof["preferred_style"] == "vi_du"
    assert "analogy:thu_vien" in orch.store.learner_memory("u6", "self_attention")["worked"]


def test_xoa_ho_so_xoa_ca_tren_supabase(orch):
    orch.store.apply_event("u7", "self_attention", "confused")
    orch.store.delete("u7")
    assert rows(orch, "person_profiles", user_id="u7") == []
    assert rows(orch, "person_strategy_memory", user_id="u7") == []
