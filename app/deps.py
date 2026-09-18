from __future__ import annotations

from collections import defaultdict, deque
from time import time

from fastapi import Header, Request

from app.errors import ApiError
from app.service.errors import AppError
from app.service.container import AppContainer
from app.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)


def container(request: Request) -> AppContainer:
    return request.app.state.container


async def require_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    settings = get_settings()
    if not x_api_key or x_api_key not in settings.api_key_set:
        raise ApiError(401, "unauthorized", "Thiếu hoặc sai X-API-Key.")
    return x_api_key


def rate_limit(user_id: str) -> None:
    q = _hits[user_id]
    now = time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= get_settings().rate_limit_per_min:
        raise ApiError(429, "rate_limited", "Quá 30 lượt/phút.")
    q.append(now)


def http_from_app(exc: AppError) -> ApiError:
    return ApiError(exc.http_status, exc.code, exc.message)
