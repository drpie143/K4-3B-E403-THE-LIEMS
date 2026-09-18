from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def envelope(code: str, message: str, request_id: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
    )


class ApiError(HTTPException):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(status_code=status, detail=message)
        self.code = code
        self.message = message


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    rid = request.headers.get("X-Request-Id") or str(uuid4())
    return envelope(exc.code, exc.message, rid, exc.status_code)
