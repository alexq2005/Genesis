@echo off
chcp 65001 >nul 2>&1
title GENESIS Desktop — Tipo Copilot
cd /d "%~dp0"

echo =======================================
echo   GENESIS Desktop App
echo   Ctrl+Shift+G = Mostrar/Ocultar
echo =======================================
echo.

:: Limpiar cache Python antes de iniciar
if exist __pycache__ rd /s /q __pycache__ >nul 2>&1
if exist core\__pycache__ rd /s /q core\__pycache__ >nul 2>&1

:: Iniciar Genesis como app nativa (sidebar derecha)
python genesis_desktop.py --right

pause
