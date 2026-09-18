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
|  |  | Backend & giao diện | `backend/app/`, `mock/js/` |
|  |  | Spec, eval & demo | `spec.md`, `eval/`, video, slide |

Đội trưởng: `[tên · MSHV]`

---

## 2. Bài toán và lát cắt

- **Pain (P3):** học viên đã đọc giải thích mà vẫn chưa hiểu; tutor không biết họ vướng ở đâu nên giảng lại cùng một kiểu → hỏi đi hỏi lại, mất thời gian, hoặc hiểu lệch khi làm quiz/lab.
- **Bằng chứng (chatlog K4, 3.097 lượt):** 106 lượt / 49 học viên nói rõ chưa hiểu; tutor vẫn dùng `review_concept` **86/106 lần**, chỉ **1 lần** hỏi lại; trung vị câu trả lời **995 ký tự**. Case gốc: **T10728**.
- **Lát cắt một câu:** *Một học viên vừa đọc lời giải thích mà vẫn chưa hiểu · cần hiểu khái niệm đó · **AI chọn mức và kiểu giải thích** (dựa trên Sổ tay học tập, hỏi nhanh khi chưa chắc) · học viên nhận lời giải thích lại đúng mức, có nguồn, và trả lời đúng câu kiểm tra.*
- **Mức tự động:** Conditional. Thẻ khái niệm do TA/giảng viên duyệt một lần (Augment).
- Chi tiết: [`spec.md`](spec.md) · thiết kế: [`docs/`](docs/)

## 3. Trạng thái

| Mốc | Nội dung | Trạng thái |
|---|---|---|
| CP1 | Canvas + repo | Xong |
| CP2 | Mock bấm được, 4 đường trải nghiệm | Xong — `codebase/mock/` |
| CP3 | AI thật ở quyết định trung tâm + golden set + bảng đo | Xong — `codebase/backend/`, `codebase/eval/`; vòng 4: **22/23 test (96%)**, 0 case dùng mẫu dự phòng, baseline 3/21 |
| CP4 | Chốt `spec.md` + quality bar | Còn: điền khảo sát, chấm D6, chốt bar |
| CP5 | Slide PDF + video dự phòng | Chưa |

---

## 4. Cài đặt

Cần **Python 3.11+**, và **Node 18+** nếu muốn chạy test của giao diện.

**macOS / Linux**

```bash
git clone <repo> && cd K4-3B-E403-THE-LIEMS
python3 -m venv codebase/backend/.venv
codebase/backend/.venv/bin/pip install -r requirements.txt
cp codebase/backend/.env.example codebase/backend/.env      # điền key, KHÔNG commit file này
```

**Windows (PowerShell)**

```powershell
git clone <repo>; cd K4-3B-E403-THE-LIEMS
py -3.11 -m venv codebase\backend\.venv
codebase\backend\.venv\Scripts\pip install -r requirements.txt
copy codebase\backend\.env.example codebase\backend\.env
```

