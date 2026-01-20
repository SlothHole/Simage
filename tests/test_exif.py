import json
import sys
from pathlib import Path

import pytest

from simage.core import exif
from simage.utils.paths import repo_relative


def test_run_exiftool_writes_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    temp_json = tmp_path / "temp.json"
    called = {}

    def fake_run(args, stdout, stderr, check):
        called["args"] = args
        stdout.write(b"[]")
        return 0

    monkeypatch.setattr(exif.subprocess, "run", fake_run)
    exif.run_exiftool(input_dir, "exiftool", temp_json)

    assert temp_json.read_bytes() == b"[]"
    assert called["args"][0] == "exiftool"
    assert "-j" in called["args"]
    assert str(input_dir) in called["args"]


def test_json_array_to_jsonl(tmp_path: Path) -> None:
    temp_json = tmp_path / "in.json"
    out_jsonl = tmp_path / "out.jsonl"
    temp_json.write_text(json.dumps([{"a": 1}, {"b": 2}]), encoding="utf-8")

    count = exif.json_array_to_jsonl(temp_json, out_jsonl)
    assert count == 2
    lines = out_jsonl.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"a": 1}


def test_json_array_to_jsonl_rejects_non_list(tmp_path: Path) -> None:
    temp_json = tmp_path / "bad.json"
    out_jsonl = tmp_path / "out.jsonl"
    temp_json.write_text(json.dumps({"a": 1}), encoding="utf-8")

    with pytest.raises(ValueError):
        exif.json_array_to_jsonl(temp_json, out_jsonl)


def test_main_writes_empty_jsonl_when_no_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    input_dir = tmp_path / "input_empty"
    input_dir.mkdir()
    out_jsonl = tmp_path / "exif_raw.jsonl"

    input_rel = str(repo_relative(input_dir))
    out_rel = str(repo_relative(out_jsonl))

    monkeypatch.setattr(
        sys,
        "argv",
        ["exif", "--input", input_rel, "--out", out_rel, "--exiftool", "exiftool"],
    )

    rc = exif.main()
    assert rc == 0
    assert out_jsonl.exists()
    assert out_jsonl.read_text(encoding="utf-8") == ""
