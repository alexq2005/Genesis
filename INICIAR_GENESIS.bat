@echo off
chcp 65001 >nul 2>&1
title GENESIS — IA Auto-Evolutiva
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno virtual ^(venv^). Ejecuta setup.bat primero.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" genesis.py
pause
