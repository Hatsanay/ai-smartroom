@echo off
REM ============================================================
REM  setup.bat  - run ONCE right after cloning
REM   0) install Python 3.10+ if missing (via winget)
REM   1) create venv in jusmin-ai\
REM   2) pip install -r requirements.txt
REM   3) create jusmin-ai\.env (asks for your Gemini API key)
REM  after this: double-click  dev.bat  to run the web app
REM ============================================================
setlocal
set "ROOT=%~dp0"

echo [setup] 0/3  Checking Python...
python --version >nul 2>&1
if errorlevel 1 goto NO_PYTHON
python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)"
if errorlevel 1 goto OLD_PYTHON
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo        found Python %%v
goto HAVE_PYTHON

:NO_PYTHON
echo [setup] Python not found on PATH.
where winget >nul 2>&1
if errorlevel 1 (
    echo [setup] winget is not available. Install Python 3.10+ manually:
    echo         https://www.python.org/downloads/   ^(tick "Add python.exe to PATH"^)
    start "" https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [setup] Installing Python 3.12 via winget...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
echo.
echo [setup] Python installed. CLOSE this window and run setup.bat again
echo         (a new window is needed so PATH picks up python).
pause
exit /b 0

:OLD_PYTHON
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo [setup] Python %%v is too old - need 3.10 or newer.
echo         Get a newer one: https://www.python.org/downloads/
start "" https://www.python.org/downloads/
pause
exit /b 1

:HAVE_PYTHON
cd /d "%ROOT%jusmin-ai"

echo [setup] 1/3  Creating virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo        venv already exists - keeping it
) else (
    python -m venv venv
    if errorlevel 1 ( echo [setup] failed to create venv & pause & exit /b 1 )
)
call venv\Scripts\activate.bat

echo [setup] 2/3  Installing dependencies ^(first time can take a few minutes^)...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 ( echo [setup] pip install failed - check the errors above & pause & exit /b 1 )

echo [setup] 3/3  Setting up jusmin-ai\.env ...
if exist ".env" goto ENV_OK
set "GKEY="
set /p GKEY=        Paste your Gemini API key ^(Enter to skip and edit .env later^):
> .env echo GEMINI_API_KEY=%GKEY%
if "%GKEY%"=="" ( echo        wrote empty .env - remember to edit it! ) else ( echo        wrote .env )
:ENV_OK

echo.
echo ============================================================
echo  [setup] Done.
echo   - Gemini API key ^(free^): https://aistudio.google.com  -> put it in  jusmin-ai\.env
echo   - Start the app:  double-click  dev.bat  in the repo root
echo ============================================================
pause
endlocal
