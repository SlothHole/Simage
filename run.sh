#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

py="$repo_root/.venv/bin/python"
if [ ! -x "$py" ]; then
	python -m venv .venv || true
fi
if [ ! -x "$py" ]; then
	py="python"
fi

if "$py" -m pip --version >/dev/null 2>&1; then
	"$py" -m pip install -r simage/ui/requirements.txt
elif "$py" -m ensurepip --upgrade >/dev/null 2>&1 && "$py" -m pip --version >/dev/null 2>&1; then
	"$py" -m pip install -r simage/ui/requirements.txt
else
	echo "pip not available; skipping dependency install."
fi

exiftool="./exiftool-13.45_64/exiftool"
if [ ! -x "$exiftool" ]; then
	exiftool="exiftool"
fi

"$py" -m simage.core.exif --input "./Input" --out "./out/exif_raw.jsonl" --exiftool "$exiftool"
"$py" -m simage all --in "out/exif_raw.jsonl" --db "out/images.db" --schema "simage/data/schema.sql" --jsonl "out/records.jsonl" --csv "out/records.csv"
"$py" -m simage.ui.app
