"""
parse_resources.py

Purpose:
  Read ComfyUI workflow JSON stored in SQLite (kv.k='workflow_json', kv.v_json),
  extract resources (checkpoint / lora / upscaler / controlnet / vae / embedding),
  and populate the `resources` table.

Run in PowerShell from this directory (repository root):
  .

Example:
  python .\parse_resources.py --db .\out\images.db

Optional quick test:
  python .\parse_resources.py --db .\out\images.db --limit 25
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from typing import Any, Dict, Iterable, List, Optional, Tuple

from path_utils import resolve_repo_path

# ----------------- small helpers -----------------

def as_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def classify_urn(name: str) -> Optional[str]:
    """
    Classify a URN-ish resource string into a kind.
    Example formats seen:
      urn:air:sdxl:checkpoint:civitai:...@...
      urn:air:sdxl:lora:civitai:...@...
      urn:air:other:upscaler:civitai:...@...
    """
    n = name.lower()

    if ":checkpoint:" in n:
        return "checkpoint"
    if ":lora:" in n:
        return "lora"
    if ":controlnet:" in n or "controlnet" in n:
        return "controlnet"
    if ":vae:" in n or ":vae-" in n or (":sd" in n and ":vae" in n):
        return "vae"
    if ":upscaler:" in n or "upscale" in n:
        return "upscaler"
    if ":embedding:" in n or "textual" in n or "embedding" in n:
        return "embedding"

    return None


# ----------------- workflow walking -----------------

def iter_node_dicts(workflow: Any) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """
    Yield (node_id_str, node_dict) across multiple common ComfyUI JSON shapes.

    Supports:
      A) "prompt" style (common embeds):
         { "6": {"class_type":"...", "inputs":{...}}, "7": {...}, ... }

      B) nested containers:
         { "prompt": {...} } or { "workflow": {...} } or { "graph": {...} }

      C) nodes list variants:
         { "nodes": [ {"id":6, "type":"...", ...}, ... ] }

      D) nodes dict variants:
         { "nodes": { "6": {...}, ... } }
    """
    if isinstance(workflow, dict):
        # Common nested containers
        for container_key in ("prompt", "workflow", "graph"):
            if container_key in workflow:
                yield from iter_node_dicts(workflow[container_key])

        # nodes can be dict or list
        nodes = workflow.get("nodes")
        if isinstance(nodes, dict):
            yield from iter_node_dicts(nodes)
        elif isinstance(nodes, list):
            for i, n in enumerate(nodes):
                if isinstance(n, dict):
                    nid = n.get("id") or n.get("node_id") or n.get("key") or str(i)
                    yield str(nid), n

        # Direct node map: keys are node ids
        for k, v in workflow.items():
            if not isinstance(v, dict):
                continue
            if ("class_type" in v) or ("inputs" in v) or ("type" in v):
                yield str(k), v

    elif isinstance(workflow, list):
        for i, item in enumerate(workflow):
            if isinstance(item, dict):
                nid = item.get("id") or item.get("node_id") or str(i)
                yield str(nid), item


def normalize_class_type(node: Dict[str, Any]) -> str:
    # Comfy nodes usually have "class_type"; some exports use "type"
    ct = node.get("class_type") or node.get("type") or ""
    return str(ct)


def get_inputs(node: Dict[str, Any]) -> Dict[str, Any]:
    inputs = node.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


# ----------------- extract from nodes -----------------

def extract_from_nodes(workflow: Any) -> List[Dict[str, Any]]:
    """
    Extract resources by walking node dictionaries and inspecting class_type + inputs.
    """
    out: List[Dict[str, Any]] = []

    for node_id, node in iter_node_dicts(workflow):
        ct_raw = normalize_class_type(node)
        ct = ct_raw.lower()
        inputs = get_inputs(node)

        # --- checkpoint loaders ---
        if ("checkpointloader" in ct) or ("checkpoint_loader" in ct) or ("checkpointloadersimple" in ct):
            ckpt = inputs.get("ckpt_name") or inputs.get("checkpoint") or inputs.get("model_name")
            if isinstance(ckpt, str) and ckpt.strip():
                out.append({
                    "kind": "checkpoint",
                    "name": ckpt.strip(),
                    "weight": 1.0,
                    "extra": {"node_id": node_id, "class_type": ct_raw},
                })

        # --- LoRA loaders ---
        if ("loraloader" in ct) or ("lora_loader" in ct):
            lora = inputs.get("lora_name") or inputs.get("lora") or inputs.get("model_name")
            if isinstance(lora, str) and lora.strip():
                w_model = as_float(inputs.get("strength_model"))
                w_clip = as_float(inputs.get("strength_clip"))
                w_main = w_model if w_model is not None else (as_float(inputs.get("strength")) or 1.0)
                out.append({
                    "kind": "lora",
                    "name": lora.strip(),
                    "weight": w_main,
                    "extra": {
                        "node_id": node_id,
                        "class_type": ct_raw,
                        "strength_model": w_model,
                        "strength_clip": w_clip,
                    },
                })

        # --- Upscaler model loaders ---
        if ("upscalemodelloader" in ct) or ("upscalerloader" in ct) or ("upscale_model_loader" in ct):
            up = inputs.get("model_name") or inputs.get("upscale_model") or inputs.get("upscaler_name")
            if isinstance(up, str) and up.strip():
                out.append({
                    "kind": "upscaler",
                    "name": up.strip(),
                    "weight": 1.0,
                    "extra": {"node_id": node_id, "class_type": ct_raw},
                })

        # --- ControlNet model loaders (varies by pack) ---
        if ("controlnet" in ct) and (("loader" in ct) or ("load" in ct)):
            cn = (
                inputs.get("control_net_name")
                or inputs.get("controlnet_name")
                or inputs.get("controlnet_model")
                or inputs.get("model_name")
            )
            if isinstance(cn, str) and cn.strip():
                w = as_float(inputs.get("strength")) or as_float(inputs.get("weight")) or 1.0
                out.append({
                    "kind": "controlnet",
                    "name": cn.strip(),
                    "weight": w,
                    "extra": {"node_id": node_id, "class_type": ct_raw},
                })

        # --- VAE loaders ---
        if ("vaeloader" in ct) or ("vae_loader" in ct):
            vae = inputs.get("vae_name") or inputs.get("vae") or inputs.get("model_name")
            if isinstance(vae, str) and vae.strip():
                out.append({
                    "kind": "vae",
                    "name": vae.strip(),
                    "weight": 1.0,
                    "extra": {"node_id": node_id, "class_type": ct_raw},
                })

        # --- Embedding loaders (rare in comfy graphs; varies) ---
        if ("embedding" in ct) and (("loader" in ct) or ("load" in ct)):
            emb = inputs.get("embedding_name") or inputs.get("name") or inputs.get("model_name")
            if isinstance(emb, str) and emb.strip():
                out.append({
                    "kind": "embedding",
                    "name": emb.strip(),
                    "weight": 1.0,
                    "extra": {"node_id": node_id, "class_type": ct_raw},
                })

    return out


# ----------------- fallbacks: extra.airs and extraMetadata -----------------

def extract_from_extra_airs(workflow: Any) -> List[Dict[str, Any]]:
    """
    Many embeds include:
      "extra": { "airs": [ "urn:air:...:checkpoint:...", "urn:air:...:lora:..." ] }
    This is a compact and reliable fallback.
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(workflow, dict):
        return out

    extra = workflow.get("extra")
    if not isinstance(extra, dict):
        return out

    airs = extra.get("airs")
    if not isinstance(airs, list):
        return out

    for s in airs:
        if not isinstance(s, str) or not s.strip():
            continue
        kind = classify_urn(s)
        if not kind:
            continue
        out.append({
            "kind": kind,
            "name": s.strip(),
            "weight": 1.0,
            "extra": {"source": "extra.airs"},
        })

    return out


