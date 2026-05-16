@echo off
title Math Agent - Quick Tunnel Mode
cd /d "%~dp0"

echo ================================================
echo   Math Agent - Quick Tunnel Mode
echo ================================================
echo.

echo Starting background services...
if exist public_url.txt del public_url.txt
if exist service_pids.txt del service_pids.txt

cscript //nologo launcher_quick.vbs

echo Waiting for tunnel URL...
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
echo   Temp  URL : %URL%
echo   Local URL : http://localhost:5000
echo   Account   : admin / admin123
echo ================================================
echo.
echo Close this window to stop the service.
echo.
pause
exit

:fail
echo.
echo Failed to get tunnel URL.
echo Check bg_debug.log for details.
echo.
pause
