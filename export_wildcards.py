# export_wildcards.py
# Purpose: Export prompts/tokens/resources/kv values (or any SQL query) to a newline-delimited
#          text file suitable for SD/ComfyUI wildcard lists.

import argparse
import os
import re
import sqlite3
from typing import Iterable, List, Optional, Tuple

from path_utils import resolve_repo_path
def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1;", (name,)
    ).fetchone()
    return row is not None

def ensure_out_dir(out_path: str) -> None:
    d = os.path.dirname(out_path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)

def write_lines(out_path: str, lines: Iterable[str]) -> int:
    ensure_out_dir(out_path)
    n = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            line = (line or "").strip()
            if not line:
                continue
            f.write(line + "\n")
            n += 1
    return n

def apply_filters(
    items: Iterable[Tuple[str, int]],
    include_re: Optional[re.Pattern],
    exclude_re: Optional[re.Pattern],
    min_count: int,
    max_count: Optional[int],
) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for text, cnt in items:
        if text is None:
            continue
        t = str(text).strip()
        if not t:
            continue
        if cnt < min_count:
            continue
        if max_count is not None and cnt > max_count:
            continue
        if include_re and not include_re.search(t):
            continue
        if exclude_re and exclude_re.search(t):
            continue
        out.append((t, cnt))
    return out

def export_tokens(args) -> int:
    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)
    out_path = resolve_repo_path(args.out, allow_absolute=False)
    conn = connect(str(db_path))

    include_re = re.compile(args.include, re.IGNORECASE) if args.include else None
    exclude_re = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None

    # Prefer the materialized tokens table (fast)
    if table_exists(conn, "tokens"):
        cols = "t_norm" if args.field == "t_norm" else "t"
        side_clause = ""
        params: List[str] = []
        if args.side in ("pos", "neg"):
            side_clause = "WHERE side=?"
            params.append(args.side)

        sql = f"""
            SELECT {cols} AS s, COUNT(*) AS n
            FROM tokens
            {side_clause}
            GROUP BY {cols}
        """
        rows = conn.execute(sql, params).fetchall()
        items = [(r["s"], int(r["n"])) for r in rows]
    else:
        # Fallback: derive from kv JSON (slower; only used if tokens table doesn't exist)
        # prompt_tokens / neg_tokens stored in kv.v_json
        sides = []
        if args.side in ("pos", "both"):
            sides.append(("prompt_tokens", "pos"))
        if args.side in ("neg", "both"):
            sides.append(("neg_tokens", "neg"))

        items = []
        for k_name, _side in sides:
            sql = f"""
                SELECT
                  json_extract(je.value, '$.{args.field}') AS s,
                  COUNT(*) AS n
                FROM kv
                JOIN json_each(kv.v_json) je
                WHERE kv.k = ?
                  AND kv.v_json IS NOT NULL
                  AND json_extract(je.value, '$.{args.field}') IS NOT NULL
                GROUP BY s
            """
            rows = conn.execute(sql, (k_name,)).fetchall()
            items.extend([(r["s"], int(r["n"])) for r in rows])

        # If we combined both sides in fallback, merge counts by string
        merged = {}
        for s, n in items:
            if s is None:
                continue
            merged[s] = merged.get(s, 0) + n
        items = list(merged.items())

    filtered = apply_filters(items, include_re, exclude_re, args.min_count, args.max_count)

    # Sorting
    if args.sort == "count_desc":
        filtered.sort(key=lambda x: (-x[1], x[0].lower()))
    elif args.sort == "count_asc":
        filtered.sort(key=lambda x: (x[1], x[0].lower()))
    else:  # alpha
        filtered.sort(key=lambda x: x[0].lower())

    if args.limit is not None:
        filtered = filtered[: args.limit]

    # Formatting
    def fmt(token: str, cnt: int) -> str:
        if args.with_count:
            return f"{token}\t{cnt}"
        return token

    n = write_lines(str(out_path), (fmt(t, c) for t, c in filtered))
    print(f"Wrote {n} lines -> {out_path}")
    return 0

