"""Module chia chunk bài giảng theo Cấu Trúc Ba Tầng & Tiêu Chuẩn Kích Thước:

Cấu trúc ba tầng:
    Buổi học (Lesson / Transcript)
    └── Chủ đề lớn – tiêu đề ## (Section)
        └── Chunk retrieval
            └── Một hoặc nhiều slide / đoạn Txx (Thường 1–3 đoạn)

Quy tắc kích thước:
    - Kích thước mục tiêu: 180–350 từ
    - Giới hạn mềm: 400 từ
    - Giới hạn tối đa: 450–500 từ
    - Overlap: 40–70 từ (khoảng 50 từ) giữa 2 chunk kế tiếp trong cùng một chủ đề
    - Số đoạn T trong một chunk: Thường 1–3 đoạn
    - Có vượt qua tiêu đề ## không?: KHÔNG (mỗi chunk nằm trọn vẹn trong một ##)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PARA_RE = re.compile(r"^\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*)$")
LESSON_RE = re.compile(r"^#\s+(.+)$")


@dataclass
class Paragraph:
    id: str
    section: str
    file: str
    lesson: str
    text: str

    @property
    def words(self) -> list[str]:
        return self.text.split()

    @property
    def word_count(self) -> int:
        return len(self.words)


@dataclass
class Chunk:
    id: str
    lesson: str
    section: str
    file: str
    text: str
    source_ids: list[str] = field(default_factory=list)
    word_count: int = 0
    overlap_words: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lesson": self.lesson,
            "section": self.section,
            "file": self.file,
            "text": self.text,
            "source_ids": self.source_ids or [self.id],
            "word_count": self.word_count or len(self.text.split()),
            "overlap_words": self.overlap_words,
        }


def parse_transcript_file(file_path: Path) -> list[Paragraph]:
    """Phân tích một file transcript thành danh sách các paragraph có gắn mã [Txx-NNN] và tiêu đề ##."""
    if not file_path.exists():
        return []

    paragraphs: list[Paragraph] = []
    current_lesson = file_path.stem
    current_section = ""
    filename = file_path.name

    for line in file_path.read_text(encoding="utf-8").splitlines():
        line_s = line.strip()
        if line_s.startswith("# ") and not current_section:
            m_l = LESSON_RE.match(line_s)
            if m_l:
                current_lesson = m_l.group(1).strip()
            continue
        if line_s.startswith("## "):
            current_section = line_s[3:].strip()
            continue
        m = PARA_RE.match(line_s)
        if m:
            pid = m.group(1)
            ptext = m.group(2).strip()
            paragraphs.append(
                Paragraph(
                    id=pid,
                    section=current_section,
                    file=filename,
                    lesson=current_lesson,
                    text=ptext,
                )
            )

    return paragraphs


def _split_long_paragraph(
    p: Paragraph,
    target_words: int = 280,
    overlap_target: int = 55,
) -> list[dict]:
    """Tách một đoạn Txx đơn lẻ quá dài (> 400 từ) thành các phần con có overlap 40-70 từ."""
    words = p.words
    n = len(words)
    parts = []
    start = 0
    part_idx = 1

    while start < n:
        end = min(start + target_words, n)
        chunk_words = words[start:end]
        text_content = " ".join(chunk_words)
        tag = f"[{p.id}]" if start == 0 else f"[{p.id} (tiếp)]"
        
        # Đảm bảo ID duy nhất cho các đoạn bị cắt
        chunk_id = p.id if part_idx == 1 else f"{p.id}-{part_idx}"
        
        parts.append({
            "primary_id": chunk_id,
            "source_ids": [p.id],
            "text": f"{tag} {text_content}",
            "words": chunk_words,
            "overlap_from_prev": overlap_target if start > 0 else 0,
        })
        if end >= n:
            break
        # Bước nhảy với overlap 40-70 từ (55 từ)
        start = max(start + 1, end - overlap_target)
        part_idx += 1

    return parts


