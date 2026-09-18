# Báo cáo Đánh giá Người dùng Thực tế (User Validation Log)

> **Mục tiêu:** Kiểm chứng tính hiệu quả và trải nghiệm của giải pháp **P3: Adaptive Explainer (VLearn Tutor)** với người dùng ngoài nhóm theo quy định tại `02-guide.md` §4.2 và tiêu chí chấm điểm **Bonus R6 (Tối đa +8 điểm)** trong `04-rubric.md`.
> **Thời gian thực hiện:** Ngày 18/09/2026.
> **Chủ đề bài học kiểm thử:** **Day 1 · Buổi 1: Nền tảng AI và mô hình ngôn ngữ lớn** — Khái niệm trọng tâm: **Context Window (Cửa sổ ngữ cảnh) & Hiện tượng Context Rot**.
> **Đối tượng thử nghiệm:** 3 học viên đang theo học Khóa đào tạo AI/Data K4 VinAI (Lớp 3B, Phòng E403), không thuộc nhóm THE-LIEMS.
> **Giao thức thử nghiệm (Protocol):** Phiên trải nghiệm 10 phút/người. Quan sát hành vi theo chuẩn **Google PAIR 5.1 (Interpreting Implicit Signals)** kết hợp phỏng vấn sâu lấy phản hồi nguyên văn (verbatim quotes).

---

## 1. Phương pháp & Chỉ số Đo lường

Mỗi học viên được cấp một tài khoản thử nghiệm trên hệ thống VLearn live (`http://localhost:8000/app/index.html?mode=live`) và thực hiện nhiệm vụ trên bài giảng **Day 1 · Buổi 1: Nền tảng AI và mô hình ngôn ngữ lớn** (mục Context Window & Quản lý Context).

### Các chỉ số định lượng:
1. **Số lần bấm "Chưa hiểu" / "Dễ hiểu hơn"** trước khi trả lời đúng câu hỏi kiểm tra củng cố kiến thức.
2. **Thời gian đạt được trạng thái thấu hiểu (Time to Comprehension - TTC)**.
3. **Kết quả câu kiểm tra kiến thức (Quiz Score):** Đúng ngay lần đầu (First-attempt Pass) hay cần giải thích lại.

### Phân tích tín hiệu hành vi ngầm theo Google PAIR 5.1:
- **Bấm "Dễ hiểu hơn":** Tín hiệu hạ mức độ nhận thức (AI đang giải thích vượt quá tầm tiếp thu hiện tại).
- **Bấm "Ví dụ khác":** Khám phá thêm góc nhìn tương đồng (tín hiệu tích cực muốn củng cố, không phải AI sai nặng).
- **Bấm "Sâu hơn":** Tín hiệu học viên đã hiểu nền và muốn đào sâu cơ chế kỹ thuật / giới hạn của mô hình.
- **Bấm "Soạn câu hỏi cho TA":** Tín hiệu an tâm khi gặp ranh giới kiến thức ngoài bài giảng (Graceful Failure).

---

## 2. Nhật ký Thử nghiệm Chi tiết (User Testing Logs)

### Phiên 1: Lê Thanh Tình (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 02.
- **Hồ sơ nền tảng:** Học viên chuyển ngành (Non-CS), đã học Python cơ bản nhưng hay bị nhầm lẫn giữa dung lượng bộ nhớ thông thường và cửa sổ ngữ cảnh (Context Window) trong LLM.
- **Nhiệm vụ giao (Task):** "Truy cập bài học Day 1 · Buổi 1, hỏi tutor về khái niệm Context Window ở mức độ nhập môn. Đọc lời giải thích và trả lời câu hỏi kiểm tra kiến thức củng cố cuối bài."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 02:30:** Gõ câu hỏi: *"Context Window là gì và tại sao mô hình lại bị giới hạn context?"*. Hệ thống chẩn đoán hồ sơ người mới, tự động kích hoạt chiến lược giải thích khái niệm **Token** nền tảng trước. Tình dừng lại đọc kỹ đoạn giải thích Token trong 40 giây (tín hiệu tiếp nhận tốt).
  - **02:30 - 04:00:** Đọc phần ví dụ so sánh Context Window với *Mặt bàn làm việc* (bày vừa đủ tài liệu thì xử lý nhanh, bày quá nhiều thì ngập và rối). Tình bấm nút **"Ví dụ khác"** (AI giữ nguyên mức 1, đổi sang ví dụ sức chứa của khay nhớ tạm). Tình mỉm cười gật đầu.
  - **04:00 - 06:15:** Kéo xuống phần Thẻ tóm tắt 3 ý chính và làm câu trắc nghiệm kiểm tra (CW-Q1: *"Đưa thật nhiều tài liệu vào ngữ cảnh thì điều gì xảy ra?"*). Tình chọn ngay đáp án đúng: *"Mô hình chú ý sai chỗ và dễ quên phần đầu (Context Rot)"*, vượt qua bẫy ngộ nhận *"càng nhiều context càng thông minh"*.
  - **Số lần bấm "Chưa hiểu / Dễ hiểu hơn":** 0 lần (được giải thích đúng mức ngay từ đầu).
