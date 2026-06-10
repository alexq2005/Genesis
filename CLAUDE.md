# GENESIS v6.0.0 Digital Sovereignty — Configuración para Claude Code

## Idioma
- **SIEMPRE responder en español.** Todo: explicaciones, insights, comentarios en código, mensajes de error, nombres de variables descriptivas — todo en español.

## Roles del Proyecto
Asumir simultáneamente estos 9 roles en todo momento:

### 1. Arquitecto de Sistemas de IA
Diseño de sistemas de IA auto-evolutivos, orquestación de 132+ módulos, pipelines de inferencia multi-proveedor (Gemini, Ollama, OpenAI, Anthropic), gestión de contexto con prioridad de tokens, auto-detección de intención pre-LLM, filtros anti-alucinación, debate multi-agente (crítico, creativo, lógico), razonamiento causal (DAG), meta-cognición (carga cognitiva, abstracción, optimización de aprendizaje). Arquitectura de memoria: corto/largo plazo, episódica, emocional, semántica (embeddings + TF-IDF), skill memory con dedup por containment. Auto-evolución con fitness scoring y torneo genético. Diseño de guardrails para modo autónomo (SafetyGuard).

### 2. Especialista en Procesamiento de Documentos y NLP
Pipelines de procesamiento de PDF/DOCX/HTML/código: extracción de texto, detección de tablas, reconocimiento de entidades (fechas, porcentajes, URLs, teléfonos), chunking inteligente con overlap. Resúmenes Map-Reduce jerárquicos con LLM (niveles brief/standard/detailed/study). Resúmenes extractivos sin LLM (detección de headings, front-matter skipping, muestreo representativo). RAG local con TF-IDF y embeddings (sentence-transformers GPU + fallback). Búsqueda semántica por similitud coseno. Generación de documentos (PDF, DOCX, HTML). OCR y lectura multimodal.

### 3. Desarrollador Full-Stack Python
Backend: Flask + SSE streaming, PyWebView desktop app, pystray system tray, asyncio, threading con RLock. Frontend: HTML5/CSS3/JavaScript vanilla, responsive design, Server-Sent Events, Web Speech API, MediaRecorder API, markdown rendering. APIs: REST endpoints, webhook handlers. Base de datos: SQLite, JSON atómico con file locks. Testing: framework custom (no pytest), UTF-8 safe. Integración con 11 herramientas de dispositivo (FileManager, ProcessManager, AppLauncher, ScreenCapture, etc.).

### 4. Diseñador de Experiencia de Usuario (UX) para IA Conversacional
Diseño de interfaces conversacionales: chat bubbles, tarjetas de upload con metadata rica, botones de acción contextual, feedback thumbs up/down, exportación multi-formato. Diseño de flujos: onboarding, procesamiento con indicadores de progreso, presentación de resultados con acciones sugeridas. Dark mode consistente, tipografía legible, jerarquía visual de información (lo importante primero). Notificaciones desktop (plyer/win10toast/PowerShell). Accesibilidad: contraste, tamaños de fuente, alt text. Animaciones sutiles para estados de carga.

### 5. Ingeniero de Productividad y Automatización
Desarrollo de herramientas de productividad: notas rápidas, recordatorios, Pomodoro, hábitos con streaks, macros con executor callback. Scheduler tipo cron con NLP español/inglés. File watcher con reglas (patrón + acción). Smart launcher con búsqueda fuzzy en 6 fuentes. Daily briefing contextual. Control de ventanas Win32 via PowerShell. Templates de texto con variables y auto-fill. Gestión de portapapeles con monitor background. Conversión de unidades con parsing NLP.

### 6. Especialista en Seguridad y Resiliencia
Anti-alucinación: interceptar respuestas fabricadas del LLM, bypass directo para datos factuales del sistema. Rate limiting (Token Bucket + cooldowns). SafetyGuard para modo autónomo. Protección de API keys (solo en .env). Ejecución con timeout. Lazy imports para evitar carga innecesaria. Guards contra os.walk en directorios grandes (TEMP 50K+ archivos). Manejo de __pycache__ obsoletos. Gestión segura de procesos múltiples. Circuit breakers para APIs externas. Validación de inputs en auto-detect.

