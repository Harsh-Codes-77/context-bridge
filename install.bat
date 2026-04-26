@echo off
setlocal enabledelayedexpansion
title context-bridge Installer

echo.
echo  ██████╗ ██████╗ ███╗   ██╗████████╗███████╗██╗  ██╗████████╗       ██████╗ ██████╗ ██╗██████╗  ██████╗ ███████╗
echo ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝      ██╔══██╗██╔══██╗██║██╔══██╗██╔════╝ ██╔════╝
echo ██║     ██║   ██║██╔██╗ ██║   ██║   █████╗   ╚███╔╝    ██║    █████╗██████╔╝██████╔╝██║██║  ██║██║  ███╗█████╗
echo ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══╝   ██╔██╗    ██║    ╚════╝██╔══██╗██╔══██╗██║██║  ██║██║   ██║██╔══╝
echo ╚██████╗╚██████╔╝██║ ╚████║   ██║   ███████╗██╔╝ ██╗   ██║          ██████╔╝██║  ██║██║██████╔╝╚██████╔╝███████╗
echo  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝   ╚═╝          ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝  ╚═════╝ ╚══════╝
echo.
echo  Windows Installer
echo  ==========================================
echo.

REM --- Step 1: Check Python -------------------------------------------------
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found!
    echo  Please install Python 3.9+ from https://python.org/downloads
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if !PY_MAJOR! LSS 3 (
    echo  ERROR: Python 3.9+ required, found %PYVER%
    pause
    exit /b 1
)

if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 9 (
    echo  ERROR: Python 3.9+ required, found %PYVER%
    pause
    exit /b 1
)

echo  OK - Python %PYVER% found
echo.

REM --- Step 2: Create Virtual Environment ----------------------------------
echo [2/5] Creating virtual environment...
if exist "venv\" (
    echo  venv already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo  OK - Virtual environment created
)
echo.

REM --- Step 3: Activate & Install ------------------------------------------
echo [3/5] Installing context-bridge...
call venv\Scripts\activate.bat

python -m pip install --upgrade pip setuptools wheel >nul

pip install -e . --quiet
if errorlevel 1 (
    echo  ERROR: Installation failed!
    echo  Try running as Administrator.
    pause
    exit /b 1
)
echo  OK - context-bridge installed
echo.

REM --- Step 4: Add cb to PATH permanently ----------------------------------
echo [4/5] Adding 'cb' command to your system PATH...

set "CB_PATH=%CD%\venv\Scripts"

REM Check if already in PATH
echo %PATH% | find /i "%CB_PATH%" >nul
if errorlevel 1 (
    REM Add to user PATH permanently using setx
    for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

    if "!CURRENT_PATH!"=="" (
        setx PATH "%CB_PATH%"
    ) else (
        setx PATH "!CURRENT_PATH!;%CB_PATH%"
    )
    echo  OK - Added to PATH (restart terminal to use 'cb' globally)
) else (
    echo  OK - Already in PATH
)
echo.

REM --- Step 5: Create quick-launch shortcut --------------------------------
echo [5/5] Creating quick launch script...
set "LAUNCHER=%USERPROFILE%\cb.bat"
echo @echo off > "%LAUNCHER%"
echo call "%CD%\venv\Scripts\activate.bat" >> "%LAUNCHER%"
echo cb %%* >> "%LAUNCHER%"
echo  OK - Launcher created
echo.

REM --- Done -----------------------------------------------------------------
echo  ==========================================
echo  context-bridge installed successfully!
echo  ==========================================
echo.
echo  Next steps:
echo.
echo   1. Close and reopen your terminal (Command Prompt or PowerShell)
echo   2. Run: cb init
echo   3. Run: cb status
echo   4. If cb is still not found, run: %LAUNCHER% init
echo.
echo  Dashboard: cb web  (opens at http://localhost:4242)
echo.
pause
