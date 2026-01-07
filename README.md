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
  exif_dump.py
  normalize_and_ingest.py
  parse_resources.py
  resolve_resource_refs.py
  aiimagepipe.py
  run.ps1
  run.cmd

  Input/
    (your image files go here)

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

Run these from PowerShell in the repository root:

.

1) Dump metadata using ExifTool

This creates out\exif_raw.jsonl.

python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl

2) Normalize + ingest into SQLite

This creates/updates out\images.db, and also writes records.jsonl + records.csv.

python .\normalize_and_ingest.py --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv

3) Parse resources into the resources table

This populates checkpoint / lora / embedding / vae / upscaler entries.

python .\parse_resources.py --db .\out\images.db

4) (Optional) Resolve resource_ref placeholders

Only needed if your DB contains kind='resource_ref' entries and you want them rewritten into real resources.

python .\resolve_resource_refs.py --db .\out\images.db --rewrite

Quick run scripts

Use these to run the full workflow with default paths (Input/ and out/):

.\run.ps1
.\run.cmd

TryCode (package + tests)

This repo also includes a minimal Python package used by the tests.

Quickstart:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m TryCode
```

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

exif_dump.py

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
`.`

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

Repository flow tree (reference)

This section is a single-source, end-to-end reference for how the repo runs, which files call which, and every function definition.

Run flow (repository root)

1) `.\run.ps1` or `.\run.cmd`
   - `python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl`
   - `python .\aiimagepipe.py all`
2) `aiimagepipe.py all`
   - `normalize_and_ingest.py` (ingest EXIF JSONL -> DB + exports)
   - `parse_resources.py` (resources table extraction)
   - `resolve_resource_refs.py` (optional resource ref resolution; no-op if no mapping provided)

Repository tree (path layout)

AIImageMetaPipe/
  README.md
  aiimagepipe.py
  exif_dump.py
  export_wildcards.py
  normalize_and_ingest.py
  parse_resources.py
  resolve_resource_refs.py
  path_utils.py
  schema.sql
  run.cmd
  run.ps1
  pyproject.toml
  src/
    TryCode/
      __init__.py
      __main__.py
      core.py
  tests/
    test_core.py

File-to-file flow map (role → inbound → outbound)

run.ps1
- Role: PowerShell launcher.
- Inbound: user runs `.\run.ps1` from repo root (or any location).
- Outbound: `python .\exif_dump.py` then `python .\aiimagepipe.py all`.

run.cmd
- Role: Windows CMD launcher.
- Inbound: user runs `.\run.cmd` from repo root (or any location).
- Outbound: `python .\exif_dump.py` then `python .\aiimagepipe.py all`.

exif_dump.py
- Role: EXIF JSONL dump (ExifTool wrapper).
- Inbound: run directly, or via run.ps1/run.cmd.
- Outbound: calls ExifTool, writes `out/exif_raw.jsonl`.
- Definitions:
  - `build_parser()`: CLI options for input/out/exiftool.
  - `run_exiftool(input_path, exiftool, temp_json)`: runs ExifTool and captures JSON.
  - `json_array_to_jsonl(temp_json, out_jsonl)`: converts JSON array to JSONL.
  - `main()`: resolves repo paths, handles empty input, writes output.

aiimagepipe.py
- Role: Orchestrator wrapper for subcommands.
- Inbound: run directly, or via run.ps1/run.cmd.
- Outbound: imports and calls `normalize_and_ingest.main`, `parse_resources.main`, `resolve_resource_refs.main`.
- Definitions:
  - `_run_module_main(main_func, argv)`: runs another module main with temporary argv.
  - `build_parser()`: defines subcommands ingest/resources/resolve/all.
  - `main()`: resolves paths, dispatches subcommands.

normalize_and_ingest.py
- Role: Ingest EXIF JSONL into SQLite, normalize metadata, and export JSONL/CSV.
- Inbound: run directly or via `aiimagepipe.py`.
- Outbound: reads EXIF JSONL, writes SQLite DB, records.jsonl, records.csv.
- Definitions:
  - `utc_now_iso()`: timestamp helper.
  - `stable_id_for_path(path)`: deterministic ID from repo-relative path.
  - `sha256_file(path)`: file hash.
  - `is_probably_json(s)`: JSON detection.
  - `safe_json_loads(s)`: defensive JSON loads.
  - `first_present(d, keys)`: returns first found key.
  - `clean_ws(s)`: whitespace cleanup.
  - `cut_at_tail_markers(s)`: trims prompt tail markers.
  - `enforce_pos_neg_separation(pos, neg)`: separates pos/neg prompts.
  - `split_tokens_top_level(s)`: splits tokens at top level.
  - `token_norm(t)`: token normalization.
  - `parse_weighted_token(raw)`: parses weighted tokens.
  - `tokenize_prompt(s)`: tokenizes prompt text.
  - `norm_keyish(s)`: normalizes key-like strings.
  - `normalize_sampler(s)`: sampler normalization.
  - `normalize_scheduler(s)`: scheduler normalization.
  - `to_int(x)`: safe int conversion.
  - `to_float(x)`: safe float conversion.
  - `postprocess_prompts_and_params(rec)`: final prompt/param normalization.
  - `extract_candidate_blobs(exif_obj)`: candidate EXIF blobs for parsing.
  - `parse_a1111_parameters(text)`: parses A1111-style parameters.
  - `parse_comfyui_embedded_json(blob)`: parses ComfyUI JSON blob.
  - `normalize_record(exif_obj)`: core record normalization.
  - `init_db(db_path, schema_sql_path)`: initializes DB schema.
  - `upsert_record(conn, rec)`: inserts/updates DB rows.
  - `write_csv(csv_path, records)`: writes CSV export.
  - `main()`: CLI entrypoint for ingest.

parse_resources.py
- Role: Extract resources from workflow JSON/metadata into `resources` table.
- Inbound: run directly or via `aiimagepipe.py`.
- Outbound: reads SQLite DB, writes `resources` rows.
- Definitions:
  - `as_float(x)`: float normalization.
  - `classify_urn(name)`: classify resource type from URN.
  - `iter_node_dicts(workflow)`: iterate workflow nodes.
  - `normalize_class_type(node)`: normalize class type.
  - `get_inputs(node)`: safe inputs extraction.
  - `extract_from_nodes(workflow)`: resource extraction from nodes.
  - `extract_from_extra_airs(workflow)`: extra resources extraction.
  - `extract_from_extra_metadata(workflow)`: extra metadata extraction.
  - `dedupe_resources(items)`: resource dedupe.
  - `ensure_resources_table(conn)`: ensure table exists.
  - `main()`: CLI entrypoint for resource parsing.

resolve_resource_refs.py
- Role: Resolve placeholder resource refs into real resources.
- Inbound: run directly or via `aiimagepipe.py`.
- Outbound: reads SQLite DB, optional mapping JSON/CSV, writes updates.
- Definitions:
  - `ensure_table(conn)`: ensures table exists.
  - `norm_kind(x)`: normalizes resource kinds.
  - `pick_sha256(obj)`: selects sha256 value.
  - `merge_extra_json(existing, patch)`: merges JSON payloads.
  - `upsert_mv(...)`: upserts model version records.
  - `import_manual_map(conn, path)`: imports manual mapping.
  - `iter_dicts_deep(x)`: iterates dicts recursively.
  - `import_civitai_export(conn, path)`: imports CivitAI export.
  - `rewrite_resources(conn)`: rewrites resource refs.
  - `main()`: CLI entrypoint for resource ref resolution.

export_wildcards.py
- Role: Export wildcard text files from DB (tokens/prompts/resources/SQL).
- Inbound: run directly.
- Outbound: reads SQLite DB, writes text files under out/.
- Definitions:
  - `connect(db_path)`: opens SQLite connection.
  - `table_exists(conn, name)`: checks for table existence.
  - `ensure_out_dir(out_path)`: creates output dir.
  - `write_lines(out_path, lines)`: writes newline-delimited file.
  - `apply_filters(items, include_re, exclude_re, min_count, max_count)`: filter helper.
  - `export_tokens(args)`: exports tokens.
  - `export_prompts(args)`: exports prompts.
  - `export_kv(args)`: exports key/value items.
  - `export_resources(args)`: exports resources.
  - `export_sql(args)`: exports arbitrary SQL query results.
  - `build_parser()`: CLI parser.
  - `main()`: CLI entrypoint.

path_utils.py
- Role: Repo-root anchored path resolution.
- Inbound: imported by other scripts.
- Outbound: none.
- Definitions:
  - `_reject_parent_segments(path)`: blocks `..` segments.
  - `resolve_repo_path(path_str, must_exist=False, allow_absolute=False)`: repo-root resolver.
  - `repo_relative(path)`: converts to repo-relative path.
  - `resolve_repo_relative(path_str, ...)`: returns relative + absolute pair.

schema.sql
- Role: SQLite schema used by normalize_and_ingest.py.
- Inbound: read by normalize_and_ingest.py (direct or via aiimagepipe.py).
- Outbound: defines tables, indexes, constraints.

pyproject.toml
- Role: Python project configuration and tool settings.
- Inbound: used by tooling (pytest, build, etc.).
- Outbound: none.

src/TryCode/__init__.py
- Role: Package initialization for TryCode.
- Inbound: imported by tests or python -m TryCode.
- Outbound: none.

src/TryCode/__main__.py
- Role: Module entrypoint for `python -m TryCode`.
- Inbound: `python -m TryCode`.
- Outbound: calls `TryCode.core.main`.

src/TryCode/core.py
- Role: Minimal app function.
- Inbound: called by `__main__.py`.
- Outbound: returns 0.
- Definitions:
  - `main()`: returns 0.

tests/test_core.py
- Role: Test for TryCode main.
- Inbound: `pytest`.
- Outbound: imports `TryCode.core.main`.
