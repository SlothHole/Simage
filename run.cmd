@echo off
setlocal

set "REPO_ROOT=%~dp0"
pushd "%REPO_ROOT%"

python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl
python .\aiimagepipe.py all

popd
