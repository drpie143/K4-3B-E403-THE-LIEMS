"""Validator độ bám bài giảng (port checkFidelity của mock) + gộp kết quả LLM chấm."""
from __future__ import annotations

from .cards import Card
from .guard import ability_labels
from .schemas import Block, FidelityReport, LLMJudge
from .textutil import norm, strip_tags

# Trần số từ theo mức (không tính bảng, phần nền "prereq" và phần "outside").
# Đây là TRẦN chống lan man, không phải mục tiêu: prompt explain.md đặt khoảng mong muốn thấp hơn.
# Nới rộng ở v5 vì bản v4 ép quá chặt, câu trả lời cụt — học viên phải hỏi lại mới đủ ý.
WORD_LIMIT = {"L1": 190, "L2": 280, "L3": 320, "L4": 380, "L5": 520}
# Khoảng mong muốn cho mỗi mức — ghép vào prompt explain để mô hình có con số cụ thể,
# thay vì tự chọn độ dài rồi viết cụt.
WORD_TARGET = {"L1": (110, 160), "L2": (160, 240), "L3": (190, 280), "L4": (230, 330), "L5": (300, 460)}
NOT_COUNTED = {"map", "prereq", "outside", "formula"}
EXEMPT_SOURCE = {"outside", "formula"}


# Cụm phủ định: "không đọc lần lượt từng từ" là câu ĐÚNG, không phải hiểu lệch.
NEGATIONS = ("khong", "ko", "chang", "chua", "thay vi", "chu khong", "khac voi", "dung nghi",
             "hieu lam", "sai lam", "nham", "khong phai la")
NEG_WINDOW = 60


def mentions_misconception(normalized: str, pattern: str) -> bool:
    """True khi câu nhắc tới hiểu lệch mà KHÔNG phủ định nó."""
    start = normalized.find(pattern)
    while start != -1:
        before = normalized[max(0, start - NEG_WINDOW):start]
        if not any(neg in before for neg in NEGATIONS):
            return True
        start = normalized.find(pattern, start + 1)
    return False


def plain_text(blocks: list[Block], include_tables: bool = True) -> str:
    parts = []
    for b in blocks:
        parts += [b.title or "", strip_tags(b.html or "")]
        parts += [strip_tags(x) for x in (b.items or [])]
        if include_tables:
            parts += [strip_tags(c) for row in (b.rows or []) for c in row]
    return " ".join(p for p in parts if p)


def rule_check(card: Card, blocks: list[Block], allowed_sources: set[str], level: str | None = None,
               require_all_claims: bool = True) -> FidelityReport:
    text = plain_text(blocks)
    n = norm(text)
    covered = {c for b in blocks for c in b.claims}
    total = card.claim_ids
    rep = FidelityReport(
        covered=len([c for c in total if c in covered]),
        total=len(total),
        missing_claims=[c for c in total if c not in covered],
        missing_terms=[t for t in card.required_terms if norm(t) not in n],
        misconceptions=[m["id"] for m in card.misconceptions if mentions_misconception(n, m["pattern"])],
        unlabeled=sum(1 for b in blocks if b.t not in EXEMPT_SOURCE and not b.src),
        outside=sum(1 for b in blocks if b.t == "outside"),
        bad_sources=sorted({s for b in blocks for s in b.src if s not in allowed_sources}),
        ability_labels=ability_labels(text),
    )
    if level:
        words = len(plain_text([b for b in blocks if b.t not in NOT_COUNTED], include_tables=False).split())
        rep.too_long = words > WORD_LIMIT.get(level, 300)
    claims_ok = not rep.missing_claims if require_all_claims else rep.covered >= 1
    rep.ok = claims_ok and not (rep.missing_terms or rep.misconceptions or rep.unlabeled
                                or rep.bad_sources or rep.ability_labels or rep.too_long)
    return rep


def merge_judge(rep: FidelityReport, judge: LLMJudge, card: Card, require_all_claims: bool = True) -> FidelityReport:
    rep = rep.model_copy(deep=True)
    valid = set(card.claim_ids)
    judged_missing = [c.id for c in judge.claims if not c.ok and c.id in valid]
    rep.missing_claims = sorted(set(rep.missing_claims) | set(judged_missing))
    rep.covered = rep.total - len(rep.missing_claims)
    known = {m["id"] for m in card.misconceptions}
    rep.misconceptions = sorted(set(rep.misconceptions) | {h for h in judge.misconception_hits if h in known})
    rep.unsupported = judge.unsupported_sentences[:5]
    rep.judge_verdict = judge.verdict
    claims_ok = not judged_missing if require_all_claims else (rep.total - len(rep.missing_claims)) >= 1
    rep.ok = rep.ok and judge.verdict == "pass" and claims_ok and not rep.misconceptions and not rep.unsupported
    return rep


def fake_judge(rep: FidelityReport, card: Card) -> LLMJudge:
    """Phán quyết giả lập cho FakeLLM: khớp với kiểm tra luật."""
    return LLMJudge(
        claims=[{"id": c, "ok": c not in rep.missing_claims, "evidence": ""} for c in card.claim_ids],
        misconception_hits=rep.misconceptions,
        unsupported_sentences=[],
        verdict="pass" if rep.ok else "fail",
    )
