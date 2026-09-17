# Canvas CP1 — Nhóm THE-LIEMS · Lớp 3B · Phòng E403

> **Track & Đề:** Track A · VLearn Tutor — Đề A2: Tính năng AI mới trên VLearn  
> **Tên tính năng:** Adaptive Explainer (Giải thích thích ứng theo trình độ — Đo mức hiểu trước khi giải thích)

---

## Bảng Canvas 7 dòng

| # | Dòng | Nội dung |
|---|---|---|
| 1 | **Track + đề** | Track A · VLearn Tutor — Đề A2: Tính năng AI mới trên VLearn *(P3 · Adaptive Explainer: Giải thích thích ứng theo trình độ)* |
| 2 | **Job executor** | Học viên khoá AI Thực Chiến K4 đang tự học trên trang VLearn, bôi đen một khái niệm khó trên slide và hỏi Tutor để hiểu bài. |
| 3 | **Pain một câu** | Khi học viên hỏi Tutor một đoạn kiến thức, Tutor giải thích không đúng tầm trình độ (quá hàn lâm, dùng thuật ngữ vượt tầm hoặc quá dài) khiến học viên không hiểu, phải hỏi đi hỏi lại liên tục nhiều lần trong vài phút, gây ức chế và tốn thời gian. |
| 4 | **1–2 bằng chứng đầu** | **(1) Khảo sát thực tế ($n = 18$ học viên phòng E403 Lớp 3B vừa thực hiện, log tại `survey_responses.csv`):**<br>• **83.3%** (15/18) xác nhận Tutor giải thích chưa hợp trình độ (quá dài dòng/hàn lâm hoặc dùng thuật ngữ khó hiểu).<br>• **61.1%** (11/18) phải gõ hỏi lại lần 2, lần 3 ("giải thích ngắn lại / đơn giản hơn").<br>• **72.2%** (13/18) thừa nhận đọc lướt tưởng hiểu nhưng thực chất chưa nắm vững (*ảo giác hiểu bài*).<br>• **100%** (18/18) xác nhận từng bị sai Quiz/Lab ở chính phần vừa hỏi Tutor và ngỡ mình đã hiểu.<br>**(2) Data Mining (`tutor_turns.csv`):**<br>• **1.274 lượt** hỏi tiếp trong vòng 3 phút; **62 cặp** có ≥10 lượt hỏi liên tiếp.<br>• **75 lượt / 37 học viên** gõ đòi giải thích lại (`T10317`, `T10536`, `T10728`, `T10807`); `validate_understanding` chỉ 11/3.097 lượt (0.35%). |
| 5 | **Lát cắt MỘT CÂU** | Một học viên bôi đen hỏi một khái niệm khó · cần được giải thích đúng trình độ · AI đưa ra 1 câu hỏi thăm dò (probing) để đo mức hiểu hiện tại rồi quyết định mức độ giải thích (cơ bản / nâng cao) · kết quả là lời giải thích vừa tầm kèm ví dụ trực quan giúp học viên hiểu ngay mà không phải hỏi lại. |
| 6 | **AI tự làm đến đâu** | • **Tự làm:** Đo nhanh mức hiểu qua câu trả lời thăm dò, quyết định độ sâu (mức 1: ELI5/ví dụ đời thường; mức 2: kỹ thuật chuẩn) và sinh lời giải thích bám sát slide.<br>• **Không tự làm:** Không tự suy diễn khi học viên chưa phản hồi câu thăm dò; không bịa kiến thức ngoài tài liệu bài giảng.<br>• **Lý do (cost-of-error):** Giải thích sai trình độ làm học viên mất thời gian hỏi đi hỏi lại và mất niềm tin vào công cụ; giải thích sai kiến thức làm học viên học sai bản chất.<br>• **Willing users (13 học viên thật từ khảo sát đồng ý test ở CP5, đã ẩn danh):**<br>  1. Học viên `HV-01` (Lớp 3B - Phòng E403)<br>  2. Học viên `HV-02` (Lớp 3B - Phòng E403)<br>  3. Học viên `HV-03` (Lớp 3B - Phòng E403)<br>  4. Học viên `HV-04` (Lớp 3B - Phòng E403)<br>  5. Học viên `HV-05` (Lớp 3B - Phòng E403) |
| 7 | **Phân công có tên** | • `[Thành viên 1]` — Product Lead, Canvas, Spec.md, System Prompt<br>• `[Thành viên 2]` — Data & Evidence mining, khảo sát lớp, Golden set<br>• `[Thành viên 3]` — Backend/API AI call thật, Validator logic<br>• `[Thành viên 4]` — Frontend UI Mock/Flow, User Testing & Feedback log (R6) |

---

## Chi tiết kế hoạch triển khai cho các Checkpoint tiếp theo

### 1. Luồng trải nghiệm chính (cho CP2 — 21:00 17/9)
1. **Bước 1:** Học viên bôi đen khái niệm khó trên slide và bấm hỏi Tutor.
2. **Bước 2 (Chặn hỏi dồn dập):** Thay vì tuôn ra ngay 1 đoạn văn dài, Tutor đưa ra 1 câu hỏi thăm dò ngắn (1 câu trắc nghiệm hoặc kiểm tra nền tảng) để đo mức hiểu hiện tại của học viên.
3. **Bước 3:** Học viên chọn câu trả lời phản hồi.
4. **Bước 4 (Giải thích thích ứng):** AI phân loại trình độ (Cơ bản / Nâng cao) và sinh lời giải thích vừa vặn:
   - *Nếu cơ bản:* Dùng phương pháp ELI5 (Explain Like I'm 5) với ví dụ đời thường, giải thích ngắn gọn, không dùng thuật ngữ lắt léo.
   - *Nếu nâng cao:* Giải thích sâu về mặt kỹ thuật, kiến trúc, cơ chế hoạt động kèm trích dẫn số trang slide.
5. **Bước 5:** Học viên nắm được bản chất ngay từ lượt đầu tiên, không cần phải gõ hỏi lại lần 2, lần 3.

### 2. Kế hoạch kiểm thử (cho CP3 — 16:00 18/9)
- Xây dựng Golden Set 20 case: Lấy từ chính các turn chat thật học viên phải hỏi lại nhiều lần (`T10317`, `T10536`, `T10728`, `T10807`...).
- Đo lường trước/sau: Tỷ lệ câu trả lời giải thích trúng mức hiểu, giảm tỷ lệ học viên phải hỏi lại.

