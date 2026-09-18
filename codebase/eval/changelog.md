# Changelog đánh giá

Mỗi vòng: chạy **trọn bộ** tập test → chọn **1 lỗi đau nhất** → sửa và thử trên tập dev → chạy lại trọn bộ.

| Vòng | Ngày | Provider / model | Prompt | Đổi gì | Vì sao (case) | Case đạt (test) | D4 | Chi phí |
|---|---|---|---|---|---|---|---|---|
| 0 | 17/9 | fake | p3-v1 | Khung eval + 30 case nháp | Kiểm tra đường ống, không phải kết quả AI | 30/30 (luật) | — | $0 |
| 1 | 17/9 | openai / gpt-4o-mini | p3-v1 | Chạy lần đầu với AI thật | — | 20/20 test, nhưng **6/20 phải dùng mẫu dự phòng** | 11/11 | $0,031 (test) + $0,011 (dev) |
| 1b | 18/9 | openai / gpt-4o-mini | **p3-v2** | Sửa 2 lỗi báo nhầm của bước kiểm tra: (1) LLM chấm coi phần nền và câu "giới hạn ví dụ" là không có căn cứ; (2) cả luật lẫn LLM chấm coi câu **phủ định** hiểu lệch ("không đọc lần lượt từng từ") là hiểu lệch. Thêm nhãn [đã duyệt]/[tự viết] khi đưa câu trả lời cho LLM chấm. | Case T04: bị loại 2 lần rồi rơi về mẫu dù nội dung đúng | Thử 1 lượt: hết dự phòng, 3 lời gọi thay vì 5, 9,9 s thay vì 25 s, $0,002 thay vì $0,0035 | | |
| 2 | 18/9 | openai / gpt-4o-mini | p3-v2 | (nhóm chạy lại) | — | 20/20 test nhưng còn **6/20 dùng mẫu dự phòng**; dev 10/10 với 3 dự phòng | 11/11 | ~$0,05 |
| 3 | 18/9 | openai / gpt-4o-mini | **p3-v3** | (1) block thiếu `src` được vá theo mẫu đã duyệt / nguồn của khái niệm thay vì loại; (2) LLM chấm chỉ soi dòng `[tự viết]`, khung sư phạm (ví dụ, bảng nối, giới hạn, phần nền) là ngữ cảnh; (3) prompt nhắc "map cũng phải có src"; (4) mở rộng `outside_terms` (BERT, decoder-only, tiktoken…); (5) ghi vết prompt + phản hồi thô | 9/10 lượt bị loại là do thiếu `src` ở block bảng nối, không phải sai kiến thức | Thử D03, D07, D10: hết dự phòng. T22, T23, D11, D12 (thuật ngữ chưa có thẻ): từ chối đúng | | ~$0,02 |
| 4 | 18/9 | openai / gpt-4o-mini | p3-v3 | Chạy trọn bộ sau các sửa ở vòng 3 | — | **22/23 test (96%)**, dev 12/12, **0 case dùng dự phòng**; baseline 3/21 (14%) | 11/11 (100%) | $0,054 (test) + $0,042 (dev) |
| 4b | 18/9 | openai / gpt-4o-mini | **p3-v4** | Thêm **khía cạnh câu hỏi (`ask_type`)**: khai_niem · co_che · ung_dung · so_sanh · vi_du. Thẻ có phần trả lời riêng cho "ứng dụng"; validator chỉ bắt phủ đủ 3 ý chính khi hỏi "là gì / hoạt động thế nào"; hỏi khía cạnh khác không còn bị tính là "hỏi lại"; bước chấm được xem mọi đoạn mà câu trả lời trích dẫn | Dùng thật: hỏi "tính ứng dụng của self-attention" nhưng nhận lời giải thích cơ chế; hỏi tiếp về ứng dụng lại bị hỏi khảo sát | Thử 2 lượt thật: trả lời đúng khía cạnh, 0 lần bị loại, 3 lời gọi, $0,002 | | |
| 5 | | | p3-v4 | Việc tiếp: chạy lại dev + test + baseline; soạn thẻ **Transformer** (case T21) | T21 hỏi "tóm tắt hoạt động của transformer" — trợ giảng trả lời "chưa có thẻ" | | | |
