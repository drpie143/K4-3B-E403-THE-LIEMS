<task>
Xác định học viên đang vướng ở đâu và nên giải thích ở mức nào, theo kiểu nào.
Trả về Decision. KHÔNG viết lời giải thích.
</task>

<concept_card>
{{card}}
</concept_card>

<passages>
{{passages}}
</passages>

<learner_memory>
{{memory}}
</learner_memory>

<survey>
{{survey}}
</survey>

<session>
{{session}}
</session>

<rule_suggestion>
{{rule_suggestion}}
</rule_suggestion>

<selection>{{selection}}</selection>
<student_message>{{text}}</student_message>

<rules>
- concept phải là "{{concept}}".
- Khái niệm nền nào có effective_level = "chua" → đưa vào missing_concepts và level = L1.
- Mục nào trong learner_memory có stale = true → coi là thấp hơn 1 bậc và giảm confidence.
- Học viên nói chưa hiểu sau một lời giải thích → level thấp hơn lần trước ít nhất 1 bậc và style khác lần trước.
- Ưu tiên style/analogy trong "worked"; không chọn style/analogy trong "failed" nếu còn lựa chọn khác.
- preferred_analogy chỉ được là id trong approved_analogies hoặc null.
- Không suy ra mức hiểu của khái niệm này từ khái niệm khác.
- Không đủ thông tin để chọn → need_survey = true và confidence < 0.6.
- in_scope = false chỉ khi học viên yêu cầu việc không phải giải thích nội dung bài.
- source_ids chỉ lấy từ id trong <passages>.
- misconception_suspected: id M* nếu câu học viên lộ ra một ý trong misconceptions, nếu không thì null.
- reason_for_user: 1 câu tiếng Việt thân thiện nói vì sao giải thích như vậy; KHÔNG nhắc tên mức (L1…L5, "cơ bản", "nâng cao"...).
- <rule_suggestion> là gợi ý từ luật; có thể khác nếu câu hỏi cho thấy rõ điều khác.
</rules>
