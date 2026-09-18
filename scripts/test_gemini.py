r"""Script kiểm tra nhanh API Key Gemini (gemini-embedding-001 miễn phí).

Cách chạy:
    .\backend\.venv\Scripts\python.exe scripts/test_gemini.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import load_settings
import httpx

def main():
    settings = load_settings()
    key = os.environ.get("GEMINI_API_KEY", "").strip()

    if not key:
        print("❌ Chưa tìm thấy GEMINI_API_KEY trong file backend/.env!")
        print("👉 Hãy mở backend/.env và điền GEMINI_API_KEY của bạn vào dòng 17.")
        return

    print(f"Đang kiểm tra Gemini API Key: {key[:8]}...{key[-4:]}")
    test_text = "Xin chào, đây là đoạn văn kiểm tra cơ chế Self-attention và Transformer."

    model = "gemini-embedding-001"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={key}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": test_text}]},
        "output_dimensionality": 768
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                values = data.get("embedding", {}).get("values", [])
                dim = len(values)
                print(f"\n🎉 THÀNH CÔNG RỰC RỠ!")
                print(f"✓ Model: {model} (Google Gemini - Miễn phí 100%)")
                print(f"✓ Chiều vector embedding: {dim} chiều (khớp chuẩn Supabase pgvector 768)")
                print(f"✓ Mẫu 5 giá trị đầu: {[round(x, 4) for x in values[:5]]}")
                print(f"\n👉 API Key Gemini hoạt động hoàn hảo!")
                print(f"👉 Bây giờ bạn có thể đồng bộ lên Supabase bằng lệnh:")
                print(f"   .\\backend\\.venv\\Scripts\\python.exe scripts/sync_to_supabase.py")
            else:
                print(f"\n❌ Lỗi kết nối Google Gemini ({resp.status_code}):")
                print(resp.text)
    except Exception as exc:
        print(f"\n❌ Ngoại lệ khi gọi API: {exc}")

if __name__ == "__main__":
    main()
