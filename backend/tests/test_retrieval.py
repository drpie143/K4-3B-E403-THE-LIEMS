"""Unit test kiểm thử tính năng Chunking có Overlap và Hybrid Search (BM25 + Dense RRF)."""
from pathlib import Path
import pytest

from app.cards import CardStore
from app.chunking import Paragraph, chunk_paragraphs_three_tier
from app.config import Settings
from app.retrieval import Retriever, Passage, cosine_similarity


def test_chunking_three_tier():
    # Giả lập 4 đoạn văn trong cùng 1 section
    p1 = " ".join(["từ"] * 120)
    p2 = " ".join(["từ"] * 100)
    p3 = " ".join(["từ"] * 110)
    p4 = " ".join(["từ"] * 120)
    p_sec2 = " ".join(["từ"] * 90)

    paras = [
        Paragraph(id="T01-001", section="Section 1", file="transcript-01.md", lesson="Day 1", text=p1),
        Paragraph(id="T01-002", section="Section 1", file="transcript-01.md", lesson="Day 1", text=p2),
        Paragraph(id="T01-003", section="Section 1", file="transcript-01.md", lesson="Day 1", text=p3),
        Paragraph(id="T01-004", section="Section 1", file="transcript-01.md", lesson="Day 1", text=p4),
        # Đoạn trong section khác để kiểm tra không vượt qua tiêu đề ##
        Paragraph(id="T02-001", section="Section 2", file="transcript-01.md", lesson="Day 1", text=p_sec2),
    ]
    chunks = chunk_paragraphs_three_tier(paras, target_min=180, target_max=350, soft_limit=400, overlap_target=55)

    # Đảm bảo không bao giờ gộp qua tiêu đề ## khác
    for c in chunks:
        if "T02-001" in c.source_ids:
            assert c.section == "Section 2"
            assert "T01-001" not in c.source_ids
            assert "T01-002" not in c.source_ids

    # Kiểm tra kích thước chunk trong ngưỡng cho phép (180-350 từ, tối đa 450 từ)
    c1 = chunks[0]
    assert 180 <= c1.word_count <= 400
    assert len(c1.source_ids) in (1, 2, 3)

    # Kiểm tra overlap 40-70 từ giữa 2 chunk trong cùng Section 1
    sec1_chunks = [c for c in chunks if c.section == "Section 1"]
    assert len(sec1_chunks) >= 2
    assert 40 <= sec1_chunks[1].overlap_words <= 70


def test_cosine_similarity():
    v1 = {"ai": 1.0, "llm": 2.0}
    v2 = {"ai": 1.0, "llm": 2.0}
    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0

    v3 = {"cat": 1.0}
    assert cosine_similarity(v1, v3) == 0.0


def test_retriever_hybrid_search(tmp_path):
    # Tạo dữ liệu giả lập cho card store
    backend_dir = Path(__file__).resolve().parents[1]
    cards = CardStore(backend_dir / "cards")

    # Kiểm tra khởi tạo với summary mode hoặc chunks.local.json
    settings = Settings(retrieval_mode="hybrid", hybrid_alpha=0.5, rrf_k=60)
    retriever = Retriever(cards, backend_dir.parent / "data" / "chunks.local.json", settings=settings)

    assert len(retriever.docs) > 0
    # Test tìm kiếm hybrid với câu hỏi về attention
    results = retriever.search("self-attention cơ chế Q K V là gì", lesson_id="day01-self-attention", k=5)
    assert len(results) > 0
    # Kết quả trả về phải có score > 0 và thuộc lớp Passage
    assert isinstance(results[0], Passage)
    assert results[0].score > 0

    # Kiểm tra tra cứu theo id hoặc source_id
    first_doc = results[0]
    fetched = retriever.get(first_doc.id)
    assert fetched is not None
    assert fetched.id == first_doc.id

    if first_doc.source_ids:
        sec_id = first_doc.source_ids[-1]
        fetched_sec = retriever.get(sec_id)
        assert fetched_sec is not None


def test_retriever_modes():
    backend_dir = Path(__file__).resolve().parents[1]
    cards = CardStore(backend_dir / "cards")
    chunks_path = backend_dir.parent / "data" / "chunks.local.json"

    # 1. BM25 only
    s_bm25 = Settings(retrieval_mode="bm25")
    r_bm25 = Retriever(cards, chunks_path, settings=s_bm25)
    res_bm25 = r_bm25.search("vector embedding", lesson_id="day01-self-attention", k=3)
    assert len(res_bm25) > 0

    # 2. Dense only
    s_dense = Settings(retrieval_mode="dense")
    r_dense = Retriever(cards, chunks_path, settings=s_dense)
    res_dense = r_dense.search("vector embedding", lesson_id="day01-self-attention", k=3)
    assert len(res_dense) > 0

    # 3. Hybrid
    s_hybrid = Settings(retrieval_mode="hybrid", hybrid_alpha=0.6)
    r_hybrid = Retriever(cards, chunks_path, settings=s_hybrid)
    res_hybrid = r_hybrid.search("vector embedding", lesson_id="day01-self-attention", k=3)
    assert len(res_hybrid) > 0
