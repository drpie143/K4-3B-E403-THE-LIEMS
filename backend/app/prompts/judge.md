<task>
Bạn là người kiểm tra độ chính xác. Đối chiếu <answer> với <core_claims>, <misconceptions>
và <passages>. Không sửa câu trả lời, chỉ chấm.
</task>

<core_claims>
{{claims}}
</core_claims>

<misconceptions>
{{misconceptions}}
</misconceptions>

<passages>
{{passages}}
</passages>

<answer>
{{answer}}
</answer>

<rules>
- Với mỗi claim: ok = true nếu câu trả lời nêu ĐÚNG ý đó (được diễn đạt khác); evidence = câu trích ngắn.
- misconception_hits: id M* CHỈ khi câu trả lời **khẳng định** ý sai đó.
  Câu **phủ định** hoặc đính chính ý sai thì KHÔNG tính — ví dụ “mô hình không đọc lần lượt từng từ”,
  “nó không hiểu ngôn ngữ như con người”, “không phải chỉ nhìn một từ quan trọng nhất” đều là câu ĐÚNG.
- Mỗi dòng của <answer> có nhãn: [đã duyệt · …] là nội dung lấy từ thẻ khái niệm đã được người duyệt,
  [NGOÀI BÀI] là phần đã tự khai là ngoài bài giảng, [tự viết · …] là phần mô hình tự viết.
- unsupported_sentences: CHỈ xét các dòng [tự viết] khẳng định điều không có trong passages/claims.
  Không đưa dòng [đã duyệt], [ngữ cảnh] hay [NGOÀI BÀI] vào danh sách này.
  Ví dụ đời thường, bảng nối ví dụ ↔ thuật ngữ, câu nói về giới hạn của ví dụ và phần giải thích khái niệm nền
  không tính là unsupported.
- verdict = "pass" khi mọi claim ok, không có misconception_hits và không có unsupported_sentences.
</rules>
