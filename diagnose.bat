@echo off
REM BankU Diagnostic Tools - Windows Batch Script
REM Quick access to all diagnostic tools

:menu
cls
echo ============================================================
echo               BankU Diagnostic Tools
echo ============================================================
echo.
echo 1. Remote Diagnostic (Test from outside)
echo 2. Server Diagnostic (Run on server)
echo 3. Apply Session Fix (Fix hanging issue)
echo 4. Quick Health Check
echo 5. Read Diagnostic Guide
echo 6. Exit
echo.
echo ============================================================
set /p choice="Select option (1-6): "

if "%choice%"=="1" goto remote
if "%choice%"=="2" goto server
if "%choice%"=="3" goto fix
if "%choice%"=="4" goto health
if "%choice%"=="5" goto guide
if "%choice%"=="6" goto end

echo Invalid choice!
timeout /t 2
goto menu

:remote
cls
echo Running Remote Diagnostic...
echo.
python diagnose_app.py
echo.
pause
goto menu

:server
cls
echo Running Server-Side Diagnostic...
echo.
python server_diagnostics.py
echo.
pause
goto menu

:fix
cls
echo ============================================================
echo               APPLY SESSION FIX
echo ============================================================
echo.
echo WARNING: This will modify your app.py file
echo A backup will be created automatically
echo.
set /p confirm="Do you want to continue? (yes/no): "
if /i "%confirm%"=="yes" (
    python apply_session_fix.py
) else (
    echo Cancelled.
)
echo.
pause
goto menu

:health
cls
echo Running Quick Health Check...
echo.
python monitor_health.py
echo.
pause
goto menu

:guide
cls
type DIAGNOSTIC_GUIDE.md | more
echo.
pause
goto menu

:end
echo.
echo Goodbye!
timeout /t 1
exit


