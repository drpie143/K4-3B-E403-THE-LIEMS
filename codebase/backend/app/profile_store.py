"""Hồ sơ học viên, bộ nhớ dài hạn (§7.4) và trạng thái phiên — SQLite.

Chỉ code ghi vào đây; LLM không bao giờ ghi trực tiếp.
"""
from __future__ import annotations

import json
import sqlite3
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

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  user_id TEXT, concept TEXT, level TEXT, streak INT DEFAULT 0, source TEXT,
  updated_at TEXT, last_signal_at TEXT, PRIMARY KEY (user_id, concept));
CREATE TABLE IF NOT EXISTS strategy_memory (
  user_id TEXT, concept TEXT, strategy TEXT, worked INT DEFAULT 0, failed INT DEFAULT 0,
  last_at TEXT, PRIMARY KEY (user_id, concept, strategy));
CREATE TABLE IF NOT EXISTS settings (
  user_id TEXT PRIMARY KEY, memory_on INT DEFAULT 1, preferred_style TEXT);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, concept TEXT, type TEXT,
  payload TEXT, before_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY, user_id TEXT, state_json TEXT, updated_at TEXT);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


class ProfileStore:
    def __init__(self, settings: Settings, cards: CardStore, db_path: Path | None = None):
        self.s = settings
        self.cards = cards
        path = str(db_path or settings.db_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.lock = threading.RLock()
        pp = settings.personas_path
        self.personas: dict[str, dict] = yaml.safe_load(Path(pp).read_text(encoding="utf-8")) if Path(pp).exists() else {}

    # ------------------------------------------------------------ users
    def ensure_user(self, user_id: str, now: datetime | None = None) -> None:
        with self.lock:
            if self.db.execute("SELECT 1 FROM settings WHERE user_id=?", (user_id,)).fetchone():
                return
            self._seed(user_id, now or utcnow())

    def _seed(self, user_id: str, now: datetime) -> None:
        p = self.personas.get(user_id, {})
        self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?,?)", (user_id, 1, p.get("preferred_style")))
        for cid, row in (p.get("concepts") or {}).items():
            ts = iso(now - timedelta(days=row.get("days_ago", 0)))
            self.db.execute(
                "INSERT OR REPLACE INTO profiles VALUES (?,?,?,?,?,?,?)",
                (user_id, cid, row["level"], 0, row.get("source", "tu_khai"), ts, ts),
            )
        for cid, items in (p.get("strategies") or {}).items():
            for it in items:
                ts = iso(now - timedelta(days=it.get("days_ago", 0)))
                self.db.execute(
                    "INSERT OR REPLACE INTO strategy_memory VALUES (?,?,?,?,?,?)",
                    (user_id, cid, it["strategy"], it.get("worked", 0), it.get("failed", 0), ts),
                )
        self.db.commit()

    def reset_user(self, user_id: str, now: datetime | None = None) -> None:
        with self.lock:
            self._delete_rows(user_id, None, include_settings=True)
            self._seed(user_id, now or utcnow())

    def settings(self, user_id: str) -> dict:
        self.ensure_user(user_id)
        r = self.db.execute("SELECT memory_on, preferred_style FROM settings WHERE user_id=?", (user_id,)).fetchone()
        return {"memory_on": bool(r["memory_on"]), "preferred_style": r["preferred_style"]}

    def update_settings(self, user_id: str, memory_on: bool | None = None, preferred_style: str | None = None, clear_style: bool = False) -> None:
        self.ensure_user(user_id)
        with self.lock:
            if memory_on is not None:
                self.db.execute("UPDATE settings SET memory_on=? WHERE user_id=?", (int(memory_on), user_id))
            if preferred_style is not None or clear_style:
                self.db.execute("UPDATE settings SET preferred_style=? WHERE user_id=?", (None if clear_style else preferred_style, user_id))
            self.db.commit()

    # ------------------------------------------------------------ reads
    def profile(self, user_id: str, now: datetime | None = None) -> dict[str, Any]:
        self.ensure_user(user_id)
        now = now or utcnow()
        rows = self.db.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,)).fetchall()
        concepts = {}
        for r in rows:
            last = parse(r["last_signal_at"])
            days = (now - last).days if last else None
            ev = self.db.execute(
                "SELECT type, created_at FROM events WHERE user_id=? AND concept=? ORDER BY id DESC LIMIT 5",
                (user_id, r["concept"]),
            ).fetchall()
            concepts[r["concept"]] = {
                "level": r["level"], "streak": r["streak"], "source": r["source"],
                "updated_at": r["updated_at"], "last_signal_at": r["last_signal_at"],
                "days_since_signal": days, "stale": days is not None and days > self.s.stale_days,
                "evidence": [f"{e['type']}@{e['created_at'][:10]}" for e in ev],
            }
        strategies: dict[str, dict] = {}
        for cid in {r["concept"] for r in self.db.execute("SELECT concept FROM strategy_memory WHERE user_id=?", (user_id,))}:
            strategies[cid] = self._strategy_lists(user_id, cid, now)
        return {"user_id": user_id, **self.settings(user_id), "concepts": concepts, "strategies": strategies}

    def _row(self, user_id: str, concept: str) -> dict | None:
        r = self.db.execute("SELECT * FROM profiles WHERE user_id=? AND concept=?", (user_id, concept)).fetchone()
        return dict(r) if r else None

    def _strategy_rows(self, user_id: str, concept: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM strategy_memory WHERE user_id=? AND concept=?", (user_id, concept))]

    def _strategy_lists(self, user_id: str, concept: str, now: datetime) -> dict[str, list[str]]:
        worked, failed = [], []
        for r in self._strategy_rows(user_id, concept):
            last = parse(r["last_at"])
            if last and (now - last).days > self.s.strategy_ttl_days:
                continue
            if r["worked"] >= self.s.worked_min and r["worked"] > r["failed"]:
                worked.append(r["strategy"])
            elif r["failed"] >= self.s.failed_min and r["failed"] > r["worked"]:
                failed.append(r["strategy"])
        return {"worked": sorted(worked), "failed": sorted(failed)}

    def learner_memory(self, user_id: str, concept: str, now: datetime | None = None) -> dict[str, Any]:
        """JSON gọn gửi cho LLM (§7.4.5): chỉ khái niệm đang hỏi + khái niệm nền."""
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
            if not r or not r["level"]:
                continue
            last = parse(r["last_signal_at"])
            days = (now - last).days if last else 0
            stale = days > self.s.stale_days
            stale_any = stale_any or stale
            eff = BY_RANK[max(0, RANK[r["level"]] - 1)] if stale else r["level"]
            out[cid] = {"level": r["level"], "effective_level": eff, "stale": stale, "days_since_signal": days}
        lists = self._strategy_lists(user_id, concept, now)
        return {"memory_on": True, "concepts": out, **lists, "preferred_style": st["preferred_style"], "stale_any": stale_any}

    # ------------------------------------------------------------ writes
    def _snapshot(self, user_id: str, concept: str) -> str:
        return json.dumps({"profile": self._row(user_id, concept), "strategies": self._strategy_rows(user_id, concept)}, ensure_ascii=False)

    def _log(self, user_id: str, concept: str, etype: str, payload: dict, before: str, now: datetime) -> int:
        cur = self.db.execute(
            "INSERT INTO events (user_id, concept, type, payload, before_json, created_at) VALUES (?,?,?,?,?,?)",
            (user_id, concept, etype, json.dumps(payload, ensure_ascii=False), before, iso(now)),
        )
        return int(cur.lastrowid)

    def apply_event(self, user_id: str, concept: str, etype: str, level: str | None = None, now: datetime | None = None) -> Notice | None:
        """Quy tắc mức hiểu (port applyEvent của mock)."""
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
            lvl, streak, source = cur["level"], cur["streak"] or 0, cur["source"]
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
                    text, kind = f"Ghi nhận 1 lần trả lời đúng về {name}. Mức vẫn là “{UNDERSTANDING_LABEL[lvl]}” — đúng thêm 1 lần nữa mình mới nâng.", "up"
            elif etype == "check_wrong":
                streak, lvl = 0, lvl or "chua"
            else:
                raise ValueError(f"Sự kiện không hỗ trợ: {etype}")
            self._touch(user_id, concept, lvl, streak, source, now)
            eid = self._log(user_id, concept, etype, {"level": level}, before, now)
            self.db.commit()
        return Notice(text=text, kind=kind, event_ids=[eid]) if text else None

    def _touch(self, user_id: str, concept: str, lvl, streak, source, now: datetime) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO profiles VALUES (?,?,?,?,?,?,?)",
            (user_id, concept, lvl, streak, source, iso(now), iso(now)),
        )
        self.db.commit()

    def record_strategy(self, user_id: str, concept: str, strategies: list[str], outcome: str, now: datetime | None = None) -> None:
        """Ghi cách giải thích đã hiệu quả / chưa hiệu quả (§7.4.3)."""
        if outcome not in ("worked", "failed"):
            raise ValueError(outcome)
        strategies = [s for s in strategies if s and not s.endswith(":None")]
        if not strategies or not self.settings(user_id)["memory_on"]:
            return
        now = now or utcnow()
        with self.lock:
            before = self._snapshot(user_id, concept)
            for sname in strategies:
                self.db.execute(
                    "INSERT INTO strategy_memory (user_id, concept, strategy, worked, failed, last_at) VALUES (?,?,?,0,0,?) "
                    "ON CONFLICT(user_id, concept, strategy) DO NOTHING",
                    (user_id, concept, sname, iso(now)),
                )
                self.db.execute(
                    f"UPDATE strategy_memory SET {outcome} = {outcome} + 1, last_at=? WHERE user_id=? AND concept=? AND strategy=?",
                    (iso(now), user_id, concept, sname),
                )
            self._log(user_id, concept, f"strategy_{outcome}", {"strategies": strategies}, before, now)
            self.db.commit()

    def undo(self, user_id: str, event_id: int) -> bool:
        with self.lock:
            ev = self.db.execute("SELECT * FROM events WHERE id=? AND user_id=?", (event_id, user_id)).fetchone()
            if not ev:
                return False
            snap = json.loads(ev["before_json"])
            concept = ev["concept"]
            self.db.execute("DELETE FROM profiles WHERE user_id=? AND concept=?", (user_id, concept))
            self.db.execute("DELETE FROM strategy_memory WHERE user_id=? AND concept=?", (user_id, concept))
            if snap["profile"]:
                p = snap["profile"]
                self.db.execute(
                    "INSERT INTO profiles VALUES (?,?,?,?,?,?,?)",
                    (user_id, concept, p["level"], p["streak"], p["source"], p["updated_at"], p["last_signal_at"]),
                )
            for r in snap["strategies"]:
                self.db.execute(
                    "INSERT INTO strategy_memory VALUES (?,?,?,?,?,?)",
                    (user_id, concept, r["strategy"], r["worked"], r["failed"], r["last_at"]),
                )
            self.db.execute("DELETE FROM events WHERE user_id=? AND id>=? AND concept=?", (user_id, event_id, concept))
            self.db.commit()
        return True

    def _delete_rows(self, user_id: str, concept: str | None, include_settings: bool = False) -> None:
        where, args = ("user_id=?", (user_id,)) if concept is None else ("user_id=? AND concept=?", (user_id, concept))
        for table in ("profiles", "strategy_memory", "events"):
            self.db.execute(f"DELETE FROM {table} WHERE {where}", args)
        if include_settings:
            self.db.execute("DELETE FROM settings WHERE user_id=?", (user_id,))
            self.db.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        self.db.commit()

    def delete(self, user_id: str, concept: str | None = None) -> None:
        """Xoá một khái niệm, hoặc toàn bộ Sổ tay (giữ cài đặt ghi nhớ)."""
        with self.lock:
            self._delete_rows(user_id, concept)

    def delete_strategy(self, user_id: str, concept: str, strategy: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM strategy_memory WHERE user_id=? AND concept=? AND strategy=?", (user_id, concept, strategy))
            self.db.commit()

    # ------------------------------------------------------------ sessions
    def session(self, session_id: str, user_id: str) -> dict:
        r = self.db.execute("SELECT state_json, user_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if r and r["user_id"] == user_id:
            return json.loads(r["state_json"])
        return {"answered": {}, "last": {}, "last_concept": None, "thumbs_down": {}, "wrong": {}, "check_attempt": {}, "tried": {}, "last_question": ""}

    def save_session(self, session_id: str, user_id: str, state: dict) -> None:
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?)",
                (session_id, user_id, json.dumps(state, ensure_ascii=False), iso(utcnow())),
            )
            self.db.commit()

    def reset_session(self, session_id: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            self.db.commit()
