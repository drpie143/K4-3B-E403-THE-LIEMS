CREATE TYPE user_level AS ENUM ('unknown', 'beginner', 'intermediate', 'advanced');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');
CREATE TYPE intent_type AS ENUM (
  'ask_concept', 'clarify_harder', 'ask_deeper',
  'answer_probe', 'refuse_probe', 'off_topic', 'meta'
);
CREATE TYPE explanation_mode AS ENUM ('eli5', 'slide_short', 'technical');
CREATE TYPE level_source AS ENUM (
  'assessor', 'choice_map', 'explicit_signal', 'fallback_refuse',
  'fallback_low_conf', 'fallback_score_timeout', 'seed'
);
CREATE TYPE response_kind AS ENUM (
  'probe', 'explanation', 'redirect', 'retrieval_miss', 'error', 'meta'
);
CREATE TYPE idempotency_status AS ENUM ('processing', 'completed', 'error');

CREATE TABLE users (
  id            UUID PRIMARY KEY,
  external_id   TEXT UNIQUE NOT NULL,
  display_name  TEXT,
  default_level user_level NOT NULL DEFAULT 'unknown',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE skill_levels (
  user_id                 UUID NOT NULL REFERENCES users(id),
  topic_key               TEXT NOT NULL CHECK (topic_key ~ '^[a-z0-9_]{1,64}$'),
  level                   user_level NOT NULL,
  confidence              REAL NOT NULL DEFAULT 0,
  source                  level_source NOT NULL,
  probe_consumed          BOOLEAN NOT NULL DEFAULT FALSE,
  last_level_change_turn  INT NOT NULL DEFAULT 0,
  cooldown_until_turn     INT NOT NULL DEFAULT 0,
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, topic_key)
);

CREATE TABLE conversations (
  id                         UUID PRIMARY KEY,
  user_id                    UUID NOT NULL REFERENCES users(id),
  session_id                 TEXT NOT NULL,
  turn_index                 INT NOT NULL DEFAULT 0,
  awaiting_probe             BOOLEAN NOT NULL DEFAULT FALSE,
  pending_original_query     TEXT,
  pending_topic              TEXT,
  probe_asked_this_episode   BOOLEAN NOT NULL DEFAULT FALSE,
  episode_id                 UUID,
  last_kind                  response_kind,
  last_explanation_mode      explanation_mode,
  last_assistant_sentence_count INT NOT NULL DEFAULT 0,
  last_retrieval_query       TEXT,
  last_retrieved_chunk_ids   UUID[] NOT NULL DEFAULT '{}',
  lease_until                TIMESTAMPTZ,
  started_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_turn_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id               UUID PRIMARY KEY,
  conversation_id  UUID NOT NULL REFERENCES conversations(id),
  role             message_role NOT NULL,
  content          TEXT NOT NULL,
  intent           intent_type,
  topic_key        TEXT,
  explanation_mode explanation_mode,
  response_kind    response_kind,
  citations        JSONB NOT NULL DEFAULT '[]',
  payload          JSONB,
  route_reason     TEXT,
  client_turn_id   UUID,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE level_events (
  id               UUID PRIMARY KEY,
  user_id          UUID NOT NULL REFERENCES users(id),
  conversation_id  UUID REFERENCES conversations(id),
  topic_key        TEXT NOT NULL,
  from_level       user_level,
  to_level         user_level NOT NULL,
  reason           TEXT NOT NULL,
  probe_question   TEXT,
  probe_answer     TEXT,
  confidence       REAL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documents (
  id          UUID PRIMARY KEY,
  lecture_id  TEXT UNIQUE NOT NULL,
  title       TEXT NOT NULL,
  source_uri  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
  id              UUID PRIMARY KEY,
  document_id     UUID NOT NULL REFERENCES documents(id),
  lecture_id      TEXT NOT NULL,
  slide_page      INT,
  chunk_index     INT NOT NULL,
  text            TEXT NOT NULL,
  token_count     INT,
  qdrant_point_id UUID UNIQUE,
  topic_tags      TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE idempotency_keys (
  client_turn_id   UUID PRIMARY KEY,
  conversation_id  UUID NOT NULL REFERENCES conversations(id),
  status           idempotency_status NOT NULL,
  response_json    JSONB,
  http_status      INT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idempotency_one_processing_per_conv
  ON idempotency_keys (conversation_id)
  WHERE status = 'processing';

CREATE TABLE eval_runs (
  id          UUID PRIMARY KEY,
  git_sha     TEXT,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  metrics     JSONB NOT NULL
);
