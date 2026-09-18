#!/usr/bin/env python3
"""Sinh dữ liệu cục bộ cho mock P3 từ data pack (KHÔNG commit các file sinh ra).

Đầu ra (đều đã nằm trong .gitignore):
  app/ui/data/sources.local.js
  app/data/chunks.local.json
  app/eval/golden_candidates.local.csv

Cách chạy (từ gốc repo):
  python app/scripts/build_local_data.py
  python app/scripts/build_local_data.py --pack "/đường/dẫn/tới/data/vlearn-pack"
Hoặc đặt biến môi trường VLEARN_PACK.
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
APP = REPO / "app"
DEFAULT_PACK = Path(
    "/Users/levanviet/Documents/Workspace/th_lab_vin/K4-3B-Day05-06-AI-Product-Hackathon/data/vlearn-pack"
)
PACK_FALLBACKS = [
    REPO.parent / "K4-3B-Day05-06-AI-Product-Hackathon" / "data" / "vlearn-pack",
    REPO.parent / "ĐỌC ĐỀ" / "K4-3B-Day05-06-AI-Product-Hackathon" / "data" / "vlearn-pack",
]
TRANSCRIPTS = ["transcript-04-clean.md", "transcript-06-clean.md"]
PARA_RE = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")
MAX_CHARS = 900

# Lượt chatlog dùng làm ứng viên golden set (chỉ K4, câu học viên nói chưa hiểu / hỏi lại / ngoài phạm vi).
GOLDEN_TURNS = ["T10728", "T10317", "T10536", "T10480", "T10508", "T10807", "T10709", "T10319", "T10326", "T10599", "T10744", "T10502"]
CONFUSED_RE = re.compile(r"không hiểu|chưa hiểu|khó hiểu|giải thích lại|đơn giản|dễ hiểu|ngắn gọn", re.I)


def find_pack(arg):
    for cand in [arg, os.environ.get("VLEARN_PACK"), DEFAULT_PACK, *PACK_FALLBACKS]:
        if cand and (Path(cand) / "transcript").is_dir():
            return Path(cand)
    sys.exit("Không tìm thấy vlearn-pack. Dùng --pack hoặc biến VLEARN_PACK.")


def read_paragraphs(pack):
    chunks = []
    for name in TRANSCRIPTS:
        section = ""
        for line in (pack / "transcript" / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            m = PARA_RE.match(line)
            if m:
                chunks.append({"id": m.group(1), "file": name, "section": section, "text": m.group(2).strip()})
    return chunks


def referenced_ids():
    src = (APP / "ui" / "js" / "content.js").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"T0[46]-\d{3}", src)))


def write_sources(chunks):
    wanted = set(referenced_ids())
    out = {}
    for c in chunks:
        if c["id"] in wanted:
            text = c["text"]
            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS].rsplit(" ", 1)[0] + " …"
            out[c["id"]] = {"section": c["section"], "text": text}
    missing = wanted - set(out)
    path = APP / "ui" / "data" / "sources.local.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// SINH TỰ ĐỘNG — dữ liệu được cấp, KHÔNG commit.\nwindow.VLEARN_SOURCES_LOCAL = "
        + json.dumps(out, ensure_ascii=False, indent=1)
        + ";\n",
        encoding="utf-8",
    )
    print(f"✓ {path.relative_to(REPO)}: {len(out)} đoạn" + (f" (thiếu: {', '.join(sorted(missing))})" if missing else ""))


def write_chunks(chunks):
    path = APP / "data" / "chunks.local.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {path.relative_to(REPO)}: {len(chunks)} đoạn")


def write_golden(pack):
    src = pack / "chatlog" / "tutor_turns.csv"
    if not src.exists():
        print("! Bỏ qua golden set: không có chatlog")
        return
    rows = []
    with src.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["cohort_hint"] != "K4":
                continue
            q = re.sub(r"^\([^)]*\)\s*", "", r["student_question"]).strip()
            if r["turn_id"] in GOLDEN_TURNS or (r["is_preset"] == "False" and CONFUSED_RE.search(q)):
                section = re.match(r"^\(Đang học phần “([^”]+)”", r["student_question"])
                rows.append({
                    "turn_id": r["turn_id"],
                    "lecture_code": r["lecture_code"],
                    "section": section.group(1) if section else "",
                    "question": q[:300],
                    "move_used": r["move_used"],
                    "has_citation": r["has_citation"],
                    "reply_len": r["reply_len"],
                    "expected_level": "",
                    "expected_style": "",
                    "layer": "",
                })
    path = APP / "eval" / "golden_candidates.local.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"✓ {path.relative_to(REPO)}: {len(rows)} lượt ứng viên (điền expected_* rồi chép mã lượt sang eval/golden_set.csv)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", help="Đường dẫn tới thư mục data/vlearn-pack")
    args = ap.parse_args()
    pack = find_pack(args.pack)
    print(f"Data pack: {pack}")
    chunks = read_paragraphs(pack)
    write_sources(chunks)
    write_chunks(chunks)
    write_golden(pack)


if __name__ == "__main__":
    main()
