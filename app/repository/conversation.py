from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from app.model.entities import (
    ConversationRow,
    IdempotencyRow,
    MessageRow,
    SkillRow,
    UserRow,
    utcnow,
)


class ConversationRepository:
    def __init__(self, lease_seconds: int = 45):
        self.lease_seconds = lease_seconds
        self._lock = asyncio.Lock()
        self.users: dict[str, UserRow] = {}
        self.users_by_id: dict[UUID, UserRow] = {}
        self.skills: dict[tuple[UUID, str], SkillRow] = {}
        self.conversations: dict[UUID, ConversationRow] = {}
        self.messages: list[MessageRow] = []
        self.idempotency: dict[UUID, IdempotencyRow] = {}
        self.level_events: list[dict] = []
        for i in range(1, 6):
            ext = f"hv-0{i}"
            u = UserRow(id=uuid4(), external_id=ext)
            self.users[ext] = u
            self.users_by_id[u.id] = u

    async def upsert_user(self, external_id: str) -> UserRow:
        async with self._lock:
            if external_id not in self.users:
                u = UserRow(id=uuid4(), external_id=external_id)
                self.users[external_id] = u
                self.users_by_id[u.id] = u
            return self.users[external_id]

    async def get_user(self, external_id: str) -> UserRow | None:
        async with self._lock:
            return self.users.get(external_id)

    async def get_user_by_id(self, user_id: UUID) -> UserRow | None:
        async with self._lock:
            return self.users_by_id.get(user_id)

    async def skill_map(self, user_id: UUID) -> dict[str, dict]:
        async with self._lock:
            out = {}
            for (uid, topic), row in self.skills.items():
                if uid == user_id:
                    out[topic] = {
                        "level": row.level,
                        "confidence": row.confidence,
                        "source": row.source,
                        "probe_consumed": row.probe_consumed,
                        "cooldown_until_turn": row.cooldown_until_turn,
                        "last_level_change_turn": row.last_level_change_turn,
                    }
            return out

    async def get_conversation(self, conv_id: UUID) -> ConversationRow | None:
        async with self._lock:
            return self.conversations.get(conv_id)

    async def get_conversation_by_session(self, user_id: UUID, session_id: str) -> ConversationRow | None:
        async with self._lock:
            for row in self.conversations.values():
                if row.user_id == user_id and row.session_id == session_id:
                    return row
            return None

    async def insert_conversation(self, conv_id: UUID, user_id: UUID, session_id: str) -> ConversationRow:
        async with self._lock:
            row = ConversationRow(id=conv_id, user_id=user_id, session_id=session_id)
            self.conversations[conv_id] = row
            return row

    async def get_idempotency(self, client_turn_id: UUID) -> IdempotencyRow | None:
        async with self._lock:
            return self.idempotency.get(client_turn_id)

    async def assistant_for_turn(self, client_turn_id: UUID) -> MessageRow | None:
        async with self._lock:
            for m in reversed(self.messages):
                if m.client_turn_id == client_turn_id and m.role == "assistant":
                    return m
            return None

    def _processing_for_conv(self, conv_id: UUID) -> IdempotencyRow | None:
        for row in self.idempotency.values():
            if row.conversation_id == conv_id and row.status == "processing":
                return row
        return None

    async def acquire_lease(self, conv_id: UUID) -> bool:
        async with self._lock:
            conv = self.conversations.get(conv_id)
            if not conv:
                return False
            now = utcnow()
            if conv.lease_until and conv.lease_until > now:
                return False
            conv.lease_until = now + timedelta(seconds=self.lease_seconds)
            return True

    async def clear_lease(self, conv_id: UUID) -> None:
        async with self._lock:
            conv = self.conversations.get(conv_id)
            if conv:
                conv.lease_until = None

    async def insert_processing(self, client_turn_id: UUID, conv_id: UUID) -> str | None:
        async with self._lock:
            other = self._processing_for_conv(conv_id)
            if other and other.client_turn_id != client_turn_id:
                return "turn_in_flight"
            self.idempotency[client_turn_id] = IdempotencyRow(
                client_turn_id=client_turn_id,
                conversation_id=conv_id,
                status="processing",
            )
            return None

    async def finish_idempotency(
        self, client_turn_id: UUID, status: str, response_json: dict, http_status: int
    ) -> None:
        async with self._lock:
            row = self.idempotency.get(client_turn_id)
            if row:
                row.status = status
                row.response_json = response_json
                row.http_status = http_status

    async def upsert_skill(self, user_id: UUID, topic_key: str, **kwargs) -> SkillRow:
        async with self._lock:
            key = (user_id, topic_key)
            row = self.skills.get(key)
            if not row:
                row = SkillRow(user_id=user_id, topic_key=topic_key, level=kwargs.get("level", "beginner"))
                self.skills[key] = row
            for k, v in kwargs.items():
                setattr(row, k, v)
            row.updated_at = utcnow()
            return row

    async def add_level_event(self, event: dict) -> None:
        async with self._lock:
            self.level_events.append(event)

    async def add_messages(self, rows: list[MessageRow]) -> None:
        async with self._lock:
            self.messages.extend(rows)

    async def update_conversation(self, conv_id: UUID, **kwargs) -> None:
        async with self._lock:
            conv = self.conversations[conv_id]
            for k, v in kwargs.items():
                setattr(conv, k, v)
            conv.last_turn_at = utcnow()

    async def list_messages(self, conv_id: UUID) -> list[MessageRow]:
        async with self._lock:
            return [m for m in self.messages if m.conversation_id == conv_id]

    async def recent_events(self, user_id: UUID, limit: int = 10) -> list[dict]:
        async with self._lock:
            rows = [
                e
                for e in self.level_events
                if e.get("user_id") == str(user_id) or e.get("user_pk") == user_id
            ]
            return rows[-limit:]

    async def health(self) -> bool:
        return True
