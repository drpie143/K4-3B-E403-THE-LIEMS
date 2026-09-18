#!/usr/bin/env python3
"""LLM soạn NHÁP thẻ khái niệm từ các đoạn transcript → backend/cards/drafts/<id>.yaml (reviewed: false).

Người trong nhóm/TA phải đọc, sửa, chuyển sang backend/cards/ và đổi reviewed: true thì hệ thống mới dùng.
Lưu ý: script gửi nguyên văn các đoạn được chọn cho provider — chỉ chọn số đoạn tối thiểu.

Ví dụ (từ gốc repo):
    LLM_PROVIDER=openai backend/.venv/bin/python scripts/draft_cards.py --id softmax --term Softmax --sources T06-130 T06-136
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.cards import CardStore  # noqa: E402
from app.config import BACKEND_DIR, load_settings  # noqa: E402
from app.llm import make_client  # noqa: E402
from app.retrieval import Retriever  # noqa: E402


class DraftClaim(BaseModel):
    id: str
    text: str
    src: list[str]


class DraftAnalogy(BaseModel):
    id: str
    title: str
    text: str
    src: list[str]


class DraftMisconception(BaseModel):
    id: str
    text: str
    fix: str
    src: list[str]


class DraftOption(BaseModel):
    k: str
    text: str
    correct: bool
    misconception: Optional[str]


class DraftCheck(BaseModel):
    id: str
    question: str
    options: list[DraftOption]
    src: list[str]


class CardDraft(BaseModel):
    vi_name: str
    aliases: list[str]
    prerequisites: list[str]
    required_terms: list[str]
    core_claims: list[DraftClaim]
    approved_analogies: list[DraftAnalogy]
    analogy_limits: list[str]
    misconceptions: list[DraftMisconception]
    primer_html: str
    checks: list[DraftCheck]


PROMPT = """Soạn nháp thẻ khái niệm "{term}" cho trợ giảng, CHỈ dựa trên các đoạn bài giảng dưới đây.
- core_claims: 1–3 ý chính, diễn đạt lại (không chép nguyên văn), mỗi ý có src là id đoạn.
- approved_analogies: chỉ ví dụ mà giảng viên thực sự dùng trong đoạn.
- misconceptions: các cách hiểu lệch dễ gặp, kèm lời sửa (fix) có căn cứ.
- prerequisites: chỉ chọn trong {known}.
- checks: 1–2 câu trắc nghiệm 4 lựa chọn, đáp án nhiễu gắn misconception.
- Chỗ nào bài giảng nói chưa chuẩn thì KHÔNG đưa vào core_claims.
<passages>
{passages}
</passages>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--term", required=True)
    ap.add_argument("--sources", nargs="+", required=True)
    args = ap.parse_args()
    s = load_settings()
    if s.llm_provider == "fake":
        sys.exit("Cần LLM_PROVIDER thật (openai/claude/gemini) để soạn nháp.")
    cards = CardStore(s.cards_dir)
    r = Retriever(cards, s.chunks_path)
    if r.mode != "local":
        sys.exit("Chưa có data/chunks.local.json — chạy scripts/build_local_data.py trước.")
    passages = [{"id": sid, "text": r.text_for(sid, 1500)} for sid in args.sources]
    user = PROMPT.format(term=args.term, known=sorted(cards.cards), passages=json.dumps(passages, ensure_ascii=False, indent=1))
    llm = make_client(s)
    draft, usage = llm.complete_json("draft_card", "Bạn là trợ lý soạn tài liệu học tập, trả lời bằng tiếng Việt.", user, CardDraft, s.llm_model)
    data = {
        "id": args.id, "term": args.term, "vi_name": draft.vi_name, "lesson_id": "day01-self-attention",
        "reviewed": False, "reviewed_by": "", "aliases": draft.aliases, "prerequisites": draft.prerequisites,
        "required_terms": draft.required_terms, "core_claims": [c.model_dump() for c in draft.core_claims],
        "approved_analogies": [a.model_dump() for a in draft.approved_analogies],
        "analogy_limits": draft.analogy_limits,
        "misconceptions": [dict(m.model_dump(), pattern="(điền cụm không dấu để validator bắt)") for m in draft.misconceptions],
        "outside_lesson_notes": [], "primer": {"html": draft.primer_html, "src": args.sources},
        "checks": [c.model_dump() for c in draft.checks],
        "templates": {"first": []},
    }
    out = BACKEND_DIR / "cards" / "drafts" / f"{args.id}.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# NHÁP do LLM soạn — cần người duyệt, viết templates, rồi chuyển lên cards/\n" + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Đã ghi {out} · token vào {usage.input_tokens}, ra {usage.output_tokens}")


if __name__ == "__main__":
    main()
