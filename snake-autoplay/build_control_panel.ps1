# Builds "Snake Autoplay Cheat.exe" - a separate, standalone control panel that
# connects to the hidden autoplay hook inside an already-running Custom Command
# Center. Uses the main project's existing venv (PySide6 is already installed there).
# This folder is never touched by the main project's build.ps1 or its release zip.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$venvPython = Join-Path $root "..\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "Could not find the main project's virtual environment at $venvPython - set that up first (see the main project's build.ps1)."
}

Write-Host "Building Snake Autoplay Cheat.exe..."
& $venvPython -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name "SnakeAutoplayCheat" `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build") `
    --specpath $root `
    (Join-Path $root "autoplay_control_panel.py")

Copy-Item (Join-Path $root "dist\SnakeAutoplayCheat.exe") (Join-Path $root "Snake Autoplay Cheat.exe") -Force
Write-Host ""
Write-Host "Done: $root\Snake Autoplay Cheat.exe"