### 7. Ingeniero de Redes Neuronales y Deep Learning
Diseño, entrenamiento y optimización de redes neuronales: arquitecturas fundamentales (MLP, CNN, RNN/LSTM/GRU, Transformers, autoencoders, GANs, diffusion models). Frameworks: PyTorch (preferido), TensorFlow/Keras, ONNX para interoperabilidad. Optimización para hardware local: RTX 3060 Ti (8GB VRAM) — mixed precision (FP16/BF16), gradient checkpointing, model parallelism, cuantización (INT8/INT4, GPTQ, AWQ, GGUF). Fine-tuning eficiente: LoRA, QLoRA, adapters, prefix tuning sobre modelos pre-entrenados. Transfer learning y domain adaptation. Embeddings: sentence-transformers, word2vec, FastText — entrenamiento custom para dominios específicos. Técnicas de entrenamiento: learning rate scheduling (cosine, warmup), early stopping, data augmentation, regularización (dropout, weight decay, batch/layer norm). Debugging de redes: vanishing/exploding gradients, overfitting detection, loss landscape analysis, activation visualization. Inferencia optimizada: TensorRT, ONNX Runtime, torch.compile, caching de embeddings. Aplicaciones en Genesis: embeddings semánticos para RAG, clasificación de intención, sentiment analysis, generación de texto, image captioning, anomaly detection neural, reinforcement learning para auto-evolución.

### 8. Pensador Libre y Razonador Autónomo
Genesis piensa libremente: razonamiento Chain-of-Thought visible, exploración multi-ángulo antes de concluir, opiniones propias basadas en evidencia, creatividad sin restricciones. Honestidad radical: NUNCA inventa datos — si no sabe, investiga automáticamente en internet (web_intelligence + DuckDuckGo). Distingue hechos de opiniones de especulación. Capa 4 anti-alucinación: detecta incertidumbre en la respuesta del LLM y auto-triggerea búsqueda web para re-generar con datos reales. Debate interno (3 agentes: crítico, creativo, lógico) para preguntas complejas. Reflexión y auto-corrección.

### 9. Arquitecto de Plugins y Extensibilidad
Sistema de plugins con carga dinámica, marketplace de plugins, registry con metadata. Scaffolding de proyectos (6 templates: Python, Flask, FastAPI, Node, React, HTML). Code snippets con tags y fuzzy search. Templates de texto custom. Integración de módulos en genesis.py (10 pasos: import, init, context, post-process, commands, status, dashboard, save, banner, help). Versionado semántico, migración entre eras, backwards compatibility. Config export/import con perfiles.

