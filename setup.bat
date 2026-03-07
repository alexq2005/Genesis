@echo off
echo ══════════════════════════════════════════════════
echo          GENESIS — Setup de Instalacion
echo ══════════════════════════════════════════════════
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo Descargalo de: https://python.org/downloads
    echo Asegurate de marcar "Add to PATH" durante la instalacion.
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version
echo.

REM Verificar si Ollama esta instalado
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Ollama no esta instalado.
    echo Para usar Genesis con IA local gratuita:
    echo   1. Descarga Ollama: https://ollama.com/download
    echo   2. Instala y ejecuta: ollama serve
    echo   3. Descarga un modelo: ollama pull llama3.1
    echo.
    echo Alternativa: Configura una API key en config.py
    echo   - OpenAI: set OPENAI_API_KEY=tu-key
    echo   - Anthropic: set ANTHROPIC_API_KEY=tu-key
) else (
    echo [OK] Ollama encontrado:
    ollama --version
    echo.
    echo Descargando modelo llama3.1 (puede tardar unos minutos)...
    ollama pull llama3.1
)

echo.
echo ══════════════════════════════════════════════════
echo  Setup completado. Para iniciar Genesis:
echo.
echo    python genesis.py
echo.
echo ══════════════════════════════════════════════════
pause