def chunk_paragraphs_three_tier(
    paragraphs: list[Paragraph],
    target_min: int = 180,
    target_max: int = 350,
    soft_limit: int = 400,
    hard_limit: int = 480,
    overlap_min: int = 40,
    overlap_max: int = 70,
    overlap_target: int = 55,
    max_paragraphs: int = 3,
) -> list[Chunk]:
    """Chia chunk theo mô hình 3 tầng:
    Tầng 1: Buổi học (Lesson)
    Tầng 2: Chủ đề lớn (Section ##) - Không bao giờ vượt qua tiêu đề ##
    Tầng 3: Chunk retrieval: Thường 1-3 đoạn Txx, kích thước 180-350 từ, overlap 40-70 từ.
    """
    if not paragraphs:
        return []

    # Nhóm theo từng Section trong từng Buổi học (Tầng 1 + Tầng 2)
    grouped: list[list[Paragraph]] = []
    current_group: list[Paragraph] = []
    last_key = None

    for p in paragraphs:
        key = (p.file, p.section)
        if key != last_key:
            if current_group:
                grouped.append(current_group)
            current_group = [p]
            last_key = key
        else:
            current_group.append(p)
    if current_group:
        grouped.append(current_group)

    all_chunks: list[Chunk] = []

    for group in grouped:
        if not group:
            continue

        lesson = group[0].lesson
        section = group[0].section
        filename = group[0].file

        # Xử lý các paragraph trong cùng section:
        # Nếu có paragraph dài > 400 từ thì tách con trước
        items = []
        for p in group:
            if p.word_count > soft_limit:
                items.extend(_split_long_paragraph(p, target_words=target_max, overlap_target=overlap_target))
            else:
                items.append({
                    "primary_id": p.id,
                    "source_ids": [p.id],
                    "text": f"[{p.id}] {p.text}",
                    "words": p.words,
                    "overlap_from_prev": 0,
                })

        # Ghép các items thành chunks trong section
        idx = 0
        prev_chunk_tail_words: list[str] = []

        while idx < len(items):
            current_batch = [items[idx]]
            current_words = list(items[idx]["words"])
            j = idx + 1

            # Gom thêm tối đa 1-3 đoạn T sao cho kích thước 180-350 từ (tối đa 450-480 từ)
            while j < len(items) and len(current_batch) < max_paragraphs:
                cand = items[j]
                cand_len = len(cand["words"])
                # Nếu đã đạt kích thước tối thiểu (>= target_min) và thêm vào sẽ vượt soft_limit
                if len(current_words) >= target_min and (len(current_words) + cand_len > soft_limit):
                    break
                # Nếu thêm vào vượt hard_limit
                if len(current_words) + cand_len > hard_limit:
                    break
                current_batch.append(cand)
                current_words.extend(cand["words"])
                j += 1

            # Xây dựng text của chunk
            source_ids = list(dict.fromkeys(sid for it in current_batch for sid in it["source_ids"]))
            primary_id = current_batch[0]["primary_id"]

            overlap_len = 0
            # Nếu có overlap từ chunk trước trong cùng section, chèn đoạn gối đầu 40-70 từ
            if prev_chunk_tail_words:
                overlap_words_slice = prev_chunk_tail_words[-overlap_target:]
                overlap_len = len(overlap_words_slice)
                overlap_text = " ".join(overlap_words_slice)
                body_text = " ".join(it["text"] for it in current_batch)
                full_text = f"... {overlap_text} ...\n{body_text}"
            else:
                full_text = " ".join(it["text"] for it in current_batch)

            total_wc = len(full_text.split())

            all_chunks.append(
                Chunk(
                    id=primary_id,
                    lesson=lesson,
                    section=section,
                    file=filename,
                    text=full_text,
                    source_ids=source_ids,
                    word_count=total_wc,
                    overlap_words=overlap_len,
                )
            )

            # Lưu lại 40-70 từ cuối của chunk hiện tại để làm overlap cho chunk kế tiếp
            prev_chunk_tail_words = current_words[-overlap_target:] if len(current_words) >= overlap_target else current_words

            # Tiến đến đoạn tiếp theo
            idx = j

    return all_chunks


def build_chunks_from_directory(transcript_dir: Path) -> list[Chunk]:
    """Đọc toàn bộ file transcript trong thư mục và sinh ra danh sách chunks theo cấu trúc 3 tầng."""
    files = sorted(transcript_dir.glob("transcript-*-clean.md"))
    all_paras: list[Paragraph] = []
    for f in files:
        all_paras.extend(parse_transcript_file(f))

    return chunk_paragraphs_three_tier(all_paras)
