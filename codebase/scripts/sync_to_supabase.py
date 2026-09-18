#!/usr/bin/env python3
"""Script đẩy toàn bộ 384 chunks và Dense Vector Embeddings lên Supabase (pgvector).

Cách dùng:
    python codebase/scripts/sync_to_supabase.py
    Hoặc:
    python codebase/scripts/sync_to_supabase.py --batch-size 50
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[2]
CODEBASE = REPO / "codebase"
BACKEND = CODEBASE / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import load_settings
from app.supabase_client import SupabaseClient

# Cache local model để không bị load lại với mỗi batch
_local_embedding_model = None


def get_embeddings(texts: list[str], settings) -> list[list[float]]:
    """Sinh vector embeddings qua local model intfloat/multilingual-e5-base."""
    import httpx
    import os

    # Ưu tiên theo cấu hình EMBEDDING_PROVIDER trong .env
    provider = getattr(settings, "embedding_provider", "").strip().lower()
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    # 1. Local Embedding (Miễn phí 100%, Không giới hạn rate limit)
    if provider == "local" or provider == "e5":
        try:
            from sentence_transformers import SentenceTransformer
            global _local_embedding_model
            
            # Khởi tạo model (sẽ tự tải xuống nếu chưa có)
            model_name = getattr(settings, "embedding_model", "intfloat/multilingual-e5-base")
            if not model_name or model_name == "text-embedding-004":
                model_name = "intfloat/multilingual-e5-base"
                
            if _local_embedding_model is None:
                print(f"Đang tải model {model_name} vào bộ nhớ...")
                _local_embedding_model = SentenceTransformer(model_name)
            
            # Prefix cho E5 models: "passage: " đối với documents
            # Thêm 'passage: ' vào trước text để đảm bảo độ chính xác theo tài liệu chuẩn của E5
            passages = [f"passage: {t}" for t in texts]
            
            embeddings = _local_embedding_model.encode(passages, normalize_embeddings=True)
            return embeddings.tolist()
        except ImportError:
            print("! Thiếu thư viện sentence-transformers. Hãy chạy: pip install sentence-transformers")
            return []
        except Exception as e:
            print(f"! Lỗi khi chạy local embedding: {e}")
            return []

    # 2. Gemini
    if (provider == "gemini" or not openai_key) and gemini_key:
        model = "gemini-embedding-001"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={gemini_key}"
        requests = [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}, "output_dimensionality": 768} for t in texts]
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json={"requests": requests})
            if resp.status_code == 200:
                return [e["values"] for e in resp.json()["embeddings"]]
            else:
                print(f"! Lỗi Gemini embedding ({resp.status_code}): {resp.text}")

    # 3. OpenAI
    if openai_key:
        model = getattr(settings, "embedding_model", "text-embedding-3-small")
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json={"input": texts, "model": model})
            if resp.status_code == 200:
                data = resp.json()["data"]
                return [item["embedding"] for item in data]
            else:
                print(f"! Lỗi OpenAI embedding ({resp.status_code}): {resp.text}")

    # 4. Fallback kiểm thử khi chưa điền key
    dim = 768 if provider in ("gemini", "local", "e5") else 1536
    print(f"! Chưa cấu hình provider hợp lệ: sinh vector giả lập {dim} chiều để kiểm tra kết nối Supabase.")
    import hashlib
    vectors = []
    for t in texts:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        vec = [(float(b) / 255.0 - 0.5) for b in (h * 48)[:dim]]
        vectors.append(vec)
    return vectors


def main():
    ap = argparse.ArgumentParser(description="Đồng bộ chunks lên Supabase")
    ap.add_argument("--batch-size", type=int, default=40, help="Số lượng chunk đẩy mỗi batch")
    args = ap.parse_args()

    settings = load_settings()
    sb = SupabaseClient(settings.supabase_url, settings.supabase_key)

    if not sb.is_configured():
        print("! Chưa cấu hình SUPABASE_URL hoặc SUPABASE_KEY trong codebase/backend/.env.")
        print("  Vui lòng điền thông tin Supabase vào .env trước khi chạy script.")
        return

    chunks_file = CODEBASE / "data" / "chunks.local.json"
    if not chunks_file.exists():
        print(f"! Không tìm thấy {chunks_file}. Chạy python codebase/scripts/build_local_data.py trước.")
        return

    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    total = len(chunks)
    print(f"Bắt đầu đồng bộ {total} chunks lên Supabase: {settings.supabase_url}")

    batch_size = args.batch_size
    synced = 0

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = get_embeddings(texts, settings)

        records = []
        for c, emb in zip(batch, embeddings):
            records.append({
                "id": c["id"],
                "lesson": c.get("lesson", ""),
                "section": c.get("section", ""),
                "file": c.get("file", ""),
                "text": c["text"],
                "source_ids": c.get("source_ids", [c["id"]]),
                "word_count": c.get("word_count", len(c["text"].split())),
                "overlap_words": c.get("overlap_words", 0),
                "embedding": emb,
            })

        ok = sb.upsert("lecture_chunks", records)
        if ok:
            synced += len(records)
            print(f"  ✓ Đã đẩy: {synced}/{total} chunks")
        else:
            print(f"  ✗ Lỗi khi đẩy batch {i} - {i + len(batch)}")

    print(f"\n Hoàn tất đồng bộ {synced}/{total} chunks lên Supabase!")


if __name__ == "__main__":
    main()
