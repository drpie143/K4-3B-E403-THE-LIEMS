"""Tài khoản: đăng ký, đăng nhập, và hồ sơ gắn đúng người."""
import pytest
from fastapi.testclient import TestClient

from app import main
from app.auth import AuthError


def client(orch):
    main.app.dependency_overrides[main.get_orchestrator] = lambda: orch
    return TestClient(main.app)


def test_dang_ky_va_dang_nhap(orch):
    acc = orch.auth.register("an@vinuni.edu.vn", "matkhau123", "An")
    assert acc["user_id"].startswith("u_") and acc["email"] == "an@vinuni.edu.vn"
    _, token = orch.auth.login("an@vinuni.edu.vn", "matkhau123")
    assert orch.auth.account_for_token(token)["user_id"] == acc["user_id"]
    orch.auth.logout(token)
    assert orch.auth.account_for_token(token) is None


def test_tu_choi_dau_vao_khong_hop_le(orch):
    with pytest.raises(AuthError):
        orch.auth.register("khong-phai-email", "matkhau123")
    with pytest.raises(AuthError):
        orch.auth.register("b@vinuni.edu.vn", "ngan")
    orch.auth.register("b@vinuni.edu.vn", "matkhau123")
    with pytest.raises(AuthError):
        orch.auth.register("b@vinuni.edu.vn", "matkhau123")  # trùng email
    with pytest.raises(AuthError):
        orch.auth.login("b@vinuni.edu.vn", "sai-mat-khau")


def test_mat_khau_khong_luu_dang_tho(orch):
    orch.auth.register("c@vinuni.edu.vn", "matkhau123")
    row = orch.store.sb.select("person_accounts", {"email": "eq.c@vinuni.edu.vn"})[0]
    assert "matkhau123" not in row["password_hash"] and row["password_hash"].startswith("pbkdf2$")


def test_http_dang_nhap_roi_hoc(orch):
    c = client(orch)
    r = c.post("/api/auth/register", json={"email": "d@vinuni.edu.vn", "password": "matkhau123", "display_name": "D"})
    assert r.status_code == 200
    token, uid = r.json()["token"], r.json()["account"]["user_id"]
    head = {"Authorization": "Bearer " + token}

    # user_id gửi lên bị bỏ qua: mọi thao tác gắn vào tài khoản đang đăng nhập
    chat = c.post("/api/chat", headers=head,
                  json={"user_id": "nguoi-khac", "session_id": "s1", "lesson_id": "day01-foundation-b",
                        "text": "Self-attention là gì?"}).json()
    assert chat["kind"] == "explain"
    assert c.get("/api/auth/me", headers=head).json()["account"]["user_id"] == uid
    assert orch.store.sb.select("person_settings", {"user_id": "eq.nguoi-khac"}) == []

    assert c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/logout", headers=head).status_code == 200
    assert c.get("/api/auth/me", headers=head).status_code == 401


def test_xoa_tai_khoan_xoa_luon_du_lieu(orch):
    c = client(orch)
    tok = c.post("/api/auth/register", json={"email": "e@vinuni.edu.vn", "password": "matkhau123"}).json()["token"]
    head = {"Authorization": "Bearer " + tok}
    uid = c.get("/api/auth/me", headers=head).json()["account"]["user_id"]
    c.post("/api/chat", headers=head, json={"user_id": uid, "session_id": "s2",
                                            "lesson_id": "day01-foundation-b", "text": "Token là gì?"})
    assert c.request("DELETE", "/api/auth/me", headers=head).status_code == 200
    assert orch.store.sb.select("person_accounts", {"id": f"eq.{uid}"}) == []
    assert orch.store.sb.select("person_profiles", {"user_id": f"eq.{uid}"}) == []


def test_can_dang_nhap_va_khong_xoa_duoc_phien_nguoi_khac(orch):
    c = client(orch)
    payload = {"session_id": "shared", "lesson_id": "day01-foundation-b", "text": "Token la gi?"}
    for method, path, kwargs in [
        ("post", "/api/chat", {"json": payload}),
        ("get", "/api/profile", {}),
        ("get", "/api/lessons", {}),
        ("get", "/api/sources/T06-131", {}),
        ("post", "/api/session/reset", {"params": {"session_id": "shared"}}),
    ]:
        assert getattr(c, method)(path, **kwargs).status_code == 401

    one = c.post("/api/auth/register", json={"email": "one@example.com", "password": "password123"}).json()
    two = c.post("/api/auth/register", json={"email": "two@example.com", "password": "password123"}).json()
    head_one = {"Authorization": "Bearer " + one["token"]}
    head_two = {"Authorization": "Bearer " + two["token"]}
    assert c.post("/api/chat", json=payload, headers=head_one).status_code == 200
    assert c.post("/api/session/reset", params={"session_id": "shared"}, headers=head_two).status_code == 200
    assert orch.store.sb.select("person_chat_sessions", {
        "session_id": f"eq.{one['account']['user_id']}:shared",
        "user_id": f"eq.{one['account']['user_id']}",
    })
    assert c.post("/api/chat", json=payload, headers=head_two).status_code == 200
    assert len([r for r in orch.store.sb.tables["person_chat_sessions"] if r["session_id"].endswith(":shared")]) == 2


def test_dang_ky_bao_loi_khi_supabase_khong_ghi_duoc(orch):
    class Remote:
        def is_configured(self):
            return True

        def select(self, table, params):
            return []

        def upsert(self, table, record):
            return False

    orch.auth.sb = Remote()
    orch.store.sb = Remote()
    c = client(orch)
    r = c.post("/api/auth/register", json={"email": "remote@example.com", "password": "password123"})
    assert r.status_code == 503
    assert True


def test_dang_nhap_ghi_tai_khoan_va_phien_len_supabase(orch):
    acc = orch.auth.register("local@example.com", "password123")
    result, token = orch.auth.login("local@example.com", "password123")
    assert result["user_id"] == acc["user_id"]
    assert orch.store.sb.select("person_sessions", {"account_id": f"eq.{acc['user_id']}"})
    assert orch.auth.account_for_token(token)["user_id"] == acc["user_id"]
    c = client(orch)
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 200
