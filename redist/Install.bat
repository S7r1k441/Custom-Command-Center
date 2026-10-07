@echo off
setlocal
title Custom Command Center - Setup

set "INSTALL_DIR=%LOCALAPPDATA%\CustomCommandCenter"
set "SRC=%~dp0CustomCommandCenter.exe"
set "SRC_VER_FILE=%~dp0VERSION"
set "DEST_EXE=%INSTALL_DIR%\CustomCommandCenter.exe"
set "DEST_VER_FILE=%INSTALL_DIR%\VERSION"

echo ============================================
echo   Custom Command Center - Setup
echo ============================================
echo.

if not exist "%SRC%" (
    echo ERROR: CustomCommandCenter.exe was not found next to this Install.bat.
    echo Make sure you extracted the whole redist folder before running this.
    pause
    exit /b 1
)

set "NEW_VER=unknown"
if exist "%SRC_VER_FILE%" set /p NEW_VER=<"%SRC_VER_FILE%"

set "OLD_VER="
if exist "%DEST_VER_FILE%" set /p OLD_VER=<"%DEST_VER_FILE%"

if not exist "%DEST_EXE%" (
    echo Installing version %NEW_VER% to: %INSTALL_DIR%
    if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
    copy /Y "%SRC%" "%DEST_EXE%" >nul
    if not "%NEW_VER%"=="unknown" (
        > "%DEST_VER_FILE%" echo %NEW_VER%
    )
) else (
    if "%NEW_VER%"=="unknown" (
        echo Found an existing installation - reinstalling...
        call :do_upgrade
        if errorlevel 1 exit /b 1
    ) else (
        if "%OLD_VER%"=="%NEW_VER%" (
            echo Version %NEW_VER% is already installed and up to date - nothing to do.
        ) else (
            if "%OLD_VER%"=="" (
                echo Found an existing installation - upgrading to version %NEW_VER%...
            ) else (
                echo Found version %OLD_VER% installed - upgrading to version %NEW_VER%...
            )
            call :do_upgrade
            if errorlevel 1 exit /b 1
        )
    )
)

goto :after_install

:do_upgrade
echo Closing any running copy of Custom Command Center...
taskkill /IM CustomCommandCenter.exe /F >nul 2>&1
ping -n 2 127.0.0.1 >nul 2>&1
copy /Y "%SRC%" "%DEST_EXE%" >nul
if errorlevel 1 (
    echo.
    echo Could not replace the installed copy - it may still be running.
    echo Please close Custom Command Center and run Install.bat again.
    pause
    exit /b 1
)
if not "%NEW_VER%"=="unknown" > "%DEST_VER_FILE%" echo %NEW_VER%
exit /b 0

:after_install
echo Creating Desktop shortcut...
set "VBS=%TEMP%\ccc_shortcut_desktop.vbs"
> "%VBS%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>> "%VBS%" echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Custom Command Center.lnk"
>> "%VBS%" echo Set oLink = oWS.CreateShortcut(sLinkFile)
>> "%VBS%" echo oLink.TargetPath = "%DEST_EXE%"
>> "%VBS%" echo oLink.WorkingDirectory = "%INSTALL_DIR%"
>> "%VBS%" echo oLink.IconLocation = "%DEST_EXE%"
>> "%VBS%" echo oLink.Description = "Custom Command Center"
>> "%VBS%" echo oLink.Save
cscript //nologo "%VBS%"
del "%VBS%"

echo Creating Start Menu shortcut...
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "VBS2=%TEMP%\ccc_shortcut_startmenu.vbs"
> "%VBS2%" echo Set oWS = WScript.CreateObject("WScript.Shell")
>> "%VBS2%" echo sLinkFile = "%STARTMENU%\Custom Command Center.lnk"
>> "%VBS2%" echo Set oLink = oWS.CreateShortcut(sLinkFile)
>> "%VBS2%" echo oLink.TargetPath = "%DEST_EXE%"
>> "%VBS2%" echo oLink.WorkingDirectory = "%INSTALL_DIR%"
>> "%VBS2%" echo oLink.IconLocation = "%DEST_EXE%"
>> "%VBS2%" echo oLink.Description = "Custom Command Center"
>> "%VBS2%" echo oLink.Save
cscript //nologo "%VBS2%"
del "%VBS2%"

echo.
echo ============================================
echo   Done! No other setup needed - it's ready to use.
echo   A shortcut is on your Desktop and in the Start Menu.
echo ============================================
echo.

set /p LAUNCH="Launch Custom Command Center now? (Y/N): "
if /I "%LAUNCH%"=="Y" start "" "%DEST_EXE%"

echo.
pause
