# GENESIS — Guía de instalación (multi-usuario)

Cada usuario corre su **propia instancia** con sus datos y credenciales separados.
Nada personal viaja al compartir el repo (todo está en `.gitignore`).

## Requisitos
- Windows 10/11
- Python 3.11 o 3.12 (NO 3.13+)
- [Ollama](https://ollama.com) instalado y corriendo
- (Opcional) GPU NVIDIA 8GB+ para los modelos grandes
- (Opcional) Node.js ≥22 para música (reproductor YouTube Music)

## Instalación (1 vez)
1. Cloná o copiá el proyecto.
2. Corré **`setup.bat`** → crea el `venv` e instala dependencias.
3. Descargá los modelos de Ollama:
   ```
   ollama pull genesis          # o el modelo base que uses (llama3.1)
   ollama pull qwen2.5-coder:7b # para desarrollo de código
   ```
4. **Copiá `.env.example` → `.env`** y completá TUS valores (ver abajo).
5. Arrancá: **`GENESIS_DESKTOP.bat`** (o `venv\Scripts\pythonw genesis_desktop.py --right`).

En el primer arranque se crean tus carpetas de datos **vacías** (memoria, índices,
perfiles) — cada usuario tiene las suyas.

## Configuración del `.env` (cada usuario la suya)
Todo es **opcional** salvo el provider de LLM. Copiá `.env.example` y llená:

| Variable | Para qué | Cómo obtenerla |
|---|---|---|
| `GOOGLE_API_KEY` | Usar Gemini (rápido, gratis) en vez de Ollama local | aistudio.google.com |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | Que Genesis **envíe** emails | App Password de Gmail (ver nota) |
| `GMAIL_READ_USER` / `GMAIL_READ_APP_PASSWORD` | Que Genesis **lea** tu inbox | App Password de tu cuenta |

> **Nota App Password (Gmail)**: la contraseña normal NO sirve. Activá Verificación
> en 2 pasos (myaccount.google.com/signinoptions/two-step-verification) y generá una
> App Password de 16 letras (myaccount.google.com/apppasswords). Es revocable.

## Qué NO se comparte (queda en cada PC)
`.env`, `memory_data/`, `data/`, `evolution_data/`, `logs/`, `backups/`,
`generated_media/`, el perfil de Chrome de música — todo gitignored. **Tus
credenciales y datos nunca salen de tu máquina.**

## Verificar que anda
```
venv\Scripts\python tests\test_v3_0_capabilities.py   # 26 tests
venv\Scripts\python tests\_run_all.py                 # suite completa
```
