@echo off
setlocal
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (
    py src\main.py
) else (
    python src\main.py
)

endlocal
