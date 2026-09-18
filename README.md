# Trợ giảng AI — giải thích lại đúng mức (VLearn · Track A2)

Nhóm **THE LIEMS** · Lớp 3B · Phòng E403 · Mini Hackathon AI, Batch 04

> Khi học viên đọc lời giải thích của tutor mà **vẫn chưa hiểu**, trợ giảng hiện tại giảng lại **cùng một kiểu**.
> Sản phẩm này xác định *học viên đang vướng ở đâu*, rồi giải thích lại **đúng mức**, **bám bài giảng** và **có nguồn**.

---

## 1. Thành viên & phân công

| Họ và Tên | Mã Học Viên | Vai trò chính | Phần việc đảm nhiệm |
|---|---|---|---|
|  |  | Evidence & khảo sát | Mining chatlog, khảo sát ≥20 người, log nguyên văn |
|  |  | Prompt & thẻ khái niệm | `backend/app/prompts/`, `backend/cards/` |
|  |  | Backend & giao diện | `backend/app/`, `frontend/js/` |
|  |  | Spec, eval & demo | `spec.md`, `eval/`, video, slide |

Đội trưởng: `[tên · MSHV]`

---

## 2. Bài toán và lát cắt

- **Pain (P3):** học viên đã đọc giải thích mà vẫn chưa hiểu; tutor không biết họ vướng ở đâu nên giảng lại cùng một kiểu → hỏi đi hỏi lại, mất thời gian, hoặc hiểu lệch khi làm quiz/lab.
- **Bằng chứng (chatlog K4, 3.097 lượt):** 106 lượt / 49 học viên nói rõ chưa hiểu; tutor vẫn dùng `review_concept` **86/106 lần**, chỉ **1 lần** hỏi lại; trung vị câu trả lời **995 ký tự**. Case gốc: **T10728**.
- **Lát cắt một câu:** *Một học viên vừa đọc lời giải thích mà vẫn chưa hiểu · cần hiểu khái niệm đó · **AI chọn mức và kiểu giải thích** (dựa trên Sổ tay học tập, hỏi nhanh khi chưa chắc) · học viên nhận lời giải thích lại đúng mức, có nguồn, và trả lời đúng câu kiểm tra.*
- **Mức tự động:** Conditional. Thẻ khái niệm do TA/giảng viên duyệt một lần (Augment).
- **Phạm vi nội dung:** 6 buổi học của khoá (transcript 01–06), xem [`backend/lessons.yaml`](backend/lessons.yaml). Mỗi buổi có thẻ khái niệm riêng; trợ giảng chỉ trả lời trong phạm vi buổi đang mở.
- Chi tiết: [`spec.md`](spec.md) · thiết kế: [`docs/`](docs/)

## 3. Trạng thái

| Mốc | Nội dung | Trạng thái |
|---|---|---|
| CP1 | Canvas + repo | Xong |
| CP2 | Mock bấm được, 4 đường trải nghiệm | Xong — `frontend/` |
| CP3 | AI thật ở quyết định trung tâm + golden set + bảng đo | Xong — `backend/`, `eval/`; vòng 4: **22/23 test (96%)**, 0 case dùng mẫu dự phòng, baseline 3/21 |
| CP3+ | Mở rộng **6 buổi học** (17 thẻ khái niệm), **tài khoản học viên**, bộ nhớ dài hạn trên Supabase | Xong — `lessons.yaml`, `app/auth.py`, `app/memory.py`; 69 test backend + 17 test giao diện |
| CP4 | Chốt `spec.md` + quality bar | Còn: điền khảo sát, chấm D6, chốt bar |
| CP5 | Slide PDF + video dự phòng | Chưa |

---

## 4. Cài đặt

Cần **Python 3.11+**, và **Node 18+** nếu muốn chạy test của giao diện.

**macOS / Linux**

```bash
git clone <repo> && cd K4-3B-E403-THE-LIEMS
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r requirements.txt
cp backend/.env.example backend/.env      # điền key, KHÔNG commit file này
```

**Windows (PowerShell)**

```powershell
git clone <repo>; cd K4-3B-E403-THE-LIEMS
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\pip install -r requirements.txt
copy backend\.env.example backend\.env
```

> Trên Windows, mọi lệnh `backend/.venv/bin/xxx` đổi thành `backend\.venv\Scripts\xxx.exe`.
> Các script `.sh` (như `check_no_data.sh`) chạy bằng **Git Bash** đi kèm Git for Windows.

