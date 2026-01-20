from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from simage.utils.paths import resolve_repo_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ExifTool and convert its JSON output to JSONL.")
    parser.add_argument("--input", default="Input", help="Input directory under repo root.")
    parser.add_argument("--out", default="out/exif_raw.jsonl", help="Output JSONL path under repo root.")
    parser.add_argument("--exiftool", default="exiftool", help="ExifTool executable name or path.")
    return parser


def run_exiftool(input_path: Path, exiftool: str, temp_json: Path) -> None:
    with temp_json.open("wb") as f_out:
        subprocess.run(
            [
                exiftool,
                "-r",
                "-a",
                "-G1",
                "-s",
                "-n",
                "-charset",
                "utf8",
                "-api",
                "largefilesupport=1",
                "-j",
                str(input_path),
            ],
            stdout=f_out,
            stderr=subprocess.DEVNULL,
            check=True,
        )


def _record_key(item: dict) -> str:
    src = item.get("SourceFile") or item.get("File:FileName") or item.get("FileName") or ""
    if not isinstance(src, str):
        return ""
    return src.replace("\\", "/").lower().strip()


def _load_existing_keys(out_jsonl: Path) -> set[str]:
    if not out_jsonl.exists():
        return set()
    keys = set()
    with out_jsonl.open("r", encoding="utf-8") as f_in:
        for line in f_in:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            key = _record_key(item)
            if key:
                keys.add(key)
    return keys


def _ensure_trailing_newline(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("rb+") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) != b"\n":
            f.write(b"\n")


def append_new_jsonl(temp_json: Path, out_jsonl: Path) -> int:
    with temp_json.open("r", encoding="utf-8") as f_in:
        payload = json.load(f_in)

    if not isinstance(payload, list):
        raise ValueError("ExifTool output was not a JSON array.")

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_existing_keys(out_jsonl)
    _ensure_trailing_newline(out_jsonl)

    count = 0
    with out_jsonl.open("a", encoding="utf-8") as f_out:
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = _record_key(item)
            if key and key in existing:
                continue
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")
            if key:
                existing.add(key)
            count += 1
    return count


def main() -> int:
    args = build_parser().parse_args()

    input_path = resolve_repo_path(args.input, must_exist=False, allow_absolute=False)
    if not input_path.exists():
        input_path.mkdir(parents=True, exist_ok=True)
    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_path}")

    out_jsonl = resolve_repo_path(args.out, allow_absolute=False)
    out_dir = out_jsonl.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    has_files = any(p.is_file() for p in input_path.rglob("*"))
    if not has_files:
        if not out_jsonl.exists():
            out_jsonl.write_text("", encoding="utf-8")
            print(f"No input files found in {input_path}. Wrote empty JSONL: {out_jsonl}")
        else:
            print(f"No input files found in {input_path}. Leaving existing JSONL unchanged.")
        return 0

    with tempfile.NamedTemporaryFile(prefix="exif_", suffix=".json", dir=out_dir, delete=False) as tmp:
        temp_json = Path(tmp.name)

    try:
        run_exiftool(input_path, args.exiftool, temp_json)
        count = append_new_jsonl(temp_json, out_jsonl)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"ExifTool not found ({args.exiftool}). Install exiftool or provide --exiftool path."
        ) from exc
    finally:
        if temp_json.exists():
            temp_json.unlink()

    if count:
        print(f"Appended {count} new record(s) to JSONL: {out_jsonl}")
    else:
        print(f"No new records found. JSONL unchanged: {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
