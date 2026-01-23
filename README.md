# Simage

Local pipeline for extracting AI image metadata and normalizing into SQLite with a full UI.

## Layout

- simage/cli.py: main entrypoint (python -m simage)
- simage/core/exif.py: EXIF JSONL extraction
- simage/core/ingest.py: normalize + ingest into SQLite
- simage/core/resources.py: extract resources from workflow JSON
- simage/core/resolve.py: resolve resource refs
- simage/core/wildcards.py: export wildcard lists
- simage/utils/paths.py: repo-root path helpers
- simage/data/schema.sql: SQLite schema
- simage/ui/: PySide UI
- run.ps1, run.cmd, run.sh: convenience runners (optional)
- Input/: source images
- out/: generated outputs

## Setup

- Python 3.11+
- ExifTool on PATH (or pass --exiftool). Bundled ExifTool is included in `exiftool-13.45_64/`.
- Optional UI deps: simage/ui/requirements.txt

## Run

Preferred: launch the UI and use the built-in buttons for setup and pipeline actions.

```powershell
python -m simage.ui.app
```

Optional convenience runners:

```powershell
.\run.ps1
```

```cmd
run.cmd
```

```bash
chmod +x ./run.sh
./run.sh
```

## Pipeline (CLI, optional)

1) Extract EXIF JSONL

```powershell
python -m simage.core.exif --input Input --out out/exif_raw.jsonl --exiftool .\exiftool-13.45_64\ExifTool.exe
```

2) Ingest + normalize

```powershell
python -m simage ingest --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv
```

3) Parse resources

```powershell
python -m simage resources --db out/images.db
```

4) Resolve resource refs (optional)

```powershell
python -m simage resolve --db out/images.db --rewrite
```

Full pipeline:

```powershell
python -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv
```

## Wildcards

```powershell
python -m simage.core.wildcards tokens --db out/images.db --out out/wildcards/pos_tokens.txt --side pos --min-count 10 --sort count_desc
```

## UI

```powershell
pip install -r simage/ui/requirements.txt
python -m simage.ui.app
```

UI features:
- Gallery & Search: fast thumbnail grid, metadata preview, keyboard navigation, search (including `key:value`), tag filter dropdown, and sort options.
- Gallery controls: thumbnail size/spacing sliders, persistent splitters, and saved display settings in `out/ui_settings.json`.
- Tag Images: manage tags, rename tags, queue tag updates, and maintain a custom tag list (`out/tag_list.json`).
- Batch Processing: import folders into `Input/`, batch tag/rename/move, export metadata JSON, and refresh the pipeline.
- Edit Images: workflow search/anchor tools, editable prompt/model params, image details, and metadata strip actions.
- Settings: display themes/custom colors/font (saved in `out/ui_settings.json`), environment setup, pipeline actions, and restart UI.
- DB Viewer: connect/browse DB, table list tools, SQL editor with history, export to CSV, and copy rows/cells.
- Thumbnail cache: stored in `/.thumbnails` (contents ignored by git).
- Full Image Viewer: placeholder for future tools.

## Tests

```powershell
python -m pytest tests
```


## Change Process (DIFF System)

This repository uses a **DIFF-governed change process** to ensure all modifications are intentional, auditable, and reversible.

### What is a DIFF?

A **DIFF** is a versioned change contract that defines:
- What is allowed to change
- What is explicitly forbidden
- Why the change exists
- How completion is verified

DIFFs are authoritative.  
If a change is not explicitly covered by a DIFF, it must not be made.

---

### DIFF Files

DIFFs live in:

docs/diffs/
DIFF-000.md # Baseline snapshot (read-only)
DIFF-001.md # First change set
DIFF-002.md # Subsequent scoped changes

- **DIFF-000** captures the factual baseline and allows no changes.
- **DIFF-001+** introduce scoped, verified changes.
- Locked DIFFs are never edited.

---

### How Changes Are Made

1. A DIFF is authored by the repo owner.
2. Scope is frozen before implementation.
3. Changes are implemented strictly within DIFF scope.
4. All changes are verified against the DIFF checklist.
5. The DIFF is accepted and locked.

Only one DIFF may be active at a time.

---

### What Is Not Allowed

Unless explicitly permitted by a DIFF:
- Feature movement
- Renaming
- Logic or behavior changes
- Refactors or cleanup
- Styling or redesign
- “While I’m here” improvements

If a change seems necessary but is not covered by a DIFF, it must be discussed before proceeding.

---

### Agents and Automation

This repository may use automated agents to implement DIFFs.  
Agents operate under strict instructions and do not define scope or authorize changes.

All authority remains with the DIFF documents.

---

### Documentation

- `docs/DIFF_PROCESS.md` — DIFF governance rules
- `docs/DIFF_TEMPLATE.md` — Template for authoring new DIFFs
- `docs/AGENT_PROMPT.md` — Execution rules for agents (read-only)

---

### Guiding Principle

> **Intent is explicit.  
> Scope is enforced.  
> Changes are provable.**

If you are unsure whether a change is allowed, assume it is not and ask first.