from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    lecture_id: str | None = None
    slide_page: int | None = None
    highlighted_text: str | None = None


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    client_turn_id: UUID
    conversation_id: UUID | None = None
    message: str | None = ""
    context: ChatContext | None = None


class Choice(BaseModel):
    id: str
    text: str
    maps_to_level: str | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    turn_id: UUID
    kind: Literal["probe", "explanation", "redirect", "retrieval_miss", "error", "meta"]
    content: str
    choices: list[Choice] = Field(default_factory=list)
    user_level: str
    topic_key: str
    explanation_mode: str | None = None
    citations: list[Any] = Field(default_factory=list)
    route_reason: str = ""
