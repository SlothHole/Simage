PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
PRAGMA wal_autocheckpoint = 1000; -- pages; tune later
PRAGMA optimize;
PRAGMA busy_timeout = 5000;


CREATE TABLE IF NOT EXISTS images (
  id TEXT PRIMARY KEY,
  source_file TEXT UNIQUE,
  file_name TEXT,
  ext TEXT,
  width INTEGER,
  height INTEGER,
  created_utc TEXT,
  imported_utc TEXT,
  sha256 TEXT,
  format_hint TEXT,
  raw_text_preview TEXT
);

CREATE TABLE IF NOT EXISTS kv (
  image_id TEXT NOT NULL,
  k TEXT NOT NULL,
  v TEXT,
  v_num REAL,
  v_json TEXT,
  PRIMARY KEY (image_id, k),
  FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kv_k ON kv(k);
CREATE INDEX IF NOT EXISTS idx_kv_v ON kv(v);
CREATE INDEX IF NOT EXISTS idx_kv_vnum ON kv(v_num);

CREATE TABLE IF NOT EXISTS resources (
  image_id TEXT NOT NULL,
  kind TEXT NOT NULL,         -- checkpoint, lora, embedding, vae, controlnet, upscaler, etc.
  name TEXT,
  version TEXT,
  hash TEXT,
  weight REAL,
  extra_json TEXT,
  FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS files (
  image_id TEXT NOT NULL,
  kind TEXT NOT NULL,         -- mask, control_image, depth, pose, edge, etc.
  path TEXT NOT NULL,
  sha256 TEXT,
  width INTEGER,
  height INTEGER,
  extra_json TEXT,
  FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS image_gen (
  image_id TEXT PRIMARY KEY,

  model_name TEXT,
  model_version TEXT,
  model_hash TEXT,
  base_model TEXT,

  sampler TEXT,
  scheduler TEXT,
  steps INTEGER,
  cfg REAL,
  seed INTEGER,

  prompt_pos_raw TEXT,
  prompt_neg_raw TEXT,
  prompt_pos_norm TEXT,
  prompt_neg_norm TEXT,

  created_utc TEXT,

  FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prompt_tags (
  image_id TEXT NOT NULL,
  side TEXT NOT NULL,         -- 'pos' or 'neg'
  tag TEXT NOT NULL,          -- normalized (weight removed)
  weight REAL,                -- numeric weight if present else NULL
  pos INTEGER,                -- original order index
  raw TEXT,                   -- original token

  PRIMARY KEY (image_id, side, tag),
  FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
  CHECK (side IN ('pos','neg'))
);

CREATE INDEX IF NOT EXISTS idx_prompt_tags_side ON prompt_tags(side);
CREATE INDEX IF NOT EXISTS idx_prompt_tags_tag  ON prompt_tags(tag);
CREATE INDEX IF NOT EXISTS idx_prompt_tags_img  ON prompt_tags(image_id);
