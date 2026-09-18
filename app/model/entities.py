from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRow:
    id: UUID
    external_id: str
    default_level: str = "unknown"


@dataclass
class SkillRow:
    user_id: UUID
    topic_key: str
    level: str
    confidence: float = 0.0
    source: str = "assessor"
    probe_consumed: bool = False
    last_level_change_turn: int = 0
    cooldown_until_turn: int = 0
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ConversationRow:
    id: UUID
    user_id: UUID
    session_id: str
    turn_index: int = 0
    awaiting_probe: bool = False
    pending_original_query: str | None = None
    pending_topic: str | None = None
    probe_asked_this_episode: bool = False
    episode_id: UUID | None = None
    last_kind: str | None = None
    last_explanation_mode: str | None = None
    last_assistant_sentence_count: int = 0
    last_retrieval_query: str | None = None
    last_retrieved_chunk_ids: list[str] = field(default_factory=list)
    lease_until: datetime | None = None
    last_turn_at: datetime = field(default_factory=utcnow)


@dataclass
class MessageRow:
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    intent: str | None = None
    topic_key: str | None = None
    explanation_mode: str | None = None
    response_kind: str | None = None
    citations: list = field(default_factory=list)
    payload: dict | None = None
    route_reason: str | None = None
    client_turn_id: UUID | None = None
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class IdempotencyRow:
    client_turn_id: UUID
    conversation_id: UUID
    status: str
    response_json: dict | None = None
    http_status: int | None = None
    created_at: datetime = field(default_factory=utcnow)
