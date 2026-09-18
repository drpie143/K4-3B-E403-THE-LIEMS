from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "app" / "router").is_dir() and (parent / "app" / "fixtures").is_dir():
            return parent
    raise RuntimeError("Không tìm thấy root repo")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_keys: str = "dev-key"
    storage: str = "memory"
    checkpointer: str = "memory"
    vector_backend: str = "memory"

    dump_first: bool = True
    adaptive_probes: bool = True
    llm_probe: bool = True
    validator_enabled: bool = False
    llm_timeout_seconds: int = 8

    llm_base_url: str = "https://api.x.ai/v1"
    llm_api_key: str = ""
    llm_model: str = "grok-4.6"
    xai_api_key: str = ""

    embedding_provider: str = "fake"
    embedding_dim: int = 1536
    embedding_model: str = "text-embedding-3-small"

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    checkpointer_ttl_minutes: int = 1440

    lease_seconds: int = 45
    stale_processing_seconds: int = 45
    rate_limit_per_min: int = 30

    @property
    def resolved_llm_key(self) -> str:
        return self.llm_api_key or self.xai_api_key

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
