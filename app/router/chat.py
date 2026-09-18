from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.deps import http_from_app, rate_limit, require_key
from app.schema.chat import ChatRequest, ChatResponse
from app.service.errors import AppError

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    _: str = Depends(require_key),
):
    rate_limit(req.user_id)
    try:
        return await request.app.state.container.chat.handle(req)
    except AppError as exc:
        raise http_from_app(exc) from exc


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    _: str = Depends(require_key),
):
    rate_limit(req.user_id)

    async def events():
        try:
            resp = await request.app.state.container.chat.handle(req)
            payload = resp.model_dump(mode="json")
            content = payload.get("content") or ""
            yield f"event: meta\ndata: {json.dumps({k: payload[k] for k in payload if k != 'content'})}\n\n"
            chunk = 80
            for i in range(0, len(content), chunk):
                yield f"event: token\ndata: {json.dumps({'text': content[i:i+chunk]})}\n\n"
            yield f"event: done\ndata: {json.dumps(payload)}\n\n"
        except AppError as exc:
            yield f"event: error\ndata: {json.dumps({'code': exc.code, 'message': exc.message})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