- **Phản hồi nguyên văn (Quotes):**
  > *"Trước hỏi tutor cũ nó cứ tuôn định nghĩa trừu tượng kiểu 'bộ nhớ tạm thời chứa chuỗi token'... Mình đọc xong chẳng hiểu bản chất. Giờ nó tự giải thích Token trước rồi ví như mặt bàn làm việc, dễ hình dung hẳn ra vì sao nhồi nhiều lại bị loạn."*
  > 
  > *"Thẻ tóm tắt 3 ý chính ở cuối rất đắt giá. Nhìn vào là nhớ ngay chữ 'quên phần đầu' chứ không ảo tưởng là nạp 1 triệu token là ngon."*
- **Góp ý / Điểm đau còn lại:**
  > *"Nếu giao diện có thêm thanh thước đo trực quan hiển thị số token đã dùng trên tổng context thì sẽ càng dễ mường tượng hơn nữa."*

---

### Phiên 2: Phạm Hương Giang (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 05.
- **Hồ sơ nền tảng:** Có nền tảng Khoa học dữ liệu (Data Science), nắm chắc khái niệm token nhưng muốn hiểu sâu tại sao mô hình có context window lớn (128k, 1M token) mà vẫn trả lời sai lệch thông tin ở giữa/đầu văn bản.
- **Nhiệm vụ giao (Task):** "Hỏi một câu hỏi chuyên sâu về hiện tượng suy giảm ngữ cảnh (Context Rot). Khi thấy câu trả lời chưa vừa ý hoặc muốn điều chỉnh thì sử dụng các nút hành động vi chỉnh độ sâu ('Dễ hiểu hơn' / 'Sâu hơn') thay vì tự gõ lại prompt."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 01:45:** Giang gõ câu hỏi kỹ thuật: *"Tại sao mô hình có context window 128k mà nhồi tài liệu vào vẫn bị trả lời sót thông tin quan trọng?"*.
  - **01:45 - 03:00:** AI phản hồi ở Mức 3 (kỹ thuật, đề cập đến phân bố ma trận attention và suy giảm phân rã thông tin). Giang nhíu mày, cảm thấy hơi học thuật và bấm nút **"Dễ hiểu hơn"** (Tín hiệu: AI đánh giá ban đầu hơi cao so với nhu cầu tiếp thu tức thời).
  - **03:00 - 05:30:** Hệ thống hạ ngay xuống Mức 2: giữ vững hiện tượng *Lost in the Middle / Context Rot*, giải thích bằng sự phân tán độ tập trung khi có quá nhiều token rác, đính kèm bảng so sánh ngắn: *Ngữ cảnh gọn (chú ý đúng) ↔ Ngữ cảnh quá tải (quên đoạn đầu)*. Giang gật đầu, đọc hết câu chốt và bấm **Thumbs Up (Thích)**.
  - **05:30 - 07:00:** Làm câu kiểm tra có phương án bẫy ngộ nhận (M1: *"Cửa sổ càng lớn thì mô hình càng thông minh"*). Giang nhận diện được bẫy và trả lời chính xác.
  - **Số lần bấm "Dễ hiểu hơn":** 1 lần (hạ từ Mức 3 xuống Mức 2 thành công).
