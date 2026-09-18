# Adaptive Explainer — Workflow cho team THE-LIEMS

Nhóm **THE-LIEMS** · Lớp 3B · Phòng E403 · Track A2 · VLearn Tutor  
Nhánh: `vinai-levanviet-02504`

Canvas: [`canvas.md`](canvas.md) · Spec: [`spec.md`](spec.md)

Tài liệu này mô tả **luồng đang chạy trong code**, không phải ý tưởng trên giấy.

---

## 1. Sản phẩm làm gì?

Học viên bôi đen khái niệm trên slide (ví dụ *RAG*, *self-attention*) rồi hỏi Trợ giảng AI.

Pain: tutor cũ giải thích **một kiểu hàn lâm**, không đúng tầm → hỏi lại 2–3 lần (`T10728`, `T10317`, `T10536`).

Sản phẩm:

1. Lần đầu trả lời **đúng khái niệm** (học thuật).
2. Nếu học viên kêu **khó hiểu** → **không** giải thích mù quáng lần nữa.
3. Hỏi **một câu thăm dò** trình độ.
4. Ghi `User_Level` theo **từng topic**.
5. Giải thích lại đúng tầm (ELI5 / gắn slide / kỹ thuật), **bám tài liệu**, không bịa.

---

## 2. Happy path (đúng spec dump-first)

Cờ: `DUMP_FIRST=true` (mặc định trong `.env`).

### Lượt 1 — hỏi khái niệm

Học viên: **「RAG là gì?」**

| Bước | Node | Việc |
|---|---|---|
| Tiếp nhận | `ingest` | Lưu tin nhắn, tăng `turn_index` |
| Profile | `load_profile` | Đọc skill map. Chưa có hàng → `user_level = unknown` |
| Retrieve | `retrieve` | Query vector (memory hoặc Qdrant) lấy đoạn bài giảng |
| Intent | `intent_router` | `ask_concept` |
| Route | `DUMP_FIRST` + unknown | → **`tutor_standard`** |
| Trả lời | `tutor_standard` | Giải thích **technical / học thuật**, cite slide |
| Lưu | `persist_turn` | Short-term (checkpoint) + messages |

Học viên nhận định nghĩa chuẩn, chưa đổi level.

### Lượt 2 — kêu khó

Học viên: **「khó hiểu quá」** / **「giải thích chi tiết hơn」** / nút *Mình chưa hiểu* trên UI.

| Bước | Việc |
|---|---|
| Intent | `clarify_harder` (regex: khó hiểu, giải thích lại, đơn giản hơn, chi tiết hơn…) |
| Route | Chưa probe episode này → **`assessor_probe`** |
| Assessor | 1 câu MCQ 3 lựa chọn (template theo topic; có `LLM_API_KEY` thì LLM đọc lịch sử rồi sinh câu) |
| Ví dụ | *Để giải thích RAG vừa tầm, bạn đã từng làm việc với Database chưa?* |

**Không** giải thích lại ngay.

### Lượt 3 — trả lời probe

Học viên: **「Mình mới học code」** hoặc bấm choice beginner.

| Bước | Node | Việc |
|---|---|---|
| Intent | `answer_probe` | Đang `awaiting_probe = true` |
| Chấm | `assessor_score` | Map choice / keyword → `beginner` / `intermediate` / `advanced` |
| Ghi level | `persist_level` | `skill_levels[rag] = beginner` |
| Tutor | `tutor_adaptive` | Persona ELI5: ẩn dụ đời sống, ngắn, bám excerpt |
| Lưu | `persist_turn` | Tắt cờ probe; lần sau cùng topic **skip probe** |

### Lượt sau

- Hỏi *RAG* lần nữa → đã có skill → giải thích đúng tầm, **không** hỏi probe.
- **「nâng cao hơn」** → +1 bậc (`beginner` → `intermediate` = `slide_short`).
- **「ngắn lại」** → cùng level, rút câu.
- Topic khác (Docker) đang chờ probe RAG → **abandon** probe cũ, retrieve topic mới.

Chạy thử in-process:

```bash
python -m app.service.agent.demo
```

---

## 3. Graph (LangGraph) — team đọc khi sửa agent

File: `app/service/agent/graph.py`, routing: `app/service/agent/routing.py`.

```
ingest → load_profile → regex_prepass → retrieve → intent_router
    │
    ├─ standard            tutor_standard   (học thuật, dump-first hoặc advanced)
    ├─ probe               assessor_probe   (1 câu thăm dò)
    ├─ score               assessor_score → persist_level → tutor_adaptive
    ├─ persist_then_adapt  persist_level → tutor_adaptive  (kêu khó khi đã probe)
    ├─ adapt               tutor_adaptive   (đã có level)
    ├─ miss                retrieval_miss   (không bịa)
    └─ redirect            tutor_redirect   (off-topic / meta)
              ↓
         validator (mặc định tắt)
              ↓
         persist_turn → END
```

