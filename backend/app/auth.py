"""Supabase-only learner auth."""
from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ITERATIONS = 120_000
SESSION_DAYS = 30


class AuthError(ValueError):
    pass


class AuthRemoteError(RuntimeError):
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
    def __init__(self, supabase: Any):
        self.sb = supabase

    @property
    def remote(self) -> bool:
        return bool(self.sb and self.sb.is_configured())

    def _require_remote(self) -> None:
        if not self.remote:
            raise AuthRemoteError("Chưa cấu hình Supabase. Điền SUPABASE_URL và SUPABASE_KEY trong backend/.env.")

    def register(self, email: str, password: str, display_name: str = "") -> dict:
        self._require_remote()
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
        if not self.sb.upsert("person_accounts", acc):
            raise AuthRemoteError("Không lưu được tài khoản lên Supabase. Kiểm tra SUPABASE_KEY và bảng person_accounts.")
        return self._public(acc)

    def login(self, email: str, password: str) -> tuple[dict, str]:
        self._require_remote()
        acc = self._find((email or "").strip().lower())
        if not acc or not verify_password(password or "", acc.get("password_hash", "")):
            raise AuthError("Email hoặc mật khẩu chưa đúng.")
        token = secrets.token_urlsafe(32)
        now = utcnow()
        last_login = iso(now)
        row = {
            "token_hash": token_hash(token),
            "account_id": acc["id"],
            "created_at": last_login,
            "expires_at": iso(now + timedelta(days=SESSION_DAYS)),
        }
        if not self.sb.update("person_accounts", {"id": f"eq.{acc['id']}"}, {"last_login_at": last_login}):
            raise AuthRemoteError("Không cập nhật được tài khoản trên Supabase.")
        if not self.sb.upsert("person_sessions", row):
            raise AuthRemoteError("Không lưu được phiên đăng nhập lên Supabase.")
        return self._public({**acc, "last_login_at": last_login}), token

    def logout(self, token: str) -> None:
        if self.remote:
            self.sb.delete("person_sessions", {"token_hash": f"eq.{token_hash(token or '')}"})

    def account_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        self._require_remote()
        rows = self.sb.select(
            "person_sessions",
            {"token_hash": f"eq.{token_hash(token)}", "select": "account_id,expires_at", "limit": "1"},
        )
        if not rows:
            return None
        row = rows[0]
        if row.get("expires_at") and str(row["expires_at"]) < iso(utcnow()):
            self.logout(token)
            return None
        acc = self._by_id(row["account_id"])
        return self._public(acc) if acc else None

    def sync_session(self, token: str) -> None:
        if not self.account_for_token(token):
            raise AuthRemoteError("Phiên đăng nhập không còn hợp lệ trên Supabase.")

    def update_account(self, account_id: str, display_name: str | None = None, password: str | None = None) -> dict:
        self._require_remote()
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
            if not self.sb.update("person_accounts", {"id": f"eq.{account_id}"}, patch):
                raise AuthRemoteError("Không cập nhật được tài khoản trên Supabase.")
            acc = {**acc, **patch}
        return self._public(acc)

    def delete_account(self, account_id: str) -> None:
        self._require_remote()
        self.sb.delete("person_sessions", {"account_id": f"eq.{account_id}"})
        self.sb.delete("person_accounts", {"id": f"eq.{account_id}"})

    def _find(self, email: str) -> dict | None:
        rows = self.sb.select("person_accounts", {"email": f"eq.{email}", "select": "*", "limit": "1"})
        return rows[0] if rows else None

    def _by_id(self, account_id: str) -> dict | None:
        rows = self.sb.select("person_accounts", {"id": f"eq.{account_id}", "select": "*", "limit": "1"})
        return rows[0] if rows else None

    @staticmethod
    def _public(acc: dict) -> dict:
        return {
            "user_id": acc["id"],
            "email": acc["email"],
            "display_name": acc.get("display_name", ""),
            "role": acc.get("role", "learner"),
            "created_at": acc.get("created_at", ""),
        }
