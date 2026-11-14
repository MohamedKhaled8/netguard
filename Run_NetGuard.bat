@echo off
title NetGuard AI — Autonomous Network Intelligence & Self-Healing
cd /d "%~dp0"

echo ======================================================================
echo   Launching NetGuard AI Desktop Application...
echo ======================================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py gui
) else (
    uv run python main.py gui
)

if errorlevel 1 (
    echo.
    echo NetGuard AI encountered an error during startup.
    pause
)
