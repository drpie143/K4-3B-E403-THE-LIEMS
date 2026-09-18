from __future__ import annotations

from app.repository.hashing import embed_text
from app.repository.seed import CHUNKS
from app.repository.vector import MemoryVectorStore, _lexical


class QdrantVectorStore:
    COLLECTION = "vlearn_chunks"

    def __init__(self, url: str, dim: int = 1536):
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import Distance, PointStruct, VectorParams

        self.dim = dim
        self._client = QdrantClient(url=url, timeout=3)
        self._PointStruct = PointStruct
        names = {c.name for c in self._client.get_collections().collections}
        if self.COLLECTION not in names:
            self._client.create_collection(
                self.COLLECTION,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        points = []
        for i, c in enumerate(CHUNKS):
            vec = embed_text(c["text"], dim)
            points.append(
                PointStruct(
                    id=i + 1,
                    vector=vec,
                    payload={
                        "chunk_id": c["chunk_id"],
                        "lecture_id": c["lecture_id"],
                        "slide_page": c["slide_page"],
                        "text": c["text"],
                    },
                )
            )
        self._client.upsert(self.COLLECTION, points=points)
        self._fallback = MemoryVectorStore(dim)

    async def health(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    async def search(
        self,
        vector: list[float],
        k: int = 6,
        lecture_id: str | None = None,
        query_text: str | None = None,
    ) -> list[dict]:
        try:
            hits = self._client.search(
                collection_name=self.COLLECTION,
                query_vector=vector,
                limit=k,
            )
            out = []
            for h in hits:
                p = h.payload or {}
                lex = _lexical(query_text or "", p.get("text") or "") if query_text else 0.0
                out.append(
                    {
                        "chunk_id": p.get("chunk_id"),
                        "lecture_id": p.get("lecture_id"),
                        "slide_page": p.get("slide_page"),
                        "text": p.get("text"),
                        "score": max(float(h.score or 0), lex),
                    }
                )
            out.sort(key=lambda x: x["score"], reverse=True)
            return out[:k]
        except Exception:
            return await self._fallback.search(vector, k=k, lecture_id=lecture_id, query_text=query_text)

    async def get_by_ids(self, ids: list[str]) -> list[dict]:
        return await self._fallback.get_by_ids(ids)


async def connect_qdrant(url: str, dim: int) -> QdrantVectorStore | None:
    try:
        store = QdrantVectorStore(url, dim)
        if await store.health():
            return store
    except Exception:
        return None
    return None
