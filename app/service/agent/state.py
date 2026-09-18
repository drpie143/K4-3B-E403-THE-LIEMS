from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages

UserLevel = Literal["unknown", "beginner", "intermediate", "advanced"]
Intent = Literal[
    "ask_concept",
    "clarify_harder",
    "ask_deeper",
    "answer_probe",
    "refuse_probe",
    "off_topic",
    "meta",
]
ExplanationMode = Literal["eli5", "slide_short", "technical"]
ResponseKind = Literal["probe", "explanation", "redirect", "retrieval_miss", "error", "meta"]
RouteKey = Literal[
    "probe",
    "score",
    "persist_then_adapt",
    "adapt",
    "standard",
    "redirect",
    "miss",
]
TutorNode = Literal["tutor_adaptive", "tutor_standard"]


class RetrievedChunk(TypedDict, total=False):
    chunk_id: str
    lecture_id: str
    slide_page: int
    text: str
    score: float


class SkillEntry(TypedDict, total=False):
    level: UserLevel
    confidence: float
    source: str
    probe_consumed: bool
    cooldown_until_turn: int
    last_level_change_turn: int


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str
    conversation_id: str
    turn_id: str
    client_turn_id: str
    turn_index: int
    user_message: str
    context_lecture_id: str | None
    context_slide_page: int | None
    highlighted_text: str | None

    current_topic: str | None
    skill_map: dict[str, SkillEntry]
    user_level: UserLevel
    default_level: UserLevel
    probe_consumed_for_topic: bool

    regex_intent: Intent | None
    intent: Intent | None
    intent_confidence: float
    intent_source: Literal["regex", "llm", "forced"]
    learning_bottleneck: bool
    length_only: bool
    proposed_level_delta: Literal[-1, 0, 1]
    proposed_level: UserLevel | None

    last_kind: ResponseKind | None
    last_assistant_mode: ExplanationMode | None
    last_assistant_sentence_count: int

    retrieved_docs: list[RetrievedChunk]
    retrieval_query: str | None
    retrieval_skipped: bool
    last_retrieval_query: str | None
    last_retrieved_chunk_ids: list[str]

    probe_question: str | None
    probe_choices: list[dict] | None
    probe_answer: str | None
    probe_asked_this_episode: bool
    awaiting_probe_answer: bool
    pending_original_query: str | None
    pending_topic: str | None
    episode_id: str | None

    explanation_mode: ExplanationMode | None
    tutor_node: TutorNode | None
    draft_answer: str | None
    final_answer: str | None
    citations: list[RetrievedChunk]
    validator_ok: bool
    validator_issues: list[str]
    rewrite_count: int

    response_kind: ResponseKind | None
    error: str | None
    route_reason: str
    llm_hops: int
    flags_dump_first: bool
    flags_adaptive_probes: bool
    user_pk: str | None


TURN_RESET_FIELDS: tuple[str, ...] = (
    "user_message",
    "turn_id",
    "client_turn_id",
    "regex_intent",
    "intent",
    "intent_confidence",
    "intent_source",
    "learning_bottleneck",
    "length_only",
    "proposed_level_delta",
    "proposed_level",
    "retrieved_docs",
    "retrieval_query",
    "retrieval_skipped",
    "draft_answer",
    "final_answer",
    "citations",
    "validator_ok",
    "validator_issues",
    "rewrite_count",
    "response_kind",
    "error",
    "route_reason",
    "llm_hops",
    "probe_question",
    "probe_choices",
    "probe_answer",
    "explanation_mode",
    "tutor_node",
    "current_topic",
    "flags_dump_first",
    "flags_adaptive_probes",
)

TURN_RESET_DEFAULTS: dict = {
    "regex_intent": None,
    "intent": None,
    "intent_confidence": 0.0,
    "intent_source": "regex",
    "learning_bottleneck": False,
    "length_only": False,
    "proposed_level_delta": 0,
    "proposed_level": None,
    "retrieved_docs": [],
    "retrieval_query": None,
    "retrieval_skipped": False,
    "draft_answer": None,
    "final_answer": None,
    "citations": [],
    "validator_ok": True,
    "validator_issues": [],
    "rewrite_count": 0,
    "response_kind": None,
    "error": None,
    "route_reason": "",
    "llm_hops": 0,
    "probe_question": None,
    "probe_choices": None,
    "probe_answer": None,
    "explanation_mode": None,
    "tutor_node": None,
    "current_topic": None,
}
