# GENESIS — Evolución del Proyecto

## Objetivo Principal
Sistema de IA auto-evolutivo que corre 100% local en GPU (RTX 3060 Ti, 8GB VRAM).
Usa modelos open-source (Dolphin 2.8 Mistral 7B) via ctransformers con CUDA.
Sin APIs externas, sin censura, con capacidad de auto-modificación.

## Stack Tecnológico
| Componente | Tecnología | Razón |
|---|---|---|
| Lenguaje | Python 3.11+ | Ecosistema ML/AI maduro |
| Motor LLM | ctransformers[cuda] | Inferencia directa en GPU sin servidor |
| Modelo principal | dolphin-2.8-mistral-7b-v02 Q4_K_M | 7B parámetros, sin censura, GGUF optimizado |
| Web UI | Flask + SSE | Ligero, sin dependencias pesadas |
| Tests | pytest | Estándar de la industria |
| Hardware | RTX 3060 Ti (8GB VRAM), 16GB RAM | GPU consumer accesible |

## Arquitectura
```
GENESIS/
├── genesis.py              # Clase principal Genesis (~1,920 líneas)
├── config.py               # Configuración central
├── web_ui.py               # Interfaz web Flask
├── core/                   # 28 módulos del sistema
│   ├── brain.py            # Interfaz con LLM (multi-proveedor)
│   ├── local_engine.py     # Motor ctransformers + CUDA
│   ├── memory.py           # Memoria corto/largo plazo + TF-IDF
│   ├── evolution.py        # Auto-evolución con fitness tracking
│   ├── knowledge_graph.py  # Grafo de conocimiento con PageRank
│   ├── tool_creator.py     # Creador dinámico de herramientas
│   ├── self_modifier.py    # Auto-modificación de código
│   ├── prompt_templates.py # Templates auto-detectados por tags
│   ├── proactive.py        # Motor de sugerencias proactivas
│   ├── project_generator.py# Generador multi-archivo
│   └── ... (18 módulos más)
├── tests/                  # 4 suites, 277 tests
├── models/                 # Modelos .gguf (excluidos de git)
└── plugins/                # Sistema de plugins extensible
```

---

## Historial de Versiones

### v1.0.0 — Fundación (2025-03-04)
**Hito:** Sistema base funcional con arquitectura modular.
- Clase Genesis principal con loop interactivo
- Brain: interfaz multi-proveedor (local, ollama, openai, anthropic)
- LocalEngine: inferencia directa con ctransformers + CUDA
- MemorySystem: corto plazo (lista) + largo plazo (JSON) + emocional
- EvolutionEngine: auto-evaluación con fitness scoring
- DebateSystem: multi-agente interno (crítico, creativo, lógico)
- CuriosityEngine: tracking de preguntas pendientes
- Heartbeat: despertar periódico para investigación autónoma
- Config centralizado con variables de entorno
- **51 tests pasando**

### v1.1.0 — Robustez (2025-03-04)
**Hito:** Sistema hardened para producción.
- GenesisLogger: sistema de logging thread-safe con rotación
- safe_io: lectura/escritura JSON atómica con locks
- BackupManager: backups automáticos cada N interacciones
- PathValidator + CodeSandbox: ejecución segura de código
- ShellExecutor: ejecución de comandos con timeout
- TF-IDF search en memoria largo plazo
- EmotionalMemory: scoring de importancia emocional
- Persistencia de sesión entre reinicios
- **51 tests pasando (suite v1.1)**

### v1.2.0 — Extensibilidad (2025-03-05)
**Hito:** Sistema extensible con plugins y auto-modificación.
- TimeoutExecutor: ejecución con límite de tiempo configurable
- Spinner + ProgressBar: indicadores visuales Unicode en terminal
- PluginSystem: carga dinámica de plugins desde directorio
- SelfModifier: auto-modificación de código con validación AST
- Mejoras de streaming para respuesta token-by-token
- **77 tests pasando (suite v1.2)**

### v1.3.0 — Inteligencia (2025-03-06)
**Hito:** Sistema con creación de herramientas y grafo de conocimiento.
- ToolCreator: creación dinámica de herramientas por el LLM
- KnowledgeGraph: grafo de conceptos con relaciones y PageRank
- CodeMemory: indexación semántica de código con TF-IDF
- ContextBudgetManager: gestión de tokens por prioridad
- ConversationSummarizer: resumen automático de conversaciones
- IntentRouter: clasificación de intención del usuario
- MetricsTracker: métricas de rendimiento
- TaskPlanner: planificación de tareas multi-paso
- Workspace: gestión de directorio de trabajo
- FeedbackSystem: sistema de retroalimentación positiva/negativa
- ErrorMemory: memoria de errores con pattern matching
- Brain refactorizado con soporte multi-proveedor real
- **59 tests pasando (suite v1.3)**

