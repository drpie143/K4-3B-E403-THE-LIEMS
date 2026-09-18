# Backend · Trợ giảng AI giải thích lại đúng mức (P3)

Hiện thực tài liệu `ĐỌC ĐỀ/P3-backend-ha-tang-agent.md`: workflow cố định do code điều phối, LLM làm 3 bước có cấu trúc (chẩn đoán → viết giải thích → chấm), mọi hành động có hậu quả do code làm.

## Chạy

### Windows (PowerShell)

Chạy các lệnh sau từ thư mục gốc repository. Cần đứng trong `codebase/backend` khi import `app`:

```powershell
cd codebase\backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Mở `http://localhost:8000/`. Nếu đã có `.venv` ở thư mục gốc repository, vẫn cần `cd codebase\backend` trước khi chạy `uvicorn`; hoặc dùng môi trường `.venv` riêng trong backend như trên.

### Chạy bằng API thật trên Windows

1. Thu hồi API key đã từng bị lộ và tạo key mới trên trang quản lý của provider. Không gửi key vào Git, chat hoặc issue.
2. Từ thư mục gốc repository, tạo file cấu hình local:

```powershell
cd codebase\backend
Copy-Item .env.example .env -ErrorAction SilentlyContinue
notepad .env
```

Trong `.env`, chọn **một** provider và điền key tương ứng:

```dotenv
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=điền_key_mới_vào_đây

# Hoặc Gemini
# LLM_PROVIDER=gemini
# LLM_MODEL=gemini-2.5-flash
# GEMINI_API_KEY=điền_key_mới_vào_đây

# Hoặc Claude
# LLM_PROVIDER=claude
# LLM_MODEL=claude-opus-5
# ANTHROPIC_API_KEY=điền_key_mới_vào_đây
```

3. Kiểm tra một lượt gọi API thật trước khi mở server. Lệnh dưới đây tắt bước judge để giảm chi phí; thêm `--full` để chạy đủ workflow 3 lần gọi LLM:

```powershell
..\..\.venv\Scripts\python.exe ..\scripts\smoke_llm.py
..\..\.venv\Scripts\python.exe ..\scripts\smoke_llm.py --full
```

4. Nếu smoke test thành công, chạy ứng dụng:

```powershell
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Mở `http://localhost:8000/`. Kiểm tra provider/model tại `http://localhost:8000/health`. Nếu key sai, model không tồn tại hoặc hết hạn mức, backend có thể dùng câu trả lời dự phòng; xem kết quả smoke test và log để biết lỗi.

### Linux / macOS

```bash
cd codebase/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # điền OPENAI_API_KEY (hoặc để LLM_PROVIDER=fake để chạy không tốn tiền)

# (tuỳ chọn) dữ liệu nguyên văn trên máy — không commit
python3 ../scripts/build_local_data.py

.venv/bin/uvicorn app.main:app --reload --port 8000
# mở http://localhost:8000/  → mock chạy ở chế độ live (gọi backend)

.venv/bin/python -m pytest -q    # 40 test, dùng FakeLLM, không cần key, không cần data pack

# Thử 1 lượt với provider thật trước khi chạy cả bộ (in token, độ trễ, và lỗi nếu có)
LLM_PROVIDER=gemini LLM_MODEL=gemini-2.5-flash GEMINI_API_KEY=... .venv/bin/python ../scripts/smoke_llm.py
```

**Windows (PowerShell):** đổi `.venv/bin/xxx` thành `.venv\Scripts\xxx.exe`, ví dụ
`.venv\Scripts\uvicorn.exe app.main:app --port 8000` và `.venv\Scripts\python.exe -m pytest -q`.
Đặt biến môi trường cho một lệnh: `$env:LLM_PROVIDER="fake"; .venv\Scripts\python.exe ...`

Không có `data/chunks.local.json` → backend chạy **chế độ tóm tắt** (dùng tóm tắt trong `cards/_sources.yaml`); `/health` báo `retrieval_mode`.

## Cấu trúc

