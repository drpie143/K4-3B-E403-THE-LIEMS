"""Nạp và kiểm tra thẻ khái niệm (YAML) + sổ đăng ký nguồn."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schemas import Block


class CardError(ValueError):
    pass


@dataclass
class Card:
    id: str
    term: str
    vi_name: str
    lesson_id: str
    reviewed: bool
    aliases: list[str]
    prerequisites: list[str]
    required_terms: list[str]
    core_claims: list[dict]
    approved_analogies: list[dict]
    analogy_limits: list[str]
    misconceptions: list[dict]
    outside_lesson_notes: list[str]
    primer: dict
    checks: list[dict]
    templates: dict[str, list[dict]]
    extras: dict[str, dict] = field(default_factory=dict)
    aspects: dict[str, list[dict]] = field(default_factory=dict)  # trả lời riêng theo khía cạnh hỏi

    @property
    def claim_ids(self) -> list[str]:
        return [c["id"] for c in self.core_claims]

    @property
    def source_ids(self) -> list[str]:
        ids: list[str] = []
        for c in self.core_claims + self.approved_analogies:
            ids += c.get("src", [])
        ids += self.primer.get("src", [])
        return list(dict.fromkeys(ids))

    @property
    def analogy_ids(self) -> list[str]:
        return [a["id"] for a in self.approved_analogies]

    def template(self, key: str) -> list[Block] | None:
        raw = self.templates.get(key)
        return [Block(**b) for b in raw] if raw else None

    def extra(self, key: str) -> Block | None:
        raw = self.extras.get(key)
        return Block(**raw) if raw else None

    def for_prompt(self) -> dict[str, Any]:
        """Phần thẻ gửi cho LLM (không gồm đáp án câu kiểm tra, không gồm mẫu trả lời)."""
        return {
            "id": self.id,
            "term": self.term,
            "vi_name": self.vi_name,
            "prerequisites": self.prerequisites,
            "required_terms": self.required_terms,
            "core_claims": self.core_claims,
            "approved_analogies": self.approved_analogies,
            "analogy_limits": self.analogy_limits,
            "misconceptions": [{"id": m["id"], "text": m["text"]} for m in self.misconceptions],
            "outside_lesson_notes": self.outside_lesson_notes,
        }


class CardStore:
    def __init__(self, cards_dir: Path, include_unreviewed: bool = False):
        self.dir = Path(cards_dir)
        reg = yaml.safe_load((self.dir / "_sources.yaml").read_text(encoding="utf-8"))
        self.lessons: dict[str, dict] = reg.get("lessons", {})
        self.sources: dict[str, dict] = reg.get("sources", {})
        self.outside_terms: dict[str, list[str]] = reg.get("outside_terms", {}) or {}
        self.cards: dict[str, Card] = {}
        for path in sorted(self.dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            card = self._build(data, path)
            if card.reviewed or include_unreviewed:
                self.cards[card.id] = card
        self.validate()

    @staticmethod
    def _build(d: dict, path: Path) -> Card:
        try:
            return Card(
                id=d["id"], term=d["term"], vi_name=d.get("vi_name", ""), lesson_id=d["lesson_id"],
                reviewed=bool(d.get("reviewed")), aliases=d.get("aliases", []),
                prerequisites=d.get("prerequisites", []), required_terms=d.get("required_terms", []),
                core_claims=d["core_claims"], approved_analogies=d.get("approved_analogies", []),
                analogy_limits=d.get("analogy_limits", []), misconceptions=d.get("misconceptions", []),
                outside_lesson_notes=d.get("outside_lesson_notes", []), primer=d.get("primer", {}),
                checks=d.get("checks", []), templates=d.get("templates", {}), extras=d.get("extras", {}),
                aspects=d.get("aspects", {}) or {},
            )
        except KeyError as exc:
            raise CardError(f"{path.name}: thiếu trường {exc}") from exc

    def validate(self) -> None:
        errors = []
        for card in self.cards.values():
            for sid in card.source_ids:
                if sid not in self.sources:
                    errors.append(f"{card.id}: nguồn {sid} không có trong _sources.yaml")
            for p in card.prerequisites:
                if p not in self.cards:
                    errors.append(f"{card.id}: khái niệm nền {p} chưa có thẻ")
            if not card.templates:
                errors.append(f"{card.id}: chưa có mẫu trả lời")
            for key, blocks in list(card.templates.items()) + list(card.aspects.items()):
                for b in blocks:
                    for sid in b.get("src", []):
                        if sid not in self.sources:
                            errors.append(f"{card.id}.{key}: nguồn {sid} không hợp lệ")
        if errors:
            raise CardError("; ".join(errors))

    def get(self, concept_id: str | None) -> Card | None:
        return self.cards.get(concept_id or "")

    def by_source(self, source_id: str) -> list[Card]:
        return [c for c in self.cards.values() if source_id in c.source_ids]

    def lesson_files(self, lesson_id: str) -> list[str]:
        return self.lessons.get(lesson_id, {}).get("transcript_files", [])

    def summary(self, source_id: str) -> str:
        return self.sources.get(source_id, {}).get("summary", "")
