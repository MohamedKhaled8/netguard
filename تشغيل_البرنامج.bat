@echo off
title NetGuard AI — Autonomous Network Intelligence & Self-Healing
cd /d "%~dp0"

echo ======================================================================
echo   NETGUARD AI - جاري تشغيل واجهة البرنامج الرسومية...
echo ======================================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py gui
) else (
    uv run python main.py gui
)

if errorlevel 1 (
    echo.
    echo حدث خطأ أثناء تشغيل البرنامج.
    pause
)
