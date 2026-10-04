@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3.10-3.12 and the Windows py launcher are required. Install Python 3.12 and retry.& pause & exit /b 1)
if not exist backend\.venv\Scripts\python.exe py -3.12 -m venv backend\.venv
if not exist backend\.venv\Scripts\python.exe (echo Could not create the Python 3.12 environment.& pause & exit /b 1)
call backend\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if errorlevel 1 (echo Backend dependency installation failed.& pause & exit /b 1)
start "WeldSight API" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0backend\.venv\Scripts\python.exe"" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
where npm >nul 2>nul || (echo Node.js 18+ and npm are required. Install Node.js and retry.& pause & exit /b 1)
cd frontend
if not exist node_modules call npm install
if errorlevel 1 (echo Frontend dependency installation failed.& pause & exit /b 1)
call npm run dev
