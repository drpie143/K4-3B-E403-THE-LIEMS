#!/usr/bin/env python3
"""Chạy vài case golden qua agent 5 tầng (không dùng P3 orchestrator)."""

from __future__ import annotations

import asyncio
import csv
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import repo_root
from app.service.container import build_container


async def run() -> None:
    path = repo_root() / "app" / "eval" / "golden_set.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    c = build_container()
    ok = 0
    n = 0
    for row in rows:
        if row.get("split") != "test":
            continue
        action = row.get("action") or "ask"
        if action not in ("ask", "confused"):
            continue
        n += 1
        conv = uuid4()
        user = row.get("persona") or "demo-moi-toanh"
        u = await c.repository.upsert_user(user)
        await c.repository.insert_conversation(conv, u.id, "eval")
        text = row.get("input") or ""
        sel = row.get("selection") or row.get("concept") or ""
        if action == "confused":
            text = "khó hiểu quá"
        state = await c.graph.ainvoke(
            {
                "user_id": user,
                "session_id": "eval",
                "conversation_id": str(conv),
                "client_turn_id": str(uuid4()),
                "turn_id": str(uuid4()),
                "user_message": text,
                "highlighted_text": sel or None,
                "context_lecture_id": "day01-self-attention",
            },
            config={"configurable": {"thread_id": str(conv)}},
        )
        kind = state.get("response_kind")
        expect = row.get("expect_kind") or ""
        mapped = {
            "explanation": "explain",
            "probe": "survey",
            "retrieval_miss": "no_source",
            "redirect": "no_source",
        }.get(kind or "", kind)
        hit = (not expect) or mapped == expect or kind == expect
        ok += int(bool(hit))
        mark = "✓" if hit else "✗"
        print(f"{mark} {row.get('case_id')} expect={expect} got={kind}/{mapped}")
    print(f"\n{ok}/{n} khớp expect_kind (xấp xỉ)")
    await c.aclose()


if __name__ == "__main__":
    asyncio.run(run())