def extract_from_extra_metadata(workflow: Any) -> List[Dict[str, Any]]:
    """
    Some embeds include:
      "extraMetadata": "{...json string...}"
    which may include:
      resources: [{modelVersionId, strength}, ...]

    Without names/URNs, we store as references:
      kind = 'resource_ref'
      name = 'modelVersionId:<id>'
    """
    out: List[Dict[str, Any]] = []
    if not isinstance(workflow, dict):
        return out

    em = workflow.get("extraMetadata")
    if not isinstance(em, str) or not em.strip():
        return out

    try:
        obj = json.loads(em)
    except Exception:
        return out

    res = obj.get("resources")
    if not isinstance(res, list):
        return out

    for r in res:
        if not isinstance(r, dict):
            continue
        mvid = r.get("modelVersionId")
        strength = as_float(r.get("strength")) or 1.0
        if mvid is None:
            continue
        out.append({
            "kind": "resource_ref",
            "name": f"modelVersionId:{mvid}",
            "weight": strength,
            "extra": {"source": "extraMetadata.resources"},
        })

    return out


def dedupe_resources(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dedupe by (kind, name). Merge extras lightly.
    """
    seen: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for it in items:
        kind = it.get("kind")
        name = it.get("name")
        if not kind or not name:
            continue

        key = (str(kind), str(name))

        if key not in seen:
            seen[key] = it
            continue

        # Prefer a non-null weight if existing is null
        w_new = it.get("weight")
        w_old = seen[key].get("weight")
        if w_old is None and w_new is not None:
            seen[key]["weight"] = w_new

        # Merge extras (non-destructive)
        ex_old = seen[key].get("extra") or {}
        ex_new = it.get("extra") or {}
        if isinstance(ex_old, dict) and isinstance(ex_new, dict):
            for k, v in ex_new.items():
                ex_old.setdefault(k, v)
            seen[key]["extra"] = ex_old

    return list(seen.values())


# ----------------- DB ops -----------------

def ensure_resources_table(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("""
      CREATE TABLE IF NOT EXISTS resources (
        image_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        name TEXT,
        version TEXT,
        hash TEXT,
        weight REAL,
        extra_json TEXT,
        FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
      );
    """)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="Path to images.db")
    ap.add_argument("--limit", type=int, default=0, help="Optional limit for testing (0 = no limit)")
    args = ap.parse_args()

    db_path = resolve_repo_path(args.db, must_exist=True, allow_absolute=False)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_resources_table(conn)

        sql = """
        SELECT image_id, v_json
        FROM kv
        WHERE k='workflow_json' AND v_json IS NOT NULL
        """
        if args.limit and args.limit > 0:
            sql += f" LIMIT {int(args.limit)}"

        rows = conn.execute(sql).fetchall()
        print(f"workflow_json rows found: {len(rows)}")

        images_updated = 0
        resources_inserted = 0

        for row in rows:
            image_id = row["image_id"]
            v_json = row["v_json"]

            # v_json is stored as TEXT; parse to object
            try:
                workflow = json.loads(v_json)
            except Exception:
                continue

            extracted: List[Dict[str, Any]] = []
            extracted.extend(extract_from_nodes(workflow))
            extracted.extend(extract_from_extra_airs(workflow))
            extracted.extend(extract_from_extra_metadata(workflow))

            extracted = dedupe_resources(extracted)

            # Idempotent rebuild per image_id
            conn.execute("DELETE FROM resources WHERE image_id=?", (image_id,))

            for it in extracted:
                conn.execute(
                    "INSERT INTO resources(image_id, kind, name, version, hash, weight, extra_json) VALUES(?,?,?,?,?,?,?)",
                    (
                        image_id,
                        it.get("kind"),
                        it.get("name"),
                        None,
                        None,
                        it.get("weight"),
                        json.dumps(it.get("extra"), ensure_ascii=False) if it.get("extra") is not None else None,
                    ),
                )

            if extracted:
                images_updated += 1
                resources_inserted += len(extracted)

        conn.commit()
        print(f"Images updated: {images_updated}")
        print(f"Resources inserted: {resources_inserted}")


if __name__ == "__main__":
    main()
