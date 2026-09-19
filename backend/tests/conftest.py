import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.llm.fake import FakeLLM  # noqa: E402
from app.orchestrator import Orchestrator  # noqa: E402


class InMemorySupabase:
    KEYS = {
        "person_accounts": ("id",),
        "person_sessions": ("token_hash",),
        "person_settings": ("user_id",),
        "person_profiles": ("user_id", "concept"),
        "person_strategy_memory": ("user_id", "concept", "strategy"),
        "person_chat_sessions": ("session_id",),
        "lecture_chunks": ("id",),
    }

    def __init__(self):
        self.allow_local_fallback = True
        self.tables = {name: [] for name in self.KEYS}
        self.tables["person_events"] = []
        self._event_id = 0

    def is_configured(self):
        return True

    def _match(self, row, params):
        for key, raw in (params or {}).items():
            if key in {"select", "order", "limit"}:
                continue
            op, _, val = str(raw).partition(".")
            if op == "eq" and str(row.get(key)) != val:
                return False
            if op == "gte" and row.get(key) < self._coerce(val):
                return False
            if op == "lte" and row.get(key) > self._coerce(val):
                return False
        return True

    @staticmethod
    def _coerce(val):
        try:
            return int(val)
        except ValueError:
            return val

    def select(self, table, params=None):
        rows = [dict(r) for r in self.tables.get(table, []) if self._match(r, params or {})]
        order = (params or {}).get("order")
        if order:
            field, _, direction = order.partition(".")
            rows.sort(key=lambda r: r.get(field), reverse=direction == "desc")
        limit = (params or {}).get("limit")
        if limit:
            rows = rows[: int(limit)]
        select = (params or {}).get("select")
        if select and select != "*":
            fields = [f.strip() for f in select.split(",")]
            rows = [{k: r.get(k) for k in fields if k in r} for r in rows]
        return rows

    def upsert(self, table, records):
        payload = records if isinstance(records, list) else [records]
        rows = self.tables.setdefault(table, [])
        keys = self.KEYS.get(table, ("id",))
        for record in payload:
            record = dict(record)
            found = None
            for i, row in enumerate(rows):
                if all(row.get(k) == record.get(k) for k in keys):
                    found = i
                    break
            if found is None:
                rows.append(record)
            else:
                rows[found] = {**rows[found], **record}
        return True

    def insert(self, table, record):
        record = dict(record)
        if table == "person_events":
            self._event_id += 1
            record.setdefault("id", self._event_id)
        self.tables.setdefault(table, []).append(record)
        return dict(record)

    def update(self, table, filter_params, data):
        changed = False
        for row in self.tables.get(table, []):
            if self._match(row, filter_params):
                row.update(data)
                changed = True
        return changed

    def delete(self, table, filter_params):
        rows = self.tables.get(table, [])
        self.tables[table] = [r for r in rows if not self._match(r, filter_params)]
        return True

    def rpc(self, func_name, params, timeout=None):
        return []


@pytest.fixture
def settings(tmp_path):
    s = Settings()
    s.chunks_path = tmp_path / "khong-co.json"  # chạy ở chế độ tóm tắt, không cần data pack
    s.cache_dir = tmp_path / "cache"
    s.trace_dir = tmp_path / "traces"
    s.supabase_url = ""
    s.supabase_key = ""
    return s


@pytest.fixture
def make_orch(settings):
    def _make(script=None, **overrides):
        supabase = overrides.pop("supabase", InMemorySupabase())
        for k, v in overrides.items():
            setattr(settings, k, v)
        return Orchestrator(settings, llm=FakeLLM(script), supabase=supabase)
    return _make


@pytest.fixture
def orch(make_orch):
    return make_orch()