`.env` tối thiểu:

```ini
LLM_PROVIDER=openai        # fake | openai | gemini | claude
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

- `LLM_PROVIDER=fake` chạy được **toàn bộ luồng mà không tốn tiền và không cần key** (dùng luật + mẫu đã duyệt).
- Gemini free tier: `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-2.5-flash`, `GEMINI_API_KEY=...`.

## 5. Chạy

### 5.1 Giao diện + AI thật

```bash
# macOS / Linux
cd backend && .venv/bin/uvicorn app.main:app --port 8000
```
```powershell
# Windows
cd backend; .venv\Scripts\uvicorn.exe app.main:app --port 8000
```

Mở **http://localhost:8000/** → giao diện tự chạy ở chế độ live (gọi backend thật).

- Xem bản offline chạy bằng luật, không cần backend: thêm `?mode=mock` vào URL,
  hoặc mở thẳng `frontend/index.html` (Windows: `start frontend\index.html`).
- Lần chạy đầu, backend nạp mô hình embedding ở nền mất ~30 giây. Mở `/health` một lần
  rồi hẵng hỏi để câu đầu tiên không phải chờ (xem §8).

### 5.2 Test

```bash
# macOS / Linux
backend/.venv/bin/python -m pytest -q backend    # 69 test backend (FakeLLM, không cần key)
node --test frontend/tests/engine.test.js                           # 17 test logic giao diện
```
```powershell
# Windows
backend\.venv\Scripts\python.exe -m pytest -q backend
node --test frontend\tests\engine.test.js
```

### 5.3 Kiểm tra đang chạy trên **dữ liệu thật**

Mặc định repo không có data pack, hệ thống chạy ở **chế độ tóm tắt**. Muốn trợ giảng trích đúng nguyên văn bài giảng thì sinh dữ liệu cục bộ (file sinh ra bị `.gitignore` chặn):

```bash
# macOS / Linux — trỏ tới thư mục data/vlearn-pack của khoá, đặt NGOÀI repo
backend/.venv/bin/python scripts/build_local_data.py --pack "<đường dẫn>/data/vlearn-pack"
backend/.venv/bin/python scripts/build_index.py
```
```powershell
# Windows
backend\.venv\Scripts\python.exe scripts\build_local_data.py --pack "D:\...\data\vlearn-pack"
backend\.venv\Scripts\python.exe scripts\build_index.py
```

Dựng và kiểm tra **6 buổi học** (đoạn nào thuộc mục nào, thẻ khái niệm có trích đúng nguồn trong buổi không):

```bash
backend/.venv/bin/python scripts/build_lessons.py --pack "<đường dẫn>/data/vlearn-pack"
# chỉ kiểm tra, không sinh lại dữ liệu:
backend/.venv/bin/python scripts/build_lessons.py --check
```

Dấu hiệu đang dùng dữ liệu thật:

| Kiểm ở đâu | Phải thấy |
|---|---|
| `build_lessons.py --check` | 6 dòng buổi học, cột nguồn là `local` |
| `curl -s localhost:8000/api/lessons` | 6 buổi, mỗi buổi `"source":"local"` (hoặc `supabase`) |
| `curl -s localhost:8000/health` (Windows: `curl.exe`) | `"retrieval_mode":"local","passages":384` |
| Giao diện | cột trái hiện 6 buổi; đầu bài có nhãn xanh **“Dữ liệu bài giảng trên máy”** |
| Giao diện | bấm mã nguồn `[T06-131]` dưới câu trả lời → hiện **nguyên văn lời giảng**, không phải tóm tắt |
| Báo cáo eval | dòng `retrieval: local` ở đầu `eval/results/round*.md` |

### 5.3b Tài khoản học viên và Supabase (điền key sau)

Hồ sơ mức hiểu và bộ nhớ dài hạn được lưu **theo tài khoản**, nên mỗi người đăng nhập thấy đúng dữ liệu của mình.

1. Mở Supabase → **SQL Editor** → dán toàn bộ [`backend/supabase_schema.sql`](backend/supabase_schema.sql) rồi chạy.
   File này tạo: `lecture_chunks` (bài giảng + vector), `profiles`, `strategy_memory`, `settings`, `events`, `sessions`,
   **`accounts` + `account_sessions`** (đăng nhập) và hàm `prune_learner_memory()` để bộ nhớ không phình.
2. Điền hai dòng này vào `backend/.env` (chép từ `.env.example`, **không commit**):

   ```env
   SUPABASE_URL=https://<project>.supabase.co
   SUPABASE_KEY=<service_role key>
   ```

3. Đẩy bài giảng lên Supabase (tuỳ chọn, khi muốn chạy không cần data pack trên máy):

   ```bash
   cd backend && .venv/bin/python ../scripts/sync_to_supabase.py
   ```

4. Trên giao diện: bấm nút **Đăng nhập** ở góc trên bên phải → thẻ **Đăng ký** để tạo tài khoản mới.
   Đăng nhập xong, nút đổi thành avatar chữ cái đầu — bấm vào đó để đổi tên hiển thị, đăng xuất hoặc xoá tài khoản. Sau khi đăng nhập, mọi câu hỏi, mức hiểu và
   “cách giải thích đã hiệu quả” được ghi vào tài khoản đó.

**Bộ nhớ dài hạn không phình** — ba lớp chặn (chỉnh trong `.env`):

| Cơ chế | Mặc định | Ở đâu |
|---|---|---|
| Ghi trễ: gom nhiều lượt rồi mới đẩy lên Supabase | `MEMORY_FLUSH_EVERY=3` | `app/memory.py` |
| Nén định kỳ: quên cách giải thích quá hạn, mỗi khái niệm giữ tối đa N cách, cắt nhật ký cũ | `MEMORY_COMPACT_EVERY=10`, `MEMORY_MAX_STRATEGIES=6`, `MEMORY_MAX_EVENTS=50` | `ProfileStore.compact()` |
| Chặn phía CSDL | hàm `prune_learner_memory(user_id)` | `supabase_schema.sql` |

Xem nhanh bộ nhớ đang chiếm bao nhiêu dòng: `SELECT * FROM learner_memory_size;` trong SQL Editor.
Đẩy ngay phần đang chờ: `curl -X POST localhost:8000/api/memory/flush`.

### 5.4 Thử một lượt với AI thật (rẻ, in rõ lỗi)

```bash
cd backend
.venv/bin/python ../scripts/smoke_llm.py --full --user demo-moi   --text "bước 2 là gì mình chưa hiểu, sao lại cộng trọng số và cộng vào đâu"
```
```powershell
cd backend
.venv\Scripts\python.exe ..\scripts\smoke_llm.py --full --user demo-trung-binh --text "Tính ứng dụng của self-attention"
```

Cần thấy `tìm nguồn: local`, `Độ bám bài giảng: ĐẠT`, `Dự phòng: không`. Có dòng `⚠ Lỗi gọi LLM` nghĩa là **chưa** chạy AI thật (sai key / sai tên model).

### 5.5 Đánh giá (golden set 37 case)

```bash
cd .
backend/.venv/bin/python eval/run_eval.py --round 5 --split dev            # ~$0,05
backend/.venv/bin/python eval/run_eval.py --round 5 --split test           # ~$0,06
backend/.venv/bin/python eval/run_eval.py --round 5 --split test --baseline
backend/.venv/bin/python eval/run_eval.py --round 5 --split dev --cases D13,D14   # chạy vài case cho rẻ
```
```powershell
cd .
backend\.venv\Scripts\python.exe eval\run_eval.py --round 5 --split test
```

Đọc kết quả ở `eval/results/round5-*.md`: xem cột **Dự phòng** trước cột %.

### 5.6 Xuất trace cho TA xem

```bash
cd backend && .venv/bin/python ../scripts/export_trace_sample.py --limit 2
```

Mỗi câu hỏi tốn khoảng **$0,002** và **5–10 giây** (3 lời gọi AI: chẩn đoán → viết giải thích → chấm). Câu bị từ chối không gọi AI nên miễn phí.

Cách bấm thử từng kịch bản trong giao diện: [`docs/codebase.md`](docs/codebase.md) §1.

---

## 6. ⚠️ Dữ liệu được cấp — KHÔNG public

Repo này **public**. Data pack của khoá (chatlog, transcript, slide) thuộc quy định bảo mật: không chia sẻ ra ngoài khoá, **không commit vào repo**.

**Được commit:** mã đoạn (`T06-130`, `T10728`), tóm tắt/diễn giải do nhóm tự viết, thẻ khái niệm, bộ câu thử (câu hỏi đã diễn đạt lại), bảng kết quả `%`, và **trace mẫu đã che nguyên văn** trong `eval/traces-sample/`.

**Không bao giờ commit:** nguyên văn transcript/chatlog, file CSV của data pack, `p3.db`, `traces/`, `.env`, mọi file `*.local.*`.

Cơ chế chặn đã có sẵn:

```bash
bash scripts/check_no_data.sh      # chạy trước mỗi commit
git status --ignored                         # kiểm tra file dữ liệu nằm ở mục Ignored
```

Muốn có dữ liệu nguyên văn trên máy mình (để trợ giảng trích đúng đoạn bài giảng):

```bash
# cần data pack của khoá đặt ở ngoài repo
python3 scripts/build_local_data.py --pack "<đường dẫn>/data/vlearn-pack"
```

Script sinh ra `data/chunks.local.json`, `frontend/data/sources.local.js`, `eval/golden_candidates.local.csv` — cả ba đều bị `.gitignore` chặn. **Không có chúng thì hệ thống vẫn chạy**, chỉ khác là phần "Xem đoạn gốc" hiện tóm tắt thay cho nguyên văn.

Ngoài ra: mỗi lượt chỉ gửi cho mô hình tối đa **5 đoạn × 1400 ký tự** bài giảng, không gửi chatlog. Key chỉ nằm trong `.env` của backend, giao diện không bao giờ gọi thẳng provider.

---

## 7. Cấu trúc repo

Từ v5, `codebase/` được bỏ đi: `backend/` và `frontend/` nằm thẳng ở gốc để Render và Vercel
trỏ vào đúng một thư mục mà không cần cấu hình đường dẫn lồng nhau.

```text
K4-3B-E403-THE-LIEMS/
├── README.md              # file này
├── spec.md                # AI Spec (nộp CP4)
├── requirements.txt       # trỏ sang backend/requirements.txt
├── render.yaml            # cấu hình deploy backend lên Render (§10)
├── vercel.json            # cấu hình deploy frontend lên Vercel (§10)
│
├── backend/               # FastAPI + agent  → deploy lên Render
│   ├── app/               #   main.py · orchestrator.py · retrieval.py · lessons.py · auth.py · memory.py
│   ├── app/prompts/       #   system.md · diagnose.md · explain.md · judge.md · VERSION
│   ├── cards/             #   17 thẻ khái niệm đã duyệt (nguồn sự thật của câu trả lời)
│   ├── lessons.yaml       #   danh mục 6 buổi học
│   ├── tests/             #   69 test (FakeLLM, không cần key)
│   ├── requirements.txt   #   đầy đủ, có sentence-transformers (dùng trên máy)
│   ├── requirements-deploy.txt  # gọn, không torch — dùng trên Render (§10)
│   └── supabase_schema.sql
│
├── frontend/              # giao diện VLearn (HTML/CSS/JS thuần) → deploy lên Vercel
│   ├── index.html
│   ├── config.js          #   địa chỉ backend khi deploy tách đôi
│   ├── js/                #   lessons.js (6 buổi, slide) · app.js (chat) · auth.js (tài khoản) · api.js
│   └── tests/             #   17 test logic giao diện (Node)
│
├── data/                  # chunks.local.json — sinh trên máy, KHÔNG commit
├── eval/                  # golden_set.csv, run_eval.py, rubric.md, results/, traces-sample/
├── scripts/               # build_local_data · build_lessons · build_index · sync_to_supabase · …
└── docs/                  # tài liệu thiết kế + codebase.md (kiến trúc, kịch bản demo)
```

## 8. Tốc độ trả lời

Một lượt hỏi đi qua **tìm nguồn → LLM chẩn đoán → LLM soạn bài → LLM chấm**. Đo bằng
`traces/<ngày>.jsonl`, trường `marks_ms` cho biết từng chặng hết bao lâu:

```bash
backend/.venv/bin/python - <<'EOF'
import json, glob
for r in [json.loads(l) for l in open(sorted(glob.glob('backend/traces/*.jsonl'))[-1], encoding='utf-8')][-5:]:
    print(r['latency_ms'], 'ms', r.get('marks_ms'), [(u['task'], u.get('latency_ms')) for u in r.get('llm', [])])
