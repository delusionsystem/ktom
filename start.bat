@echo off
setlocal enabledelayedexpansion
rem KTOM start script (based on universal_start_script.bat)

cd /d "%~dp0"

rem 1. Use the project's virtual environment interpreter so cv2 etc. resolve correctly
set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

rem 2. Read the port from .env (KTOM_PORT), default to 8080
set "PORT=8080"
if exist .env (
    for /f "tokens=2 delims==" %%i in ('findstr /b "KTOM_PORT=" .env') do (
        set "RAW_PORT=%%i"
        set "RAW_PORT=!RAW_PORT: =!"
        set "RAW_PORT=!RAW_PORT:'=!"
        set "RAW_PORT=!RAW_PORT:"=!"
        if not "!RAW_PORT!"=="" set "PORT=!RAW_PORT!"
    )
)

echo ===================================================
echo  SYSTEM: KTOM - Keep Track Of Media
echo  PYTHON: !PYTHON!
echo  PORT  : !PORT!
echo  URL   : http://localhost:!PORT!
echo ===================================================
echo.
echo [-] Rensar gamla processer och cache enbart for port !PORT!...

rem 3. Stäng ENDAST processer som ockuperar just denna port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :!PORT! ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

rem 4. Rensa pycache och tillfälliga filer
for /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
del /s /q *.pyc *.pyo >nul 2>&1
if exist .nicegui rmdir /s /q .nicegui >nul 2>&1
if exist .cache rmdir /s /q .cache >nul 2>&1
if exist .chrome_kiosk_profile rmdir /s /q .chrome_kiosk_profile >nul 2>&1
echo [^+] Systemet rensat och redo.
echo [^+] Startar applikationen...
echo.

rem Starta appen med rätt interpreter
"!PYTHON!" main.py

endlocal
