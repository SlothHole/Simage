import os
from simage.core.ingest import sha256_file_backup

def test_sha256_file_backup(tmp_path):
    tmp_file = tmp_path / "hash.bin"
    tmp_file.write_bytes(b"testdata")
    hash_val = sha256_file_backup(os.fspath(tmp_file))
    assert isinstance(hash_val, str)
