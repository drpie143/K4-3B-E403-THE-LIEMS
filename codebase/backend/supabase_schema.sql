-- ==============================================================================
-- SUPABASE DATABASE INITIALIZATION SCHEMA
-- VLearn Tutor: Adaptive Explainer (P3)
-- Chạy toàn bộ file này trong tab SQL Editor trên Supabase Dashboard
-- ==============================================================================

-- 1. Kích hoạt extension pgvector phục vụ lưu trữ và tìm kiếm vector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Bảng lưu trữ hồ sơ mức độ hiểu của học viên theo từng khái niệm
CREATE TABLE IF NOT EXISTS profiles (
  user_id TEXT NOT NULL,
  concept TEXT NOT NULL,
  level TEXT NOT NULL, -- chua | biet_so | hieu_ro
  streak INT DEFAULT 0,
  source TEXT DEFAULT 'tu_khai', -- tu_khai | tu_doi | doi_muc | kiem_tra
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_signal_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, concept)
);

-- 3. Bảng lưu trữ bộ nhớ chiến lược sư phạm (long-term memory)
CREATE TABLE IF NOT EXISTS strategy_memory (
  user_id TEXT NOT NULL,
  concept TEXT NOT NULL,
  strategy TEXT NOT NULL, -- ví dụ: analogy:con_meo, style:vi_du
  worked INT DEFAULT 0,
  failed INT DEFAULT 0,
  last_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, concept, strategy)
);

-- 4. Bảng cấu hình cá nhân của người học
CREATE TABLE IF NOT EXISTS settings (
  user_id TEXT PRIMARY KEY,
  memory_on INT DEFAULT 1,
  preferred_style TEXT DEFAULT NULL -- vi_du | chi_tiet | ngan_gon
);

-- 5. Bảng nhật ký sự kiện tương tác (hỗ trợ Undo / Hoàn tác)
CREATE TABLE IF NOT EXISTS events (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  concept TEXT,
  type TEXT NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  before_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Bảng lưu trữ trạng thái phiên học (Session state)
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  state_json JSONB DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Bảng lưu trữ các chunk bài giảng và Dense Vector Embedding
-- MẶC ĐỊNH: vector(768) cho Google Gemini (MIỄN PHÍ 100%)
-- NẾU DÙNG OPENAI: đổi thành vector(1536)
CREATE TABLE IF NOT EXISTS lecture_chunks (
  id TEXT PRIMARY KEY,
  lesson TEXT NOT NULL,
  section TEXT NOT NULL,
  file TEXT NOT NULL,
  text TEXT NOT NULL,
  source_ids TEXT[] DEFAULT '{}'::text[],
  word_count INT DEFAULT 0,
  overlap_words INT DEFAULT 0,
  embedding vector(768), -- Đổi thành vector(1536) nếu dùng OpenAI
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Tạo chỉ mục HNSW cosine vector index để truy vấn siêu tốc (< 10ms)
CREATE INDEX IF NOT EXISTS lecture_chunks_embedding_hnsw_idx 
ON lecture_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 9. Hàm RPC tìm kiếm vector (match_chunks)
CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(768), -- Đổi thành vector(1536) nếu dùng OpenAI
  match_count int DEFAULT 5,
  lesson_filter text DEFAULT NULL
) RETURNS TABLE (
  id TEXT,
  lesson TEXT,
  section TEXT,
  file TEXT,
  text TEXT,
  source_ids TEXT[],
  similarity float
) LANGUAGE sql STABLE AS $$
  SELECT
    id,
    lesson,
    section,
    file,
    text,
    source_ids,
    1 - (embedding <=> query_embedding) AS similarity
  FROM lecture_chunks
  WHERE (lesson_filter IS NULL OR file = lesson_filter OR lesson ILIKE '%' || lesson_filter || '%')
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;