> Trên Windows, mọi lệnh `codebase/backend/.venv/bin/xxx` đổi thành `codebase\backend\.venv\Scripts\xxx.exe`.
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
cd codebase/backend && .venv/bin/uvicorn app.main:app --port 8000
```
```powershell
# Windows
cd codebase\backend; .venv\Scripts\uvicorn.exe app.main:app --port 8000
```

Mở **http://localhost:8000/** → mock tự chạy ở chế độ live (gọi backend).
Chỉ muốn xem giao diện, không cần cài gì: mở thẳng `codebase/mock/index.html` (Windows: `start codebase\mock\index.html`) — khi đó logic chạy bằng luật.

### 5.2 Test

```bash
# macOS / Linux
codebase/backend/.venv/bin/python -m pytest -q codebase/backend    # 43 test backend (FakeLLM, không cần key)
node --test codebase/tests/engine.test.js                           # 17 test logic giao diện
```
```powershell
# Windows
codebase\backend\.venv\Scripts\python.exe -m pytest -q codebase\backend
node --test codebase\tests\engine.test.js
```

### 5.3 Kiểm tra đang chạy trên **dữ liệu thật**

Mặc định repo không có data pack, hệ thống chạy ở **chế độ tóm tắt**. Muốn trợ giảng trích đúng nguyên văn bài giảng thì sinh dữ liệu cục bộ (file sinh ra bị `.gitignore` chặn):

```bash
# macOS / Linux — trỏ tới thư mục data/vlearn-pack của khoá, đặt NGOÀI repo
codebase/backend/.venv/bin/python codebase/scripts/build_local_data.py --pack "<đường dẫn>/data/vlearn-pack"
codebase/backend/.venv/bin/python codebase/scripts/build_index.py
```
```powershell
# Windows
codebase\backend\.venv\Scripts\python.exe codebase\scripts\build_local_data.py --pack "D:\...\data\vlearn-pack"
codebase\backend\.venv\Scripts\python.exe codebase\scripts\build_index.py
```

Dấu hiệu đang dùng dữ liệu thật:

| Kiểm ở đâu | Phải thấy |
|---|---|
| `build_index.py` | dòng đầu `Chế độ: local · 260 đoạn` |
| `curl -s localhost:8000/health` (Windows: `curl.exe`) | `"retrieval_mode":"local","passages":260` |
| Giao diện | bấm mã nguồn `[T06-131]` dưới câu trả lời → hiện **nguyên văn lời giảng**, không phải tóm tắt |
| Báo cáo eval | dòng `retrieval: local` ở đầu `eval/results/round*.md` |

### 5.4 Thử một lượt với AI thật (rẻ, in rõ lỗi)

```bash
cd codebase/backend
.venv/bin/python ../scripts/smoke_llm.py --full --user demo-moi   --text "bước 2 là gì mình chưa hiểu, sao lại cộng trọng số và cộng vào đâu"
```
```powershell
cd codebase\backend
.venv\Scripts\python.exe ..\scripts\smoke_llm.py --full --user demo-trung-binh --text "Tính ứng dụng của self-attention"
```

Cần thấy `tìm nguồn: local`, `Độ bám bài giảng: ĐẠT`, `Dự phòng: không`. Có dòng `⚠ Lỗi gọi LLM` nghĩa là **chưa** chạy AI thật (sai key / sai tên model).

### 5.5 Đánh giá (golden set 37 case)

```bash
cd codebase
backend/.venv/bin/python eval/run_eval.py --round 5 --split dev            # ~$0,05
backend/.venv/bin/python eval/run_eval.py --round 5 --split test           # ~$0,06
backend/.venv/bin/python eval/run_eval.py --round 5 --split test --baseline
backend/.venv/bin/python eval/run_eval.py --round 5 --split dev --cases D13,D14   # chạy vài case cho rẻ
```
```powershell
cd codebase
backend\.venv\Scripts\python.exe eval\run_eval.py --round 5 --split test
```

Đọc kết quả ở `eval/results/round5-*.md`: xem cột **Dự phòng** trước cột %.

### 5.6 Xuất trace cho TA xem

```bash
cd codebase/backend && .venv/bin/python ../scripts/export_trace_sample.py --limit 2
```

Mỗi câu hỏi tốn khoảng **$0,002** và **5–10 giây** (3 lời gọi AI: chẩn đoán → viết giải thích → chấm). Câu bị từ chối không gọi AI nên miễn phí.

Cách bấm thử từng kịch bản trong giao diện: [`codebase/README.md`](codebase/README.md) §1.

---

## 6. ⚠️ Dữ liệu được cấp — KHÔNG public

Repo này **public**. Data pack của khoá (chatlog, transcript, slide) thuộc quy định bảo mật: không chia sẻ ra ngoài khoá, **không commit vào repo**.

**Được commit:** mã đoạn (`T06-130`, `T10728`), tóm tắt/diễn giải do nhóm tự viết, thẻ khái niệm, bộ câu thử (câu hỏi đã diễn đạt lại), bảng kết quả `%`, và **trace mẫu đã che nguyên văn** trong `codebase/eval/traces-sample/`.

**Không bao giờ commit:** nguyên văn transcript/chatlog, file CSV của data pack, `p3.db`, `traces/`, `.env`, mọi file `*.local.*`.

Cơ chế chặn đã có sẵn:

```bash
bash codebase/scripts/check_no_data.sh      # chạy trước mỗi commit
git status --ignored                         # kiểm tra file dữ liệu nằm ở mục Ignored
```

Muốn có dữ liệu nguyên văn trên máy mình (để trợ giảng trích đúng đoạn bài giảng):

```bash
# cần data pack của khoá đặt ở ngoài repo
python3 codebase/scripts/build_local_data.py --pack "<đường dẫn>/data/vlearn-pack"
```

Script sinh ra `codebase/data/chunks.local.json`, `codebase/mock/data/sources.local.js`, `codebase/eval/golden_candidates.local.csv` — cả ba đều bị `.gitignore` chặn. **Không có chúng thì hệ thống vẫn chạy**, chỉ khác là phần "Xem đoạn gốc" hiện tóm tắt thay cho nguyên văn.

Ngoài ra: mỗi lượt chỉ gửi cho mô hình tối đa **3 đoạn × 900 ký tự** bài giảng, không gửi chatlog. Key chỉ nằm trong `.env` của backend, giao diện không bao giờ gọi thẳng provider.

---

## 7. Cấu trúc repo

```text
K4-3B-E403-THE-LIEMS/
├── README.md              # file này
├── spec.md                # AI Spec (nộp CP4)
├── requirements.txt       # trỏ sang codebase/backend/requirements.txt
├── docs/                  # tài liệu thiết kế: pain point, workflow, mức tự động hoá, hạ tầng backend
└── codebase/
    ├── README.md          # hướng dẫn chi tiết + kiến trúc + kịch bản demo
    ├── mock/              # giao diện VLearn (HTML/CSS/JS thuần), chạy được cả khi không có backend
    ├── backend/           # FastAPI + agent (xem backend/README.md)
    ├── eval/              # golden_set.csv (35 case), run_eval.py, rubric.md, coverage.md,
    │                       #   results/ (bảng %), traces-sample/ (prompt + phản hồi thô, đã che nguyên văn)
    ├── scripts/           # build_local_data · build_index · draft_cards · smoke_llm ·
    │                       #   export_trace_sample · check_no_data
    └── tests/             # test logic của giao diện (Node)
