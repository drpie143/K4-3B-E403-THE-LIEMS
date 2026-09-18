"""FastAPI — hợp đồng API ở §5 tài liệu backend.

Chạy (từ backend):
    .venv/bin/uvicorn app.main:app --reload --port 8000
Rồi mở http://localhost:8000/?mode=live — frontend/ được phục vụ cùng origin.

Khi deploy tách đôi (backend trên Render, frontend trên Vercel), đặt biến môi trường
ALLOWED_ORIGINS = "https://ten-app.vercel.app,https://ten-mien-rieng.com" để mở CORS.
"""
from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
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

# Máy cá nhân luôn được phép; thêm miền Vercel/miền riêng qua ALLOWED_ORIGINS (ngăn cách bằng dấu phẩy).
_extra_origins = [o.strip().rstrip("/") for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "null", *_extra_origins],
    # localhost mọi cổng + mọi bản preview của Vercel (ten-app-git-nhanh-user.vercel.app)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?|https://[\w-]+\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

Orch = Depends(get_orchestrator)


# ---------------------------------------------------------------- tài khoản
class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AccountUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = None


def bearer(authorization: str | None = Header(default=None)) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def current_account(o: Orchestrator = Orch, token: str | None = Depends(bearer)) -> dict | None:
    """Tài khoản của phiên đăng nhập (nếu có). Không có token vẫn chạy được (chế độ hồ sơ mẫu)."""
    return o.auth.account_for_token(token)


Account = Depends(current_account)


def own(req, account: dict | None):
    """Khi đã đăng nhập, mọi thao tác gắn vào user_id của tài khoản đó — không cho gửi user_id người khác."""
    if account:
        req = req.model_copy(update={"user_id": account["user_id"]})
    return req


def own_id(user_id: str, account: dict | None) -> str:
    return account["user_id"] if account else user_id


def _not_found(exc: Exception):
    raise HTTPException(status_code=404, detail=str(exc))


@app.get("/health")
def health(o: Orchestrator = Orch):
    return o.health()


@app.get("/api/personas")
def personas(o: Orchestrator = Orch):
    return {uid: {"label": p.get("label", uid)} for uid, p in o.store.personas.items()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, o: Orchestrator = Orch, account: dict | None = Account):
    return o.chat(own(req, account))


@app.post("/api/survey", response_model=ChatResponse)
def survey(req: SurveyRequest, o: Orchestrator = Orch, account: dict | None = Account):
    try:
        return o.survey(own(req, account))
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/adjust", response_model=ChatResponse)
def adjust(req: AdjustRequest, o: Orchestrator = Orch, account: dict | None = Account):
    try:
        return o.adjust(own(req, account))
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/feedback", response_model=FeedbackResult)
def feedback(req: FeedbackRequest, o: Orchestrator = Orch, account: dict | None = Account):
    try:
        return o.feedback(own(req, account))
    except KeyError as exc:
        _not_found(exc)


@app.get("/api/check", response_model=CheckQuestion | None)
def check_question(user_id: str, session_id: str, concept: str, o: Orchestrator = Orch, account: dict | None = Account):
    try:
        return o.check_question(own_id(user_id, account), session_id, concept)
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/check", response_model=CheckResult)
def check_answer(req: CheckAnswerRequest, o: Orchestrator = Orch, account: dict | None = Account):
    try:
        return o.check_answer(own(req, account))
    except KeyError as exc:
        _not_found(exc)


@app.post("/api/handoff")
def handoff(req: HandoffRequest, o: Orchestrator = Orch):
    return {"draft": o.handoff(req)}


@app.get("/api/profile")
def get_profile(user_id: str = "", o: Orchestrator = Orch, account: dict | None = Account):
    uid = own_id(user_id, account)
    if not uid:
        raise HTTPException(status_code=401, detail="Cần đăng nhập hoặc truyền user_id")
    o.store.flush()  # mở Sổ tay là dịp tốt để đẩy bộ nhớ đang chờ lên Supabase
    return o.store.profile(uid)


@app.put("/api/profile")
def put_profile(req: ProfileUpdate, o: Orchestrator = Orch, account: dict | None = Account):
    req = own(req, account)
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
def delete_profile(user_id: str = "", concept: str | None = None, o: Orchestrator = Orch, account: dict | None = Account):
    uid = own_id(user_id, account)
    o.store.delete(uid, concept)
    return {"profile": o.store.profile(uid)}


