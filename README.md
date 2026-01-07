AIImageMetaPipe

AIImageMetaPipe is a local metadata pipeline for AI-generated images. It:

extracts embedded metadata (ExifTool JSON output)

normalizes it into a consistent schema in SQLite

parses resources (checkpoint / lora / embedding / vae / upscaler)

tokenizes prompts into searchable tokens

supports fast analysis with indexes + views

This project is designed so you can validate everything in DB Browser for SQLite.

Directory layout

Recommended layout:

AIImageMetaPipe/
  README.md
  schema.sql
  exif_dump.ps1
  normalize_and_ingest.py
  parse_resources.py
  resolve_resource_refs.py
  aiimagepipe.py

  out/
    exif_raw.jsonl        # ExifTool dump (input to ingest)
    images.db             # SQLite database (main output)
    records.jsonl         # normalized records (debug/export)
    records.csv           # normalized flat export (quick view)

Requirements

Windows 11

Python 3.10+ (3.11+ recommended)

ExifTool installed and available on PATH (exiftool -ver works)

DB Browser for SQLite (for inspecting/queries)

SQLite must support JSON functions (DB Browser builds usually do)

Quick start (normal workflow)

Run these from PowerShell in:

C:\Users\nasty\Documents\MyTools\AIImageMetaPipe

1) Dump metadata using ExifTool

This creates out\exif_raw.jsonl.

.\exif_dump.ps1

2) Normalize + ingest into SQLite

This creates/updates out\images.db, and also writes records.jsonl + records.csv.

python .\normalize_and_ingest.py --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv

3) Parse resources into the resources table

This populates checkpoint / lora / embedding / vae / upscaler entries.

python .\parse_resources.py --db .\out\images.db

4) (Optional) Resolve resource_ref placeholders

Only needed if your DB contains kind='resource_ref' entries and you want them rewritten into real resources.

python .\resolve_resource_refs.py --db .\out\images.db --rewrite

Using the “one command” wrapper (aiimagepipe.py)

aiimagepipe.py is a convenience wrapper so you don’t have to remember which script does what.

Examples:

# help
python .\aiimagepipe.py -h

# run ingest only
python .\aiimagepipe.py ingest --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv

# parse resources only
python .\aiimagepipe.py resources --db .\out\images.db

# run the whole pipeline in order
python .\aiimagepipe.py all --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv

What each file does
schema.sql

Defines the SQLite schema (tables and constraints). At minimum this project uses:

images — one row per image file

kv — key/value storage for normalized metadata (including JSON fields)

resources — parsed model resources per image (checkpoint/lora/etc)

You also created additional objects via SQL in DB Browser:

indexes (performance)

views (convenient browsing/querying)

tokens (materialized tokens table)

exif_dump.ps1

Runs ExifTool across your image directory and writes a JSONL dump.

Output:

out\exif_raw.jsonl (one JSON object per file)

This is meant to be the stable raw input for ingestion.

normalize_and_ingest.py

Reads out\exif_raw.jsonl, extracts metadata, normalizes it, and writes:

images table rows

kv entries, including:

prompt_text, neg_prompt_text

prompt_tokens, neg_tokens (stored as JSON arrays in kv.v_json)

normalized params like steps_norm, cfg_scale_norm, seed_norm, size_norm

normalized sampler/scheduler like sampler_norm, scheduler_norm

Also produces exports:

out\records.jsonl

out\records.csv

parse_resources.py

Populates the resources table from embedded metadata sources (ex: CivitAI resources JSON, workflow JSON, A1111-like blocks, etc.).

It assigns:

resources.kind = checkpoint / lora / embedding / vae / upscaler / etc.

resources.name = normalized URN-like ID or file/name

resources.weight if present

resources.extra_json for traceability when needed

resolve_resource_refs.py

Handles the case where resources were captured as placeholders like:

kind='resource_ref'

name='modelVersionId:####'

