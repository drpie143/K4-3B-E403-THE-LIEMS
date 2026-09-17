# Track A2 — Pain point từ data & bộ câu hỏi khảo sát

> Nguồn: `data/vlearn-pack/chatlog/tutor_turns.csv`, lọc `cohort_hint = K4` (3.097 lượt, 448 học viên, 09/09–15/09).
> Số đếm bằng từ khoá là **số thô** — trước khi đưa vào canvas/spec, mở các mã lượt `T#####` để kiểm lại bằng tay.
> Không commit file CSV vào repo; chỉ dẫn mã lượt và trích ngắn.

---

## Phần 1 · Pain point tìm thấy trong data

| # | Pain point | Bằng chứng (số + mã lượt) | Hướng tính năng A2 |
|---|---|---|---|
| **P1** | **Ôn tập trước quiz / cuối buổi không có cấu trúc** — học viên hỏi lẻ từng thuật ngữ | • 203 lượt / 108 học viên xin tóm tắt, ôn tập (T10291, T10306, T10312, T10315, T10357)<br>• Học viên S1005 ở phần "Ôn toàn bộ câu hỏi" hỏi **36 lượt trong ~27 giờ**, từng câu một: "Readiness là gì", "iteration budget. là cgi"… | Tự tạo bộ ôn tập / flashcard cho từng buổi |
| **P2** | **Tutor xử lý câu hỏi quiz không nhất quán** | • 27 lượt / 13 học viên dán câu quiz hoặc xin đáp án<br>• T10515: tutor từ chối đưa đáp án<br>• T10456: tutor xác nhận "hoàn toàn chính xác"; T10511: tutor đưa luôn thứ tự đúng | Kiểm tra hiểu bài: hỏi ngược thay vì đưa đáp án |
| **P3** | **Giải thích chưa hợp trình độ, học viên phải hỏi đi hỏi lại** | • 1.274 lượt hỏi tiếp trong vòng 3 phút<br>• 62 cặp (học viên, phần học) có ≥10 lượt hỏi<br>• 75 lượt / 37 học viên đòi "giải thích lại / đơn giản hơn": T10317 "giải thích lại dc không hơi khó hiểu", T10536 "Đang không hiểu gì chớt", T10728, T10807<br>• `understanding_level` gần như trống; `validate_understanding` chỉ 11/3.097 lượt | Hỏi 1–2 câu để đo mức hiểu, rồi giải thích đúng trình độ |
| **P4** | **Thuật ngữ mới dồn dập** | • 397 lượt / 165 học viên hỏi "X là gì / khác gì" (T10320, T10322, T10345, T10350, T10356) | Bảng thuật ngữ theo buổi, gắn với slide |
| **P5** | **Học ngoài giờ, không có người hỗ trợ** | • 292 lượt hỏi từ 22h đến 6h<br>• 69 lượt / 47 học viên hỏi về lỗi khi chạy code (T10319, T10336, T10346)<br>• 215 lượt / 102 học viên hỏi "làm sao / bước nào" | Trợ giúp lab ban đêm *(gần A1 hơn)* |
| **P6** | **Giảng viên không biết lớp đang kẹt ở đâu** | • Phần ReAct (D04): **344 lượt / 85 học viên**; Prompt Engineering (D08): 266 / 77; AI-ML-DataLifecycle (D01): 213 / 77<br>• 10 học viên hỏi nhiều nhất chiếm 14,7% số lượt → phải đếm số học viên khác nhau, không đếm số lượt | Bản đồ chỗ khó của lớp cho giảng viên |

**Nhận định ban đầu:** P1 + P3 mạnh nhất (nhiều người gặp, tutor hiện chưa có tính năng tương ứng). Khảo sát để xác định P1, P3 hay P4 là pain đau nhất.

### Cách đếm (để TA kiểm lại)

- Lọc `cohort_hint == "K4"`; với P1–P4 bỏ câu mẫu (`is_preset == True`, 542 lượt).
- Tách tên phần học từ tiền tố câu hỏi `(Đang học phần "…")`; phần còn lại là câu hỏi thật.
- Từ khoá (không phân biệt hoa thường):
  - P1: `tóm tắt | \bôn\b | ôn tập | ôn lại | tổng hợp | review`
  - P2: phần học chứa "Quiz" và câu hỏi chứa `đáp án | chọn | Yêu cầu | Sắp xếp | ghép`
  - P3: `đơn giản | dễ hiểu | giải thích lại | lại lần | ngắn gọn`; "hỏi tiếp" = cùng học viên, cách lượt trước ≤ 3 phút
  - P4: `là gì | khác gì | khác nhau | so sánh`
  - P5: giờ hỏi ≥ 22 hoặc < 6; lỗi: `lỗi | error | bug | không chạy | ko chạy | fail`; bước: `làm sao | làm thế nào | cách | bước`
  - P6: nhóm theo (`lecture_code`, tên phần học), đếm `student` khác nhau

---

## Phần 2 · Bộ câu hỏi khảo sát học viên

**Mục tiêu:** ≥20 học viên ngoài nhóm · ~3 phút/người · ≥50% xác nhận pain.

**Nguyên tắc (Mom Test):**
- Hỏi về **lần gần nhất đã xảy ra**, không hỏi "bạn có muốn tính năng X không".
- **Không giới thiệu ý tưởng** của nhóm trước khi hỏi xong.
- Ghi **nguyên văn** từng câu trả lời.