@app.delete("/api/profile/strategy")
def delete_strategy(user_id: str = "", concept: str = "", strategy: str = "", o: Orchestrator = Orch, account: dict | None = Account):
    uid = own_id(user_id, account)
    o.store.delete_strategy(uid, concept, strategy)
    return {"profile": o.store.profile(uid)}


@app.post("/api/profile/undo")
def undo(req: UndoRequest, o: Orchestrator = Orch, account: dict | None = Account):
    req = own(req, account)
    done = [eid for eid in sorted(req.event_ids, reverse=True) if o.store.undo(req.user_id, eid)]
    return {"undone": done, "profile": o.store.profile(req.user_id)}


@app.post("/api/profile/reset")
def reset(req: UserReq, o: Orchestrator = Orch, account: dict | None = Account):
    req = own(req, account)
    o.store.reset_user(req.user_id)
    return {"profile": o.store.profile(req.user_id)}


@app.post("/api/session/reset")
def reset_session(session_id: str = Query(...), o: Orchestrator = Orch):
    o.store.reset_session(session_id)
    return {"ok": True}


@app.get("/api/lessons")
def lessons(o: Orchestrator = Orch):
    """Danh mục 6 buổi học (tên buổi, mục, thẻ khái niệm, đang đọc dữ liệu từ đâu)."""
    return {"lessons": o.lessons.catalog()}


@app.get("/api/lessons/{lesson_id}")
def lesson(lesson_id: str, section: str | None = None, o: Orchestrator = Orch):
    """Thân bài của một buổi — đọc từ dữ liệu cục bộ hoặc Supabase, không bao giờ từ repo."""
    try:
        return o.lessons.lesson(lesson_id, section)
    except KeyError:
        raise HTTPException(status_code=404, detail="Không có buổi học này")


@app.post("/api/auth/register")
def auth_register(req: RegisterRequest, o: Orchestrator = Orch):
    try:
        acc = o.auth.register(req.email, req.password, req.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _, token = o.auth.login(req.email, req.password)
    o.store.ensure_user(acc["user_id"])
    return {"account": acc, "token": token}


@app.post("/api/auth/login")
def auth_login(req: LoginRequest, o: Orchestrator = Orch):
    try:
        acc, token = o.auth.login(req.email, req.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    o.store.ensure_user(acc["user_id"])  # kéo hồ sơ + bộ nhớ dài hạn của tài khoản về
    return {"account": acc, "token": token}


@app.post("/api/auth/logout")
def auth_logout(o: Orchestrator = Orch, token: str | None = Depends(bearer)):
    o.store.flush()  # đẩy nốt bộ nhớ đang chờ trước khi rời máy
    o.auth.logout(token or "")
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(o: Orchestrator = Orch, account: dict | None = Account):
    if not account:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    return {"account": account, "profile": o.store.profile(account["user_id"])}


@app.put("/api/auth/me")
def auth_update(req: AccountUpdate, o: Orchestrator = Orch, account: dict | None = Account):
    if not account:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    try:
        return {"account": o.auth.update_account(account["user_id"], req.display_name, req.password)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/auth/me")
def auth_delete(o: Orchestrator = Orch, account: dict | None = Account, token: str | None = Depends(bearer)):
    if not account:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    o.store.delete(account["user_id"])          # xoá hồ sơ + bộ nhớ dài hạn (cả trên Supabase)
    o.auth.delete_account(account["user_id"])   # rồi mới xoá tài khoản
    o.auth.logout(token or "")
    return {"ok": True}


@app.post("/api/memory/flush")
def memory_flush(o: Orchestrator = Orch):
    """Đẩy ngay hàng đợi bộ nhớ lên Supabase (dùng khi demo để thấy dữ liệu xuất hiện)."""
    return {"pushed": o.store.flush(), "memory": o.store.memory_health()}


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
if _settings.frontend_dir.exists():
    # Tiện khi chạy trên một máy: backend phục vụ luôn frontend cùng origin, không lo CORS.
    # Khi deploy tách đôi (Vercel), phần mount này chỉ là bản dự phòng.
    app.mount("/app", StaticFiles(directory=_settings.frontend_dir, html=True), name="frontend")
