from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

from app.model.entities import ConversationRow, IdempotencyRow, MessageRow, SkillRow, UserRow, utcnow

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
VALID_SOURCES = {
    "assessor",
    "choice_map",
    "explicit_signal",
    "fallback_refuse",
    "fallback_low_conf",
    "fallback_score_timeout",
    "seed",
}
VALID_INTENTS = {
    "ask_concept",
    "clarify_harder",
    "ask_deeper",
    "answer_probe",
    "refuse_probe",
    "off_topic",
    "meta",
}
VALID_KINDS = {"probe", "explanation", "redirect", "retrieval_miss", "error", "meta"}
VALID_MODES = {"eli5", "slide_short", "technical"}
VALID_ROLES = {"user", "assistant", "system"}


def _dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _uuids(ids: list | None) -> list[UUID]:
    out = []
    for x in ids or []:
        try:
            out.append(x if isinstance(x, UUID) else UUID(str(x)))
        except (ValueError, TypeError, AttributeError):
            continue
    return out


def _user(r) -> UserRow:
    return UserRow(id=r["id"], external_id=r["external_id"], default_level=r["default_level"])


def _conv(r) -> ConversationRow:
    ids = r["last_retrieved_chunk_ids"] or []
    return ConversationRow(
        id=r["id"],
        user_id=r["user_id"],
        session_id=r["session_id"],
        turn_index=r["turn_index"],
        awaiting_probe=r["awaiting_probe"],
        pending_original_query=r["pending_original_query"],
        pending_topic=r["pending_topic"],
        probe_asked_this_episode=r["probe_asked_this_episode"],
        episode_id=r["episode_id"],
        last_kind=r["last_kind"],
        last_explanation_mode=r["last_explanation_mode"],
        last_assistant_sentence_count=r["last_assistant_sentence_count"] or 0,
        last_retrieval_query=r["last_retrieval_query"],
        last_retrieved_chunk_ids=[str(x) for x in ids],
        lease_until=r["lease_until"],
        last_turn_at=r["last_turn_at"],
    )


