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
"""
Run from: repository root (this directory)
Example:
	python .\normalize_and_ingest.py --in .\out\exif_raw.jsonl --db .\out\images.db --jsonl .\out\records.jsonl --csv .\out\records.csv

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

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import uuid
from typing import Any, Dict, List, Optional, Tuple

from simage.path_utils import resolve_repo_path, resolve_repo_relative

# ...existing code...