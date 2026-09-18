from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.deps import http_from_app, require_key
from app.service.errors import AppError

router = APIRouter(prefix="/v1", tags=["profile"])


@router.get("/profile/{user_id}")
async def profile(user_id: str, request: Request, _: str = Depends(require_key)):
    try:
        return await request.app.state.container.profile.get_profile(user_id)
    except AppError as exc:
        raise http_from_app(exc) from exc


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    _: str = Depends(require_key),
):
    try:
        return await request.app.state.container.profile.get_conversation(conversation_id)
    except AppError as exc:
        raise http_from_app(exc) from exc
