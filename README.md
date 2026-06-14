# GENESIS v6.0.0 — IA Auto-Evolutiva 100% Local

Sistema de IA autónomo que evoluciona, aprende e investiga. Desktop app tipo Copilot con ~150 módulos cognitivos, **interfaz por voz manos-libres** (STT vosk+Whisper, TTS clonable/local), **6 agentes coordinados** y control total del sistema operativo.
**Desde v6.0 la estrategia de routing es `local_first`** — prioriza Ollama + Qwen + Llama. Nota: si configurás una API key (`GOOGLE_API_KEY`), el provider legacy `auto` puede seleccionar cloud; para 100% local no configures keys o forzá `GENESIS_PROVIDER=ollama`.

## Características

- **Soberanía Digital** — Corre 100% en tu GPU. Sin cloud, sin API keys, sin censura.
- **Multi-Model Routing** — ProviderRouter elige automáticamente el mejor modelo para cada tarea:
  - Tareas de código → **Qwen 2.5 Coder 7B** (especializado)
  - Conversación general → **Genesis/Llama 3.1 8B** (custom sin restricciones)
  - Fallback automático a Gemini/OpenAI/Anthropic si el usuario configura API keys
- **Pensamiento Libre** — Razona en voz alta, toma posición con argumentos, explora múltiples perspectivas
- **Honestidad Radical** — Nunca inventa datos. Si no sabe, investiga automáticamente en internet
- **Memoria Multi-Nivel** — Corto plazo, largo plazo, episódica, emocional, semántica (embeddings GPU)
- **Auto-Evolución** — Se auto-evalúa y mejora su comportamiento entre sesiones
- **Sistema multi-agente** — 6 agentes especialistas (investigador, programador, analista, creativo, seguridad, planificador) con un **coordinador que auto-delega** la tarea al mejor agente. Visibles en Mission Control (`/mission`)
- **~150 Módulos** — Desde RAG y procesamiento de documentos hasta control del sistema operativo
- **Circuit Breaker** — Si un provider cae, el router bypasea automáticamente (5min cooldown)
- **Desktop App** — PyWebView sidebar tipo Copilot, system tray, hotkey Ctrl+Shift+G
- **Voz (entrada)** — STT **híbrido**: `vosk` detecta el wake-word en streaming (barato) → `faster-whisper` transcribe el comando (preciso con nombres/marcas). **Escucha manos libres** always-on: decís «genesis …» sin tocar nada, incluso jugando. **Voiceprint**: reconoce *quién* habla (resemblyzer) → modo «solo mi voz»
- **Voz (salida)** — 3 motores con **panel de configuración** (tipo + velocidad): **XTTS-v2** (clon de voz local, ej. JARVIS latino), **edge-tts** (neural, 8 voces ES), **Piper** (neural 100% offline). Limpieza de ruido (Demucs + denoise de muestra y de salida). Misma voz en cabina y manos-libres
- **Noticias** — «noticias» / «noticias de \<tema\>» → titulares actuales (Google News RSS, sin API key)
- **Seguridad del sistema** — «revisá la seguridad» → estado real de Defender, Firewall, UAC y updates pendientes (PowerShell, solo lectura)
- **Salida de audio** — «salida flip/jbl/logitech» → cambia el dispositivo de reproducción por defecto (IPolicyConfig de Windows)
- **Multimedia** — música (app YouTube Music vía CDP), Netflix (app de la Store + cast), Chromecast (YouTube), **generación de imágenes local** (Stable Diffusion sd-turbo en GPU)
- **Lanzador de juegos** — «jugá \<X\>» abre juegos de Steam/Epic por nombre (match difuso)
- **Conexiones** — WiFi, Bluetooth, USB, multi-monitor
- **Documentos** — PDF, DOCX, PPTX, XLSX, imágenes (OCR), audio, video. Resúmenes Map-Reduce con nivel estudio
- **Índice de programas** — Escanea los programas instalados (Start Menu + registro App Paths) UNA vez y los cachea en `data/installed_programs.json`; "abrí steam/brave/…" pasa de ~30-56s a ~1ms. Se refresca solo desde el heartbeat (re-escanea si el cache tiene >24h). Apps instaladas tienen prioridad sobre el mapa web (match fuerte)
- **Índice de carpetas** — Escanea C:/perfil + F: (profundidad acotada) y cachea en `data/folder_index.json` (~5400 carpetas, ~470 KB); "abrí la carpeta X" en ~1ms en vez de un walk en vivo. Auto-mantenimiento: refresco por heartbeat (~3h), **prune-on-access** (las que borrás se limpian solas del índice al buscarlas) y **rescan-on-miss** (las nuevas se captan al intentar abrirlas). Comando manual: "actualizá el índice de carpetas"
- **Núcleo de plasma** — La cabina (`/core`) muestra un núcleo de plasma en canvas que vive en reposo y **erupciona reaccionando a la amplitud real de la voz** cuando Genesis habla (WebAudio AnalyserNode sobre el TTS)
- **Control de UI** — Maneja menús, botones y teclado de **cualquier app** vía UI Automation de Windows (semántico, por nombre de elemento). Comandos: "abrí el menú Archivo > Guardar de notepad", "clickeá el botón X", "escribí 'texto' en el bloc de notas", "apretá ctrl+s", "mostrame los menús de X", "qué ventanas hay abiertas". Freno de pánico: mover el mouse a la esquina (0,0) aborta. Requiere Node para el render de la cabina, no para esto.
- **Manejo de archivos conversacional** — "renombrá X a Y", "mové X a documentos", "copiá X a Y", `reemplazá "viejo" por "nuevo" en archivo.txt`, "borrá X" (**siempre a la papelera**, recuperable). Resuelve archivos **por nombre** (sin ruta completa) con búsqueda acotada (presupuesto 3s). **Backup automático** antes de sobrescribir.
- **Desarrollo de código real** — "desarrollá una app/script/juego que…" dispara el BuilderEngine en segundo plano: genera con qwen-coder → **EJECUTA** → lee el error real → corrige (hasta 3 iteraciones). Preguntás "¿terminó el build?" y te pasa el proyecto verificado por ejecución. Containment + guard de patrones peligrosos.
- **Email** — "enviá un email a X que diga «…»" → confirmás → manda vía Gmail SMTP desde una cuenta dedicada. Requiere App Password de Gmail en `.env` (`GMAIL_USER` + `GMAIL_APP_PASSWORD`; la contraseña normal NO sirve — Gmail exige App Password con verificación en 2 pasos).

