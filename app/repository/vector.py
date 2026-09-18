from __future__ import annotations

from app.repository.hashing import cosine, embed_text, tokenize
from app.repository.seed import CHUNKS


def _lexical(query: str, text: str) -> float:
    qt = set(tokenize(query))
    if not qt:
        return 0.0
    tt = set(tokenize(text))
    return len(qt & tt) / len(qt)


class MemoryVectorStore:
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self._items: list[dict] = []
        for c in CHUNKS:
            rec = dict(c)
            rec["vector"] = embed_text(c["text"], dim)
            self._items.append(rec)

    async def health(self) -> bool:
        return True

    async def search(
        self,
        vector: list[float],
        k: int = 6,
        lecture_id: str | None = None,
        query_text: str | None = None,
    ) -> list[dict]:
        scored = []
        for it in self._items:
            lex = _lexical(query_text or "", it["text"]) if query_text else 0.0
            score = max(cosine(vector, it["vector"]), lex)
            scored.append(
                {
                    "chunk_id": it["chunk_id"],
                    "lecture_id": it["lecture_id"],
                    "slide_page": it["slide_page"],
                    "text": it["text"],
                    "score": score,
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    async def get_by_ids(self, ids: list[str]) -> list[dict]:
        want = set(ids)
        out = []
        for it in self._items:
            if it["chunk_id"] in want:
                out.append(
                    {
                        "chunk_id": it["chunk_id"],
                        "lecture_id": it["lecture_id"],
                        "slide_page": it["slide_page"],
                        "text": it["text"],
                        "score": 1.0,
                    }
                )
        return out