### v1.4.0 — Proactividad (2025-03-07)
**Hito:** Sistema proactivo con templates y generación de proyectos.
- PromptTemplateSystem: 8 templates auto-detectados por tags
  - code (temp=0.3), debug (0.2), explain (0.5), creative (0.9)
  - analysis (0.4), research (0.4), summarize (0.3), security (0.4)
- ProactiveEngine: sugerencias inteligentes con cooldown y prioridad
- ProjectGenerator: parseo multi-formato y generación de proyectos
- Web UI: Flask + SSE con tema cyberpunk oscuro
- Fix: encoding UTF-8 para Windows (cp1252 → utf-8)
- Fix: GenesisLogger no tiene .warning(), usar .info()
- **90 tests pasando (suite v1.4)**
- **Total: 277 tests, 36 archivos, ~13,767 líneas**

---

## Roadmap — Próximos Pasos

### v1.5.0 — Conocimiento y Multi-Modelo (2025-03-07)
**Hito:** RAG, multi-model routing, dashboard visual y voz.
- RAGSystem: indexación de documentos locales con TF-IDF propio
  - DocumentChunker: chunking por párrafos con overlap configurable
  - RAGVectorizer: cosine similarity sin dependencias externas
  - Soporta 25+ extensiones (.py, .md, .txt, .json, etc.)
  - Persistencia en JSON, re-indexación incremental por hash MD5
  - Inyección automática de contexto RAG en prompts
- ModelRouter: routing automático de tareas a modelos óptimos
  - 3 perfiles predefinidos: dolphin (general), mistral (formal), qwen (code/math)
  - Scoring por fortalezas × template detectado
  - Override manual con prioridad: exacto > nombre parcial > filename
  - Toggle auto-routing on/off
- Dashboard Visual: página `/dashboard` en Web UI
  - Chart.js para gráficos (templates, feedback)
  - vis-network para Knowledge Graph interactivo
  - Mini-stats cards, sistema status, modelos info
  - Auto-refresh cada 30 segundos
- VoiceSystem: TTS local con pyttsx3 + STT con vosk
  - TTS: limpieza de markdown/código para habla natural
  - STT: reconocimiento offline con modelo vosk (opcional)
  - Toggle on/off, configuración de velocidad y voz
- Fix: ModelRouter match por nombre prioriza exacto sobre filename
- **111 tests pasando (suite v1.5)**
- **Total: 388 tests, 40 archivos, ~16,000+ líneas**

### v1.6.0 — Sistema Multi-Agente (2026-03-07)
**Hito:** Agentes especializados, workflows automatizados y sesiones múltiples.
- AgentSystem: 6 agentes predefinidos con auto-routing por keywords
  - researcher (investigación), coder (código), analyst (análisis)
  - creative (escritura creativa), security (ciberseguridad), planner (planificación)
  - Detección automática por scoring keyword→capability con desempate por prioridad
  - Delegación con system prompt especializado por agente
  - Pipeline: encadenamiento output_agente_N → contexto_agente_N+1
  - CRUD: agregar/eliminar/toggle agentes custom
- WorkflowEngine: 4 workflows predefinidos con ejecución paso a paso
  - code_review: analizar → seguridad → mejoras (coder→security→coder)
  - research_deep: investigar → analizar → sintetizar (researcher→analyst→researcher)
  - debug_fix: diagnosticar → planificar → implementar (coder→planner→coder)
  - project_scaffold: planificar → estructura → documentar (planner→coder→researcher)
  - Contexto acumulativo entre pasos ({input} + {context})
  - Custom workflows: crear workflows con pasos y agentes propios
- SessionManager: conversaciones múltiples independientes
  - Crear, cambiar, eliminar, renombrar sesiones
  - Persistencia en JSON (memory_data/sessions/)
  - Match parcial en switch (ej: "proyecto" → "proyecto_web")
  - Auto-save cada 5 mensajes, sanitización de IDs
- Fix: capabilities compartidas (architecture) resueltas por prioridad de agente
- Fix: pipeline se detiene correctamente cuando un agente falla (sin LLM)
- **240 tests pasando (suite v1.6)**
- **Total: 628 tests, 44 archivos, ~18,000+ líneas**

### v1.7.0 — Aprendizaje Adaptativo (2026-03-07)
**Hito:** Genesis aprende de cada interacción para mejorar automáticamente.
- AutoLearner: aprendizaje por patrones multi-dimensional
  - PatternTracker para agentes, templates, tags y combinaciones
  - Generación automática de reglas cada 10 feedbacks
  - Ajustes de prioridad de agentes basados en tasa de éxito
  - get_best_agent_for_template() sugiere combos óptimos
  - Persistencia completa en JSON
- ConversationAnalytics: analytics profundos de conversación
  - TopicTracker: 8 categorías (programación, seguridad, datos, ia_ml, web, sistema, creative, general)
  - EngagementMetrics: distribución horaria/diaria, tiempos de respuesta, largo de queries
  - KnowledgeGapDetector: detecta preguntas con feedback negativo, resuelve cuando mejora
  - Reporte completo con tendencias y gaps
