#!/usr/bin/env python3
"""Dựng và kiểm tra 6 buổi học từ transcript trên máy.

Việc script làm:
  1. Gọi build_local_data.py để sinh data/chunks.local.json (KHÔNG commit)
  2. Đối chiếu với danh mục backend/lessons.yaml: buổi nào thiếu đoạn, mục nào rỗng
  3. In bảng tóm tắt để biết trang học sẽ hiển thị được những gì

Cách chạy (từ gốc repo):
    python scripts/build_lessons.py
    python scripts/build_lessons.py --pack "/đường/dẫn/data/vlearn-pack"
    python scripts/build_lessons.py --check     # chỉ kiểm tra, không sinh lại dữ liệu
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="", help="thư mục data/vlearn-pack của khoá")
    ap.add_argument("--check", action="store_true", help="chỉ kiểm tra, không sinh lại chunks")
    args = ap.parse_args()

    if not args.check:
        cmd = [sys.executable, str(REPO / "scripts" / "build_local_data.py")]
        if args.pack:
            cmd += ["--pack", args.pack]
        if subprocess.call(cmd) != 0:
            return 1
        print()

    from app.cards import CardStore
    from app.config import load_settings
    from app.lessons import LessonStore
    from app.retrieval import Retriever

    s = load_settings()
    cards = CardStore(s.cards_dir)
    retriever = Retriever(cards, s.chunks_path, settings=s)
    store = LessonStore(cards, s, retriever)

    print(f"Nguồn dữ liệu: {retriever.mode} · {len(retriever.docs)} chunk")
    print(f"{'#':>2} {'buổi':26} {'đoạn':>5} {'mục':>4} {'thẻ':>4}  nguồn")
    problems: list[str] = []
    for row in store.catalog():
        data = store.lesson(row["id"])
        paras = sum(len(x["paragraphs"]) for x in data["sections"])
        empty = [x["title"] for x in data["sections"] if not x["paragraphs"]]
        print(f"{row['order']:>2} {row['id']:26} {paras:>5} {len(data['sections']):>4} {len(row['concepts']):>4}  {row['source']}")
        if not paras:
            problems.append(f"{row['id']}: chưa có đoạn nào (thiếu transcript {cards.lesson_files(row['id'])})")
        for title in empty:
            problems.append(f"{row['id']}: mục rỗng — {title}")
        for cid in row["concepts"]:
            card = cards.get(cid["id"])
            files = set(cards.lesson_files(row["id"]))
            wrong = [sid for sid in card.source_ids if f"transcript-{sid[1:3]}-clean.md" not in files]
            if wrong:
                problems.append(f"{row['id']}: thẻ {cid['id']} trích nguồn ngoài buổi — {wrong}")

    if problems:
        print("\nCần xem lại:")
        for p in problems:
            print("  -", p)
        return 1
    print("\n✓ 6 buổi đều có nội dung và thẻ khái niệm trích đúng nguồn trong buổi.")
    print("  Dữ liệu nguyên văn nằm ở data/chunks.local.json (đã gitignore).")
    print("  Muốn đẩy lên Supabase: python scripts/sync_to_supabase.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
