"""Schema dữ liệu.

- Nhóm `LLM*`: đầu ra có cấu trúc gửi cho provider. Cố ý KHÔNG đặt ràng buộc
  (min/max, dict tự do) để tương thích structured output của OpenAI/Claude/Gemini;
  ràng buộc được kiểm lại bằng code sau khi nhận.
- Nhóm còn lại: trạng thái nội bộ và hợp đồng HTTP (§5 tài liệu backend).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Level = Literal["L1", "L2", "L3", "L4", "L5"]
Style = Literal["vi_du", "ngan_gon", "chi_tiet"]
GapType = Literal["thieu_nen", "can_vi_du", "qua_dai", "hieu_sai", "khong_ro"]
BlockType = Literal["p", "prereq", "analogy", "map", "steps", "key", "limit", "outside", "formula"]
Understanding = Literal["chua", "biet_so", "hieu_ro"]
Kind = Literal["explain", "survey", "no_source", "out_of_scope", "injection", "help", "handoff"]

LEVELS: list[str] = ["L1", "L2", "L3", "L4", "L5"]
LEVEL_LABEL = {"L1": "Làm quen", "L2": "Cơ bản", "L3": "Hiểu bản chất", "L4": "Kỹ thuật", "L5": "Chuyên sâu"}
STYLE_LABEL = {"vi_du": "Ví dụ đời thường", "ngan_gon": "Ngắn gọn từng bước", "chi_tiet": "Chi tiết kỹ thuật"}
UNDERSTANDING_LABEL = {"chua": "Chưa", "biet_so": "Biết sơ", "hieu_ro": "Hiểu rõ"}


# ---------------------------------------------------------------- LLM output
class LLMDecision(BaseModel):
    concept: str
    gap_type: GapType
    level: Level
    style: Style
    missing_concepts: list[str]
    preferred_analogy: Optional[str]
    misconception_suspected: Optional[str]
    confidence: float
    need_survey: bool
    in_scope: bool
    source_ids: list[str]
    reason_for_user: str


class LLMBlock(BaseModel):
    t: BlockType
    title: Optional[str]
    html: Optional[str]
    rows: Optional[list[list[str]]]
    items: Optional[list[str]]
    src: list[str]
    claims: list[str]


class LLMAnswer(BaseModel):
    blocks: list[LLMBlock]
    analogy_id: Optional[str]
    summary_for_next_turn: str


class ClaimCheck(BaseModel):
    id: str
    ok: bool
    evidence: str


class LLMJudge(BaseModel):
    claims: list[ClaimCheck]
    misconception_hits: list[str]
    unsupported_sentences: list[str]
    verdict: Literal["pass", "fail"]


class LLMBaselineAnswer(BaseModel):
    text: str


# ---------------------------------------------------------------- internal
class Block(BaseModel):
    t: BlockType
    title: Optional[str] = None
    html: Optional[str] = None
    rows: Optional[list[list[str]]] = None
    items: Optional[list[str]] = None
    src: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)


class Decision(BaseModel):
    kind: Kind
    concept: Optional[str] = None
    gap_type: GapType = "khong_ro"
    level: Level = "L3"
    style: Style = "ngan_gon"
    missing_concepts: list[str] = Field(default_factory=list)
    prereq_first: Optional[str] = None
    preferred_analogy: Optional[str] = None
    misconception_suspected: Optional[str] = None
    confidence: float = 0.5
    need_survey: bool = False
    in_scope: bool = True
    source_ids: list[str] = Field(default_factory=list)
    reason_for_user: str = ""
    weighted_sum: bool = False
    full: bool = False
    alt_example: bool = False
    decided_by: str = "rules"  # rules | llm | llm+policy


class FidelityReport(BaseModel):
    covered: int = 0
    total: int = 0
    missing_claims: list[str] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    unlabeled: int = 0
    outside: int = 0
    bad_sources: list[str] = Field(default_factory=list)
    ability_labels: list[str] = Field(default_factory=list)
    too_long: bool = False
    judge_verdict: Optional[str] = None
    unsupported: list[str] = Field(default_factory=list)
    ok: bool = False

    def errors(self) -> list[str]:
        out = []
        if self.missing_claims:
            out.append("Thiếu ý chính: " + ", ".join(self.missing_claims))
        if self.missing_terms:
            out.append("Thiếu thuật ngữ gốc: " + ", ".join(self.missing_terms))
        if self.misconceptions:
            out.append("Có câu hiểu lệch: " + ", ".join(self.misconceptions))
        if self.unlabeled:
            out.append(f"{self.unlabeled} block không có nguồn và không gắn nhãn outside")
        if self.bad_sources:
            out.append("Nguồn không hợp lệ: " + ", ".join(self.bad_sources))
        if self.ability_labels:
            out.append("Có câu nhận xét năng lực học viên")
        if self.too_long:
            out.append("Quá dài so với mức")
        if self.unsupported:
            out.append("Câu không có căn cứ: " + " | ".join(self.unsupported[:3]))
        return out


class Answer(BaseModel):
    key: str = ""
    blocks: list[Block]
    analogy_id: Optional[str] = None
    summary_for_next_turn: str = ""


class Notice(BaseModel):
    text: str
    kind: Literal["up", "down", "info"] = "info"
    event_ids: list[int] = Field(default_factory=list)


class CheckOption(BaseModel):
    k: str
    text: str


class CheckQuestion(BaseModel):
    id: str
    concept: str
    question: str
    options: list[CheckOption]
    src: list[str] = Field(default_factory=list)


class SurveyRow(BaseModel):
    concept: str
    term: str
    vi_name: str
    level: Optional[Understanding] = None


class SurveyPayload(BaseModel):
    concept: str
    term: str
    rows: list[SurveyRow]
    style: Optional[Style] = None
    reason: str


class ScopePayload(BaseModel):
    message: str
    term: Optional[str] = None
    nearest: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class Meta(BaseModel):
    request_id: str
    prompt_version: str
    provider: str
    latency_ms: int = 0
    fallback: Optional[str] = None
    cached: bool = False
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ChatResponse(BaseModel):
    kind: Kind
    decision: Optional[Decision] = None
    answer: Optional[Answer] = None
    fidelity: Optional[FidelityReport] = None
    sources: list[str] = Field(default_factory=list)
    survey: Optional[SurveyPayload] = None
    scope: Optional[ScopePayload] = None
    handoff: Optional[str] = None
    notices: list[Notice] = Field(default_factory=list)
    meta: Optional[Meta] = None


# ---------------------------------------------------------------- HTTP requests
class BaseReq(BaseModel):
    user_id: str = "demo-trung-binh"
    session_id: str = "s-default"
    lesson_id: str = "day01-self-attention"


class ChatRequest(BaseReq):
    text: str
    selection: str = ""
    action: Literal["ask", "confused"] = "ask"
    concept_hint: Optional[str] = None


class SurveyRequest(BaseReq):
    concept: str
    levels: dict[str, Understanding] = Field(default_factory=dict)
    style: Optional[Style] = None
    note: str = ""
    skipped: bool = False


class AdjustRequest(BaseReq):
    concept: str
    kind: Literal["easier", "deeper", "shorter", "example"]


class FeedbackRequest(BaseReq):
    concept: str
    value: Literal["up", "down"]
    reason: Optional[Literal["hard", "long", "wrong"]] = None


class CheckAnswerRequest(BaseReq):
    concept: str
    question_id: str
    answer: str


class ProfileUpdate(BaseModel):
    user_id: str
    concept: Optional[str] = None
    level: Optional[Understanding] = None
    memory_on: Optional[bool] = None
    preferred_style: Optional[Style] = None
    clear_style: bool = False


class UndoRequest(BaseModel):
    user_id: str
    event_ids: list[int]


class UserReq(BaseModel):
    user_id: str


class HandoffRequest(BaseReq):
    concept: Optional[str] = None


class FeedbackResult(BaseModel):
    next: Literal["check", "retry", "handoff", "report", "done"]
    notices: list[Notice] = Field(default_factory=list)
    check: Optional[CheckQuestion] = None
    response: Optional[ChatResponse] = None
    handoff: Optional[str] = None


class CheckResult(BaseModel):
    correct: bool
    right: str
    fix_html: Optional[str] = None
    misconception: Optional[str] = None
    src: list[str] = Field(default_factory=list)
    next: Literal["done", "retry", "handoff"]
    notices: list[Notice] = Field(default_factory=list)
    response: Optional[ChatResponse] = None
    handoff: Optional[str] = None
