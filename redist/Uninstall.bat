@echo off
title Custom Command Center - Uninstall

set "INSTALL_DIR=%LOCALAPPDATA%\CustomCommandCenter"

echo This will remove Custom Command Center and its shortcuts.
set /p CONFIRM="Continue? (Y/N): "
if /I not "%CONFIRM%"=="Y" exit /b 0

del /Q "%USERPROFILE%\Desktop\Custom Command Center.lnk" 2>nul
del /Q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Custom Command Center.lnk" 2>nul
rmdir /S /Q "%INSTALL_DIR%" 2>nul

echo Done. (Your saved settings and Python history in %%APPDATA%%\CustomCommandCenter were kept.)
echo If you want those removed too, delete "%APPDATA%\CustomCommandCenter" manually.
pause
