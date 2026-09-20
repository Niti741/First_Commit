@echo off
setlocal
echo =====================================================================
echo Starting Kifayat Intelligent Context Gateway ^& Helpdesk (Local Mode)
echo =====================================================================
echo.

REM Always switch to the project root directory
cd /d "%~dp0\.."

if not exist ".env" (
    echo [.env not found, copying from .env.example...]
    copy .env.example .env
)

echo Working Directory: %CD%
echo Starting FastAPI server at http://127.0.0.1:8000 ...
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
