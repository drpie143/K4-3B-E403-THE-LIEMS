"""Bộ điều phối — luồng cố định ở §3 tài liệu backend.

AI chỉ làm 3 việc (diagnose / explain / judge); mọi hành động có hậu quả do code làm.
"""
from __future__ import annotations

import html
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from . import checks, handoff
from .cache import AnswerCache
from .cards import Card, CardStore
from .config import Settings
from .fidelity import fake_judge, merge_judge, plain_text, rule_check
from .textutil import norm, strip_tags
from .guard import check_input
from .llm import LLMClient, LLMError, Usage, make_client
from .policy import STYLE_ORDER, Ctx, enforce, rule_decide, to_llm
from .profile_store import ProfileStore, utcnow
from .prompts import Prompts
from .retrieval import Passage, Retriever
from .schemas import (
    STYLE_LABEL, UNDERSTANDING_LABEL, AdjustRequest, Answer, Block, ChatRequest, ChatResponse, CheckAnswerRequest,
    CheckResult, Decision, FeedbackRequest, FeedbackResult, FidelityReport, HandoffRequest,
    LLMAnswer, LLMBaselineAnswer, LLMBlock, LLMDecision, LLMJudge, Meta, Notice, ScopePayload,
    SurveyPayload, SurveyRequest, SurveyRow,
)
from .signals import SignalDetector, Signals
from .templates import build_answer, rank, step

QUESTION_HINT = re.compile(r"\?|la gi|la sao|nhu the nao|tai sao|vi sao|khac gi|giai thich|hoat dong")
ALLOWED_TAGS = re.compile(r"&lt;(/?)(b|i|sub|sup)&gt;")
SUGGESTIONS = ["Self-attention là gì?", "Q, K, V khác nhau thế nào?"]


@dataclass
class Turn:
    request_id: str = field(default_factory=lambda: "r-" + uuid.uuid4().hex[:8])
    t0: float = field(default_factory=time.perf_counter)
    usages: list[Usage] = field(default_factory=list)
    fallback: str | None = None
    cached: bool = False
    notices: list[Notice] = field(default_factory=list)
    rejected: list[dict] = field(default_factory=list)  # vì sao bản LLM bị validator loại


def clean_html(text: str | None) -> str | None:
    if text is None:
        return None
    return ALLOWED_TAGS.sub(lambda m: f"<{m.group(1)}{m.group(2)}>", html.escape(text, quote=False))


