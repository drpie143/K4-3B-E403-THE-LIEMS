from __future__ import annotations

import re
from uuid import UUID, uuid4

from app.schema.chat import ChatRequest, ChatContext
from app.schema.vlearn import (
    LEVEL_FROM_SKILL,
    SKILL_FROM_UNDERSTANDING,
    STYLE_FROM_SKILL,
    UNDERSTANDING_FROM_SKILL,
    VLearnAdjustRequest,
    VLearnChatRequest,
    VLearnCheckRequest,
    VLearnFeedbackRequest,
    VLearnHandoffRequest,
    VLearnProfileUpdate,
    VLearnSurveyRequest,
)
from app.repository.cards import CardRepository
from app.repository.conversation import ConversationRepository
from app.service.chat import ChatService

INJECTION_RE = re.compile(
    r"bỏ qua hướng dẫn|ignore previous|system_override|system prompt|jailbreak",
    re.I,
)
OFF_RE = re.compile(r"viết blog|làm bài hộ|code giúp tôi cả project", re.I)


def _md_to_html(text: str) -> str:
    t = (text or "").replace("\n\n", "<br><br>").replace("\n", "<br>")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t


class VLearnService:
    """Adapter UI VLearn (main mock) ↔ ChatService / LangGraph."""

    def __init__(
        self,
        chat: ChatService,
        repository: ConversationRepository,
        cards: CardRepository,
    ):
        self.chat_service = chat
        self.repository = repository
        self.cards = cards
        self._memory_on: dict[str, bool] = {}
        self._style: dict[str, str | None] = {}
        self._check_i: dict[tuple[str, str], int] = {}
        self._down: dict[tuple[str, str], int] = {}
        self._wrong: dict[tuple[str, str], int] = {}
        self._seeded: set[str] = set()

    async def health(self) -> dict:
        return {
            "status": "ok",
            "provider": "fake" if not self.chat_service.settings.resolved_llm_key else "spacexai",
            "model": self.chat_service.settings.llm_model,
            "retrieval_mode": "local" if self.cards.local_chunks else "summary",
            "cards": len(self.cards.cards),
            "dump_first": self.chat_service.settings.dump_first,
        }

    def personas(self) -> dict:
        return {uid: {"label": p.get("label", uid)} for uid, p in self.cards.personas.items()}

    async def _ensure_user_persona(self, user_id: str) -> None:
        if user_id in self._seeded:
            return
        user = await self.repository.upsert_user(user_id)
        persona = self.cards.personas.get(user_id) or {}
        for cid, row in (persona.get("concepts") or {}).items():
            level = SKILL_FROM_UNDERSTANDING.get(row.get("level") or "", "beginner")
            await self.repository.upsert_skill(
                user.id, cid, level=level, source="seed", probe_consumed=True, confidence=0.8
            )
        self._style[user_id] = persona.get("preferred_style")
        self._memory_on.setdefault(user_id, True)
        self._seeded.add(user_id)

    async def _conv_id(self, user_id: str, session_id: str) -> UUID:
        user = await self.repository.upsert_user(user_id)
        row = await self.repository.get_conversation_by_session(user.id, session_id)
        if row:
            return row.id
        cid = uuid4()
        await self.repository.insert_conversation(cid, user.id, session_id)
        return cid

    async def _invoke(
        self,
        user_id: str,
        session_id: str,
        message: str,
        selection: str = "",
        lesson_id: str = "day01-self-attention",
    ):
        await self._ensure_user_persona(user_id)
        conv = await self._conv_id(user_id, session_id)
        req = ChatRequest(
            user_id=user_id,
            session_id=session_id,
            client_turn_id=uuid4(),
            conversation_id=conv,
            message=message,
            context=ChatContext(
                lecture_id=lesson_id,
                highlighted_text=selection or None,
            ),
        )
        return await self.chat_service.handle(req)

    def _to_ui(self, internal, concept_hint: str | None = None) -> dict:
        kind = internal.kind
        topic = internal.topic_key if internal.topic_key != "misc" else (concept_hint or "self_attention")
        card = self.cards.get(topic)
        skill = internal.user_level
        level = LEVEL_FROM_SKILL.get(skill, "L2")
        style = STYLE_FROM_SKILL.get(skill, "vi_du")
        src = []
        for c in internal.citations or []:
            if isinstance(c, dict):
                lec = str(c.get("lecture_id") or "")
                if re.match(r"T\d{2}-\d{3}", lec):
                    src.append(lec)
        text = internal.content or ""
        for m in re.findall(r"\[(T\d{2}-\d{3})\]", text):
            if m not in src:
                src.append(m)
        if card:
            for claim in card.get("core_claims") or []:
                for s in claim.get("src") or []:
                    if s not in src:
                        src.append(s)
            src = src[:6]

        decision = {
            "kind": "explain",
            "concept": topic if card else None,
            "level": level,
            "style": style,
            "missing_concepts": [],
            "confidence": 0.7,
            "need_survey": kind == "probe",
            "in_scope": kind not in ("retrieval_miss", "redirect"),
            "source_ids": src,
            "reason_for_user": internal.route_reason or "",
            "decided_by": "agent",
        }

        if kind == "probe":
            rows = []
            if card:
                for prereq in (card.get("prerequisites") or [])[:3]:
                    pc = self.cards.get(prereq) or {}
                    rows.append(
                        {
                            "concept": prereq,
                            "term": pc.get("term") or prereq,
                            "vi_name": pc.get("vi_name") or "",
                            "level": None,
                        }
                    )
            if not rows:
                rows = [
                    {
                        "concept": topic,
                        "term": (card or {}).get("term") or topic,
                        "vi_name": (card or {}).get("vi_name") or "",
                        "level": None,
                    }
                ]
            decision["kind"] = "survey"
            decision["need_survey"] = True
            decision["reason_for_user"] = internal.content or "Để giải thích đúng tầm, cho mình biết nền tảng của bạn."
            return {
                "kind": "survey",
                "decision": decision,
                "survey": {
                    "concept": topic,
                    "term": (card or {}).get("term") or topic,
                    "rows": rows,
                    "style": style,
                    "reason": decision["reason_for_user"],
                },
                "notices": [],
                "sources": src,
                "meta": {"request_id": str(internal.turn_id), "prompt_version": "agent-v1", "provider": "agent"},
            }

        if kind in ("retrieval_miss", "redirect"):
            ui_kind = "injection" if INJECTION_RE.search(internal.content or "") else "no_source"
            nearest = list((self.cards.sources.get("sources") or {}).keys())[:3]
            return {
                "kind": ui_kind if ui_kind == "injection" else "no_source",
                "decision": {**decision, "kind": "no_source", "in_scope": False},
                "scope": {
                    "message": internal.content
                    or "Slide không đề cập nội dung này trong kho bài giảng hiện tại.",
                    "term": topic if topic != "misc" else None,
                    "nearest": nearest,
                    "suggestions": [
                        "Self-attention là gì?",
                        "Token khác gì với từ?",
                        "Vector embedding dùng để làm gì?",
                    ],
                },
                "notices": [],
                "sources": [],
                "meta": {"request_id": str(internal.turn_id), "prompt_version": "agent-v1", "provider": "agent"},
            }

        claims = [c.get("id") for c in (card.get("core_claims") or [])] if card else []
        blocks = [
            {
                "t": "analogy" if skill == "beginner" else "p",
                "html": _md_to_html(internal.content),
                "src": src,
                "claims": claims,
            }
        ]
        total = max(1, len(claims))
        return {
            "kind": "explain",
            "decision": decision,
            "answer": {
                "blocks": blocks,
                "summary_for_next_turn": (internal.content or "")[:180],
            },
            "fidelity": {
                "covered": total,
                "total": total,
                "missing_claims": [],
                "missing_terms": [],
                "misconceptions": [],
                "unlabeled": 0,
                "outside": 0,
                "ok": True,
            },
            "sources": src,
            "notices": [],
            "meta": {"request_id": str(internal.turn_id), "prompt_version": "agent-v1", "provider": "agent"},
        }

    async def chat(self, req: VLearnChatRequest) -> dict:
        text = (req.text or "").strip()
        if INJECTION_RE.search(text):
            return {
                "kind": "injection",
                "decision": {"kind": "injection", "in_scope": False, "reason_for_user": "Ngoài phạm vi trợ giảng."},
                "scope": {
                    "message": "Mình không làm theo chỉ dẫn ghi đè hệ thống. Bạn hỏi một khái niệm trên slide nhé.",
                    "suggestions": ["Self-attention là gì?", "Query khác Key chỗ nào?"],
                    "nearest": [],
                },
                "notices": [],
                "sources": [],
            }
        if req.action == "confused":
            text = "khó hiểu quá"
        sel = req.selection or ""
        if req.concept_hint and not sel:
            sel = req.concept_hint.replace("_", "-")
        internal = await self._invoke(req.user_id, req.session_id, text, sel, req.lesson_id)
        return self._to_ui(internal, req.concept_hint)

    async def survey(self, req: VLearnSurveyRequest) -> dict:
        if req.skipped:
            msg = "cứ giải thích"
        else:
            ranks = [SKILL_FROM_UNDERSTANDING.get(v, "beginner") for v in req.levels.values()]
            if not ranks or "beginner" in ranks:
                msg = "Mới bắt đầu, chưa rõ token và vector"
            elif all(r == "advanced" for r in ranks):
                msg = "Đã hiểu Q·K và softmax, cần cơ chế và trade-off"
            else:
                msg = "Biết token/vector, chưa nắm Query-Key-Value"
            if req.note:
                msg = msg + ". " + req.note
            if req.style:
                self._style[req.user_id] = req.style
        internal = await self._invoke(
            req.user_id, req.session_id, msg, req.concept.replace("_", "-"), "day01-self-attention"
        )
        return self._to_ui(internal, req.concept)

    async def adjust(self, req: VLearnAdjustRequest) -> dict:
        msg = {
            "easier": "khó hiểu quá",
            "deeper": "nâng cao hơn",
            "shorter": "ngắn lại",
            "example": "giải thích chi tiết hơn",
        }[req.kind]
        internal = await self._invoke(req.user_id, req.session_id, msg, req.concept.replace("_", "-"))
        return self._to_ui(internal, req.concept)

    async def feedback(self, req: VLearnFeedbackRequest) -> dict:
        key = (req.user_id, req.concept)
        if req.value == "up":
            check = self._pick_check(req.concept, self._check_i.get(key, 0))
            return {"next": "check" if check else "ok", "check": check, "notices": []}
        self._down[key] = self._down.get(key, 0) + 1
        if self._down[key] >= 2:
            return {
                "next": "handoff",
                "handoff": self._handoff_text(req.concept, "Đã thử 2 cách chưa hợp."),
                "notices": [{"text": "Chuyển TA sau 2 lần chưa hợp", "kind": "down"}],
            }
        if req.reason == "wrong":
            return {
                "next": "report",
                "handoff": self._handoff_text(req.concept, "Học viên báo có thể sai kiến thức."),
                "notices": [],
            }
        kind = "easier" if req.reason in ("hard", None) else "shorter"
        resp = await self.adjust(
            VLearnAdjustRequest(
                user_id=req.user_id, session_id=req.session_id, concept=req.concept, kind=kind
            )
        )
        return {"next": "explain", "response": resp, "notices": []}

    def _pick_check(self, concept: str, index: int) -> dict | None:
        checks = self.cards.checks(concept)
        if not checks:
            return None
        c = checks[index % len(checks)]
        return {
            "id": c.get("id"),
            "concept": concept,
            "question": c.get("question"),
            "q": c.get("question"),
            "options": [
                {"k": o.get("k"), "text": o.get("text")} for o in c.get("options") or []
            ],
            "src": c.get("src") or [],
        }

    async def get_check(self, user_id: str, concept: str) -> dict | None:
        key = (user_id, concept)
        i = self._check_i.get(key, 0)
        q = self._pick_check(concept, i)
        if q:
            self._check_i[key] = i + 1
        return q

    async def grade_check(self, req: VLearnCheckRequest) -> dict:
        checks = self.cards.checks(req.concept)
        q = next((c for c in checks if c.get("id") == req.question_id), None)
        if not q:
            return {"correct": False, "right": "A", "src": []}
        right = next((o for o in q.get("options") or [] if o.get("correct")), None)
        chosen = next((o for o in q.get("options") or [] if o.get("k") == req.answer), None)
        ok = bool(chosen and chosen.get("correct"))
        key = (req.user_id, req.concept)
        if not ok:
            self._wrong[key] = self._wrong.get(key, 0) + 1
        card = self.cards.get(req.concept) or {}
        misc = None
        if chosen and chosen.get("misconception"):
            mid = chosen["misconception"]
            misc = next((m for m in card.get("misconceptions") or [] if m.get("id") == mid), None)
        out = {
            "correct": ok,
            "right": (right or {}).get("k") or "A",
            "src": q.get("src") or [],
            "fix_html": (misc or {}).get("fix") if misc else "",
            "misconception": bool(misc),
            "notices": [],
        }
        if not ok and self._wrong.get(key, 0) >= 2:
            out["next"] = "handoff"
            out["handoff"] = self._handoff_text(req.concept, "Sai 2 câu kiểm tra.")
        elif not ok:
            adj = await self.adjust(
                VLearnAdjustRequest(
                    user_id=req.user_id,
                    session_id=req.session_id,
                    concept=req.concept,
                    kind="easier",
                )
            )
            out["next"] = "explain"
            out["response"] = adj
        return out

    def _handoff_text(self, concept: str | None, why: str) -> str:
        card = self.cards.get(concept or "") or {}
        term = card.get("term") or concept or "khái niệm này"
        return (
            f"Mình đang học {term} (Day 1 · LLM Foundation). {why} "
            f"Bạn giải thích giúp với nguồn trên slide/transcript được không?"
        )

    async def handoff(self, req: VLearnHandoffRequest) -> dict:
        return {"draft": self._handoff_text(req.concept, "Mình chưa hiểu phần này.")}

    async def profile(self, user_id: str) -> dict:
        await self._ensure_user_persona(user_id)
        user = await self.repository.upsert_user(user_id)
        skills = await self.repository.skill_map(user.id)
        concepts = {}
        for cid, row in skills.items():
            concepts[cid] = {
                "level": UNDERSTANDING_FROM_SKILL.get(row.get("level") or "", "chua"),
                "source": row.get("source") or "assessor",
                "streak": 0,
                "evidence": [],
            }
        return {
            "user_id": user_id,
            "memory_on": self._memory_on.get(user_id, True),
            "preferred_style": self._style.get(user_id),
            "concepts": concepts,
            "events": [],
        }

    async def put_profile(self, req: VLearnProfileUpdate) -> dict:
        await self._ensure_user_persona(req.user_id)
        if req.memory_on is not None:
            self._memory_on[req.user_id] = req.memory_on
        if req.clear_style:
            self._style[req.user_id] = None
        elif req.preferred_style is not None:
            self._style[req.user_id] = req.preferred_style
        if req.concept and req.level:
            user = await self.repository.upsert_user(req.user_id)
            await self.repository.upsert_skill(
                user.id,
                req.concept,
                level=SKILL_FROM_UNDERSTANDING.get(req.level, "beginner"),
                source="explicit_signal",
                probe_consumed=True,
            )
        return {"profile": await self.profile(req.user_id)}

    async def source(self, source_id: str) -> dict | None:
        return self.cards.source(source_id)

    async def reset_session(self, session_id: str) -> dict:
        return {"ok": True}

    async def reset_user(self, user_id: str) -> dict:
        self._seeded.discard(user_id)
        await self._ensure_user_persona(user_id)
        return {"profile": await self.profile(user_id)}