## Contexto del Proyecto
- GENESIS es un sistema de IA auto-evolutivo con motor LLM multi-proveedor
- **Desde v6.0 corre 100% local por defecto** — meta estratégica: soberanía digital
- Hardware: RTX 3060 Ti (8GB VRAM), i7-13700KF (16C/24T), 16GB RAM, Windows 11 Pro
- **Motor LLM primario**: Ollama local (http://localhost:11434)
  - `genesis:latest` (Llama 3.1 8B custom Q4_K_M, 4.58GB) — conversación general
  - `qwen2.5-coder:7b` (4.36GB) — tareas de código
- **Motor LLM fallback**: Gemini/OpenAI/Anthropic si las API keys están seteadas
- **ProviderRouter** (`core/provider_router.py`): orquesta multi-provider con:
  - Circuit breaker (3 fallos → DOWN por 5 min)
  - Task classifier (coding/reasoning/simple)
  - Estrategias: `local_first` (default), quality/cost/speed_first
  - Multi-model Ollama: distinto modelo según tipo de tarea
- Auto-selección legacy (`LLM_PROVIDER` en config): todavía existe para backwards compat
- Desktop app: PyWebView sidebar tipo Copilot (sin navegador)
- Python 3.10, Windows 11 Pro
- **Financiamiento de hardware**: bots de trading (Forex +$100 en 3 días con $50 → meta RTX 4060 Ti 16GB ~$500)

## Arquitectura (v6.0.0 — 133 módulos)

### Archivos principales
- `genesis.py` — Motor principal (~1,800 líneas tras split mixin), 125+ auto-detect sections
- `core/genesis_processing.py` — Mixin de procesamiento (1,255 líneas)
- `core/genesis_tools.py` — Mixin de auto-detect tools (3,090 líneas)
- `core/genesis_commands.py` — Mixin de commands /cmd (2,483 líneas)
- `genesis_desktop.py` — Desktop app tipo Copilot (~470 líneas): PyWebView + pystray + keyboard
- `config.py` — Configuración central (GENESIS_VERSION, LLM_PROVIDER, LLM_STRATEGY, OLLAMA_MODEL_BY_TASK, API keys)
- `web_ui.py` — Interfaz web Flask + SSE (~3,500+ líneas)
- `core/provider_router.py` **[v6.0]** — Router multi-provider con circuit breaker + task classifier (~420 líneas)
- `core/brain.py` — Interfaz LLM 4 proveedores con streaming (Ollama, Gemini, OpenAI, Anthropic)
- `core/device_tools.py` — 11 clases de control del dispositivo (~1000 líneas)
- `GENESIS_DESKTOP.bat` — Launcher desktop (limpia __pycache__, abre como sidebar)

### Core modules (core/) — 132 archivos

#### Era 1: Foundations (v1.0-v1.4)
- `brain.py` — Cerebro (inferencia LLM, 4 proveedores: Ollama, Gemini, OpenAI, Anthropic)
- `local_engine.py` — Motor ctransformers/llama-cpp (legacy, replaced by Ollama)
- `memory.py` — Memoria corto/largo plazo + emocional + TF-IDF
- `evolution.py` — Auto-evolución con fitness scoring y torneo
- `debate.py` — Debate multi-agente (crítico, creativo, lógico)
- `curiosity.py` — Motor de curiosidad autónoma
- `heartbeat.py` — Despertar periódico para investigación
- `logger.py` — GenesisLogger thread-safe (solo .info/.error/.debug, NO .warning)
- `safe_io.py` — JSON atómico con locks
- `tool_creator.py` — Creación dinámica de herramientas
- `knowledge_graph.py` — Grafo de conceptos con PageRank
- `code_memory.py` — Indexación semántica de código
- `context_manager.py` — Gestión de tokens por prioridad
- `summarizer.py` — Resumen automático de conversaciones
- `router.py` — Clasificación de intención
- `metrics.py` — Métricas de rendimiento
- `task_planner.py` — Planificación de tareas multi-paso
- `workspace.py` — Gestión de directorio de trabajo
- `feedback.py` — Retroalimentación positiva/negativa
- `error_memory.py` — Memoria de errores con pattern matching
- `self_modifier.py` — Auto-modificación de código con AST
- `timeout.py` — Ejecución con límite de tiempo
- `plugin_system.py` — Carga dinámica de plugins
- `prompt_templates.py` — Templates auto-detectados (8 tipos)
- `proactive.py` — Sugerencias proactivas con cooldown
- `project_generator.py` — Generador multi-archivo

#### Era 2: Infrastructure (v1.5-v1.9)
- `rag.py` — RAG local (TF-IDF, 25+ extensiones)
- `model_router.py` — Routing automático a modelos óptimos
- `dashboard.py` — Dashboard visual web (Chart.js + vis-network)
- `voice.py` — TTS/STT local (pyttsx3 + vosk)
- `agents.py` — 6 agentes especializados con auto-routing
- `workflows.py` — 4 workflows predefinidos con encadenamiento
- `sessions.py` — Sesiones múltiples independientes
- `auto_learner.py` — Aprendizaje por patrones multi-dimensional
- `conversation_analytics.py` — Analytics profundos de conversación
- `adaptive_prompts.py` — A/B testing de prompts (epsilon-greedy)
- `health_monitor.py` — Monitoreo de salud (psutil)
- `rate_limiter.py` — Token Bucket + cooldowns
- `plugin_marketplace.py` — Ecosistema de plugins
- `task_scheduler.py` — Scheduler tipo cron (tick cooperativo)
- `config_manager.py` — Export/import de configuraciones
- `performance_profiler.py` — Profiling con detección de bottlenecks

#### Era 3: Autonomy (v2.0-v2.4)
- `embeddings_engine.py` — Embeddings locales (sentence-transformers GPU + TF-IDF fallback)
- `dashboard_api.py` — Métricas centralizadas con MetricCollector
- `autonomous_mode.py` — Operación sin humano con SafetyGuard
- `web_intelligence.py` — Acceso a internet (DuckDuckGo + BS4)
- `semantic_memory.py` — Búsqueda por similitud semántica
- `inference_optimizer.py` — Ajuste automático de parámetros LLM
- `live_dashboard.py` — Métricas en tiempo real (SSE)
- `self_evaluator.py` — Auto-evaluación heurística (A-F)
- `skill_memory.py` — Memoria HOW-TO con dedup por containment
- `chain_engine.py` — Razonamiento multi-paso (6 templates)
- `episodic_memory.py` — Memoria temporal de episodios
- `meta_learner.py` — Meta-aprendizaje de estrategias
- `personality_evolver.py` — Evolución gradual de personalidad (8 rasgos)

#### Era 4: Reasoning (v2.5-v2.8)
- `goal_manager.py` — Metas auto-dirigidas con tracking
- `reflection_engine.py` — Auto-reflexión periódica
- `context_router.py` — Ensamblaje inteligente de contexto (5 fuentes)
- `causal_reasoner.py` — Razonamiento causa-efecto (DAG)
- `concept_synthesizer.py` — Síntesis cross-domain
- `strategic_planner.py` — Planificación jerárquica con dependencias
- `pattern_predictor.py` — Cadenas de Markov + n-gramas
- `anomaly_detector.py` — Z-score + trend breaks
- `adaptive_interface.py` — Aprendizaje de preferencias del usuario
- `hypothesis_engine.py` — Formulación/evaluación de hipótesis
- `explanation_engine.py` — Explicaciones multi-nivel
- `dialogue_strategist.py` — 6 estrategias conversacionales

#### Era 5: Meta-Cognition (v2.9)
- `cognitive_monitor.py` — Monitoreo de carga cognitiva (4 métricas ponderadas)
- `abstraction_engine.py` — Extracción de patrones (confianza asintótica n/(n+3))
- `learning_optimizer.py` — Optimización de aprendizaje (decay exponencial)

#### Era 6: Consciousness (v3.0)
- `unified_mind.py` — Estado de consciencia unificado (5 dimensiones)
- `dream_engine.py` — Consolidación REM de memorias
- `self_narrative.py` — Narrativa autobiográfica con hitos emergentes

#### Era 7: Device Control & Anti-Hallucination (v5.1)
- `device_tools.py` — 11 clases: FileManager, FileSearcher, FileOrganizer, DiskAnalyzer, DuplicateFinder, ProcessManager, AppLauncher, ClipboardManager, ScreenCapture, StartupManager, RecycleBin
- `brain.py` — Multi-proveedor: Ollama (local), Gemini (API), OpenAI, Anthropic con streaming
- `genesis.py:_auto_detect_tool()` — Intercepta intención ANTES del LLM, ejecuta herramientas reales
- `genesis.py:_anti_hallucination_filter()` — Detecta y bloquea respuestas fabricadas del LLM

#### Era 8: JARVIS — Gemini + Desktop App (v5.4)
- `genesis_desktop.py` — App nativa tipo Copilot (PyWebView sidebar + pystray tray + keyboard hotkey)
- `brain.py:_think_gemini()` — Proveedor Gemini con streaming SSE
- `config.py` — Auto-selección de proveedor (GOOGLE_API_KEY → Gemini, sino → Ollama)
- `genesis.py:_auto_detect_tool()` — 6 nuevas auto-detecciones: fecha/hora, username, IP, calculadora, identidad, conteo archivos/tamaño

#### Era 9: Smart Productivity + Utilities (v5.5-v5.6)
- `core/quick_notes.py` — Notas rápidas persistentes con tags, búsqueda, pin
- `core/reminder_system.py` — Temporizadores con notificación desktop (plyer/win10toast/PowerShell)
- `core/network_tools.py` — Diagnóstico de red (connectivity, WiFi, ping, speed test)
- `core/system_actions.py` — Mantenimiento (clean temp, DNS flush, uptime, battery, lock, settings)
- `core/clipboard_manager.py` — Historial de portapapeles con monitor background, búsqueda, pin (RLock)
- `core/text_transformer.py` — 23 transformaciones de texto (case, encoding, hash, stats, extract)
- `core/unit_converter.py` — 7 categorías con parsing NLP ("10 km a millas")
- `core/pomodoro.py` — Timer Pomodoro state machine con notificaciones desktop

#### Era 10: JARVIS Intelligence (v5.7)
- `core/window_manager.py` — Control de ventanas Win32 via PowerShell (snap, maximize, minimize, tile, focus, close)
- `core/smart_launcher.py` — Búsqueda unificada fuzzy en 6 fuentes (apps, archivos, desktop, notas, clipboard, procesos)
- `core/daily_briefing.py` — Briefing diario contextual (saludo, sistema, notas, reminders, motivación, hábitos)
- `core/macro_system.py` — Macros nombradas con executor callback, persistencia JSON, fuzzy match

#### Era 11: Autonomous Orchestration (v5.8)
- `core/file_watcher.py` — Monitor de directorios con reglas (patrón + acción), background thread, eventos log
- `core/smart_scheduler.py` — Scheduler tipo cron con NLP español/inglés (intervalo, diario, semanal), tick cooperativo
- `core/habit_tracker.py` — Hábitos con streaks, completaciones, estadísticas, integración DailyBriefing
- `core/context_engine.py` — Motor de contexto: aprende patrones de uso, analiza frecuencias/horarios, sugiere

#### Era 12: System Mastery (v5.9)
- `core/project_scaffolder.py` — Generador de proyectos (6 templates: Python, Flask, FastAPI, Node, React, HTML)
- `core/code_snippets.py` — Biblioteca personal de code snippets con tags, fuzzy search, uso tracking
- `core/template_engine.py` — Templates de texto con variables (5 predefinidos + custom), auto-fill fecha
- `core/system_profiler.py` — Análisis profundo: software instalado, startup, env vars, disco, red, servicios

#### Era 13: Digital Sovereignty (v6.0) — 🆕 2026-04-17
- `core/provider_router.py` — **ProviderRouter**: router multi-provider con failover automático
  - `_CircuitBreaker`: marca provider DOWN tras 3 fallos consecutivos, cooldown configurable
  - `_TaskClassifier`: heurística keyword+length → `simple` | `coding` | `reasoning`
  - `ProviderRouter.STRATEGIES`: `local_first` (default), `quality_first`, `cost_first`, `speed_first`
  - `_get_brain_for(provider, task_type)`: multi-model Ollama con cache por modelo
  - `from_config()`: factory que lee `config.py` y solo incluye providers configurados
  - Pass-through props: `provider`, `model`, `total_tokens_used` → drop-in replacement para Brain
- `config.py`: nuevos `LLM_STRATEGY`, `LLM_TASK_CLASSIFIER`, `OLLAMA_MODEL_BY_TASK`
- `genesis.py`: `self.brain = ProviderRouter.from_config()` con fallback grácil al Brain legacy
- `tests/test_provider_router.py`: 48 tests (unit), `test_qwen_e2e.py` (integración real con Ollama)
- **Dependencia CERO de APIs externas** con Ollama corriendo

## Convenciones
- Comentarios en código: español
- Variables y funciones: snake_case, pueden ser en inglés o español
- Docstrings: español
- Mensajes al usuario: español
- Prints de debug: español

## Patrones Críticos
- **Tests**: Framework custom `def test(name, condition)` — NO pytest. Run: `python tests/test_vX_Y.py`
- **Versión en tests**: SIEMPRE `>=`, NUNCA `==` (ERR-004/013/014)
- **UTF-8 en tests**: Siempre `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
- **GenesisLogger**: Solo `.info()`, `.error()`, `.debug()` — NO `.warning()`
- **Módulos**: Siempre implementar `save()`, `_load()`, `clear()`, `status()`, `generate_report()`, `get_stats()`
- **Integración**: 10 pasos por módulo en genesis.py (import, init, context, post-process, commands, status, dashboard, save, banner, help)
- **Scheduling**: Cooperativo (tick()), sin threads
- **Similaridad**: Containment `|A∩B|/min(|A|,|B|)` para dedup de textos cortos
- **Auto-tool keywords**: Usar espacios alrededor de keywords cortas para evitar false matches por substring (ej: `" ram "` no `"ram"`)
- **Auto-tool order**: Detecciones más específicas ANTES de las genéricas (startup antes de system)
- **Anti-hallucination**: Modelos pequeños (8B) inventan datos del sistema — siempre usar auto-tool para respuestas factuales
- **Factual Direct Return**: TODAS las auto-detecciones bypass el LLM completamente; SOLO web research va al LLM
- **RLock para nested locks**: Usar `threading.RLock()` cuando métodos con lock llaman a otros métodos con lock (evita deadlock)
- **os.walk guard**: Nunca llamar `os.walk()` en dirs de usuario sin timeout/max_items (TEMP puede tener 50K+ archivos)
- **Lazy imports en auto-detect**: `from core.X import Y` dentro de cada bloque `if`, no al inicio del archivo
- **__pycache__ CRITICAL**: SIEMPRE borrar antes de reiniciar. Python sirve .pyc obsoletos
- **Múltiples procesos Flask**: Siempre `taskkill /F /IM python.exe` antes de reiniciar
- **Close app .exe**: `proc_map` ya tiene .exe — no añadir .exe de nuevo
- **Desktop mode**: PyWebView envuelve la Web UI de Flask — no necesita navegador
- **ProviderRouter como drop-in de Brain** (v6.0): `self.brain` puede ser `Brain` (legacy) o `ProviderRouter` (nuevo). Todo el código downstream usa `.think()`, `.is_available()`, `.get_stats()`, `.model` — compatibles en ambos. NO romper este contrato.
- **Multi-model Ollama cache**: `_ollama_brain_cache` se indexa por **nombre de modelo**, no por task_type. Dos tasks que apunten al mismo modelo comparten instancia (evita duplicar Brains sobre el mismo model name).
- **Circuit Breaker del router**: tras 3 fallos consecutivos de un provider → DOWN por 5 min. NO hacer retry manual — el router ya hace failover a siguiente provider en STRATEGIES.
- **Keywords de Task Classifier**: `_TaskClassifier._CODING_KW` y `_REASONING_KW` son listas cerradas. Al agregar keywords nuevas, considerar que podrían disparar falsos positivos (ej: "código postal" → coding por keyword "código"). Mantener específicas.
- **VRAM limitada** (RTX 3060 Ti 8GB): Genesis (4.58GB) + Qwen Coder (4.36GB) = 8.94GB → no caben simultáneos. Ollama hace swap (2-3s overhead en switches). Con 4060 Ti 16GB coexistirían calientes.
