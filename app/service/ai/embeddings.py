from __future__ import annotations

from app.repository.hashing import embed_text


class HashingEmbedder:
    """Deterministic local embed — mặc định MVP / pytest, không gọi mạng."""

    def __init__(self, dim: int = 1536):
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        return embed_text(text, self.dim)
