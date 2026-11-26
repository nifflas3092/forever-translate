@echo off
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
py -3.14 --version >nul 2>nul && set "PY=py -3.14"
if not exist .venv (
  echo First run: setting things up, this takes a minute...
  %PY% -m venv .venv || goto nopython
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
.venv\Scripts\python forever_translate.py %*
if errorlevel 1 pause
exit /b
:nopython
echo Python 3 is needed. Install it from https://www.python.org/downloads/
echo (tick "Add python.exe to PATH" in the installer), then run this again.
pause
