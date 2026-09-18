#!/usr/bin/env python3
"""Sinh dữ liệu cục bộ cho mock P3 từ data pack (KHÔNG commit các file sinh ra).

Đầu ra (đều đã nằm trong .gitignore):
  frontend/data/sources.local.js     nguyên văn các đoạn transcript mà mock trích dẫn
  data/chunks.local.json         toàn bộ đoạn transcript-04/06 (chuẩn bị cho retrieval ở CP3)
  eval/golden_candidates.local.csv  các lượt chatlog K4 làm ứng viên golden set

Cách chạy (từ gốc repo):
  python scripts/build_local_data.py
  python scripts/build_local_data.py --pack "/đường/dẫn/tới/data/vlearn-pack"
Hoặc đặt biến môi trường VLEARN_PACK.
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
BACKEND_DATA = REPO / "backend" / "Data"
DEFAULT_PACK = REPO.parent / "ĐỌC ĐỀ" / "K4-3B-Day05-06-AI-Product-Hackathon" / "data" / "vlearn-pack"
TRANSCRIPTS = [f"transcript-0{i}-clean.md" for i in range(1, 7)]
PARA_RE = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")
MAX_CHARS = 900

# Thêm backend vào sys.path để dùng module chunking
sys.path.insert(0, str(REPO / "backend"))
try:
    from app.chunking import parse_transcript_file, chunk_paragraphs_three_tier, Paragraph
except ImportError:
    parse_transcript_file = None

# Lượt chatlog dùng làm ứng viên golden set (chỉ K4, câu học viên nói chưa hiểu / hỏi lại / ngoài phạm vi).
GOLDEN_TURNS = ["T10728", "T10317", "T10536", "T10480", "T10508", "T10807", "T10709", "T10319", "T10326", "T10599", "T10744", "T10502"]
CONFUSED_RE = re.compile(r"không hiểu|chưa hiểu|khó hiểu|giải thích lại|đơn giản|dễ hiểu|ngắn gọn", re.I)


def find_pack(arg):
    candidates = [
        Path(arg) if arg else None,
        BACKEND_DATA,
        Path(os.environ["VLEARN_PACK"]) if "VLEARN_PACK" in os.environ else None,
        DEFAULT_PACK,
    ]
    for cand in candidates:
        if cand and (cand / "transcript").is_dir():
            return cand
        if cand and (cand.name == "transcript" and cand.is_dir()):
            return cand.parent
    sys.exit("Không tìm thấy thư mục transcript. Dùng --pack hoặc đặt trong backend/Data/transcript.")


def read_chunks_with_overlap(pack):
    trans_dir = pack / "transcript" if (pack / "transcript").is_dir() else pack
    all_paras: list[Paragraph] = []
    
    for name in TRANSCRIPTS:
        fp = trans_dir / name
        if not fp.exists():
            continue
        if parse_transcript_file:
            all_paras.extend(parse_transcript_file(fp))
        else:
            section = ""
            for line in fp.read_text(encoding="utf-8").splitlines():
                if line.startswith("## "):
                    section = line[3:].strip()
                    continue
                m = PARA_RE.match(line)
                if m:
                    all_paras.append(Paragraph(id=m.group(1), section=section, file=name, text=m.group(2).strip()))

    if parse_transcript_file:
        chunks_objs = chunk_paragraphs_three_tier(all_paras)
        return [c.to_dict() for c in chunks_objs], all_paras
    
    # Fallback nếu không import được chunking
    return [{"id": p.id, "file": p.file, "section": p.section, "text": p.text, "source_ids": [p.id]} for p in all_paras], all_paras


def referenced_ids():
    src = (REPO / "frontend" / "js" / "content.js").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"T0[46]-\d{3}", src)))


def write_sources(all_paras):
    wanted = set(referenced_ids())
    out = {}
    for p in all_paras:
        pid = getattr(p, "id", None) or p.get("id")
        if pid in wanted:
            ptext = getattr(p, "text", None) or p.get("text")
            psec = getattr(p, "section", None) or p.get("section", "")
            if len(ptext) > MAX_CHARS:
                ptext = ptext[:MAX_CHARS].rsplit(" ", 1)[0] + " …"
            out[pid] = {"section": psec, "text": ptext}
    missing = wanted - set(out)
    path = REPO / "frontend" / "data" / "sources.local.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// SINH TỰ ĐỘNG — dữ liệu được cấp, KHÔNG commit.\nwindow.VLEARN_SOURCES_LOCAL = "
        + json.dumps(out, ensure_ascii=False, indent=1)
        + ";\n",
        encoding="utf-8",
    )
    print(f"✓ {path.relative_to(REPO)}: {len(out)} đoạn" + (f" (thiếu: {', '.join(sorted(missing))})" if missing else ""))


def write_chunks(chunks):
    path = REPO / "data" / "chunks.local.json"
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
    path = REPO / "eval" / "golden_candidates.local.csv"
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
    chunks, all_paras = read_chunks_with_overlap(pack)
    write_sources(all_paras)
    write_chunks(chunks)
    write_golden(pack)


if __name__ == "__main__":
    main()
