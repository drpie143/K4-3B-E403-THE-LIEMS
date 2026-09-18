"""Tiện ích xử lý chữ tiếng Việt."""
from __future__ import annotations

import re
import unicodedata

_TAG = re.compile(r"<[^>]+>")
_TOKEN = re.compile(r"[a-z0-9]+")


def norm(text: str | None) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (đ → d)."""
    s = unicodedata.normalize("NFD", str(text or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def strip_tags(html: str | None) -> str:
    return _TAG.sub(" ", html or "")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(norm(text))


def word_count(text: str) -> int:
    return len(strip_tags(text).split())


def cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text
