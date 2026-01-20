@echo off
setlocal

cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
set "PY_IS_VENV=1"
if not exist "%PY%" (
	python -m venv .venv
)
if not exist "%PY%" (
	set "PY=python"
	set "PY_IS_VENV=0"
)

set "PIP_OK=0"
%PY% -m pip --version >nul 2>&1
if not errorlevel 1 set "PIP_OK=1"
if "%PIP_OK%"=="0" (
	%PY% -m ensurepip --upgrade >nul 2>&1
	%PY% -m pip --version >nul 2>&1
	if not errorlevel 1 set "PIP_OK=1"
)
if "%PIP_OK%"=="0" if "%PY_IS_VENV%"=="1" (
	echo pip not available in .venv; falling back to system python.
	set "PY=python"
	set "PY_IS_VENV=0"
	%PY% -m pip --version >nul 2>&1
	if not errorlevel 1 set "PIP_OK=1"
	if "%PIP_OK%"=="0" (
		%PY% -m ensurepip --upgrade >nul 2>&1
		%PY% -m pip --version >nul 2>&1
		if not errorlevel 1 set "PIP_OK=1"
	)
)
if "%PIP_OK%"=="1" (
	%PY% -m pip install -r simage\ui\requirements.txt
) else (
	echo pip not available; skipping dependency install.
)

set "EXIFTOOL=exiftool"
if exist ".\exiftool-13.45_64\ExifTool.exe" (
	set "EXIFTOOL=.\exiftool-13.45_64\ExifTool.exe"
)

%PY% -m simage.core.exif --input .\Input --out .\out\exif_raw.jsonl --exiftool "%EXIFTOOL%"
%PY% -m simage all --in out/exif_raw.jsonl --db out/images.db --schema simage/data/schema.sql --jsonl out/records.jsonl --csv out/records.csv
%PY% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
	if "%PIP_OK%"=="1" (
		%PY% -m pip install -r simage\ui\requirements.txt
		%PY% -c "import PySide6" >nul 2>&1
	)
)
if errorlevel 1 (
	echo PySide6 is not available. Install UI deps or fix pip, then rerun.
	exit /b 1
)
%PY% -m simage.ui.app
endlocal