def export_prompts(args) -> int:
    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)
    out_path = resolve_repo_path(args.out, allow_absolute=False)
    conn = connect(str(db_path))
    include_re = re.compile(args.include, re.IGNORECASE) if args.include else None
    exclude_re = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None

    keys = []
    if args.which in ("pos", "both"):
        keys.append("prompt_text")
    if args.which in ("neg", "both"):
        keys.append("neg_prompt_text")

    items: List[Tuple[str, int]] = []
    for k in keys:
        rows = conn.execute(
            "SELECT v AS s, COUNT(*) AS n FROM kv WHERE k=? AND v IS NOT NULL AND trim(v)<>'' GROUP BY v;",
            (k,),
        ).fetchall()
        items.extend([(r["s"], int(r["n"])) for r in rows])

    filtered = apply_filters(items, include_re, exclude_re, args.min_count, args.max_count)

    # sort by count by default for prompts (more useful)
    if args.sort == "count_desc":
        filtered.sort(key=lambda x: (-x[1], x[0][:80].lower()))
    elif args.sort == "alpha":
        filtered.sort(key=lambda x: x[0].lower())
    else:
        filtered.sort(key=lambda x: (-x[1], x[0][:80].lower()))

    if args.limit is not None:
        filtered = filtered[: args.limit]

    def fmt(s: str, cnt: int) -> str:
        if args.with_count:
            return f"{s}\t{cnt}"
        return s

    n = write_lines(str(out_path), (fmt(t, c) for t, c in filtered))
    print(f"Wrote {n} lines -> {out_path}")
    return 0

def export_kv(args) -> int:
    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)
    out_path = resolve_repo_path(args.out, allow_absolute=False)
    conn = connect(str(db_path))
    include_re = re.compile(args.include, re.IGNORECASE) if args.include else None
    exclude_re = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None

    col = "v" if args.column == "v" else "v_num"
    where_num = "AND v_num IS NOT NULL" if col == "v_num" else "AND v IS NOT NULL AND trim(v)<>''"

    rows = conn.execute(
        f"SELECT {col} AS s, COUNT(*) AS n FROM kv WHERE k=? {where_num} GROUP BY {col};",
        (args.key,),
    ).fetchall()
    items = [(r["s"], int(r["n"])) for r in rows]

    filtered = apply_filters(items, include_re, exclude_re, args.min_count, args.max_count)

    if args.sort == "count_desc":
        filtered.sort(key=lambda x: (-x[1], str(x[0]).lower()))
    elif args.sort == "alpha":
        filtered.sort(key=lambda x: str(x[0]).lower())
    else:
        filtered.sort(key=lambda x: (-x[1], str(x[0]).lower()))

    if args.limit is not None:
        filtered = filtered[: args.limit]

    def fmt(v, cnt: int) -> str:
        s = str(v).strip()
        if args.with_count:
            return f"{s}\t{cnt}"
        return s

    n = write_lines(str(out_path), (fmt(t, c) for t, c in filtered))
    print(f"Wrote {n} lines -> {out_path}")
    return 0

def export_resources(args) -> int:
    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)
    out_path = resolve_repo_path(args.out, allow_absolute=False)
    conn = connect(str(db_path))
    include_re = re.compile(args.include, re.IGNORECASE) if args.include else None
    exclude_re = re.compile(args.exclude, re.IGNORECASE) if args.exclude else None

    # Group by name (and optionally weight) to avoid spamming duplicates
    if args.with_weight:
        rows = conn.execute(
            """
            SELECT name AS s,
                   COALESCE(weight, 1.0) AS w,
                   COUNT(*) AS n
            FROM resources
            WHERE kind=?
            GROUP BY name, COALESCE(weight, 1.0);
            """,
            (args.kind,),
        ).fetchall()
        items = [(f"{r['s']}:{float(r['w']):.3f}", int(r["n"])) for r in rows]
    else:
        rows = conn.execute(
            "SELECT name AS s, COUNT(*) AS n FROM resources WHERE kind=? GROUP BY name;",
            (args.kind,),
        ).fetchall()
        items = [(r["s"], int(r["n"])) for r in rows]

    filtered = apply_filters(items, include_re, exclude_re, args.min_count, args.max_count)

    if args.sort == "count_desc":
        filtered.sort(key=lambda x: (-x[1], x[0].lower()))
    else:
        filtered.sort(key=lambda x: x[0].lower())

    if args.limit is not None:
        filtered = filtered[: args.limit]

    def fmt(s: str, cnt: int) -> str:
        if args.with_count:
            return f"{s}\t{cnt}"
        return s

    n = write_lines(str(out_path), (fmt(t, c) for t, c in filtered))
    print(f"Wrote {n} lines -> {out_path}")
    return 0

