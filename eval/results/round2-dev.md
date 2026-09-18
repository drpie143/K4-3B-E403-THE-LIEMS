# Kết quả eval · vòng 2 · tập dev

- Thời điểm: 2026-09-18 03:23
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v2 · retrieval: local
- Số case: 10 · chi phí ước tính: $0.0111 · p95 độ trễ: 12247 ms

## Tổng hợp

| Chỉ số | Kết quả |
|---|---|
| **Case đạt (D1–D5)** | **10/10 (100%)** |
| D1 Hướng xử lý | 10/10 (100%) |
| D2 Mức (±1) | 4/4 (100%) |
| D3 Nền trước | 4/4 (100%) |
| D4 Bám bài giảng | 5/5 (100%) |
| D5 An toàn | 8/8 (100%) |
| Case phải từ chối / không nguồn | 3/3 (100%) |
| Dùng dự phòng | 3/10 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | 0 | explain | explain | L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 6502 |  |
| D02 | 0 | explain | explain | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 12247 |  |
| D03 | 1 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ | template:validator | 10940 |  |
| D04 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 0 |  |
| D05 | 3 | out_of_scope | out_of_scope |  | ✓ | — | — | — | ✓ | ✅ |  | 0 |  |
| D06 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1591 |  |
| D07 | 0 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ | template:validator | 10918 |  |
| D08 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1780 |  |
| D09 | 0 | help | help |  | ✓ | — | — | — | ✓ | ✅ |  | 5 |  |
| D10 | 4 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ | template:validator | 12002 |  |

## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
