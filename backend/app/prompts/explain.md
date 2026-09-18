<task>
Viết lời giải thích lại cho học viên theo <decision>. Trả về Answer gồm các block.
</task>

<decision>
{{decision}}
</decision>

<concept_card>
{{card}}
</concept_card>

<prerequisite_primer>
{{primer}}
</prerequisite_primer>

<passages>
{{passages}}
</passages>

<reference_answer>
Đây là mẫu đã được duyệt cho đúng mức và kiểu này. Nó cho bạn biết **cấu trúc** và **mức chính xác**
cần đạt — KHÔNG phải độ dài cần viết. Mẫu được viết cô đọng để làm khung; bài của bạn phải
**đầy đặn hơn mẫu**: cùng bộ khung đó nhưng mỗi ý được làm rõ thêm bằng chi tiết lấy từ <passages>.
Chép lại độ dài của mẫu là chưa đạt.
{{reference}}
</reference_answer>

<previous_answer_summary>{{previous}}</previous_answer_summary>
<memory_hint>dùng: {{worked}} · tránh: {{failed}}</memory_hint>
<learner_note>{{note}}</learner_note>
<selection>{{selection}}</selection>
<student_message>{{text}}</student_message>

<ask_type>{{ask_type}}</ask_type>

<format>
- **Trả lời đúng khía cạnh học viên hỏi (ask_type) ngay ở block đầu**: khai_niem = nó là gì · co_che = nó chạy thế nào ·
  ung_dung = dùng để làm gì (chỉ nêu ứng dụng có trong passages/thẻ) · so_sanh = khác ở chỗ nào · vi_du = một ví dụ cụ thể.
  Không trả lời sang khía cạnh khác rồi mới nói tới điều được hỏi.
- **Viết cho đủ, đừng viết cụt.** Học viên đang ở đây vì lần giải thích trước chưa đủ rõ. Mỗi ý chính cần
  một câu nêu ý + một câu làm rõ (vì sao / ra sao / nếu không có thì sao). Một câu trơ trọi cho cả một ý
  chính là chưa đạt.
- **Viết dài hơn bằng chất liệu có sẵn, không bằng kiến thức ngoài.** Chỗ để nói thêm là: chi tiết trong
  <passages>, câu chữ và ví dụ giảng viên đã dùng, các ý trong core_claims, ví dụ trong approved_analogies.
  Mỗi câu bạn viết phải chỉ ra được nó dựa vào đoạn nguồn nào — câu nào không bám được đoạn nào
  thì **bỏ đi**, đừng thêm nhận định chung chung ("điều này cho thấy…", "đây là khái niệm phức tạp…").
  <passages> thường dài hơn những gì bạn cần: hãy đọc hết rồi lấy đúng chi tiết làm rõ được câu hỏi,
  đừng chỉ chép lại mấy câu chốt trong core_claims.
- Khi ví dụ đời thường đã dùng, phải **nối ngược lại thuật ngữ** — nói rõ trong ví dụ thì cái gì đóng vai gì.
  Ví dụ mà không nối về thuật ngữ thì học viên không dùng được khi đọc tài liệu.
- Cấu trúc 4 phần (analogy → map → key → limit) chỉ bắt buộc khi ask_type là khai_niem hoặc co_che;
  với khía cạnh khác, giữ ít nhất một block "key" chốt bằng thuật ngữ gốc.
- Kết bằng đúng **một** câu mở đường học tiếp: chỉ ra phần kế tiếp trong bài hoặc chỗ dễ nhầm sắp gặp.
  Không hỏi ngược "bạn đã hiểu chưa", không hứa hẹn, không chào hỏi xã giao.
- Nếu bài giảng không nói về khía cạnh được hỏi, nói thẳng điều đó trong block "outside" thay vì suy diễn.
- Nếu decision.prereq_first khác null: block đầu có t = "prereq", title = "Trước hết: <tên khái niệm>", giải thích khái niệm đó 1–2 câu theo <prerequisite_primer>.
- Mức L1/L2 phải có đủ các block: "analogy" → "map" (rows là các cặp [ví dụ, thuật ngữ]) → "key" → "limit".
- Block "key" phải nêu đủ các ý trong core_claims, dùng thuật ngữ trong required_terms; ghi claims = ["C1", ...] tương ứng.
- Mỗi block (trừ "outside", "formula") phải có src là các id trong decision.source_ids hoặc <passages>, và claims mà block đó nêu.
  Kể cả block "map" (bảng nối) và "analogy" cũng phải có src — để trống là câu trả lời bị loại.
- Nội dung ngoài bài giảng (công thức chuẩn, chi tiết phép tính không có trong passages) đặt trong block "outside", src = [].
- Nếu dùng ví dụ, chỉ dùng id trong approved_analogies, ưu tiên decision.preferred_analogy, không dùng id trong "tránh". Ghi id vào analogy_id (không dùng ví dụ thì null).
- Không lặp lại cách giải thích trong previous_answer_summary.
- **Độ dài: {{length_hint}}** Mức L1 giữ câu ngắn (≤ 15 từ/câu) nhưng vẫn phải đủ số câu để nói trọn ý.
  Trước khi trả JSON, tự đếm lại: thiếu thì bổ sung phần làm rõ cho ý còn mỏng nhất.
- html chỉ dùng <b>, <i>, <sub>. Không dùng tiêu đề markdown.
- summary_for_next_turn: 1 câu mô tả cách vừa giải thích (kiểu, ví dụ đã dùng).
{{fix_instructions}}
</format>
