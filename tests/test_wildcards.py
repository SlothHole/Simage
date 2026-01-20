import pytest
import sqlite3
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simage.export_wildcards import table_exists, apply_filters

def test_table_exists(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER)")
    assert table_exists(conn, "test")
    assert not table_exists(conn, "missing")
    conn.close()

def test_apply_filters():
    items = [("foo", 10), ("bar", 5), ("baz", 20)]
    # min_count
    filtered = apply_filters(items, None, None, 10, None)
    assert filtered == [("foo", 10), ("baz", 20)]
    # max_count
    filtered = apply_filters(items, None, None, 0, 10)
    assert filtered == [("foo", 10), ("bar", 5)]
    # include_re
    import re
    filtered = apply_filters(items, re.compile("ba"), None, 0, None)
    assert filtered == [("bar", 5), ("baz", 20)]
    # exclude_re
    filtered = apply_filters(items, None, re.compile("ba"), 0, None)
    assert filtered == [("foo", 10)]
