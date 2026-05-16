@echo off
cd /d "%~dp0"

echo Stopping Math Agent services...

if exist service_pids.txt (
    for /f "tokens=*" %%p in (service_pids.txt) do (
        taskkill /f /pid %%p >nul 2>&1
    )
    del service_pids.txt
)

taskkill /f /im cloudflared.exe >nul 2>&1

if exist public_url.txt del public_url.txt

echo Services stopped.
timeout /t 2 >nul
