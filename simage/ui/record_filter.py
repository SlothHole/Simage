import csv
import os
from typing import Dict, List, Tuple

from simage.utils.paths import REPO_ROOT

SEARCH_SKIP_KEYS = {"workflow_json", "raw_text_preview", "kv", "resources"}


def _record_key(rec: Dict) -> str:
    return rec.get("source_file") or rec.get("file_name") or ""


def _record_image_path(rec: Dict) -> str:
    name = rec.get("file_name")
    if isinstance(name, str) and name:
        return str((REPO_ROOT / "Input" / name).resolve())
    src = rec.get("source_file")
    if isinstance(src, str) and src:
        return str((REPO_ROOT / "Input" / os.path.basename(src)).resolve())
    return ""


def _build_search_blob(rec: Dict) -> str:
    parts = []
    for k, v in rec.items():
        if k.startswith("_") or k in SEARCH_SKIP_KEYS:
            continue
        if v is None:
            continue
        parts.append(str(v))
    return " ".join(parts).lower()


def _parse_query(query: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    field_terms: List[Tuple[str, str]] = []
    free_terms: List[str] = []
    for token in query.split():
        if ":" in token:
            key, val = token.split(":", 1)
            key = key.strip().lower()
            val = val.strip().lower()
            if key and val:
                field_terms.append((key, val))
        else:
            free_terms.append(token.lower())
    return field_terms, free_terms

def load_records(csv_path: str) -> List[Dict]:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    deduped: Dict[str, Dict] = {}
    for rec in rows:
        key = _record_key(rec)
        if not key:
            continue
        deduped[key] = rec

    records = list(deduped.values())
    for rec in records:
        img_path = _record_image_path(rec)
        rec["_image_path"] = img_path
        rec["_missing_original"] = bool(img_path and not os.path.exists(img_path))
        rec["_search_blob"] = _build_search_blob(rec)
        prompt = rec.get("prompt", "") or ""
        rec["_prompt_tags"] = {t.strip().lower() for t in prompt.split(",") if t.strip()}

    return records

def filter_records(records: List[Dict], query: str) -> List[Dict]:
    if not query:
        return records
    field_terms, free_terms = _parse_query(query)
    def match(rec):
        for key, val in field_terms:
            field_val = str(rec.get(key, "")).lower()
            if val not in field_val:
                return False
        if free_terms:
            blob = rec.get("_search_blob", "")
            return all(term in blob for term in free_terms)
        return True
    return [rec for rec in records if match(rec)]

def filter_by_tags(records: List[Dict], tags: List[str]) -> List[Dict]:
    if not tags:
        return records
    tags = [t.lower() for t in tags]
    def match(rec):
        prompt_tags = rec.get("_prompt_tags")
        if not prompt_tags:
            return False
        return all(tag in prompt_tags for tag in tags)
    return [rec for rec in records if match(rec)]
