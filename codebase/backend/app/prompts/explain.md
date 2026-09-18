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
Đây là mẫu đã được duyệt cho đúng mức và kiểu này. Giữ cấu trúc và độ chính xác,
điều chỉnh để trả lời đúng câu học viên hỏi; không cần chép nguyên văn.
{{reference}}
</reference_answer>

<previous_answer_summary>{{previous}}</previous_answer_summary>
<memory_hint>dùng: {{worked}} · tránh: {{failed}}</memory_hint>
<learner_note>{{note}}</learner_note>
<selection>{{selection}}</selection>
<student_message>{{text}}</student_message>

<format>
- Nếu decision.prereq_first khác null: block đầu có t = "prereq", title = "Trước hết: <tên khái niệm>", giải thích khái niệm đó 1–2 câu theo <prerequisite_primer>.
- Mức L1/L2 phải có đủ các block: "analogy" → "map" (rows là các cặp [ví dụ, thuật ngữ]) → "key" → "limit".
- Block "key" phải nêu đủ các ý trong core_claims, dùng thuật ngữ trong required_terms; ghi claims = ["C1", ...] tương ứng.
- Mỗi block (trừ "outside", "formula") phải có src là các id trong decision.source_ids hoặc <passages>, và claims mà block đó nêu.
  Kể cả block "map" (bảng nối) và "analogy" cũng phải có src — để trống là câu trả lời bị loại.
- Nội dung ngoài bài giảng (công thức chuẩn, chi tiết phép tính không có trong passages) đặt trong block "outside", src = [].
- Nếu dùng ví dụ, chỉ dùng id trong approved_analogies, ưu tiên decision.preferred_analogy, không dùng id trong "tránh". Ghi id vào analogy_id (không dùng ví dụ thì null).
- Không lặp lại cách giải thích trong previous_answer_summary.
- Độ dài (không tính bảng, block prereq và block outside): L1 ≤ 120 từ · L2 ≤ 180 · L3 ≤ 180 · L4 ≤ 220 · L5 ≤ 320. Mức L1 dùng câu ngắn.
- html chỉ dùng <b>, <i>, <sub>. Không dùng tiêu đề markdown.
- summary_for_next_turn: 1 câu mô tả cách vừa giải thích (kiểu, ví dụ đã dùng).
{{fix_instructions}}
</format>
