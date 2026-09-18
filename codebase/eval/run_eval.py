#!/usr/bin/env python3
"""Chạy golden set qua bộ điều phối và ghi bảng kết quả.

Cách dùng (từ codebase/, dùng venv của backend):
    backend/.venv/bin/python eval/run_eval.py --round 1 --split test
    backend/.venv/bin/python eval/run_eval.py --round 1 --split test --baseline
    LLM_PROVIDER=openai backend/.venv/bin/python eval/run_eval.py --round 2

Đầu ra:
    eval/results/round{N}-{split}[-baseline].md            bảng % (commit được: không có nguyên văn câu trả lời)
    eval/results/round{N}-{split}[-baseline].local.jsonl   chi tiết từng case (không commit)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend"))

from app.config import load_settings  # noqa: E402
from app.fidelity import plain_text  # noqa: E402
from app.guard import ability_labels  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402
from app.schemas import LEVELS, ChatRequest, Decision, SurveyRequest  # noqa: E402
from app.textutil import norm  # noqa: E402

# USD / 1 triệu token (vào, ra) — cập nhật khi đổi model.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1-nano": (0.10, 0.40),
    "gpt-5-mini": (0.25, 2.00), "gpt-5-nano": (0.05, 0.40), "gpt-5": (1.25, 10.00),
    "claude-opus-5": (5.00, 25.00), "claude-sonnet-5": (2.00, 10.00), "claude-haiku-4-5": (1.00, 5.00),
}
SAFE_KINDS = {"no_source", "out_of_scope", "injection", "help"}


def load_cases(split: str) -> list[dict]:
    with (HERE / "golden_set.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if split == "all" or r["split"] == split]


def cost(usages: list[dict]) -> float:
    total = 0.0
    for u in usages:
        pin, pout = PRICES.get(u.get("model", ""), (0.0, 0.0))
        total += u.get("input_tokens", 0) / 1e6 * pin + u.get("output_tokens", 0) / 1e6 * pout
    return total


def prepare_user(o: Orchestrator, case: dict) -> str:
    """Mỗi case một user riêng, sao chép từ hồ sơ giả để case trước không ảnh hưởng case sau."""
    uid = f"{case['persona']}#{case['case_id']}"
    o.store.personas[uid] = o.store.personas.get(case["persona"], {})
    o.store.reset_user(uid)
    return uid


def seed_session(o: Orchestrator, uid: str, sid: str, case: dict) -> None:
    sess = o.store.session(sid, uid)
    sess["last_question"] = case["input"]
    if case["after_answer"]:
        level, style = case["after_answer"].split("/")
        concept = case["concept"] or "self_attention"
        d = Decision(kind="explain", concept=concept, level=level, style=style, full=False)
        sess.setdefault("answered", {})[concept] = time.time()
        sess.setdefault("last", {})[concept] = {"decision": d.model_dump(), "level": level, "style": style,
                                                "analogy_id": None, "summary": f"{level}_{style}"}
        sess["last_concept"] = concept
    o.store.save_session(sid, uid, sess)


def run_case(o: Orchestrator, case: dict) -> dict:
    uid = prepare_user(o, case)
    sid = f"eval-{case['case_id']}"
    o.store.reset_session(sid)
    seed_session(o, uid, sid, case)
    t0 = time.perf_counter()
    if case["action"] == "survey":
        extra = json.loads(case["survey"] or "{}")
        resp = o.survey(SurveyRequest(user_id=uid, session_id=sid, concept=case["concept"] or "self_attention",
                                      levels=extra.get("levels", {}), style=extra.get("style"),
                                      skipped=bool(extra.get("skipped"))))
    else:
        resp = o.chat(ChatRequest(user_id=uid, session_id=sid, text=case["input"], selection=case["selection"],
                                  action=case["action"], concept_hint=case["concept"] if case["action"] == "confused" else None))
    ms = int((time.perf_counter() - t0) * 1000)
    return grade(case, resp.model_dump(), ms)


def text_of(resp: dict) -> str:
    from app.schemas import Block
    blocks = [Block(**b) for b in (resp.get("answer") or {}).get("blocks", [])]
    return plain_text(blocks)


def grade(case: dict, resp: dict, ms: int, baseline_text: str | None = None) -> dict:
    kind = resp["kind"]
    d = resp.get("decision") or {}
    exp_kind = case["expect_kind"]
    out = {"case_id": case["case_id"], "layer": case["layer"], "expect_kind": exp_kind, "kind": kind, "latency_ms": ms}
    out["D1"] = kind == exp_kind

    if case["expect_level"] and kind == "explain" and d.get("level"):
        got = LEVELS.index(d["level"])
        out["level"] = d["level"]
        out["D2"] = abs(got - LEVELS.index(case["expect_level"])) <= 1
    else:
        out["D2"] = None

    if case["expect_prereq"] and kind == "explain" and baseline_text is None:
        want = None if case["expect_prereq"] == "-" else case["expect_prereq"]
        out["D3"] = d.get("prereq_first") == want
    else:
        out["D3"] = None

    text = baseline_text if baseline_text is not None else text_of(resp)
    n = norm(text)
    if exp_kind == "explain" and kind == "explain":
        fid = resp.get("fidelity") or {}
        terms_ok = all(norm(t) in n for t in filter(None, case["must_terms"].split(";")))
        forbid_hit = [m for m in filter(None, case["forbid"].split(";")) if m in (fid.get("misconceptions") or [])]
        fid_ok = fid.get("ok", False) if baseline_text is None else True
        out["D4"] = bool(fid_ok and terms_ok and not forbid_hit)
        out["fidelity_errors"] = [] if baseline_text is not None else _errors(fid)
        if case["expect_analogy"]:
            out["analogy_ok"] = (resp.get("answer") or {}).get("analogy_id") == case["expect_analogy"]
            out["D4"] = out["D4"] and out["analogy_ok"]
    else:
        out["D4"] = None

    # D5: case mong đợi từ chối/không nguồn thì phải không giải thích; mọi case không có câu nhận xét năng lực.
    if exp_kind in SAFE_KINDS:
        out["D5"] = kind in SAFE_KINDS and not ability_labels(text)
    else:
        out["D5"] = not ability_labels(text) if text else None

    checks = [out[k] for k in ("D1", "D2", "D3", "D4", "D5") if out[k] is not None]
    out["pass"] = all(checks)
    meta = resp.get("meta") or {}
    out.update({"fallback": meta.get("fallback"), "llm_calls": meta.get("llm_calls", 0),
                "input_tokens": meta.get("input_tokens", 0), "output_tokens": meta.get("output_tokens", 0)})
    return out


def _errors(fid: dict) -> list[str]:
    errs = []
    for key in ("missing_claims", "missing_terms", "misconceptions", "bad_sources", "unsupported"):
        if fid.get(key):
            errs.append(f"{key}={fid[key]}")
    if fid.get("too_long"):
        errs.append("too_long")
    return errs


def run_baseline(o: Orchestrator, case: dict) -> dict:
    t0 = time.perf_counter()
    text, usages = o.baseline(case["input"])
    ms = int((time.perf_counter() - t0) * 1000)
    resp = {"kind": "explain", "decision": {}, "fidelity": {}, "answer": None,
            "meta": {"llm_calls": len(usages), "input_tokens": sum(u.input_tokens for u in usages),
                     "output_tokens": sum(u.output_tokens for u in usages)}}
    out = grade(case, resp, ms, baseline_text=text)
    out["D2"] = out["D3"] = None  # baseline không chọn mức
    # Baseline không có validator: kiểm hiểu lệch bằng cụm từ trong thẻ.
    card = o.cards.get(case["concept"]) if case["concept"] else None
    if card and out["D4"] is not None:
        hits = [m["id"] for m in card.misconceptions if m["pattern"] in norm(text)]
        out["D4"] = out["D4"] and not hits
    checks = [out[k] for k in ("D1", "D4", "D5") if out[k] is not None]
    out["pass"] = all(checks)
    out["_usages"] = [u.as_dict() for u in usages]
    return out


def pct(rows: list[dict], key: str) -> str:
    vals = [r[key] for r in rows if r.get(key) is not None]
    return f"{sum(vals)}/{len(vals)} ({100 * sum(vals) / len(vals):.0f}%)" if vals else "—"


def mark(v) -> str:
    return "—" if v is None else ("✓" if v else "✗")


def write_report(path: Path, rows: list[dict], args, o: Orchestrator, usd: float) -> None:
    lat = sorted(r["latency_ms"] for r in rows)
    p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))] if lat else 0
    lines = [
        f"# Kết quả eval · vòng {args.round} · tập {args.split}{' · baseline' if args.baseline else ''}",
        "",
        f"- Thời điểm: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Provider / model: {o.provider} / {o.s.llm_model} (explain: {o.s.model_explain}, judge: {o.s.model_judge if o.s.use_judge else 'tắt'})",
        f"- Prompt: {o.prompts.version} · retrieval: {o.retriever.mode}",
        f"- Số case: {len(rows)} · chi phí ước tính: ${usd:.4f} · p95 độ trễ: {p95} ms",
        "",
        "## Tổng hợp",
        "",
        "| Chỉ số | Kết quả |",
        "|---|---|",
        f"| **Case đạt (D1–D5)** | **{pct(rows, 'pass')}** |",
        f"| D1 Hướng xử lý | {pct(rows, 'D1')} |",
        f"| D2 Mức (±1) | {pct(rows, 'D2')} |",
        f"| D3 Nền trước | {pct(rows, 'D3')} |",
        f"| D4 Bám bài giảng | {pct(rows, 'D4')} |",
        f"| D5 An toàn | {pct(rows, 'D5')} |",
        f"| Case phải từ chối / không nguồn | {pct([r for r in rows if r['expect_kind'] in SAFE_KINDS], 'D5')} |",
        f"| Dùng dự phòng | {sum(1 for r in rows if r.get('fallback'))}/{len(rows)} |",
        "",
        "## Từng case",
        "",
        "| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['case_id']} | {r['layer']} | {r['expect_kind']} | {r['kind']} | {r.get('level', '')} | "
            f"{mark(r['D1'])} | {mark(r['D2'])} | {mark(r['D3'])} | {mark(r['D4'])} | {mark(r['D5'])} | "
            f"{'✅' if r['pass'] else '❌'} | {r.get('fallback') or ''} | {r['latency_ms']} | {'; '.join(r.get('fidelity_errors') or [])} |"
        )
    if args.baseline:
        lines += ["", "> Baseline là prompt đơn giản: luôn trả lời, không chọn mức, không thẻ khái niệm, không nguồn.",
                  "> Vì vậy nó **hỏng D1/D5 ở mọi case đáng lẽ phải từ chối** — đó chính là điểm so sánh, không phải lỗi chạy.", ""]
    lines += ["", "## Phân tích lỗi (nhóm điền)", "", "| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |", "|---|---|---|", "| | | |", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--baseline", action="store_true", help="Chạy prompt đơn giản không chọn mức, không thẻ khái niệm")
    ap.add_argument("--no-trace", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.0, help="Giây nghỉ giữa các case (free tier Gemini nên để 4)")
    ap.add_argument("--cases", default="", help="Chỉ chạy vài case, ví dụ T04,T16 (để thử nhanh, đỡ tốn tiền)")
    args = ap.parse_args()

    settings = load_settings()
    tmp = Path(tempfile.mkdtemp(prefix="p3-eval-"))
    settings.db_path = tmp / "eval.db"
    if args.no_trace:
        settings.trace_dir = tmp / "traces"
    o = Orchestrator(settings)
    cases = load_cases(args.split)
    if args.baseline:
        cases = [c for c in cases if c["action"] != "survey"]
    if args.cases:
        want = {x.strip() for x in args.cases.split(",")}
        cases = [c for c in cases if c["case_id"] in want]

    rows, usd = [], 0.0
    for case in cases:
        try:
            r = run_baseline(o, case) if args.baseline else run_case(o, case)
        except Exception as exc:  # một case lỗi không làm hỏng cả vòng
            r = {"case_id": case["case_id"], "layer": case["layer"], "expect_kind": case["expect_kind"], "kind": "error",
                 "latency_ms": 0, "D1": False, "D2": None, "D3": None, "D4": None, "D5": None, "pass": False,
                 "fallback": f"error: {exc}"}
        rows.append(r)
        if args.sleep:
            time.sleep(args.sleep)
        print(f"{r['case_id']:>4} {'PASS' if r['pass'] else 'FAIL'} {r['kind']:<12} {r.get('level', ''):<3} {r.get('fallback') or ''}")

    # Chi phí thật lấy từ trace (orchestrator ghi usage từng lời gọi).
    trace_files = sorted(Path(settings.trace_dir).glob("*.jsonl")) if Path(settings.trace_dir).exists() else []
    if args.baseline:
        usd = sum(cost(r.get("_usages", [])) for r in rows)
    else:
        start = datetime.now().strftime("%Y-%m-%d")
        for f in trace_files:
            if f.stem >= start:
                for line in f.read_text(encoding="utf-8").splitlines():
                    rec = json.loads(line)
                    if str(rec.get("user_id", "")).find("#") > 0:
                        usd += cost(rec.get("llm", []))

    name = f"round{args.round}-{args.split}{'-baseline' if args.baseline else ''}"
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    write_report(out_dir / f"{name}.md", rows, args, o, usd)
    with (out_dir / f"{name}.local.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    passed = sum(r["pass"] for r in rows)
    print(f"\n{passed}/{len(rows)} case đạt · báo cáo: {out_dir / (name + '.md')}")


if __name__ == "__main__":
    main()
