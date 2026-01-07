from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from path_utils import resolve_repo_path


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


def json_array_to_jsonl(temp_json: Path, out_jsonl: Path) -> int:
    with temp_json.open("r", encoding="utf-8") as f_in:
        payload = json.load(f_in)

    if not isinstance(payload, list):
        raise ValueError("ExifTool output was not a JSON array.")

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_jsonl.open("w", encoding="utf-8") as f_out:
        for item in payload:
            f_out.write(json.dumps(item, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    args = build_parser().parse_args()

    input_path = resolve_repo_path(args.input, must_exist=True, allow_absolute=False)
    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_path}")

    out_jsonl = resolve_repo_path(args.out, allow_absolute=False)
    out_dir = out_jsonl.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(prefix="exif_", suffix=".json", dir=out_dir, delete=False) as tmp:
        temp_json = Path(tmp.name)

    try:
        run_exiftool(input_path, args.exiftool, temp_json)
        count = json_array_to_jsonl(temp_json, out_jsonl)
    finally:
        if temp_json.exists():
            temp_json.unlink()

    print(f"Wrote JSONL: {out_jsonl}")
    print(f"Files: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
