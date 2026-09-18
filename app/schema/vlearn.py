from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["L1", "L2", "L3", "L4", "L5"]
Style = Literal["vi_du", "ngan_gon", "chi_tiet"]
Understanding = Literal["chua", "biet_so", "hieu_ro"]
Kind = Literal["explain", "survey", "no_source", "out_of_scope", "injection", "help", "handoff"]


class VLearnChatRequest(BaseModel):
    user_id: str = "demo-trung-binh"
    session_id: str = "s-default"
    lesson_id: str = "day01-self-attention"
    text: str = ""
    selection: str = ""
    action: Literal["ask", "confused"] = "ask"
    concept_hint: Optional[str] = None


class VLearnSurveyRequest(BaseModel):
    user_id: str
    session_id: str
    concept: str
    levels: dict[str, Understanding] = Field(default_factory=dict)
    style: Optional[Style] = None
    note: str = ""
    skipped: bool = False


class VLearnAdjustRequest(BaseModel):
    user_id: str
    session_id: str
    concept: str
    kind: Literal["easier", "deeper", "shorter", "example"]


class VLearnFeedbackRequest(BaseModel):
    user_id: str
    session_id: str
    concept: str
    value: Literal["up", "down"]
    reason: Optional[Literal["hard", "long", "wrong"]] = None


class VLearnCheckRequest(BaseModel):
    user_id: str
    session_id: str
    concept: str
    question_id: str
    answer: str


class VLearnHandoffRequest(BaseModel):
    user_id: str
    session_id: str
    concept: Optional[str] = None


class VLearnProfileUpdate(BaseModel):
    user_id: str
    concept: Optional[str] = None
    level: Optional[Understanding] = None
    memory_on: Optional[bool] = None
    preferred_style: Optional[Style] = None
    clear_style: bool = False


LEVEL_FROM_SKILL = {
    "beginner": "L1",
    "intermediate": "L3",
    "advanced": "L4",
    "unknown": "L2",
}
STYLE_FROM_SKILL = {
    "beginner": "vi_du",
    "intermediate": "ngan_gon",
    "advanced": "chi_tiet",
    "unknown": "vi_du",
}
SKILL_FROM_UNDERSTANDING = {
    "chua": "beginner",
    "biet_so": "intermediate",
    "hieu_ro": "advanced",
}
UNDERSTANDING_FROM_SKILL = {
    "beginner": "chua",
    "intermediate": "biet_so",
    "advanced": "hieu_ro",
}
