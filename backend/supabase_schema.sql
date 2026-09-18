-- ==============================================================================
-- SUPABASE DATABASE INITIALIZATION SCHEMA
-- VLearn Tutor: Adaptive Explainer (P3)
-- Chạy toàn bộ file này trong tab SQL Editor trên Supabase Dashboard
-- ==============================================================================

-- 1. Kích hoạt extension pgvector phục vụ lưu trữ và tìm kiếm vector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Bảng lưu trữ hồ sơ mức độ hiểu của học viên theo từng khái niệm
CREATE TABLE IF NOT EXISTS person_profiles (
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
CREATE TABLE IF NOT EXISTS person_strategy_memory (
  user_id TEXT NOT NULL,
  concept TEXT NOT NULL,
  strategy TEXT NOT NULL, -- ví dụ: analogy:con_meo, style:vi_du
  worked INT DEFAULT 0,
  failed INT DEFAULT 0,
  last_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, concept, strategy)
);

-- 4. Bảng cấu hình cá nhân của người học
CREATE TABLE IF NOT EXISTS person_settings (
  user_id TEXT PRIMARY KEY,
  memory_on INT DEFAULT 1,
  preferred_style TEXT DEFAULT NULL -- vi_du | chi_tiet | ngan_gon
);

-- 5. Bảng nhật ký sự kiện tương tác (hỗ trợ Undo / Hoàn tác)
CREATE TABLE IF NOT EXISTS person_events (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  concept TEXT,
  type TEXT NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  before_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Bảng lưu trữ trạng thái phiên học (Session state)
CREATE TABLE IF NOT EXISTS person_chat_sessions (
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

-- ==============================================================================
-- 10. TÀI KHOẢN HỌC VIÊN (đăng ký / đăng nhập)
-- `person_accounts.id` chính là `user_id` dùng trong profiles / strategy_memory / events,
-- nên mỗi người đăng nhập sẽ thấy đúng hồ sơ và bộ nhớ dài hạn của mình.
-- Mật khẩu lưu dạng băm PBKDF2-SHA256, không bao giờ lưu thô.
-- ==============================================================================
CREATE TABLE IF NOT EXISTS person_accounts (
  id            TEXT PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  display_name  TEXT,
  password_hash TEXT NOT NULL,
  role          TEXT DEFAULT 'learner',      -- learner | ta | admin
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  last_login_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS person_sessions (
  token_hash TEXT PRIMARY KEY,               -- SHA-256 của token, không lưu token gốc
  account_id TEXT NOT NULL REFERENCES person_accounts(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS person_sessions_account_idx ON person_sessions (account_id);
CREATE INDEX IF NOT EXISTS person_accounts_email_idx ON person_accounts (LOWER(email));

-- Bật RLS: chỉ backend (service_role key) được đọc/ghi hai bảng này.
ALTER TABLE person_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_sessions ENABLE ROW LEVEL SECURITY;

-- ==============================================================================
-- 11. GIỮ BỘ NHỚ DÀI HẠN KHÔNG PHÌNH
-- Backend đã nén ở phía ứng dụng (app/memory.py). Hàm dưới đây là lớp chặn thứ hai,
-- chạy được bằng tay trong SQL Editor hoặc bằng pg_cron.
-- ==============================================================================
CREATE INDEX IF NOT EXISTS person_profiles_user_idx         ON person_profiles (user_id);
CREATE INDEX IF NOT EXISTS person_strategy_memory_user_idx  ON person_strategy_memory (user_id, concept);
CREATE INDEX IF NOT EXISTS person_events_user_created_idx   ON person_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS person_chat_sessions_user_idx    ON person_chat_sessions (user_id, updated_at DESC);

CREATE OR REPLACE FUNCTION prune_learner_memory(
  p_user_id        TEXT,
  p_max_strategies INT DEFAULT 6,    -- số cách giải thích giữ lại cho mỗi khái niệm
  p_max_events     INT DEFAULT 50,   -- số sự kiện giữ lại cho mỗi người học
  p_strategy_ttl   INT DEFAULT 30,   -- ngày: cách giải thích cũ hơn thì quên
  p_session_ttl    INT DEFAULT 7     -- ngày: phiên học cũ hơn thì xoá
) RETURNS TABLE (deleted_strategies INT, deleted_events INT, deleted_sessions INT)
LANGUAGE plpgsql AS $$
DECLARE s INT; e INT; ss INT;
BEGIN
  -- 1. Quên các cách giải thích quá hạn
  DELETE FROM person_strategy_memory
   WHERE user_id = p_user_id AND last_at < NOW() - (p_strategy_ttl || ' days')::interval;
  GET DIAGNOSTICS s = ROW_COUNT;

  -- 2. Mỗi khái niệm chỉ giữ N cách tốt nhất (worked - failed, rồi tới gần đây nhất)
  WITH ranked AS (
    SELECT ctid, ROW_NUMBER() OVER (
             PARTITION BY concept ORDER BY (worked - failed) DESC, last_at DESC) AS rn
      FROM person_strategy_memory WHERE user_id = p_user_id)
  DELETE FROM person_strategy_memory sm USING ranked r
   WHERE sm.ctid = r.ctid AND r.rn > p_max_strategies;
  GET DIAGNOSTICS e = ROW_COUNT;
  s := s + e;

  -- 3. Nhật ký sự kiện: giữ N dòng gần nhất
  WITH ranked AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY created_at DESC) AS rn
      FROM person_events WHERE user_id = p_user_id)
  DELETE FROM person_events ev USING ranked r
   WHERE ev.id = r.id AND r.rn > p_max_events;
  GET DIAGNOSTICS e = ROW_COUNT;

  -- 4. Phiên học cũ
  DELETE FROM person_chat_sessions
   WHERE user_id = p_user_id AND updated_at < NOW() - (p_session_ttl || ' days')::interval;
  GET DIAGNOSTICS ss = ROW_COUNT;

  RETURN QUERY SELECT s, e, ss;
END; $$;

-- Xem nhanh bộ nhớ của từng người học đang chiếm bao nhiêu dòng
CREATE OR REPLACE VIEW learner_memory_size AS
SELECT a.id AS user_id, a.email, a.display_name,
       (SELECT COUNT(*) FROM person_profiles         p WHERE p.user_id = a.id) AS profiles,
       (SELECT COUNT(*) FROM person_strategy_memory  m WHERE m.user_id = a.id) AS strategies,
       (SELECT COUNT(*) FROM person_events           e WHERE e.user_id = a.id) AS events,
       (SELECT COUNT(*) FROM person_chat_sessions    s WHERE s.user_id = a.id) AS sessions,
       a.last_login_at
  FROM person_accounts a;
