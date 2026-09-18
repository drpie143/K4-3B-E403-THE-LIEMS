from __future__ import annotations

from uuid import UUID

from app.service.errors import AppError
from app.repository.conversation import ConversationRepository


class ProfileService:
    def __init__(self, repository: ConversationRepository):
        self.repository = repository

    async def get_profile(self, user_id: str) -> dict:
        user = await self.repository.get_user(user_id)
        if not user:
            user = await self.repository.upsert_user(user_id)
        skills = await self.repository.skill_map(user.id)
        return {
            "user_id": user_id,
            "default_level": user.default_level,
            "skill_map": [
                {
                    "topic_key": k,
                    "level": v["level"],
                    "confidence": v["confidence"],
                    "probe_consumed": v["probe_consumed"],
                    "cooldown_until_turn": v["cooldown_until_turn"],
                    "updated_at": None,
                }
                for k, v in skills.items()
            ],
            "recent_level_events": [
                {
                    kk: str(vv) if not isinstance(vv, (str, int, float, bool, type(None))) else vv
                    for kk, vv in e.items()
                }
                for e in await self.repository.recent_events(user.id)
            ],
        }

    async def get_conversation(self, conversation_id: UUID) -> dict:
        conv = await self.repository.get_conversation(conversation_id)
        if not conv:
            raise AppError(404, "conversation_not_found", "Không tìm thấy hội thoại.")
        user = await self.repository.get_user_by_id(conv.user_id)
        msgs = []
        for m in await self.repository.list_messages(conv.id):
            msgs.append(
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "intent": m.intent,
                    "response_kind": m.response_kind,
                    "payload": m.payload,
                    "client_turn_id": str(m.client_turn_id) if m.client_turn_id else None,
                    "created_at": m.created_at.isoformat(),
                }
            )
        return {
            "id": str(conv.id),
            "user_id": user.external_id if user else None,
            "session_id": conv.session_id,
            "awaiting_probe": conv.awaiting_probe,
            "turn_index": conv.turn_index,
            "messages": msgs,
        }
