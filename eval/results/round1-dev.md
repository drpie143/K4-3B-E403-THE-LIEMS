# Kết quả eval · vòng 1 · tập dev

- Thời điểm: 2026-09-17 18:22
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v1 · retrieval: local
- Số case: 10 · chi phí ước tính: $0.0109 · p95 độ trễ: 13996 ms

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
| Dùng dự phòng | 2/10 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | 0 | explain | explain | L3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 10118 |  |
| D02 | 0 | explain | explain | L4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 13996 |  |
| D03 | 1 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ | template:validator | 13981 |  |
| D04 | 1 | no_source | no_source |  | ✓ | — | — | — | ✓ | ✅ |  | 2 |  |
| D05 | 3 | out_of_scope | out_of_scope |  | ✓ | — | — | — | ✓ | ✅ |  | 1 |  |
| D06 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 2607 |  |
| D07 | 0 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ |  | 6147 |  |
| D08 | 2 | survey | survey |  | ✓ | — | — | — | — | ✅ |  | 1490 |  |
| D09 | 0 | help | help |  | ✓ | — | — | — | ✓ | ✅ |  | 5 |  |
| D10 | 4 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ | template:validator | 10651 |  |

## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
