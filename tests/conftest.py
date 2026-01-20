import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

# Ensure repo root is on sys.path for test discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force temp paths under .venv when available (keeps pytest temp under ignored dirs).
_REPO_ROOT = Path(__file__).resolve().parents[1]
_VENV_ROOT = _REPO_ROOT / ".venv"
_TMP_ROOT = (_VENV_ROOT / ".pytest_tmp") if _VENV_ROOT.is_dir() else (_REPO_ROOT / ".pytest_tmp_work")
_TMP_ROOT.mkdir(parents=True, exist_ok=True)
_RUN_ROOT = _TMP_ROOT / f"run_{uuid.uuid4().hex}"
_RUN_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(_RUN_ROOT)
os.environ["TEMP"] = str(_RUN_ROOT)
os.environ["TMP"] = str(_RUN_ROOT)
tempfile.tempdir = str(_RUN_ROOT)


@pytest.fixture
def tmp_path() -> Path:
    base = _RUN_ROOT / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid.uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
