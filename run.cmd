
@echo off
setlocal
set "REPO_ROOT=%~dp0"
pushd "%REPO_ROOT%"

REM Create venv if missing
if not exist .venv (
	python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install requirements if needed
pip install -r SimageUI\requirements.txt

python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl
python .\aiimagepipe.py all

REM Deactivate venv on close
call deactivate

popd
