from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.config import Settings
from app.service.errors import AppError
from app.schema.chat import ChatRequest, ChatResponse, Choice
from app.repository.conversation import ConversationRepository


def _age_seconds(created: datetime) -> float:
    now = datetime.now(timezone.utc)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (now - created).total_seconds()


def _state_to_response(state: dict, conversation_id: UUID) -> ChatResponse:
    kind = state.get("response_kind") or "explanation"
    choices = []
    if kind == "probe":
        for c in state.get("probe_choices") or []:
            choices.append(Choice.model_validate(c))
    turn_id = state.get("turn_id") or str(uuid4())
    return ChatResponse(
        conversation_id=conversation_id,
        turn_id=UUID(str(turn_id)),
        kind=kind,  # type: ignore[arg-type]
        content=state.get("final_answer") or "",
        choices=choices,
        user_level=state.get("user_level") or "unknown",
        topic_key=state.get("current_topic") or "misc",
        explanation_mode=state.get("explanation_mode"),
        citations=list(state.get("citations") or []),
        route_reason=state.get("route_reason") or "",
    )


def _message_to_response(msg, conv_id: UUID, user_level: str, topic: str) -> ChatResponse:
    payload = msg.payload or {}
    choices = [Choice.model_validate(c) for c in payload.get("choices") or []]
    return ChatResponse(
        conversation_id=conv_id,
        turn_id=msg.id,
        kind=msg.response_kind or "explanation",
        content=msg.content,
        choices=choices,
        user_level=user_level,
        topic_key=msg.topic_key or topic or "misc",
        explanation_mode=msg.explanation_mode,
        citations=list(msg.citations or []),
        route_reason=msg.route_reason or "",
    )


class ChatService:
    def __init__(self, repository: ConversationRepository, graph, settings: Settings):
        self.repository = repository
        self.graph = graph
        self.settings = settings

    async def handle(self, req: ChatRequest) -> ChatResponse:
        repo = self.repository
        message = (req.message or "").strip()
        hi = (req.context.highlighted_text if req.context else None) or ""
        if not message and not hi.strip():
            raise AppError(422, "empty_message", "message hoặc highlighted_text bắt buộc.")

        user = await repo.upsert_user(req.user_id)
        client = req.client_turn_id
        existing = await repo.get_idempotency(client)

        if existing:
            if existing.status == "completed" and existing.response_json:
                return ChatResponse.model_validate(existing.response_json)
            if existing.status == "error" and existing.response_json:
                err = existing.response_json.get("error") or {}
                raise AppError(
                    existing.http_status or 504,
                    err.get("code") or "llm_timeout",
                    err.get("message") or "error",
                )
            if existing.status == "processing":
                asst = await repo.assistant_for_turn(client)
                if asst:
                    skills = await repo.skill_map(user.id)
                    topic = asst.topic_key or "misc"
                    level = (skills.get(topic) or {}).get("level", "unknown")
                    resp = _message_to_response(asst, existing.conversation_id, level, topic)
                    await repo.finish_idempotency(client, "completed", resp.model_dump(mode="json"), 200)
                    await repo.clear_lease(existing.conversation_id)
                    return resp
                conv = await repo.get_conversation(existing.conversation_id)
                lease_expired = (
                    not conv
                    or conv.lease_until is None
                    or conv.lease_until < datetime.now(timezone.utc)
                )
                stale = _age_seconds(existing.created_at) >= self.settings.stale_processing_seconds
                if not (lease_expired and stale):
                    raise AppError(409, "turn_in_flight", "Lượt trước vẫn đang xử lý.")
                conv_id = existing.conversation_id
            else:
                conv_id = existing.conversation_id
        else:
            if req.conversation_id is None:
                conv_id = uuid4()
                await repo.insert_conversation(conv_id, user.id, req.session_id)
            else:
                conv = await repo.get_conversation(req.conversation_id)
                if not conv:
                    raise AppError(404, "conversation_not_found", "Không tìm thấy hội thoại.")
                if conv.user_id != user.id:
                    raise AppError(403, "conversation_forbidden", "Hội thoại không thuộc user này.")
                bound = await repo.get_idempotency(client)
                if bound and bound.conversation_id != req.conversation_id:
                    raise AppError(409, "idempotency_conflict", "client_turn_id đã gắn conversation khác.")
                conv_id = req.conversation_id

        ok = await repo.acquire_lease(conv_id)
        if not ok:
            raise AppError(409, "turn_in_flight", "Conversation đang bận.")
        conflict = await repo.insert_processing(client, conv_id)
        if conflict:
            await repo.clear_lease(conv_id)
            raise AppError(409, "turn_in_flight", "Conversation đang bận.")

        turn_id = uuid4()
        ctx = req.context
        try:
            state = await self.graph.ainvoke(
                {
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                    "conversation_id": str(conv_id),
                    "client_turn_id": str(client),
                    "turn_id": str(turn_id),
                    "user_message": message or hi,
                    "highlighted_text": hi or None,
                    "context_lecture_id": ctx.lecture_id if ctx else None,
                    "context_slide_page": ctx.slide_page if ctx else None,
                },
                config={"configurable": {"thread_id": str(conv_id)}},
            )
            resp = _state_to_response(state, conv_id)
            await repo.finish_idempotency(client, "completed", resp.model_dump(mode="json"), 200)
            await repo.clear_lease(conv_id)
            return resp
        except AppError:
            await repo.clear_lease(conv_id)
            raise
        except Exception as exc:
            env = {
                "error": {
                    "code": "llm_timeout",
                    "message": "Tutor đang quá tải, thử lại giúp nhé.",
                    "request_id": str(uuid4()),
                }
            }
            await repo.finish_idempotency(client, "error", env, 504)
            await repo.clear_lease(conv_id)
            raise AppError(504, "llm_timeout", str(exc)[:200]) from exc
