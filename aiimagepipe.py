"""
aiimagepipe.py

A single entrypoint that combines the three scripts in this repo:

  - normalize_and_ingest.py
  - parse_resources.py
  - resolve_resource_refs.py

It DOES NOT duplicate their logic; it simply orchestrates them with subcommands,
so you only have to remember one command.

Run from (example):
  .

Examples:

  # 1) Ingest EXIF JSONL -> images + kv
  python .\aiimagepipe.py ingest --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv

  # 2) Extract resources from workflow_json in kv -> resources table
  python .\aiimagepipe.py resources --db .\out\images.db

  # 3) Resolve modelVersionId refs (if you have a mapping file)
  python .\aiimagepipe.py resolve --db .\out\images.db --import-map .\civitai_map.json --rewrite

  # 4) Full pipeline (ingest -> resources -> resolve)
  python .\aiimagepipe.py all --in .\out\exif_raw.jsonl --db .\out\images.db --schema .\schema.sql --jsonl .\out\records.jsonl --csv .\out\records.csv --import-map .\civitai_map.json --rewrite

Notes:
- If you don't have a mapping file/export for resolve, you can omit --import-map/--import-json.
  The resolve step will still ensure civitai_model_versions exists, but it won't rewrite anything.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, List, Optional


def _run_module_main(main_func: Callable[[], None], argv: List[str]) -> None:
    """
    Call an existing script's main() by temporarily overriding sys.argv.
    This avoids subprocess and keeps everything in one Python process.
    """
    old = sys.argv[:]
    try:
        sys.argv = [old[0]] + argv
        main_func()
    finally:
        sys.argv = old


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aiimagepipe", add_help=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    # ingest
    p_ing = sub.add_parser("ingest", help="Run normalize_and_ingest.py (EXIF JSONL -> images + kv)")
    p_ing.add_argument("--in", dest="in_jsonl", required=True, help="Input exif_raw.jsonl (one JSON per line)")
    p_ing.add_argument("--db", dest="db_path", required=True, help="Path to images.db")
    p_ing.add_argument("--schema", dest="schema_path", default="schema.sql", help="Path to schema.sql")
    p_ing.add_argument("--jsonl", dest="out_jsonl", required=True, help="Output records.jsonl")
    p_ing.add_argument("--csv", dest="out_csv", required=True, help="Output records.csv")

    # resources
    p_res = sub.add_parser("resources", help="Run parse_resources.py (workflow_json -> resources table)")
    p_res.add_argument("--db", required=True, help="Path to images.db")
    p_res.add_argument("--limit", type=int, default=0, help="Optional limit for testing (0 = no limit)")

    # resolve
    p_sol = sub.add_parser("resolve", help="Run resolve_resource_refs.py (resolve resource_ref modelVersionId)")
    p_sol.add_argument("--db", required=True, help="Path to images.db")
    p_sol.add_argument("--import-json", dest="import_json", default="", help="Path to CivitAI export/dump JSON")
    p_sol.add_argument("--import-map", dest="import_map", default="", help="Path to manual mapping file (.json or .csv)")
    p_sol.add_argument("--rewrite", action="store_true", help="Rewrite resources.resource_ref into resolved resources")

    # all
    p_all = sub.add_parser("all", help="Run ingest -> resources -> resolve in one go")
    p_all.add_argument("--in", dest="in_jsonl", required=True, help="Input exif_raw.jsonl (one JSON per line)")
    p_all.add_argument("--db", dest="db_path", required=True, help="Path to images.db")
    p_all.add_argument("--schema", dest="schema_path", default="schema.sql", help="Path to schema.sql")
    p_all.add_argument("--jsonl", dest="out_jsonl", required=True, help="Output records.jsonl")
    p_all.add_argument("--csv", dest="out_csv", required=True, help="Output records.csv")
    p_all.add_argument("--limit", type=int, default=0, help="Optional limit for resource parsing (0 = no limit)")
    p_all.add_argument("--import-json", dest="import_json", default="", help="Path to CivitAI export/dump JSON")
    p_all.add_argument("--import-map", dest="import_map", default="", help="Path to manual mapping file (.json or .csv)")
    p_all.add_argument("--rewrite", action="store_true", help="Rewrite resources.resource_ref into resolved resources")

    return p


def main() -> None:
    args = build_parser().parse_args()

    # Import lazily so this file can show help even if modules have issues.
    import normalize_and_ingest
    import parse_resources
    import resolve_resource_refs

    if args.cmd == "ingest":
        _run_module_main(
            normalize_and_ingest.main,
            ["--in", args.in_jsonl, "--db", args.db_path, "--schema", args.schema_path, "--jsonl", args.out_jsonl, "--csv", args.out_csv],
        )
        return

    if args.cmd == "resources":
        argv = ["--db", args.db]
        if args.limit and args.limit > 0:
            argv += ["--limit", str(args.limit)]
        _run_module_main(parse_resources.main, argv)
        return

    if args.cmd == "resolve":
        argv = ["--db", args.db]
        if args.import_json:
            argv += ["--import-json", args.import_json]
        if args.import_map:
            argv += ["--import-map", args.import_map]
        if args.rewrite:
            argv += ["--rewrite"]
        _run_module_main(resolve_resource_refs.main, argv)
        return

    if args.cmd == "all":
        _run_module_main(
            normalize_and_ingest.main,
            ["--in", args.in_jsonl, "--db", args.db_path, "--schema", args.schema_path, "--jsonl", args.out_jsonl, "--csv", args.out_csv],
        )
        _run_module_main(parse_resources.main, ["--db", args.db_path] + (["--limit", str(args.limit)] if args.limit and args.limit > 0 else []))

        argv = ["--db", args.db_path]
        if args.import_json:
            argv += ["--import-json", args.import_json]
        if args.import_map:
            argv += ["--import-map", args.import_map]
        if args.rewrite:
            argv += ["--rewrite"]
        _run_module_main(resolve_resource_refs.main, argv)
        return


if __name__ == "__main__":
    main()
