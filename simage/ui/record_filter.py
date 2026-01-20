import csv
import os
from typing import List, Dict

def load_records(csv_path: str) -> List[Dict]:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def filter_records(records: List[Dict], query: str) -> List[Dict]:
    if not query:
        return records
    q = query.lower()
    def match(rec):
        return any(q in (str(rec.get(col, "")).lower()) for col in rec)
    return [rec for rec in records if match(rec)]

def filter_by_tags(records: List[Dict], tags: List[str]) -> List[Dict]:
    if not tags:
        return records
    tags = [t.lower() for t in tags]
    def match(rec):
        prompt = rec.get("prompt", "").lower()
        return all(tag in prompt for tag in tags)
    return [rec for rec in records if match(rec)]
