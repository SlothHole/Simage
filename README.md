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

# AIImagePipe - Image Processing and EXIF Management Pipeline

A Python-based image processing pipeline that handles image ingestion, EXIF data extraction, resource normalization, and metadata management.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Usage](#usage)
- [Core Modules](#core-modules)
- [Execution Flow](#execution-flow)
- [Database Schema](#database-schema)
- [Troubleshooting](#troubleshooting)

## Overview

AIImagePipe is a comprehensive image pipeline system designed to:
- Extract and dump EXIF metadata from images
- Normalize and ingest images into a managed database
- Parse and resolve resource references
- Export wildcards for batch processing
- Manage image paths and metadata relationships

## Project Structure

```

├── src/
│   └── TryCode/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # Entry point for package execution
│       └── core.py              # Core pipeline logic
├── tests/
│   └── test_core.py             # Unit tests for core functionality
├── Input/                       # Input directory for source images
├── aiimagepipe.py              # Main application entry point
├── exif_dump.py                # EXIF data extraction utilities
├── export_wildcards.py         # Wildcard export functionality
├── normalize_and_ingest.py     # Image normalization & ingestion
├── parse_resources.py          # Resource parsing logic
├── resolve_resource_refs.py    # Resource reference resolution
├── path_utils.py               # Path manipulation utilities
├── schema.sql                  # Database schema definition
├── pyproject.toml              # Project configuration (Poetry/setuptools)
├── run.cmd                     # Windows batch execution script
├── run.ps1                     # PowerShell execution script
└── README.md                   # This file
```

## Setup & Installation

### Requirements
- Python 3.8+
- Dependencies specified in `pyproject.toml`

### Installation

```bash
# Using pip
pip install -e .

# Or using Poetry
poetry install
```

## Usage

### Running the Pipeline

**Windows (Command Prompt):**
```cmd
run.cmd
```

**Windows (PowerShell):**
```powershell
./run.ps1
```

**Linux/macOS:**
```bash
python -m src.TryCode
```

### Direct Module Execution

```bash
# Extract EXIF data
python exif_dump.py

# Normalize and ingest images
python normalize_and_ingest.py

# Export wildcards
python export_wildcards.py

# Parse resources
python parse_resources.py

# Resolve resource references
python resolve_resource_refs.py
```

## Core Modules

### [aiimagepipe.py](aiimagepipe.py)
Main application entry point. Orchestrates the entire pipeline execution.

### [src/TryCode/__main__.py](src/TryCode/__main__.py)
Package entry point that can be executed via `python -m src.TryCode`.

### [src/TryCode/core.py](src/TryCode/core.py)
Core pipeline logic containing primary processing functions:
- Image processing workflows
- Metadata handling
- Pipeline orchestration

### [exif_dump.py](exif_dump.py)
Extracts and dumps EXIF metadata from images.
- Reads image files from `Input/` directory
- Extracts metadata (camera, lens, ISO, aperture, etc.)
- Outputs formatted EXIF data

### [normalize_and_ingest.py](normalize_and_ingest.py)
Normalizes images and ingests them into the database.
- Validates image formats
- Normalizes metadata
- Stores images and metadata in database

### [parse_resources.py](parse_resources.py)
Parses resource definitions and configurations.
- Reads resource files
- Extracts resource metadata
- Prepares resources for processing

### [resolve_resource_refs.py](resolve_resource_refs.py)
Resolves cross-references between resources.
- Identifies resource relationships
- Links related resources
- Validates reference integrity

### [export_wildcards.py](export_wildcards.py)
Exports wildcard patterns for batch processing.
- Generates wildcard expressions
- Exports batch processing templates

### [path_utils.py](path_utils.py)
Utility functions for path manipulation.
- Normalizes paths across platforms
- Resolves relative/absolute paths
- Manages path conventions

## Execution Flow

```
Entry Point: run.cmd / run.ps1 / python -m src.TryCode
    │
    ├─→ aiimagepipe.py (Main orchestrator)
    │   │
    │   └─→ src/TryCode/__main__.py
    │       │
    │       └─→ src/TryCode/core.py (Core pipeline)
    │           │
    │           ├─→ exif_dump.py
    │           │   ├─ Read images from Input/
    │           │   └─ Extract EXIF metadata
    │           │
    │           ├─→ normalize_and_ingest.py
    │           │   ├─ Validate image formats
    │           │   ├─ Normalize metadata
    │           │   └─ Store in database (schema.sql)
    │           │
    │           ├─→ parse_resources.py
    │           │   └─ Parse resource definitions
    │           │
    │           ├─→ resolve_resource_refs.py
    │           │   └─ Resolve resource relationships
    │           │
    │           └─→ export_wildcards.py
    │               └─ Export batch patterns
    │
    └─→ path_utils.py (Used throughout pipeline)
        └─ Path normalization & resolution
```

## Detailed Function Flow

### Pipeline Initialization
1. Load configuration from `pyproject.toml`
2. Initialize database using `schema.sql`
3. Set up path utilities via `path_utils.py`

### Image Processing Sequence
1. **Input Stage**: Scan `Input/` directory
2. **EXIF Extraction**: `exif_dump.py` → Extract metadata
3. **Normalization**: `normalize_and_ingest.py` → Standardize formats & metadata
4. **Database Ingestion**: Store processed images and metadata
5. **Resource Parsing**: `parse_resources.py` → Parse related resources
6. **Reference Resolution**: `resolve_resource_refs.py` → Link resources
7. **Batch Export**: `export_wildcards.py` → Generate batch patterns

### Testing
```bash
python -m pytest tests/test_core.py -v
```

## Database Schema

Database configuration defined in [`schema.sql`](schema.sql). Includes tables for:
- Image metadata
- EXIF information
- Resource definitions
- Reference mappings

## Configuration

Edit [`pyproject.toml`](pyproject.toml) to configure:
- Package metadata
- Dependencies
- Build configuration
- Entry points

## Troubleshooting

### Issue: Images not found in Input directory
- **Solution**: Ensure `Input/` directory exists and contains image files
- **Path**: Check `path_utils.py` for path resolution logic

### Issue: EXIF extraction fails
- **Solution**: Verify images have EXIF metadata
- **Module**: Review `exif_dump.py` for supported formats

### Issue: Database errors during ingestion
- **Solution**: Verify `schema.sql` is properly initialized
- **Module**: Check `normalize_and_ingest.py` for data validation

### Issue: Resource reference resolution fails
- **Solution**: Ensure all referenced resources exist
- **Module**: Debug with `resolve_resource_refs.py` directly

### Issue: Tests fail
- **Solution**: Run tests with verbose output
  ```bash
  python -m pytest tests/test_core.py -v -s
  ```
- **Test File**: [`tests/test_core.py`](tests/test_core.py)

## Development

### Running in Development Mode
```bash
pip install -e ".[dev]"
```

### Adding New Modules
1. Create module in root or appropriate subdirectory
2. Import in `src/TryCode/core.py`
3. Add tests in `tests/`
4. Update this README

## License

See project documentation for license information.

## Contact & Support

For issues or questions, refer to the troubleshooting section or review the execution flow diagram above.
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
