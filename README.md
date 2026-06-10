# GENESIS v6.0.0 — IA Auto-Evolutiva 100% Local

Sistema de IA autónomo que evoluciona, aprende e investiga. Desktop app tipo Copilot con 132 módulos cognitivos.
**Desde v6.0 corre 100% local por defecto** — cero dependencia de APIs externas gracias a Ollama + Qwen + Llama.

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
- **Debate Interno** — 3 agentes (crítico, creativo, lógico) debaten antes de responder
- **132 Módulos** — Desde RAG y procesamiento de documentos hasta control del sistema operativo
- **Circuit Breaker** — Si un provider cae, el router bypasea automáticamente (5min cooldown)
- **Desktop App** — PyWebView sidebar tipo Copilot, system tray, hotkey Ctrl+Shift+G
- **Voz** — TTS neural (Edge-TTS, 45 voces en español) + STT offline (Vosk)
- **Documentos** — PDF, DOCX, PPTX, XLSX, imágenes (OCR), audio, video. Resúmenes Map-Reduce con nivel estudio

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
├── core/debate.py                       — Debate multi-agente (3 voces internas)
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

## Comandos principales

```
/status          — Estado de todos los subsistemas
/memory          — Contenido de la memoria
/evolution       — Estado de auto-evolución
/debate toggle   — Activar/desactivar debate interno
/thinking        — Mostrar proceso de pensamiento
/heartbeat       — Estado de investigación autónoma
/investigar X    — Agregar tema a cola de investigación
/help            — Ayuda completa (80+ comandos)
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
| TTS | Edge-TTS (neural, 45 voces ES) + pyttsx3 (fallback) |
| STT | Vosk (offline) + Web Speech API (online) |
| Embeddings | sentence-transformers (GPU) + TF-IDF (fallback) |
| OCR | Tesseract |
| Documentos | PyMuPDF, python-docx, openpyxl, reportlab |
| Base de datos | JSON atómico con file locks |

## Licencia

Software propietario. Ver [LEGAL.md](LEGAL.md) para detalles.
