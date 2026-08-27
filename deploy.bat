@echo off
setlocal
cd /d "%~dp0"

if not exist ".git" (
    echo [deploy] No git repo found here yet - initializing...
    git init
    git branch -M main
    git remote add origin https://github.com/Hatsanay/ai-smartroom.git
)

echo.
echo [deploy] Current status:
git status
echo.

set "MSG=%~1"
if "%MSG%"=="" set "MSG=Update"

echo [deploy] Will commit with message: "%MSG%" and push to origin/main.
echo [deploy] Press Ctrl+C now to cancel, or any other key to continue.
pause >nul

git add .
git commit -m "%MSG%"
git push -u origin main

echo.
echo [deploy] Done.
pause
endlocal
