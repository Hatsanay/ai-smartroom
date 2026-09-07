@echo off
REM ============================================================
REM  dev.bat  - one click: run the จาร์วิส web server (dev)
REM   1) cancel : kill whatever is holding port 8000
REM   2) activate venv
REM   3) run server.py  + open the browser automatically
REM ============================================================
setlocal
cd /d "%~dp0jarvis-ai"

echo [dev] 1/3  Freeing port 8000 (killing old server if any)...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo       - taskkill PID %%p
    taskkill /F /PID %%p >nul 2>&1
)

if not exist "venv\Scripts\activate.bat" (
    echo [dev] venv not found at jarvis-ai\venv - create it first:
    echo       cd jarvis-ai ^&^& python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

echo [dev] 2/3  Activating virtual environment...
call venv\Scripts\activate.bat

echo [dev] 3/3  Starting server + opening browser...  (Ctrl+C to stop)
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000/"
python server.py

echo.
echo [dev] Server stopped.
pause
endlocal
