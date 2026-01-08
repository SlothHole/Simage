from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/TryCode')))
from core import main

def test_main_returns_int() -> None:
    assert isinstance(main(), int)