- AdaptivePrompts: A/B testing de prompts con epsilon-greedy
  - PromptExperiment con múltiples PromptVariant
  - Selección epsilon-greedy (80% exploit, 20% explore)
  - Conclusión automática cuando ganador tiene ≥15% ventaja con ≥N muestras
  - CRUD completo de experimentos con persistencia
- Integración: feedback (+/-) alimenta AutoLearner + Analytics automáticamente
  - _last_agent, _last_template, _last_response_time trackeados
  - analytics.track_message() en process_input para cada interacción
- Fix: test_v1_6 version check cambiado a >= para forward compatibility
- Fix: A/B test con variantes empatadas (100% vs 100%) no concluye prematuramente
- **158 tests pasando (suite v1.7)**
- **Total: 786 tests, 48 archivos, ~20,000+ líneas**

### v1.8.0 — Production Hardening (2026-03-07)
**Hito:** Monitoreo de salud, control de recursos y ecosistema de plugins.
- HealthMonitor: monitoreo de salud del sistema con checks extensibles
  - HealthCheck, Alert, ResourceMetrics (CPU, RAM, disco via psutil)
  - Checks built-in: resources, data_dirs, disk_space
  - Factory methods para checks de brain y memory
  - Sistema de alertas con acknowledge individual/global
  - Reportes completos y thresholds configurables
- RateLimiter: control de uso de recursos con Token Bucket
  - TokenBucket: algoritmo clasico con refill por tiempo
  - 5 buckets predefinidos: inference, tools, self_modify, disk_write, api_external
  - CooldownTracker: cooldowns por accion (evolucion, backup, health_check, rag_reindex)
  - UsageTracker: analytics de uso por recurso (tasas/min, /hora)
  - Toggle on/off, reset individual/global
- PluginMarketplace: ecosistema de plugins con discovery e instalacion
  - Registry local (plugin_registry/available/) con manifests JSON
  - Search por nombre, descripcion, tags, autor
  - Install/uninstall/update con verificacion de dependencias
  - Sistema de ratings (1-5 estrellas, promedio incremental)
  - Generador de templates para nuevos plugins
  - Persistencia de indice en manifest.json
- Fix: test_v1_7 version check cambiado a >= para forward compatibility
- Dependencia agregada: psutil>=5.9.0 para monitoreo de recursos
- **245 tests pasando (suite v1.8)**
- **Total: 1031 tests, 52 archivos, ~23,000+ líneas**

### v1.9.0 — Automatizacion & Configuracion (2026-03-07)
**Hito:** Scheduler, perfiles de configuracion, y profiling de rendimiento.
- TaskScheduler: programacion de tareas periodicas tipo cron
  - ScheduledTask con intervalos configurables y ejecucion automatica
  - ExecutionLog con historial, queries por tarea y por fallas
  - tick() cooperativo (sin threads), pause/resume, toggle por tarea
  - run_task_now() para ejecucion inmediata
  - Reportes con proximas ejecuciones y stats de exito/fallo
- ConfigManager: export/import de configuraciones completas
  - ConfigProfile con secciones serializables a JSON
  - Collector/Applier pattern para capture y restore de subsistemas
  - save/load/delete/apply profiles con persistencia en disco
  - compare_profiles con diff recursivo de dicts
  - export/import a rutas externas para portabilidad
- PerformanceProfiler: profiling de subsistemas con deteccion de bottlenecks
  - TimingRecord con percentiles (p50, p95), min/max, trend detection
  - Context manager (with profiler.measure()) y start/stop manual
  - Deteccion automatica de degradacion (primera vs segunda mitad de muestras)
  - Bottlenecks, slow operations, most called, highest error rate
  - Thresholds configurables para alertas de lentitud
- **215 tests pasando (suite v1.9)**
- **Total: 1246 tests, 55 archivos, ~26,000+ lineas**

### v2.0.0 — (Pendiente)
Candidatos:
- [ ] Embeddings locales con sentence-transformers (upgrade RAG)
- [ ] Multi-modal input (imagenes)
- [ ] Web UI v2 con dashboard de metricas en tiempo real
- [ ] Modo autonomo (Genesis opera sin input humano por periodos)

---

## Decisiones Técnicas Clave

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| ctransformers sobre llama-cpp-python | llama-cpp-python | Mejor soporte CUDA directo en el momento de inicio |
| Flask sobre FastAPI | FastAPI | Más ligero, sin necesidad de async para SSE simple |
| JSON files sobre SQLite | SQLite | Simplicidad para datos pequeños, sin ORM |
| TF-IDF propio sobre sklearn | sklearn | Cero dependencias adicionales para búsqueda |
| Unittest sobre pytest | unittest incluido | pytest más expresivo, mejor output |