def _msg(r) -> MessageRow:
    payload = r["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    citations = r["citations"]
    if isinstance(citations, str):
        citations = json.loads(citations)
    return MessageRow(
        id=r["id"],
        conversation_id=r["conversation_id"],
        role=r["role"],
        content=r["content"],
        intent=r["intent"],
        topic_key=r["topic_key"],
        explanation_mode=r["explanation_mode"],
        response_kind=r["response_kind"],
        citations=citations or [],
        payload=payload,
        route_reason=r["route_reason"],
        client_turn_id=r["client_turn_id"],
        created_at=r["created_at"],
    )


class PostgresConversationRepository:
    def __init__(self, pool: asyncpg.Pool, lease_seconds: int = 45):
        self.pool = pool
        self.lease_seconds = lease_seconds

    @classmethod
    async def connect(cls, database_url: str, lease_seconds: int = 45) -> PostgresConversationRepository:
        pool = await asyncpg.create_pool(_dsn(database_url), min_size=1, max_size=8)
        repo = cls(pool, lease_seconds)
        await repo.ensure_schema()
        return repo

    async def aclose(self) -> None:
        await self.pool.close()

    async def ensure_schema(self) -> None:
        async with self.pool.acquire() as conn:
            exists = await conn.fetchval("SELECT to_regclass('public.users')")
            if exists:
                return
            sql = SCHEMA_PATH.read_text(encoding="utf-8")
            await conn.execute(sql)

    async def health(self) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def upsert_user(self, external_id: str) -> UserRow:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, external_id)
                VALUES ($1, $2)
                ON CONFLICT (external_id) DO UPDATE SET updated_at = now()
                RETURNING id, external_id, default_level
                """,
                uuid4(),
                external_id,
            )
            return _user(row)

    async def get_user(self, external_id: str) -> UserRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, external_id, default_level FROM users WHERE external_id = $1",
                external_id,
            )
            return _user(row) if row else None

    async def get_user_by_id(self, user_id: UUID) -> UserRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, external_id, default_level FROM users WHERE id = $1",
                user_id,
            )
            return _user(row) if row else None

    async def skill_map(self, user_id: UUID) -> dict[str, dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT topic_key, level, confidence, source, probe_consumed,
                       cooldown_until_turn, last_level_change_turn
                FROM skill_levels WHERE user_id = $1
                """,
                user_id,
            )
        return {
            r["topic_key"]: {
                "level": r["level"],
                "confidence": r["confidence"],
                "source": r["source"],
                "probe_consumed": r["probe_consumed"],
                "cooldown_until_turn": r["cooldown_until_turn"],
                "last_level_change_turn": r["last_level_change_turn"],
            }
            for r in rows
        }

    async def get_conversation(self, conv_id: UUID) -> ConversationRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM conversations WHERE id = $1", conv_id)
            return _conv(row) if row else None

    async def get_conversation_by_session(self, user_id: UUID, session_id: str) -> ConversationRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM conversations WHERE user_id = $1 AND session_id = $2 ORDER BY started_at DESC LIMIT 1",
                user_id,
                session_id,
            )
            return _conv(row) if row else None

    async def insert_conversation(self, conv_id: UUID, user_id: UUID, session_id: str) -> ConversationRow:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (id, user_id, session_id)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                conv_id,
                user_id,
                session_id,
            )
            return _conv(row)

    async def get_idempotency(self, client_turn_id: UUID) -> IdempotencyRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM idempotency_keys WHERE client_turn_id = $1",
                client_turn_id,
            )
        if not row:
            return None
        payload = row["response_json"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return IdempotencyRow(
            client_turn_id=row["client_turn_id"],
            conversation_id=row["conversation_id"],
            status=row["status"],
            response_json=payload,
            http_status=row["http_status"],
            created_at=row["created_at"],
        )

    async def assistant_for_turn(self, client_turn_id: UUID) -> MessageRow | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM messages
                WHERE client_turn_id = $1 AND role = 'assistant'
                ORDER BY created_at DESC LIMIT 1
                """,
                client_turn_id,
            )
            return _msg(row) if row else None

    async def acquire_lease(self, conv_id: UUID) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE conversations
                SET lease_until = now() + ($2 * interval '1 second')
                WHERE id = $1 AND (lease_until IS NULL OR lease_until < now())
                RETURNING id
                """,
                conv_id,
                self.lease_seconds,
            )
            return row is not None

    async def clear_lease(self, conv_id: UUID) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE conversations SET lease_until = NULL WHERE id = $1", conv_id)

    async def insert_processing(self, client_turn_id: UUID, conv_id: UUID) -> str | None:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO idempotency_keys (client_turn_id, conversation_id, status)
                    VALUES ($1, $2, 'processing')
                    """,
                    client_turn_id,
                    conv_id,
                )
            except asyncpg.UniqueViolationError:
                return "turn_in_flight"
        return None

    async def finish_idempotency(
        self, client_turn_id: UUID, status: str, response_json: dict, http_status: int
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE idempotency_keys
                SET status = $2::idempotency_status, response_json = $3::jsonb, http_status = $4
                WHERE client_turn_id = $1
                """,
                client_turn_id,
                status,
                json.dumps(response_json),
                http_status,
            )

    async def upsert_skill(self, user_id: UUID, topic_key: str, **kwargs) -> SkillRow:
        level = kwargs.get("level", "beginner")
        source = kwargs.get("source", "assessor")
        if source not in VALID_SOURCES:
            source = "assessor"
        conf = float(kwargs.get("confidence") or 0)
        consumed = bool(kwargs.get("probe_consumed", True))
        last_change = int(kwargs.get("last_level_change_turn") or 0)
        cooldown = int(kwargs.get("cooldown_until_turn") or 0)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO skill_levels (
                  user_id, topic_key, level, confidence, source,
                  probe_consumed, last_level_change_turn, cooldown_until_turn
                ) VALUES ($1, $2, $3::user_level, $4, $5::level_source, $6, $7, $8)
                ON CONFLICT (user_id, topic_key) DO UPDATE SET
                  level = EXCLUDED.level,
                  confidence = EXCLUDED.confidence,
                  source = EXCLUDED.source,
                  probe_consumed = EXCLUDED.probe_consumed,
                  last_level_change_turn = EXCLUDED.last_level_change_turn,
                  cooldown_until_turn = EXCLUDED.cooldown_until_turn,
                  updated_at = now()
                RETURNING *
                """,
                user_id,
                topic_key,
                level,
                conf,
                source,
                consumed,
                last_change,
                cooldown,
            )
        return SkillRow(
            user_id=row["user_id"],
            topic_key=row["topic_key"],
            level=row["level"],
            confidence=row["confidence"],
            source=row["source"],
            probe_consumed=row["probe_consumed"],
            last_level_change_turn=row["last_level_change_turn"],
            cooldown_until_turn=row["cooldown_until_turn"],
            updated_at=row["updated_at"],
        )

    async def add_level_event(self, event: dict) -> None:
        uid = event.get("user_id")
        try:
            user_uuid = UUID(str(uid))
        except (ValueError, TypeError):
            return
        conv = event.get("conversation_id")
        conv_uuid = None
        if conv:
            try:
                conv_uuid = UUID(str(conv))
            except (ValueError, TypeError):
                conv_uuid = None
        reason = event.get("reason") or "assessor"
        to_level = event.get("to_level") or "beginner"
        from_level = event.get("from_level") or "unknown"
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO level_events (
                  id, user_id, conversation_id, topic_key, from_level, to_level,
                  reason, probe_question, probe_answer, confidence
                ) VALUES ($1, $2, $3, $4, $5::user_level, $6::user_level, $7, $8, $9, $10)
                """,
                UUID(event["id"]) if event.get("id") else uuid4(),
                user_uuid,
                conv_uuid,
                event.get("topic_key") or "misc",
                from_level,
                to_level,
                reason,
                event.get("probe_question"),
                event.get("probe_answer"),
                event.get("confidence"),
            )

    async def add_messages(self, rows: list[MessageRow]) -> None:
        async with self.pool.acquire() as conn:
            for m in rows:
                role = m.role if m.role in VALID_ROLES else "user"
                intent = m.intent if m.intent in VALID_INTENTS else None
                mode = m.explanation_mode if m.explanation_mode in VALID_MODES else None
                kind = m.response_kind if m.response_kind in VALID_KINDS else None
                await conn.execute(
                    """
                    INSERT INTO messages (
                      id, conversation_id, role, content, intent, topic_key,
                      explanation_mode, response_kind, citations, payload,
                      route_reason, client_turn_id
                    ) VALUES (
                      $1, $2, $3::message_role, $4, $5::intent_type, $6,
                      $7::explanation_mode, $8::response_kind, $9::jsonb, $10::jsonb,
                      $11, $12
                    )
                    """,
                    m.id,
                    m.conversation_id,
                    role,
                    m.content,
                    intent,
                    m.topic_key,
                    mode,
                    kind,
                    json.dumps(m.citations or []),
                    json.dumps(m.payload) if m.payload is not None else None,
                    m.route_reason,
                    m.client_turn_id,
                )

    async def update_conversation(self, conv_id: UUID, **kwargs) -> None:
        mapping = {
            "awaiting_probe": "awaiting_probe",
            "probe_asked_this_episode": "probe_asked_this_episode",
            "pending_original_query": "pending_original_query",
            "pending_topic": "pending_topic",
            "last_kind": "last_kind",
            "last_explanation_mode": "last_explanation_mode",
            "last_assistant_sentence_count": "last_assistant_sentence_count",
            "last_retrieval_query": "last_retrieval_query",
            "last_retrieved_chunk_ids": "last_retrieved_chunk_ids",
            "turn_index": "turn_index",
            "episode_id": "episode_id",
        }
        sets = ["last_turn_at = now()"]
        args: list = [conv_id]
        i = 2
        for k, col in mapping.items():
            if k not in kwargs:
                continue
            val = kwargs[k]
            if col == "last_kind":
                sets.append(f"{col} = ${i}::response_kind")
            elif col == "last_explanation_mode":
                sets.append(f"{col} = ${i}::explanation_mode")
            elif col == "last_retrieved_chunk_ids":
                val = _uuids(val)
                sets.append(f"{col} = ${i}::uuid[]")
            else:
                sets.append(f"{col} = ${i}")
            args.append(val)
            i += 1
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE conversations SET {', '.join(sets)} WHERE id = $1",
                *args,
            )

    async def list_messages(self, conv_id: UUID) -> list[MessageRow]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM messages WHERE conversation_id = $1 ORDER BY created_at",
                conv_id,
            )
        return [_msg(r) for r in rows]

    async def recent_events(self, user_id: UUID, limit: int = 10) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM level_events WHERE user_id = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                user_id,
                limit,
            )
        out = []
        for r in rows:
            out.append({k: r[k] for k in r.keys()})
        return list(reversed(out))
