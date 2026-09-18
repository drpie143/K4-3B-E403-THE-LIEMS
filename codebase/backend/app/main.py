"""FastAPI — hợp đồng API ở §5 tài liệu backend.

Chạy (từ codebase/backend):
    .venv/bin/uvicorn app.main:app --reload --port 8000
Rồi mở http://localhost:8000/?mode=live — mock được phục vụ cùng origin.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .orchestrator import Orchestrator
from .schemas import (
    AdjustRequest, ChatRequest, ChatResponse, CheckAnswerRequest, CheckQuestion, CheckResult,
    FeedbackRequest, FeedbackResult, HandoffRequest, ProfileUpdate, SurveyRequest, UndoRequest, UserReq,
)


@lru_cache
def get_orchestrator() -> Orchestrator:
    return Orchestrator(load_settings())


app = FastAPI(title="P3 · Trợ giảng AI giải thích lại đúng mức", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "null"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

Orch = Depends(get_orchestrator)


def _not_found(exc: Exception):
    raise HTTPException(status_code=404, detail=str(exc))


@app.get("/health")
def health(o: Orchestrator = Orch):
    return o.health()


@app.get("/api/personas")
def personas(o: Orchestrator = Orch):
    return {uid: {"label": p.get("label", uid)} for uid, p in o.store.personas.items()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, o: Orchestrator = Orch):
    return o.chat(req)


@app.post("/api/survey", response_model=ChatResponse)
def survey(req: SurveyRequest, o: Orchestrator = Orch):
    try:
        return o.survey(req)
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/adjust", response_model=ChatResponse)
def adjust(req: AdjustRequest, o: Orchestrator = Orch):
    try:
        return o.adjust(req)
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/feedback", response_model=FeedbackResult)
def feedback(req: FeedbackRequest, o: Orchestrator = Orch):
    try:
        return o.feedback(req)
    except KeyError as exc:
        _not_found(exc)


@app.get("/api/check", response_model=CheckQuestion | None)
def check_question(user_id: str, session_id: str, concept: str, o: Orchestrator = Orch):
    try:
        return o.check_question(user_id, session_id, concept)
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/check", response_model=CheckResult)
def check_answer(req: CheckAnswerRequest, o: Orchestrator = Orch):
    try:
        return o.check_answer(req)
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/handoff")
def handoff(req: HandoffRequest, o: Orchestrator = Orch):
    return {"draft": o.handoff(req)}


@app.get("/api/profile")
def get_profile(user_id: str, o: Orchestrator = Orch):
    return o.store.profile(user_id)


@app.put("/api/profile")
def put_profile(req: ProfileUpdate, o: Orchestrator = Orch):
    notices = []
    if req.memory_on is not None or req.preferred_style is not None or req.clear_style:
        o.store.update_settings(req.user_id, req.memory_on, req.preferred_style, req.clear_style)
    if req.concept and req.level:
        if not o.cards.get(req.concept):
            _not_found(KeyError(req.concept))
        n = o.store.apply_event(req.user_id, req.concept, "manual", level=req.level)
        if n:
            notices.append(n)
    return {"profile": o.store.profile(req.user_id), "notices": notices}


@app.delete("/api/profile")
def delete_profile(user_id: str, concept: str | None = None, o: Orchestrator = Orch):
    o.store.delete(user_id, concept)
    return {"profile": o.store.profile(user_id)}


@app.delete("/api/profile/strategy")
def delete_strategy(user_id: str, concept: str, strategy: str, o: Orchestrator = Orch):
    o.store.delete_strategy(user_id, concept, strategy)
    return {"profile": o.store.profile(user_id)}


@app.post("/api/profile/undo")
def undo(req: UndoRequest, o: Orchestrator = Orch):
    done = [eid for eid in sorted(req.event_ids, reverse=True) if o.store.undo(req.user_id, eid)]
    return {"undone": done, "profile": o.store.profile(req.user_id)}


@app.post("/api/profile/reset")
def reset(req: UserReq, o: Orchestrator = Orch):
    o.store.reset_user(req.user_id)
    return {"profile": o.store.profile(req.user_id)}


@app.post("/api/session/reset")
def reset_session(session_id: str = Query(...), o: Orchestrator = Orch):
    o.store.reset_session(session_id)
    return {"ok": True}


@app.get("/api/sources/{source_id}")
def source(source_id: str, o: Orchestrator = Orch):
    s = o.source(source_id)
    if not s:
        raise HTTPException(status_code=404, detail="Không có đoạn này")
    return s


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/app/index.html?mode=live")


_settings = load_settings()
if _settings.mock_dir.exists():
    app.mount("/app", StaticFiles(directory=_settings.mock_dir, html=True), name="mock")
