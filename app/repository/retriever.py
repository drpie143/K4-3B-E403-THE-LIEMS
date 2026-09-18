from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.repository.vector import MemoryVectorStore

EmbedFn = Callable[[str], Awaitable[list[float]]]


class LectureRetriever:
    def __init__(self, store: MemoryVectorStore, embed: EmbedFn):
        self._store = store
        self._embed = embed

    async def retrieve(
        self,
        query: str,
        *,
        k: int = 6,
        lecture_id: str | None = None,
    ) -> list[dict]:
        vec = await self._embed(query)
        return await self._store.search(
            vec, k=k, lecture_id=lecture_id, query_text=query
        )

    async def get_by_ids(self, ids: list[str]) -> list[dict]:
        return await self._store.get_by_ids(ids)

    async def health(self) -> bool:
        return await self._store.health()
