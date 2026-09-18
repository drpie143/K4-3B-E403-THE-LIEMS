from __future__ import annotations

import json
from functools import lru_cache

import yaml

from app.config import repo_root

ROOT = repo_root()
APP = ROOT / "app"
CARDS_DIR = APP / "data" / "cards"
SOURCES_YAML = CARDS_DIR / "_sources.yaml"
CHUNKS_LOCAL = APP / "data" / "chunks.local.json"
PERSONAS_YAML = APP / "data" / "personas.yaml"


class CardRepository:
    def __init__(self) -> None:
        self.cards = self._load_cards()
        self.sources = self._load_sources()
        self.personas = self._load_personas()
        self.local_chunks = self._load_local_chunks()

    @staticmethod
    def _load_cards() -> dict[str, dict]:
        out = {}
        if not CARDS_DIR.is_dir():
            return out
        for path in CARDS_DIR.glob("*.yaml"):
            if path.name.startswith("_"):
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            cid = data.get("id") or path.stem
            if data.get("reviewed") is False:
                continue
            out[cid] = data
        return out

    @staticmethod
    def _load_sources() -> dict:
        if not SOURCES_YAML.exists():
            return {"lessons": {}, "sources": {}}
        return yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8")) or {}

    @staticmethod
    def _load_personas() -> dict:
        if not PERSONAS_YAML.exists():
            return {}
        return yaml.safe_load(PERSONAS_YAML.read_text(encoding="utf-8")) or {}

    @staticmethod
    def _load_local_chunks() -> dict[str, dict]:
        if not CHUNKS_LOCAL.exists():
            return {}
        try:
            raw = json.loads(CHUNKS_LOCAL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if isinstance(raw, list):
            return {c["id"]: c for c in raw if isinstance(c, dict) and "id" in c}
        if isinstance(raw, dict):
            return raw
        return {}

    def get(self, concept_id: str | None) -> dict | None:
        if not concept_id:
            return None
        return self.cards.get(concept_id)

    def source(self, source_id: str) -> dict | None:
        local = self.local_chunks.get(source_id)
        if local:
            text = local.get("text") or local.get("summary") or ""
            return {
                "id": source_id,
                "section": local.get("section") or "",
                "text": text,
                "mode": "local",
            }
        meta = (self.sources.get("sources") or {}).get(source_id)
        if not meta:
            return None
        return {
            "id": source_id,
            "section": meta.get("section") or "",
            "text": meta.get("summary") or "",
            "mode": "summary",
        }

    def checks(self, concept_id: str) -> list[dict]:
        card = self.get(concept_id) or {}
        return list(card.get("checks") or [])


@lru_cache
def get_card_repository() -> CardRepository:
    return CardRepository()
