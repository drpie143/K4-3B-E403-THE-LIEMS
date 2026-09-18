"""Tài khoản học viên: đăng ký, đăng nhập, phiên đăng nhập.

Mỗi tài khoản có một `user_id` — đây chính là khoá của hồ sơ và bộ nhớ dài hạn,
nên mỗi người đăng nhập sẽ thấy đúng mức hiểu và cách giải thích đã hiệu quả của mình.

Lưu ở đâu: Supabase (bảng `accounts`, `account_sessions`) khi đã cấu hình
SUPABASE_URL/SUPABASE_KEY; nếu chưa có thì lưu tạm trong SQLite cùng file p3.db.
Mật khẩu luôn băm bằng PBKDF2-SHA256, không bao giờ lưu dạng thô.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ITERATIONS = 120_000
SESSION_DAYS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS person_accounts (
  id TEXT PRIMARY KEY, email TEXT UNIQUE, display_name TEXT, password_hash TEXT,
  role TEXT DEFAULT 'learner', created_at TEXT, last_login_at TEXT);
CREATE TABLE IF NOT EXISTS person_sessions (
  token_hash TEXT PRIMARY KEY, account_id TEXT, created_at TEXT, expires_at TEXT);
"""


class AuthError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, want = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return secrets.compare_digest(dk.hex(), want)
    except Exception:
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def __init__(self, db: sqlite3.Connection, supabase=None):
        self.db = db
        self.sb = supabase
        self.lock = threading.RLock()
        self.db.executescript(SCHEMA)

    @property
    def remote(self) -> bool:
        return bool(self.sb and self.sb.is_configured())

    # ------------------------------------------------------------- đăng ký
    def register(self, email: str, password: str, display_name: str = "") -> dict:
        email = (email or "").strip().lower()
        if not EMAIL_RE.match(email):
            raise AuthError("Email chưa đúng định dạng.")
        if len(password or "") < 8:
            raise AuthError("Mật khẩu cần ít nhất 8 ký tự.")
        if self._find(email):
            raise AuthError("Email này đã có tài khoản. Hãy đăng nhập.")
        now = utcnow()
        acc = {
            "id": f"u_{uuid.uuid4().hex[:16]}",
            "email": email,
            "display_name": (display_name or email.split("@")[0]).strip()[:60],
            "password_hash": hash_password(password),
            "role": "learner",
            "created_at": iso(now),
            "last_login_at": iso(now),
        }
        with self.lock:
            self.db.execute(
                "INSERT INTO person_accounts VALUES (?,?,?,?,?,?,?)",
                (acc["id"], acc["email"], acc["display_name"], acc["password_hash"], acc["role"],
                 acc["created_at"], acc["last_login_at"]))
            self.db.commit()
        if self.remote:
            self.sb.upsert("person_accounts", acc)
        return self._public(acc)

    # ----------------------------------------------------------- đăng nhập
    def login(self, email: str, password: str) -> tuple[dict, str]:
        acc = self._find((email or "").strip().lower())
        if not acc or not verify_password(password or "", acc.get("password_hash", "")):
            raise AuthError("Email hoặc mật khẩu chưa đúng.")
        token = secrets.token_urlsafe(32)
        now = utcnow()
        row = {
            "token_hash": token_hash(token), "account_id": acc["id"],
            "created_at": iso(now), "expires_at": iso(now + timedelta(days=SESSION_DAYS)),
        }
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO person_sessions VALUES (?,?,?,?)",
                            (row["token_hash"], row["account_id"], row["created_at"], row["expires_at"]))
            self.db.execute("UPDATE person_accounts SET last_login_at=? WHERE id=?", (iso(now), acc["id"]))
            self.db.commit()
        if self.remote:
            self.sb.upsert("person_sessions", row)
            self.sb.update("person_accounts", {"id": f"eq.{acc['id']}"}, {"last_login_at": iso(now)})
        return self._public(acc), token

    def logout(self, token: str) -> None:
        th = token_hash(token or "")
        with self.lock:
            self.db.execute("DELETE FROM person_sessions WHERE token_hash=?", (th,))
            self.db.commit()
        if self.remote:
            self.sb.delete("person_sessions", {"token_hash": f"eq.{th}"})

    def account_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        th = token_hash(token)
        row = self.db.execute("SELECT account_id, expires_at FROM person_sessions WHERE token_hash=?", (th,)).fetchone()
        if row is None and self.remote:
            rows = self.sb.select("person_sessions", {"token_hash": f"eq.{th}", "select": "account_id,expires_at"})
            row = rows[0] if rows else None
            if row:  # nhớ lại phiên đã mở ở máy khác
                with self.lock:
                    self.db.execute("INSERT OR REPLACE INTO person_sessions VALUES (?,?,?,?)",
                                    (th, row["account_id"], iso(utcnow()), row["expires_at"]))
                    self.db.commit()
        if not row:
            return None
        data = dict(row) if not isinstance(row, dict) else row
        if data.get("expires_at") and data["expires_at"] < iso(utcnow()):
            self.logout(token)
            return None
        acc = self._by_id(data["account_id"])
        return self._public(acc) if acc else None

    # ------------------------------------------------------------ hồ sơ tk
    def update_account(self, account_id: str, display_name: str | None = None, password: str | None = None) -> dict:
        acc = self._by_id(account_id)
        if not acc:
            raise AuthError("Không tìm thấy tài khoản.")
        patch: dict[str, str] = {}
        if display_name:
            patch["display_name"] = display_name.strip()[:60]
        if password:
            if len(password) < 8:
                raise AuthError("Mật khẩu cần ít nhất 8 ký tự.")
            patch["password_hash"] = hash_password(password)
        if patch:
            sets = ", ".join(f"{k}=?" for k in patch)
            with self.lock:
                self.db.execute(f"UPDATE person_accounts SET {sets} WHERE id=?", (*patch.values(), account_id))
                self.db.commit()
            if self.remote:
                self.sb.update("person_accounts", {"id": f"eq.{account_id}"}, patch)
            acc = {**acc, **patch}
        return self._public(acc)

    def delete_account(self, account_id: str) -> None:
        with self.lock:
            self.db.execute("DELETE FROM person_sessions WHERE account_id=?", (account_id,))
            self.db.execute("DELETE FROM person_accounts WHERE id=?", (account_id,))
            self.db.commit()
        if self.remote:
            self.sb.delete("person_sessions", {"account_id": f"eq.{account_id}"})
            self.sb.delete("person_accounts", {"id": f"eq.{account_id}"})

    # --------------------------------------------------------------- nội bộ
    def _find(self, email: str) -> dict | None:
        row = self.db.execute("SELECT * FROM person_accounts WHERE email=?", (email,)).fetchone()
        if row:
            return dict(row)
        if self.remote:
            rows = self.sb.select("person_accounts", {"email": f"eq.{email}", "select": "*"})
            if rows:
                self._cache(rows[0])
                return rows[0]
        return None

    def _by_id(self, account_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM person_accounts WHERE id=?", (account_id,)).fetchone()
        if row:
            return dict(row)
        if self.remote:
            rows = self.sb.select("person_accounts", {"id": f"eq.{account_id}", "select": "*"})
            if rows:
                self._cache(rows[0])
                return rows[0]
        return None

    def _cache(self, acc: dict) -> None:
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO person_accounts VALUES (?,?,?,?,?,?,?)",
                (acc["id"], acc["email"], acc.get("display_name", ""), acc.get("password_hash", ""),
                 acc.get("role", "learner"), acc.get("created_at", ""), acc.get("last_login_at", "")))
            self.db.commit()

    @staticmethod
    def _public(acc: dict) -> dict:
        return {
            "user_id": acc["id"], "email": acc["email"], "display_name": acc.get("display_name", ""),
            "role": acc.get("role", "learner"), "created_at": acc.get("created_at", ""),
        }
