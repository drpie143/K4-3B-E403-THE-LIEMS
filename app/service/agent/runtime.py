from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.repository.retriever import LectureRetriever
from app.repository.conversation import ConversationRepository
from app.service.ai.service import AIService


@dataclass
class Runtime:
    settings: Settings
    repository: ConversationRepository
    retriever: LectureRetriever
    ai: AIService


_RUNTIME: Runtime | None = None


def set_runtime(rt: Runtime) -> None:
    global _RUNTIME
    _RUNTIME = rt


def get_runtime() -> Runtime:
    if _RUNTIME is None:
        raise RuntimeError("Runtime not initialized — gọi build_container() trước.")
    return _RUNTIME
