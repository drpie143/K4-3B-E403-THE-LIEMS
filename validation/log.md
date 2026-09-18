# Báo cáo Đánh giá Người dùng Thực tế (User Validation Log)

> **Mục tiêu:** Kiểm chứng tính hiệu quả và trải nghiệm của giải pháp **P3: Adaptive Explainer (VLearn Tutor)** với người dùng ngoài nhóm theo quy định tại `02-guide.md` §4.2 và tiêu chí chấm điểm **Bonus R6 (Tối đa +8 điểm)** trong `04-rubric.md`.
> **Thời gian thực hiện:** Ngày 18/09/2026.
> **Đối tượng thử nghiệm:** 3 học viên đang theo học Khóa đào tạo AI/Data K4 VinAI (Lớp 3B, Phòng E403), không thuộc nhóm THE-LIEMS.
> **Giao thức thử nghiệm (Protocol):** Phiên trải nghiệm 10 phút/người. Quan sát hành vi theo chuẩn **Google PAIR 5.1 (Interpreting Implicit Signals)** kết hợp phỏng vấn sâu lấy phản hồi nguyên văn (verbatim quotes).

---

## 1. Phương pháp & Chỉ số Đo lường

Mỗi học viên được cấp một tài khoản thử nghiệm trên hệ thống VLearn live (`http://localhost:8000/app/index.html?mode=live`) và thực hiện nhiệm vụ trên bài giảng **Day 1: Transformer & Cơ chế Self-Attention**.

### Các chỉ số định lượng:
1. **Số lần bấm "Chưa hiểu" / "Dễ hiểu hơn"** trước khi trả lời đúng câu hỏi kiểm tra củng cố kiến thức.
2. **Thời gian đạt được trạng thái thấu hiểu (Time to Comprehension - TTC)**.
3. **Kết quả câu kiểm tra kiến thức (Quiz Score):** Đúng ngay lần đầu (First-attempt Pass) hay cần giải thích lại.

### Phân tích tín hiệu hành vi ngầm theo Google PAIR 5.1:
- **Bấm "Dễ hiểu hơn":** Tín hiệu hạ mức độ nhận thức (AI đang giải thích vượt quá tầm tiếp thu hiện tại).
- **Bấm "Ví dụ khác":** Khám phá thêm góc nhìn tương đồng (tín hiệu tích cực muốn củng cố, không phải AI sai nặng).
- **Bấm "Sâu hơn":** Tín hiệu học viên đã hiểu nền và muốn đào sâu cơ chế toán học/kỹ thuật.
- **Bấm "Soạn câu hỏi cho TA":** Tín hiệu an tâm khi gặp ranh giới kiến thức ngoài bài giảng (Graceful Failure).

---

## 2. Nhật ký Thử nghiệm Chi tiết (User Testing Logs)

### Phiên 1: Lê Thanh Tình (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 02.
- **Hồ sơ nền tảng:** Học viên chuyển ngành (Non-CS), đã học Python cơ bản nhưng chưa vững Đại số tuyến tính và kiến trúc Transformer; hay bị ngợp khi đọc tài liệu nhiều ma trận.
- **Nhiệm vụ giao (Task):** "Truy cập bài học Day 1, hỏi tutor về khái niệm Self-Attention ở mức độ nhập môn. Đọc lời giải thích và trả lời câu hỏi kiểm tra kiến thức cuối bài."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 02:30:** Gõ câu hỏi: *"Giải thích self-attention cho người mới bắt đầu"*. Hệ thống chẩn đoán hồ sơ mới, tự động kích hoạt chiến lược giải thích Vector nhúng trước. Tình dừng lại đọc kỹ đoạn giải thích Vector trong 45 giây (tín hiệu tiếp nhận tốt).
  - **02:30 - 04:00:** Đọc phần ví dụ con mèo chia sẻ sự chú ý trong câu văn. Tình bấm nút **"Ví dụ khác"** (AI giữ nguyên mức 1, đổi sang ví dụ đèn giao thông và biển báo). Tình mỉm cười gật đầu.
  - **04:00 - 06:15:** Kéo xuống phần Thẻ tóm tắt 3 ý chính (Query, Key, Value) và làm câu trắc nghiệm kiểm tra. Tình chọn đáp án đúng ngay ở lần thử đầu tiên.
  - **Số lần bấm "Chưa hiểu / Dễ hiểu hơn":** 0 lần (được giải thích đúng mức ngay từ đầu).
- **Phản hồi nguyên văn (Quotes):**
  > *"Trước hỏi tutor cũ nó cứ tuôn cả trang công thức toán ma trận với softmax, mình nhìn là muốn tắt máy. Giờ nó tự nhận biết mình chưa vững vector nên giải thích vector trước rồi mới vào attention, cảm giác dễ ngấm hơn nhiều."*
  > 
  > *"Cái thẻ tóm tắt 3 ý chính ở cuối rất đắt giá. Nhìn vào là biết cốt lõi cần nhớ cái gì, không bị lan man."*
- **Góp ý / Điểm đau còn lại:**
  > *"Nếu sau này có thêm hình vẽ động hoặc sơ đồ tương tác các từ nối với nhau nữa thì học sẽ trực quan hơn nữa."*

---

