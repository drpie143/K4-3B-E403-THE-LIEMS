#!/usr/bin/env python3
"""Xuất vài lượt trace mẫu để commit vào repo (xác minh kỹ thuật ở CP3–CP6).

Giữ: prompt của nhóm, quyết định JSON, câu trả lời JSON, kết quả chấm, token, độ trễ.
Bỏ: nguyên văn đoạn bài giảng lấy từ data pack — thay bằng mã đoạn.

Chạy (từ gốc repo):
    backend/.venv/bin/python scripts/export_trace_sample.py --limit 2
Kết quả: eval/traces-sample/<request_id>.json  (được commit)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
OUT_DIR = HERE.parent / "eval" / "traces-sample"
PLACEHOLDER = "[nguyên văn đoạn bài giảng — chỉ có trên máy, không commit]"
LONG_TEXT = re.compile(r'("text":\s*")((?:[^"\\]|\\.){200,}?)(")')


def redact(text: str) -> str:
    """Thay mọi trường "text" dài (đoạn transcript trong prompt) bằng placeholder."""
    return LONG_TEXT.sub(lambda m: m.group(1) + PLACEHOLDER + m.group(3), text)


def load_turns(limit: int) -> list[dict]:
    rows = []
    for f in sorted((BACKEND / "traces").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("llm"):
                rows.append(rec)
    rows = [r for r in rows if not any(u.get("error") for u in r["llm"])]
    # Ưu tiên lấy đa dạng: 1 lượt giải thích, 1 lượt khảo sát/điều chỉnh…
    picked, seen_kinds = [], set()
    for rec in reversed(rows):
        kind = rec.get("kind") or rec.get("route")
        if kind in seen_kinds and len(picked) >= 1:
            continue
        seen_kinds.add(kind)
        picked.append(rec)
        if len(picked) >= limit:
            break
    return picked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2)
    args = ap.parse_args()
    turns = load_turns(args.limit)
    if not turns:
        raise SystemExit("Chưa có trace nào có lời gọi LLM thành công — chạy prototype với provider thật trước.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for rec in turns:
        rid = rec["request_id"]
        calls = []
        pf = BACKEND / "traces" / "prompts" / f"{rid}.jsonl"
        if pf.exists():
            for line in pf.read_text(encoding="utf-8").splitlines():
                c = json.loads(line)  # che sau khi giải mã JSON, vì prompt nằm trong chuỗi
                calls.append({"task": c["task"], "model": c["model"], "system_prompt": c["system"],
                              "user_prompt": redact(c["user"]), "raw_response": c["raw_response"], "error": c["error"]})
        out = {
            "_ghi_chu": "Trace mẫu đã che nguyên văn đoạn bài giảng. Bản đầy đủ nằm ở backend/traces/ trên máy chạy.",
            "request_id": rid, "route": rec.get("route"), "kind": rec.get("kind"),
            "prompt_version": rec.get("prompt_version"), "provider": rec.get("provider"),
            "fallback": rec.get("fallback"), "latency_ms": rec.get("latency_ms"),
            "llm_usage": rec.get("llm"), "decision": rec.get("decision"), "fidelity": rec.get("fidelity"),
            "rejected_attempts": rec.get("rejected"), "calls": calls,
        }
        path = OUT_DIR / f"{rid}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"✓ {path.relative_to(HERE.parent)} · {len(calls)} lời gọi · {rec.get('kind')}")


if __name__ == "__main__":
    main()