```text
backend/
├── app/
│   ├── main.py            # FastAPI: 16 route (§5) + phục vụ mock tại /app
│   ├── config.py          # đọc .env / biến môi trường
│   ├── schemas.py         # LLMDecision/LLMAnswer/LLMJudge (structured output) + model HTTP
│   ├── orchestrator.py    # luồng §3: guard → signals → retrieval → rules → LLM#1 → policy → LLM#2 → validator → LLM#3
│   ├── signals.py         # tín hiệu từ câu hỏi (port detect() của mock)
│   ├── guard.py           # injection / ngoài phạm vi / thuật ngữ ngoài bài / nhãn năng lực
│   ├── retrieval.py       # BM25 tự cài, lọc theo buổi, ưu tiên nguồn của thẻ
│   ├── cards.py           # nạp + kiểm tra thẻ YAML (chỉ thẻ reviewed: true)
│   ├── policy.py          # rule_decide (dự phòng) + enforce (luật cứng ép lên quyết định của LLM)
│   ├── templates.py       # mẫu trả lời đã duyệt theo 5 mức
│   ├── fidelity.py        # validator độ bám bài giảng + gộp LLM chấm
│   ├── profile_store.py   # SQLite: hồ sơ, bộ nhớ dài hạn (§7.4), sự kiện + hoàn tác, phiên
│   ├── checks.py · handoff.py · cache.py · tracing.py · prompts.py · textutil.py
│   ├── llm/               # base (giao diện) · fake · openai_client · claude · gemini
│   └── prompts/           # system · diagnose · explain · judge · baseline · VERSION
├── cards/                 # _sources.yaml + 5 thẻ khái niệm (commit: chỉ diễn giải + mã đoạn)
├── personas.yaml          # 6 hồ sơ giả (có 2 hồ sơ minh hoạ bộ nhớ dài hạn)
├── tests/                 # pytest
├── requirements.txt · .env.example
└── (không commit) .venv/ · p3.db · traces/ · .cache/ · cards/drafts/
```

## API

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/health` | provider, model, chế độ tìm kiếm, thẻ, phiên bản prompt |
| GET | `/api/personas` | danh sách hồ sơ giả |
| POST | `/api/chat` | câu hỏi (`action=ask`) hoặc "Mình chưa hiểu" (`action=confused`, `concept_hint`) |
| POST | `/api/survey` | gửi / bỏ qua khảo sát → giải thích lại |
| POST | `/api/adjust` | `easier` · `deeper` · `shorter` · `example` |
| POST | `/api/feedback` | 👍 → câu kiểm tra · 👎 (`hard` / `long` / `wrong` / không lý do) → giải thích lại hoặc chuyển TA |
| GET / POST | `/api/check` | lấy câu kiểm tra / nộp đáp án |
| POST | `/api/handoff` | soạn câu hỏi cho TA |
| GET · PUT · DELETE | `/api/profile` | Sổ tay: xem, sửa mức / bật-tắt ghi nhớ / kiểu ưa thích, xoá |
| DELETE | `/api/profile/strategy` | xoá một "cách giải thích" đã nhớ |
| POST | `/api/profile/undo` · `/api/profile/reset` | hoàn tác sự kiện · khôi phục hồ sơ mẫu |
| POST | `/api/session/reset` | xoá trạng thái phiên |
| GET | `/api/sources/{id}` | đoạn gốc (nguyên văn nếu có file local, không thì tóm tắt) |

Tài liệu tương tác: http://localhost:8000/docs

## Chế độ vận hành

| Biến | Tác dụng |
|---|---|
| `LLM_PROVIDER=fake` | Không gọi mạng; LLM giả trả đúng quyết định/mẫu của luật (dùng để test, demo không tốn tiền) |
| `LLM_PROVIDER=gemini` + `LLM_MODEL=gemini-2.5-flash` | Free tier của Google AI Studio — thử miễn phí trước khi dùng key trả phí. Free tier có thể dùng dữ liệu để huấn luyện nên chỉ gửi đoạn bài giảng (đã giới hạn 3 đoạn × 900 ký tự) |
| `LLM_PROVIDER=openai` + `LLM_MODEL=gpt-4o-mini` | Khuyến nghị cho hackathon (~0,002 USD/lượt) |
| `LLM_MODEL_EXPLAIN=gpt-4.1-mini` | Dùng model tốt hơn chỉ cho bước viết giải thích |
| `USE_JUDGE=0` | Bỏ bước LLM chấm, chỉ dùng validator luật (nhanh, rẻ hơn) |
| `REPLAY=1` | Không gọi LLM: dùng câu trả lời đã cache hoặc mẫu đã duyệt — dùng khi quay video dự phòng / mạng lỗi |

## An toàn dữ liệu

- Key chỉ ở `.env` của backend; frontend không gọi provider.
- Mỗi lượt gửi LLM tối đa 3 đoạn × 900 ký tự; không gửi chatlog.
- `traces/*.jsonl` chỉ ghi độ dài + hash câu hỏi (trừ khi `TRACE_TEXT=1`).
- `traces/prompts/<request_id>.jsonl` ghi **prompt đầu vào + phản hồi thô** của từng lời gọi (phục vụ xác minh kỹ thuật ở CP3–CP5). Tắt bằng `TRACE_PROMPTS=0`. Thư mục `traces/` đã bị `.gitignore` chặn.
- Muốn có trace **trong repo** cho TA xem: `python ../scripts/export_trace_sample.py --limit 2` → `codebase/eval/traces-sample/*.json` (đã thay nguyên văn đoạn bài giảng bằng mã đoạn).
- Trước khi commit: `bash ../scripts/check_no_data.sh`.
