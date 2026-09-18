from app.schemas import AdjustRequest, ChatRequest


def test_easier_and_deeper_walk_the_5_levels(orch):
    r = orch.chat(ChatRequest(user_id="demo-moi", session_id="s", text="bước 2 chưa hiểu, cộng trọng số vào đâu"))
    assert r.decision.level == "L1"
    levels = []
    for _ in range(5):
        r = orch.adjust(AdjustRequest(user_id="demo-moi", session_id="s", concept="self_attention", kind="deeper"))
        levels.append(r.decision.level)
        assert r.fidelity.ok, r.fidelity.errors()
    assert levels == ["L2", "L3", "L4", "L5", "L5"]
    r = orch.adjust(AdjustRequest(user_id="demo-moi", session_id="s", concept="self_attention", kind="easier"))
    assert r.decision.level == "L4"


def test_example_switches_analogy_and_records_failed(orch):
    orch.chat(ChatRequest(user_id="demo-moi", session_id="s", text="self-attention mình chưa hiểu"))
    r = orch.adjust(AdjustRequest(user_id="demo-moi", session_id="s", concept="self_attention", kind="example"))
    assert r.answer.analogy_id == "thu_vien"  # lần đầu là con_meo (mặc định mức 1)
    rows = orch.store._strategy_rows("demo-moi", "self_attention")
    assert any(x["strategy"] == "analogy:con_meo" and x["failed"] == 1 for x in rows)


def test_shorter_from_technical(orch):
    orch.chat(ChatRequest(user_id="demo-vung", session_id="s", text="Q, K, V khác nhau thế nào"))
    r = orch.adjust(AdjustRequest(user_id="demo-vung", session_id="s", concept="self_attention", kind="shorter"))
    assert r.answer.key == "L3_first"
    assert orch.store.settings("demo-vung")["preferred_style"] == "ngan_gon"
