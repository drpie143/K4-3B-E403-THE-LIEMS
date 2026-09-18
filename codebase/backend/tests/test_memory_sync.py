"""Bộ nhớ dài hạn: ghi trễ theo nhịp, nén để không phình, và nạp lại từ Supabase."""
from datetime import timedelta

from app.profile_store import utcnow


class FakeSupabase:
    """Supabase giả: đủ cho việc đếm số lần ghi và kiểm tra dữ liệu được đẩy lên."""

    def __init__(self, rows=None):
        self.rows = rows or {}
        self.upserts = []
        self.deletes = []

    def is_configured(self):
        return True

    def select(self, table, params=None):
        return self.rows.get(table, [])

    def upsert(self, table, records):
        batch = records if isinstance(records, list) else [records]
        self.upserts.append((table, batch))
        return True

    def update(self, table, filters, data):
        return True

    def delete(self, table, filters):
        self.deletes.append((table, filters))
        return True


def use_fake(orch, rows=None):
    sb = FakeSupabase(rows)
    orch.store.sb = sb
    orch.store.mem.sb = sb
    return sb


def test_khong_ghi_moi_luot_ma_gom_lai(orch):
    """Ghi trễ: 3 lượt hỏi mới đẩy một lần (MEMORY_FLUSH_EVERY mặc định = 3)."""
    sb = use_fake(orch)
    for i in range(2):
        orch.store.note_turn("u1")
    assert sb.upserts == [], "chưa đủ 3 lượt thì chưa được gọi mạng"
    orch.store.apply_event("u1", "self_attention", "confused")
    orch.store.note_turn("u1")
    assert sb.upserts, "đủ 3 lượt phải đẩy một lần"
    tables = {t for t, _ in sb.upserts}
    assert "profiles" in tables or "events" in tables


def test_hang_doi_khong_phinh_theo_so_luot(orch):
    use_fake(orch)
    for _ in range(5):
        orch.store.apply_event("u2", "self_attention", "confused")
    # cùng một khái niệm → vẫn chỉ một dòng profiles trong hàng đợi
    assert len(orch.store.mem.queue["profiles"]) == 1


def test_nen_bo_nho_giu_toi_da_n_cach_giai_thich(orch):
    use_fake(orch)
    orch.s.memory_max_strategies = 3
    for i in range(6):
        orch.store.record_strategy("u3", "self_attention", [f"style:cach_{i}"], "worked")
    orch.store.compact("u3")
    rows = orch.store.db.execute("SELECT strategy FROM strategy_memory WHERE user_id=?", ("u3",)).fetchall()
    assert len(rows) == 3


def test_nen_bo_cach_giai_thich_qua_han(orch):
    use_fake(orch)
    old = utcnow() - timedelta(days=orch.s.strategy_ttl_days + 5)
    orch.store.record_strategy("u4", "self_attention", ["analogy:thu_vien"], "worked", now=old)
    orch.store.record_strategy("u4", "self_attention", ["style:ngan_gon"], "worked")
    orch.store.compact("u4")
    left = [r["strategy"] for r in orch.store.db.execute(
        "SELECT strategy FROM strategy_memory WHERE user_id=?", ("u4",)).fetchall()]
    assert left == ["style:ngan_gon"]


def test_nen_cat_nhat_ky_su_kien(orch):
    use_fake(orch)
    orch.s.memory_max_events = 5
    for _ in range(9):
        orch.store.apply_event("u5", "self_attention", "confused")
    orch.store.compact("u5")
    n = orch.store.db.execute("SELECT COUNT(*) c FROM events WHERE user_id=?", ("u5",)).fetchone()["c"]
    assert n <= 5


def test_trang_thai_phien_khong_phinh(orch):
    state = {"tried": {"self_attention": [f"style_{i}" for i in range(30)]},
             "last_question": "x" * 2000, "last": {}, "answered": {}}
    trimmed = orch.store.trim_session(state)
    assert len(trimmed["tried"]["self_attention"]) <= orch.s.session_max_tried
    assert len(trimmed["last_question"]) <= 500


def test_nap_lai_ho_so_tu_supabase(orch):
    """Đăng nhập trên máy khác: hồ sơ và bộ nhớ được kéo từ Supabase về."""
    use_fake(orch, {
        "settings": [{"user_id": "u6", "memory_on": 1, "preferred_style": "vi_du"}],
        "profiles": [{"user_id": "u6", "concept": "self_attention", "level": "hieu_ro", "streak": 2, "source": "kiem_tra"}],
        "strategy_memory": [{"user_id": "u6", "concept": "self_attention", "strategy": "analogy:thu_vien", "worked": 2, "failed": 0}],
    })
    orch.store.ensure_user("u6")
    prof = orch.store.profile("u6")
    assert prof["concepts"]["self_attention"]["level"] == "hieu_ro"
    assert prof["preferred_style"] == "vi_du"
    mem = orch.store.learner_memory("u6", "self_attention")
    assert "analogy:thu_vien" in mem["worked"]


def test_xoa_ho_so_xoa_ca_tren_supabase(orch):
    sb = use_fake(orch)
    orch.store.apply_event("u7", "self_attention", "confused")
    orch.store.delete("u7")
    assert any(t == "profiles" for t, _ in sb.deletes)
    assert any(t == "strategy_memory" for t, _ in sb.deletes)
