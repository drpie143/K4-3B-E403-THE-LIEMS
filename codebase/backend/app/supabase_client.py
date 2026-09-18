"""Client kết nối Supabase REST API & pgvector RPC qua httpx."""
from __future__ import annotations

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

    def is_configured(self) -> bool:
        return bool(self.url and self.key and "your-project" not in self.url)

    def select(self, table: str, params: dict[str, str] | None = None) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(f"{self.rest_url}/{table}", headers=self.headers, params=params or {})
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
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.rest_url}/{table}", headers=headers, json=payload)
                if resp.status_code not in (200, 201, 204):
                    print(f"  [Supabase Error] POST {table} trả về {resp.status_code}: {resp.text}")
                return resp.status_code in (200, 201, 204)
        except Exception as e:
            print(f"  [Supabase Error] Exception khi upsert: {e}")
            return False

    def update(self, table: str, filter_params: dict[str, str], data: dict) -> bool:
        if not self.is_configured():
            return False
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.patch(f"{self.rest_url}/{table}", headers=self.headers, params=filter_params, json=data)
                return resp.status_code in (200, 204)
        except Exception:
            return False

    def delete(self, table: str, filter_params: dict[str, str]) -> bool:
        if not self.is_configured():
            return False
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.delete(f"{self.rest_url}/{table}", headers=self.headers, params=filter_params)
                return resp.status_code in (200, 204)
        except Exception:
            return False

    def rpc(self, func_name: str, params: dict[str, Any]) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.rest_url}/rpc/{func_name}", headers=self.headers, json=params)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return []
