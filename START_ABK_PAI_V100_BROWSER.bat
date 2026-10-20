@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%CD%
start "" http://127.0.0.1:8200/v100/student-home
python -m uvicorn backend.main_v100:app --host 127.0.0.1 --port 8200
endlocal
