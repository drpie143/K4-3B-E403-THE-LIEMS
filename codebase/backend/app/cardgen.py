"""Sinh mẫu trả lời đã duyệt cho các thẻ khái niệm "nhẹ" (auto_template: true).

Vì sao có file này: thẻ đầy đủ (như self_attention.yaml) viết tay 5 mức rất tốn công.
Với 6 buổi học, nhóm chỉ viết phần **nội dung đã duyệt** (core_claims, ví dụ, giới hạn,
hiểu lệch) rồi để code ráp thành mẫu trả lời theo mức. Mẫu sinh ra vẫn:
  - chỉ dùng câu trong thẻ (không có chữ nào do LLM tự nghĩ),
  - luôn gắn mã đoạn nguồn cho từng block,
  - phủ đủ core_claims và các thuật ngữ bắt buộc,
  - nằm trong giới hạn số từ của từng mức (phần dài đẩy vào block "map" — không tính độ dài).

Khoá mẫu sinh ra khớp với templates.template_key(): L1_ngan_gon, L1_vi_du_<analogy>,
L2_ngan_gon, L2_vi_du_<analogy>, L3_first, L3, L4, L5.
"""
from __future__ import annotations

from .textutil import strip_tags

WORD_LIMIT = {"L1": 140, "L2": 200, "L3": 200, "L4": 240, "L5": 340}


def _words(blocks: list[dict]) -> int:
    parts = []
    for b in blocks:
        if b["t"] in {"map", "prereq", "outside", "formula"}:
            continue
        parts += [b.get("title") or "", strip_tags(b.get("html") or "")]
        parts += [strip_tags(x) for x in (b.get("items") or [])]
    return len(" ".join(p for p in parts if p).split())


def _claim_block(claim: dict, t: str = "p") -> dict:
    return {"t": t, "html": claim["text"], "src": list(claim.get("src", [])), "claims": [claim["id"]]}


def _map_block(claims: list[dict], title: str = "Các ý còn lại của bài") -> dict:
    return {
        "t": "map", "title": title,
        "rows": [[f"Ý {i + 2}", c["text"]] for i, c in enumerate(claims)],
        "src": sorted({s for c in claims for s in c.get("src", [])}),
        "claims": [c["id"] for c in claims],
    }


def _steps_block(claims: list[dict], title: str = "Các ý chính") -> dict:
    return {
        "t": "steps", "title": title, "items": [c["text"] for c in claims],
        "src": sorted({s for c in claims for s in c.get("src", [])}),
        "claims": [c["id"] for c in claims],
    }


def _limit_block(card: dict) -> dict | None:
    limits = card.get("analogy_limits") or []
    if not limits:
        return None
    src = sorted({s for a in card.get("approved_analogies") or [] for s in a.get("src", [])})
    return {"t": "limit", "html": " ".join(limits), "src": src or list(card["core_claims"][0].get("src", []))}


def _analogy_block(analogy: dict) -> dict:
    return {"t": "analogy", "title": "Ví dụ trong bài", "html": analogy["text"], "src": list(analogy.get("src", []))}


def _outside_block(card: dict) -> dict | None:
    notes = card.get("outside_lesson_notes") or []
    if not notes:
        return None
    return {"t": "outside", "html": "Ngoài buổi học này: " + " ".join(notes), "src": []}


def _fit(level: str, head: list[dict], claims: list[dict]) -> list[dict]:
    """Ráp block sao cho phủ hết claim mà không vượt giới hạn số từ của mức."""
    blocks = head + [_steps_block(claims)] if claims else list(head)
    if _words(blocks) <= WORD_LIMIT[level] or not claims:
        return blocks
    return head + [_map_block(claims)]


def build_templates(card: dict) -> dict[str, list[dict]]:
    """Trả về dict {khoá mẫu: [block]} cho một thẻ nhẹ."""
    claims = card["core_claims"]
    first, rest = claims[0], claims[1:]
    analogies = card.get("approved_analogies") or []
    limit = _limit_block(card)
    outside = _outside_block(card)

    out: dict[str, list[dict]] = {}

    # --- L1: ví dụ (nếu có) + ý chính, phần còn lại đẩy vào bảng ------------
    base_l1 = [_claim_block(first, "key")]
    out["L1_ngan_gon"] = _fit("L1", base_l1, rest)
    for a in analogies:
        out[f"L1_vi_du_{a['id']}"] = _fit("L1", [_analogy_block(a)] + base_l1, rest)

    # --- L2: ý chính + các ý còn lại ---------------------------------------
    out["L2_ngan_gon"] = _fit("L2", [_claim_block(first, "key")], rest)
    for a in analogies:
        out[f"L2_vi_du_{a['id']}"] = _fit("L2", [_analogy_block(a), _claim_block(first, "key")], rest)

    # --- L3: đủ ý + giới hạn của ví dụ -------------------------------------
    l3_head = [_claim_block(first, "p")]
    l3 = _fit("L3", l3_head, rest)
    if limit:
        l3 = l3 + [limit]
    out["L3"] = l3
    out["L3_first"] = l3

    # --- L4: thêm ví dụ và giới hạn ----------------------------------------
    l4_head = ([_analogy_block(analogies[0])] if analogies else []) + [_claim_block(first, "p")]
    l4 = _fit("L4", l4_head, rest) + [_claim_block(first, "key")]
    if limit:
        l4 = l4 + [limit]
    out["L4"] = l4

    # --- L5: L4 + phần ghi chú ngoài bài -----------------------------------
    l5 = list(l4)
    if outside:
        l5 = l5 + [outside]
    out["L5"] = l5
    return out
