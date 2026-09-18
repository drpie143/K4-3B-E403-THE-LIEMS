from __future__ import annotations

# Diễn giải nhóm từ thẻ khái niệm Day 1 (app/data/cards/) — không phải nguyên văn transcript.
CHUNKS = [
    {
        "chunk_id": "a1b2c3d4-e5f6-7890-abcd-111111111111",
        "lecture_id": "day01-self-attention",
        "slide_page": 1,
        "text": (
            "Self-attention: mỗi token nhìn các token khác trong câu cùng lúc (song song) "
            "và tính điểm liên quan / trọng số. Dùng Query–Key–Value: Query của token so với "
            "Key của token khác → trọng số → lấy Value theo trọng số. Ví dụ “Con mèo ngồi lên bàn, "
            "nó rất đáng yêu”: mô hình gắn “nó” với “con mèo”. [T06-126] [T06-130]"
        ),
        "topic_tags": ["self_attention", "attention"],
    },
    {
        "chunk_id": "a1b2c3d4-e5f6-7890-abcd-222222222222",
        "lecture_id": "day01-self-attention",
        "slide_page": 2,
        "text": (
            "Ví dụ thư viện: dò nhãn trên gáy từng cuốn (Key), cuốn khớp nhất thì đọc nội dung "
            "bên trong (Value); cuốn đang tìm là Query. Key là nhãn để so khớp; Value mới là "
            "nội dung được lấy ra. [T06-131]"
        ),
        "topic_tags": ["self_attention"],
    },
    {
        "chunk_id": "a1b2c3d4-e5f6-7890-abcd-333333333333",
        "lecture_id": "day01-self-attention",
        "slide_page": 3,
        "text": (
            "Vector (embedding) giống toạ độ GPS của một token: một dãy số định vị token "
            "trong không gian toán học. Có toạ độ thì máy mới tính được hai token gần nhau đến đâu. [T06-127] [T06-128]"
        ),
        "topic_tags": ["vector", "embedding"],
    },
    {
        "chunk_id": "a1b2c3d4-e5f6-7890-abcd-444444444444",
        "lecture_id": "day01-self-attention",
        "slide_page": 4,
        "text": (
            "Token là đơn vị mà LLM đọc — không phải từng ký tự, cũng không hẳn là từng từ. "
            "Ví dụ “Hello World” là 2 token. [T06-134] [T06-135]"
        ),
        "topic_tags": ["token"],
    },
    {
        "chunk_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "lecture_id": "k4-week3-rag",
        "slide_page": 12,
        "text": (
            "RAG (Retrieval-Augmented Generation) là kỹ thuật kết hợp truy xuất tài liệu "
            "với mô hình sinh. Thay vì chỉ dựa vào bộ nhớ của LLM, hệ thống tìm các đoạn "
            "văn liên quan trong kho tài liệu rồi nhồi vào prompt trước khi sinh câu trả lời."
        ),
        "topic_tags": ["rag"],
    },
    {
        "chunk_id": "8d0f7780-8536-51ef-a55c-f18fd2a01bf8",
        "lecture_id": "k4-week3-rag",
        "slide_page": 13,
        "text": (
            "Pipeline RAG gồm: (1) chunk tài liệu, (2) embedding, (3) lưu vector DB, "
            "(4) embed câu hỏi, (5) retrieve top-k, (6) generate. Trade-off: thêm độ trễ "
            "retrieve để giảm hallucination so với LLM thuần."
        ),
        "topic_tags": ["rag", "embedding"],
    },
    {
        "chunk_id": "9e1a8891-9647-62f0-b66d-029ae3b12ca9",
        "lecture_id": "k4-week4-docker",
        "slide_page": 4,
        "text": (
            "Docker volume là cơ chế lưu dữ liệu bền ngoài vòng đời container. "
            "Volume được mount vào filesystem của container; khi container bị xóa, "
            "dữ liệu trên volume vẫn còn."
        ),
        "topic_tags": ["docker"],
    },
]
