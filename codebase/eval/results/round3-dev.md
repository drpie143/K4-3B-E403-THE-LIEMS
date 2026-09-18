# Kết quả eval · vòng 3 · tập dev

- Thời điểm: 2026-09-18 03:31
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v3 · retrieval: local
- Số case: 5 · chi phí ước tính: $0.0362 · p95 độ trễ: 8847 ms

## Tổng hợp

| Chỉ số | Kết quả |
|---|---|
| **Case đạt (D1–D5)** | **3/5 (60%)** |
| D1 Hướng xử lý | 3/5 (60%) |
| D2 Mức (±1) | 2/2 (100%) |
| D3 Nền trước | 2/2 (100%) |
| D4 Bám bài giảng | 3/3 (100%) |
| D5 An toàn | 3/5 (60%) |
| Case phải từ chối / không nguồn | 0/2 (0%) |
| Dùng dự phòng | 0/5 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D03 | 1 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 8213 |  |
| D07 | 0 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ |  | 8115 |  |
| D10 | 4 | explain | explain | L1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✅ |  | 1497 |  |
| D11 | 1 | no_source | explain |  | ✗ | — | — | — | ✗ | ❌ |  | 8847 |  |
| D12 | 1 | no_source | explain |  | ✗ | — | — | — | ✗ | ❌ |  | 8268 |  |

## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
