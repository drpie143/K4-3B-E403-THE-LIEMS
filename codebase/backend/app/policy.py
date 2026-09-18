"""Luật Conditional (bước ⑥) và quyết định bằng luật (dự phòng + FakeLLM).

`rule_decide` là bản Python của engine.decide trong mock, cộng thêm bộ nhớ dài hạn.
`enforce` ép quyết định của LLM vào các luật cứng — LLM không được vượt qua.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .cards import Card
from .schemas import LEVELS, STYLE_LABEL, Decision, LLMDecision
from .signals import Signals
from .templates import rank, step
from .textutil import cap

STYLE_ORDER = ["vi_du", "ngan_gon", "chi_tiet"]
LEVEL_WORDS = re.compile(r"\bL[1-5]\b|mức\s*[1-5]|làm quen|cơ bản|hiểu bản chất|kỹ thuật|chuyên sâu|nâng cao", re.I)


@dataclass
class Ctx:
    signals: Signals
    card: Card
    memory: dict
    session: dict
    survey: dict | None
    allowed_sources: set[str]
    grounded_ids: list[str]
    threshold: float = 0.6
    terms: dict[str, str] = field(default_factory=dict)  # id khái niệm → tên hiển thị

    @property
    def after_explanation(self) -> bool:
        return self.card.id in self.session.get("answered", {})

    @property
    def last(self) -> dict:
        return self.session.get("last", {}).get(self.card.id, {})


def effective_levels(ctx: Ctx) -> dict[str, str | None]:
    ids = [ctx.card.id] + ctx.card.prerequisites
    out = {cid: (ctx.memory.get("concepts", {}).get(cid) or {}).get("effective_level") for cid in ids}
    if ctx.survey:
        for cid, lv in (ctx.survey.get("levels") or {}).items():
            if cid in out:
                out[cid] = lv
    return out


def confidence(ctx: Ctx) -> float:
    if not ctx.memory.get("memory_on", True):
        return 0.35
    ids = [ctx.card.id] + ctx.card.prerequisites
    known = sum(1 for cid in ids if cid in ctx.memory.get("concepts", {}))
    conf = 0.35 + 0.55 * known / len(ids)
    if ctx.memory.get("stale_any"):
        conf -= 0.2
    return round(max(0.0, conf), 2)


def _choose_style(ctx: Ctx, level: str) -> str:
    worked = [s.split(":", 1)[1] for s in ctx.memory.get("worked", []) if s.startswith("style:")]
    failed = {s.split(":", 1)[1] for s in ctx.memory.get("failed", []) if s.startswith("style:")}
    candidates = []
    if ctx.survey and ctx.survey.get("style"):
        candidates.append(ctx.survey["style"])
    candidates += worked
    if ctx.memory.get("preferred_style"):
        candidates.append(ctx.memory["preferred_style"])
    candidates.append("vi_du" if rank(level) <= 1 else "ngan_gon")
    for s in candidates:
        if s not in failed or (ctx.survey and s == ctx.survey.get("style")):
            return s
    return next((s for s in STYLE_ORDER if s not in failed), candidates[0])


def _choose_analogy(ctx: Ctx) -> tuple[str | None, bool]:
    ids = ctx.card.analogy_ids
    worked = [s.split(":", 1)[1] for s in ctx.memory.get("worked", []) if s.startswith("analogy:")]
    failed = {s.split(":", 1)[1] for s in ctx.memory.get("failed", []) if s.startswith("analogy:")}
    for a in worked:
        if a in ids:
            return a, True
    ok = [a for a in ids if a not in failed]
    if failed and ok:
        return ok[0], False
    return None, False


def rule_decide(ctx: Ctx) -> Decision:
    card, sig = ctx.card, ctx.signals
    eff = effective_levels(ctx)
    conf = confidence(ctx)
    survey = ctx.survey
    missing = next((p for p in card.prerequisites if eff.get(p) == "chua"), None)
    base_solid = all(eff.get(p) == "hieu_ro" for p in card.prerequisites)
    c_lv = eff.get(card.id)
    if survey and survey.get("skipped"):
        level = "L2"
    elif missing:
        level = "L1"
    elif c_lv == "chua":
        level = "L2"
    elif c_lv == "hieu_ro":
        level = "L5" if base_solid else "L4"
    elif c_lv == "biet_so":
        level = "L4" if base_solid else "L3"
    else:
        level = "L3"

    need_survey = False
    reason = ""
    stepped_down = False
    if not survey and (sig.confused or sig.reask):
        if ctx.after_explanation:
            need_survey = True
            reason = (f"Bạn hỏi lại về {card.term}, nên mình hỏi nhanh để đổi cách giải thích." if sig.reask
                      else "Lời giải thích trước chưa hợp với bạn, nên mình hỏi nhanh để giải thích đúng chỗ.")
        elif conf < ctx.threshold:
            need_survey = True
            reason = f"Mình chưa biết bạn đã quen với {card.term} đến đâu."
        else:
            level = step(level, -1)
            stepped_down = True

    style = _choose_style(ctx, level)
    analogy, from_memory = _choose_analogy(ctx)

    if not need_survey:
        bits = []
        miss_name = ""
        if missing:
            miss_name = ctx.terms.get(missing, missing)
        if survey:
            if survey.get("skipped"):
                bits.append("bạn bỏ qua khảo sát nên mình giải thích ngắn gọn, dễ hiểu trước")
            else:
                if missing:
                    bits.append(f"bạn chọn “{miss_name}: Chưa” nên mình nói phần này trước")
                bits.append(f"mình giải thích theo kiểu “{STYLE_LABEL[style]}” như bạn chọn")
        elif ctx.memory.get("concepts"):
            if missing:
                bits.append(f"Sổ tay ghi bạn chưa rõ {miss_name} nên mình nói phần này trước")
            elif rank(level) >= 3:
                bits.append("Sổ tay ghi bạn đã nắm phần nền nên mình đi thẳng vào chi tiết kỹ thuật")
            if ctx.memory.get("stale_any"):
                bits.append("đã lâu bạn chưa ôn phần này nên mình giải thích từ nền hơn một chút")
            if stepped_down:
                bits.append("bạn nói chưa hiểu nên mình giải thích đơn giản hơn")
        if from_memory and analogy:
            title = next((a["title"] for a in card.approved_analogies if a["id"] == analogy), analogy)
            bits.append(f"lần trước ví dụ “{title}” giúp bạn hiểu, nên mình dùng lại")
        reason = ". ".join(cap(b) for b in bits) + ("." if bits else "")

    src = [s for s in ctx.grounded_ids if s in card.source_ids] or [s for c in card.core_claims for s in c["src"]]
    return Decision(
        kind="survey" if need_survey else "explain",
        concept=card.id,
        gap_type="thieu_nen" if missing else ("khong_ro" if sig.vague else "can_vi_du" if style == "vi_du" else "qua_dai"),
        level=level,
        style=style,
        missing_concepts=[missing] if missing else [],
        prereq_first=missing,
        preferred_analogy=analogy,
        confidence=0.9 if survey else conf,
        need_survey=need_survey,
        source_ids=list(dict.fromkeys(src)),
        reason_for_user=reason,
        weighted_sum=sig.weighted_sum,
        full=bool(survey) or sig.confused or ctx.after_explanation,
        decided_by="rules",
    )


def to_llm(d: Decision) -> LLMDecision:
    return LLMDecision(
        concept=d.concept or "", gap_type=d.gap_type, level=d.level, style=d.style,
        missing_concepts=d.missing_concepts, preferred_analogy=d.preferred_analogy,
        misconception_suspected=d.misconception_suspected, confidence=d.confidence,
        need_survey=d.need_survey, in_scope=d.in_scope, source_ids=d.source_ids,
        reason_for_user=d.reason_for_user,
    )


def enforce(llm: LLMDecision, rules: Decision, ctx: Ctx) -> Decision:
    """Ép quyết định của LLM vào luật cứng. Trả về quyết định cuối cùng."""
    card = ctx.card
    d = rules.model_copy(deep=True)
    d.decided_by = "llm+policy"
    if not llm.in_scope:
        d.kind, d.in_scope = "out_of_scope", False
        return d

    # Khảo sát: luật bắt buộc thì giữ; LLM được đề xuất thêm khi chưa khảo sát.
    need_survey = rules.need_survey or (llm.need_survey and not ctx.survey and llm.confidence < ctx.threshold)
    if need_survey:
        d.kind, d.need_survey = "survey", True
        d.reason_for_user = rules.reason_for_user or f"Mình chưa biết bạn đã quen với {card.term} đến đâu."
        d.confidence = min(rules.confidence, max(0.0, min(1.0, llm.confidence)))
        return d

    d.kind, d.need_survey = "explain", False
    d.gap_type = llm.gap_type
    d.level = llm.level if llm.level in LEVELS else rules.level
    d.style = llm.style
    d.confidence = max(0.0, min(1.0, llm.confidence))
    d.misconception_suspected = llm.misconception_suspected if llm.misconception_suspected in {m["id"] for m in card.misconceptions} else None

    # Khái niệm nền "Chưa" theo hồ sơ/khảo sát → bắt buộc mức 1 và nói phần nền trước.
    llm_missing = [m for m in llm.missing_concepts if m in card.prerequisites]
    if rules.prereq_first:
        d.level, d.prereq_first = "L1", rules.prereq_first
        d.missing_concepts = list(dict.fromkeys([rules.prereq_first] + llm_missing))
    else:
        d.missing_concepts = llm_missing
        d.prereq_first = llm_missing[0] if llm_missing else None
        if d.prereq_first:
            d.level = LEVELS[min(rank(d.level), 1)]

    # Bỏ khảo sát → không cao hơn mức 2.
    if ctx.survey and ctx.survey.get("skipped"):
        d.level = LEVELS[min(rank(d.level), 1)]

    # Vừa giải thích mà vẫn chưa hiểu → thấp hơn lần trước ít nhất 1 bậc và đổi kiểu.
    last = ctx.last
    if ctx.signals.confused and last.get("level"):
        cap_level = step(last["level"], -1)
        if rank(d.level) > rank(cap_level):
            d.level = cap_level
        if d.style == last.get("style"):
            d.style = next(s for s in STYLE_ORDER if s != last.get("style"))

    # Tránh cách đã thất bại (nếu còn lựa chọn khác).
    failed_styles = {s.split(":", 1)[1] for s in ctx.memory.get("failed", []) if s.startswith("style:")}
    if d.style in failed_styles and not (ctx.survey and ctx.survey.get("style") == d.style):
        d.style = next((s for s in STYLE_ORDER if s not in failed_styles), d.style)
    failed_analogies = {s.split(":", 1)[1] for s in ctx.memory.get("failed", []) if s.startswith("analogy:")}
    if llm.preferred_analogy in card.analogy_ids and llm.preferred_analogy not in failed_analogies:
        d.preferred_analogy = llm.preferred_analogy
    else:
        d.preferred_analogy = rules.preferred_analogy

    # Nguồn: chỉ lấy trong tập được phép.
    src = [s for s in llm.source_ids if s in ctx.allowed_sources]
    d.source_ids = src or rules.source_ids

    # Lý do: một câu, không lộ tên mức.
    reason = (llm.reason_for_user or "").strip()
    d.reason_for_user = rules.reason_for_user if (not reason or LEVEL_WORDS.search(reason) or len(reason) > 220) else reason
    return d
