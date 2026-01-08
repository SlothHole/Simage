import pytest
import os
import sqlite3
import tempfile
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from simage.pipe_normalize import utc_now_iso, stable_id_for_path, sha256_file, is_probably_json, safe_json_loads, first_present, clean_ws

def test_utc_now_iso_format():
    result = utc_now_iso()
    assert result.endswith('Z')
    assert 'T' in result

def test_stable_id_for_path_consistency():
    path = 'test_image.png'
    id1 = stable_id_for_path(path)
    id2 = stable_id_for_path(path)
    assert id1 == id2
    assert isinstance(id1, str)

def test_sha256_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b'testdata')
        tmp.flush()
        hash_val = sha256_file(tmp.name)
    assert isinstance(hash_val, str)
    os.remove(tmp.name)

def test_is_probably_json():
    assert is_probably_json('{"a":1}')
    assert is_probably_json('[1,2,3]')
    assert not is_probably_json('not json')

def test_safe_json_loads():
    assert safe_json_loads('{"a":1}') == {"a":1}
    assert safe_json_loads('invalid') is None

def test_first_present():
    d = {"a": 1, "b": None}
    assert first_present(d, ["b", "a"]) == 1
    assert first_present(d, ["c"]) is None

def test_clean_ws():
    s = 'a   b\n\n\n\nc'
    cleaned = clean_ws(s)
    assert '\n\n' in cleaned
    assert cleaned.startswith('a')
