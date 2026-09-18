# Backend · Trợ giảng AI giải thích lại đúng mức (P3)

Hiện thực tài liệu `ĐỌC ĐỀ/P3-backend-ha-tang-agent.md`: workflow cố định do code điều phối, LLM làm 3 bước có cấu trúc (chẩn đoán → viết giải thích → chấm), mọi hành động có hậu quả do code làm.

## Chạy

```bash
cd codebase/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # điền OPENAI_API_KEY (hoặc để LLM_PROVIDER=fake để chạy không tốn tiền)

# (tuỳ chọn) dữ liệu nguyên văn trên máy — không commit
python3 ../scripts/build_local_data.py

.venv/bin/uvicorn app.main:app --reload --port 8000
# mở http://localhost:8000/  → mock chạy ở chế độ live (gọi backend)

.venv/bin/python -m pytest -q    # 66 test, dùng FakeLLM, không cần key, không cần data pack

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
│   ├── cards.py           # nạp + kiểm tra thẻ YAML (chỉ thẻ reviewed: true) + gộp danh mục 6 buổi
│   ├── cardgen.py         # sinh mẫu trả lời 5 mức cho thẻ "nhẹ" (auto_template: true)
│   ├── lessons.py         # 6 buổi học: danh mục + thân bài (local → Supabase → tóm tắt)
│   ├── auth.py            # tài khoản: đăng ký / đăng nhập / phiên (mật khẩu băm PBKDF2)
│   ├── memory.py          # bộ nhớ dài hạn: ghi trễ, nén, nạp lại từ Supabase
│   ├── policy.py          # rule_decide (dự phòng) + enforce (luật cứng ép lên quyết định của LLM)
│   ├── templates.py       # mẫu trả lời đã duyệt theo 5 mức
│   ├── fidelity.py        # validator độ bám bài giảng + gộp LLM chấm
│   ├── profile_store.py   # SQLite: hồ sơ, bộ nhớ dài hạn (§7.4), sự kiện + hoàn tác, phiên
│   ├── checks.py · handoff.py · cache.py · tracing.py · prompts.py · textutil.py
│   ├── llm/               # base (giao diện) · fake · openai_client · claude · gemini
│   └── prompts/           # system · diagnose · explain · judge · baseline · VERSION
├── cards/                 # _sources.yaml + 17 thẻ khái niệm cho 6 buổi (commit: chỉ diễn giải + mã đoạn)
├── lessons.yaml           # danh mục 6 buổi: tên buổi, mục, thẻ khái niệm, transcript tương ứng
├── supabase_schema.sql    # toàn bộ bảng + hàm nén bộ nhớ, dán vào SQL Editor của Supabase
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
| GET | `/api/lessons` | danh mục **6 buổi học** (tên buổi, mục, thẻ khái niệm, đang đọc dữ liệu từ đâu) |
| GET | `/api/lessons/{id}` | thân bài một buổi (`?section=s3` để lấy một mục) — đọc từ `chunks.local.json` hoặc Supabase |
| POST | `/api/auth/register` · `/api/auth/login` | tạo tài khoản · đăng nhập (trả về token Bearer) |
| GET · PUT · DELETE | `/api/auth/me` | xem · đổi tên hiển thị/mật khẩu · xoá tài khoản kèm toàn bộ hồ sơ |
| POST | `/api/auth/logout` | đăng xuất (đẩy nốt bộ nhớ đang chờ lên Supabase) |
| POST | `/api/memory/flush` | đẩy ngay hàng đợi bộ nhớ dài hạn lên Supabase |

Khi request có `Authorization: Bearer <token>`, backend **bỏ qua `user_id` gửi lên** và gắn mọi thao tác vào
tài khoản đang đăng nhập — không ai đọc/ghi được hồ sơ của người khác.

Tài liệu tương tác: http://localhost:8000/docs

## Chế độ vận hành

| Biến | Tác dụng |
|---|---|
| `LLM_PROVIDER=fake` | Không gọi mạng; LLM giả trả đúng quyết định/mẫu của luật (dùng để test, demo không tốn tiền) |
| `LLM_PROVIDER=gemini` + `LLM_MODEL=gemini-2.5-flash` | Free tier của Google AI Studio — thử miễn phí trước khi dùng key trả phí. Free tier có thể dùng dữ liệu để huấn luyện nên chỉ gửi đoạn bài giảng (đã giới hạn 3 đoạn × 900 ký tự) |
| `LLM_PROVIDER=openai` + `LLM_MODEL=gpt-4o-mini` | Khuyến nghị cho hackathon (~0,002 USD/lượt) |
| `LLM_MODEL_EXPLAIN=gpt-4.1-mini` | Dùng model tốt hơn chỉ cho bước viết giải thích |
| `USE_JUDGE=0` | Bỏ bước LLM chấm, chỉ dùng validator luật (nhanh, rẻ hơn) |
| `SUPABASE_URL` + `SUPABASE_KEY` | Bật lưu hồ sơ, bộ nhớ dài hạn, tài khoản và bài giảng trên Supabase (dùng service_role key, chỉ để ở backend) |
| `MEMORY_FLUSH_EVERY=3` | Cứ 3 lượt hỏi mới đẩy bộ nhớ lên Supabase (ghi trễ, đỡ tốn request) |
| `MEMORY_COMPACT_EVERY=10` · `MEMORY_MAX_STRATEGIES=6` · `MEMORY_MAX_EVENTS=50` | Nén bộ nhớ dài hạn để không phình theo số lượt |
| `REPLAY=1` | Không gọi LLM: dùng câu trả lời đã cache hoặc mẫu đã duyệt — dùng khi quay video dự phòng / mạng lỗi |

## An toàn dữ liệu

- Key chỉ ở `.env` của backend; frontend không gọi provider.
- Mỗi lượt gửi LLM tối đa 3 đoạn × 900 ký tự; không gửi chatlog.
- `traces/*.jsonl` chỉ ghi độ dài + hash câu hỏi (trừ khi `TRACE_TEXT=1`).
- `traces/prompts/<request_id>.jsonl` ghi **prompt đầu vào + phản hồi thô** của từng lời gọi (phục vụ xác minh kỹ thuật ở CP3–CP5). Tắt bằng `TRACE_PROMPTS=0`. Thư mục `traces/` đã bị `.gitignore` chặn.
- Muốn có trace **trong repo** cho TA xem: `python ../scripts/export_trace_sample.py --limit 2` → `codebase/eval/traces-sample/*.json` (đã thay nguyên văn đoạn bài giảng bằng mã đoạn).
- Trước khi commit: `bash ../scripts/check_no_data.sh`.
