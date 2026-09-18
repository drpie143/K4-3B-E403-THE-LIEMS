# P3 · Chọn mức tự động hoá theo cost-of-error

> Track A2 · Tính năng "Kiểm tra hiểu và giải thích lại theo mức" · buổi Foundation (transformer, attention)
> Căn cứ: `02-guide.md` §2.3 (bảng Augment / Conditional / Automate) và PAIR 1.2–1.3.
> Dùng để điền `spec.md` §4 dòng *Automation* và canvas CP1 dòng 6.

---

## 1. Kết luận

**Chọn mức Conditional.**

AI tự làm khi có căn cứ trong transcript và đủ chắc về chỗ học viên đang vướng. Khi không có căn cứ, không chắc, hoặc học viên đã 2 lần báo vẫn chưa hiểu, AI dừng lại và chuyển học viên sang TA.

---

## 2. Cách suy luận: đi qua từng câu hỏi của §2.3

### Câu 1 · Sai thì ai chịu, chịu gì?

| Nếu AI sai ở… | Ai chịu | Hậu quả |
|---|---|---|
| Hỏi lại một câu không trúng | Học viên | Mất vài giây, hơi phiền |
| Xác định sai chỗ vướng (vd học viên cần ví dụ nhưng AI giảng lại lý thuyết nền) | Học viên | Vẫn chưa hiểu, phải bấm 👎 thêm một lần |
| **Giải thích lại sai kiến thức** (vd nói sai cách attention cộng trọng số) | Học viên, rồi đến giảng viên | **Học sai kiến thức nền của cả khoá**, làm sai quiz và lab; giảng viên phải sửa lại sau |
| Kết luận "bạn yếu phần X" | Học viên | Mất tự tin, mất niềm tin vào tính năng |

### Câu 2 · Người dùng có tự thấy và tự sửa được không?

**Không**, ở đúng chỗ đắt nhất. Học viên dùng tính năng này **vì đang chưa hiểu**, nên họ không đủ kiến thức để nhận ra lời giải thích lại bị sai. Lỗi sai kiến thức sẽ trôi qua mà không ai phát hiện.

→ **Loại Automate.** §2.3 chỉ cho Automate khi "sai thì rẻ, user tự thấy và sửa được". P3 không thoả điều kiện thứ hai.

### Câu 3 · Có thể để người duyệt từng lượt không?

**Không thực tế.**
- K4 có 3.097 lượt hỏi tutor chỉ trong khoảng 1 tuần (09/09–15/09).
- Học viên cần câu trả lời ngay trong lúc học, kể cả lúc khuya (292 lượt từ 22h đến 6h).
- Nếu giảng viên phải duyệt từng lời giải thích, học viên phải chờ, tức là mất đúng giá trị mà tính năng muốn đem lại.

→ **Loại Augment cho toàn bộ luồng.** Augment hợp với quiz AI sinh (giảng viên duyệt một lần, dùng cho cả lớp), không hợp với hỗ trợ theo thời gian thực cho từng học viên.

### Câu 4 · Đa số case có lành, và có tách được số ít case hiểm không?

**Có.**
- **Case lành chiếm đa số:** học viên hỏi về một đoạn slide có sẵn trong transcript-04/06 (T10728, T10480, T10508…). AI tìm được đoạn nguồn và giải thích dựa trên đoạn đó.
- **Case hiểm là số ít và nhận ra được bằng tín hiệu cụ thể:**
  - Không tìm được đoạn nguồn khớp.
  - Độ chắc khi xác định chỗ vướng thấp.
  - Câu trả lời mơ hồ ("Đang không hiểu gì chớt", T10536).
  - Câu hỏi ngoài phạm vi (T10709 "viết một blog…"), hoặc prompt injection.
  - Học viên đã bấm 👎 hai lần.

→ **Đúng mô tả của Conditional:** "AI tự làm case chắc, chuyển người case mơ hồ".

---

## 3. Mức tự động của từng bước trong luồng

Cả tính năng ở mức Conditional, nhưng từng bước có mức khác nhau tuỳ cost-of-error:

