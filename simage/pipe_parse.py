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

from simage.path_utils import resolve_repo_path

# ...existing code...