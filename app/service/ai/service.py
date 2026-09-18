from __future__ import annotations

from typing import Any

from app.config import Settings
from app.service.ai.embeddings import HashingEmbedder
from app.service.ai.tutor import TutorEngine


class AIService:
    """
    AI service layer — điểm vào duy nhất cho LLM + embedding.

    Domain / graph chỉ gọi port này. Đổi provider = đổi adapter trong layer này.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._embedder = HashingEmbedder(settings.embedding_dim)
        self._tutor = TutorEngine(settings)

    @property
    def live(self) -> bool:
        return self._tutor.live

    async def embed(self, text: str) -> list[float]:
        return await self._embedder.embed(text)

    async def explain(
        self,
        *,
        mode: str,
        topic: str,
        query: str,
        excerpts: list[dict],
    ) -> dict[str, Any]:
        return await self._tutor.explain(
            mode=mode, topic=topic, query=query, excerpts=excerpts
        )

    async def generate_probe(
        self,
        *,
        topic: str,
        query: str,
        history: str,
        excerpts: list[dict],
    ) -> dict | None:
        return await self._tutor.generate_probe(
            topic=topic, query=query, history=history, excerpts=excerpts
        )

    async def aclose(self) -> None:
        await self._tutor.aclose()
