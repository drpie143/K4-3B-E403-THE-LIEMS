# Kết quả eval · vòng 5 · tập dev

- Thời điểm: 2026-09-18 07:21
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v4 · retrieval: local
- Số case: 14 · chi phí ước tính: $0.0673 · p95 độ trễ: 10536 ms

## Tổng hợp

| Chỉ số | Kết quả |
|---|---|
| **Case đạt (D1–D5)** | **13/14 (93%)** |
| D1 Hướng xử lý | 13/14 (93%) |
| D2 Mức (±1) | 5/5 (100%) |
| D3 Nền trước | 5/5 (100%) |
| D4 Bám bài giảng | 6/6 (100%) |
| D5 An toàn | 11/11 (100%) |
| Case phải từ chối / không nguồn | 5/5 (100%) |
| Dùng dự phòng | 1/14 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | 0 | explain | explain | L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 8045 |  |
| D02 | 0 | explain | explain | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ | template:validator | 10319 |  |
| D03 | 1 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 9982 |  |
| D04 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D05 | 3 | out_of_scope | out_of_scope |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D06 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1578 |  |
| D07 | 0 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ |  | 10536 |  |
| D08 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1479 |  |
| D09 | 0 | help | help |  | ✓ | — | — | — | ✓ | ✅ |  | 5 |  |
| D10 | 4 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 14543 |  |
| D11 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D12 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D13 | 0 | explain | explain | L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 1753 |  |
| D14 | 2 | explain | survey |  | ✗ | — | — | — | — | ❌ |  | 3202 |  |

## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
