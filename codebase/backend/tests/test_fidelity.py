from app.fidelity import merge_judge, rule_check
from app.orchestrator import clean_html
from app.schemas import Block, Decision, LLMJudge
from app.templates import build_answer


def test_all_templates_pass_validator(orch):
    allowed = set(orch.cards.sources)
    for cid, card in orch.cards.cards.items():
        for key in card.templates:
            level = key[:2] if key.startswith("L") else "L3"
            analogy = key.split("_vi_du_")[1] if "_vi_du_" in key else None
            for pre in ([None, "vector"] if cid == "self_attention" else [None]):
                for ws in (False, True):
                    d = Decision(kind="explain", concept=cid, level=level, style="vi_du" if analogy else "ngan_gon",
                                 full=key != "L3_first", prereq_first=pre, weighted_sum=ws, preferred_analogy=analogy)
                    a = build_answer(orch.cards, d)
                    assert a.key == key
                    rep = rule_check(card, a.blocks, allowed, level)
                    assert rep.ok, (cid, key, pre, ws, rep.errors())


def test_validator_catches_problems(orch):
    card = orch.cards.get("self_attention")
    bad = [Block(t="p", html="Self-attention chỉ nhìn một từ quan trọng nhất, bạn yếu phần này.", src=[], claims=["C1"])]
    rep = rule_check(card, bad, {"T06-130"}, "L3")
    assert not rep.ok
    assert rep.misconceptions == ["M1"]
    assert "C2" in rep.missing_claims and "Query" in rep.missing_terms
    assert rep.unlabeled == 1 and rep.ability_labels
    rep2 = rule_check(card, [Block(t="p", html="x", src=["T99-999"], claims=[])], {"T06-130"})
    assert rep2.bad_sources == ["T99-999"]


def test_judge_can_fail_a_rule_pass(orch):
    card = orch.cards.get("self_attention")
    a = build_answer(orch.cards, Decision(kind="explain", concept="self_attention", level="L3", full=True))
    rep = rule_check(card, a.blocks, set(orch.cards.sources), "L3")
    assert rep.ok
    judge = LLMJudge(claims=[{"id": "C1", "ok": True, "evidence": ""}, {"id": "C2", "ok": False, "evidence": ""},
                             {"id": "C3", "ok": True, "evidence": ""}],
                     misconception_hits=["M9"], unsupported_sentences=[], verdict="fail")
    merged = merge_judge(rep, judge, card)
    assert not merged.ok and merged.missing_claims == ["C2"] and merged.misconceptions == []


def test_clean_html_keeps_only_safe_tags():
    out = clean_html('<b>Key</b> <script>alert(1)</script><i onclick="x">y</i><sub>k</sub>')
    assert "<b>Key</b>" in out and "<sub>k</sub>" in out
    assert "<script>" not in out and "&lt;i onclick" in out


def test_negated_misconception_is_not_a_hit(orch):
    card = orch.cards.get("self_attention")
    good = [Block(t="p", html="Mô hình <b>không</b> đọc lần lượt từng từ; mọi <b>token</b> nhìn nhau cùng lúc qua <b>Query</b>, <b>Key</b>, <b>Value</b> và <b>trọng số</b>.",
                  src=["T06-127"], claims=["C1", "C2", "C3"])]
    assert rule_check(card, good, {"T06-127"}, "L3").misconceptions == []
    bad = [Block(t="p", html="Mô hình đọc lần lượt từng từ.", src=["T06-127"], claims=[])]
    assert rule_check(card, bad, {"T06-127"}, "L3").misconceptions == ["M2"]
