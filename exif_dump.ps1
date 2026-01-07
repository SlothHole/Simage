<#
Run from: repository root (this directory)
Example:
  .\exif_dump.ps1 -InputPath ".\Input" -OutJsonl ".\out\exif_raw.jsonl"

Requires:
  exiftool.exe in PATH (recommended) OR set $ExifToolPath below.
#>

param(
  [Parameter(Mandatory=$true)][string]$InputPath,
  [Parameter(Mandatory=$true)][string]$OutJsonl,
  [string]$ExifToolPath = "exiftool"
)

# Ensure output directory exists
$parent = Split-Path -Parent $OutJsonl
if ($parent -and !(Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }

# ExifTool notes:
# -a -G1 -s : include duplicates, group names, short tags
# -j        : JSON per file
# -n        : keep numeric values numeric where possible
# -charset  : safer for weird text
# We write JSON arrays from ExifTool and convert to JSONL (one object per line) for streaming.
$tempJson = [System.IO.Path]::GetTempFileName()

& $ExifToolPath `
  -r `
  -a -G1 -s -n `
  -charset utf8 `
  -api largefilesupport=1 `
  -j `
  $InputPath `
  1>$tempJson 2>$null

if (!(Test-Path $tempJson)) { throw "ExifTool failed to produce output." }

# Convert JSON array -> JSONL
$json = Get-Content $tempJson -Raw | ConvertFrom-Json
Remove-Item $tempJson -Force

# Stream out as JSONL
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$sw = New-Object System.IO.StreamWriter($OutJsonl, $false, $utf8NoBom)
try {
  foreach ($obj in $json) {
    $line = ($obj | ConvertTo-Json -Depth 64 -Compress)
    $sw.WriteLine($line)
  }
}
finally {
  $sw.Dispose()
}

Write-Host "Wrote JSONL:" $OutJsonl
Write-Host "Files:" $json.Count
