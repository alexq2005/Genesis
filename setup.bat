@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ==================================================
echo          GENESIS - Setup de Instalacion
echo ==================================================
echo.

REM --- Buscar Python 3.12 o 3.11 (requerido: numpy/torch no soportan 3.13+) ---
set "PYEXE="
for %%V in (3.12 3.11) do (
    if not defined PYEXE (
        py -%%V --version >nul 2>&1 && set "PYEXE=py -%%V"
    )
)
if not defined PYEXE (
    echo [ERROR] No se encontro Python 3.11 o 3.12.
    echo Genesis necesita 3.11/3.12 ^(numpy/torch no tienen wheels para 3.13+^).
    echo Descargalo de: https://python.org/downloads
    pause
    exit /b 1
)
echo [OK] Usando: %PYEXE%
%PYEXE% --version
echo.

REM --- Crear entorno virtual ---
if not exist "venv\Scripts\python.exe" (
    echo Creando entorno virtual ^(venv^)...
    %PYEXE% -m venv venv
) else (
    echo [OK] El entorno virtual ya existe.
)

REM --- Instalar dependencias en el venv ---
echo.
echo Instalando dependencias ^(puede tardar varios minutos: torch es grande^)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.

REM --- Verificar Ollama ---
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Ollama no esta instalado.
    echo   1. Descarga Ollama: https://ollama.com/download
    echo   2. Instala y ejecuta: ollama serve
    echo   3. Descarga modelos: ollama pull llama3.1 ^&^& ollama pull qwen2.5-coder:7b
) else (
    echo [OK] Ollama encontrado:
    ollama --version
)

echo.
echo ==================================================
echo  Setup completado. Para iniciar Genesis:
echo    run.bat              ^(terminal^)
echo    GENESIS_DESKTOP.bat  ^(app de escritorio^)
echo    venv\Scripts\python web_ui.py   ^(web^)
echo ==================================================
pause
