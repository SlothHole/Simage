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

# ...existing code...