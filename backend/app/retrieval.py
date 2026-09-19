"""Tìm đoạn nguồn bằng Hybrid Search (kết hợp BM25 và Semantic Vector Search qua Reciprocal Rank Fusion - RRF).

Đặc điểm:
- Nguồn runtime ưu tiên: bảng `lecture_chunks` trên Supabase.
- Chỉ khi chưa cấu hình Supabase mới fallback sang data/chunks.local.json / transcript local.
- Thiếu dữ liệu → dùng tóm tắt trong cards/_sources.yaml ("summary mode").
- BM25: Tìm kiếm chính xác từ khoá và thuật ngữ kỹ thuật tiếng Việt.
- Vector Search: Tìm kiếm theo ngữ nghĩa (OpenAI / Gemini Embeddings với cache, hoặc subword vector space).
- RRF: Dung hợp thứ hạng 2 luồng tìm kiếm theo chuẩn công nghiệp:
    RRF_Score(d) = alpha / (k + rank_bm25(d)) + (1 - alpha) / (k + rank_dense(d))
"""
from __future__ import annotations

import json
import math
import os
import threading
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cards import CardStore
from .supabase_client import SupabaseClient
from .textutil import tokens

STOPWORDS = set(
    "la gi cua va co cho cac nhung mot the nao nay do thi de duoc khong trong khi nhu ve voi tu den o ra vao minh ban toi em anh chi a nhe a oi sao".split()
)


@dataclass
class Passage:
    id: str
    section: str
    text: str
    file: str
    score: float = 0.0
    source_ids: list[str] = field(default_factory=list)


def cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
    """Tính cosine similarity giữa 2 sparse vector dạng dictionary."""
    if not v1 or not v2:
        return 0.0
    # Lấy dot product
    if len(v1) > len(v2):
        v1, v2 = v2, v1
    dot = sum(val * v2.get(k, 0.0) for k, val in v1.items())
    if dot <= 0.0:
        return 0.0
    norm1 = math.sqrt(sum(x * x for x in v1.values()))
    norm2 = math.sqrt(sum(x * x for x in v2.values()))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


