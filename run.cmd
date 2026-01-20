@echo off
setlocal

cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
	python -m venv .venv
)
if not exist "%PY%" (
	set "PY=python"
)

%PY% -m pip --version >nul 2>&1
if errorlevel 1 (
	%PY% -m ensurepip --upgrade >nul 2>&1
	%PY% -m pip --version >nul 2>&1
)
if errorlevel 1 (
	echo pip not available; skipping dependency install.
) else (
	%PY% -m pip install -r simage\ui\requirements.txt
)

set "EXIFTOOL=exiftool"
if exist ".\exiftool-13.45_64\ExifTool.exe" (
	set "EXIFTOOL=.\exiftool-13.45_64\ExifTool.exe"
)

%PY% -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl --exiftool "%EXIFTOOL%"
%PY% -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv
%PY% -m simage.ui.app
endlocal
