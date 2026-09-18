"""Đồng bộ bộ nhớ dài hạn với Supabase — và giữ cho nó không phình.

Ba việc:
  1. **Nạp về (pull)** — lần đầu một tài khoản dùng máy này, kéo hồ sơ + bộ nhớ từ Supabase
     xuống SQLite để mọi truy vấn sau đó chạy cục bộ, không tốn round-trip.
  2. **Ghi trễ (write-behind)** — mỗi lượt hỏi không đẩy ngay lên mạng; gom vào hàng đợi và
     chỉ đẩy sau mỗi MEMORY_FLUSH_EVERY lượt (hoặc khi người dùng đăng xuất / gọi /api/profile).
  3. **Nén (compaction)** — mỗi MEMORY_COMPACT_EVERY lượt: bỏ chiến lược quá hạn, chỉ giữ
     N chiến lược tốt nhất cho mỗi khái niệm, cắt bớt nhật ký sự kiện cũ.

Nhờ (2) và (3), số dòng trên Supabase của một người học là hữu hạn:
  profiles ≤ số khái niệm · strategy_memory ≤ số khái niệm × MEMORY_MAX_STRATEGIES
  events ≤ MEMORY_MAX_EVENTS · sessions = 1 dòng cho mỗi phiên.
"""
from __future__ import annotations

from typing import Any

TABLES = ("person_profiles", "person_strategy_memory", "person_settings", "person_events", "person_chat_sessions")


class MemorySync:
    def __init__(self, supabase: Any, settings: Any):
        self.sb = supabase
        self.s = settings
        self.queue: dict[str, dict[str, dict]] = {t: {} for t in TABLES}
        self.turns: dict[str, int] = {}
        self.pulled: set[str] = set()
        self.stats = {"flushes": 0, "rows": 0, "pulls": 0, "compactions": 0}

    @property
    def enabled(self) -> bool:
        return bool(self.sb and self.sb.is_configured())

    # ------------------------------------------------------------ ghi trễ
    def put(self, table: str, key: str, row: dict) -> None:
        """Xếp hàng một dòng; dòng cùng khoá ghi đè nhau nên hàng đợi không phình."""
        if not self.enabled:
            return
        self.queue.setdefault(table, {})[key] = row

    def append(self, table: str, key: str, row: dict) -> None:
        self.put(table, key, row)

    def pending(self) -> int:
        return sum(len(v) for v in self.queue.values())

    def tick(self, user_id: str) -> int:
        """Đếm một lượt hỏi của người học; trả về số lượt đã tính."""
        self.turns[user_id] = self.turns.get(user_id, 0) + 1
        return self.turns[user_id]

    def should_flush(self, user_id: str) -> bool:
        every = max(1, int(getattr(self.s, "memory_flush_every", 3)))
        return self.enabled and self.turns.get(user_id, 0) % every == 0

    def should_compact(self, user_id: str) -> bool:
        every = max(1, int(getattr(self.s, "memory_compact_every", 10)))
        return self.turns.get(user_id, 0) % every == 0

    def flush(self) -> int:
        """Đẩy toàn bộ hàng đợi lên Supabase. Trả về số dòng đã đẩy."""
        if not self.enabled:
            return 0
        sent = 0
        for table, rows in self.queue.items():
            if not rows:
                continue
            batch = list(rows.values())
            if self.sb.upsert(table, batch):
                sent += len(batch)
                rows.clear()
        if sent:
            self.stats["flushes"] += 1
            self.stats["rows"] += sent
        return sent

    # -------------------------------------------------------------- nạp về
    def pull(self, user_id: str) -> dict[str, list[dict]]:
        """Kéo hồ sơ + bộ nhớ của một tài khoản từ Supabase (một lần cho mỗi tiến trình)."""
        if not self.enabled or user_id in self.pulled:
            return {}
        self.pulled.add(user_id)
        out = {}
        for table in ("person_settings", "person_profiles", "person_strategy_memory"):
            out[table] = self.sb.select(table, {"user_id": f"eq.{user_id}", "select": "*", "limit": "500"})
        self.stats["pulls"] += 1
        return out

    # ---------------------------------------------------------------- xoá
    def drop(self, table: str, filters: dict[str, str]) -> None:
        if self.enabled:
            self.sb.delete(table, filters)

    def health(self) -> dict:
        return {
            "remote": self.enabled,
            "flush_every": getattr(self.s, "memory_flush_every", 3),
            "compact_every": getattr(self.s, "memory_compact_every", 10),
            "max_strategies": getattr(self.s, "memory_max_strategies", 6),
            "max_events": getattr(self.s, "memory_max_events", 50),
            "pending_rows": self.pending(),
            **self.stats,
        }
