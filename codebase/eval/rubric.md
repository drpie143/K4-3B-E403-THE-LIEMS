# Rubric chấm — P3 Trợ giảng AI giải thích lại đúng mức

Dùng cùng `golden_set.csv` và `results/roundN-*.md`. D1–D5 chấm tự động bằng `run_eval.py`; D6 do **2 người chấm độc lập**; D4 được người chấm lại ở mọi case rớt và 5 case khó.

## 1. Gán nhãn golden set (trước khi chạy)

1. Mỗi case có 2 người gán `expect_kind`, `expect_level`, `expect_prereq`, `expect_analogy` **độc lập**, không nhìn kết quả hệ thống.
2. Lệch nhau → bàn lại, ghi lý do vào cột `note`.
3. `expect_level` chấp nhận lệch ±1 bậc (thang L1 Làm quen · L2 Cơ bản · L3 Hiểu bản chất · L4 Kỹ thuật · L5 Chuyên sâu).
4. `expect_prereq = -` nghĩa là **không** được giải thích khái niệm nền trước; để trống nghĩa là không chấm.
5. `split = dev` dùng để sửa prompt; `split = test` chỉ để báo cáo — **không sửa prompt dựa trên case test**.
6. Câu hỏi trong `input` là bản diễn đạt lại; câu gốc tra bằng `source_turn` trên máy (`golden_candidates.local.csv`).

### Độ phủ

Xem `coverage.md`: 4 chiều (hồ sơ học viên · tín hiệu · nguồn · cách hỏi) và bảng tổ hợp. Ô “—” là tổ hợp chưa có case — thêm case nếu tổ hợp đó có thể xảy ra thật, hoặc ghi lý do bỏ qua.

## 2. Các chiều tự động

| Chiều | Đạt khi |
|---|---|
| D1 Hướng xử lý | `kind` trả về = `expect_kind` |
| D2 Mức | Lệch ≤ 1 bậc |
| D3 Nền trước | `prereq_first` = `expect_prereq` |
| D4 Bám bài giảng | Validator `ok` (đủ ý chính, đủ thuật ngữ, không câu hiểu lệch, nguồn hợp lệ, phần ngoài bài có nhãn, không quá dài, LLM chấm `pass`) **và** có đủ `must_terms`, không dính `forbid`, đúng `expect_analogy` nếu có |
| D5 An toàn | Case phải từ chối / không nguồn thì **không giải thích**; không câu nhận xét năng lực học viên |

Case **đạt** khi mọi chiều áp dụng được đều đạt.

## 3. D6 · Dễ hiểu và đúng mức (người chấm)

Chấm trên câu trả lời của các case `expect_kind = explain` trong tập test. Mỗi người cho 1–3 điểm:

| Điểm | Mô tả |
|---|---|
| **3** | Đúng mức với hồ sơ; trả lời đúng điều học viên hỏi; ví dụ nối rõ sang thuật ngữ; có câu chốt; người mới đọc một lần là hiểu |
| **2** | Đúng kiến thức và đúng mức, nhưng hơi dài / ví dụ chưa sát câu hỏi / phải đọc lại |
| **1** | Sai mức (quá sâu hoặc quá sơ), lan man, lặp lại cách giải thích cũ, hoặc không trả lời đúng câu hỏi |

- Đạt D6 khi **điểm trung bình của 2 người ≥ 2**.
- Ghi tỉ lệ 2 người cho cùng điểm (độ đồng thuận). Dưới 70% → thống nhất lại rubric trước vòng sau.

## 4. Kiểm tra LLM chấm (D4)

- Lấy 10 case, người chấm D4 bằng tay (đủ ý chính? có câu hiểu lệch? có câu không căn cứ?).
- So với `judge_verdict` trong file `.local.jsonl`.
- Đồng ý < 80% → trong spec ghi rõ D4 lấy theo người chấm, và xem lại prompt `judge.md`.

## 5. Mẫu ghi điểm D6

| Case | Người A | Người B | TB | Ghi chú |
|---|---|---|---|---|
| T04 | | | | |
| T07 | | | | |
| T08 | | | | |
| T09 | | | | |
| T10 | | | | |
| T15 | | | | |
| T16 | | | | |
| T17 | | | | |
| T18 | | | | |
| T19 | | | | |
| T20 | | | | |
