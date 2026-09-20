@echo off
set "PATH=C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0;C:\Users\hi\AppData\Local\Programs\Python\Python314;C:\Users\hi\AppData\Local\Programs\Python\Python314\Scripts;%PATH%"
set "PYTHONUNBUFFERED=1"
C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -ExecutionPolicy Bypass -NoProfile -NonInteractive %*
