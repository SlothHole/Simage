Set-StrictMode -Version Latest

$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# Create venv if missing and prefer its python, without activation.
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $venvPython)) {
	try {
		python -m venv .venv
	} catch {
		Write-Warning "Failed to create .venv; falling back to system python."
	}
}
if (Test-Path $venvPython) {
	$py = $venvPython
} else {
	$py = "python"
}

function Ensure-Pip([string]$pythonExe) {
	try {
		& $pythonExe -m pip --version | Out-Null
		return $true
	} catch {
		try {
			& $pythonExe -m ensurepip --upgrade | Out-Null
			& $pythonExe -m pip --version | Out-Null
			return $true
		} catch {
			return $false
		}
	}
}

# Install requirements if pip is available
if (Ensure-Pip $py) {
	& $py -m pip install -r simage\ui\requirements.txt
} else {
	Write-Warning "pip not available; skipping dependency install."
}

# Run EXIF extraction (prefer bundled ExifTool)
$exifTool = Join-Path $repoRoot "exiftool-13.45_64\ExifTool.exe"
if (!(Test-Path $exifTool)) {
	$exifTool = "exiftool"
}
& $py -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl --exiftool $exifTool

# Run full pipeline
& $py -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv

# Launch UI
& $py -m simage.ui.app
