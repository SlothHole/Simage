
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

# Create venv if missing
if (!(Test-Path ".venv")) {
	python -m venv .venv
}

# Activate venv
. .\.venv\Scripts\Activate.ps1

# Install requirements if needed
pip install -r SimageUI\requirements.txt

python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl
python .\aiimagepipe.py all

# Deactivate venv on close
deactivate
