#!/usr/bin/env python3
"""Trích xuất toàn bộ 6 file transcript thành chunks và đồng bộ lên Upstash Vector DB.

Đầu ra:
- codebase/data/chunks.local.json (toàn bộ 700 đoạn từ transcript 01 đến 06)
- Upsert lên Upstash Vector DB (nếu có UPSTASH_VECTOR_REST_URL & UPSTASH_VECTOR_REST_TOKEN)

Cách chạy:
  python codebase/scripts/index_all_transcripts.py
  python codebase/scripts/index_all_transcripts.py --upload
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]
CODEBASE = REPO / "codebase"
TRANSCRIPT_DIR = REPO / "data" / "vlearn-pack" / "transcript"
PARA_RE = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")


def load_all_transcripts() -> list[dict]:
    if not TRANSCRIPT_DIR.is_dir():
        sys.exit(f"Không tìm thấy thư mục transcript tại: {TRANSCRIPT_DIR}")

    files = sorted(TRANSCRIPT_DIR.glob("transcript-0*-clean.md"))
    if not files:
        sys.exit("Không tìm thấy file transcript-0*-clean.md nào!")

    chunks = []
    for f in files:
        section = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            line_s = line.strip()
            if line_s.startswith("## "):
                section = line_s[3:].strip()
                continue
            m = PARA_RE.match(line_s)
            if m:
                cid = m.group(1)
                text = m.group(2).strip()
                chunks.append({
                    "id": cid,
                    "file": f.name,
                    "section": section,
                    "text": text,
                })
    return chunks


def save_local_chunks(chunks: list[dict]):
    out_path = CODEBASE / "data" / "chunks.local.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ Đã lưu {len(chunks)} chunks từ cả 6 transcript vào {out_path.relative_to(REPO)}")


def upload_to_upstash(chunks: list[dict], url: str, token: str, batch_size: int = 50):
    url = url.rstrip("/")
    upsert_endpoint = f"{url}/upsert-data"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Đang đồng bộ {len(chunks)} chunks lên Upstash Vector ({url})...")
    total = len(chunks)
    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        payload = [
            {
                "id": c["id"],
                "data": f"[{c['section']}] {c['text']}",
                "metadata": {
                    "file": c["file"],
                    "section": c["section"],
                    "text": c["text"][:1000],
                },
            }
            for c in batch
        ]
        resp = requests.post(upsert_endpoint, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"❌ Lỗi batch {i}-{i+len(batch)}: HTTP {resp.status_code} - {resp.text}")
            return False
        print(f"  → Đã đẩy {min(i + batch_size, total)}/{total} chunks...")
        time.sleep(0.2)

    print("🎉 Đồng bộ lên Upstash Vector DB thành công 100%!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Index all 6 transcripts to local JSON and Upstash Vector DB")
    parser.add_argument("--upload", action="store_true", help="Upload chunks lên Upstash Vector DB")
    args = parser.parse_args()

    chunks = load_all_transcripts()
    print(f"Đã trích xuất {len(chunks)} đoạn từ 6 file transcript.")
    save_local_chunks(chunks)

    # Đọc biến môi trường từ .env nếu có
    env_path = CODEBASE / "backend" / ".env"
    url = os.environ.get("UPSTASH_VECTOR_REST_URL", "")
    token = os.environ.get("UPSTASH_VECTOR_REST_TOKEN", "")

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("UPSTASH_VECTOR_REST_URL="):
                url = url or line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("UPSTASH_VECTOR_REST_TOKEN="):
                token = token or line.split("=", 1)[1].strip().strip('"').strip("'")

    if args.upload or (url and token):
        if not url or not token:
            print("⚠️ Chưa cấu hình UPSTASH_VECTOR_REST_URL hoặc UPSTASH_VECTOR_REST_TOKEN trong backend/.env")
        else:
            upload_to_upstash(chunks, url, token)
    else:
        print("💡 Chạy với cờ --upload sau khi điền UPSTASH_VECTOR_REST_URL và UPSTASH_VECTOR_REST_TOKEN vào backend/.env để đồng bộ lên Cloud!")


if __name__ == "__main__":
    main()
