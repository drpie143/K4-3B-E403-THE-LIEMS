"""Cấu hình đọc từ biến môi trường (và file .env nếu có). Không bao giờ in key ra log."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent          # gốc repo: backend/ và frontend/ nằm cạnh nhau

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
    # Chỉ gọi LLM chấm khi câu trả lời có câu tự viết (không nằm trong phần đã duyệt).
    judge_only_when_novel: bool = True
    # Soạn sẵn lời giải thích theo quyết định của luật, song song với lúc LLM chẩn đoán.
    speculative_explain: bool = True
    replay: bool = False
    trace_text: bool = False
    trace_prompts: bool = True
    retrieval_min_score: float = 1.0
    retrieval_top_k: int = 6
    # Câu trả lời chỉ được dùng chất liệu trong <passages>. Đưa ít đoạn / đoạn bị cắt cụt thì
    # mô hình không có gì để nói thêm ngoài mấy câu chốt → trả lời cụt. Nới ở v5 để bài giảng
    # đủ chi tiết cho một lời giải thích đầy đặn mà vẫn bám nguồn.
    passages_for_llm: int = 5
    passage_max_chars: int = 1400
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
    dense_timeout: float = 4.0      # Trần chờ vector search trên Supabase mỗi câu hỏi
    embedding_provider: str = ""    # "openai" | "gemini" (nếu để trống, theo llm_provider)
    embedding_model: str = ""       # "text-embedding-3-small" hoặc "text-embedding-004"
    embedding_dimensions: int = 768  # Supabase hiện dùng vector(768); OpenAI text-embedding-3-small hỗ trợ rút chiều
    supabase_url: str = ""
    supabase_key: str = ""
    memory_flush_every: int = 3        # bao nhiêu lượt hỏi thì đẩy bộ nhớ lên Supabase
    memory_compact_every: int = 10     # bao nhiêu lượt thì nén bộ nhớ dài hạn
    memory_max_strategies: int = 6     # số cách giải thích tối đa nhớ cho mỗi khái niệm
    memory_max_events: int = 50        # số sự kiện tối đa giữ lại cho mỗi người học
    session_max_tried: int = 8         # số kiểu trình bày đã thử giữ trong trạng thái phiên
    cards_dir: Path = field(default_factory=lambda: BACKEND_DIR / "cards")
    personas_path: Path = field(default_factory=lambda: BACKEND_DIR / "personas.yaml")
    prompts_dir: Path = field(default_factory=lambda: BACKEND_DIR / "app" / "prompts")
    chunks_path: Path = field(default_factory=lambda: ROOT_DIR / "data" / "chunks.local.json")
    transcripts_dir: Path = field(default_factory=lambda: BACKEND_DIR / "Data" / "transcript")
    trace_dir: Path = field(default_factory=lambda: BACKEND_DIR / "traces")
    cache_dir: Path = field(default_factory=lambda: BACKEND_DIR / ".cache")
    frontend_dir: Path = field(default_factory=lambda: ROOT_DIR / "frontend")

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
        judge_only_when_novel=_flag("JUDGE_ONLY_WHEN_NOVEL", True),
        speculative_explain=_flag("SPECULATIVE_EXPLAIN", True),
        replay=_flag("REPLAY", False),
        trace_text=_flag("TRACE_TEXT", False),
        trace_prompts=_flag("TRACE_PROMPTS", True),
        retrieval_min_score=float(env.get("RETRIEVAL_MIN_SCORE", "1.0")),
        stale_days=int(env.get("STALE_DAYS", "14")),
        strategy_ttl_days=int(env.get("STRATEGY_TTL_DAYS", "30")),
        retrieval_mode=env.get("RETRIEVAL_MODE", "hybrid").strip().lower(),
        hybrid_alpha=float(env.get("HYBRID_ALPHA", "0.5")),
        rrf_k=int(env.get("RRF_K", "60")),
        dense_timeout=float(env.get("DENSE_TIMEOUT", "4")),
        embedding_provider=env.get("EMBEDDING_PROVIDER", "").strip().lower(),
        embedding_model=env.get("EMBEDDING_MODEL", "").strip(),
        embedding_dimensions=int(env.get("EMBEDDING_DIMENSIONS", "768") or "0"),
        supabase_url=env.get("SUPABASE_URL", "").strip(),
        supabase_key=env.get("SUPABASE_KEY", "").strip(),
        memory_flush_every=int(env.get("MEMORY_FLUSH_EVERY", "3")),
        memory_compact_every=int(env.get("MEMORY_COMPACT_EVERY", "10")),
        memory_max_strategies=int(env.get("MEMORY_MAX_STRATEGIES", "6")),
        memory_max_events=int(env.get("MEMORY_MAX_EVENTS", "50")),
    )
    for key, attr in [("CHUNKS_PATH", "chunks_path"), ("TRACE_DIR", "trace_dir"), ("CACHE_DIR", "cache_dir"), ("TRANSCRIPTS_DIR", "transcripts_dir")]:
        if env.get(key):
            setattr(s, attr, Path(env[key]))
    return s
