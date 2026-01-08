import pytest
import os
import tempfile
from simage.pipe_normalize import sha256_file_backup

def test_sha256_file_backup():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b'testdata')
        tmp.flush()
        hash_val = sha256_file_backup(tmp.name)
    assert isinstance(hash_val, str)
    os.remove(tmp.name)