**Intent** (regex, không LLM): `ask_concept`, `clarify_harder`, `ask_deeper`, `answer_probe`, `refuse_probe`, `off_topic`, `meta`.

**Level theo topic**, không một số cho cả user: `rag=beginner`, `self_attention=intermediate`.

**Ba persona tutor** (`app/service/ai/prompts.py`):

| Level | Mode | Cách nói |
|---|---|---|
| beginner | `eli5` | Ẩn dụ đời sống, ngắn |
| intermediate | `slide_short` | “Trên slide N, X nghĩa là Y” |
| advanced | `technical` | Cơ chế + 1 trade-off, bám excerpt |

State quan trọng: `current_topic`, `user_level`, `learning_bottleneck`, `awaiting_probe_answer`, `skill_map`, `retrieved_docs`.

---

## 4. Kiến trúc code (để biết sửa file nào)

```
HTTP  app/router/          chat, vlearn (UI), profile, health
  ↓
SVC   app/service/         ChatService, VLearnService
      app/service/agent/   graph, nodes, routing
      app/service/ai/      LLM + embed + probe
  ↓
DATA  app/repository/      conversation (memory/Postgres), vector (memory/Qdrant)
      app/model/           entity
      app/schema/          request/response
```

| Thành phần | Công nghệ | Runtime mặc định |
|---|---|---|
| Orchestration | LangGraph | Đang chạy |
| API | FastAPI async | `uvicorn app.main:app` |
| UI | `app/ui` (mock VLearn từ main) | http://localhost:8000/ `?mode=live` |
| Long-term DB | Postgres (code + schema.sql) | **Chưa** — `.env` `STORAGE=memory` |
| Short-term | MemorySaver; Redis chỉ ping | **Chưa checkpoint Redis** |
| RAG | Hashing + lexical; Qdrant optional | **Memory** |
| LLM | OpenAI-compatible (xAI) | **Trống key → template** |

UI gọi `/api/chat` (hợp đồng mock). API nội bộ: `POST /v1/chat`, stream `POST /v1/chat/stream`.

---

## 5. Phân công (sửa đúng lớp)

| Người | Đụng vào |
|---|---|
| Việt | Prompt `app/service/ai/prompts.py`, persona, spec |
| Đoàn | Golden `app/eval/golden_set.csv`, `eval_agent.py`, cards `app/data/cards/` |
| Khoa | Router, repository Postgres/Qdrant, Docker, `/readyz` |
| Dũng | `app/ui/` (index, css, js) — bôi đen slide, chip khó hiểu, sổ tay |

---

## 6. Chạy local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp -n .env.example .env

python -m app.service.agent.demo
uvicorn app.main:app --reload --port 8000
pytest tests/ -q
```

Mở **http://localhost:8000/** → trang học VLearn.

Hồ sơ demo UI: *Chưa có hồ sơ* = chưa có skill (dump rồi probe). *Đã vững* = đã có level, giải thích ngay.

### Bật Postgres / Qdrant / Redis (khi Docker chạy)

`.env`:

```
STORAGE=postgres
VECTOR_BACKEND=qdrant
CHECKPOINTER=redis
DATABASE_URL=postgresql+asyncpg://vlearn:vlearn@localhost:5432/vlearn
LLM_API_KEY=          # điền để tutor + probe dùng model thật
```

```bash
docker compose up -d postgres redis qdrant
```

Không kết nối được → **fallback memory**, app vẫn chạy. `GET /readyz` báo `storage` / `vector` / `redis`.

### Data pack (không commit nguyên văn)

```bash
python app/scripts/build_local_data.py
bash app/scripts/check_no_data.sh
```

---

## 7. Việc còn lại (roadmap ngắn)

1. Bật Docker + `STORAGE=postgres` — level sống sau restart.
2. Điền `LLM_API_KEY` — tutor/assessor không còn template.
3. RedisSaver cho graph (hiện Redis chỉ health; cờ probe đã thiết kế lưu Postgres).
4. Ingest transcript đầy đủ vào Qdrant.
5. SSE stream từng token LLM (hiện cắt câu đã generate xong).
6. Siết golden eval dump-first (`python app/eval/eval_agent.py`).

---

## 8. An toàn

- Không commit `.env`, CSV/PDF transcript (xem `.gitignore`).
- Input học viên là **dữ liệu**, không phải chỉ thị (injection → từ chối).
- Không có chunk retrieve → `retrieval_miss`, không bịa.
- Probe tối đa **1 câu / episode**.