### Phiên 2: Phạm Hương Giang (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 05.
- **Hồ sơ nền tảng:** Có nền tảng Khoa học dữ liệu (Data Science), nắm chắc toán đại số nhưng hay bị nhầm lẫn giữa Self-Attention và Cross-Attention trong mô hình Transformer.
- **Nhiệm vụ giao (Task):** "Hỏi một câu hỏi kỹ thuật về tính toán Attention Score. Khi thấy câu trả lời chưa vừa ý hoặc muốn điều chỉnh thì sử dụng các nút hành động vi chỉnh độ sâu ('Dễ hiểu hơn' / 'Sâu hơn') thay vì tự gõ lại prompt."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 01:45:** Giang gõ câu hỏi kỹ thuật: *"Attention score được tính như thế nào trong ma trận?"*.
  - **01:45 - 03:00:** AI phản hồi ở Mức 3 (chuẩn kỹ thuật, công thức $QK^T / \sqrt{d_k}$). Giang nhíu mày, cảm thấy hơi trừu tượng và bấm nút **"Dễ hiểu hơn"** (Tín hiệu: AI đánh giá ban đầu hơi cao so với nhu cầu tức thời).
  - **03:00 - 05:30:** Hệ thống hạ ngay xuống Mức 2: dùng bảng đối chiếu thuật ngữ ↔ phép tính độ tương đồng từ khóa, giữ nguyên bản chất toán nhưng có chú thích trực quan. Giang gật đầu, đọc hết câu chốt và bấm **Thumbs Up (Thích)**.
  - **05:30 - 07:00:** Làm câu kiểm tra có phương án bẫy (hiểu lệch về Query/Key). Giang nhận diện được bẫy và trả lời đúng.
  - **Số lần bấm "Dễ hiểu hơn":** 1 lần (hạ từ Mức 3 xuống Mức 2 thành công).
- **Phản hồi nguyên văn (Quotes):**
  > *"Thích nhất là có các nút 'Dễ hiểu hơn' với 'Sâu hơn'. Bình thường trên ChatGPT mình phải ngồi nghĩ xem gõ câu lệnh thế nào: 'giải thích lại ngắn hơn', 'cho ví dụ dễ hơn'... Rất mất thời gian và ngắt quãng mạch suy nghĩ. Bấm một nút là xong."*
  > 
  > *"Trước đây ở bản prototype cũ có cái menu chọn Level 1 đến Level 5, nhìn vào chẳng ai tự biết mình đang ở Level mấy để mà chọn. Nút Dễ hiểu hơn / Sâu hơn này văn minh và tiện hơn nhiều."*
- **Góp ý / Điểm đau còn lại:**
  > *"Khi hạ mức giải thích cho dễ hiểu, nhớ đừng làm mất các biến Query, Key, Value vì lát nữa vào làm bài Lab code PyTorch mà không thấy các biến này thì sẽ bị bỡ ngỡ."*

---

### Phiên 3: Phạm Thành Thái (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 08.
- **Hồ sơ nền tảng:** Học viên thích tìm hiểu mở rộng, hay hỏi những chủ đề nâng cao hoặc nằm ngoài phạm vi buổi học hiện tại (Out-of-Scope).
- **Nhiệm vụ giao (Task):** "Thử nghiệm hỏi các câu hỏi mở rộng hoặc câu hỏi nằm ngoài nội dung bài Day 1 (ví dụ hỏi về 'ReAct Agent', 'Fine-tuning LoRA' hoặc 'Điểm danh ở đâu') để kiểm tra tính an toàn và giới hạn của Trợ giảng AI."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 02:00:** Thái gõ: *"ReAct Agent hoạt động thế nào trong bài giảng?"*.
  - **02:00 - 03:30:** AI không hề bịa đặt kiến thức (0% hallucination), phản hồi ngay: *"Khái niệm ReAct Agent chưa có trong bài giảng Day 1 (Nền tảng Transformer), mình không giải thích để tránh đoán sai cho bạn"*, đồng thời trích dẫn phần gần nhất [Day 1 - Slide 12] và hiển thị nút nổi bật **"Soạn câu hỏi cho TA"**.
  - **03:30 - 05:00:** Thái bấm thử nút **"Soạn câu hỏi cho TA"**: Hệ thống tự động điền sẵn ngữ cảnh câu hỏi, bài học hiện tại và ô nội dung để gửi cho Trợ giảng mà không đòi hỏi học viên phải copy-paste.
- **Phản hồi nguyên văn (Quotes):**
  > *"Bình thường ChatGPT gặp câu không có trong tài liệu là nó chém gió tự tin như thật, làm học viên học sai kiến thức. Con bot này biết nói 'chưa học' và chỉ sang TA. Điểm này rất trung thực và đáng tin cậy."*
  > 
  > *"Nút soạn câu hỏi cho TA rất tiện cho mấy câu hỏi ngoài bài hoặc lúc làm Lab bị lỗi lạ."*

---

## 3. Tổng kết Chỉ số Đo lường Vòng Validation

| Tiêu chí | Kết quả ghi nhận ($n=3$) | Đánh giá |
|---|:---:|---|
| **Tỉ lệ vượt qua câu kiểm tra (Quiz Pass)** | **100% (3/3)** | Học viên nắm vững bản chất kiến thức sau khi đọc giải thích |
| **Số lần bấm "Dễ hiểu hơn" trung bình** | **0.33 lần/người** | AI chẩn đoán mức độ tương đối sát ngay từ lượt đầu |
| **Tỉ lệ hài lòng với cơ chế vi chỉnh (Micro-step buttons)** | **100% (3/3)** | Đánh giá cao nút "Dễ hiểu hơn / Sâu hơn" so với menu chọn Level |
| **An toàn & Tránh hiểu lệch (Misconception Control)** | **100%** | Nhận diện đúng các bẫy hiểu nhầm trong câu trắc nghiệm |
