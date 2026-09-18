from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.schema.vlearn import (
    VLearnAdjustRequest,
    VLearnChatRequest,
    VLearnCheckRequest,
    VLearnFeedbackRequest,
    VLearnHandoffRequest,
    VLearnProfileUpdate,
    VLearnSurveyRequest,
)

router = APIRouter(tags=["vlearn-ui"])


def _svc(request: Request):
    return request.app.state.container.vlearn


@router.get("/health")
async def health(request: Request):
    return await _svc(request).health()


@router.get("/api/personas")
async def personas(request: Request):
    return _svc(request).personas()


@router.post("/api/chat")
async def chat(req: VLearnChatRequest, request: Request):
    return await _svc(request).chat(req)


@router.post("/api/survey")
async def survey(req: VLearnSurveyRequest, request: Request):
    return await _svc(request).survey(req)


@router.post("/api/adjust")
async def adjust(req: VLearnAdjustRequest, request: Request):
    return await _svc(request).adjust(req)


@router.post("/api/feedback")
async def feedback(req: VLearnFeedbackRequest, request: Request):
    return await _svc(request).feedback(req)


@router.get("/api/check")
async def get_check(
    request: Request,
    user_id: str = Query(...),
    session_id: str = Query(""),
    concept: str = Query(...),
):
    return await _svc(request).get_check(user_id, concept)


@router.post("/api/check")
async def post_check(req: VLearnCheckRequest, request: Request):
    return await _svc(request).grade_check(req)


@router.post("/api/handoff")
async def handoff(req: VLearnHandoffRequest, request: Request):
    return await _svc(request).handoff(req)


@router.get("/api/profile")
async def get_profile(request: Request, user_id: str = Query(...)):
    return await _svc(request).profile(user_id)


@router.put("/api/profile")
async def put_profile(req: VLearnProfileUpdate, request: Request):
    return await _svc(request).put_profile(req)


@router.post("/api/profile/reset")
async def reset_profile(request: Request, payload: dict):
    return await _svc(request).reset_user(payload.get("user_id") or "demo-trung-binh")


@router.post("/api/session/reset")
async def reset_session(request: Request, session_id: str = Query(...)):
    return await _svc(request).reset_session(session_id)


@router.get("/api/sources/{source_id}")
async def source(source_id: str, request: Request):
    src = await _svc(request).source(source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Không có đoạn này")
    return src
