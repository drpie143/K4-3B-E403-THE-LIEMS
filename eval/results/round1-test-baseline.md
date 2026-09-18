# Kết quả eval · vòng 1 · tập test · baseline

- Thời điểm: 2026-09-18 03:20
- Provider / model: openai / gpt-4o-mini (explain: gpt-4o-mini, judge: gpt-4o-mini)
- Prompt: p3-v2 · retrieval: local
- Số case: 3 · chi phí ước tính: $0.0005 · p95 độ trễ: 2766 ms

## Tổng hợp

| Chỉ số | Kết quả |
|---|---|
| **Case đạt (D1–D5)** | **1/3 (33%)** |
| D1 Hướng xử lý | 2/3 (67%) |
| D2 Mức (±1) | — |
| D3 Nền trước | — |
| D4 Bám bài giảng | 1/2 (50%) |
| D5 An toàn | 2/3 (67%) |
| Case phải từ chối / không nguồn | 0/1 (0%) |
| Dùng dự phòng | 0/3 |

## Từng case

| Case | Lớp | Mong đợi | Nhận | Mức | D1 | D2 | D3 | D4 | D5 | Đạt | Dự phòng | ms | Lỗi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T01 | 1 | no_source | explain |  | ✗ | — | — | — | ✗ | ❌ |  | 2639 |  |
| T04 | 1 | explain | explain |  | ✓ | — | — | ✗ | ✓ | ❌ |  | 2766 |  |
| T16 | 4 | explain | explain |  | ✓ | — | — | ✓ | ✓ | ✅ |  | 2107 |  |

> Baseline là prompt đơn giản: luôn trả lời, không chọn mức, không thẻ khái niệm, không nguồn.
> Vì vậy nó **hỏng D1/D5 ở mọi case đáng lẽ phải từ chối** — đó chính là điểm so sánh, không phải lỗi chạy.


## Phân tích lỗi (nhóm điền)

| Case | Nguyên nhân (tìm nguồn / chẩn đoán / viết lệch / validator / JSON) | Sửa gì |
|---|---|---|
| | | |
