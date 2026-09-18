from __future__ import annotations

import hashlib
import math
import re


_TOKEN = re.compile(r"[a-z0-9à-ỹ]+", re.I)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def embed_text(text: str, dim: int = 1536) -> list[float]:
    vec = [0.0] * dim
    for tok in tokenize(text):
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b, strict=False)))