class Orchestrator:
    def __init__(self, settings: Settings, llm: LLMClient | None = None, db_path=None):
        self.s = settings
        self.cards = CardStore(settings.cards_dir)
        self.retriever = Retriever(
            self.cards,
            settings.chunks_path,
            upstash_url=settings.upstash_vector_url,
            upstash_token=settings.upstash_vector_token,
        )
        self.detector = SignalDetector(self.cards, settings.reask_seconds)
        self.store = ProfileStore(settings, self.cards, db_path)
        self.prompts = Prompts(settings.prompts_dir)
        self.llm = llm or make_client(settings)
        self.cache = AnswerCache(settings.cache_dir)
        from .tracing import Tracer
        self.tracer = Tracer(settings.trace_dir, settings.trace_text, settings.trace_prompts)
        self.terms = {cid: c.term for cid, c in self.cards.cards.items()}

    # ================================================================ helpers
    @property
    def provider(self) -> str:
        return getattr(self.llm, "provider", "unknown")

    def lesson_title(self, lesson_id: str) -> str:
        return self.cards.lessons.get(lesson_id, {}).get("title", lesson_id)

    def page_concept(self, lesson_id: str) -> str | None:
        concepts = self.cards.lessons.get(lesson_id, {}).get("concepts", [])
        return concepts[0] if concepts else None

    def _meta(self, turn: Turn) -> Meta:
        return Meta(
            request_id=turn.request_id, prompt_version=self.prompts.version, provider=self.provider,
            latency_ms=int((time.perf_counter() - turn.t0) * 1000), fallback=turn.fallback, cached=turn.cached,
            llm_calls=len(turn.usages),
            input_tokens=sum(u.input_tokens for u in turn.usages),
            output_tokens=sum(u.output_tokens for u in turn.usages),
        )

    def _trace(self, turn: Turn, route: str, req, resp: ChatResponse | None = None, extra: dict | None = None) -> None:
        rec = {
            "request_id": turn.request_id, "route": route, "user_id": getattr(req, "user_id", None),
            "session_id": getattr(req, "session_id", None), "prompt_version": self.prompts.version,
            "provider": self.provider, "fallback": turn.fallback, "cached": turn.cached,
            "llm": [u.as_dict() for u in turn.usages],
            "rejected": turn.rejected,
            "latency_ms": int((time.perf_counter() - turn.t0) * 1000),
        }
        if isinstance(req, ChatRequest):
            rec.update(self.tracer.text_fields(req.text))
        if resp is not None:
            rec["kind"] = resp.kind
            rec["decision"] = resp.decision.model_dump() if resp.decision else None
            rec["fidelity"] = resp.fidelity.model_dump() if resp.fidelity else None
            rec["answer_key"] = resp.answer.key if resp.answer else None
        if extra:
            rec.update(extra)
        try:
            self.tracer.write(rec)
        except OSError:
            pass

    def _call(self, turn: Turn, task: str, user: str, schema, model: str, fallback=None, system: str | None = None):
        sys_prompt = system or self.prompts.system
        try:
            obj, usage = self.llm.complete_json(task, sys_prompt, user, schema, model, fallback=fallback)
        except LLMError as exc:
            turn.usages.append(Usage(task=task, model=model, error=str(exc)[:300]))
            self.tracer.prompt(turn.request_id, task, model, sys_prompt, user, None, str(exc))
            raise
        turn.usages.append(usage)
        self.tracer.prompt(turn.request_id, task, model, sys_prompt, user, obj.model_dump(), None)
        return obj

    def _passages(self, hits: list[Passage], grounded: list[str]) -> list[dict]:
        order = sorted(hits, key=lambda p: (p.id not in grounded, -p.score))[: self.s.passages_for_llm]
        return [{"id": p.id, "section": p.section, "text": self.retriever.text_for(p.id, self.s.passage_max_chars)} for p in order]

    def _passages_for(self, ids: list[str], hits: list[Passage], grounded: list[str], limit: int = 6) -> list[dict]:
        """Đoạn nguồn cho bước chấm: mọi đoạn mà câu trả lời trích dẫn + các đoạn tìm được."""
        order = list(dict.fromkeys(ids + [p.id for p in sorted(hits, key=lambda p: (p.id not in grounded, -p.score))]))
        return [{"id": i, "section": (self.retriever.get(i).section if self.retriever.get(i) else self.cards.sources.get(i, {}).get("section", "")),
                 "text": self.retriever.text_for(i, self.s.passage_max_chars)} for i in order[:limit]]

    def _grounding(self, card: Card, text: str, selection: str, lesson_id: str) -> tuple[list[Passage], list[str], set[str]]:
        query = " ".join([text, selection, card.term, *card.required_terms])
        hits = self.retriever.search(query, lesson_id, self.s.retrieval_top_k, boost_ids=card.source_ids)
        grounded = [h.id for h in hits if h.score >= self.s.retrieval_min_score and h.id in card.source_ids]
        allowed = {h.id for h in hits} | set(self.cards.sources)
        return hits, grounded, allowed

    def _ctx(self, req, card: Card, sess: dict, sig: Signals, survey: dict | None, now: datetime,
             hits_info=None) -> tuple[Ctx, list[Passage]]:
        hits, grounded, allowed = hits_info or self._grounding(card, sess.get("last_question", ""), "", req.lesson_id)
        memory = self.store.learner_memory(req.user_id, card.id, now)
        ctx = Ctx(signals=sig, card=card, memory=memory, session=sess, survey=survey,
                  allowed_sources=allowed, grounded_ids=grounded,
                  threshold=self.s.confidence_survey_threshold, terms=self.terms)
        return ctx, hits

    def _synthetic_signals(self, concept: str, text: str, confused: bool = False) -> Signals:
        """Tín hiệu dựng lại cho các thao tác không phải câu hỏi mới (điều chỉnh, kiểm tra, sau khảo sát)."""
        ask_type = self.detector.detect(text, "", {}, concept).ask_type if text else "khac"
        return Signals(text=text, concept=concept, concept_from_page=False, confused=confused,
                       reask=False, weighted_sum=False, vague=False, ask_type=ask_type)

    def _record_strategy(self, user_id: str, concept: str, sess: dict, outcome: str, parts=("style", "analogy")) -> None:
        last = sess.get("last", {}).get(concept)
        if not last:
            return
        strategies = []
        if "style" in parts and last.get("style"):
            strategies.append(f"style:{last['style']}")
        if "analogy" in parts and last.get("analogy_id"):
            strategies.append(f"analogy:{last['analogy_id']}")
        self.store.record_strategy(user_id, concept, strategies, outcome)

    def _add_notice(self, turn: Turn, notice: Notice | None) -> None:
        if notice:
            turn.notices.append(notice)

    # ================================================================ responses
    def _scope(self, turn: Turn, kind: str, text: str, term: str | None = None, nearest: list[str] | None = None,
               decision: Decision | None = None, in_lesson: bool = False) -> ChatResponse:
        if kind == "injection":
            msg = ("Tin nhắn có yêu cầu thay đổi hướng dẫn của trợ giảng — mình coi đó là nội dung và không làm theo. "
                   "Mình chỉ giúp giải thích nội dung bài đang học (Self-attention, Day 1).")
        elif kind == "out_of_scope":
            if re.search(r"blog|lam ho|giai ho|nop bai", _norm(text)):
                msg = "Mình chỉ giúp giải thích nội dung bài đang học. Viết bài blog hay làm bài thay bạn nằm ngoài phạm vi này."
            else:
                msg = "Mình chỉ giúp giải thích nội dung bài đang học. Câu hỏi về điểm danh, deadline hay XP bạn xem thông báo chính thức hoặc hỏi TA nhé."
        elif kind == "no_source" and in_lesson:
            name = term or "Phần này"
            msg = (f"{name} có được nhắc trong bài giảng nhưng chưa nằm trong phần mình được duyệt để giải thích, "
                   "nên mình không tự giải thích để tránh sai. Bạn xem đoạn gốc bên dưới hoặc hỏi TA nhé.")
        elif kind == "no_source":
            name = term or "Khái niệm này"
            msg = f"{name} chưa có trong bài giảng buổi này, nên mình không giải thích để tránh đoán sai."
        else:
            msg = ("Mình là trợ giảng cho bài Self-attention. Bạn có thể bôi đen một đoạn trong bài rồi hỏi, "
                   "hoặc hỏi thẳng một khái niệm trong bài.")
        d = decision or Decision(kind=kind, in_scope=kind in ("no_source", "help"), confidence=0.9)
        return ChatResponse(kind=kind, decision=d, scope=ScopePayload(message=msg, term=term, nearest=nearest or [], suggestions=SUGGESTIONS),
                            notices=turn.notices, meta=self._meta(turn))

    def _survey_payload(self, card: Card, user_id: str, reason: str) -> SurveyPayload:
        prof = self.store.profile(user_id)
        on = prof["memory_on"]
        rows = []
        for cid in card.prerequisites[:3]:
            pc = self.cards.get(cid)
            lvl = prof["concepts"].get(cid, {}).get("level") if on else None
            rows.append(SurveyRow(concept=cid, term=pc.term, vi_name=pc.vi_name, level=lvl))
        return SurveyPayload(concept=card.id, term=card.term, rows=rows,
                             style=prof["preferred_style"] if on else None, reason=reason)

    # ================================================================ AI steps
    def _diagnose(self, turn: Turn, ctx: Ctx, rules: Decision, text: str, selection: str, hits: list[Passage]) -> Decision:
        if self.s.replay:
            turn.fallback = turn.fallback or "replay:rules"
            return rules
        user = self.prompts.render(
            "diagnose",
            card=ctx.card.for_prompt(),
            passages=self._passages(hits, ctx.grounded_ids),
            memory={k: v for k, v in ctx.memory.items() if k != "memory_on"} if ctx.memory.get("memory_on") else "(học viên tắt ghi nhớ)",
            survey=ctx.survey or "(chưa khảo sát)",
            session={
                "đã giải thích khái niệm này trong phiên": ctx.after_explanation,
                "lần trước": {k: ctx.last.get(k) for k in ("level", "style", "analogy_id")} if ctx.last else None,
                "số lần 👎": ctx.session.get("thumbs_down", {}).get(ctx.card.id, 0),
                "học viên nói chưa hiểu": ctx.signals.confused,
                "hỏi lại trong 3 phút": ctx.signals.reask,
            },
            rule_suggestion={k: getattr(rules, k) for k in ("level", "style", "missing_concepts", "need_survey", "confidence", "preferred_analogy")},
            selection=selection or "(không có)",
            text=text,
            concept=ctx.card.id,
        )
        try:
            llm_dec = self._call(turn, "diagnose", user, LLMDecision, self.s.llm_model, fallback=to_llm(rules))
        except LLMError:
            turn.fallback = "rules:llm_error"
            return rules
        return enforce(llm_dec, rules, ctx)

    def _to_answer(self, llm: LLMAnswer, d: Decision, card: Card, template: Answer | None = None) -> Answer:
        blocks = []
        for b in llm.blocks[:8]:
            rows = [[clean_html(c) or "" for c in r[:2]] for r in (b.rows or []) if len(r) >= 2] or None
            blocks.append(Block(
                t=b.t, title=clean_html(b.title), html=clean_html(b.html), rows=rows,
                items=[clean_html(x) or "" for x in (b.items or [])] or None,
                src=list(dict.fromkeys(b.src)), claims=[c for c in b.claims if c in card.claim_ids],
            ))
        # Sửa nhẹ: block thiếu src → lấy theo mẫu đã duyệt (cùng nội dung) hoặc theo nguồn của quyết định.
        by_text = {norm(plain_text([b])): b.src for b in (template.blocks if template else []) if b.src}
        for b in blocks:
            if b.src or b.t in ("outside", "formula"):
                continue
            same = by_text.get(norm(plain_text([b])))
            if same:
                b.src = list(same)
            elif b.t == "map":  # bảng nối ví dụ ↔ thuật ngữ lấy nguồn của chính khái niệm
                b.src = list(d.source_ids[:2])

        # Sửa nhẹ: thiếu phần nền bắt buộc thì chèn primer đã duyệt.
        if d.prereq_first and not any(b.t == "prereq" for b in blocks):
            pre = self.cards.get(d.prereq_first)
            if pre and pre.primer:
                blocks.insert(0, Block(t="prereq", title=f"Trước hết: {pre.term}", html=pre.primer["html"], src=pre.primer.get("src", [])))
        analogy = llm.analogy_id if llm.analogy_id in card.analogy_ids else None
        return Answer(key="llm", blocks=blocks, analogy_id=analogy, summary_for_next_turn=llm.summary_for_next_turn[:200])

    @staticmethod
    def _approved_texts(card: Card, template: Answer, prereq: Card | None) -> set[str]:
        """Nội dung đã có người duyệt (mẫu, ví dụ, giới hạn ví dụ, phần nền) — LLM chấm không cần soi lại."""
        texts = {norm(plain_text([b])) for b in template.blocks}
        texts |= {norm(a["text"]) for a in card.approved_analogies}
        texts |= {norm(x) for x in card.analogy_limits}
        for c in (card, prereq):
            if c and c.primer.get("html"):
                texts |= {norm(strip_tags(c.primer["html"]))}
        return {t for t in texts if t}

    @staticmethod
    def _answer_text_for_judge(blocks: list[Block], approved: set[str]) -> str:
        lines = []
        for b in blocks:
            body = plain_text([b])
            if b.t == "outside":
                tag = "[NGOÀI BÀI]"
            elif b.t in ("analogy", "map", "limit", "prereq"):
                tag = f"[ngữ cảnh · {b.t}]"
            elif norm(body) in approved:
                tag = f"[đã duyệt · {b.t}]"
            else:
                tag = f"[tự viết · {b.t}]"
            lines.append(f"{tag} {body}")
        return "\n".join(lines)

    def _explain(self, turn: Turn, ctx: Ctx, d: Decision, text: str, selection: str, hits: list[Passage],
                 note: str = "") -> tuple[Answer, FidelityReport]:
        card = ctx.card
        # Hỏi "là gì / hoạt động thế nào" → phải phủ đủ ý chính. Hỏi khía cạnh khác (ứng dụng, ví dụ,
        # so sánh) → chỉ cần bám ít nhất một ý chính, phần còn lại trả lời đúng câu hỏi.
        need_all = d.ask_type in ("khai_niem", "co_che", "khac")
        template = build_answer(self.cards, d)
        allowed = ctx.allowed_sources
        cache_key = AnswerCache.key(
            concept=card.id, ask=d.ask_type, level=d.level, style=d.style, prereq=d.prereq_first, analogy=d.preferred_analogy,
            alt=d.alt_example, full=d.full, ws=d.weighted_sum, prompt=self.prompts.version,
            model=self.s.model_explain, provider=self.provider,
        )
        if not note and self.provider != "fake":
            hit = self.cache.get(cache_key)
            if hit:
                turn.cached = True
                return hit
        if self.s.replay:
            turn.fallback = turn.fallback or "replay:template"
            return template, rule_check(card, template.blocks, allowed | {s for b in template.blocks for s in b.src}, d.level, need_all)

        mem = ctx.memory
        pre = self.cards.get(d.prereq_first) if d.prereq_first else None
        fix = ""
        for attempt in range(2):
            user = self.prompts.render(
                "explain",
                decision={k: v for k, v in d.model_dump().items() if k not in ("kind", "decided_by", "need_survey", "in_scope")},
                ask_type=d.ask_type,
                card=card.for_prompt(),
                primer=pre.primer if pre else "(không cần)",
                passages=self._passages(hits, ctx.grounded_ids),
                reference=[b.model_dump(exclude_none=True) for b in template.blocks],
                previous=ctx.last.get("summary") or "(không có)",
                worked=", ".join(mem.get("worked", [])) or "—",
                failed=", ".join(mem.get("failed", [])) or "—",
                note=note or "(không có)",
                selection=selection or "(không có)",
                text=text,
                fix_instructions=fix,
            )
            fallback = LLMAnswer(
                blocks=[LLMBlock(t=b.t, title=b.title, html=b.html, rows=b.rows, items=b.items, src=b.src, claims=b.claims) for b in template.blocks],
                analogy_id=template.analogy_id, summary_for_next_turn=template.summary_for_next_turn,
            )
            try:
                llm_ans = self._call(turn, "explain", user, LLMAnswer, self.s.model_explain, fallback=fallback)
            except LLMError:
                turn.fallback = "template:llm_error"
                break
            ans = self._to_answer(llm_ans, d, card, template)
            if self.provider == "fake":
                ans.key = template.key
            rep = rule_check(card, ans.blocks, allowed, d.level, need_all)
            if rep.ok and self.s.use_judge:
                cited = [i for b in ans.blocks for i in b.src]
                judge_user = self.prompts.render(
                    "judge",
                    claims=card.core_claims,
                    misconceptions=[{"id": m["id"], "text": m["text"]} for m in card.misconceptions],
                    passages=self._passages_for(cited, hits, ctx.grounded_ids),
                    answer=self._answer_text_for_judge(ans.blocks, self._approved_texts(card, template, pre)),
                )
                try:
                    judge = self._call(turn, "judge", judge_user, LLMJudge, self.s.model_judge, fallback=fake_judge(rep, card))
                    rep = merge_judge(rep, judge, card, need_all)
                except LLMError:
                    rep.judge_verdict = "error"
            if rep.ok:
                if not note and self.provider != "fake":
                    self.cache.put(cache_key, ans, rep)
                return ans, rep
            turn.rejected.append({"attempt": attempt + 1, "errors": rep.errors(),
                                  "blocks": [{"t": b.t, "src": b.src, "claims": b.claims} for b in ans.blocks],
                                  "text": plain_text(ans.blocks)[:1500]})
            fix = "- LẦN TRƯỚC BỊ LOẠI VÌ: " + "; ".join(rep.errors()) + ". Sửa đúng các lỗi này."
        turn.fallback = turn.fallback or "template:validator"
        rep = rule_check(card, template.blocks, allowed | {s for b in template.blocks for s in b.src}, d.level, need_all)
        return template, rep

    def _explain_response(self, turn: Turn, req, ctx: Ctx, d: Decision, text: str, selection: str,
                          hits: list[Passage], sess: dict, note: str = "") -> ChatResponse:
        answer, rep = self._explain(turn, ctx, d, text, selection, hits, note)
        card = ctx.card
        now_ts = time.time()
        sess.setdefault("answered", {})[card.id] = now_ts
        sess.setdefault("last", {})[card.id] = {
            "decision": d.model_dump(), "level": d.level, "style": d.style, "ask_type": d.ask_type,
            "analogy_id": answer.analogy_id, "summary": answer.summary_for_next_turn or answer.key,
        }
        sess["last_concept"] = card.id
        sess.setdefault("tried", {}).setdefault(card.id, []).append(d.style)
        sess.pop("survey", None)
        self.store.save_session(req.session_id, req.user_id, sess)
        sources = list(dict.fromkeys(s for b in answer.blocks for s in b.src))
        return ChatResponse(kind="explain", decision=d, answer=answer, fidelity=rep, sources=sources,
                            notices=turn.notices, meta=self._meta(turn))

    # ================================================================ public API
    def chat(self, req: ChatRequest, survey: dict | None = None, turn: Turn | None = None) -> ChatResponse:
        turn = turn or Turn()
        now = utcnow()
        self.store.ensure_user(req.user_id, now)
        sess = self.store.session(req.session_id, req.user_id)
        if req.action == "ask":
            sess["last_question"] = req.text
        text, selection = req.text, req.selection

        g = check_input(text, selection, self.cards.outside_terms)
        if g.injection or g.out_of_scope:
            resp = self._scope(turn, "injection" if g.injection else "out_of_scope", text)
            self._trace(turn, "chat", req, resp)
            return resp
        if g.outside_term:
            resp = self._scope(turn, "no_source", text, term=_guess_term(text) or g.outside_term,
                               nearest=self.cards.outside_terms.get(g.outside_term, []))
            self._trace(turn, "chat", req, resp)
            return resp

        sig = self.detector.detect(text, selection, sess, self.page_concept(req.lesson_id))
        if req.action == "confused":
            sig.confused, sig.vague, sig.reask = True, False, False
            sig.concept = req.concept_hint or sig.concept or sess.get("last_concept") or self.page_concept(req.lesson_id)
            sess["last_question"] = sess.get("last_question") or text
            if sig.concept in sess.get("answered", {}):
                self._add_notice(turn, self.store.apply_event(req.user_id, sig.concept, "confused", now=now))
                self._record_strategy(req.user_id, sig.concept, sess, "failed")
        elif req.concept_hint and not sig.concept:
            sig.concept = req.concept_hint

        if not sig.concept:
            hits = self.retriever.search(f"{text} {selection}", req.lesson_id, self.s.retrieval_top_k)
            strong = [h for h in hits if h.score >= self.s.retrieval_min_score]
            mapped = next((c for h in strong[:1] for c in self.cards.by_source(h.id)), None)
            if mapped:
                sig.concept = mapped.id
            elif strong:
                top = strong[0]
                term = _guess_term(text) or top.section or "Nội dung bài giảng"
                dyn_id = f"dyn_{top.id.lower()}"
                from .cards import Card
                dyn_card = Card(
                    id=dyn_id,
                    term=term,
                    vi_name=top.section or term,
                    lesson_id=req.lesson_id,
                    reviewed=True,
                    aliases=[term],
                    prerequisites=[],
                    required_terms=[],
                    core_claims=[{"id": "C1", "text": f"Nội dung về {term} được giảng giải trong bài.", "src": [top.id]}],
                    approved_analogies=[],
                    analogy_limits=[],
                    misconceptions=[],
                    outside_lesson_notes=[],
                    primer={},
                    checks=[],
                    templates={
                        "L2_vi_du": [
                            {"t": "p", "html": f"Trong bài giảng, phần <b>{top.section}</b> có giải thích về nội dung này.", "src": [top.id], "claims": ["C1"]},
                            {"t": "p", "html": top.text[:400] + "...", "src": [top.id], "claims": ["C1"]}
                        ]
                    },
                    extras={},
                    aspects={},
                )
                self.cards.cards[dyn_id] = dyn_card
                sig.concept = dyn_id
            else:
                kind = "no_source" if QUESTION_HINT.search(_norm(text)) else "help"
                resp = self._scope(turn, kind, text, term=_guess_term(text) if kind == "no_source" else None,
                                   nearest=[], in_lesson=False)
                self.store.save_session(req.session_id, req.user_id, sess)
                self._trace(turn, "chat", req, resp)
                return resp

        card = self.cards.get(sig.concept)
        hits, grounded, allowed = self._grounding(card, text, selection, req.lesson_id)
        if not grounded:
            resp = self._scope(turn, "no_source", text, term=card.term, nearest=[h.id for h in hits[:2]])
            self._trace(turn, "chat", req, resp)
            return resp

        ctx, _ = self._ctx(req, card, sess, sig, survey, now, (hits, grounded, allowed))
        rules = rule_decide(ctx)
        d = self._diagnose(turn, ctx, rules, text, selection, hits)

        if d.kind == "out_of_scope":
            resp = self._scope(turn, "out_of_scope", text, decision=d)
        elif d.kind == "survey":
            sess["survey_pending"] = card.id
            self.store.save_session(req.session_id, req.user_id, sess)
            resp = ChatResponse(kind="survey", decision=d, survey=self._survey_payload(card, req.user_id, d.reason_for_user),
                                notices=turn.notices, meta=self._meta(turn))
        else:
            resp = self._explain_response(turn, req, ctx, d, text, selection, hits, sess, note=(survey or {}).get("note", ""))
        self._trace(turn, "chat", req, resp)
        return resp

    def survey(self, req: SurveyRequest) -> ChatResponse:
        turn = Turn()
        if not self.cards.get(req.concept):
            raise KeyError(req.concept)
        if not req.skipped:
            changed, ids = [], []
            for cid, lvl in req.levels.items():
                if not self.cards.get(cid):
                    continue
                n = self.store.apply_event(req.user_id, cid, "self_report", level=lvl)
                if n:
                    changed.append(f"{self.terms[cid]}: {UNDERSTANDING_LABEL[lvl]}")
                    ids += n.event_ids
            if changed:
                turn.notices.append(Notice(text="Đã ghi vào Sổ tay (bạn tự khai): " + " · ".join(changed), kind="up", event_ids=ids))
            if req.style and self.store.settings(req.user_id)["memory_on"]:
                self.store.update_settings(req.user_id, preferred_style=req.style)
        survey = {"concept": req.concept, "levels": {} if req.skipped else dict(req.levels),
                  "style": "ngan_gon" if req.skipped else req.style, "note": req.note, "skipped": req.skipped}
        sess = self.store.session(req.session_id, req.user_id)
        # Không ghi thêm sự kiện "chưa hiểu": đã ghi khi học viên bấm nút.
        chat_req = ChatRequest(user_id=req.user_id, session_id=req.session_id, lesson_id=req.lesson_id,
                               text=sess.get("last_question") or "Mình chưa hiểu", action="confused", concept_hint=req.concept)
        return self._chat_after_survey(chat_req, survey, turn)

    def _chat_after_survey(self, req: ChatRequest, survey: dict, turn: Turn) -> ChatResponse:
        now = utcnow()
        sess = self.store.session(req.session_id, req.user_id)
        card = self.cards.get(req.concept_hint)
        sig = self._synthetic_signals(card.id, req.text, confused=True)
        hits, grounded, allowed = self._grounding(card, req.text, "", req.lesson_id)
        ctx, _ = self._ctx(req, card, sess, sig, survey, now, (hits, grounded or card.source_ids[:1], allowed))
        rules = rule_decide(ctx)
        d = self._diagnose(turn, ctx, rules, req.text, "", hits)
        if d.kind != "explain":  # sau khảo sát luôn giải thích
            d = rules.model_copy(update={"kind": "explain", "need_survey": False})
        resp = self._explain_response(turn, req, ctx, d, req.text, "", hits, sess, note=survey.get("note", ""))
        self._trace(turn, "survey", req, resp, {"survey": {k: v for k, v in survey.items() if k != "note"}})
        return resp

    def adjust(self, req: AdjustRequest) -> ChatResponse:
        turn = Turn()
        now = utcnow()
        sess = self.store.session(req.session_id, req.user_id)
        card = self.cards.get(req.concept)
        last = sess.get("last", {}).get(req.concept)
        if not card or not last:
            raise KeyError("Chưa có lời giải thích nào để điều chỉnh")
        d = Decision(**last["decision"])
        d.kind, d.full, d.decided_by, d.alt_example = "explain", True, "user", False
        r = rank(d.level)
        if req.kind == "easier":
            d.level = step(d.level, -1)
            d.style = "vi_du" if rank(d.level) <= 1 else d.style
            d.reason_for_user = "Mình giải thích dễ hơn lần trước" + (", dùng ví dụ đời thường." if d.style == "vi_du" else ".")
            self._add_notice(turn, self.store.apply_event(req.user_id, card.id, "level_down", now=now))
        elif req.kind == "deeper":
            d.level, d.style, d.prereq_first = step(d.level, 1), "chi_tiet", None
            d.reason_for_user = "Mình đi sâu thêm một bước. Phần nào ngoài bài giảng sẽ có nhãn riêng."
        elif req.kind == "shorter":
            if last.get("style") == "chi_tiet":
                self._record_strategy(req.user_id, card.id, sess, "failed", parts=("style",))
            d.prereq_first = None
            if r >= 2:
                d.level, d.full = "L3", False
            else:
                d.style = "ngan_gon"
            d.reason_for_user = "Bạn muốn ngắn hơn, nên mình chỉ giữ các ý chính."
            if self.store.settings(req.user_id)["memory_on"]:
                self.store.update_settings(req.user_id, preferred_style="ngan_gon")
        else:  # example
            self._record_strategy(req.user_id, card.id, sess, "failed", parts=("analogy",))
            d.level, d.style = ("L1" if r == 0 else "L2"), "vi_du"
            ids = card.analogy_ids
            used = last.get("analogy_id")
            d.preferred_analogy = next((a for a in ids if a != used), used)
            d.reason_for_user = "Bạn muốn ví dụ khác, nên mình dùng ví dụ giảng viên đã dùng trong bài."
        sig = self._synthetic_signals(card.id, sess.get("last_question", ""))
        ctx, hits = self._ctx(req, card, sess, sig, None, now)
        resp = self._explain_response(turn, req, ctx, d, sess.get("last_question", ""), "", hits, sess)
        self._trace(turn, "adjust", req, resp, {"adjust": req.kind})
        return resp

    def check_question(self, user_id: str, session_id: str, concept: str):
        card = self.cards.get(concept)
        if not card:
            raise KeyError(concept)
        sess = self.store.session(session_id, user_id)
        return checks.pick(card, sess.get("check_attempt", {}).get(concept, 0))

    def feedback(self, req: FeedbackRequest) -> FeedbackResult:
        turn = Turn()
        sess = self.store.session(req.session_id, req.user_id)
        card = self.cards.get(req.concept)
        if not card:
            raise KeyError(req.concept)
        if req.value == "up":
            sess.setdefault("pending_up", {})[card.id] = True
            self.store.save_session(req.session_id, req.user_id, sess)
            q = checks.pick(card, sess.get("check_attempt", {}).get(card.id, 0))
            self._trace(turn, "feedback", req, extra={"value": "up"})
            return FeedbackResult(next="check" if q else "done", check=q)

        td = sess.setdefault("thumbs_down", {})
        td[card.id] = td.get(card.id, 0) + 1
        self._record_strategy(req.user_id, card.id, sess, "failed")
        self.store.save_session(req.session_id, req.user_id, sess)
        if td[card.id] >= self.s.max_thumbs_down:
            self._trace(turn, "feedback", req, extra={"value": "down", "next": "handoff"})
            return FeedbackResult(next="handoff", handoff=handoff.draft(card, sess, self.lesson_title(req.lesson_id)))
        if req.reason == "wrong":
            self._trace(turn, "feedback", req, extra={"value": "down", "reason": "wrong"})
            return FeedbackResult(next="report", handoff=handoff.draft(card, sess, self.lesson_title(req.lesson_id)),
                                  notices=[Notice(text="Cảm ơn bạn đã báo. Mình đã ghi lại để TA kiểm tra thẻ khái niệm.", kind="info")])
        if req.reason in ("hard", "long"):
            resp = self.adjust(AdjustRequest(user_id=req.user_id, session_id=req.session_id, lesson_id=req.lesson_id,
                                             concept=card.id, kind="easier" if req.reason == "hard" else "shorter"))
            return FeedbackResult(next="retry", response=resp, notices=resp.notices)
        # Không nêu lý do → đổi kiểu, giữ mức.
        last = sess["last"][card.id]
        d = Decision(**last["decision"])
        d.kind, d.full, d.decided_by = "explain", True, "user"
        d.style = STYLE_ORDER[(STYLE_ORDER.index(d.style) + 1) % len(STYLE_ORDER)]
        d.reason_for_user = "Mình đổi cách giải thích so với lần trước."
        ctx, hits = self._ctx(req, card, sess, self._synthetic_signals(card.id, sess.get("last_question", "")), None, utcnow())
        resp = self._explain_response(turn, req, ctx, d, sess.get("last_question", ""), "", hits, sess)
        self._trace(turn, "feedback", req, resp, {"value": "down"})
        return FeedbackResult(next="retry", response=resp)

    def check_answer(self, req: CheckAnswerRequest) -> CheckResult:
        turn = Turn()
        now = utcnow()
        card = self.cards.get(req.concept)
        if not card:
            raise KeyError(req.concept)
        g = checks.grade(card, req.question_id, req.answer)
        if g is None:
            raise KeyError(req.question_id)
        sess = self.store.session(req.session_id, req.user_id)
        att = sess.setdefault("check_attempt", {})
        att[card.id] = att.get(card.id, 0) + 1
        if g["correct"]:
            self._add_notice(turn, self.store.apply_event(req.user_id, card.id, "check_correct", now=now))
            if sess.get("pending_up", {}).pop(card.id, None):
                self._record_strategy(req.user_id, card.id, sess, "worked")
            self.store.save_session(req.session_id, req.user_id, sess)
            self._trace(turn, "check", req, extra={"correct": True})
            return CheckResult(correct=True, right=g["right"], src=g["src"], next="done", notices=turn.notices)

        self.store.apply_event(req.user_id, card.id, "check_wrong", now=now)
        self._record_strategy(req.user_id, card.id, sess, "failed")
        sess.get("pending_up", {}).pop(card.id, None)
        wrong = sess.setdefault("wrong", {})
        wrong[card.id] = wrong.get(card.id, 0) + 1
        self.store.save_session(req.session_id, req.user_id, sess)
        base = dict(correct=False, right=g["right"], fix_html=g["fix_html"], misconception=g.get("misconception"), src=g["src"])
        if wrong[card.id] >= self.s.max_wrong_checks:
            self._trace(turn, "check", req, extra={"correct": False, "next": "handoff"})
            return CheckResult(**base, next="handoff", handoff=handoff.draft(card, sess, self.lesson_title(req.lesson_id)))
        last = sess.get("last", {}).get(card.id)
        d = Decision(**last["decision"]) if last else Decision(kind="explain", concept=card.id, level="L2")
        d.kind, d.full, d.decided_by, d.alt_example, d.prereq_first = "explain", True, "user", True, None
        d.level = "L2" if rank(d.level) >= 2 else d.level
        d.style = STYLE_ORDER[(STYLE_ORDER.index(d.style) + 1) % len(STYLE_ORDER)]
        d.reason_for_user = f"Mình đổi sang cách “{STYLE_LABEL[d.style]}” để làm rõ đúng chỗ bạn vừa chọn sai."
        ctx, hits = self._ctx(req, card, sess, self._synthetic_signals(card.id, sess.get("last_question", "")), None, now)
        resp = self._explain_response(turn, req, ctx, d, sess.get("last_question", ""), "", hits, sess)
        self._trace(turn, "check", req, resp, {"correct": False})
        return CheckResult(**base, next="retry", response=resp, notices=turn.notices)

    def handoff(self, req: HandoffRequest) -> str:
        sess = self.store.session(req.session_id, req.user_id)
        card = self.cards.get(req.concept or sess.get("last_concept"))
        return handoff.draft(card, sess, self.lesson_title(req.lesson_id))

    def source(self, source_id: str) -> dict | None:
        p = self.retriever.get(source_id)
        if not p and source_id not in self.cards.sources:
            return None
        meta = self.cards.sources.get(source_id, {})
        return {
            "id": source_id,
            "section": (p.section if p else meta.get("section", "")),
            "text": p.text if (p and self.retriever.mode == "local") else meta.get("summary", ""),
            "mode": self.retriever.mode if p else "summary",
        }

    def health(self) -> dict:
        return {
            "status": "ok", "provider": self.provider, "model": self.s.llm_model,
            "model_explain": self.s.model_explain, "model_judge": self.s.model_judge,
            "use_judge": self.s.use_judge, "replay": self.s.replay,
            "retrieval_mode": self.retriever.mode, "passages": len(self.retriever.docs),
            "cards": sorted(self.cards.cards), "prompt_version": self.prompts.version,
        }

    # ---------------------------------------------------------------- baseline (eval)
    def baseline(self, text: str) -> tuple[str, list[Usage]]:
        turn = Turn()
        user = self.prompts.render("baseline", text=text)
        fb = LLMBaselineAnswer(text="Self-attention giúp mô hình chú ý tới các từ quan trọng trong câu.")
        obj = self._call(turn, "baseline", user, LLMBaselineAnswer, self.s.model_explain, fallback=fb,
                         system="Bạn là trợ giảng AI của khoá học, trả lời bằng tiếng Việt.")
        return obj.text, turn.usages


def _norm(text: str) -> str:
    return norm(text)


def _guess_term(text: str) -> str | None:
    """Lấy cụm đứng trước "là gì / là sao" để nêu tên trong câu trả lời (chỉ hiển thị)."""
    m = re.match(r"\s*(.{2,40}?)\s+(là gì|là sao|là như thế nào|hoạt động)", text, re.I)
    return m.group(1).strip() if m else None
