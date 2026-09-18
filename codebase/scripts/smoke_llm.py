#!/usr/bin/env python3
"""Thử 1 lượt với provider thật: kiểm tra key, schema JSON, độ trễ và token — tốn rất ít.

Ví dụ:
    cd codebase/backend
    LLM_PROVIDER=gemini LLM_MODEL=gemini-2.5-flash GEMINI_API_KEY=... .venv/bin/python ../scripts/smoke_llm.py
    LLM_PROVIDER=openai LLM_MODEL=gpt-4o-mini OPENAI_API_KEY=... .venv/bin/python ../scripts/smoke_llm.py --full
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import load_settings  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.schemas import ChatRequest  # noqa: E402

PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60), "gpt-5-mini": (0.25, 2.00),
          "claude-opus-5": (5.00, 25.00), "gemini-2.5-flash": (0.0, 0.0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="bước 2 là gì mình chưa hiểu, sao lại cộng trọng số và cộng vào đâu")
    ap.add_argument("--user", default="demo-moi")
    ap.add_argument("--full", action="store_true", help="Chạy trọn lượt (chẩn đoán + viết giải thích + chấm)")
    args = ap.parse_args()

    s = load_settings()
    s.trace_dir = Path(tempfile.mkdtemp(prefix="p3-smoke-"))
    if s.llm_provider == "fake":
        sys.exit("Đang là LLM_PROVIDER=fake — đặt biến môi trường sang openai/gemini/claude rồi chạy lại.")
    if not args.full:
        s.use_judge = False
    o = Orchestrator(s, db_path=":memory:")
    print(f"Provider: {o.provider} · model: {s.llm_model} · judge: {'bật' if s.use_judge else 'tắt'} · tìm nguồn: {o.retriever.mode}")

    resp = o.chat(ChatRequest(user_id=args.user, session_id="smoke", text=args.text))
    m = resp.meta
    print(f"\nKết quả: {resp.kind} · mức {resp.decision.level if resp.decision else '-'} · "
          f"nền trước: {resp.decision.prereq_first if resp.decision else '-'}")
    print(f"Lý do cho học viên: {resp.decision.reason_for_user if resp.decision else ''}")
    if resp.fidelity:
        print(f"Độ bám bài giảng: {'ĐẠT' if resp.fidelity.ok else 'RỚT ' + str(resp.fidelity.errors())} "
              f"({resp.fidelity.covered}/{resp.fidelity.total} ý chính)")
    print(f"Dự phòng: {m.fallback or 'không'} · gọi LLM {m.llm_calls} lần · "
          f"{m.input_tokens} token vào, {m.output_tokens} ra · {m.latency_ms} ms")
    pin, pout = PRICES.get(s.llm_model, (0.0, 0.0))
    print(f"Chi phí lượt này: ${m.input_tokens / 1e6 * pin + m.output_tokens / 1e6 * pout:.5f}")
    errors = []
    for f in Path(s.trace_dir).glob("*.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            errors += [u for u in json.loads(line).get("llm", []) if u.get("error")]
    if errors:
        print("\n⚠ Lỗi gọi LLM (đã dùng bản dự phòng):")
        for e in errors:
            print(f"  - {e['task']}: {e['error'][:200]}")
        print("  → Kiểm tra key, tên model và hạn mức. Không có lỗi nào thì mới là chạy AI thật.")
    if resp.answer:
        print("\nCác block:", json.dumps([{"t": b.t, "src": b.src, "claims": b.claims} for b in resp.answer.blocks], ensure_ascii=False))
        for b in resp.answer.blocks[:3]:
            print(" -", (b.title or b.t) + ":", (b.html or " / ".join(b.items or []) or "")[:160])


if __name__ == "__main__":
    main()
