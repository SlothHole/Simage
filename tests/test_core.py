from __future__ import annotations

from TryCode.core import main

def test_main_returns_int() -> None:
    assert isinstance(main(), int)

