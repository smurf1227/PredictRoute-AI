@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn ml_backend:app --host 127.0.0.1 --port 8000
) else (
    py -m uvicorn ml_backend:app --host 127.0.0.1 --port 8000
)