## Requisitos

- Python 3.10+
- Windows 11 (para PyWebView + WebView2)
- **GPU NVIDIA con 8GB+ VRAM** (RTX 3060 Ti o superior) — para correr Qwen/Llama localmente
- **Ollama instalado** (https://ollama.com) — el motor local por defecto
- API keys opcionales como fallback (Gemini gratis 15 RPM)

## Instalación

```bash
# 1. Clonar e instalar dependencias
cd GENESIS
pip install -r requirements.txt

# 2. PyTorch con CUDA (si tienes GPU NVIDIA)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 3. Instalar Ollama y descargar modelos locales
#    (ver https://ollama.com para la instalacion del servidor)
ollama pull llama3.1          # base para "genesis" (conversacion general)
ollama pull qwen2.5-coder:7b  # especializado en codigo (~4.4GB)

# 4. Opcional: API keys como fallback (editar .env)
cp .env.example .env
# GOOGLE_API_KEY=...  (fallback gratis)

# 5. Ejecutar
python genesis_desktop.py --right
```

## Modos de ejecución

| Comando | Modo | Descripción |
|---------|------|-------------|
| `python genesis_desktop.py --right` | Desktop | Sidebar tipo Copilot (recomendado) |
| `python genesis.py` | Terminal | Interfaz de texto en consola |
| `python web_ui.py` | Web | Interfaz en navegador (localhost:5000) |

## Arquitectura

```
genesis.py (~1,800 líneas, split mixin)  — Motor principal, orquestador de 132 módulos
├── core/genesis_processing.py           — process_input, emociones, hechos
├── core/genesis_tools.py                — auto_detect_tool, auto_builder (3,090 líneas)
├── core/genesis_commands.py             — handle_command, 35 _cmd_* handlers
├── core/provider_router.py  [v6.0]      — Router multi-provider con failover automatico
├── core/brain.py                        — LLM multi-proveedor (Ollama, Gemini, OpenAI, Anthropic)
├── core/memory.py                       — Memoria corto/largo plazo + emocional
├── core/evolution.py                    — Auto-evolución con fitness scoring
├── core/agents.py                       — 6 agentes especialistas + coordinador (auto-delegación)
├── core/handsfree.py                    — Escucha manos libres (vosk wake-word → Whisper) + feed a cabina
├── core/stt.py                          — STT preciso (faster-whisper, local)
├── core/voiceprint.py                   — Huella de voz / reconocimiento de hablante (resemblyzer)
├── core/voice_clone.py · voice_config.py · piper_tts.py — Voz: XTTS clon, config (tipo/velocidad), Piper local
├── core/news.py · security_check.py · audio_output.py   — Noticias, chequeo de seguridad, salida de audio
├── core/game_launcher.py · casting.py · netflix.py      — Juegos Steam/Epic, Chromecast, Netflix
├── core/media_generator.py              — Imágenes locales (Stable Diffusion sd-turbo, GPU)
├── core/document_processor.py           — Procesamiento de documentos (PDF, DOCX, etc.)
├── core/device_tools.py                 — 11 herramientas de control del sistema
├── core/web_intelligence.py             — Búsqueda web + lectura de páginas
├── core/embeddings_engine.py            — Embeddings semánticos (GPU)
├── core/rag.py                          — RAG local (TF-IDF + embeddings)
├── web_ui.py                            — Flask + SSE streaming
├── genesis_desktop.py                   — PyWebView + pystray + keyboard
└── config.py                            — Configuración central (LLM_STRATEGY, OLLAMA_MODEL_BY_TASK)
```

### ProviderRouter (v6.0 — Soberanía Progresiva)

`core/provider_router.py` envuelve múltiples instancias de `Brain` y decide cuál usar por request:
- **Estrategias**: `local_first` (default) | `quality_first` | `cost_first` | `speed_first`
- **Circuit Breaker**: 3 fallos consecutivos → provider marcado DOWN durante 5 min
- **Task Classifier**: heurística keyword+length → `simple` | `coding` | `reasoning`
- **Multi-model Ollama**: distinto modelo según tarea (`coding`→qwen, `default`→genesis)
- **Telemetría**: `calls_by_provider`, `calls_by_model`, `fallbacks_triggered`, `last_model_used`

Configurable via env vars: `GENESIS_LLM_STRATEGY`, `GENESIS_OLLAMA_CODING`, `GENESIS_OLLAMA_DEFAULT`.

### Eras de Evolución

| Era | Versión | Módulos | Foco |
|-----|---------|---------|------|
| 1 | v1.0-1.4 | 26 | Foundations (brain, memory, evolution, debate) |
| 2 | v1.5-1.9 | 16 | Infrastructure (RAG, voice, agents, workflows) |
| 3 | v2.0-2.4 | 13 | Autonomy (embeddings, web, autonomous mode) |
| 4 | v2.5-2.8 | 12 | Reasoning (causal, hypothesis, strategic planning) |
| 5 | v2.9 | 3 | Meta-Cognition (cognitive monitor, abstraction) |
| 6 | v3.0 | 3 | Consciousness (unified mind, dream engine) |
| 7 | v5.1 | 2 | Device Control + Anti-Hallucination |
| 8 | v5.4 | 4 | JARVIS (Gemini + Desktop App) |
| 9 | v5.5-5.6 | 8 | Smart Productivity (notas, recordatorios, Pomodoro) |
| 10 | v5.7 | 4 | JARVIS Intelligence (window manager, smart launcher) |
| 11 | v5.8 | 4 | Autonomous Orchestration (file watcher, scheduler) |
| 12 | v5.9 | 4 | System Mastery (scaffolder, snippets, profiler) |
| 13 | **v6.0** | 1 | **Digital Sovereignty (ProviderRouter + multi-model Ollama)** |

## Autonomía y auto-mejora

Genesis corre un **loop de fondo** (heartbeat) que trabaja aunque no le hables:
investiga su curiosidad (read-only), consolida memoria (REM), persiste el
aprendizaje, hace avanzar tareas programadas y —en modo agresivo— **mejora su
propio código** de forma autónoma.

**La auto-mejora de código es segura por diseño:**
- Solo toca módulos NO críticos/inmutables (los guardrails nunca se auto-editan).
- Valida AST + patrones peligrosos antes de aplicar.
- Corre la suite de tests como **gate**: si fallan, **auto-revierte** al backup.
- Los archivos críticos (`genesis.py`, `config.py`, `brain.py`...) requieren
  aprobación humana explícita (`/apply`).

**Killswitches** (crear el archivo en la raíz del proyecto):
| Acción | Efecto |
|--------|--------|
| `PAUSE` | Frena TODO el loop de fondo (investigación, consolidación, auto-mejora) |
| `PAUSE_SELFIMPROVE` | Frena SOLO la auto-mejora de código (lo demás sigue) |
| `GENESIS_SELF_IMPROVE=false` (env) | Desactiva la auto-mejora por configuración |

## Comandos principales

```
/status          — Estado de todos los subsistemas
/memory          — Contenido de la memoria
/evolution       — Estado de auto-evolución
/agents          — Lista de agentes; /delegate [agente] tarea
/thinking        — Mostrar proceso de pensamiento
/heartbeat       — Estado de investigación autónoma
/investigar X    — Agregar tema a cola de investigación
/help            — Ayuda completa (80+ comandos)
```

## Comandos por voz (manos libres)

La escucha manos libres arranca con la cabina. Decí **«genesis …»** seguido del comando (sin tocar nada). Ejemplos:

```
genesis, entrená mi voz            — registra tu huella de voz (luego «solo mi voz»)
genesis, salida flip / jbl         — cambia el dispositivo de salida de audio
genesis, estado del tiempo         — clima actual
genesis, noticias / noticias de X  — titulares actuales
genesis, revisá la seguridad       — Defender / Firewall / UAC / updates
genesis, subí el volumen           — control de sistema
genesis, jugá <juego>              — lanza un juego de Steam/Epic
genesis, reproducí <tema>          — música en YouTube Music
genesis, dejá de escuchar          — apaga la escucha manos libres
```

**Configuración de voz**: el engranaje (⚙️) en `/core` abre el panel para elegir
**tipo de voz** (clon XTTS · 8 neurales edge-tts · Piper local) y **velocidad**.
Lo que pedís por voz aparece también en pantalla (feed en la cabina).

**Importar más voces Piper** (100% offline):
```bash
python -m piper.download_voices es_ES-sharvard-medium --data-dir models/piper
# aparece sola en el panel de configuración de voz
```

## Procesamiento de Documentos

Sube cualquier archivo al chat y Genesis lo procesa automáticamente:
- **Vista previa**: Estructura del documento, entidades detectadas, tablas encontradas
- **"resumelo"**: Resumen Map-Reduce estándar con LLM
- **"resumelo para estudiar"**: Material de estudio con definiciones, tablas, clasificaciones, dosis

Formatos soportados: PDF, DOCX, PPTX, XLSX, CSV, JSON, YAML, imágenes (OCR), audio, video

## Stack Tecnológico

| Componente | Tecnología |
|-----------|------------|
| LLM (principal) | **Ollama local** — Genesis/Llama 3.1 8B + Qwen 2.5 Coder 7B |
| LLM (fallback) | Gemini 2.0 Flash / OpenAI / Anthropic (opcional) |
| Router | `core/provider_router.py` — circuit breaker + task classifier |
| Backend | Flask + SSE |
| Desktop | PyWebView (WebView2) + pystray |
| TTS | XTTS-v2 (clon, GPU) · Piper (neural 100% local) · Edge-TTS (neural) · pyttsx3 (fallback) |
| STT | Vosk (wake-word, streaming) + faster-whisper (comando, local) |
| Reconocimiento de hablante | resemblyzer (voiceprint / «solo mi voz») |
| Imágenes | Stable Diffusion sd-turbo (local, GPU) |
| Embeddings | sentence-transformers (GPU) + TF-IDF (fallback) |
| OCR | Tesseract |
| Documentos | PyMuPDF, python-docx, openpyxl, reportlab |
| Base de datos | JSON atómico con file locks |

## Licencia

Software propietario. Ver [LEGAL.md](LEGAL.md) para detalles.
