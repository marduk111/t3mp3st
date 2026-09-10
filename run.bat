@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  set "PY=python"
) else (
  set "PY=py"
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo First run: setting up a private environment for the game...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Could not create a virtual environment. Install Python 3.11 from https://python.org and re-run.
    echo.
    pause
    exit /b 1
  )
  ".venv\Scripts\python" -m pip install --upgrade pip >nul
  ".venv\Scripts\python" -m pip install "pygame-ce>=2.5"
  if errorlevel 1 (
    echo.
    echo Failed to install pygame-ce. Check your internet connection and re-run.
    echo.
    pause
    exit /b 1
  )
)

".venv\Scripts\python" main.py
if errorlevel 1 (
  echo.
  echo The game exited with an error. Tell the developer what you saw.
  echo.
  pause
)