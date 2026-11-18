@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py -V:3.14"
)
%PY% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.14 was not found. See START_HERE.md.
    pause
    exit /b 1
)
%PY% -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Installing AstroHealth requirements...
    %PY% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installation failed. See START_HERE.md.
        pause
        exit /b 1
    )
)
echo Starting AstroHealth. Open http://127.0.0.1:8001
%PY% -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
pause
