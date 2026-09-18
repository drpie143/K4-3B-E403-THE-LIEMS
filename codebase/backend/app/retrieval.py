"""Tìm đoạn nguồn bằng Hybrid Search: BM25 + Upstash Vector DB (Reciprocal Rank Fusion - RRF).

Nguồn:
1. BM25 cục bộ trên toàn bộ 700 đoạn bài giảng (transcript 01 - 06 từ codebase/data/chunks.local.json).
2. Upstash Vector DB (nếu cấu hình UPSTASH_VECTOR_REST_URL & UPSTASH_VECTOR_REST_TOKEN):
   Gọi REST API của Upstash, vector DB tự embedding bằng model tích hợp sẵn.
3. Kết hợp kết quả bằng Reciprocal Rank Fusion (RRF):
   score(d) = 1.0 / (60 + rank_bm25) + 1.0 / (60 + rank_vector)
4. Tự động fallback về BM25 trên 700 đoạn bài giảng nếu không có cấu hình Upstash hoặc lỗi mạng.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import requests

from .cards import CardStore
from .textutil import tokens

STOPWORDS = set("la gi cua va co cho cac nhung mot the nao nay do thi de duoc khong trong khi nhu ve voi tu den o ra vao minh ban toi em anh chi a nhe a oi sao".split())


@dataclass
class Passage:
    id: str
    section: str
    text: str
    file: str
    score: float = 0.0


class Retriever:
    k1 = 1.5
    b = 0.75

    def __init__(
        self,
        cards: CardStore,
        chunks_path: Path,
        upstash_url: str = "",
        upstash_token: str = "",
    ):
        self.cards = cards
        self.upstash_url = upstash_url.rstrip("/") if upstash_url else ""
        self.upstash_token = upstash_token
        self.mode = "local"

        docs: list[Passage] = []
        if Path(chunks_path).exists():
            try:
                raw = json.loads(Path(chunks_path).read_text(encoding="utf-8"))
                for c in raw:
                    docs.append(Passage(id=c["id"], section=c.get("section", ""), text=c["text"], file=c.get("file", "")))
            except Exception:
                pass

        if not docs:
            self.mode = "summary"
            for sid, meta in cards.sources.items():
                file = "transcript-04-clean.md" if sid.startswith("T04") else "transcript-06-clean.md"
                docs.append(Passage(id=sid, section=meta.get("section", ""), text=meta.get("summary", ""), file=file))

        self.docs = docs
        self.by_id = {d.id: d for d in docs}
        self._index()

    def _index(self) -> None:
        self.doc_tokens = [self._toks(f"{d.section} {d.text}") for d in self.docs]
        self.tf = [Counter(t) for t in self.doc_tokens]
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(1, len(self.doc_tokens))
        df: Counter = Counter()
        for t in self.doc_tokens:
            df.update(set(t))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    @staticmethod
    def _toks(text: str) -> list[str]:
        return [t for t in tokens(text) if t not in STOPWORDS]

    def _bm25_search(self, query: str, allowed_files: set[str], top_k: int, boost_ids: set[str]) -> list[Passage]:
        q = self._toks(query)
        scored = []
        for i, d in enumerate(self.docs):
            if allowed_files and d.file not in allowed_files:
                continue
            tf, dl = self.tf[i], len(self.doc_tokens[i])
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if f:
                    s += self.idf.get(w, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0 and d.id in boost_ids:
                s = s * 1.5 + 0.5
            if s > 0:
                scored.append(Passage(d.id, d.section, d.text, d.file, round(s, 3)))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:top_k]

    def _upstash_vector_search(self, query: str, allowed_files: set[str], top_k: int) -> list[Passage]:
        if not self.upstash_url or not self.upstash_token:
            return []
        endpoint = f"{self.upstash_url}/query-data"
        headers = {
            "Authorization": f"Bearer {self.upstash_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "data": query,
            "topK": top_k * 2,
            "includeMetadata": True,
            "includeData": True,
        }
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=4.0)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = data.get("result", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                return []
            results = []
            for item in items:
                cid = str(item.get("id", ""))
                score = float(item.get("score", 0.0))
                meta = item.get("metadata", {}) or {}
                doc_file = meta.get("file", "")
                if allowed_files and doc_file not in allowed_files:
                    continue
                # Ưu tiên lấy từ cache local by_id để có đầy đủ thông tin chuẩn xác
                existing = self.by_id.get(cid)
                if existing:
                    results.append(Passage(existing.id, existing.section, existing.text, existing.file, round(score, 4)))
                else:
                    text = meta.get("text") or item.get("data") or ""
                    section = meta.get("section", "")
                    results.append(Passage(cid, section, text, doc_file, round(score, 4)))
            return results[:top_k]
        except Exception:
            return []

    def search(self, query: str, lesson_id: str, k: int = 5, boost_ids: list[str] | None = None) -> list[Passage]:
        allowed = set(self.cards.lesson_files(lesson_id))
        boost = set(boost_ids or [])

        # 1. Chạy BM25
        bm25_res = self._bm25_search(query, allowed, top_k=k * 2, boost_ids=boost)

        # 2. Chạy Upstash Dense Vector Search (nếu có cấu hình)
        vector_res = self._upstash_vector_search(query, allowed, top_k=k * 2)

        # 3. Nếu không có kết quả vector, trả về kết quả BM25 thuần túy
        if not vector_res:
            # Nếu tìm trong allowed bị rỗng, tự động mở rộng tìm kiếm toàn bộ 6 bài giảng
            if not bm25_res and allowed:
                return self._bm25_search(query, set(), top_k=k, boost_ids=boost)
            return bm25_res[:k]

        # 4. Reciprocal Rank Fusion (RRF) kết hợp BM25 + Dense Vector
        rrf_k = 60
        scores: dict[str, float] = {}
        passages: dict[str, Passage] = {}

        for rank, p in enumerate(bm25_res, start=1):
            scores[p.id] = scores.get(p.id, 0.0) + (1.0 / (rrf_k + rank))
            passages[p.id] = p

        for rank, p in enumerate(vector_res, start=1):
            scores[p.id] = scores.get(p.id, 0.0) + (1.0 / (rrf_k + rank))
            if p.id not in passages:
                passages[p.id] = p

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        final_results = []
        for pid, score in ranked[:k]:
            p = passages[pid]
            # Nhân 100 để thang điểm RRF (~0.015 - 0.035) tương thích với ngưỡng RETRIEVAL_MIN_SCORE (mặc định 1.0)
            scaled_score = round(score * 100.0, 3)
            final_results.append(Passage(p.id, p.section, p.text, p.file, scaled_score))

        return final_results

    def get(self, source_id: str) -> Passage | None:
        return self.by_id.get(source_id)

    def text_for(self, source_id: str, max_chars: int) -> str:
        p = self.by_id.get(source_id)
        if not p:
            return self.cards.summary(source_id)
        return p.text if len(p.text) <= max_chars else p.text[:max_chars].rsplit(" ", 1)[0] + " …"