**Lời mở đầu:** *"Nhóm mình đang tìm hiểu cách các bạn học trên VLearn, không có đúng/sai, bạn cứ kể thật nhé."*

### A. Sàng lọc

1. Tuần này bạn đã dùng tutor trên VLearn chưa?
   ☐ Chưa ☐ 1–2 lần ☐ 3–10 lần ☐ >10 lần
2. Bạn thường mở VLearn lúc nào? *(chọn nhiều)*
   ☐ Trong giờ học ☐ Tối sau buổi học ☐ Khuya sau 22h ☐ Trước quiz

### B. P1 — Ôn tập
*Tính là xác nhận pain nếu người trả lời phải tự ôn không có định hướng, hoặc thấy mất thời gian.*

3. Lần gần nhất bạn ôn bài trước quiz hoặc sau buổi học, bạn đã làm cụ thể những gì?
4. Lần đó mất khoảng bao lâu? Bạn có biết mình nên ôn phần nào trước không?
   ☐ Biết rõ ☐ Đoán đại ☐ Đọc lại toàn bộ slide
5. Có phần nào bạn tưởng đã hiểu nhưng vào quiz mới thấy mình sai không? Đó là phần nào?

### C. P3 — Giải thích chưa hợp trình độ
*Tính là xác nhận pain nếu người trả lời từng phải hỏi lại.*

6. Lần gần nhất tutor giải thích một đoạn, bạn có phải hỏi lại hoặc bấm "giải thích đơn giản hơn" không? Vì sao?
7. Câu trả lời lần đó như thế nào với bạn?
   ☐ Quá dài ☐ Quá sâu ☐ Quá sơ sài ☐ Vừa
8. Sau khi đọc câu trả lời, làm sao bạn biết mình đã hiểu thật?
   ☐ Tự làm lại ☐ Hỏi bạn bè ☐ Không kiểm tra ☐ Làm quiz mới biết

### D. P4 — Thuật ngữ

9. Trong buổi gần nhất, có bao nhiêu thuật ngữ mới bạn phải đi tra? Bạn tra ở đâu?
   ☐ Tutor ☐ ChatGPT / AI khác ☐ Google ☐ Hỏi bạn ☐ Bỏ qua

### E. P2 — Quiz

10. Lần gần nhất bạn kẹt ở một câu quiz, bạn đã làm gì?
    ☐ Hỏi tutor ☐ Hỏi AI khác ☐ Xem lại slide ☐ Đoán
    → Tutor có giúp bạn *hiểu ra* không, hay chỉ cho đáp án?

### F. Xếp hạng & xin willing user

11. Trong các việc sau, việc nào **tốn thời gian hoặc khó chịu nhất** với bạn? *(chọn 1)*
    ☐ Ôn tập trước quiz (P1)
    ☐ Phải hỏi lại vì giải thích chưa hợp (P3)
    ☐ Gặp quá nhiều thuật ngữ mới (P4)
    ☐ Kẹt quiz không biết sai ở đâu (P2)
    ☐ Kẹt lab lúc khuya (P5)
12. Nhóm mình làm thử một công cụ cho vấn đề này, tối 18/9 cần 10 phút dùng thử. Bạn có sẵn lòng không?
    ☐ Có — tên / Discord: ________ ☐ Không

---

## Phần 3 · Phỏng vấn giảng viên / TA (nếu chọn P6)

*Cần ≥3 người, ghi nguyên văn.*

1. Lần gần nhất bạn chuẩn bị phần ôn đầu buổi, bạn dựa vào đâu để chọn nội dung?
2. Bạn biết lớp đang kẹt ở đâu bằng cách nào? Việc đó mất bao lâu?
3. Có lần nào sau buổi học bạn mới phát hiện cả lớp hiểu sai một chỗ không? Chuyện gì đã xảy ra?
4. Hiện bạn có xem lịch sử chat tutor của lớp không? Vì sao có / không?
5. *(Cuối cùng)* Tối 18/9 bạn có 10 phút để thử một công cụ của nhóm không?

---

## Phần 4 · Bảng log khảo sát

Mỗi người một dòng, ghi nguyên văn. Mã người `K01, K02…`, không ghi họ tên (trừ willing user ở cột cuối).

| Mã | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Q7 | Q8 | Q9 | Q10 | Q11 | Xác nhận P1? | Xác nhận P3? | Willing user |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| K01 | | | | | | | | | | | | | | |
| K02 | | | | | | | | | | | | | | |

### Tổng hợp (điền sau khi đủ ≥20 người)

| Pain | Số người xác nhận / tổng | % | Số phiếu ở Q11 | Quote tiêu biểu (nguyên văn) |
|---|---|---|---|---|
| P1 · Ôn tập | /  | | | |
| P2 · Quiz | /  | | | |
| P3 · Giải thích chưa hợp | /  | | | |
| P4 · Thuật ngữ | /  | | | |
| P5 · Lab ban đêm | /  | | | |

**Chốt:** pain được chọn = ______ (vì ______). Hai pain còn lại đưa vào bảng impact làm ứng viên đã loại, kèm lý do.

**Lát cắt nháp (nếu chọn P1 + P3):** *Một học viên · trước quiz · AI hỏi 3 câu kiểm tra các khái niệm đã hỏi trong buổi và quyết định phần nào chưa vững · học viên nhận danh sách 3 phần cần ôn kèm trang slide.*
