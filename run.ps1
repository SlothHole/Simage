Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

python .\exif_dump.py --input .\Input --out .\out\exif_raw.jsonl
python .\aiimagepipe.py all