| Bước | Mức | Lý do theo cost-of-error |
|---|---|---|
| Hỏi lại 1 câu làm rõ | **Automate** | Sai thì rẻ: học viên thấy ngay câu hỏi không liên quan và bấm **Bỏ qua** |
| Xác định chỗ vướng | **Conditional** | Sai thì tốn một vòng hỏi lại. Độ chắc thấp thì dùng mặc định "bản ngắn gọn", không đoán tiếp |
| Giải thích lại | **Conditional** | Sai thì đắt (học sai kiến thức), học viên không tự phát hiện được. Chỉ trả lời khi có đoạn nguồn và qua bước kiểm tra output; không có nguồn thì nói "chưa có trong bài" |
| Sau 2 lần 👎 | **Chuyển người** | AI đã thử 2 cách mà không hiệu quả, lặp tiếp thì học viên mất thời gian. Gợi ý hỏi TA hoặc xem đoạn video |
| Đánh giá năng lực học viên ("bạn yếu phần X") | **Không làm** | Sai thì đắt (mất tự tin, dán nhãn sai). Chỉ ghi log `gap_type` ẩn danh, không hiển thị kết luận |

---

## 4. Ba câu PAIR 1.3 (ghi vào spec)

- **AI luôn phải** dựa lời giải thích lại vào một đoạn transcript cụ thể và hiện đoạn đó cho học viên.
- **AI không được** giải thích một nội dung không có trong bài giảng, hoặc kết luận về năng lực của học viên, **kể cả khi học viên vô tình yêu cầu**.
- **Nếu AI xác định chỗ vướng chưa trúng**, học viên sẵn lòng bấm 👎 hoặc Bỏ qua một lần, **miễn là** lần sau AI đổi cách giải thích và không bắt học viên trả lời thêm câu hỏi.

---

## 5. Đoạn điền sẵn cho `spec.md` §4

```markdown
- Automation: [ ] augment [x] conditional [ ] automate — lý do theo cost-of-error:
  Sai lời giải thích lại → học viên học sai kiến thức nền, mang lỗi vào quiz/lab; và học viên
  đang chưa hiểu nên KHÔNG tự phát hiện được lỗi → loại Automate. Duyệt từng lượt bởi giảng
  viên làm học viên phải chờ trong lúc học (3.097 lượt/tuần ở K4, 292 lượt sau 22h) → loại
  Augment. Đa số câu hỏi nằm trong transcript buổi Foundation (case lành), số ít hiểm nhận ra
  được (không có đoạn nguồn, độ chắc thấp, ngoài phạm vi, 2 lần 👎) → Conditional:
  AI tự hỏi lại (≤1 câu, bỏ qua được) và giải thích lại khi có nguồn + qua kiểm tra output;
  không có nguồn → nói "chưa có trong bài"; 2 lần 👎 → chuyển TA.
  Không tự kết luận năng lực học viên.
```

## 6. Đoạn điền sẵn cho canvas CP1 dòng 6

> **Conditional.** *AI tự làm:* hỏi lại ≤1 câu (bỏ qua được), xác định chỗ vướng, giải thích lại kèm đoạn transcript. *AI không làm:* giải thích khi không có nguồn (nói "chưa có trong bài"), kết luận năng lực học viên; sau 2 lần 👎 thì chuyển TA. *Lý do:* giải thích sai khiến học viên học sai kiến thức nền, và học viên đang chưa hiểu nên không tự phát hiện được lỗi. Không thể để giảng viên duyệt từng lượt vì học viên cần câu trả lời ngay khi học. **Willing users:** `[Tên 1]`, `[Tên 2]`, `[Tên 3]`.

---

## 7. Kiểm lại (TA hay hỏi ở CP4)

- **Hỏi:** "Sao không Automate luôn cho nhanh?"
  **Đáp:** Học viên đang chưa hiểu thì không phát hiện được lời giải thích sai, nên sai kiến thức sẽ trôi qua mà không ai sửa.
- **Hỏi:** "Sao không Augment cho an toàn?"
  **Đáp:** Cần câu trả lời ngay trong lúc học, kể cả lúc khuya; duyệt từng lượt thì mất giá trị. Nhóm thay việc duyệt bằng căn cứ bắt buộc, bước kiểm tra output và đường chuyển TA.
- **Hỏi:** "Case nào chuyển người?"
  **Đáp:** Không có đoạn nguồn · độ chắc thấp sau khi đã hỏi lại · ngoài phạm vi · 2 lần 👎.
- **Hỏi:** "Đo thế nào?"
  **Đáp:** Trong bộ câu thử có case không có nguồn và case ngoài phạm vi. Chỉ tính đạt khi AI chuyển hoặc từ chối đúng, không bịa.
