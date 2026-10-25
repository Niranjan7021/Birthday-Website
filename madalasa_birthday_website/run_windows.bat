@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo Python was not found. Install Python 3.11+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
 pause
 exit /b 1
)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
python app.py
pause