def export_sql(args) -> int:
    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)
    out_path = resolve_repo_path(args.out, allow_absolute=False)
    conn = connect(str(db_path))
    rows = conn.execute(args.sql).fetchall()
    if not rows:
        write_lines(str(out_path), [])
        print(f"Wrote 0 lines -> {out_path}")
        return 0

    # Take first column of each row
    first_key = rows[0].keys()[0]
    lines = (str(r[first_key]) for r in rows if r[first_key] is not None)
    n = write_lines(str(out_path), lines)
    print(f"Wrote {n} lines -> {out_path}")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export wildcards (.txt) from AIImageMetaPipe SQLite DB.")
    sub = p.add_subparsers(dest="cmd", required=True)

    # tokens
    pt = sub.add_parser("tokens", help="Export distinct tokens (from tokens table if present).")
    pt.add_argument("--db", required=True, help="Path to SQLite DB (e.g. .\\out\\images.db)")
    pt.add_argument("--out", required=True, help="Output .txt path")
    pt.add_argument("--side", choices=["pos", "neg", "both"], default="pos")
    pt.add_argument("--field", choices=["t", "t_norm"], default="t_norm")
    pt.add_argument("--min-count", type=int, default=1)
    pt.add_argument("--max-count", type=int, default=None)
    pt.add_argument("--include", default=None, help="Regex include filter")
    pt.add_argument("--exclude", default=None, help="Regex exclude filter")
    pt.add_argument("--sort", choices=["alpha", "count_desc", "count_asc"], default="count_desc")
    pt.add_argument("--limit", type=int, default=None)
    pt.add_argument("--with-count", action="store_true", help="Append tab + count per line")
    pt.set_defaults(func=export_tokens)

    # prompts
    pp = sub.add_parser("prompts", help="Export prompt_text / neg_prompt_text lines.")
    pp.add_argument("--db", required=True)
    pp.add_argument("--out", required=True)
    pp.add_argument("--which", choices=["pos", "neg", "both"], default="pos")
    pp.add_argument("--min-count", type=int, default=1)
    pp.add_argument("--max-count", type=int, default=None)
    pp.add_argument("--include", default=None)
    pp.add_argument("--exclude", default=None)
    pp.add_argument("--sort", choices=["count_desc", "alpha"], default="count_desc")
    pp.add_argument("--limit", type=int, default=None)
    pp.add_argument("--with-count", action="store_true")
    pp.set_defaults(func=export_prompts)

    # kv
    pk = sub.add_parser("kv", help="Export distinct values for any kv key.")
    pk.add_argument("--db", required=True)
    pk.add_argument("--out", required=True)
    pk.add_argument("--key", required=True, help="kv.k to export (e.g. sampler_norm, model)")
    pk.add_argument("--column", choices=["v", "v_num"], default="v")
    pk.add_argument("--min-count", type=int, default=1)
    pk.add_argument("--max-count", type=int, default=None)
    pk.add_argument("--include", default=None)
    pk.add_argument("--exclude", default=None)
    pk.add_argument("--sort", choices=["count_desc", "alpha"], default="count_desc")
    pk.add_argument("--limit", type=int, default=None)
    pk.add_argument("--with-count", action="store_true")
    pk.set_defaults(func=export_kv)

    # resources
    pr = sub.add_parser("resources", help="Export resources table entries by kind.")
    pr.add_argument("--db", required=True)
    pr.add_argument("--out", required=True)
    pr.add_argument("--kind", required=True, help="checkpoint|lora|embedding|vae|upscaler (or any kind you use)")
    pr.add_argument("--with-weight", action="store_true", help="Include :weight in output")
    pr.add_argument("--min-count", type=int, default=1)
    pr.add_argument("--max-count", type=int, default=None)
    pr.add_argument("--include", default=None)
    pr.add_argument("--exclude", default=None)
    pr.add_argument("--sort", choices=["alpha", "count_desc"], default="count_desc")
    pr.add_argument("--limit", type=int, default=None)
    pr.add_argument("--with-count", action="store_true")
    pr.set_defaults(func=export_resources)

    # sql (escape hatch: export anything)
    ps = sub.add_parser("sql", help="Export first column of an arbitrary SQL query (escape hatch).")
    ps.add_argument("--db", required=True)
    ps.add_argument("--out", required=True)
    ps.add_argument("--sql", required=True, help="SQL that returns 1+ columns; first column is written.")
    ps.set_defaults(func=export_sql)

    return p

def main() -> int:
    p = build_parser()
    args = p.parse_args()
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
