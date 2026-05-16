@echo off
title Math Agent Grade 8
cd /d "%~dp0"

echo ================================================
echo   Math Agent for Grade 8
echo ================================================
echo.

:: Try to add firewall rule (may need admin)
netsh advfirewall firewall add rule name="Math Agent Grade 8" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [Firewall] Port 5000 opened successfully.
) else (
    echo [Warning] Could not open firewall port. Run as Administrator if other PCs cannot connect.
)
echo.

:: Get LAN IP
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do set LOCAL_IP=%%a
set LOCAL_IP=%LOCAL_IP: =%

echo ================================================
echo   Access URLs:
echo   Local:   http://localhost:5000
echo   Network: http://%LOCAL_IP%:5000
echo   Account: admin / admin123
echo ================================================
echo.

echo Starting application...
echo.
python_portable\python.exe app.py
pause
