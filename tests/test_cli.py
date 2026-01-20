from __future__ import annotations

from simage.cli import build_parser


def test_cli_parser_prog() -> None:
    parser = build_parser()
    assert parser.prog == "simage"