```

## 8. Quy ước khi làm tiếp

1. **Không sửa nhãn case test cho khớp kết quả.** Tập `test` chỉ để báo cáo; sửa prompt thì thử trên tập `dev`.
2. **Thẻ khái niệm mới phải có người duyệt** (`reviewed: true`) mới được dùng lúc chạy. Dùng `scripts/draft_cards.py` để AI soạn nháp.
3. **Đổi prompt thì tăng `backend/app/prompts/VERSION`** và ghi một dòng vào `codebase/eval/changelog.md`.
4. Khi đọc báo cáo eval, **xem cột "Dự phòng" trước cột %**: `template:validator` nghĩa là câu trả lời của AI bị loại và hệ thống dùng mẫu đã duyệt.
5. Trước khi push: chạy test + `check_no_data.sh`.

## 9. Việc còn lại

- Soạn thẻ khái niệm **Transformer** (case T21 đang trượt vì thiếu thẻ).
- 2 người chấm độc lập chiều **D6 — dễ hiểu, đúng mức** theo `codebase/eval/rubric.md`.
- Điền số khảo sát và chốt quality bar trong `spec.md`.
- Vòng validation với ≥2 willing user, ghi vào `validation/log.md`.
- Quay video 30 giây (CP3) và video demo dự phòng (CP5).
