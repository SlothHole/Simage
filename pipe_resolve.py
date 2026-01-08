"""
resolve_resource_refs.py

Goal:
  Resolve resources.kind='resource_ref' + name like 'modelVersionId:####'
  into real resources (checkpoint / lora / embedding / etc.) using a lookup
  table civitai_model_versions.

What it does:
  1) Ensures table civitai_model_versions exists
  2) Imports mapping from ONE of:
       - a CivitAI export/dump JSON (best-effort parse of common shapes)
       - a manual mapping file (JSON or CSV)
  3) Rewrites resources rows where kind='resource_ref' into resolved rows:
       resources.kind = resolved kind
       resources.name = resolved urn or display name
       resources.hash = resolved sha256 (if present)
       extra_json keeps original resource_ref for traceability

PowerShell examples (run from your project directory):
  python .\resolve_resource_refs.py --db .\out\images.db --import-json .\civitai_export.json
  python .\resolve_resource_refs.py --db .\out\images.db --import-map  .\civitai_map.json
  python .\resolve_resource_refs.py --db .\out\images.db --import-map  .\civitai_map.csv
  python .\resolve_resource_refs.py --db .\out\images.db --rewrite
  python .\resolve_resource_refs.py --db .\out\images.db --import-json .\civitai_export.json --rewrite
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from simage.path_utils import resolve_repo_path

RE_MVID = re.compile(r"^modelVersionId:(\d+)$", re.IGNORECASE)


# ---------------- DB schema ----------------

def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("""
      CREATE TABLE IF NOT EXISTS civitai_model_versions(
        model_version_id INTEGER PRIMARY KEY,
        kind TEXT,
        name TEXT,
        urn TEXT,
        sha256 TEXT,
        extra_json TEXT
      );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_civitai_mv_sha256 ON civitai_model_versions(sha256);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_civitai_mv_urn    ON civitai_model_versions(urn);")


# ---------------- utilities ----------------

