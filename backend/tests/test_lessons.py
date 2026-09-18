"""6 buổi học: danh mục, thân bài và việc khoanh vùng theo buổi."""
from fastapi.testclient import TestClient

from app import main


def client(orch):
    main.app.dependency_overrides[main.get_orchestrator] = lambda: orch
    return TestClient(main.app)


def test_catalog_du_6_buoi(orch):
    rows = orch.lessons.catalog()
    assert [r["order"] for r in rows] == [1, 2, 3, 4, 5, 6]
    assert all(r["sections"] for r in rows), "buổi nào cũng phải có mục"
    assert all(r["concepts"] for r in rows), "buổi nào cũng phải có ít nhất một thẻ khái niệm"


def test_moi_buoi_tro_dung_transcript_cua_no(orch):
    for row in orch.lessons.catalog():
        files = orch.cards.lesson_files(row["id"])
        assert len(files) == 1 and files[0].startswith("transcript-")


def test_than_bai_khong_nam_trong_repo(orch):
    """Không có data pack trên máy → chạy chế độ tóm tắt, vẫn có mục để đọc."""
    data = orch.lessons.lesson("day02-constraints")
    assert data["source"] in ("summary", "local", "supabase")
    assert data["sections"], "phải có ít nhất một mục"


def test_api_lessons(orch):
    c = client(orch)
    rows = c.get("/api/lessons").json()["lessons"]
    assert len(rows) == 6
    one = c.get("/api/lessons/day02-eval-data").json()
    assert one["title"] and one["sections"]
    assert c.get("/api/lessons/khong-co-buoi-nay").status_code == 404


def test_hoi_dung_khai_niem_cua_tung_buoi(orch):
    """Hỏi trong buổi nào thì trả lời bằng thẻ của buổi đó (không bắt nhầm thẻ buổi khác)."""
    from app.schemas import ChatRequest
    cases = [
        ("day02-problem-scoping", "Double diamond là gì?", "double_diamond"),
        ("day02-metrics-automation", "North Star Metric là gì?", "north_star"),
        ("day02-constraints", "ODD là gì?", "odd_scope"),
        ("day02-eval-data", "Problem statement gồm những phần nào?", "problem_statement"),
    ]
    for lesson_id, text, concept in cases:
        r = orch.chat(ChatRequest(user_id="demo-trung-binh", session_id="s-" + concept,
                                  lesson_id=lesson_id, text=text))
        assert r.decision.concept == concept, f"{text} → {r.decision.concept}"


def test_the_nhe_sinh_du_mau_tra_loi(orch):
    """Thẻ auto_template phải có đủ khoá mẫu cho cả 5 mức."""
    card = orch.cards.get("tool_calling")
    for key in ("L1_ngan_gon", "L2_ngan_gon", "L3", "L4", "L5"):
        assert card.templates.get(key), f"thiếu mẫu {key}"
    assert all(b.get("src") for b in card.templates["L3"] if b["t"] not in ("outside", "formula"))


def test_hoi_khai_niem_cua_buoi_khac_thi_chi_duong(orch):
    """Hỏi khái niệm thuộc buổi khác: nói rõ nó nằm ở buổi nào, và gợi ý theo ĐÚNG buổi đang mở.

    Lỗi cũ: gợi ý là hằng số cố định từ hồi chỉ có một buổi, nên trợ giảng vừa từ chối
    "Self-attention là gì?" xong lại gợi ý ngay chính câu đó.
    """
    from app.schemas import ChatRequest
    r = orch.chat(ChatRequest(user_id="demo-trung-binh", session_id="s-cross",
                              lesson_id="day01-foundation-a", text="Self-attention là gì?"))
    assert r.kind == "no_source"
    assert "Buổi 2" in r.scope.message          # chỉ đúng buổi có khái niệm đó
    assert "Self-attention là gì?" not in r.scope.suggestions
    assert r.scope.suggestions == ["Context window là gì?", "Temperature là gì?", "Multi-head attention là gì?"]
