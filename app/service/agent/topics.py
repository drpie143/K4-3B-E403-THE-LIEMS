from __future__ import annotations

import json
import re
from functools import lru_cache

from app.config import repo_root

TOPIC_PATH = repo_root() / "app" / "fixtures" / "topics.json"
SLUG_RE = re.compile(r"^[a-z0-9_]{1,64}$")


@lru_cache
def _synonyms() -> dict[str, list[str]]:
    return json.loads(TOPIC_PATH.read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    t = t.strip("_")[:64]
    return t


def resolve_topic_key(message: str, highlighted: str | None) -> str:
    syn = _synonyms()
    hay_hi = (highlighted or "").lower()
    hay_msg = (message or "").lower()
    if hay_hi:
        for key, words in syn.items():
            if any(w in hay_hi for w in words):
                return key
        s = slugify(highlighted or "")
        if s and SLUG_RE.match(s):
            return s
    for key, words in syn.items():
        if any(w in hay_msg for w in words):
            return key
    s = slugify(highlighted or message)
    if s and SLUG_RE.match(s):
        return s
    return "misc"
