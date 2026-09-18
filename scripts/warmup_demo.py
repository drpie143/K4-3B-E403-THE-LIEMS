#!/usr/bin/env python3
"""Làm nóng trước khi demo: nạp mô hình, điền bộ nhớ đệm câu trả lời.

Vì sao cần: lượt hỏi đầu tiên phải nạp mô hình embedding và gọi LLM thật nên mất
7-13 giây. Chạy script này trước khi lên trình bày thì các câu trong kịch bản đã
nằm sẵn trong .cache/answers.json, lúc demo chỉ còn ~2-4 giây.

Chạy (backend phải đang chạy ở cổng 8000):
    python scripts/warmup_demo.py
    python scripts/warmup_demo.py --url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LESSON = "day01-foundation-b"

# Đúng các lượt trong kịch bản demo (xem docs/demo-script.md).
TURNS = [
    ("demo-trung-binh", "Self-attention là gì?", "ask", None),
    ("demo-trung-binh", "Mình chưa hiểu", "confused", "self_attention"),
    ("demo-vung", "Self-attention là gì?", "ask", None),
    ("demo-vung", "Q, K, V trong self-attention khác nhau thế nào?", "ask", None),
    ("demo-moi", "Self-attention là gì?", "ask", None),
    ("demo-thu-vien", "Self-attention là gì?", "ask", None),
    ("demo-moi", "Token là gì?", "ask", None),
    ("demo-trung-binh", "Transformer là gì?", "ask", None),
]


def post(url: str, path: str, body: dict, timeout: float = 90.0) -> dict:
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def reset_personas(url: str) -> None:
    """Trả 4 hồ sơ demo về trạng thái mẫu trong personas.yaml.

    Bắt buộc: mỗi lượt hỏi đều ghi vào hồ sơ (hạ mức khi nói "chưa hiểu", lên mức khi
    trả lời đúng). Không reset thì lần chạy sau trợ giảng hỏi khảo sát thay vì giải thích
    — tập trước một lần là buổi demo thật diễn ra khác hẳn.
    """
    for user in sorted({u for u, *_ in TURNS}):
        try:
            post(url, "/api/profile/reset", {"user_id": user}, timeout=30)
        except Exception as exc:
            print(f"  ! không reset được {user}: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--reset-only", action="store_true",
                    help="chỉ trả hồ sơ demo về mẫu, không gọi LLM (chạy ngay trước khi lên trình bày)")
    args = ap.parse_args()

    try:
        with urllib.request.urlopen(args.url.rstrip("/") + "/health", timeout=30) as r:
            health = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        print(f"✗ Không gọi được {args.url} — backend đã chạy chưa?\n  {exc}")
        return 1

    print(f"Provider : {health.get('provider')} · {health.get('model')}")
    print(f"Bài giảng: {health.get('retrieval_mode')} · {health.get('passages')} đoạn")
    if health.get("passages", 0) < 100:
        print("  ! Rất ít đoạn — kiểm tra data pack hoặc Supabase (README §5.3).")
    print()

    reset_personas(args.url)
    if args.reset_only:
        print("Đã trả hồ sơ demo về trạng thái mẫu. Sẵn sàng trình bày.")
        return 0

    slow = 0
    for i, (user, text, action, hint) in enumerate(TURNS, 1):
        body = {"user_id": user, "session_id": f"warm-{user}", "lesson_id": LESSON,
                "text": text, "selection": "", "action": action}
        if hint:
            body["concept_hint"] = hint
        t0 = time.perf_counter()
        try:
            resp = post(args.url, "/api/chat", body)
        except Exception as exc:
            print(f"  {i}/{len(TURNS)} ✗ {text[:40]} — {exc}")
            slow += 1
            continue
        ms = int((time.perf_counter() - t0) * 1000)
        meta = resp.get("meta") or {}
        mark = "·" if meta.get("cached") else " "
        print(f"  {i}/{len(TURNS)} {mark} {ms:6} ms  [{resp.get('kind')}]  {user:16} {text[:42]}")
        if ms > 15000:
            slow += 1

    # Trả hồ sơ về mẫu: bộ nhớ đệm câu trả lời vẫn còn, nhưng học viên demo sạch như chưa hỏi.
    reset_personas(args.url)

    print()
    print("Xong — câu trả lời đã vào bộ nhớ đệm, hồ sơ demo đã trả về mẫu.")
    print("Lúc trình bày, các lượt trong kịch bản sẽ chạy ~2-5 giây thay vì 8-15 giây.")
    if slow:
        print(f"  ! {slow} lượt chậm/lỗi — xem backend/traces/<ngày>.jsonl, trường marks_ms.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
