# Simage

Local pipeline for extracting AI image metadata and normalizing into SQLite.

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
- run.ps1, run.cmd, run.sh: convenience runners
- Input/: source images
- out/: generated outputs

## Setup

- Python 3.11+
- ExifTool on PATH (or pass --exiftool). Bundled ExifTool is included in `exiftool-13.45_64/`.
- Optional UI deps: simage/ui/requirements.txt

## Run

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

## Pipeline

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
- Import: copy images recursively from a chosen folder into `Input/`.
- Refresh: reruns EXIF + full pipeline for newly imported images.
- Gallery: keeps thumbnails for missing originals (missing images still show).
- DB Viewer tab: run read-only SQL against `out/images.db`.
- Thumbnail cache: stored in `/.thumbnails` (contents ignored by git).

## Tests

```powershell
python -m pytest tests
```
