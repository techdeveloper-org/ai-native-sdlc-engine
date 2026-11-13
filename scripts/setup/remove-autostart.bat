@echo off
REM Remove AI-Native SDLC Engine Auto-Start

setlocal

set TASK_NAME=ClaudeWorkflowEngineServer

echo.
echo ========================================
echo   Remove Auto-Start for AI-Native SDLC Engine
echo ========================================
echo.

REM Check if task exists
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Auto-start task not found
    echo [INFO] AI-Native SDLC Engine is not configured for auto-start
    goto :end
)

echo [INFO] Removing scheduled task: %TASK_NAME%

schtasks /Delete /TN "%TASK_NAME%" /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Auto-start removed successfully!
    echo.
    echo AI-Native SDLC Engine will no longer start automatically on login.
) else (
    echo.
    echo [ERROR] Failed to remove scheduled task
    echo [ERROR] You may need to run this script as Administrator
)

:end
echo.
pause

endlocal
