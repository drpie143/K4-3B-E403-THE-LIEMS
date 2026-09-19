"""Learner profile, long-term memory, and chat session state on Supabase."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from .cards import CardStore
from .config import Settings
from .schemas import UNDERSTANDING_LABEL, Notice

RANK = {"chua": 0, "biet_so": 1, "hieu_ro": 2}
BY_RANK = ["chua", "biet_so", "hieu_ro"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


class ProfileStore:
    def __init__(self, settings: Settings, cards: CardStore, supabase: Any | None = None):
        self.s = settings
        self.cards = cards
        self.lock = threading.RLock()
        pp = settings.personas_path
        self.personas: dict[str, dict] = yaml.safe_load(Path(pp).read_text(encoding="utf-8")) if Path(pp).exists() else {}
        if supabase is None:
            from .supabase_client import SupabaseClient

            supabase = SupabaseClient(settings.supabase_url, settings.supabase_key)
        self.sb = supabase
        self.turns: dict[str, int] = {}
        self.stats = {"flushes": 0, "rows": 0, "pulls": 0, "compactions": 0}

    @property
    def remote(self) -> bool:
        return bool(self.sb and self.sb.is_configured())

    def _require_remote(self) -> None:
        if not self.remote:
            raise RuntimeError("Chưa cấu hình Supabase. Điền SUPABASE_URL và SUPABASE_KEY trong backend/.env.")

    def _select(self, table: str, params: dict[str, str]) -> list[dict]:
        self._require_remote()
        return self.sb.select(table, params)

    def _upsert(self, table: str, row: dict | list[dict]) -> None:
        self._require_remote()
        if not self.sb.upsert(table, row):
            raise RuntimeError(f"Không ghi được bảng {table} trên Supabase.")

    def _update(self, table: str, filters: dict[str, str], row: dict) -> None:
        self._require_remote()
        if not self.sb.update(table, filters, row):
            raise RuntimeError(f"Không cập nhật được bảng {table} trên Supabase.")

    def _delete(self, table: str, filters: dict[str, str]) -> None:
        self._require_remote()
        self.sb.delete(table, filters)

    # ------------------------------------------------------------ users
    def ensure_user(self, user_id: str, now: datetime | None = None) -> None:
        with self.lock:
            rows = self._select("person_settings", {"user_id": f"eq.{user_id}", "select": "user_id", "limit": "1"})
            if rows:
                return
            self._seed(user_id, now or utcnow())

    def _seed(self, user_id: str, now: datetime) -> None:
        p = self.personas.get(user_id, {})
        self._upsert("person_settings", {"user_id": user_id, "memory_on": 1, "preferred_style": p.get("preferred_style")})
        profiles = []
        for cid, row in (p.get("concepts") or {}).items():
            ts = iso(now - timedelta(days=row.get("days_ago", 0)))
            profiles.append({
                "user_id": user_id, "concept": cid, "level": row["level"], "streak": 0,
                "source": row.get("source", "tu_khai"), "updated_at": ts, "last_signal_at": ts,
            })
        if profiles:
            self._upsert("person_profiles", profiles)
        strategies = []
        for cid, items in (p.get("strategies") or {}).items():
            for it in items:
                ts = iso(now - timedelta(days=it.get("days_ago", 0)))
                strategies.append({
                    "user_id": user_id, "concept": cid, "strategy": it["strategy"],
                    "worked": it.get("worked", 0), "failed": it.get("failed", 0), "last_at": ts,
                })
        if strategies:
            self._upsert("person_strategy_memory", strategies)

    def reset_user(self, user_id: str, now: datetime | None = None) -> None:
        with self.lock:
            self._delete_rows(user_id, None, include_settings=True)
            self._seed(user_id, now or utcnow())

    def settings(self, user_id: str) -> dict:
        self.ensure_user(user_id)
        rows = self._select("person_settings", {"user_id": f"eq.{user_id}", "select": "*", "limit": "1"})
        r = rows[0] if rows else {"memory_on": 1, "preferred_style": None}
        return {"memory_on": bool(int(r.get("memory_on", 1))), "preferred_style": r.get("preferred_style")}

    def update_settings(self, user_id: str, memory_on: bool | None = None, preferred_style: str | None = None, clear_style: bool = False) -> None:
        self.ensure_user(user_id)
        patch: dict[str, Any] = {}
        if memory_on is not None:
            patch["memory_on"] = int(memory_on)
        if preferred_style is not None or clear_style:
            patch["preferred_style"] = None if clear_style else preferred_style
        if patch:
            self._update("person_settings", {"user_id": f"eq.{user_id}"}, patch)

    # ------------------------------------------------------------ reads
    def profile(self, user_id: str, now: datetime | None = None) -> dict[str, Any]:
        self.ensure_user(user_id)
        now = now or utcnow()
        rows = self._select("person_profiles", {"user_id": f"eq.{user_id}", "select": "*", "limit": "500"})
        concepts = {}
        for r in rows:
            last = parse(r.get("last_signal_at"))
            days = (now - last).days if last else None
            ev = self._select(
                "person_events",
                {"user_id": f"eq.{user_id}", "concept": f"eq.{r['concept']}", "select": "type,created_at", "order": "id.desc", "limit": "5"},
            )
            concepts[r["concept"]] = {
                "level": r.get("level"), "streak": int(r.get("streak", 0)), "source": r.get("source"),
                "updated_at": r.get("updated_at"), "last_signal_at": r.get("last_signal_at"),
                "days_since_signal": days, "stale": days is not None and days > self.s.stale_days,
                "evidence": [f"{e['type']}@{str(e['created_at'])[:10]}" for e in ev],
            }
        strategies: dict[str, dict] = {}
        srows = self._select("person_strategy_memory", {"user_id": f"eq.{user_id}", "select": "*", "limit": "500"})
        for cid in {r["concept"] for r in srows}:
            strategies[cid] = self._strategy_lists(user_id, cid, now, rows=srows)
        return {"user_id": user_id, **self.settings(user_id), "concepts": concepts, "strategies": strategies}

    def _row(self, user_id: str, concept: str) -> dict | None:
        rows = self._select("person_profiles", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}", "select": "*", "limit": "1"})
        return rows[0] if rows else None

    def _strategy_rows(self, user_id: str, concept: str) -> list[dict]:
        return self._select("person_strategy_memory", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}", "select": "*", "limit": "500"})

    def _strategy_lists(self, user_id: str, concept: str, now: datetime, rows: list[dict] | None = None) -> dict[str, list[str]]:
        worked, failed = [], []
        rows = rows if rows is not None else self._strategy_rows(user_id, concept)
        for r in rows:
            if r.get("concept") != concept:
                continue
            last = parse(r.get("last_at"))
            if last and (now - last).days > self.s.strategy_ttl_days:
                continue
            if int(r.get("worked", 0)) >= self.s.worked_min and int(r.get("worked", 0)) > int(r.get("failed", 0)):
                worked.append(r["strategy"])
            elif int(r.get("failed", 0)) >= self.s.failed_min and int(r.get("failed", 0)) > int(r.get("worked", 0)):
                failed.append(r["strategy"])
        return {"worked": sorted(worked), "failed": sorted(failed)}

    def learner_memory(self, user_id: str, concept: str, now: datetime | None = None) -> dict[str, Any]:
        now = now or utcnow()
        st = self.settings(user_id)
        if not st["memory_on"]:
            return {"memory_on": False, "concepts": {}, "worked": [], "failed": [], "preferred_style": None, "stale_any": False}
        card = self.cards.get(concept)
        ids = [concept] + (card.prerequisites if card else [])
        out: dict[str, Any] = {}
        stale_any = False
        for cid in ids:
            r = self._row(user_id, cid)
            if not r or not r.get("level"):
                continue
            last = parse(r.get("last_signal_at"))
            days = (now - last).days if last else 0
            stale = days > self.s.stale_days
            stale_any = stale_any or stale
            eff = BY_RANK[max(0, RANK[r["level"]] - 1)] if stale else r["level"]
            out[cid] = {"level": r["level"], "effective_level": eff, "stale": stale, "days_since_signal": days}
        lists = self._strategy_lists(user_id, concept, now)
        return {"memory_on": True, "concepts": out, **lists, "preferred_style": st["preferred_style"], "stale_any": stale_any}

    # ------------------------------------------------------------ writes
    def _snapshot(self, user_id: str, concept: str) -> dict:
        return {"profile": self._row(user_id, concept), "strategies": self._strategy_rows(user_id, concept)}

    def _log(self, user_id: str, concept: str, etype: str, payload: dict, before: dict, now: datetime) -> int:
        row = {
            "user_id": user_id, "concept": concept, "type": etype,
            "payload": payload, "before_json": before, "created_at": iso(now),
        }
        inserted = self.sb.insert("person_events", row) if hasattr(self.sb, "insert") else None
        if not inserted:
            self._upsert("person_events", row)
            inserted = row
        return int(inserted.get("id", 0) or 0)

    def apply_event(self, user_id: str, concept: str, etype: str, level: str | None = None, now: datetime | None = None) -> Notice | None:
        now = now or utcnow()
        self.ensure_user(user_id)
        explicit = etype == "manual"
        if not explicit and not self.settings(user_id)["memory_on"]:
            return None
        card = self.cards.get(concept)
        name = card.term if card else concept
        with self.lock:
            before = self._snapshot(user_id, concept)
            cur = self._row(user_id, concept) or {"level": None, "streak": 0, "source": None}
            lvl, streak, source = cur.get("level"), int(cur.get("streak") or 0), cur.get("source")
            text, kind = None, "info"
            if etype in ("self_report", "manual"):
                if lvl == level:
                    self._touch(user_id, concept, lvl, streak, source, now)
                    return None
                lvl, streak, source = level, 0, "tu_doi" if explicit else "tu_khai"
                text, kind = f"Đã ghi {name}: {UNDERSTANDING_LABEL[level]} ({'bạn tự đổi' if explicit else 'bạn tự khai'}).", "up"
            elif etype in ("confused", "level_down"):
                r = RANK[lvl] if lvl else 1
                nxt = BY_RANK[max(0, r - 1)]
                streak = 0
                if lvl != nxt:
                    lvl, source = nxt, "doi_muc"
                    text, kind = f"Mình hạ {name} xuống “{UNDERSTANDING_LABEL[nxt]}” để lần sau giải thích dễ hơn.", "down"
            elif etype == "check_correct":
                streak += 1
                r = RANK[lvl] if lvl else 0
                if streak >= 2 and r < 2:
                    lvl, streak, source = BY_RANK[r + 1], 0, "kiem_tra"
                    text, kind = f"Bạn trả lời đúng 2 lần liên tiếp, mình nâng {name} lên “{UNDERSTANDING_LABEL[lvl]}”. Lần sau mình sẽ bớt giảng lại phần nền.", "up"
                elif r >= 2:
                    text, kind = f"Ghi nhận: bạn vẫn nắm chắc {name}.", "up"
                else:
                    lvl = lvl or "chua"
                    text, kind = f"Ghi nhận 1 lần trả lời đúng về {name}. Mức vẫn là “{UNDERSTANDING_LABEL[lvl]}” - đúng thêm 1 lần nữa mình mới nâng.", "up"
            elif etype == "check_wrong":
                streak, lvl = 0, lvl or "chua"
            else:
                raise ValueError(f"Sự kiện không hỗ trợ: {etype}")
            self._touch(user_id, concept, lvl, streak, source, now)
            eid = self._log(user_id, concept, etype, {"level": level}, before, now)
        return Notice(text=text, kind=kind, event_ids=[eid]) if text else None

    def _touch(self, user_id: str, concept: str, lvl, streak, source, now: datetime) -> None:
        self._upsert("person_profiles", {
            "user_id": user_id, "concept": concept, "level": lvl, "streak": streak,
            "source": source, "updated_at": iso(now), "last_signal_at": iso(now),
        })

    def record_strategy(self, user_id: str, concept: str, strategies: list[str], outcome: str, now: datetime | None = None) -> None:
        if outcome not in ("worked", "failed"):
            raise ValueError(outcome)
        strategies = [s for s in strategies if s and not s.endswith(":None")]
        if not strategies or not self.settings(user_id)["memory_on"]:
            return
        now = now or utcnow()
        with self.lock:
            before = self._snapshot(user_id, concept)
            for sname in strategies:
                existing = self._strategy_rows(user_id, concept)
                row = next((r for r in existing if r.get("strategy") == sname), None)
                worked = int(row.get("worked", 0)) if row else 0
                failed = int(row.get("failed", 0)) if row else 0
                if outcome == "worked":
                    worked += 1
                else:
                    failed += 1
                self._upsert("person_strategy_memory", {
                    "user_id": user_id, "concept": concept, "strategy": sname,
                    "worked": worked, "failed": failed, "last_at": iso(now),
                })
            self._log(user_id, concept, f"strategy_{outcome}", {"strategies": strategies}, before, now)

    def undo(self, user_id: str, event_id: int) -> bool:
        with self.lock:
            rows = self._select("person_events", {"id": f"eq.{event_id}", "user_id": f"eq.{user_id}", "select": "*", "limit": "1"})
            if not rows:
                return False
            ev = rows[0]
            snap = ev.get("before_json") or {}
            if isinstance(snap, str):
                snap = json.loads(snap)
            concept = ev["concept"]
            self._delete("person_profiles", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}"})
            self._delete("person_strategy_memory", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}"})
            if snap.get("profile"):
                self._upsert("person_profiles", snap["profile"])
            if snap.get("strategies"):
                self._upsert("person_strategy_memory", snap["strategies"])
            self._delete("person_events", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}", "id": f"gte.{event_id}"})
        return True

    def _delete_rows(self, user_id: str, concept: str | None, include_settings: bool = False) -> None:
        f = {"user_id": f"eq.{user_id}"}
        cf = {**f, "concept": f"eq.{concept}"} if concept else f
        for table in ("person_profiles", "person_strategy_memory", "person_events"):
            self._delete(table, cf)
        if include_settings:
            self._delete("person_settings", f)
            self._delete("person_chat_sessions", f)

    def delete(self, user_id: str, concept: str | None = None) -> None:
        with self.lock:
            self._delete_rows(user_id, concept)

    def delete_all_user(self, user_id: str) -> None:
        with self.lock:
            self._delete_rows(user_id, None, include_settings=True)

    def delete_strategy(self, user_id: str, concept: str, strategy: str) -> None:
        with self.lock:
            self._delete("person_strategy_memory", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}", "strategy": f"eq.{strategy}"})

    # ----------------------------------------------- memory cadence
    def note_turn(self, user_id: str) -> dict:
        self.turns[user_id] = self.turns.get(user_id, 0) + 1
        n = self.turns[user_id]
        info = {"turn": n, "compacted": False, "flushed": 0}
        every = max(1, int(getattr(self.s, "memory_compact_every", 10)))
        if n % every == 0:
            info["compacted"] = bool(self.compact(user_id))
        return info

    def flush(self) -> int:
        return 0

    def compact(self, user_id: str, now: datetime | None = None) -> dict:
        now = now or utcnow()
        keep = max(1, int(getattr(self.s, "memory_max_strategies", 6)))
        max_events = max(5, int(getattr(self.s, "memory_max_events", 50)))
        ttl_dt = now - timedelta(days=self.s.strategy_ttl_days)
        removed = {"stale": 0, "extra": 0, "person_events": 0}
        with self.lock:
            rows = self._select("person_strategy_memory", {"user_id": f"eq.{user_id}", "select": "*", "limit": "1000"})
            for r in rows:
                last = parse(r.get("last_at"))
                if last and last < ttl_dt:
                    self._forget_strategy(user_id, r["concept"], r["strategy"])
                    removed["stale"] += 1
            by_concept: dict[str, list[dict]] = {}
            for r in rows:
                by_concept.setdefault(r["concept"], []).append(r)
            for concept, items in by_concept.items():
                items.sort(key=lambda r: (int(r.get("worked", 0)) - int(r.get("failed", 0)), str(r.get("last_at", ""))), reverse=True)
                for r in items[keep:]:
                    self._forget_strategy(user_id, concept, r["strategy"])
                    removed["extra"] += 1
            events = self._select("person_events", {"user_id": f"eq.{user_id}", "select": "id", "order": "id.desc", "limit": "1000"})
            for r in events[max_events:]:
                self._delete("person_events", {"id": f"eq.{r['id']}", "user_id": f"eq.{user_id}"})
                removed["person_events"] += 1
        self.stats["compactions"] += 1
        return removed if any(removed.values()) else {}

    def _forget_strategy(self, user_id: str, concept: str, strategy: str) -> None:
        self._delete("person_strategy_memory", {"user_id": f"eq.{user_id}", "concept": f"eq.{concept}", "strategy": f"eq.{strategy}"})

    def trim_session(self, state: dict) -> dict:
        cap = max(2, int(getattr(self.s, "session_max_tried", 8)))
        state = dict(state)
        tried = state.get("tried") or {}
        state["tried"] = {k: list(v)[-cap:] for k, v in tried.items()}
        last = state.get("last") or {}
        if len(last) > cap:
            state["last"] = dict(list(last.items())[-cap:])
        if isinstance(state.get("last_question"), str):
            state["last_question"] = state["last_question"][:500]
        return state

    def memory_health(self) -> dict:
        return {
            "remote": self.remote,
            "flush_every": getattr(self.s, "memory_flush_every", 3),
            "compact_every": getattr(self.s, "memory_compact_every", 10),
            "max_strategies": getattr(self.s, "memory_max_strategies", 6),
            "max_events": getattr(self.s, "memory_max_events", 50),
            "pending_rows": 0,
            **self.stats,
        }

    # ------------------------------------------------------------ sessions
    def session(self, session_id: str, user_id: str) -> dict:
        rows = self._select("person_chat_sessions", {"session_id": f"eq.{session_id}", "user_id": f"eq.{user_id}", "select": "state_json", "limit": "1"})
        if rows:
            state = rows[0].get("state_json") or {}
            return json.loads(state) if isinstance(state, str) else state
        return {"answered": {}, "last": {}, "last_concept": None, "thumbs_down": {}, "wrong": {}, "check_attempt": {}, "tried": {}, "last_question": ""}

    def save_session(self, session_id: str, user_id: str, state: dict) -> None:
        with self.lock:
            self._upsert("person_chat_sessions", {
                "session_id": session_id,
                "user_id": user_id,
                "state_json": self.trim_session(state),
                "updated_at": iso(utcnow()),
            })

    def reset_session(self, session_id: str, user_id: str | None = None) -> None:
        filters = {"session_id": f"eq.{session_id}"}
        if user_id is not None:
            filters["user_id"] = f"eq.{user_id}"
        with self.lock:
            self._delete("person_chat_sessions", filters)
