@echo off
setlocal
cd /d "%~dp0"
set "PATH=C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0;C:\Users\hi\AppData\Local\Programs\Python\Python314;C:\Users\hi\AppData\Local\Programs\Python\Python314\Scripts;%PATH%"

echo =====================================================================
echo Starting Kifayat Context Gateway ^& Helpdesk (http://127.0.0.1:8000)
echo =====================================================================

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
