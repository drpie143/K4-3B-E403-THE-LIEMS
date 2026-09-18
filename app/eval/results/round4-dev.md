# Kết quả eval · vòng 4 · tập dev

- Thời điểm: 2026-09-18 03:35
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v3 · retrieval: local
- Số case: 12 · chi phí ước tính: $0.0418 · p95 độ trễ: 6895 ms

## Tổng hợp

| Chỉ số | Kết quả |
|---|---|
| **Case đạt (D1–D5)** | **12/12 (100%)** |
| D1 Hướng xử lý | 12/12 (100%) |
| D2 Mức (±1) | 4/4 (100%) |
| D3 Nền trước | 4/4 (100%) |
| D4 Bám bài giảng | 5/5 (100%) |
| D5 An toàn | 10/10 (100%) |
| Case phải từ chối / không nguồn | 5/5 (100%) |
| Dùng dự phòng | 0/12 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | 0 | explain | explain | L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 6895 |  |
| D02 | 0 | explain | explain | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 7792 |  |
| D03 | 1 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 1588 |  |
| D04 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D05 | 3 | out_of_scope | out_of_scope |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D06 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1452 |  |
| D07 | 0 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ |  | 1442 |  |
| D08 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1372 |  |
| D09 | 0 | help | help |  | ✓ | — | — | — | ✓ | ✅ |  | 7 |  |
| D10 | 4 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 1723 |  |
| D11 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 0 |  |
| D12 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 0 |  |

## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
