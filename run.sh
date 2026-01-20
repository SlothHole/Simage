#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

if [ ! -d ".venv" ]; then
	python -m venv .venv
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"

pip install -r simage/ui/requirements.txt

exiftool="./exiftool-13.45_64/exiftool"
if [ ! -x "$exiftool" ]; then
	exiftool="exiftool"
fi

python -m simage.core.exif --input "./Input" --out "./out/exif_raw.jsonl" --exiftool "$exiftool"
python -m simage all --in "out/exif_raw.jsonl" --db "out/images.db" --schema "simage/data/schema.sql" --jsonl "out/records.jsonl" --csv "out/records.csv"
python -m simage.ui.app