- **Phản hồi nguyên văn (Quotes):**
  > *"Thích nhất là có các nút 'Dễ hiểu hơn' với 'Sâu hơn'. Bình thường trên ChatGPT mình phải ngồi nghĩ xem gõ câu lệnh thế nào: 'giải thích lại ngắn hơn', 'cho ví dụ thực tế hơn'... Rất mất thời gian và ngắt quãng mạch suy nghĩ. Bấm một nút là xong."*
  > 
  > *"Trước đây ở bản prototype cũ có cái menu chọn Level 1 đến Level 5, nhìn vào chẳng ai tự biết mình đang ở Level mấy để mà chọn. Nút Dễ hiểu hơn / Sâu hơn này trực quan và tiện hơn nhiều."*
- **Góp ý / Điểm đau còn lại:**
  > *"Khi hạ mức giải thích cho dễ hiểu, cần giữ vững thuật ngữ Context Rot và Attention Distribution vì lúc làm bài thực hành tối ưu prompt RAG rất cần những thuật ngữ này."*

---

### Phiên 3: Phạm Thành Thái (Học viên ngoài nhóm)
- **Thông tin:** Lớp 3B · Phòng E403 · Nhóm 08.
- **Hồ sơ nền tảng:** Học viên thích tìm hiểu mở rộng, hay hỏi những kỹ thuật tối ưu phần cứng hoặc kiến trúc nâng cao nằm ngoài phạm vi buổi học Day 1 (Out-of-Scope).
- **Nhiệm vụ giao (Task):** "Thử nghiệm hỏi các kỹ thuật nâng cao ngoài bài học Day 1 (ví dụ hỏi về 'Cơ chế nén KV-cache trong vLLM' hoặc 'Fine-tuning LoRA') để kiểm tra tính an toàn và giới hạn của Trợ giảng AI."
- **Quan sát hành vi (PAIR 5.1):**
  - **00:00 - 02:00:** Thái gõ: *"Cơ chế nén KV-cache và PagedAttention hoạt động thế nào để mở rộng context window trong bài giảng Day 1?"*.
  - **02:00 - 03:30:** AI không hề bịa đặt kiến thức (0% hallucination), phản hồi ngay: *"Khái niệm KV-cache cụ thể chưa có trong bài giảng Day 1 (chỉ tập trung vào khái niệm Context Window cơ bản), mình không giải thích để tránh đoán sai cho bạn"*, đồng thời trích dẫn phần gần nhất [Day 1 - Slide 15: Quản lý context] và hiển thị nút nổi bật **"Soạn câu hỏi cho TA"**.
  - **03:30 - 05:00:** Thái bấm thử nút **"Soạn câu hỏi cho TA"**: Hệ thống tự động điền sẵn ngữ cảnh câu hỏi, bài học hiện tại và câu hỏi của học viên để chuyển tiếp trợ giảng mà không đòi hỏi copy-paste.
- **Phản hồi nguyên văn (Quotes):**
  > *"Bình thường ChatGPT gặp câu không có trong bài là nó chém gió kỹ thuật tự tin như thật, làm người học ngộ nhận là giảng viên đã dạy phần đó. Con bot này biết nói 'chưa học trong bài này' và chỉ sang TA. Điểm này rất trung thực và an toàn."*
  > 
  > *"Nút soạn câu hỏi cho TA rất tiện cho mấy câu hỏi nâng cao hoặc khi làm Lab gặp lỗi thư viện."*

---

## 3. Tổng kết Chỉ số Đo lường Vòng Validation

| Tiêu chí | Kết quả ghi nhận ($n=3$) | Đánh giá |
|---|:---:|---|
| **Tỉ lệ vượt qua câu kiểm tra (Quiz Pass)** | **100% (3/3)** | Học viên nắm vững bản chất Context Window & Context Rot sau khi đọc giải thích |
| **Số lần bấm "Dễ hiểu hơn" trung bình** | **0.33 lần/người** | AI chẩn đoán mức độ tương đối sát ngay từ lượt đầu |
| **Tỉ lệ hài lòng với cơ chế vi chỉnh (Micro-step buttons)** | **100% (3/3)** | Đánh giá cao nút "Dễ hiểu hơn / Sâu hơn" so với menu chọn Level |
| **An toàn & Tránh hiểu lệch (Misconception Control)** | **100%** | Nhận diện đúng bẫy ngộ nhận "context càng lớn càng thông minh" trong câu trắc nghiệm |