It rewrites those into real resources:

converts to a resolved kind (checkpoint/lora/etc)

updates name/hash

preserves the original ref inside extra_json for traceability

If you don’t have an external mapping dump (like a CivitAI export), this can still operate in “manual mapping / partial resolve” mode, depending on how you’ve been running it.

aiimagepipe.py

A wrapper script that runs the above steps via subcommands:

ingest

resources

resolve

all

It does not replace the other scripts; it just orchestrates them.


`AIImageMetaPipe\export_wildcards.py`

`Then run it from that same folder.`

```python
# export_wildcards.py
# Purpose: Export prompts/tokens/resources/kv values (or any SQL query) to a newline-delimited
# text file suitable for SD/ComfyUI wildcard lists.

### Run it (PowerShell)

Run from:
`C:\Users\nasty\Documents\MyTools\AIImageMetaPipe`

#### 1) Wildcard list of **positive tokens** (most common first)

```powershell
python .\export_wildcards.py tokens --db .\out\images.db --out .\out\wildcards\pos_tokens.txt --side pos --min-count 10 --sort count_desc
```

#### 2) Wildcard list of **negative tokens**

```powershell
python .\export_wildcards.py tokens --db .\out\images.db --out .\out\wildcards\neg_tokens.txt --side neg --min-count 10 --sort count_desc
```

#### 3) Export **samplers** as a wildcard file

```powershell
python .\export_wildcards.py kv --db .\out\images.db --out .\out\wildcards\samplers.txt --key sampler_norm --sort count_desc
```

#### 4) Export **LoRA URNs** as a wildcard file

```powershell
python .\export_wildcards.py resources --db .\out\images.db --out .\out\wildcards\loras.txt --kind lora --sort count_desc
```

#### 5) Export **full prompts** (each line is a prompt)

```powershell
python .\export_wildcards.py prompts --db .\out\images.db --out .\out\wildcards\prompts.txt --which pos --min-count 2 --sort count_desc
```

#### 6) “Anything I want” via SQL (first column becomes the wildcard lines)

Example: export **top 500 most-used positive tokens**:

```powershell
python .\export_wildcards.py sql --db .\out\images.db --out .\out\wildcards\top500_pos_tokens.txt --sql "SELECT t_norm FROM tokens WHERE side='pos' GROUP BY t_norm ORDER BY COUNT(*) DESC LIMIT 500"
```

If you tell me what wildcard file you want first (tokens? LoRAs? whole prompts? “prompt templates” like `__lighting__ __composition__`), I’ll give you the exact one-liner command for it.

DB Browser “must know” notes
Always click “Write Changes”

If you run CREATE VIEW, CREATE INDEX, UPDATE, etc., DB Browser often holds changes until you click Write Changes.

Common error: “cannot start a transaction within a transaction”

DB Browser can already be inside a transaction. If a script starts with BEGIN;, remove BEGIN; and COMMIT; and re-run.

Useful views you created

You created/used views like:

v_images_with_core_params — image + cfg/steps/sampler/model/prompt fields

v_images_with_resources — image + checkpoint + loras + embeddings + vae + upscalers

v_images_search — join of core params + resources (one-row “everything” view)

Example:

SELECT * FROM v_images_search LIMIT 20;

Token search (fast path)

You created a tokens table materialized from prompt_tokens/neg_tokens.

Example: “has token X but not token Y”:

SELECT COUNT(DISTINCT p.image_id)
FROM tokens p
WHERE p.side='pos' AND p.t_norm='masterpiece'
  AND NOT EXISTS (
    SELECT 1 FROM tokens n
    WHERE n.image_id=p.image_id AND n.side='neg' AND n.t_norm='blurry'
  );

Outputs you should expect

After a successful full run:

out\images.db exists and contains:

images rows

kv rows including prompt + params + tokens

resources rows per image

Your views return meaningful data

Token search returns non-zero counts