def dense_cosine(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class Retriever:
    k1 = 1.5
    b = 0.75

    def __init__(self, cards: CardStore, chunks_path: Path, settings: Any = None):
        self.cards = cards
        self.settings = settings
        self.mode = "local"
        self.retrieval_mode = getattr(settings, "retrieval_mode", "hybrid") if settings else "hybrid"
        self.hybrid_alpha = getattr(settings, "hybrid_alpha", 0.5) if settings else 0.5
        self.rrf_k = getattr(settings, "rrf_k", 60) if settings else 60
        self.embedding_provider = self._configured_embedding_provider()
        self.embedding_model = self._configured_embedding_model()
        self.sb = SupabaseClient(getattr(settings, "supabase_url", ""), getattr(settings, "supabase_key", "")) if settings else None

        docs: list[Passage] = []
        p_path = Path(chunks_path)

        # 1. Runtime thật: kéo nguyên văn từ bảng lecture_chunks trên Supabase.
        if self.sb and self.sb.is_configured():
            try:
                rows = self.sb.select("lecture_chunks", {
                    "select": "id,section,file,text,source_ids", "order": "id.asc", "limit": "2000",
                })
                for c in rows:
                    if not c.get("text"):
                        continue
                    docs.append(Passage(
                        id=c["id"], section=c.get("section", ""), text=c["text"],
                        file=c.get("file", ""), source_ids=c.get("source_ids") or [c["id"]],
                    ))
                if docs:
                    self.mode = "supabase"
                    print(f"[Retrieval] Loaded {len(docs)} chunks from Supabase.")
            except Exception as exc:
                pass

        # 2. Chỉ dùng local khi chưa cấu hình Supabase (test/dev offline).
        if not docs and not (self.sb and self.sb.is_configured()) and p_path.exists():
            try:
                raw_data = json.loads(p_path.read_text(encoding="utf-8"))
                for c in raw_data:
                    s_ids = c.get("source_ids", [c["id"]])
                    docs.append(
                        Passage(
                            id=c["id"],
                            section=c.get("section", ""),
                            text=c["text"],
                            file=c.get("file", ""),
                            source_ids=s_ids,
                        )
                    )
            except Exception:
                docs = []

        # 3. Nếu chưa có chunks.local.json nhưng là đường dẫn mặc định, thử đọc từ Data/transcript/
        default_chunks = Path(__file__).resolve().parents[2] / "data" / "chunks.local.json"
        is_default_chunks = False
        try:
            is_default_chunks = p_path.resolve() == default_chunks.resolve()
        except Exception:
            pass

        if not docs and not (self.sb and self.sb.is_configured()) and is_default_chunks:
            trans_dir = getattr(settings, "transcripts_dir", None)
            if not trans_dir:
                trans_dir = Path(__file__).resolve().parents[1] / "Data" / "transcript"
            if Path(trans_dir).is_dir():
                try:
                    from .chunking import build_chunks_from_directory
                    chunks_objs = build_chunks_from_directory(Path(trans_dir), target_chars=750, overlap_count=1)
                    for c in chunks_objs:
                        docs.append(
                            Passage(
                                id=c.id,
                                section=c.section,
                                text=c.text,
                                file=c.file,
                                source_ids=c.source_ids,
                            )
                        )
                except Exception:
                    pass

        # 4. Nếu Supabase đã cấu hình nhưng không có lecture_chunks, không âm thầm dùng dữ liệu mock.
        if not docs and self.sb and self.sb.is_configured():
            self.mode = "supabase_empty"

        # 5. Chế độ dự phòng cuối cho test/dev offline khi chưa cấu hình Supabase.
        if not docs and not (self.sb and self.sb.is_configured()):
            self.mode = "summary"
            for sid, meta in cards.sources.items():
                # T03-105 → transcript-03-clean.md (đúng cho cả 6 buổi, không chỉ 04/06)
                file = f"transcript-{sid[1:3]}-clean.md"
                docs.append(
                    Passage(
                        id=sid,
                        section=meta.get("section", ""),
                        text=meta.get("summary", ""),
                        file=file,
                        source_ids=[sid],
                    )
                )

        self.docs = docs

        # Lập chỉ mục tra cứu theo ID chính và tất cả source_ids thuộc chunk
        self.by_id: dict[str, Passage] = {}
        for d in docs:
            self.by_id[d.id] = d
            for sid in d.source_ids:
                if sid not in self.by_id:
                    self.by_id[sid] = d

        # Vị trí của mỗi chunk trong self.docs — tra O(1) thay cho self.docs.index() O(n).
        self.pos_of: dict[str, int] = {}
        for i, d in enumerate(docs):
            self.pos_of.setdefault(d.id, i)
            for sid in d.source_ids:
                self.pos_of.setdefault(sid, i)

        self._index_bm25()
        self._index_vectors()

        # Mô hình embedding nạp mất ~30 giây lần đầu. Nạp sẵn ở nền ngay khi khởi động
        # để câu hỏi đầu tiên của học viên không phải chờ.
        self._e5_model = None
        self._e5_lock = threading.Lock()
        self._e5_failed = False
        self._openai_client = None
        self._openai_lock = threading.Lock()
        self._openai_doc_embeddings: dict[str, list[float]] = {}
        self._openai_docs_ready = False
        self._openai_failed = False
        self._embedding_status = "disabled"
        self._emb_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._search_cache: OrderedDict[tuple, list[Passage]] = OrderedDict()
        if self._openai_local_enabled():
            self._embedding_status = "openai_pending"
        elif self._dense_remote_enabled():
            self._embedding_status = "supabase_pending"
            threading.Thread(target=self._load_embedder, name="warmup-embedder", daemon=True).start()

    # ------------------------------------------------------- embedding (dense)
    def _configured_embedding_provider(self) -> str:
        provider = getattr(self.settings, "embedding_provider", "") if self.settings else ""
        provider = (provider or "").strip().lower()
        if not provider:
            provider = (getattr(self.settings, "llm_provider", "") or "").strip().lower() if self.settings else ""
        return "" if provider == "fake" else provider

    def _configured_embedding_model(self) -> str:
        model = (getattr(self.settings, "embedding_model", "") or "").strip() if self.settings else ""
        if self.embedding_provider == "openai":
            old_local_names = {"local", "e5", "intfloat/multilingual-e5-base", "text-embedding-004"}
            if not model or model in old_local_names:
                return "text-embedding-3-small"
        return model

    def _openai_local_enabled(self) -> bool:
        return self.embedding_provider == "openai" and self.retrieval_mode in {"hybrid", "dense"}

    def embedding_health(self) -> dict[str, Any]:
        return {
            "provider": self.embedding_provider or "local_sparse",
            "model": self.embedding_model or "",
            "dimensions": int(getattr(self.settings, "embedding_dimensions", 0) or 0),
            "status": self._embedding_status,
            "cached_docs": len(self._openai_doc_embeddings),
        }

    def _dense_remote_enabled(self) -> bool:
        """Chỉ dùng vector search trên Supabase khi đã cấu hình đủ URL + KEY."""
        return bool(self.sb and self.sb.is_configured() and not self._openai_local_enabled())

    def _load_embedder(self):
        """Nạp mô hình e5 (chỉ một lần, an toàn khi nhiều luồng cùng gọi)."""
        if self._e5_model is not None or self._e5_failed:
            return self._e5_model
        with self._e5_lock:
            if self._e5_model is not None or self._e5_failed:
                return self._e5_model
            try:
                import warnings

                from sentence_transformers import SentenceTransformer
                name = getattr(self.settings, "embedding_model", "") or "intfloat/multilingual-e5-base"
                if name in ("text-embedding-004", "local"):  # tên cũ trong .env
                    name = "intfloat/multilingual-e5-base"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    self._e5_model = SentenceTransformer(name)
            except Exception as exc:
                # Thiếu gói/mạng → chạy tiếp bằng BM25 + vector cục bộ, không làm hỏng lượt hỏi.
                print(f"[Retrieval] Không nạp được mô hình embedding ({exc}) — dùng BM25 + vector cục bộ.")
                self._e5_failed = True
            return self._e5_model

    def _embed_query(self, query: str) -> list[float] | None:
        if self.embedding_provider == "openai":
            return self._embed_query_openai(query)
        key = " ".join(query.lower().split())[:400]
        cached = self._emb_cache.get(key)
        if cached is not None:
            self._emb_cache.move_to_end(key)
            return cached
        model = self._load_embedder()
        if model is None:
            return None
        vec = model.encode([f"query: {key}"], normalize_embeddings=True)[0].tolist()
        self._emb_cache[key] = vec
        if len(self._emb_cache) > 256:
            self._emb_cache.popitem(last=False)
        return vec

    def _openai_cache_path(self) -> Path:
        base = getattr(self.settings, "cache_dir", None) if self.settings else None
        cache_dir = Path(base) if base else Path(__file__).resolve().parents[1] / ".cache"
        return cache_dir / "openai_doc_embeddings.json"

    def _openai_doc_key(self, doc: Passage) -> str:
        return sha256(f"{self.embedding_model}\0{doc.id}\0{doc.text}".encode("utf-8")).hexdigest()

    def _openai_client_instance(self):
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("Missing OPENAI_API_KEY in backend/.env")
        if self._openai_client is None:
            from openai import OpenAI

            timeout = max(float(getattr(self.settings, "llm_timeout", 20.0) or 20.0), 60.0)
            retries = int(getattr(self.settings, "llm_max_retries", 2) or 2)
            self._openai_client = OpenAI(timeout=timeout, max_retries=retries)
        return self._openai_client

    def _embed_texts_openai(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._openai_client_instance()
        kwargs = {"model": self.embedding_model, "input": texts, "encoding_format": "float"}
        dims = int(getattr(self.settings, "embedding_dimensions", 0) or 0)
        if dims:
            kwargs["dimensions"] = dims
        resp = client.embeddings.create(**kwargs)
        data = sorted(resp.data, key=lambda item: item.index)
        return [list(item.embedding) for item in data]

    def _embed_query_openai(self, query: str) -> list[float] | None:
        key = f"{self.embedding_model}:query:" + " ".join(query.lower().split())[:400]
        cached = self._emb_cache.get(key)
        if cached is not None:
            self._emb_cache.move_to_end(key)
            return cached
        try:
            vec = self._embed_texts_openai([query])[0]
        except Exception as exc:
            self._embedding_status = f"openai_query_error:{type(exc).__name__}"
            print(f"[Retrieval] OpenAI query embedding failed: {exc}")
            return None
        self._emb_cache[key] = vec
        if len(self._emb_cache) > 256:
            self._emb_cache.popitem(last=False)
        return vec

    def _ensure_openai_doc_embeddings(self) -> bool:
        if not self._openai_local_enabled():
            return False
        if self._openai_docs_ready:
            return True
        if self._openai_failed:
            return False
        with self._openai_lock:
            if self._openai_docs_ready:
                return True
            cache_path = self._openai_cache_path()
            cached_vectors: dict[str, list[float]] = {}
            try:
                if cache_path.exists():
                    raw = json.loads(cache_path.read_text(encoding="utf-8"))
                    if raw.get("model") == self.embedding_model:
                        cached_vectors = raw.get("vectors", {})
            except Exception as exc:
                print(f"[Retrieval] Cannot read OpenAI embedding cache: {exc}")

            doc_keys = {d.id: self._openai_doc_key(d) for d in self.docs}
            vectors: dict[str, list[float]] = {}
            missing: list[Passage] = []
            for d in self.docs:
                vec = cached_vectors.get(doc_keys[d.id])
                if vec:
                    vectors[d.id] = vec
                else:
                    missing.append(d)

            try:
                for start in range(0, len(missing), 64):
                    batch = missing[start : start + 64]
                    embeddings = self._embed_texts_openai([d.text for d in batch])
                    for doc, emb in zip(batch, embeddings):
                        vectors[doc.id] = emb
                        cached_vectors[doc_keys[doc.id]] = emb
            except Exception as exc:
                self._openai_failed = True
                self._embedding_status = f"openai_doc_error:{type(exc).__name__}"
                print(f"[Retrieval] OpenAI document embeddings failed: {exc}")
                return False

            self._openai_doc_embeddings = vectors
            self._openai_docs_ready = True
            self._embedding_status = f"openai_ready:{len(vectors)}"
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {"model": self.embedding_model, "vectors": cached_vectors}
                cache_path.write_text(json.dumps(payload), encoding="utf-8")
            except Exception as exc:
                print(f"[Retrieval] Cannot write OpenAI embedding cache: {exc}")
            return True

    def _dense_openai_local(self, query: str, lesson_id: str, k: int) -> list[tuple[int, float]]:
        if not self._ensure_openai_doc_embeddings():
            return []
        q_emb = self._embed_query_openai(query)
        if q_emb is None:
            return []
        allowed = set(self.cards.lesson_files(lesson_id))
        scored: list[tuple[int, float]] = []
        for i, d in enumerate(self.docs):
            if allowed and d.file not in allowed:
                continue
            emb = self._openai_doc_embeddings.get(d.id)
            if not emb:
                continue
            sim = dense_cosine(q_emb, emb)
            if sim > 0:
                scored.append((i, sim))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: k * 3]

    def _dense_supabase(self, query: str, lesson_id: str, k: int) -> list[tuple[int, float]]:
        """Vector search trên Supabase → [(vị trí trong self.docs, similarity)]. Lỗi thì trả rỗng."""
        if not self._dense_remote_enabled():
            return []
        try:
            q_emb = self._embed_query(query)
            if q_emb is None:
                return []
            # Vector search nằm trong đường đi của mỗi câu hỏi: thà mất phần dense còn hơn
            # bắt học viên chờ — BM25 + vector cục bộ vẫn trả kết quả dùng được.
            allowed = self.cards.lesson_files(lesson_id)
            lesson_filter = allowed[0] if allowed else (lesson_id or None)
            rows = self.sb.rpc("match_chunks", {
                "query_embedding": q_emb,
                "match_count": k * 3,
                "lesson_filter": lesson_filter,
            }, timeout=getattr(self.settings, "dense_timeout", 4.0)) or []
        except Exception as exc:
            print(f"[Retrieval] Lỗi khi gọi Supabase vector search: {exc}")
            return []
        out = []
        for item in rows:
            idx = self.pos_of.get(item.get("id"))
            if idx is not None:
                out.append((idx, item.get("similarity", 0)))
        return out

    # ---------------------------------------------------------------- BM25
    def _index_bm25(self) -> None:
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

    def _bm25_score(self, query_tokens: list[str], idx: int) -> float:
        tf = self.tf[idx]
        dl = len(self.doc_tokens[idx])
        s = 0.0
        for w in query_tokens:
            f = tf.get(w, 0)
            if f:
                s += self.idf.get(w, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    # ---------------------------------------------------------------- Vector Space
    def _index_vectors(self) -> None:
        """Xây dựng không gian vector cho ngữ nghĩa (subword 3-gram + từ khoá TF-IDF)."""
        self.doc_vectors: list[dict[str, float]] = []
        for i, d in enumerate(self.docs):
            vec: dict[str, float] = {}
            # Word level TF-IDF
            for w, f in self.tf[i].items():
                idf = self.idf.get(w, 1.0)
                vec[f"w:{w}"] = f * idf
            # Subword 3-gram n-gram (bắt từ đồng nghĩa, gốc từ, chính tả)
            raw = f"{d.section} {d.text}".lower()
            ngrams = [raw[j:j+3] for j in range(len(raw) - 2) if " " not in raw[j:j+3]]
            ng_tf = Counter(ngrams)
            for ng, f in ng_tf.items():
                vec[f"ng:{ng}"] = f * 0.5
            self.doc_vectors.append(vec)

    def _query_vector(self, query: str) -> dict[str, float]:
        q_toks = self._toks(query)
        vec: dict[str, float] = {}
        q_tf = Counter(q_toks)
        for w, f in q_tf.items():
            vec[f"w:{w}"] = f * self.idf.get(w, 1.0)
        raw = query.lower()
        ngrams = [raw[j:j+3] for j in range(len(raw) - 2) if " " not in raw[j:j+3]]
        for ng, f in Counter(ngrams).items():
            vec[f"ng:{ng}"] = f * 0.5
        return vec

    # ---------------------------------------------------------------- Search API
    def search(self, query: str, lesson_id: str, k: int = 5, boost_ids: list[str] | None = None) -> list[Passage]:
        """Tìm kiếm tài liệu. Hỗ trợ 3 chế độ: bm25, dense, và hybrid (mặc định RRF).

        Một lượt hỏi thường tìm 2 lần với cùng truy vấn (đoán khái niệm rồi lấy căn cứ),
        nên kết quả được nhớ lại — tránh gọi embedding + Supabase hai lần cho cùng một câu.
        """
        ck = (query, lesson_id, k, tuple(boost_ids or ()), self.retrieval_mode)
        hit = self._search_cache.get(ck)
        if hit is not None:
            self._search_cache.move_to_end(ck)
            return list(hit)
        if self.retrieval_mode == "bm25":
            out = self._search_bm25_only(query, lesson_id, k, boost_ids)
        elif self.retrieval_mode == "dense":
            out = self._search_dense_only(query, lesson_id, k, boost_ids)
        else:
            out = self._search_hybrid(query, lesson_id, k, boost_ids)
        self._search_cache[ck] = out
        if len(self._search_cache) > 128:
            self._search_cache.popitem(last=False)
        return list(out)

    def _search_bm25_only(self, query: str, lesson_id: str, k: int, boost_ids: list[str] | None) -> list[Passage]:
        allowed = set(self.cards.lesson_files(lesson_id))
        q = self._toks(query)
        boost = set(boost_ids or [])
        scored = []
        for i, d in enumerate(self.docs):
            if allowed and d.file not in allowed:
                continue
            s = self._bm25_score(q, i)
            is_boosted = d.id in boost or any(sid in boost for sid in d.source_ids)
            if s > 0 and is_boosted:
                s = s * 1.5 + 0.5
            if s > 0:
                scored.append(Passage(d.id, d.section, d.text, d.file, round(s, 3), d.source_ids))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:k]

    def _search_dense_only(self, query: str, lesson_id: str, k: int, boost_ids: list[str] | None) -> list[Passage]:
        if self._openai_local_enabled():
            openai_dense_list = self._dense_openai_local(query, lesson_id, k)
            boost = set(boost_ids or [])
            scored = []
            for idx, sim in openai_dense_list:
                d = self.docs[idx]
                is_boosted = d.id in boost or any(sid in boost for sid in d.source_ids)
                if sim > 0 and is_boosted:
                    sim = sim * 1.3
                if sim > 0:
                    scored.append(Passage(d.id, d.section, d.text, d.file, round(sim, 3), d.source_ids))
            scored.sort(key=lambda p: p.score, reverse=True)
            return scored[:k]

        allowed = set(self.cards.lesson_files(lesson_id))
        openai_dense_list = self._dense_openai_local(query, lesson_id, k) if self._openai_local_enabled() else []
        supabase_dense_list = [] if openai_dense_list else self._dense_supabase(query, lesson_id, k)
        q_vec = self._query_vector(query)
        boost = set(boost_ids or [])
        scored = []
        
        # Nếu có Supabase thì dùng kết quả Supabase
        if supabase_dense_list:
            for idx, sim in supabase_dense_list:
                d = self.docs[idx]
                is_boosted = d.id in boost or any(sid in boost for sid in d.source_ids)
                if sim > 0 and is_boosted:
                    sim = sim * 1.3
                if sim > 0:
                    scored.append(Passage(d.id, d.section, d.text, d.file, round(sim, 3), d.source_ids))
        else:
            # Fallback Local TF-IDF giả lập
            for i, d in enumerate(self.docs):
                if allowed and d.file not in allowed:
                    continue
                sim = cosine_similarity(q_vec, self.doc_vectors[i])
                is_boosted = d.id in boost or any(sid in boost for sid in d.source_ids)
                if sim > 0 and is_boosted:
                    sim = sim * 1.3
                if sim > 0:
                    scored.append(Passage(d.id, d.section, d.text, d.file, round(sim, 3), d.source_ids))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:k]

    def _search_hybrid(self, query: str, lesson_id: str, k: int, boost_ids: list[str] | None) -> list[Passage]:
        """Hybrid Search kết hợp BM25 và Dense Search qua Reciprocal Rank Fusion (RRF)."""
        allowed = set(self.cards.lesson_files(lesson_id))
        q_toks = self._toks(query)
        openai_dense_list = self._dense_openai_local(query, lesson_id, k) if self._openai_local_enabled() else []
        supabase_dense_list = [] if openai_dense_list else self._dense_supabase(query, lesson_id, k)
        q_vec = self._query_vector(query)
        boost = set(boost_ids or [])

        bm25_list: list[tuple[int, float]] = []
        dense_list: list[tuple[int, float]] = []

        for i, d in enumerate(self.docs):
            if allowed and d.file not in allowed:
                continue
            # Điểm BM25
            s_bm25 = self._bm25_score(q_toks, i)
            if s_bm25 > 0:
                bm25_list.append((i, s_bm25))
                
            # Điểm Dense (Nếu Supabase rỗng thì fallback về Local TF-IDF giả lập)
            if not openai_dense_list and not supabase_dense_list and not self._openai_local_enabled():
                s_dense = cosine_similarity(q_vec, self.doc_vectors[i])
                if s_dense > 0.01:
                    dense_list.append((i, s_dense))

        # Nếu Supabase trả về kết quả, sử dụng kết quả đó thay cho giả lập local
        if openai_dense_list or supabase_dense_list:
            dense_list = openai_dense_list or supabase_dense_list

        bm25_list.sort(key=lambda x: x[1], reverse=True)
        dense_list.sort(key=lambda x: x[1], reverse=True)

        bm25_ranks = {doc_idx: rank for rank, (doc_idx, _) in enumerate(bm25_list, start=1)}
        dense_ranks = {doc_idx: rank for rank, (doc_idx, _) in enumerate(dense_list, start=1)}

        all_candidates = set(bm25_ranks.keys()) | set(dense_ranks.keys())
        scored: list[Passage] = []

        alpha = self.hybrid_alpha  # Trọng số BM25 vs Dense
        rrf_k = self.rrf_k

        for doc_idx in all_candidates:
            d = self.docs[doc_idx]
            r_bm = bm25_ranks.get(doc_idx)
            r_de = dense_ranks.get(doc_idx)

            # Công thức RRF
            rrf_score = 0.0
            if r_bm is not None:
                rrf_score += alpha / (rrf_k + r_bm)
            if r_de is not None:
                rrf_score += (1.0 - alpha) / (rrf_k + r_de)

            # Boost cho các đoạn có trong thẻ khái niệm
            is_boosted = d.id in boost or any(sid in boost for sid in d.source_ids)
            if is_boosted:
                rrf_score *= 1.35

            if rrf_score > 0:
                scored.append(Passage(d.id, d.section, d.text, d.file, round(rrf_score * 100, 3), d.source_ids))

        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:k]

    def get(self, source_id: str) -> Passage | None:
        return self.by_id.get(source_id)

    def text_for(self, source_id: str, max_chars: int) -> str:
        p = self.by_id.get(source_id)
        if not p:
            return self.cards.summary(source_id)
        return p.text if len(p.text) <= max_chars else p.text[:max_chars].rsplit(" ", 1)[0] + " …"

# Force reload 2
