Set-StrictMode -Version Latest

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# Create venv if missing
if (!(Test-Path ".venv")) {
	python -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r simage\ui\requirements.txt

# Run EXIF extraction (prefer bundled ExifTool)
$exifTool = Join-Path $repoRoot "exiftool-13.45_64\ExifTool.exe"
if (!(Test-Path $exifTool)) {
	$exifTool = "exiftool"
}
python -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl --exiftool $exifTool

# Run full pipeline
python -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv

# Launch UI
python -m simage.ui.app

deactivate
