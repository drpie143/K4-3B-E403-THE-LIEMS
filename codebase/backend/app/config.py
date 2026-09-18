"""Cấu hình đọc từ biến môi trường (và file .env nếu có). Không bao giờ in key ra log."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
CODEBASE_DIR = BACKEND_DIR.parent

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-opus-5",
    "gemini": "gemini-2.5-flash",
    "fake": "fake",
}


def _load_dotenv(path: Path) -> None:
    """Đọc .env đơn giản (KEY=VALUE), ưu tiên giá trị được khai báo trong .env."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        val = value.strip().strip('"').strip("'")
        if val:
            os.environ[key.strip()] = val


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    llm_provider: str = "fake"
    llm_model: str = "fake"
    llm_model_explain: str = ""
    llm_model_judge: str = ""
    llm_timeout: float = 20.0
    llm_max_retries: int = 2
    use_judge: bool = True
    replay: bool = False
    trace_text: bool = False
    trace_prompts: bool = True
    retrieval_min_score: float = 1.0
    retrieval_top_k: int = 5
    passages_for_llm: int = 3
    passage_max_chars: int = 900
    confidence_survey_threshold: float = 0.6
    stale_days: int = 14
    strategy_ttl_days: int = 30
    worked_min: int = 1
    failed_min: int = 2
    reask_seconds: int = 180
    max_thumbs_down: int = 2
    max_wrong_checks: int = 2
    retrieval_mode: str = "hybrid"  # "hybrid" | "bm25" | "dense"
    hybrid_alpha: float = 0.5       # Trọng số kết hợp BM25 và Dense (0.0: thuần dense, 1.0: thuần bm25)
    rrf_k: int = 60                 # Hằng số Reciprocal Rank Fusion
    embedding_provider: str = ""    # "openai" | "gemini" (nếu để trống, theo llm_provider)
    embedding_model: str = ""       # "text-embedding-3-small" hoặc "text-embedding-004"
    supabase_url: str = ""
    supabase_key: str = ""
    cards_dir: Path = field(default_factory=lambda: BACKEND_DIR / "cards")
    personas_path: Path = field(default_factory=lambda: BACKEND_DIR / "personas.yaml")
    prompts_dir: Path = field(default_factory=lambda: BACKEND_DIR / "app" / "prompts")
    chunks_path: Path = field(default_factory=lambda: CODEBASE_DIR / "data" / "chunks.local.json")
    transcripts_dir: Path = field(default_factory=lambda: BACKEND_DIR / "Data" / "transcript")
    db_path: Path = field(default_factory=lambda: BACKEND_DIR / "p3.db")
    trace_dir: Path = field(default_factory=lambda: BACKEND_DIR / "traces")
    cache_dir: Path = field(default_factory=lambda: BACKEND_DIR / ".cache")
    mock_dir: Path = field(default_factory=lambda: CODEBASE_DIR / "mock")

    @property
    def model_explain(self) -> str:
        return self.llm_model_explain or self.llm_model

    @property
    def model_judge(self) -> str:
        return self.llm_model_judge or self.llm_model


def load_settings(env_file: Path | None = None) -> Settings:
    _load_dotenv(env_file or BACKEND_DIR / ".env")
    env = os.environ
    provider = env.get("LLM_PROVIDER", "fake").strip().lower()
    s = Settings(
        llm_provider=provider,
        llm_model=env.get("LLM_MODEL", DEFAULT_MODELS.get(provider, "fake")),
        llm_model_explain=env.get("LLM_MODEL_EXPLAIN", ""),
        llm_model_judge=env.get("LLM_MODEL_JUDGE", ""),
        llm_timeout=float(env.get("LLM_TIMEOUT", "20")),
        llm_max_retries=int(env.get("LLM_MAX_RETRIES", "2")),
        use_judge=_flag("USE_JUDGE", True),
        replay=_flag("REPLAY", False),
        trace_text=_flag("TRACE_TEXT", False),
        trace_prompts=_flag("TRACE_PROMPTS", True),
        retrieval_min_score=float(env.get("RETRIEVAL_MIN_SCORE", "1.0")),
        stale_days=int(env.get("STALE_DAYS", "14")),
        strategy_ttl_days=int(env.get("STRATEGY_TTL_DAYS", "30")),
        retrieval_mode=env.get("RETRIEVAL_MODE", "hybrid").strip().lower(),
        hybrid_alpha=float(env.get("HYBRID_ALPHA", "0.5")),
        rrf_k=int(env.get("RRF_K", "60")),
        embedding_provider=env.get("EMBEDDING_PROVIDER", "").strip().lower(),
        embedding_model=env.get("EMBEDDING_MODEL", "").strip(),
        supabase_url=env.get("SUPABASE_URL", "").strip(),
        supabase_key=env.get("SUPABASE_KEY", "").strip(),
    )
    for key, attr in [("CHUNKS_PATH", "chunks_path"), ("DB_PATH", "db_path"), ("TRACE_DIR", "trace_dir"), ("CACHE_DIR", "cache_dir"), ("TRANSCRIPTS_DIR", "transcripts_dir")]:
        if env.get(key):
            setattr(s, attr, Path(env[key]))
    return s
