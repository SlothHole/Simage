@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
	python -m venv .venv
)

call .\.venv\Scripts\activate.bat

pip install -r simage\ui\requirements.txt

set "EXIFTOOL=exiftool"
if exist ".\exiftool-13.45_64\ExifTool.exe" (
	set "EXIFTOOL=.\exiftool-13.45_64\ExifTool.exe"
)

python -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl --exiftool "%EXIFTOOL%"
python -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv
python -m simage.ui.app

deactivate
endlocal
