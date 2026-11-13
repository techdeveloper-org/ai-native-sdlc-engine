@echo off
REM Add AI-Native SDLC Engine to Windows Startup Folder (No Admin Required)

setlocal

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_NAME=AI-Native SDLC Engine Server.lnk
set TARGET_SCRIPT=%~dp0start-ai-native-sdlc-engine.bat

echo.
echo ========================================
echo   Add AI-Native SDLC Engine to Startup Folder
echo ========================================
echo.
echo Startup Folder: %STARTUP_FOLDER%
echo Target Script: %TARGET_SCRIPT%
echo.

REM Create shortcut using PowerShell
powershell -Command ^
"$WshShell = New-Object -ComObject WScript.Shell; ^
$Shortcut = $WshShell.CreateShortcut('%STARTUP_FOLDER%\%SHORTCUT_NAME%'); ^
$Shortcut.TargetPath = '%TARGET_SCRIPT%'; ^
$Shortcut.WorkingDirectory = '%~dp0..'; ^
$Shortcut.WindowStyle = 7; ^
$Shortcut.Description = 'Start AI-Native SDLC Engine Server on Login'; ^
$Shortcut.Save()"

if %ERRORLEVEL% EQU 0 (
    echo [OK] Shortcut created successfully!
    echo [OK] Location: %STARTUP_FOLDER%\%SHORTCUT_NAME%
    echo.
    echo AI-Native SDLC Engine will start automatically on next login!
) else (
    echo [ERROR] Failed to create shortcut
)

echo.
pause

endlocal
