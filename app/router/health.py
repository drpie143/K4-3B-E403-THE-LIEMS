from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request

from app.errors import envelope

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request):
    c = request.app.state.container
    repo_ok = await c.repository.health()
    vector_ok = await c.retriever.health()
    body = {
        "status": "ok" if repo_ok and vector_ok else "fail",
        "storage": c.storage_kind,
        "vector": c.vector_kind,
        "postgres": "ok" if c.storage_kind == "postgres" and repo_ok else ("skipped" if c.storage_kind != "postgres" else "down"),
        "qdrant": "ok" if c.vector_kind == "qdrant" and vector_ok else ("skipped" if c.vector_kind != "qdrant" else "down"),
        "redis": "ok" if c.redis_ok else ("skipped" if c.settings.checkpointer != "redis" else "down"),
        "dump_first": c.settings.dump_first,
        "llm_live": c.ai.live,
    }
    if body["status"] != "ok":
        return envelope("dependency_unavailable", "dependency down", str(uuid4()), 503)
    return body