EOF
```

Các nút vặn (đặt trong `.env` hoặc biến môi trường trên Render):

| Biến | Mặc định | Tác dụng |
|---|---|---|
| `SPECULATIVE_EXPLAIN` | `1` | Soạn sẵn bài theo luật **song song** lúc LLM chẩn đoán. Luật đoán đúng (phần lớn lượt) thì tiết kiệm trọn một vòng gọi mô hình. Đặt `0` để chạy tuần tự, tốn ít token hơn nhưng chậm hơn. |
| `JUDGE_ONLY_WHEN_NOVEL` | `1` | Bỏ bước LLM chấm khi câu trả lời chỉ gồm phần đã có người duyệt (không có gì để chấm). |
| `USE_JUDGE` | `1` | `0` = bỏ hẳn bước chấm: nhanh hơn ~2–3 giây mỗi lượt nhưng **mất một lớp kiểm chứng**. Chỉ nên tắt khi quay demo. |
| `RETRIEVAL_MODE` | `hybrid` | `bm25` bỏ vector search trên Supabase → bớt ~0,5–2 giây mỗi câu hỏi. Đây là mặc định khi deploy (xem `render.yaml`). |
| `DENSE_TIMEOUT` | `4` | Trần chờ vector search. Quá hạn thì bỏ phần dense, vẫn trả lời bằng BM25. |
| `GEMINI_THINKING_BUDGET` | `0` | Gemini 2.5 mặc định bật "thinking" → chậm thêm vài giây mỗi lượt. `-1` để trả về mặc định của Google. |

Hai điểm nghẽn đã xử lý, ghi lại để khỏi lặp lại:

- **Mô hình embedding cục bộ nạp mất ~30 giây** và trước đây nạp ngay trong câu hỏi đầu tiên của học viên.
  Giờ được nạp ở nền lúc khởi động (`app/retrieval.py` · `_load_embedder`).
- **Mỗi lời gọi Supabase mở một kết nối TLS mới** (~1 giây). Giờ dùng lại một `httpx.Client`
  (`app/supabase_client.py` · `client`).

## 9. Quy ước khi làm tiếp

1. **Không sửa nhãn case test cho khớp kết quả.** Tập `test` chỉ để báo cáo; sửa prompt thì thử trên tập `dev`.
2. **Thẻ khái niệm mới phải có người duyệt** (`reviewed: true`) mới được dùng lúc chạy. Dùng `scripts/draft_cards.py` để AI soạn nháp.
3. **Đổi prompt thì tăng `backend/app/prompts/VERSION`** và ghi một dòng vào `eval/changelog.md`.
4. Khi đọc báo cáo eval, **xem cột "Dự phòng" trước cột %**: `template:validator` nghĩa là câu trả lời của AI bị loại và hệ thống dùng mẫu đã duyệt.
5. Trước khi push: chạy test + `check_no_data.sh`.

## 10. Deploy — backend lên Render, frontend lên Vercel

Kiến trúc khi deploy: **Vercel** phục vụ `frontend/` (tĩnh) và chuyển tiếp `/api/*` sang
**Render** chạy `backend/`. Nhờ chuyển tiếp, trình duyệt thấy mọi thứ cùng một tên miền nên
không dính CORS, và **API key không bao giờ rời backend**.

```
Trình duyệt ──► Vercel (frontend/)  ──rewrites──►  Render (backend/)  ──►  Supabase
                                                        └──►  OpenAI / Gemini / Claude
```

### 10.1 Chuẩn bị Supabase (làm trước)

Máy Render **không có** `data/chunks.local.json` (đã bị `.gitignore` chặn, xem §6), nên Supabase
là nguồn bài giảng khi chạy trên mạng. Backend tự xoay: không thấy file cục bộ thì nó **kéo toàn bộ
`lecture_chunks` từ Supabase lúc khởi động** (`app/retrieval.py`, mục 3) rồi chạy BM25 trên đúng
nguyên văn đó — không cần mô hình embedding, nên vừa gói free của Render.

1. Tạo project trên [supabase.com](https://supabase.com) → **SQL Editor** → chạy toàn bộ
   [`backend/supabase_schema.sql`](backend/supabase_schema.sql).
2. Đẩy nội dung bài giảng lên (chạy trên máy đã có data pack):
   ```bash
   backend/.venv/bin/python scripts/build_local_data.py --pack "<đường dẫn>/data/vlearn-pack"
   backend/.venv/bin/python scripts/sync_to_supabase.py
   ```
3. Lấy **Project URL** và **service_role key** ở *Settings → API*. Key này chỉ điền vào Render,
   **không bao giờ đưa ra trình duyệt**.

Kiểm tra trước khi deploy — cả ba dòng phải `OK`:

```bash
cd backend && .venv/bin/python -c "
from app.config import load_settings
from app.supabase_client import SupabaseClient
s = load_settings(); sb = SupabaseClient(s.supabase_url, s.supabase_key)
for t in ['lecture_chunks','person_accounts','person_profiles']:
    r = sb.client.get(f'{sb.rest_url}/{t}', params={'select':'*','limit':'1'})
    print(t, 'OK' if r.status_code == 200 else 'LỖI ' + str(r.status_code))
"
```

> Nếu `lecture_chunks` trống, trang deploy vẫn chạy nhưng chỉ hiện **tóm tắt** trong
> `cards/_sources.yaml` và câu trả lời sẽ cụt hơn hẳn bản chạy ở máy.

### 10.2 Backend lên Render

1. Render → **New → Blueprint** → chọn repo này. Render đọc [`render.yaml`](render.yaml) sẵn có
   (`rootDir: backend`, cài `requirements-deploy.txt`, health check `/health`).
2. Vào **Environment** điền các biến để `sync: false` — Render không nhận chúng từ file:

   | Biến | Giá trị |
   |---|---|
   | `OPENAI_API_KEY` | key của nhóm (hoặc `GEMINI_API_KEY` nếu dùng Gemini) |
   | `SUPABASE_URL` | Project URL ở bước 10.1 |
   | `SUPABASE_KEY` | service_role key |
   | `ALLOWED_ORIGINS` | bỏ trống nếu dùng rewrites; điền tên miền riêng nếu có |

3. Deploy xong, kiểm tra: `https://<tên-app>.onrender.com/health` phải trả `{"status":"ok",...}`.

> **Gói free của Render ngủ sau ~15 phút không ai dùng**, lượt hỏi đầu tiên sau đó mất 30–60 giây
> để đánh thức. Trước khi demo, mở `/health` một lần cho máy tỉnh dậy.

> `requirements-deploy.txt` **không cài** `sentence-transformers`/`torch` (~2 GB, vượt gói free).
> Thiếu gói này thì vector search tự tắt và hệ thống chạy bằng BM25 trên nguyên văn kéo từ
> `lecture_chunks` — đã lường trước trong `app/retrieval.py`, không phải lỗi.

Log khởi động đúng phải có dòng:

```
[Retrieval] Nạp 384 đoạn bài giảng từ Supabase.
```

Không thấy dòng này nghĩa là `SUPABASE_URL`/`SUPABASE_KEY` sai hoặc bảng trống → quay lại §10.1.

### 10.3 Frontend lên Vercel

1. Sửa [`vercel.json`](vercel.json): thay `https://vlearn-tutor-api.onrender.com` bằng URL Render
   thật ở cả **hai** mục `rewrites` (`/api/:path*` và `/health`).
2. Vercel → **Add New → Project** → chọn repo này:
   - **Framework Preset:** `Other`
   - **Build Command:** để trống
   - **Output Directory:** `frontend`

   (`vercel.json` đã khai `outputDirectory` nên thường Vercel tự điền đúng.)
3. Deploy xong mở `https://<tên-app>.vercel.app/` — trang tự chạy ở chế độ live.

**Không muốn dùng rewrites?** Bỏ mục `rewrites` trong `vercel.json`, rồi:
- điền URL Render vào [`frontend/config.js`](frontend/config.js):
  `window.VLEARN_API_BASE = "https://<tên-app>.onrender.com";`
- đặt `ALLOWED_ORIGINS=https://<tên-app>.vercel.app` bên Render.

### 10.4 Kiểm tra sau khi deploy

| Bước | Phải thấy |
|---|---|
| `https://<render>/health` | `{"status":"ok", "provider":"openai", ...}` |
| Mở trang Vercel | Danh sách 6 buổi học ở cột trái |
| Nhãn dưới tiêu đề buổi | `Dữ liệu bài giảng từ Supabase` (nếu là `Chưa có data pack` → xem lại bước 10.1) |
| Bấm **Đăng nhập** → tạo tài khoản | Avatar hiện ở góc phải, lời chào đổi thành tên bạn |
| Hỏi một khái niệm của buổi đang mở | Trả lời có **nguồn `[T06-xxx]`** bấm xem được |

---

## 11. Việc còn lại

- Soạn thẻ khái niệm **Transformer** (case T21 đang trượt vì thiếu thẻ).
- 2 người chấm độc lập chiều **D6 — dễ hiểu, đúng mức** theo `eval/rubric.md`.
- Điền số khảo sát và chốt quality bar trong `spec.md`.
- Vòng validation với ≥2 willing user, ghi vào `validation/log.md`.
- Quay video 30 giây (CP3) và video demo dự phòng (CP5).
