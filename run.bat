@echo off
cd /d "%~dp0"
REM Usa el venv del proyecto (creado por setup.bat). Si no existe, avisa.
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno virtual ^(venv^). Ejecuta setup.bat primero.
    pause
    exit /b 1
)
"venv\Scripts\python.exe" genesis.py
pause
