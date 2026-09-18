import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.llm.fake import FakeLLM  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402


@pytest.fixture
def settings(tmp_path):
    s = Settings()
    s.chunks_path = tmp_path / "khong-co.json"  # chạy ở chế độ tóm tắt, không cần data pack
    s.db_path = tmp_path / "p3.db"
    s.cache_dir = tmp_path / "cache"
    s.trace_dir = tmp_path / "traces"
    return s


@pytest.fixture
def make_orch(settings):
    def _make(script=None, **overrides):
        for k, v in overrides.items():
            setattr(settings, k, v)
        return Orchestrator(settings, llm=FakeLLM(script))
    return _make


@pytest.fixture
def orch(make_orch):
    return make_orch()
