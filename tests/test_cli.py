from __future__ import annotations

import sys

from simage.cli import _resolve_rel_path, _run_module_main, build_parser


def test_cli_parser_prog() -> None:
    parser = build_parser()
    assert parser.prog == "simage"


def test_run_module_main_restores_argv() -> None:
    seen = []

    def fake_main() -> None:
        seen.append(list(sys.argv))

    original = list(sys.argv)
    _run_module_main(fake_main, ["--foo", "bar"])
    assert seen[0][1:] == ["--foo", "bar"]
    assert sys.argv == original


def test_resolve_rel_path_returns_relative() -> None:
    rel = _resolve_rel_path("README.md", must_exist=True)
    assert rel == "README.md"

