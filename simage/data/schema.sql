PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

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
