# Lưới đầu vào (User Input Grid) — độ phủ bộ câu thử

Bốn chiều dưới đây là các chiều mà **đổi giá trị thì câu trả lời đúng phải đổi theo**. Mỗi case gắn vào một tổ hợp; ô trống là lỗ hổng độ phủ.

| Chiều | Các giá trị |
|---|---|
| Hồ sơ học viên | Chưa có hồ sơ · Có bộ nhớ cách giải thích · Hồ sơ cũ >14 ngày · Người mới (nền chưa) · Trung bình · Đã vững |
| Tín hiệu | Hỏi lại trong 3 phút · Hỏi lần đầu · Nói chưa hiểu (bấm nút) · Nói chưa hiểu (gõ) · Sau khảo sát (bỏ qua) · Sau khảo sát (có khai) |
| Nguồn | Có trong bài, chưa có thẻ · Có trong thẻ khái niệm · Không phải câu hỏi bài học · Ngoài buổi học |
| Cách hỏi | Bôi đen đoạn · Chứa hiểu lệch · Mơ hồ · Nêu rõ khái niệm · Yêu cầu kiểu trình bày |

## Độ phủ theo từng chiều

| Chiều | Giá trị | Số case | Case |
|---|---|---|---|
| Hồ sơ học viên | Chưa có hồ sơ | 3 | T05, T07, D06 |
| Hồ sơ học viên | Có bộ nhớ cách giải thích | 1 | T10 |
| Hồ sơ học viên | Hồ sơ cũ >14 ngày | 1 | T09 |
| Hồ sơ học viên | Người mới (nền chưa) | 10 | T04, T11, T12, T15, T20, D03, D05, D09, D10, D12 |
| Hồ sơ học viên | Trung bình | 14 | T01, T03, T06, T08, T13, T14, T17, T19, D01, D04, D07, T21, T22, T23 |
| Hồ sơ học viên | Đã vững | 6 | T02, T16, T18, D02, D08, D11 |
| Tín hiệu | Hỏi lại trong 3 phút | 1 | D08 |
| Tín hiệu | Hỏi lần đầu | 24 | T01, T02, T03, T09, T11, T12, T13, T14, T15, T16, T17, T18, T20, D01, D02, D03, D04, D05, D07, D09, D10, T21, T22, D11 |
| Tín hiệu | Nói chưa hiểu (bấm nút) | 1 | T06 |
| Tín hiệu | Nói chưa hiểu (gõ) | 7 | T04, T05, T10, T19, D06, T23, D12 |
| Tín hiệu | Sau khảo sát (bỏ qua) | 1 | T07 |
| Tín hiệu | Sau khảo sát (có khai) | 1 | T08 |
| Nguồn | Có trong bài, chưa có thẻ | 1 | T03 |
| Nguồn | Có trong thẻ khái niệm | 22 | T04, T05, T06, T07, T08, T09, T10, T15, T16, T17, T18, T19, T20, D01, D02, D03, D06, D07, D08, D09, D10, T21 |
| Nguồn | Không phải câu hỏi bài học | 5 | T11, T12, T13, T14, D05 |
| Nguồn | Ngoài buổi học | 7 | T01, T02, D04, T22, T23, D11, D12 |
| Cách hỏi | Bôi đen đoạn | 3 | D06, D10, T22 |
| Cách hỏi | Chứa hiểu lệch | 1 | T17 |
| Cách hỏi | Mơ hồ | 1 | T05 |
| Cách hỏi | Nêu rõ khái niệm | 27 | T01, T02, T03, T04, T06, T07, T08, T09, T10, T11, T12, T13, T14, T16, T18, T20, D01, D02, D03, D04, D05, D07, D08, D09, T23, D11, D12 |
| Cách hỏi | Yêu cầu kiểu trình bày | 3 | T15, T19, T21 |

## Tổ hợp đã phủ (Hồ sơ × Tín hiệu)

| Hồ sơ \\ Tín hiệu | Hỏi lại trong 3 phút | Hỏi lần đầu | Nói chưa hiểu (bấm nút) | Nói chưa hiểu (gõ) | Sau khảo sát (bỏ qua) | Sau khảo sát (có khai) |
|---|---|---|---|---|---|---|
| Chưa có hồ sơ | — | — | — | T05, D06 | T07 | — |
| Có bộ nhớ cách giải thích | — | — | — | T10 | — | — |
| Hồ sơ cũ >14 ngày | — | T09 | — | — | — | — |
| Người mới (nền chưa) | — | T11, T12, T15, T20, D03, D05, D09, D10 | — | T04, D12 | — | — |
| Trung bình | — | T01, T03, T13, T14, T17, D01, D04, D07, T21, T22 | T06 | T19, T23 | — | T08 |
| Đã vững | D08 | T02, T16, T18, D02, D11 | — | — | — | — |

Ô “—” là tổ hợp chưa có case. Nhóm quyết định: ô nào **có thể xảy ra thật** thì thêm case; ô nào vô lý (ví dụ “Chưa có hồ sơ” × “Hồ sơ cũ”) thì ghi lý do bỏ qua vào đây.
