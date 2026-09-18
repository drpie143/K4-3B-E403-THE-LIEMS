from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import repo_root
from app.errors import ApiError, api_error_handler
from app.router import chat, health, profile, vlearn
from app.service.container import build_container_async

ROOT = repo_root()
STATIC = Path(__file__).parent / "static"
MOCK = ROOT / "app" / "ui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = await build_container_async()
    app.state.container = container
    yield
    await container.aclose()


app = FastAPI(title="VLearn Adaptive Explainer", version="0.2.0", lifespan=lifespan)
app.add_exception_handler(ApiError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(vlearn.router)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(profile.router)
if MOCK.is_dir():
    app.mount("/app", StaticFiles(directory=MOCK, html=True), name="mock")
if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def root():
    if MOCK.is_dir():
        return RedirectResponse("/app/index.html?mode=live")
    index = STATIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"service": "adaptive-explainer"}
