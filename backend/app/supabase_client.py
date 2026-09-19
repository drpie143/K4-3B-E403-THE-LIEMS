"""Client kết nối Supabase REST API & pgvector RPC qua httpx."""
from __future__ import annotations

import threading
from typing import Any

import httpx


class SupabaseClient:
    def __init__(self, url: str, key: str, timeout: float = 15.0):
        self.url = url.rstrip("/")
        self.key = key
        self.rest_url = f"{self.url}/rest/v1"
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        self.timeout = timeout
        self._client: httpx.Client | None = None
        self._lock = threading.Lock()

    def is_configured(self) -> bool:
        return bool(self.url and self.key and "your-project" not in self.url)

    @property
    def client(self) -> httpx.Client:
        """Một client dùng lại cho mọi lời gọi.

        Mỗi `httpx.Client()` mới phải bắt tay TCP + TLS lại từ đầu (~1 giây tới Supabase).
        Vector search nằm ngay trong đường đi của mỗi câu hỏi nên phải giữ kết nối sống.
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = httpx.Client(
                        timeout=self.timeout,
                        headers=self.headers,
                        limits=httpx.Limits(max_keepalive_connections=8, keepalive_expiry=300.0),
                    )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def select(self, table: str, params: dict[str, str] | None = None) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            resp = self.client.get(f"{self.rest_url}/{table}", params=params or {})
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def upsert(self, table: str, records: list[dict] | dict) -> bool:
        if not self.is_configured():
            return False
        payload = records if isinstance(records, list) else [records]
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
        try:
            resp = self.client.post(f"{self.rest_url}/{table}", headers=headers, json=payload)
            if resp.status_code not in (200, 201, 204):
                try:
                    code = resp.json().get("code", "unknown")
                except ValueError:
                    code = "unknown"
                print(f"  [Supabase Error] POST {table} trả về {resp.status_code}, code={code}")
            return resp.status_code in (200, 201, 204)
        except Exception as e:
            print(f"  [Supabase Error] Exception khi upsert: {e}")
            return False

    def insert(self, table: str, record: dict) -> dict | None:
        if not self.is_configured():
            return None
        headers = {**self.headers, "Prefer": "return=representation"}
        try:
            resp = self.client.post(f"{self.rest_url}/{table}", headers=headers, json=[record])
            if resp.status_code in (200, 201):
                rows = resp.json()
                return rows[0] if rows else None
            try:
                code = resp.json().get("code", "unknown")
            except ValueError:
                code = "unknown"
            print(f"  [Supabase Error] INSERT {table} trả về {resp.status_code}, code={code}")
        except Exception as e:
            print(f"  [Supabase Error] Exception khi insert: {e}")
        return None

    def update(self, table: str, filter_params: dict[str, str], data: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            resp = self.client.patch(f"{self.rest_url}/{table}", params=filter_params, json=data)
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def delete(self, table: str, filter_params: dict[str, str]) -> bool:
        if not self.is_configured():
            return False
        try:
            resp = self.client.delete(f"{self.rest_url}/{table}", params=filter_params)
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def rpc(self, func_name: str, params: dict[str, Any], timeout: float | None = None) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            resp = self.client.post(f"{self.rest_url}/rpc/{func_name}", json=params, timeout=timeout or self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []
