@echo off
title Math Agent - Internet Mode
cd /d "%~dp0"

echo ================================================
echo   Math Agent - Fixed Domain Mode
echo   URL: https://cszxagent.asia
echo ================================================
echo.

echo Starting background services...
if exist public_url.txt del public_url.txt
if exist service_pids.txt del service_pids.txt

:: Launch with VBS for truly detached background process
cscript //nologo launcher_fixed.vbs

echo Waiting for tunnel...
set /a n=0
:loop
timeout /t 1 /nobreak >nul
set /a n+=1
if exist public_url.txt goto show
if %n% geq 30 goto fail
goto loop

:show
set /p URL=<public_url.txt
echo.
echo ================================================
echo.
echo   Fixed URL  : https://cszxagent.asia
echo   Local URL  : http://localhost:5000
echo   Account    : admin / admin123
echo.
echo ================================================
echo.
echo   You may close this window now.
echo   Service keeps running in background.
echo   To stop: double-click stop_service.bat
echo.
pause >nul
exit

:fail
echo.
echo Tunnel failed. Check internet connection.
echo.
pause
