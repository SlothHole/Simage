
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

# Create venv if missing
if (!(Test-Path ".venv")) {
	python -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Install requirements if needed
pip install -r simage\ui\requirements.txt

python -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl
python -m simage all

# Deactivate venv on close
deactivate