def norm_kind(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower()
    if not s:
        return None

    # Common CivitAI-ish / ecosystem variants -> your normalized kinds
    mapping = {
        "checkpoint": "checkpoint",
        "model": "checkpoint",
        "ckpt": "checkpoint",
        "lora": "lora",
        "locon": "lora",
        "lycoris": "lora",
        "embedding": "embedding",
        "textualinversion": "embedding",
        "textual inversion": "embedding",
        "ti": "embedding",
        "vae": "vae",
        "controlnet": "controlnet",
        "upscaler": "upscaler",
    }

    # Try direct
    if s in mapping:
        return mapping[s]

    # Heuristic contains
    if "lora" in s or "lycoris" in s or "locon" in s:
        return "lora"
    if "embed" in s or "textual" in s or "inversion" in s:
        return "embedding"
    if "vae" in s:
        return "vae"
    if "control" in s and "net" in s:
        return "controlnet"
    if "upscal" in s:
        return "upscaler"
    if "checkpoint" in s or "ckpt" in s or "model" == s:
        return "checkpoint"

    return None


def pick_sha256(obj: Any) -> Optional[str]:
    """
    Best-effort sha256 extractor from various shapes:
      - {"hashes":{"SHA256":"..."}} or {"hashes":{"sha256":"..."}}
      - {"sha256":"..."}
      - {"hash":"..."} (only if it looks like sha256)
    """
    def looks_sha256(s: str) -> bool:
        s = s.strip().lower()
        return len(s) == 64 and all(c in "0123456789abcdef" for c in s)

    if isinstance(obj, dict):
        for k in ("sha256", "SHA256"):
            v = obj.get(k)
            if isinstance(v, str) and looks_sha256(v):
                return v.lower()

        hashes = obj.get("hashes")
        if isinstance(hashes, dict):
            for k in ("sha256", "SHA256"):
                v = hashes.get(k)
                if isinstance(v, str) and looks_sha256(v):
                    return v.lower()

        v = obj.get("hash")
        if isinstance(v, str) and looks_sha256(v):
            return v.lower()

    return None


def merge_extra_json(existing: Optional[str], patch: Dict[str, Any]) -> str:
    base: Dict[str, Any] = {}
    if existing:
        try:
            loaded = json.loads(existing)
            if isinstance(loaded, dict):
                base = loaded
        except Exception:
            base = {"_raw_extra_json": existing}

    # non-destructive merge
    for k, v in patch.items():
        if k not in base:
            base[k] = v
        else:
            # if collision, keep both in a list
            if base[k] == v:
                continue
            if isinstance(base[k], list):
                if v not in base[k]:
                    base[k].append(v)
            else:
                base[k] = [base[k], v]

    return json.dumps(base, ensure_ascii=False)


# ---------------- import sources ----------------

def upsert_mv(
    conn: sqlite3.Connection,
    model_version_id: int,
    kind: Optional[str],
    name: Optional[str],
    urn: Optional[str],
    sha256: Optional[str],
    extra: Optional[Dict[str, Any]],
) -> None:
    conn.execute(
        """
        INSERT INTO civitai_model_versions(model_version_id, kind, name, urn, sha256, extra_json)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(model_version_id) DO UPDATE SET
          kind=COALESCE(excluded.kind, civitai_model_versions.kind),
          name=COALESCE(excluded.name, civitai_model_versions.name),
          urn =COALESCE(excluded.urn,  civitai_model_versions.urn),
          sha256=COALESCE(excluded.sha256, civitai_model_versions.sha256),
          extra_json=COALESCE(excluded.extra_json, civitai_model_versions.extra_json)
        """,
        (
            int(model_version_id),
            kind,
            name,
            urn,
            sha256,
            json.dumps(extra, ensure_ascii=False) if extra is not None else None,
        ),
    )


def import_manual_map(conn: sqlite3.Connection, path: str) -> int:
    """
    Supports:
      JSON: list of {model_version_id, kind, name, urn, sha256, extra...}
      CSV : columns model_version_id, kind, name, urn, sha256 (extras ignored)
    """
    map_path = resolve_repo_path(path, must_exist=True, allow_absolute=False)

    n = 0
    _, ext = os.path.splitext(str(map_path).lower())

    if ext == ".csv":
        with open(map_path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                mvid = row.get("model_version_id") or row.get("modelVersionId") or row.get("mvid")
                if not mvid:
                    continue
                kind = norm_kind(row.get("kind"))
                name = row.get("name")
                urn = row.get("urn")
                sha = row.get("sha256")
                extra = {"source": "manual_csv"}
                upsert_mv(conn, int(mvid), kind, name, urn, sha.lower() if isinstance(sha, str) else None, extra)
                n += 1
        return n

    # default JSON
    with open(map_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    items: List[Dict[str, Any]] = []
    if isinstance(obj, list):
        items = [x for x in obj if isinstance(x, dict)]
    elif isinstance(obj, dict):
        # allow {"items":[...]} or {"data":[...]}
        for k in ("items", "data", "models", "versions"):
            v = obj.get(k)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break

    for it in items:
        mvid = it.get("model_version_id") or it.get("modelVersionId") or it.get("id")
        if mvid is None:
            continue
        kind = norm_kind(it.get("kind") or it.get("type"))
        name = it.get("name") or it.get("displayName") or it.get("title")
        urn = it.get("urn")
        sha = pick_sha256(it) or pick_sha256(it.get("file")) or pick_sha256(it.get("files"))
        extra = dict(it)
        extra["source"] = "manual_json"
        upsert_mv(conn, int(mvid), kind, name, urn, sha, extra)
        n += 1

    return n


def iter_dicts_deep(x: Any) -> Iterable[Dict[str, Any]]:
    """
    Walk a JSON object and yield dicts. This is intentionally brute-force:
    it lets us parse many unknown export formats with minimal assumptions.
    """
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from iter_dicts_deep(v)
    elif isinstance(x, list):
        for item in x:
            yield from iter_dicts_deep(item)


def import_civitai_export(conn: sqlite3.Connection, path: str) -> int:
    """
    Best-effort import from a CivitAI export/dump JSON.
    We search deeply for dicts that look like "model version" records.
    """
    export_path = resolve_repo_path(path, must_exist=True, allow_absolute=False)

    with open(export_path, "r", encoding="utf-8") as f:
        root = json.load(f)

    n = 0
    seen: set[int] = set()

    for d in iter_dicts_deep(root):
        # Candidate ID fields
        mvid = d.get("modelVersionId")
        if mvid is None:
            # sometimes modelVersion is itself an object
            mv = d.get("modelVersion")
            if isinstance(mv, dict) and mv.get("id") is not None:
                mvid = mv.get("id")
                # let "d" become that modelVersion dict
                d = mv
            else:
                # common "id" for a version object
                if isinstance(d.get("id"), int) and ("trainedWords" in d or "files" in d or "baseModel" in d):
                    mvid = d.get("id")

        if mvid is None:
            continue

        try:
            mvid_int = int(mvid)
        except Exception:
            continue

        if mvid_int in seen:
            continue

        # Heuristics to confirm it's probably a version record
        looks_like_version = any(k in d for k in ("files", "trainedWords", "baseModel", "downloadUrl", "images"))
        if not looks_like_version:
            continue

        seen.add(mvid_int)

        kind = norm_kind(d.get("type") or d.get("modelType") or d.get("kind"))
        name = d.get("name") or d.get("title") or d.get("model", {}).get("name") if isinstance(d.get("model"), dict) else None

        # URN may not exist in export; we can synthesize a stable-ish one:
        urn = d.get("urn")
        if not urn:
            # best-effort: civitai model id + version id
            model_id = None
            m = d.get("model")
            if isinstance(m, dict):
                model_id = m.get("id")
            if model_id is None:
                model_id = d.get("modelId")
            if model_id is not None:
                urn = f"urn:civitai:model:{model_id}:version:{mvid_int}"
            else:
                urn = f"urn:civitai:modelVersion:{mvid_int}"

        sha = None
        files = d.get("files")
        if isinstance(files, list):
            # choose first sha256 we can find
            for fobj in files:
                sha = pick_sha256(fobj)
                if sha:
                    break
        if not sha:
            sha = pick_sha256(d)

        extra = dict(d)
        extra["source"] = "civitai_export_best_effort"
        upsert_mv(conn, mvid_int, kind, name, urn, sha, extra)
        n += 1

    return n


# ---------------- rewrite pass ----------------

def rewrite_resources(conn: sqlite3.Connection) -> Tuple[int, int]:
    """
    Rewrites resources where kind='resource_ref' and name='modelVersionId:####'
    Returns: (rows_scanned, rows_rewritten)
    """
    rows = conn.execute(
        """
        SELECT rowid, image_id, kind, name, hash, extra_json, weight
        FROM resources
        WHERE kind='resource_ref' AND name LIKE 'modelVersionId:%'
        """
    ).fetchall()

    rewritten = 0

    for r in rows:
        rowid = r["rowid"]
        name = r["name"] or ""
        m = RE_MVID.match(name.strip())
        if not m:
            continue

        mvid = int(m.group(1))
        mv = conn.execute(
            "SELECT model_version_id, kind, name, urn, sha256, extra_json FROM civitai_model_versions WHERE model_version_id=?",
            (mvid,),
        ).fetchone()

        if not mv:
            continue  # unresolved, leave as-is

        resolved_kind = mv["kind"] or "unknown"
        resolved_name = mv["urn"] or mv["name"] or f"modelVersionId:{mvid}"
        resolved_hash = mv["sha256"] or r["hash"]

        # keep original trace
        trace = {
            "resource_ref": {
                "original_kind": r["kind"],
                "original_name": r["name"],
                "original_hash": r["hash"],
                "model_version_id": mvid,
            }
        }

        new_extra = merge_extra_json(r["extra_json"], trace)

        conn.execute(
            """
            UPDATE resources
            SET kind=?, name=?, hash=?, extra_json=?
            WHERE rowid=?
            """,
            (resolved_kind, resolved_name, resolved_hash, new_extra, rowid),
        )
        rewritten += 1

    return (len(rows), rewritten)


# ---------------- main ----------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to images.db")
    ap.add_argument("--import-json", dest="import_json", default="", help="Path to CivitAI export/dump JSON")
    ap.add_argument("--import-map", dest="import_map", default="", help="Path to manual mapping file (.json or .csv)")
    ap.add_argument("--rewrite", action="store_true", help="Rewrite resources.resource_ref into resolved resources")
    args = ap.parse_args()

    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_table(conn)

        imported = 0
        if args.import_json:
            n = import_civitai_export(conn, args.import_json)
            imported += n
            print(f"Imported from CivitAI export: {n}")

        if args.import_map:
            n = import_manual_map(conn, args.import_map)
            imported += n
            print(f"Imported from manual map: {n}")

        if imported:
            conn.commit()

        if args.rewrite:
            scanned, rewritten = rewrite_resources(conn)
            conn.commit()
            print(f"resource_ref scanned: {scanned}")
            print(f"resource_ref rewritten: {rewritten}")

        if not (args.import_json or args.import_map or args.rewrite):
            print("Nothing to do. Use --import-json and/or --import-map and/or --rewrite.")


if __name__ == "__main__":
    main()
