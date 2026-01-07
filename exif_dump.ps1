<#
Run from: repository root (this directory)
Example:
  .\exif_dump.ps1 -InputPath ".\Input" -OutJsonl ".\out\exif_raw.jsonl"

Requires:
  exiftool.exe in PATH (recommended) OR set $ExifToolPath below.
#>

param(
  [string]$InputPath = ".\\Input",
  [string]$OutJsonl = ".\\out\\exif_raw.jsonl",
  [string]$ExifToolPath = "exiftool"
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $repoRoot
try {
  python .\exif_dump.py --input $InputPath --out $OutJsonl --exiftool $ExifToolPath
}
finally {
  Pop-Location
}
