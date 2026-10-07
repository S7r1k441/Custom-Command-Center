# Builds Custom Command Center.exe into dist\ using the project's venv.
# Run from the project root: .\build.ps1

$ErrorActionPreference = "Stop"
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv (Join-Path $PSScriptRoot ".venv")
}

Write-Host "Installing dependencies..."
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements.txt") --quiet

Write-Host "Building executable with PyInstaller..."
& $venvPython -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "CustomCommandCenter" `
    --icon (Join-Path $PSScriptRoot "resources\icon.ico") `
    --hidden-import tkinter `
    --collect-all tkinter `
    (Join-Path $PSScriptRoot "main.py")

Write-Host "Updating redist folder (exe + version marker)..."
$redist = Join-Path $PSScriptRoot "redist"
Copy-Item (Join-Path $PSScriptRoot "dist\CustomCommandCenter.exe") (Join-Path $redist "CustomCommandCenter.exe") -Force
$version = & $venvPython -c "from app.version import APP_VERSION; print(APP_VERSION, end='')"
Set-Content -Path (Join-Path $redist "VERSION") -Value $version -NoNewline -Encoding ascii

Write-Host ""
Write-Host "Done. Executable is at dist\CustomCommandCenter.exe (version $version)"
Write-Host "redist\ is updated - rerun Install.bat there to upgrade an existing install, or re-zip redist\ to share."
