# Nhật ký Thay đổi Sản phẩm dựa trên Phản hồi Người dùng (Validation Changelog)

> Tài liệu tổng hợp các quyết định kỹ thuật, tinh chỉnh giao diện và điều chỉnh logic hệ thống xuất phát trực tiếp từ các phiên thử nghiệm thực tế với người dùng ngoài nhóm (Lê Thanh Tình, Phạm Hương Giang, Phạm Thành Thái) được ghi lại trong `validation/log.md`.
> Đáp ứng tiêu chí chấm điểm **Bonus R6** theo `04-rubric.md`.

---

## 1. Bảng Tổng hợp Thay đổi (Feedback-to-Action Matrix)

| # | Phản hồi / Hành vi quan sát | Người dùng | Quyết định sản phẩm | Chi tiết thay đổi kỹ thuật | Trạng thái |
|---|---|---|---|---|:---:|
| **1** | Bối rối khi thấy menu chọn Level 1 đến Level 5; không tự đánh giá được mình ở level nào | **Phạm Hương Giang** | **XÓA BỎ** menu chọn level tĩnh; thay bằng các nút vi chỉnh hành vi (Micro-actions) | • Thay `select#level-picker` bằng cụm 4 nút: `Dễ hiểu hơn`, `Sâu hơn`, `Ví dụ khác`, `Ngắn hơn`.<br/>• Frontend gửi kèm `adjustment_hint` vào API.<br/>• Backend `policy.py` tự động cộng/trừ 1 bậc trên thang 5 mức nội bộ. | **Đã hoàn thành** (commit `80ccb0f`) |
| **2** | Lo ngại việc giải thích quá dễ hiểu bằng ví dụ đời thường làm mất đi thuật ngữ toán học, khiến học viên bỡ ngỡ khi làm Lab PyTorch | **Phạm Hương Giang** & **Lê Thanh Tình** | **BẮT BUỘC** giữ nguyên các thuật ngữ toán học cốt lõi và bổ sung dòng giới hạn của ví dụ | • Bổ sung bộ `Fidelity Validator` trong `app/validator.py`: Ép LLM phải giữ nguyên bộ 3 biến ($Q, K, V$) ngay cả ở mức giải thích thấp nhất.<br/>• Bắt buộc đính kèm block: *"Giới hạn của ví dụ: Trong thực tế, Attention là tích vô hướng được chuẩn hoá qua hàm Softmax..."*. | **Đã hoàn thành** (commit `80ccb0f`) |
| **3** | Đánh giá rất cao việc AI từ chối khi gặp câu hỏi ngoài bài thay vì tự bịa (hallucinate), nhưng cần cách liên hệ TA nhanh hơn | **Phạm Thành Thái** | **TÍCH HỢP** nút 1-click "Soạn câu hỏi cho TA" khi phát hiện ngoài phạm vi (Out-of-Scope) | • Khi `retrieval.py` trả về `no_source` hoặc câu hỏi vi phạm phạm vi buổi học (Decision: `out_of_scope`), UI tự động hiển thị nút `Soạn câu hỏi cho TA`.<br/>• Click nút sẽ mở modal soạn sẵn câu hỏi kèm tên bài học, mã slide gần nhất và câu hỏi của học viên. | **Đã hoàn thành** (commit `80ccb0f`) |
| **4** | Muốn có hình vẽ/biểu đồ động minh hoạ kiến trúc kết nối giữa các từ thay vì chỉ đọc text | **Lê Thanh Tình** | **GIỮ NGUYÊN BẢN HIỆN TẠI & ĐƯA VÀO ROADMAP TUẦN TỚI** (Có lý do kỹ thuật căn cứ) | • **Lý do giữ nguyên tại CP5:** Hạn chốt tính năng đã đóng; việc render biểu đồ tương tác đòi hỏi pipeline trích xuất PDF slide đa phương tiện (Multimodal OCR), có nguy cơ làm tăng độ trễ p95 vượt ngưỡng 10 giây đã cam kết.<br/>• **Hướng xử lý:** Đã đưa vào **Slide 6 (Nếu có thêm 1 tuần: Multimodal RAG)** trong `demo-slides.pdf`. | **Đã bảo lưu có căn cứ** |

---

## 2. Chi tiết Minh chứng Code thay đổi

### Thay đổi 1: Chuyển đổi từ Menu Level sang Nút bấm Vi chỉnh
- **Trước thay đổi:** Giao diện có dropdown menu `[Level 1: Nhập môn, Level 2: Cơ bản, Level 3: Chuẩn, Level 4: Nâng cao, Level 5: Chuyên gia]`. Học viên thường chọn sai hoặc không biết chọn gì.
- **Sau thay đổi:** Giao diện ẩn hoàn toàn nhãn level số, hiển thị 4 nút trực quan:
  ```html
  <div class="feedback-actions">
    <button class="btn-micro" onclick="adjustLevel(-1)">📉 Dễ hiểu hơn</button>
    <button class="btn-micro" onclick="adjustLevel(1)">📈 Sâu hơn</button>
    <button class="btn-micro" onclick="requestAlternativeExample()">🔄 Ví dụ khác</button>
    <button class="btn-micro" onclick="requestSummary()">✂️ Ngắn hơn</button>
  </div>
  ```

### Thay đổi 2: Bổ sung Quy tắc Ràng buộc Thuật ngữ trong Prompt & Validator
- Trong `app/validator.py` và `app/prompts.py`:
  ```python
  REQUIRED_CANONICAL_TERMS = {
      "self-attention": ["query", "key", "value", "độ chú ý"],
      "transformer": ["encoder", "decoder", "self-attention"],
      "temperature": ["độ ngẫu nhiên", "phân phối xác suất", "logits"]
  }
  
  def validate_canonical_integrity(concept: str, explanation: str) -> bool:
      """Bảo đảm dù giải thích ở mức đời thường vẫn không làm mất thuật ngữ chuẩn."""
      terms = REQUIRED_CANONICAL_TERMS.get(concept, [])
      missing = [t for t in terms if t.lower() not in explanation.lower()]
      return len(missing) == 0
  ```
