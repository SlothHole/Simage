"""
Ingest EXIF JSONL into SQLite and exports.

Run from repo root:
  python -m simage ingest --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv

What it does:
- Reads ExifTool JSONL objects (one per file)
- Extracts likely AI metadata text/JSON from many tag locations
- Normalizes into a consistent dict + key/value rows
- Stores into SQLite (images + kv)

Adds (prompt + params quality-of-life):
- Enforces clean positive/negative separation when possible
- Tokenizes prompts into comma-separated (+ weighted) tokens
  * kv keys: prompt_text, neg_prompt_text, prompt_tokens, neg_tokens
- Normalizes sampler/scheduler spellings and stores alongside raw
  * kv keys: sampler_norm, scheduler_norm
- Normalizes numeric params where present
  * kv keys: steps_norm, cfg_scale_norm, seed_norm, size_norm
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

from simage.utils.paths import resolve_repo_path, resolve_repo_relative


def sha256_file_backup(path: str) -> Optional[str]:
    """
    Backup: Directly compute SHA256 for any file path, bypassing repo-relative logic.
    """
    try:
        from pathlib import Path

        abs_path = Path(path)
        if not abs_path.exists():
            return None
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


CSV_COLUMNS = [
    "id",
    "source_file",
    "file_name",
    "ext",
    "width",
    "height",
    "format_hint",
    "model",
    "sampler",
    "scheduler",
    "steps",
    "cfg_scale",
    "seed",
    "prompt",
    "negative_prompt",
]


# ---------- helpers ----------

def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id_for_path(path: str) -> str:
    # deterministic UUID from repo-relative path (so re-ingest doesn’t duplicate)
    ns = uuid.UUID("12345678-1234-5678-1234-567812345678")
    rel, _abs = resolve_repo_relative(path, allow_absolute=True)
    return str(uuid.uuid5(ns, str(rel).lower()))


def sha256_file(path: str) -> Optional[str]:
    try:
        import os
        from pathlib import Path
        # If file is inside repo, use resolve_repo_relative; else, use absolute path directly
        if Path(path).is_absolute() and Path(path).exists():
            abs_path = path
        else:
            _rel, abs_path = resolve_repo_relative(path, allow_absolute=True)
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def is_probably_json(s: str) -> bool:
    s = s.strip()
    return (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]"))


def safe_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None


def first_present(d: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def clean_ws(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _key_has_any(lk: str, hints: Tuple[str, ...]) -> bool:
    return any(h in lk for h in hints)


def _is_camera_model_key(lk: str) -> bool:
    if not lk.endswith(":model"):
        return False
    prefix = lk.split(":", 1)[0]
    return prefix in ("exif", "ifd0", "quicktime")


def iter_node_dicts(workflow: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(workflow, dict):
        for container_key in ("prompt", "workflow", "graph"):
            if container_key in workflow:
                yield from iter_node_dicts(workflow[container_key])

        nodes = workflow.get("nodes")
        if isinstance(nodes, dict):
            yield from iter_node_dicts(nodes)
        elif isinstance(nodes, list):
            for item in nodes:
                if isinstance(item, dict):
                    yield item

        for v in workflow.values():
            if isinstance(v, dict) and ("class_type" in v or "inputs" in v or "type" in v):
                yield v
    elif isinstance(workflow, list):
        for item in workflow:
            if isinstance(item, dict):
                yield item


# ---------- prompt parsing + tokenization ----------

RE_NEG_MARKER = re.compile(r"\bNegative prompt:\s*", re.IGNORECASE)
# Common tail markers that begin the parameter section in A1111-style blocks
# Common tail markers that begin the parameter/resource section in A1111-style blocks.
# NOTE: Some sources jam these inline (e.g. ".Steps: 30, Sampler: ..."), so we detect them anywhere.
RE_TAIL_ANY = re.compile(
    r"(?:Steps:|Sampler:|CFG\s*scale:|Seed:|Size:|Model hash:|Model:|Denoising strength:|Hires|Clip skip:|Created Date:|Civitai resources:|Civitai metadata:|Hashes:)\s*",
    re.IGNORECASE,
)

A1111_MARKERS = (
    "steps:",
    "sampler:",
    "cfg scale:",
    "seed:",
    "size:",
    "model hash:",
    "model:",
    "denoising strength:",
    "clip skip:",
    "hires",
    "lora:",
    "<lora:",
)

def looks_like_a1111_text(s: str) -> bool:
    low = s.lower()
    return any(m in low for m in A1111_MARKERS) or ("negative prompt:" in low)


def _to_int(x: Any) -> Optional[int]:
    try:
        if isinstance(x, bool):
            return None
        if x is None or x == "":
            return None
        return int(float(x))
    except Exception:
        return None


def _to_float(x: Any) -> Optional[float]:
    try:
        if isinstance(x, bool):
            return None
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _looks_like_sampler(s: str) -> bool:
    low = s.lower()
    tokens = ("euler", "dpm", "ddim", "heun", "lms", "uni", "plms", "ancestral")
    return any(t in low for t in tokens)


def parse_ksampler_widgets(values: List[Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for v in values:
        if isinstance(v, str):
            if _looks_like_sampler(v) and "sampler" not in out:
                out["sampler"] = v
            if v.lower() in SCHEDULER_MAP and "scheduler" not in out:
                out["scheduler"] = v

    for v in values:
        i = _to_int(v)
        if i is None:
            continue
        if i >= 10000 and "seed" not in out:
            out["seed"] = i
            continue
        if 1 <= i <= 200 and "steps" not in out:
            out["steps"] = i

    for v in values:
        f = _to_float(v)
        if f is None:
            continue
        if 0.1 <= f <= 30 and "cfg_scale" not in out:
            if out.get("steps") == int(f) or out.get("seed") == int(f):
                continue
            out["cfg_scale"] = f

    return out


def _best_prompt_candidate(values: List[str]) -> Optional[str]:
    cleaned = [clean_ws(v) for v in values if isinstance(v, str) and v.strip()]
    if not cleaned:
        return None
    return max(cleaned, key=len)


def extract_comfyui_prompts(workflow: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract likely positive/negative prompts from ComfyUI-style workflows.

    We look for prompt-like nodes (Prompt / CLIPTextEncode) and prefer the
    longest candidate text for each side.
    """
    if not isinstance(workflow, (dict, list)):
        return None, None

    pos_candidates: List[str] = []
    neg_candidates: List[str] = []

    for node in iter_node_dicts(workflow):
        label_parts = [
            node.get("class_type"),
            node.get("type"),
            node.get("title"),
            node.get("name"),
        ]
        label = " ".join(str(p) for p in label_parts if p).lower()

        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}
        for k, v in inputs.items():
            if not isinstance(v, str) or not v.strip():
                continue
            key = str(k).lower()
            if "negative" in key:
                neg_candidates.append(v)
            elif key in ("text", "prompt", "positive") or "positive" in key:
                pos_candidates.append(v)

        widgets = node.get("widgets_values")
        if isinstance(widgets, list):
            widget_text = [v for v in widgets if isinstance(v, str) and v.strip()]
            if widget_text:
                best = _best_prompt_candidate(widget_text)
                if not best:
                    continue
                if "negative" in label:
                    neg_candidates.append(best)
                elif "prompt" in label or "cliptextencode" in label:
                    pos_candidates.append(best)

    pos = _best_prompt_candidate(pos_candidates)
    neg = _best_prompt_candidate(neg_candidates)
    return pos, neg


