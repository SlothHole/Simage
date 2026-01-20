#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"

py="$repo_root/.venv/bin/python"
py_is_venv=1
if [ ! -x "$py" ]; then
	python -m venv .venv || true
fi
if [ ! -x "$py" ]; then
	py="python"
	py_is_venv=0
fi

pip_ok=0
if "$py" -m pip --version >/dev/null 2>&1; then
	pip_ok=1
elif "$py" -m ensurepip --upgrade >/dev/null 2>&1 && "$py" -m pip --version >/dev/null 2>&1; then
	pip_ok=1
fi
if [ "$pip_ok" -eq 0 ] && [ "$py_is_venv" -eq 1 ]; then
	echo "pip not available in .venv; falling back to system python."
	py="python"
	py_is_venv=0
	if "$py" -m pip --version >/dev/null 2>&1; then
		pip_ok=1
	elif "$py" -m ensurepip --upgrade >/dev/null 2>&1 && "$py" -m pip --version >/dev/null 2>&1; then
		pip_ok=1
	fi
fi
if [ "$pip_ok" -eq 1 ]; then
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
"$py" -c "import PySide6" >/dev/null 2>&1 || {
	if [ "$pip_ok" -eq 1 ]; then
		"$py" -m pip install -r simage/ui/requirements.txt
		"$py" -c "import PySide6" >/dev/null 2>&1 || {
			echo "PySide6 is not available. Install UI deps or fix pip, then rerun."
			exit 1
		}
	else
		echo "PySide6 is not available. Install UI deps or fix pip, then rerun."
		exit 1
	fi
}
"$py" -m simage.ui.app
