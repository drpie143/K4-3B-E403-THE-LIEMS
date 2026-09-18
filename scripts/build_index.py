#!/usr/bin/env python3
"""Kiểm tra chỉ mục tìm kiếm và gợi ý ngưỡng RETRIEVAL_MIN_SCORE.

Chạy từ gốc repo:  backend/.venv/bin/python scripts/build_index.py
Cần chạy build_local_data.py trước để có data/chunks.local.json (nếu không sẽ dùng chế độ tóm tắt).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.cards import CardStore  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.retrieval import Retriever  # noqa: E402

# (câu hỏi, khái niệm mong đợi hoặc None nếu phải "không có nguồn")
PROBES = [
    ("self-attention là gì", "self_attention"),
    ("query key value khác nhau thế nào", "self_attention"),
    ("vì sao nó là con mèo không phải cái bàn", "self_attention"),
    ("multi-head attention thầy bói xem voi", "multi_head"),
    ("vector embedding là gì", "vector"),
    ("token là gì", "token"),
    ("ReAct agent loop là gì", None),
    ("LoRA fine-tune", None),
    ("deadline nộp lab", None),
]


def main():
    s = load_settings()
    cards = CardStore(s.cards_dir)
    r = Retriever(cards, s.chunks_path)
    print(f"Chế độ: {r.mode} · {len(r.docs)} đoạn · {len(r.idf)} từ · ngưỡng hiện tại {s.retrieval_min_score}")
    good, bad = [], []
    for q, concept in PROBES:
        card = cards.get(concept) if concept else None
        hits = r.search(q, "day01-self-attention", 5, boost_ids=card.source_ids if card else None)
        top = hits[0] if hits else None
        on_card = [h for h in hits if card and h.id in card.source_ids]
        best = on_card[0].score if on_card else (top.score if top else 0.0)
        (good if concept else bad).append(best)
        print(f"- {q!r:45} → {[(h.id, h.score) for h in hits[:3]]}")
    if good and bad:
        print(f"\nĐiểm thấp nhất của đoạn thuộc thẻ (câu có nguồn): {min(good):.2f}")
        print(f"Điểm cao nhất của câu không nguồn: {max(bad):.2f} — BM25 vẫn khớp từ chung, nên hệ thống chỉ coi là")
        print("có căn cứ khi đoạn khớp THUỘC thẻ khái niệm. Ngưỡng chỉ cần loại khớp rất yếu và phải nhỏ hơn số đầu.")


if __name__ == "__main__":
    main()