def extract_comfyui_params(workflow: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    for node in iter_node_dicts(workflow):
        ct_raw = node.get("class_type") or node.get("type") or ""
        ct = str(ct_raw).lower()
        inputs = node.get("inputs") if isinstance(node.get("inputs"), dict) else {}

        if ("checkpoint" in ct and ("loader" in ct or "load" in ct)) and "model" not in out:
            model = inputs.get("ckpt_name") or inputs.get("model_name") or inputs.get("checkpoint")
            if isinstance(model, str) and model.strip():
                out["model"] = model.strip()

        if "ksampler" in ct:
            params: Dict[str, Any] = {}
            if isinstance(inputs, dict):
                seed = _to_int(inputs.get("seed"))
                steps = _to_int(inputs.get("steps"))
                cfg = _to_float(inputs.get("cfg") or inputs.get("cfg_scale"))
                sampler = inputs.get("sampler_name") or inputs.get("sampler")
                scheduler = inputs.get("scheduler")
                if seed is not None:
                    params["seed"] = seed
                if steps is not None:
                    params["steps"] = steps
                if cfg is not None:
                    params["cfg_scale"] = cfg
                if isinstance(sampler, str) and sampler.strip():
                    params["sampler"] = sampler.strip()
                if isinstance(scheduler, str) and scheduler.strip():
                    params["scheduler"] = scheduler.strip()

            widgets = node.get("widgets_values")
            if isinstance(widgets, list):
                wparams = parse_ksampler_widgets(widgets)
                for k, v in wparams.items():
                    if k not in params or params.get(k) in (None, ""):
                        params[k] = v

            for k, v in params.items():
                if v not in (None, "") and out.get(k) in (None, ""):
                    out[k] = v

    return out

def cut_at_tail_markers(s: str) -> str:
    m = RE_TAIL_ANY.search(s)
    if not m:
        return s.strip()
    return s[: m.start()].strip()

RE_WEIGHT_PAREN = re.compile(r"^\((.+?):\s*([0-9.]+)\)\s*$")  # (token:1.2)
RE_WEIGHT_ANGLE = re.compile(r"^<lora:([^:>]+):\s*([0-9.]+)\s*>\s*$", re.IGNORECASE)  # <lora:name:1.0>


def enforce_pos_neg_separation(pos: Optional[str], neg: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Keep negative text out of positive text when the blob is messy.

    Rules:
    - If "Negative prompt:" appears inside pos, split at first occurrence.
    - If neg accidentally contains parameter tail markers, cut them off.
    """
    p = clean_ws(pos) if isinstance(pos, str) and pos.strip() else None
    n = clean_ws(neg) if isinstance(neg, str) and neg.strip() else None

    if p:
        m = RE_NEG_MARKER.search(p)
        if m:
            left = p[: m.start()].strip()
            right = p[m.end() :].strip()
            p = left if left else None
            if right and not n:
                n = right

    if p:
        p2 = cut_at_tail_markers(p)
        p = p2 if p2 else None
    if n:
        n2 = cut_at_tail_markers(n)
        n = n2 if n2 else None

    return p, n


def split_tokens_top_level(s: str) -> List[str]:
    """
    Split on commas/newlines, ignoring commas inside (), [], {}.
    Also treats the A1111 'BREAK' marker as a delimiter.
    """
    s = clean_ws(s)
    # Normalize separators
    s = s.replace("\n", ",")
    s = re.sub(r"\bBREAK\b", ",", s, flags=re.IGNORECASE)

    out: List[str] = []
    buf: List[str] = []
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0

    for ch in s:
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        elif ch == "[":
            depth_brack += 1
        elif ch == "]":
            depth_brack = max(0, depth_brack - 1)
        elif ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace = max(0, depth_brace - 1)

        if ch == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            tok = "".join(buf).strip()
            if tok:
                out.append(tok)
            buf = []
        else:
            buf.append(ch)

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)

    return [t.strip() for t in out if t and t.strip()]


def token_norm(t: str) -> str:
    t = t.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def parse_weighted_token(raw: str) -> Tuple[str, float]:
    """
    Return (token_text, weight). Default weight = 1.0.

    Supports:
      (token:1.2)
      <lora:name:1.0>  -> token_text becomes "lora:name"
    """
    r = raw.strip()

    m = RE_WEIGHT_PAREN.match(r)
    if m:
        token = m.group(1).strip()
        try:
            w = float(m.group(2))
        except Exception:
            w = 1.0
        return token, w

    m = RE_WEIGHT_ANGLE.match(r)
    if m:
        name = m.group(1).strip()
        try:
            w = float(m.group(2))
        except Exception:
            w = 1.0
        return f"lora:{name}", w

    return r, 1.0


def tokenize_prompt(s: str) -> List[Dict[str, Any]]:
    """
    Tokenize into comma-separated tokens, preserving explicit weights.
    Output (stored into kv.v_json):
      [{"t": "...", "t_norm": "...", "w": 1.0}, ...]

    Dedupe by t_norm (keeps last-seen weight).
    """
    toks = split_tokens_top_level(s)
    dedup: Dict[str, Dict[str, Any]] = {}

    for raw in toks:
        token, w = parse_weighted_token(raw)
        token = token.strip()
        if not token:
            continue

        tn = token_norm(token)
        # Drop pure BREAK tokens or empty artifacts
        if tn in ("break",):
            continue

        dedup[tn] = {"t": token, "t_norm": tn, "w": w}

    return list(dedup.values())


# ---------- parameter normalization ----------

def norm_keyish(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("-", " ")
    s = s.replace("_", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


SAMPLER_MAP = {
    "euler a": "euler_a",
    "euler ancestral": "euler_a",
    "euler_ancestral": "euler_a",
    "euler": "euler",
    "heun": "heun",
    "lms": "lms",
    "ddim": "ddim",
    "plms": "plms",
    "dpm2": "dpm2",
    "dpm 2": "dpm2",
    "dpm2 a": "dpm2_a",
    "dpm 2 a": "dpm2_a",
    "dpm++ 2m": "dpmpp_2m",
    "dpmpp 2m": "dpmpp_2m",
    "dpm++ 2m karras": "dpmpp_2m_karras",
    "dpmpp 2m karras": "dpmpp_2m_karras",
    "dpm++ sde": "dpmpp_sde",
    "dpmpp sde": "dpmpp_sde",
    "dpm++ sde karras": "dpmpp_sde_karras",
    "dpmpp sde karras": "dpmpp_sde_karras",
    "uni pc": "uni_pc",
    "unipc": "uni_pc",
}


def normalize_sampler(s: Any) -> Optional[str]:
    if not isinstance(s, str) or not s.strip():
        return None
    k = norm_keyish(s)
    return SAMPLER_MAP.get(k, k.replace(" ", "_"))


SCHEDULER_MAP = {
    "karras": "karras",
    "exponential": "exponential",
    "normal": "normal",
    "simple": "simple",
    "ddim": "ddim",
    "sgm uniform": "sgm_uniform",
    "sgm_uniform": "sgm_uniform",
}


def normalize_scheduler(s: Any) -> Optional[str]:
    if not isinstance(s, str) or not s.strip():
        return None
    k = norm_keyish(s)
    return SCHEDULER_MAP.get(k, k.replace(" ", "_"))


def to_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(float(x))
    except Exception:
        return None


def to_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def postprocess_prompts_and_params(rec: Dict[str, Any]) -> None:
    """
    Adds to rec["kv"] when possible:
      - prompt_text / neg_prompt_text
      - prompt_tokens / neg_tokens (JSON list)
      - sampler_norm / scheduler_norm
      - steps_norm / cfg_scale_norm / seed_norm / size_norm
    """
    kv = rec.get("kv", {})

    pos, neg = enforce_pos_neg_separation(
        kv.get("prompt") if "prompt" in kv else rec.get("prompt"),
        kv.get("negative_prompt") if "negative_prompt" in kv else rec.get("negative_prompt"),
    )

    if pos:
        rec["prompt"] = pos
        kv["prompt"] = pos
        kv["prompt_text"] = pos
        kv["prompt_tokens"] = tokenize_prompt(pos)
    else:
        rec["prompt"] = None
        kv.pop("prompt", None)
        kv.pop("prompt_text", None)
        kv.pop("prompt_tokens", None)

    if neg:
        rec["negative_prompt"] = neg
        kv["negative_prompt"] = neg
        kv["neg_prompt_text"] = neg
        kv["neg_tokens"] = tokenize_prompt(neg)
    else:
        rec["negative_prompt"] = None
        kv.pop("negative_prompt", None)
        kv.pop("neg_prompt_text", None)
        kv.pop("neg_tokens", None)

    # normalize sampler/scheduler
    sampler_raw = kv.get("sampler") if "sampler" in kv else rec.get("sampler")
    scheduler_raw = kv.get("scheduler") if "scheduler" in kv else rec.get("scheduler")

    s_norm = normalize_sampler(sampler_raw)
    if s_norm:
        kv["sampler_norm"] = s_norm

    sch_norm = normalize_scheduler(scheduler_raw)
    if sch_norm:
        kv["scheduler_norm"] = sch_norm

    # numeric norms
    steps_n = to_int(kv.get("steps") if "steps" in kv else rec.get("steps"))
    if steps_n is not None:
        kv["steps_norm"] = steps_n

    cfg_n = to_float(kv.get("cfg_scale") if "cfg_scale" in kv else rec.get("cfg_scale"))
    if cfg_n is not None:
        kv["cfg_scale_norm"] = cfg_n

    seed_n = to_int(kv.get("seed") if "seed" in kv else rec.get("seed"))
    if seed_n is not None:
        kv["seed_norm"] = seed_n

    w = to_int(kv.get("width") if "width" in kv else rec.get("width"))
    h = to_int(kv.get("height") if "height" in kv else rec.get("height"))
    if w and h:
        kv["size_norm"] = f"{w}x{h}"

    rec["kv"] = kv


# ---------- AI metadata extraction ----------

TEXT_CANDIDATE_KEYS = [
    "PNG:Parameters",
    "PNG:Comment",
    "PNG:Description",
    "PNG:Prompt",
    "PNG:Workflow",
    "PNG:Software",
    "PNG:Title",
    "PNG:TextualData",
    "PNG:RawProfileType",
    "PNG:RawProfileData",
    "XMP:Description",
    "XMP:Subject",
    "XMP:CreatorTool",
    "EXIF:UserComment",
    "ExifIFD:UserComment",
    "EXIF:ImageDescription",
    "EXIF:Software",
    "IPTC:Caption-Abstract",
    "IPTC:Keywords",
    "EXIF:DocumentName",
    "IFD0:ImageDescription",
    "IFD0:Software",
]

RE_A1111_SIZE = re.compile(r"\bSize:\s*(\d+)\s*x\s*(\d+)\b", re.IGNORECASE)
RE_A1111_STEPS = re.compile(r"\bSteps:\s*(\d+)\b", re.IGNORECASE)
RE_A1111_CFG = re.compile(r"\bCFG\s*scale:\s*([0-9.]+)\b", re.IGNORECASE)
RE_A1111_SEED = re.compile(r"\bSeed:\s*(\d+)\b", re.IGNORECASE)
RE_A1111_SAMPLER = re.compile(r"\bSampler:\s*([^,\\n]+)\b", re.IGNORECASE)
RE_A1111_SCHEDULER = re.compile(r"\bScheduler:\s*([^,\\n]+)\b", re.IGNORECASE)
RE_A1111_MODEL = re.compile(r"\bModel:\s*([^,\\n]+)\b", re.IGNORECASE)


def extract_candidate_blobs(exif_obj: Dict[str, Any]) -> List[Tuple[str, str]]:
    blobs: List[Tuple[str, str]] = []

    for k in TEXT_CANDIDATE_KEYS:
        v = exif_obj.get(k)
        if isinstance(v, str) and v.strip():
            blobs.append((k, v))

    ai_markers = ("steps:", "sampler:", "cfg scale:", "negative prompt:", "comfyui", "workflow", "seed:")
    for k, v in exif_obj.items():
        if not isinstance(v, str):
            continue
        s = v.strip()
        if len(s) < 30:
            continue
        low = s.lower()
        if any(m in low for m in ai_markers):
            blobs.append((k, v))

    seen = set()
    out: List[Tuple[str, str]] = []
    for k, v in blobs:
        key = (k, v)
        if key not in seen:
            seen.add(key)
            out.append((k, v))
    return out


def parse_a1111_parameters(text: str) -> Dict[str, Any]:
    """
    Best-effort parse of A1111-like parameters blocks.
    """
    out: Dict[str, Any] = {}
    t = clean_ws(text)

    pos = None
    neg = None

    m = RE_NEG_MARKER.search(t)
    if m:
        pos = t[: m.start()].strip()
        rest = t[m.end() :].strip()

        # Cut negative at first tail marker (Steps:, Sampler:, Civitai resources, etc.)
        neg = cut_at_tail_markers(rest)
    else:
        # If no negative prompt marker, treat top block as prompt, but try to cut off tail markers
        pos = cut_at_tail_markers(t)

    if pos:
        out["prompt"] = pos
    if neg:
        out["negative_prompt"] = neg

    m = RE_A1111_SIZE.search(t)
    if m:
        out["width"] = int(m.group(1))
        out["height"] = int(m.group(2))

    m = RE_A1111_STEPS.search(t)
    if m:
        out["steps"] = int(m.group(1))

    m = RE_A1111_CFG.search(t)
    if m:
        out["cfg_scale"] = float(m.group(1))

    m = RE_A1111_SEED.search(t)
    if m:
        out["seed"] = int(m.group(1))

    m = RE_A1111_SAMPLER.search(t)
    if m:
        out["sampler"] = m.group(1).strip()

    m = RE_A1111_SCHEDULER.search(t)
    if m:
        out["scheduler"] = m.group(1).strip()

    m = RE_A1111_MODEL.search(t)
    if m:
        out["model"] = m.group(1).strip()

    out["raw_text"] = t[:2000]
    out["format_hint"] = "a1111_like"
    return out


def parse_comfyui_embedded_json(blob: Any) -> Optional[Dict[str, Any]]:
    """
    ComfyUI often embeds JSON for prompt/workflow. We don't assume exact structure.
    We store the JSON and extract a few common signals if present.

    Prompt extraction is conservative:
    - If we find paired keys like (positive, negative) or (prompt, negative_prompt), we use them.
    - Otherwise we don't guess.
    """
    if not isinstance(blob, (dict, list)):
        return None

    rec: Dict[str, Any] = {
        "format_hint": "comfyui_like",
        "workflow_json": blob,
    }

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                yield k, v
                yield from walk(v)
        elif isinstance(x, list):
            for v in x:
                yield from walk(v)

    numeric_keys = {"seed", "steps", "cfg", "cfg_scale", "width", "height"}
    for k, v in walk(blob):
        lk = str(k).lower()
        if lk in numeric_keys and isinstance(v, (int, float, str)):
            rec[lk] = v

    # Conservative prompt extraction: look for dicts containing known pairs
    def find_prompt_pairs(x: Any) -> Optional[Tuple[str, str]]:
        if isinstance(x, dict):
            keys = {str(k).lower(): k for k in x.keys()}
            # prompt/negative_prompt
            if "prompt" in keys and ("negative_prompt" in keys or "negative prompt" in keys):
                p = x[keys["prompt"]]
                n = x[keys.get("negative_prompt") or keys.get("negative prompt")]
                if isinstance(p, str) and isinstance(n, str):
                    return (p, n)
            # positive/negative
            if "positive" in keys and "negative" in keys:
                p = x[keys["positive"]]
                n = x[keys["negative"]]
                if isinstance(p, str) and isinstance(n, str):
                    return (p, n)

            for v in x.values():
                r = find_prompt_pairs(v)
                if r:
                    return r
        elif isinstance(x, list):
            for v in x:
                r = find_prompt_pairs(v)
                if r:
                    return r
        return None

    pair = find_prompt_pairs(blob)
    if pair:
        rec["prompt"] = pair[0]
        rec["negative_prompt"] = pair[1]

    params = extract_comfyui_params(blob)
    for k, v in params.items():
        if v not in (None, "") and rec.get(k) in (None, ""):
            rec[k] = v

    return rec


def normalize_record(exif_obj: Dict[str, Any]) -> Dict[str, Any]:
    src_raw = exif_obj.get("SourceFile") or exif_obj.get("File:FileName") or ""
    src = ""
    src_abs: Optional[str] = None
    if isinstance(src_raw, str) and src_raw:
        rel_path, abs_path = resolve_repo_relative(src_raw, allow_absolute=True)
        src = str(rel_path)
        src_abs = str(abs_path)
    file_name = os.path.basename(src) if isinstance(src, str) and src else None
    ext = os.path.splitext(file_name or "")[1].lower().lstrip(".") if file_name else None

    width = first_present(exif_obj, ["File:ImageWidth", "EXIF:ImageWidth", "PNG:ImageWidth", "QuickTime:ImageWidth"])
    height = first_present(exif_obj, ["File:ImageHeight", "EXIF:ImageHeight", "PNG:ImageHeight", "QuickTime:ImageHeight"])

    rec: Dict[str, Any] = {
        "id": stable_id_for_path(src) if isinstance(src, str) and src else str(uuid.uuid4()),
        "source_file": src,
        "file_name": file_name,
        "ext": ext,
        "width": int(width) if isinstance(width, (int, float, str)) and str(width).isdigit() else None,
        "height": int(height) if isinstance(height, (int, float, str)) and str(height).isdigit() else None,
        "imported_utc": utc_now_iso(),
        "created_utc": None,
        "sha256": sha256_file(src_abs) if isinstance(src_abs, str) and os.path.isfile(src_abs) else None,
        "format_hint": None,
        "prompt": None,
        "negative_prompt": None,
        "steps": None,
        "cfg_scale": None,
        "seed": None,
        "sampler": None,
        "scheduler": None,
        "model": None,
        "raw_text_preview": None,
        "workflow_json": None,
        "resources": [],
        "kv": {},
    }

    blobs = extract_candidate_blobs(exif_obj)

    # Try JSON first (ComfyUI-like)
    for k, v in blobs:
        if not isinstance(v, str):
            continue
        if not is_probably_json(v):
            continue

        obj = safe_json_loads(v)
        if obj is None:
            continue

        comfy = parse_comfyui_embedded_json(obj)
        if not comfy:
            continue

        rec["format_hint"] = comfy.get("format_hint")

        wf = comfy.get("workflow_json")
        if wf is not None:
            rec["kv"]["workflow_json"] = wf
        rec["workflow_json"] = wf  # keep in JSONL export

        # Extract key params from workflow (values only, not raw workflow JSON).
        for fld in ("seed", "steps", "width", "height", "sampler", "scheduler", "model"):
            if fld in comfy and rec.get(fld) in (None, ""):
                if fld in ("sampler", "scheduler", "model"):
                    if isinstance(comfy[fld], str):
                        rec[fld] = comfy[fld]
                else:
                    try:
                        rec[fld] = int(float(comfy[fld]))
                    except Exception:
                        pass

        # cfg can be stored as cfg or cfg_scale
        if "cfg_scale" in comfy and rec.get("cfg_scale") in (None, ""):
            try:
                rec["cfg_scale"] = float(comfy["cfg_scale"])
            except Exception:
                pass
        if "cfg" in comfy and rec.get("cfg_scale") in (None, ""):
            try:
                rec["cfg_scale"] = float(comfy["cfg"])
            except Exception:
                pass

        break

    # Try A1111-like parameters text (also when workflow JSON exists)
    for k, v in blobs:
        if not isinstance(v, str):
            continue
        if is_probably_json(v):
            continue
        if "workflow" in str(k).lower():
            continue
        if looks_like_a1111_text(v):
            parsed = parse_a1111_parameters(v)
            if parsed.get("raw_text") and not rec.get("raw_text_preview"):
                rec["raw_text_preview"] = parsed.get("raw_text")
            if parsed.get("format_hint") and rec.get("format_hint") in (None, ""):
                rec["format_hint"] = parsed.get("format_hint")
            for fld in ("prompt", "negative_prompt", "steps", "cfg_scale", "seed", "width", "height", "sampler", "scheduler", "model"):
                if fld in parsed and parsed[fld] not in (None, "") and rec.get(fld) in (None, ""):
                    rec[fld] = parsed[fld]
            break

    keyed = extract_keyed_fields(exif_obj)
    for fld, val in keyed.items():
        if rec.get(fld) in (None, ""):
            rec[fld] = val

    wf_prompt, wf_neg = extract_comfyui_prompts(rec.get("workflow_json"))
    if wf_prompt:
        rec["prompt"] = wf_prompt
    if wf_neg:
        rec["negative_prompt"] = wf_neg

    if rec["raw_text_preview"] is None and blobs:
        rec["raw_text_preview"] = str(blobs[0][1])[:2000]

    kv = rec["kv"]
    for fld in ("prompt", "negative_prompt", "steps", "cfg_scale", "seed", "sampler", "scheduler", "model", "format_hint"):
        if rec.get(fld) not in (None, ""):
            kv[fld] = rec[fld]

    if rec.get("width") is not None:
        kv["width"] = rec["width"]
    if rec.get("height") is not None:
        kv["height"] = rec["height"]
    if rec.get("ext"):
        kv["ext"] = rec["ext"]

    software = first_present(exif_obj, ["EXIF:Software", "PNG:Software", "XMP:CreatorTool"])
    if isinstance(software, str) and software.strip():
        kv["software"] = software.strip()

    # NEW: enforce pos/neg separation + tokenization + param normalization
    postprocess_prompts_and_params(rec)

    return rec


# ---------- DB ingest ----------

def init_db(db_path: str, schema_sql_path: str) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON;")
        with open(schema_sql_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())


def upsert_record(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(
        """
      INSERT INTO images(id, source_file, file_name, ext, width, height, created_utc, imported_utc, sha256, format_hint, raw_text_preview)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(source_file) DO UPDATE SET
        file_name=excluded.file_name,
        ext=excluded.ext,
        width=excluded.width,
        height=excluded.height,
        sha256=excluded.sha256,
        format_hint=excluded.format_hint,
        raw_text_preview=excluded.raw_text_preview
    """,
        (
            rec["id"],
            rec["source_file"],
            rec["file_name"],
            rec["ext"],
            rec["width"],
            rec["height"],
            rec["created_utc"],
            rec["imported_utc"],
            rec["sha256"],
            rec["format_hint"],
            rec["raw_text_preview"],
        ),
    )

    for k, v in rec.get("kv", {}).items():
        v_text: Optional[str] = None
        v_num: Optional[float] = None
        v_json: Optional[str] = None

        if isinstance(v, (int, float)):
            v_num = float(v)
            v_text = str(v)
        elif isinstance(v, (dict, list)):
            v_json = json.dumps(v, ensure_ascii=False)
            v_text = None
        else:
            v_text = str(v)
            try:
                v_num = float(v_text) if re.fullmatch(r"-?\d+(\.\d+)?", v_text.strip()) else None
            except Exception:
                v_num = None

        conn.execute(
            """
          INSERT INTO kv(image_id, k, v, v_num, v_json)
          VALUES(?,?,?,?,?)
          ON CONFLICT(image_id, k) DO UPDATE SET
            v=excluded.v,
            v_num=excluded.v_num,
            v_json=excluded.v_json
        """,
            (rec["id"], k, v_text, v_num, v_json),
        )


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


PROMPT_KEY_HINTS = ("prompt", "positive", "pos_prompt", "positive_prompt")
NEG_PROMPT_KEY_HINTS = ("negative prompt", "negative_prompt", "neg_prompt", "negprompt", "negative")
MODEL_KEY_HINTS = ("model", "checkpoint", "ckpt")
SAMPLER_KEY_HINTS = ("sampler",)
SCHEDULER_KEY_HINTS = ("scheduler",)
STEPS_KEY_HINTS = ("steps",)
CFG_KEY_HINTS = ("cfg scale", "cfg_scale", "cfgscale", "cfg")
SEED_KEY_HINTS = ("seed",)
WIDTH_KEY_HINTS = ("width",)
HEIGHT_KEY_HINTS = ("height",)


def extract_keyed_fields(exif_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract direct field values from EXIF keys (not just A1111 blocks).
    Uses key names to detect where values belong and returns a best-effort map.
    """
    out: Dict[str, Any] = {}
    pos_candidates: List[str] = []
    neg_candidates: List[str] = []

    for k, v in exif_obj.items():
        if v in (None, ""):
            continue
        lk = str(k).lower()
        if "workflow" in lk:
            continue

        if isinstance(v, str):
            if _key_has_any(lk, NEG_PROMPT_KEY_HINTS) and "prompt" in lk:
                neg_candidates.append(v)
                continue
            if _key_has_any(lk, PROMPT_KEY_HINTS):
                pos_candidates.append(v)
                continue

            if _key_has_any(lk, MODEL_KEY_HINTS) and not _is_camera_model_key(lk):
                if "model" not in out:
                    out["model"] = clean_ws(v)
                continue

            if _key_has_any(lk, SAMPLER_KEY_HINTS) and "sampler" not in out:
                out["sampler"] = clean_ws(v)
                continue

            if _key_has_any(lk, SCHEDULER_KEY_HINTS) and "scheduler" not in out:
                out["scheduler"] = clean_ws(v)
                continue

            if _key_has_any(lk, STEPS_KEY_HINTS) and "steps" not in out:
                steps = _to_int(v)
                if steps is not None:
                    out["steps"] = steps
                continue

            if _key_has_any(lk, CFG_KEY_HINTS) and "cfg_scale" not in out:
                if "config" not in lk:
                    cfg = _to_float(v)
                    if cfg is not None:
                        out["cfg_scale"] = cfg
                continue

            if _key_has_any(lk, SEED_KEY_HINTS) and "seed" not in out:
                seed = _to_int(v)
                if seed is not None:
                    out["seed"] = seed
                continue

            if _key_has_any(lk, WIDTH_KEY_HINTS) and "width" not in out:
                width = _to_int(v)
                if width is not None:
                    out["width"] = width
                continue

            if _key_has_any(lk, HEIGHT_KEY_HINTS) and "height" not in out:
                height = _to_int(v)
                if height is not None:
                    out["height"] = height
                continue

        elif isinstance(v, (int, float)):
            if _key_has_any(lk, STEPS_KEY_HINTS) and "steps" not in out:
                out["steps"] = int(v)
            if _key_has_any(lk, SEED_KEY_HINTS) and "seed" not in out:
                out["seed"] = int(v)
            if _key_has_any(lk, WIDTH_KEY_HINTS) and "width" not in out:
                out["width"] = int(v)
            if _key_has_any(lk, HEIGHT_KEY_HINTS) and "height" not in out:
                out["height"] = int(v)
            if _key_has_any(lk, CFG_KEY_HINTS) and "cfg_scale" not in out:
                if "config" not in lk:
                    out["cfg_scale"] = float(v)

    pos = _best_prompt_candidate(pos_candidates)
    neg = _best_prompt_candidate(neg_candidates)
    if pos:
        out["prompt"] = pos
    if neg:
        out["negative_prompt"] = neg

    return out


def merge_missing_values(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            merge_missing_values(target[k], v)
        elif k not in target or target[k] in (None, ""):
            target[k] = v


def normalize_key(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).replace("\\", "/").lower()


def record_key(rec: Dict[str, Any]) -> str:
    return normalize_key(rec.get("source_file") or rec.get("file_name"))


def merge_record_lists(
    new_records: List[Dict[str, Any]],
    old_records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    old_by_key = {record_key(r): r for r in old_records if record_key(r)}
    old_by_name = {}
    for r in old_records:
        name = r.get("file_name")
        if name and name not in old_by_name:
            old_by_name[name] = r

    for rec in new_records:
        key = record_key(rec)
        old = old_by_key.get(key) or old_by_name.get(rec.get("file_name"))
        if old:
            merge_missing_values(rec, old)

    new_keys = {record_key(r) for r in new_records if record_key(r)}
    missing = [r for k, r in old_by_key.items() if k not in new_keys]
    return new_records + missing


def compute_csv_columns(records: List[Dict[str, Any]]) -> List[str]:
    extra = sorted({k for r in records for k in r.keys()} - set(CSV_COLUMNS) - {"kv", "resources", "workflow_json", "raw_text_preview"})
    return CSV_COLUMNS + extra


def write_csv(csv_path: str, records: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    cols = columns or CSV_COLUMNS
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            row = {c: r.get(c) for c in cols}
            w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_jsonl", required=True)
    ap.add_argument("--db", dest="db_path", required=True)
    ap.add_argument("--schema", dest="schema_path", default="simage/data/schema.sql")
    ap.add_argument("--jsonl", dest="out_jsonl", required=True)
    ap.add_argument("--csv", dest="out_csv", required=True)
    args = ap.parse_args()

    in_jsonl = resolve_repo_path(args.in_jsonl, must_exist=True, allow_absolute=False)
    db_path = resolve_repo_path(args.db_path, allow_absolute=False)
    schema_path = resolve_repo_path(args.schema_path, must_exist=True, allow_absolute=False)
    out_jsonl = resolve_repo_path(args.out_jsonl, allow_absolute=False)
    out_csv = resolve_repo_path(args.out_csv, allow_absolute=False)

    init_db(str(db_path), str(schema_path))

    records: List[Dict[str, Any]] = []
    os.makedirs(os.path.dirname(out_jsonl), exist_ok=True)

    with open(in_jsonl, "r", encoding="utf-8-sig") as f_in, sqlite3.connect(db_path) as conn:

        conn.execute("PRAGMA foreign_keys=ON;")

        for line in f_in:
            line = line.strip()
            if not line:
                continue
            line = line.lstrip("\ufeff")
            exif_obj = json.loads(line)
            rec = normalize_record(exif_obj)
            upsert_record(conn, rec)
            records.append(rec)

        conn.commit()

    old_csv_records: List[Dict[str, Any]] = []
    if out_csv.exists():
        with open(out_csv, "r", encoding="utf-8") as f_old:
            old_csv_records = list(csv.DictReader(f_old))

    old_jsonl_records = load_jsonl(str(out_jsonl))

    merged_jsonl = merge_record_lists([dict(r) for r in records], old_jsonl_records)
    merged_csv = merge_record_lists([dict(r) for r in records], old_csv_records)

    columns = compute_csv_columns(old_csv_records + merged_csv)

    with open(out_jsonl, "w", encoding="utf-8") as f_out:
        for rec in merged_jsonl:
            f_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    write_csv(str(out_csv), merged_csv, columns)
    print(f"Done.\nDB: {db_path}\nJSONL: {out_jsonl}\nCSV: {out_csv}\nRecords: {len(merged_csv)}")


if __name__ == "__main__":
    main()
