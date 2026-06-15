# GENESIS — Evolución del Proyecto

## Objetivo Principal
Sistema de IA auto-evolutivo con motor LLM multi-proveedor y **meta estratégica de soberanía digital** —
cero dependencia de APIs externas. App de escritorio tipo Copilot + Web UI. Control total del dispositivo.
Hardware: RTX 3060 Ti (8GB VRAM), i7-13700KF, 16 GB RAM, Windows 11 Pro.

## Stack Tecnológico
| Componente | Tecnología | Razón |
|---|---|---|
| Lenguaje | Python 3.10+ | Ecosistema ML/AI maduro |
| **Motor LLM primario** | **Ollama local** (Genesis/Llama 3.1 8B + Qwen 2.5 Coder 7B) | Soberanía digital, sin API keys, GPU nativa |
| Motor LLM fallback | Gemini / OpenAI / Anthropic (opcional) | Failover si Ollama cae |
| **Router** | `core/provider_router.py` (v6.0) | Circuit breaker + task classifier + multi-model |
| Desktop App | PyWebView + pystray + keyboard | Sidebar nativa tipo Copilot, sin navegador |
| Web UI | Flask + SSE | Ligero, sin dependencias pesadas |
| Tests | Framework custom `test(name, condition)` | No pytest — custom para el proyecto |
| Hardware | RTX 3060 Ti (8GB VRAM), 16GB RAM | GPU consumer accesible |
| Hardware objetivo | RTX 4060 Ti 16GB (financiado por bots de trading) | Modelos 14B calientes + DeepSeek Coder V2 Lite |

## Arquitectura
```
GENESIS/
├── genesis.py              # Clase principal Genesis (~6,500+ líneas)
├── genesis_desktop.py      # Desktop app tipo Copilot (PyWebView sidebar)
├── config.py               # Configuración central (multi-proveedor)
├── web_ui.py               # Interfaz web Flask + SSE (~3,500+ líneas)
├── GENESIS_DESKTOP.bat     # Launcher desktop (limpia __pycache__)
├── core/                   # 113+ módulos del sistema
│   ├── brain.py            # Interfaz con LLM (4 proveedores: Ollama, Gemini, OpenAI, Anthropic)
│   ├── local_engine.py     # Motor ctransformers + CUDA
│   ├── memory.py           # Memoria corto/largo plazo + TF-IDF
│   ├── evolution.py        # Auto-evolución con fitness tracking
│   ├── knowledge_graph.py  # Grafo de conocimiento con PageRank
│   ├── tool_creator.py     # Creador dinámico de herramientas
│   ├── self_modifier.py    # Auto-modificación de código
│   ├── self_evaluator.py   # Auto-evaluación de calidad (v2.3)
│   ├── skill_memory.py     # Memoria de procedimientos HOW-TO (v2.3)
│   ├── chain_engine.py     # Razonamiento multi-paso (v2.3)
│   ├── episodic_memory.py  # Memoria episódica temporal (v2.4)
│   ├── meta_learner.py     # Meta-aprendizaje estratégico (v2.4)
│   ├── personality_evolver.py # Evolución de personalidad (v2.4)
│   ├── goal_manager.py     # Sistema de metas auto-dirigidas (v2.5)
│   ├── reflection_engine.py # Auto-reflexión profunda (v2.5)
│   ├── context_router.py   # Ensamblaje inteligente de contexto (v2.5)
│   ├── causal_reasoner.py  # Razonamiento causa-efecto con grafos (v2.6)
│   ├── concept_synthesizer.py # Síntesis cross-domain de conceptos (v2.6)
│   ├── strategic_planner.py # Planificación jerárquica con dependencias (v2.6)
│   ├── prompt_templates.py # Templates auto-detectados por tags
│   ├── proactive.py        # Motor de sugerencias proactivas
│   ├── project_generator.py# Generador multi-archivo
│   └── ... (18 módulos más)
├── tests/                  # 28 suites, 5387 tests
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

### v2.0.0 — Autonomous Genesis (2026-03-07)
**Hito mayor:** Busqueda semantica, dashboard centralizado, y operacion autonoma.
- EmbeddingsEngine: motor de embeddings local para busqueda semantica
  - VectorStore con busqueda por similitud coseno y persistencia (JSON + numpy)
  - sentence-transformers (GPU) como backend principal, TF-IDF fallback
  - TFIDFEmbedder con hashing trick (MD5 -> dimension fija) como fallback
  - add_text, add_texts_batch, search, get_similar
  - Soporte batch encoding (eficiente en GPU con batch_size=32)
- DashboardAPI: metricas centralizadas de todos los subsistemas
  - MetricCollector pattern: lambdas registradas por subsistema/categoria
  - MetricTimeline: series temporales para cada metrica con max_points
  - collect_all() agrega snapshots globales con agrupacion por categoria
  - generate_dashboard() para CLI, export_json() para Web UI
  - get_timeline() para graficos temporales de metricas especificas
- AutonomousMode: operacion sin input humano con SafetyGuard
  - AutonomousAction con prioridades (1-10), cooldowns, y safe flag
  - SafetyGuard: max ciclos, max duracion, max failures consecutivas, forbidden actions
  - tick() cooperativo — ejecuta acciones elegibles por prioridad
  - Auto-stop en limites de seguridad (ciclos, tiempo, fallas)
  - Acciones prohibidas (delete_files, modify_core, send_network, execute_shell)
  - Registro de violaciones de seguridad, log de actividad
- **258 tests pasando (suite v2.0)**
- **Total: 1504 tests, 58 archivos, ~29,000+ lineas**

### v2.1.0 — Web Intelligence (2026-03-07)
**Hito:** Genesis accede a internet. Busca, lee y aprende de la web.
- WebIntelligence: modulo de acceso a internet con aprendizaje
  - WebSearcher: busqueda via DuckDuckGo (sin API key, gratis)
  - WebReader: extraccion de contenido con requests + BeautifulSoup
  - LearnedItem: tracking de paginas aprendidas con persistencia
  - search_and_learn(): flujo completo buscar -> leer -> indexar en embeddings
  - recall(): busqueda semantica en conocimiento aprendido de la web
  - Rate limiting integrado (min 2s entre busquedas DDG)
  - Graceful degradation sin internet (no crashea)
  - Chunking inteligente por parrafos para embeddings
  - 9 comandos: /web search, /web read, /web learn, /web news, /web recall, etc.
- **116 tests pasando (suite v2.1)**
- **Total: 1620 tests, 59 archivos, ~30,000+ lineas**

### v2.2.0 — Semantic Intelligence (2026-03-12)
**Hito:** Busqueda semantica en memoria, optimizacion de inferencia y dashboard en tiempo real.
- SemanticMemory: busqueda por similitud semantica en conversaciones
  - Indexacion automatica de cada interaccion en EmbeddingsEngine
  - Recall por similitud coseno con threshold configurable
  - Inyeccion de contexto semantico relevante en prompts
  - Deduplicacion por similitud antes de almacenar
- InferenceOptimizer: optimizacion automatica de parametros del modelo
  - Ajuste de temperature, top_p, repetition_penalty por intent
  - Benchmark runner para medir tokens/s y latencia
  - Presets por tipo de tarea (creative, code, research, chat)
  - Cache de configuraciones optimas por intent
- LiveDashboard: metricas en tiempo real via web UI
  - Server-Sent Events (SSE) para actualizacion sin polling
  - Graficos de performance, memoria, embeddings en tiempo real
  - Health grid de todos los subsistemas
  - Export de datos historicos
- **218 tests pasando (suite v2.2)**
- **Total: 1838 tests, 62 archivos, ~32,000+ lineas**

### v2.3.0 — Cognitive Self-Improvement (2026-03-12)
**Hito:** Genesis evalua sus propias respuestas, aprende procedimientos y razona multi-paso.
- SelfEvaluator: auto-evaluacion heuristica de calidad de respuestas
  - QualityScorer: 5 metricas (relevance, length, specificity, completeness, error_free)
  - PatternTracker: patrones de calidad por intent con trend detection
  - AutoTuner: ajuste automatico de temperature/max_tokens por intent basado en feedback
  - Grados A-F con persistencia y reportes detallados
- SkillMemory: memoria de procedimientos HOW-TO
  - SkillExtractor: detecta preguntas procedurales y extrae pasos
  - Almacenamiento con deduplicacion por containment similarity
  - Recall por keywords con inyeccion de skills en prompt
  - Eviccion por calidad + uso + antiguedad
- ChainEngine: razonamiento multi-paso forzado para preguntas complejas
  - ChainPlanner: detecta complejidad por indicadores y descompone en sub-preguntas
  - 6 templates (compare, analyze, optimize, design, explain_why, generic)
  - ChainMemory: reutiliza cadenas exitosas por similitud de query
  - Contexto acumulativo entre pasos
- Integracion: skill context en prompt, auto-tuned temperature, post-process evaluation
- Comandos: /evaluate, /eval, /skills, /chain, /chain toggle
- **248 tests pasando (suite v2.3)**
- **Total: 2086 tests, 65 archivos, ~35,000+ lineas**

### v2.4.0 — Adaptive Intelligence (2026-03-12)
**Hito:** Genesis recuerda episodios, aprende de sus estrategias y evoluciona su personalidad.
- EpisodicMemory: memoria temporal de episodios de conversación
  - Episode: timestamp, topics, summary, emotional_tone, key_facts, tags
  - EpisodeBuilder: detección automática de temas (7 categorías), tono emocional (5 tonos), extracción de hechos
  - TimelineIndex: consultas por rango temporal, últimos N, últimas horas, por tema, por keyword
  - start_episode/end_episode/record_message con recall por relevancia
  - Inyección de contexto episódico en prompts (get_context_for_prompt)
- MetaLearner: meta-aprendizaje de estrategias de respuesta
  - StrategyRecord: registra intent, template, temperature, chain_used, skill_injected, score, feedback
  - PatternDetector: análisis por intent, template, impacto de chains, impacto de skills, correlación de temperature
  - LearningInsight: insights descubiertos con categoría, confianza y recomendación
  - get_recommendation() sugiere configuración óptima por intent
  - Análisis automático cada 10 records
- PersonalityEvolver: evolución gradual de personalidad
  - TraitVector: 8 rasgos (curiosity, verbosity, formality, creativity, precision, humor, assertiveness, empathy)
  - DriftEngine: deltas por feedback (+/-), tono emocional, tipo de intent
  - Decay gradual hacia personalidad base por inactividad
  - Snapshots periódicos de estado de personalidad
  - to_prompt_hints() genera directivas de personalidad para el prompt
- Integración: episodic context en prompt, personality hints, strategy recording post-process
- Comandos: /episodes, /metalearner, /personality
- **257 tests pasando (suite v2.4)**
- **Total: 2343 tests, 68 archivos, ~37,000+ líneas**

### v2.5.0 — Self-Directed Intelligence (2026-03-12)
**Hito:** Genesis se pone metas, reflexiona sobre su rendimiento y ensambla contexto inteligentemente.
- GoalManager: sistema de metas auto-dirigidas
  - Goal: título, descripción, prioridad (1-10), progreso (0-1), sub-goals, notas
  - GoalTracker: seguimiento automático, detección de metas estancadas, priorización
  - GoalSuggester: sugiere metas desde meta-learner insights, topics frecuentes y knowledge gaps
  - Auto-tracking de progreso por keywords en conversación
  - Deduplicación por containment similarity de títulos
  - Evicción de metas abandonadas/completadas antiguas
- ReflectionEngine: auto-reflexión profunda periódica
  - ReflectionEntry: observaciones, fortalezas, puntos ciegos, plan de mejora, confianza
  - SelfAnalyzer: analiza tendencia de calidad, distribución de intents, ratio feedback, drift de personalidad
  - Reflexión automática cada 25 interacciones
  - Detección de sobre-especialización, feedback pobre, personalidad inestable
  - Historial de reflexiones con persistencia
- ContextRouter: ensamblaje inteligente de contexto
  - ContextSource: fuentes registradas con getter, prioridad base, keywords
  - ContextBudget: asignación proporcional de chars por relevancia (total 3000 chars)
  - Scoring por keywords + historial de utilidad (moving average)
  - 5 fuentes integradas: semantic_memory, episodic_memory, skill_memory, goals, reflection
  - record_feedback ajusta avg_usefulness por fuente
- Integración: goals context en prompt, reflection context, auto-tracking post-process, reflexión periódica
- Comandos: /goals, /reflection, /router
- **268 tests pasando (suite v2.5)**
- **Total: 2611 tests, 71 archivos, ~40,000+ líneas**

### v2.6.0 — Cognitive Architecture (2026-03-12)
**Hito:** Genesis razona causalmente, sintetiza conceptos cross-domain y planifica estratégicamente.
- CausalReasoner: razonamiento causa-efecto con grafos dirigidos
  - CausalLink: relación causa→efecto con confianza, refuerzos y contradicciones
  - CausalGraph: grafo DAG con índices forward/backward, trace_chain (BFS forward), trace_reverse (BFS backward)
  - CausalInference: 6 patrones regex para extracción automática de pares causales del texto
  - Detección de preguntas causales (por qué, qué causa, qué pasa si)
  - why(): traza causas hacia atrás; what_if(): traza efectos hacia adelante
  - Refuerzo automático de links duplicados, evicción de links débiles
  - Inyección de razonamiento causal en prompts para preguntas causales
- ConceptSynthesizer: síntesis creativa cross-domain de conceptos
  - Concept: propiedades, relaciones, dominio, usage/synthesis counts
  - AnalogyFinder: encuentra analogías cross-domain por similitud de propiedades (containment)
  - SynthesisEngine: genera insights combinando conceptos con templates, novelty scoring
  - Detección automática de dominio (6 dominios) y propiedades (8 propiedades) por keywords
  - auto_synthesize(): genera síntesis desde las mejores analogías encontradas
  - Novelty score: domain distance × similarity optimum × freshness
  - Evicción por usage+synthesis count
- StrategicPlanner: planificación jerárquica multi-fase con dependencias
  - Phase: status (pending/ready/in_progress/completed/blocked/skipped), prerequisitos, acciones, progreso
  - Milestone: checkpoint con target phases, auto-check al completar fases
  - PlanGraph: DAG con topological sort, critical path (BFS longest), overall progress
  - AdaptiveScheduler: adapta prioridades por bloqueos, eficiencia, feedback; sugiere próximas fases
  - Multiple plans con plan activo, auto-tracking por keywords
  - estimate_completion() calcula horas restantes
  - Evicción de planes completados más antiguos
- Integración: causal/synth/plan context en prompt, auto-extract post-process, auto-track
- Comandos: /causal, /synthesis, /planner
- **311 tests pasando (suite v2.6)**
- **Total: 2922 tests, 74 archivos, ~43,000+ líneas**

### v2.7.0 — Predictive Intelligence (2026-03-12)
**Módulos: PatternPredictor, AnomalyDetector, AdaptiveInterface**
- PatternPredictor: anticipación de necesidades del usuario
  - TransitionMatrix: cadena de Markov de primer orden para transiciones de intents
  - TemporalPattern: patrones por hora del día y día de semana
  - SequencePredictor: n-gramas (window=3) con peso por longitud de secuencia
  - Combinación ponderada: Markov (0.4) + Temporal (0.3) + Secuencia (0.3)
  - Accuracy tracking con verify_prediction()
- AnomalyDetector: detección de anomalías en métricas del sistema
  - MetricStream: serie temporal con deque(maxlen=50), mean/std/trend incrementales
  - ZScoreDetector: warning a 2σ, critical a 3σ
  - TrendBreakDetector: detecta transiciones rising↔falling
  - Streams automáticos: response_time, response_length, quality_score
- AdaptiveInterface: aprendizaje de preferencias del usuario
  - UserPreference: tracking bayesiano con learning rate decreciente
  - PreferenceTracker: detección de señales (verbosity, technical_level, format)
  - ResponseAdapter: genera directivas de estilo para inyectar en prompt
  - Feedback loop: observe_input() + observe_feedback() → adapta estilo
- Fix: bug de scope `_response_time` → `self._last_response_time` en post-process
- Integración completa 10/10 puntos × 3 módulos
- Comandos: /predictor, /anomalies, /adaptive
- **318 tests pasando (suite v2.7)**
- **Total: 3240 tests, 18 suites, 55 archivos, ~46,000+ líneas**

### v2.8.0 — Reasoning Architecture (2026-03-12)
**Módulos: HypothesisEngine, ExplanationEngine, DialogueStrategist**
- HypothesisEngine: formulación y evaluación iterativa de hipótesis
  - Evidence: pieza de evidencia con peso y dirección (supports/contradicts)
  - Hypothesis: statement con evidencia, confidence bayesiana, auto-confirm/refute
  - HypothesisGenerator: extrae hipótesis por patrones regex (especulativo, creencia, condicional, causal)
  - HypothesisEvaluator: evalúa relevancia por overlap, detecta soporte/contradicción, rankea por plausibility
  - Plausibility scoring = confidence × certainty factor
- ExplanationEngine: explicaciones multi-nivel con banco reutilizable
  - Explanation: 4 niveles (simple, technical, analogical, step_by_step), tracking de usos y feedback
  - ExplanationTemplate: directivas de estilo por nivel para prompt
  - QualityScorer: evalúa por longitud, estructura, adecuación al nivel, feedback histórico
  - detect_explanation_need(): detecta si el input solicita explicación y a qué nivel
  - Evicción por relevance_score (quality × effectiveness)
- DialogueStrategist: 6 estrategias conversacionales adaptativas
  - Estrategias: Socrático, Didáctico, Exploratorio, Directivo, Colaborativo, Reflexivo
  - StrategySelector: selecciona por señales textuales, intent y longitud de conversación
  - EngagementTracker: rastrea uso, feedback y efectividad por estrategia
  - Auto-switch a mejor estrategia cuando la actual tiene baja efectividad
- Integración completa 10/10 puntos × 3 módulos
- Comandos: /hypothesis, /explanations, /dialogue
- **246 tests pasando (suite v2.8)**
- **Total: 3486 tests, 19 suites, 58 archivos, ~50,000+ líneas**

### v2.9.0 — Meta-Cognitive Architecture (2026-03-12)
**Módulos: CognitiveMonitor, AbstractionEngine, LearningOptimizer**
- CognitiveMonitor: monitoreo de carga cognitiva del sistema
  - CognitiveMetric: deque maxlen=100, umbrales warning/critical configurables
  - CognitiveLoad: snapshot ponderado (context 0.35, latency 0.25, memory 0.2, modules 0.2)
  - OverloadDetector: detecta 4 áreas de sobrecarga con sugerencias específicas
  - Niveles: low, moderate, high, critical con auto-clamp [0.0, 1.0]
  - get_context_for_prompt() solo inyecta si carga es high o critical
- AbstractionEngine: extracción de patrones de interacción
  - AbstractPattern: confianza asintótica n/(n+3), strength = conf*0.7 + app_factor*0.3
  - PatternMatcher: 5 patrones (debug_cycle, learning_sequence, implementation_flow, refactor, exploration_spiral)
  - Containment similarity: |A∩B|/min(|A|,|B|) para detectar repeticiones
  - Auto-detección de patrones repetitivos cuando similitud > 0.5 en 2+ inputs previos
  - Evicción por strength cuando excede max_patterns
- LearningOptimizer: optimización de aprendizaje con knowledge gaps
  - LearningRate: decaimiento exponencial (0.95^successes), min 5%, boost 1.2× en failures
  - KnowledgeGap: brechas con severity creciente por ocurrencias, resolución automática
  - LearningStrategy: 5 estrategias (spaced_repetition, active_recall, interleaving, elaboration, concrete_examples)
  - Selección automática por mastery: novato→ejemplos, bajo→elaboración, medio→recall, alto→intercalación
  - Mastery = success_ratio × experience_factor, efficiency = mastery/log(interactions+2)
- Integración completa 10/10 puntos × 3 módulos
- Comandos: /cognitive, /abstraction, /learning
- **298 tests pasando (suite v2.9)**
- **Total: 3784 tests, 20 suites, 61 archivos, ~52,000+ líneas**

### v3.0.0 — Unified Consciousness (2026-03-12)
**Módulos: UnifiedMind, DreamEngine, SelfNarrative**
- UnifiedMind: estado de consciencia unificado cross-módulo
  - ConsciousnessState: 5 dimensiones (mood, energy, focus, curiosity, confidence)
  - MoodComputer: procesa señales positivas/negativas con decay hacia neutro
  - FocusTracker: rastrea consistencia de dominio, dominant_domain por frecuencia
  - 5 niveles de estado: critical, low, neutral, good, optimal
  - awareness_score = promedio de 5 dimensiones, peak tracking
- DreamEngine: procesamiento offline de experiencias (consolidación REM)
  - DreamFragment: fragmento con emotional_weight, strength con consolidate/decay
  - ConsolidationStrategy: 4 estrategias (emotional, frequency, connection, recency)
  - DreamProcessor: ciclos de consolidación con boost a fuertes y decay a débiles
  - Conexiones por dominio entre fragmentos, evicción de fragmentos débiles
  - dream() ejecuta un ciclo completo: pending → fragments → consolidation → eviction
- SelfNarrative: narrativa autobiográfica continua
  - NarrativeEntry: 4 tipos (observation, milestone, reflection, learning)
  - MilestoneDetector: thresholds progresivos, no repite hitos alcanzados
  - IdentityTracker: rasgos emergentes (curioso, técnico, creativo, analítico, colaborativo, persistente)
  - Evicción preserva milestones, descarta observations antiguas
  - get_narrative_summary(): resumen en primera persona de la historia
- Integración completa 10/10 puntos × 3 módulos
- Comandos: /mind, /dream, /narrative
- **239 tests pasando (suite v3.0)**
- **Total: 4023 tests, 21 suites, 64 archivos, ~55,000+ líneas**

### v3.1.0 — Social Intelligence (2026-03-13)
**Hito:** Genesis entiende emociones, responde con empatía y maneja conflictos conversacionales.
- **EmotionReader** (`core/emotion_reader.py`): detección de emociones del usuario en texto
  - EmotionSignal: señal emocional con tipo, intensidad y evidencia léxica
  - EmotionProfile: perfil emocional con historial y tendencia (mejorando/empeorando)
  - EmotionReader coordinador: detect(), get_trend(), get_context_for_prompt()
  - Clasificador multi-etiqueta: alegría, frustración, confusión, curiosidad, urgencia, neutral
  - Scoring por señales léxicas (puntuación, mayúsculas, palabras clave emocionales)
- **EmpathyEngine** (`core/empathy_engine.py`): generación de respuestas empáticas
  - EmpathyStrategy: 5 estrategias (validar, redirigir, profundizar, celebrar, calmar)
  - EmpathyEngine coordinador: select_strategy(), generate_modifier(), get_context_for_prompt()
  - Selección automática por emoción detectada + historial
  - Tracking de efectividad por feedback posterior
- **ConflictResolver** (`core/conflict_resolver.py`): manejo de desacuerdos y correcciones
  - ConflictSignal: detección de señales de conflicto por patrones léxicos
  - ConflictResolver coordinador: detect(), resolve(), get_context_for_prompt()
  - Estrategias: conceder, reformular, pedir clarificación, ofrecer alternativas
  - Escalation tracker: mide si el conflicto se resuelve o escala
- **314 tests pasando (suite v3.1)**
- **Total: 4337 tests, 22 suites, 67 archivos**

### v3.2.0 — Creative Genesis (2026-03-13)
**Hito:** Genesis genera contenido creativo estructurado con técnicas de ideación.
- **StoryGenerator** (`core/story_generator.py`): narrativa creativa con estructura
  - StoryArc: 5 actos (setup, rising_action, climax, falling_action, resolution) con progress tracking
  - CharacterProfile: name, traits, motivation, arc_type (hero, mentor, trickster, shadow) con inferencia automática
  - StoryTemplate: 4 géneros (sci_fi, fantasy, thriller, slice_of_life) con setting/conflict/tone y auto-detección por keywords
  - StoryGenerator coordinador: create_story(), add_character(), advance_act(), get_context_for_prompt()
  - Persistencia JSON, múltiples historias con historia activa
- **CodeArchitect** (`core/code_architect.py`): diseño de sistemas de software
  - ArchitecturePattern: 5 patrones (mvc, microservices, event_driven, layered, hexagonal) con pros/cons/best_for y auto-detección
  - ComponentSpec: name, type (service, controller, model, view, util), dependencies, description
  - DesignDecision: decision, rationale, alternatives, chosen_at timestamp
  - CodeArchitect coordinador: design_system(), add_component(), record_decision(), get_context_for_prompt()
  - Persistencia JSON, múltiples diseños con diseño activo
- **IdeaBrainstormer** (`core/idea_brainstormer.py`): ideación divergente estructurada
  - BrainstormMethod: 4 métodos (scamper, six_hats, mind_map, what_if) con prompts/steps y auto-detección
  - IdeaEntry: content, method, score (viability/novelty/impact), tags, timestamp
  - IdeaScorer: scoring automático por señales léxicas, overall = weighted avg (viability 0.4, novelty 0.3, impact 0.3)
  - IdeaBrainstormer coordinador: brainstorm(), add_idea(), get_best_ideas(), combine_ideas(), get_context_for_prompt()
  - Persistencia JSON, sesiones de brainstorming con ideas vinculadas
- **240 tests pasando (suite v3.2)**
- **Total: 4337 tests, 23 suites, 70 archivos**

### v3.3.0 — Sensory Expansion (2026-03-13)
**Hito:** Genesis procesa imágenes, genera diagramas Mermaid y tiene personalidad vocal adaptativa.
- **ImageAnalyzer** (`core/image_analyzer.py`): análisis de imágenes local basado en metadatos
  - ImageMetadata: extracción de path, formato (extension), tamaño (os.path), timestamp
  - AnalysisResult: descripción generada, tags, objetos detectados, confianza, cached flag
  - AnalysisCache: cache LRU path→result, max_entries=100, evicción por antigüedad de acceso
  - ImageAnalyzer coordinador: analyze(), describe(), get_cached(), get_context_for_prompt()
  - 10 patrones de filename (screenshot, logo, chart, diagram...) → tags y objetos automáticos
  - 9 contextos de carpeta (assets, screenshots, icons...) → semántica adicional
  - Métricas: total_analyzed, cache_hits, cache_misses, hit_rate
- **DiagramGenerator** (`core/diagram_generator.py`): generación de diagramas Mermaid desde texto
  - DiagramType: 6 tipos (flowchart, sequence, class_diagram, er_diagram, state, gantt) con templates
  - DiagramSpec: title, nodes[], edges[], raw_mermaid, serialización completa
  - DiagramDetector: detección automática por keywords ("flujo"→flowchart, "secuencia"→sequence, etc.)
  - DiagramGenerator coordinador: generate(), add_node(), add_edge(), get_mermaid(), get_context_for_prompt()
  - Extracción automática de nodos/edges por patrones regex (→, conecta, envía, listas con viñetas)
  - Renderizado Mermaid completo con formatos específicos por tipo de diagrama
- **VoicePersonality** (`core/voice_personality.py`): personalidad vocal adaptativa
  - VocalStyle: 4 parámetros (speed 0.5-2.0, pitch 0.5-2.0, emphasis_level 0-1, pause_frequency 0-1)
  - EmotionalVoice: 8 emociones mapeadas a ajustes de estilo (frustración=lento+grave, alegría=rápido+agudo, etc.)
  - ProsodyRule: 6 reglas por contenido (explanation=lento, code=monótono, warning=serio, etc.)
  - VoicePersonality coordinador: adapt_to_emotion(), adapt_to_content(), get_vocal_directives(), get_context_for_prompt()
  - Métricas: total_adaptations, emotion_counts, content_type_counts
- **174 tests pasando (suite v3.3)**
- **Total: 4337 tests, 23 suites, 73 archivos**

### v3.4.0 — Collaborative Mind (2026-03-13)
**Hito:** Múltiples instancias de Genesis colaboran y comparten conocimiento.
- **PeerDebate** (`core/peer_debate.py`): debate multi-instancia estructurado
  - DebateRole: 5 perspectivas predefinidas (optimista, pesimista, pragmático, visionario, abogado del diablo)
  - DebateArgument: argumento con stance, evidence list, confidence scoring
  - DebateRound: ronda con argumentos, counter-arguments y resolución
  - PeerDebate coordinador: create_debate(), add_argument(), resolve_round(), get_context_for_prompt()
  - Convergencia por votación ponderada (confianza × argumentos)
- **ConsensusEngine** (`core/consensus_engine.py`): búsqueda de consenso entre agentes
  - Opinion: opinión con posición, confianza y evidencia
  - AgreementMetric: métricas de acuerdo con similitud de posiciones
  - DelphiRound: rondas Delphi modificadas con convergencia
  - ConsensusEngine coordinador: create_consensus(), add_opinion(), run_round(), get_context_for_prompt()
- **KnowledgeSharing** (`core/knowledge_sharing.py`): compartir aprendizaje entre sesiones
  - KnowledgePacket: paquete de conocimiento serializable
  - KnowledgeIndex: índice de conocimiento compartido con búsqueda
  - MergeStrategy: estrategias de merge sin duplicados
  - KnowledgeSharing coordinador: share(), receive(), merge(), get_context_for_prompt()
- **51 tests pasando (suite v3.4)**
- **Total: 4388 tests, 24 suites, 76 archivos**

### v3.5.0 — Autonomous Research (2026-03-13)
**Hito:** Genesis investiga autónomamente, lee papers y genera descubrimientos.
- **PaperReader** (`core/paper_reader.py`): lectura y análisis de papers académicos
  - PaperMetadata: extracción de título, autores, abstract, secciones
  - PaperParser: parseo de PDFs con extracción de claims y metodología
  - PaperReader coordinador: read_paper(), extract_claims(), summarize(), get_context_for_prompt()
  - Cross-referencing con knowledge graph existente
- **ExperimentRunner** (`core/experiment_runner.py`): experimentación autónoma
  - ExperimentDesign: hipótesis, variables, métricas, protocolo
  - ExperimentResult: resultados con análisis estadístico básico
  - ExperimentRunner coordinador: design(), run(), analyze(), get_context_for_prompt()
  - Ejecución en sandbox con timeout, reproducibilidad por seed
- **InsightSynthesizer** (`core/insight_synthesizer.py`): generación de descubrimientos
  - InsightEntry: insight con evidencia, confianza y novedad
  - InsightSynthesizer coordinador: synthesize(), evaluate_novelty(), get_context_for_prompt()
  - Cross-domain pattern matching, novelty detection, confidence scoring
- **52 tests pasando (suite v3.5)**
- **Total: 4440 tests, 25 suites, 79 archivos**

### v4.0.0 — Autonomous Evolution (2026-03-13)
**Hito mayor:** Genesis modifica su propio código de forma segura, evoluciona arquitectura y genera nuevos módulos.
- **SafeCodeEvolver** (`core/safe_code_evolver.py`): evolución de código con validación AST
  - CodeMutation: mutación con tipo, target, validación pre/post
  - SafeCodeEvolver coordinador: propose_mutation(), apply(), rollback(), get_context_for_prompt()
  - Mutaciones controladas, rollback automático si tests fallan, fitness function
- **ArchitectureEvolver** (`core/architecture_evolver.py`): evolución de la propia arquitectura
  - ArchitectureProposal: propuesta con justificación e impacto simulado
  - ArchitectureEvolver coordinador: analyze(), propose(), simulate_impact(), get_context_for_prompt()
  - Detección de módulos infrautilizados, propuesta de fusión/split
- **ModuleGenerator** (`core/module_generator.py`): Genesis crea sus propios módulos nuevos
  - ModuleSpec: especificación de módulo con código, tests e integración
  - ModuleGenerator coordinador: detect_gap(), generate(), review(), get_context_for_prompt()
  - Generación de código + tests + integración automática
- **52 tests pasando (suite v4.0)**
- **Total: 4492 tests, 26 suites, 82 archivos**

### v4.1.0 — Temporal Intelligence (2026-03-13)
**Hito:** Genesis comprende y razona sobre el tiempo.
- **TemporalReasoner** (`core/temporal_reasoner.py`): razonamiento temporal explícito
  - TemporalEvent: evento con timestamp, duración, relaciones temporales
  - Timeline: eventos ordenados con consultas por rango
  - TemporalReasoner coordinador: add_event(), query_range(), predict_duration(), get_context_for_prompt()
- **ScheduleOptimizer** (`core/schedule_optimizer.py`): optimización de agendas y workflows
  - ScheduleEntry: tarea con deadline, prioridad, duración estimada
  - ScheduleOptimizer coordinador: add_task(), optimize(), detect_conflicts(), get_context_for_prompt()
  - Algoritmos earliest-deadline y priority-based
- **TrendForecaster** (`core/trend_forecaster.py`): predicción de tendencias
  - TrendSeries: serie temporal con moving average y exponential smoothing
  - TrendForecaster coordinador: add_datapoint(), forecast(), detect_seasonality(), get_context_for_prompt()
  - Alertas predictivas basadas en tendencia
- **52 tests pasando (suite v4.1)**
- **Total: 4544 tests, 27 suites, 85 archivos**

### v4.2.0 — Ethical Framework (2026-03-13)
**Hito:** Genesis tiene principios éticos explícitos y razona moralmente.
- **EthicalReasoner** (`core/ethical_reasoner.py`): razonamiento ético multi-framework
  - EthicalFramework: utilitarismo, deontología, virtue ethics, care ethics
  - EthicalEvaluation: evaluación por múltiples lentes éticas
  - EthicalReasoner coordinador: evaluate(), detect_dilemma(), get_context_for_prompt()
- **BiasDetector** (`core/bias_detector.py`): detección de sesgos en respuestas
  - BiasScan: análisis de lenguaje por sesgo de género, cultural, técnico
  - BiasDetector coordinador: scan(), audit(), suggest_reformulation(), get_context_for_prompt()
- **TransparencyEngine** (`core/transparency_engine.py`): explicación de decisiones internas
  - DecisionTrace: traza completa de por qué eligió cada estrategia
  - TransparencyEngine coordinador: trace(), explain(), get_context_for_prompt()
  - Confidence intervals en cada decisión
- **52 tests pasando (suite v4.2)**
- **Total: 4596 tests, 28 suites, 88 archivos**

### v4.3.0 — Knowledge Mastery (2026-03-13)
**Hito:** Genesis domina dominios específicos con profundidad de experto.
- **DomainExpert** (`core/domain_expert.py`): especialización profunda en dominios
  - DomainProfile: taxonomía, terminología, reglas por dominio
  - DomainExpert coordinador: detect_domain(), adjust_depth(), get_context_for_prompt()
  - Detección automática de nivel (novato → experto) por vocabulario
- **TutorEngine** (`core/tutor_engine.py`): enseñanza adaptativa
  - Lesson: lección con prerequisitos, ejercicios, evaluación
  - TutorEngine coordinador: create_lesson(), evaluate(), track_progress(), get_context_for_prompt()
  - Zona de desarrollo próximo (Vygotsky), spaced repetition
- **FactChecker** (`core/fact_checker.py`): verificación de hechos
  - FactCheck: verificación con fuentes, confianza, estado
  - FactChecker coordinador: check(), cross_reference(), get_context_for_prompt()
  - Confidence scoring por fuentes concordantes
- **52 tests pasando (suite v4.3)**
- **Total: 4648 tests, 29 suites, 91 archivos**

### v4.4.0 — Distributed Genesis (2026-03-13)
**Hito:** Genesis puede ejecutar sub-tareas en múltiples GPUs o máquinas.
- **TaskDistributor** (`core/task_distributor.py`): distribución de trabajo
  - WorkerNode: worker con capacidad, health check, estadísticas
  - TaskQueue: cola con prioridades y load balancing
  - TaskDistributor coordinador: submit_task(), assign(), get_context_for_prompt()
- **ResultAggregator** (`core/result_aggregator.py`): consolidación de resultados distribuidos
  - PartialResult: resultado parcial de un worker
  - VotingMechanism: votación por mayoría con similitud de contenido (Jaccard)
  - ResultAggregator coordinador: submit_result(), aggregate(), fallback_to_local(), get_context_for_prompt()
- **NetworkManager** (`core/network_manager.py`): comunicación entre nodos
  - NetworkNode: nodo con dirección, capacidades, heartbeat
  - NetworkManager coordinador: register_node(), discover(), send(), get_context_for_prompt()
  - Discovery automático en red local, health monitoring
- **52 tests pasando (suite v4.4)**
- **Total: 4700 tests, 30 suites, 94 archivos**

### v5.0.0 — Singularity (2026-03-13)
**Hito final:** Genesis es completamente autónoma — investiga, aprende, evoluciona y se mejora sin intervención humana.
- **AutonomousResearchLoop** (`core/autonomous_research_loop.py`): ciclo completo de investigación autónoma
  - ResearchCycle: ciclo gap→hipótesis→experimento→análisis→insight
  - AutonomousResearchLoop coordinador: start_cycle(), step(), get_context_for_prompt()
  - Ciclo continuo con priorización por impacto, human-in-the-loop opcional
- **SelfArchitect** (`core/self_architect.py`): rediseño arquitectónico autónomo
  - ArchitectureSnapshot: snapshot del sistema con métricas y bottlenecks
  - SelfArchitect coordinador: analyze(), propose_refactor(), validate(), get_context_for_prompt()
  - Genera tests antes del cambio, valida después
- **ConsciousnessIntegrator** (`core/consciousness_integrator.py`): integración total de todos los subsistemas
  - ConsciousnessLayer: capa de consciencia con módulos, estado y peso
  - HolisticState: estado holístico con overall_consciousness ponderado
  - EmergentDetector: detecta patrones inesperados por desviación estadística (z-score > 2σ)
  - ConsciousnessIntegrator coordinador: register_layer(), update_state(), detect_emergent(), get_context_for_prompt()
  - Estado de consciencia holístico que influye en todas las decisiones
- **52 tests pasando (suite v5.0)**
- **Total: 4752 tests, 31 suites, 97 archivos, ~70,000+ líneas**

---

### v5.1.0 — Device Control & Anti-Hallucination (2026-03-14)
**Genesis obtiene control real del dispositivo y deja de inventar datos.**
- **Ollama Migration**: Reemplazó ctransformers por Ollama como motor LLM local
  - Llama 3.1 8B via `http://localhost:11434` — respuestas en ~10s vs timeout con ctransformers
  - Brain multi-proveedor (`core/brain.py`): Ollama, OpenAI, Anthropic con streaming nativo
- **Device Tools** (`core/device_tools.py`, ~1000 líneas): 11 clases de control del dispositivo
  - `FileManager` — move, copy, rename, delete, create_folder, file_info
  - `FileSearcher` — búsqueda por nombre, extensión (*.py), tamaño (>100MB)
  - `FileOrganizer` — organización automática por tipo de archivo (13 categorías)
  - `DiskAnalyzer` — uso de disco, archivos grandes, archivos antiguos
  - `DuplicateFinder` — detección de duplicados via MD5 hash (primeros+últimos 8KB)
  - `ProcessManager` — listar procesos, matar procesos
  - `AppLauncher` — abrir archivos/apps con programa por defecto
  - `ClipboardManager` — leer/escribir portapapeles via PowerShell
  - `ScreenCapture` — capturas de pantalla via Pillow o PowerShell fallback
  - `StartupManager` — listar programas de inicio de Windows (registro)
  - `RecycleBin` — listar, restaurar (PowerShell COM), vaciar papelera
  - Directorios protegidos: windows, system32, syswow64, boot, etc.
- **Auto-Tool Pattern** (`genesis.py:_auto_detect_tool()`, ~200 líneas): Intercepta intención del usuario ANTES del LLM
  - Detecta 16+ tipos de intención por keywords (archivos, sistema, procesos, papelera, etc.)
  - Ejecuta herramientas reales y devuelve datos reales — el LLM nunca tiene oportunidad de inventar
  - Path keywords inteligentes: "escritorio"→Desktop, "descargas"→Downloads, etc.
- **Anti-Hallucination Filter** (`genesis.py:_anti_hallucination_filter()`): Post-procesamiento de respuestas LLM
  - Detecta patrones fabricados: "restaurando", "he restaurado", "accediendo a" + indicadores falsos
  - Reemplaza respuestas alucinadas con mensaje honesto
  - Core rules con "NUNCA INVENTES datos del sistema"
- **Bug fixes**:
  - `semantic_memory.py`: `key=` → `doc_id=`, `metadata=` → `extra_metadata=`
  - `skill_memory.py`: `metadata=` → `extra_metadata=`
  - `context_manager.py`: tools section budget 600→3000 tokens
  - `router.py`: Agregó "tools" y "custom_tools" a CHAT_SECTIONS
  - `genesis.py`: Context budget total 3000→8000, "ram" false match en sys_keywords

---

### v5.4.0 — JARVIS: Gemini + Desktop App + Auto-Detect Expansion (2026-03-15)
**Hito:** Genesis se convierte en app de escritorio tipo Copilot, integra Gemini como proveedor inteligente, y elimina hallucination en queries factuales.

#### Gemini API Provider
- **Nuevo proveedor**: Gemini 2.0 Flash (`generativelanguage.googleapis.com/v1beta/`)
- **Auto-selección**: Si `GOOGLE_API_KEY` existe → Gemini; sino → Ollama (fallback local)
- **Streaming SSE**: `streamGenerateContent?alt=sse` — tokens en tiempo real
- **Formato Gemini**: `contents` + `parts` + `systemInstruction` (diferente de OpenAI)
- **Free tier**: 15 RPM, 1M tokens/día — suficiente para uso personal
- **4 proveedores totales**: Ollama (local/gratis), Gemini (recomendado), OpenAI, Anthropic

#### Desktop App (Tipo Copilot)
- **`genesis_desktop.py`** (~470 líneas): App nativa sin necesidad de abrir navegador
- **PyWebView**: Sidebar nativa usando WebView2/Edge como renderer
- **pystray**: Icono en system tray con menú contextual (Mostrar/Ocultar, Cerrar)
- **keyboard**: Hotkey global `Ctrl+Shift+G` para toggle de ventana
- **Splash screen**: Pantalla de carga animada mientras Flask inicia
- **Custom titlebar**: Barra de título con drag, pin (always-on-top), minimize, close-to-tray
- **INJECTED_CSS**: CSS completo para modo sidebar (compact header, tab bar, chat, scrollbar)
- **INJECTED_JS**: Crea titlebar DOM, conecta botones a `pywebview.api`, detecta provider
- **`GENESIS_DESKTOP.bat`**: Launcher que limpia `__pycache__` y abre como sidebar derecha

#### 6 Nuevas Auto-Detecciones (bypass LLM completo)
1. **Fecha/Hora**: `time_keywords`, `date_keywords` → `datetime.now()` instant
2. **Username/Identidad**: `user_keywords` → `os.getenv("USERNAME")` + `COMPUTERNAME`
3. **Dirección IP**: `ip_keywords` → `socket` local + `api.ipify.org` pública
4. **Calculadora**: `math_keywords` → Python `eval()` con whitelist de caracteres seguros
5. **Identidad de Genesis**: `identity_keywords` → versión, provider, modelo real
6. **Conteo archivos / Tamaño carpeta**: `count_keywords`, `size_keywords` → `os.walk()` real

#### Bug Fixes
- **Windows 11 como Windows 10**: `platform.version()` devuelve `10.0.26200` — build ≥ 22000 = Windows 11. Fix en SystemInfoTool con PowerShell
- **Close app double .exe**: `proc_map` tiene `"EXCEL.EXE"` y código añadía `.exe` otra vez → `"EXCEL.EXE.exe"`. Fix: check `endswith(".exe")`
- **Multi-target close**: "cierra excel y word" parseado como un solo target. Fix: split en `" y "` para multi-target
- **Unicode en genesis_desktop.py**: Box-drawing chars (╔═╗║╚) crasheaban con `charmap`. Fix: ASCII + `sys.stdout.reconfigure()`
- **Close app verbose output**: taskkill mostraba cada PID. Fix: condensar a "Programa cerrado"
- **Anti-hallucination false positive**: "windows 11 pro" estaba en fabrication indicators pero el usuario SÍ tiene Windows 11 Pro
- **40% hallucination rate**: Auditoría encontró 6 auto-detect faltantes → añadidos todos → 15/15 tests, 0% hallucination

- **113 core modules, 36 test files, 241 tests (suite v5.4)**
- **Total: ~4,993 tests, 36 suites, 113 archivos, ~80,000+ líneas**

---

### v5.5.0 — Smart Productivity (2026-03-15)
**Hito:** Genesis se convierte en asistente de productividad con notas rápidas, recordatorios con notificación, diagnóstico de red, y acciones del sistema.

#### Nuevos Módulos
- **QuickNotes** (`core/quick_notes.py`): Sistema de notas rápidas persistentes
  - Crear notas con tags (#trabajo, #personal)
  - Listar, buscar, eliminar, fijar/desfijar notas
  - Persistencia JSON, filtrado por tags
- **ReminderSystem** (`core/reminder_system.py`): Temporizadores con notificación desktop
  - Parser de tiempo en español ("5 minutos", "2h30m", "media hora")
  - Notificación via plyer → win10toast → PowerShell toast → stdout
  - Background threads con daemon timers, cancelación individual
  - Historial de recordatorios, lista de activos
- **NetworkTools** (`core/network_tools.py`): Diagnóstico de red
  - Check conectividad (DNS + HTTP + HTTPS con latencia)
  - Info WiFi (SSID, señal, velocidad, canal, seguridad)
  - Ping con estadísticas, speed test rápido via Cloudflare
  - Adaptadores de red
- **SystemActions** (`core/system_actions.py`): Acciones rápidas del sistema
  - Limpieza de temporales con reporte de MB liberados
  - Flush DNS, vaciar papelera
  - Uptime, estado de batería
  - Bloquear pantalla, abrir configuración de Windows (16 secciones)
  - Contar apps instaladas

#### Nuevas Auto-Detecciones (12 secciones, bypass LLM)
1. Notas: "nota: ...", "mis notas", "busca en notas", "elimina nota N"
2. Recordatorios: "recuerdame en X que...", "mis recordatorios", "cancela recordatorio N"
3. Conectividad: "estoy conectado", "hay internet", "estado de red"
4. WiFi: "info wifi", "señal wifi", "a que wifi estoy conectado"
5. Ping: "haz ping a X"
6. Velocidad: "velocidad de internet", "speed test"
7. Limpieza: "limpiar temp", "flush dns"
8. Uptime: "hace cuanto esta encendido"
9. Batería: "bateria", "nivel de bateria"
10. Bloquear: "bloquea pantalla"
11. Configuración: "abre configuracion de [wifi/bluetooth/sonido/...]"
12. Apps instaladas: "cuantas apps instaladas"

- **116 core modules, 37 test files, 45 tests (suite v5.5)**
- **Total: ~5,038 tests, 37 suites, 116 archivos, ~82,000+ líneas**

---

### v5.6.0 — Smart Utilities (2026-03-15)
**Tema:** Herramientas de productividad diaria tipo asistente JARVIS.

**Nuevos módulos (4):**
- `core/clipboard_manager.py` (~190 líneas) — Historial de portapapeles con búsqueda, pin, monitoreo background. Usa `RLock` para thread safety (evitar deadlock en pin→save).
- `core/text_transformer.py` (~200 líneas) — 23 transformaciones: case conversions (upper, lower, title, camel, snake, kebab), encoding (base64, URL, hex), hashing (MD5, SHA1, SHA256), estadísticas (chars, words, lines, read time), extracción (emails, URLs, números), JSON formatter, sort, dedup, reverse.
- `core/unit_converter.py` (~220 líneas) — 7 categorías de conversión (distancia, peso, datos, tiempo, volumen, velocidad, temperatura). Parser de lenguaje natural: "10 km a millas", "cuántos metros son 5 pies", "30°C a fahrenheit". Tablas normalizadas a unidad base.
- `core/pomodoro.py` (~250 líneas) — Timer Pomodoro con state machine (idle→working→break→working→...). 25min trabajo / 5min descanso / 15min largo cada 4. Pausa, resume, skip, configure, historial, notificaciones desktop.

**Nuevos auto-detect blocks (28):**
1-6. Clipboard: ver actual, historial, buscar, monitorear, detener, limpiar
7-18. Text: mayúsculas, minúsculas, título, contar palabras, base64 enc/dec, hash, emails, URLs, números, JSON, ordenar, duplicados, invertir
19-20. Units: convertir (NLP), listar categorías
21-28. Pomodoro: iniciar, pausar, reanudar, detener, saltar, status, historial, configurar

**Bugs encontrados y corregidos:**
- **Deadlock en ClipboardManager**: `pin()` adquiría `Lock()` y llamaba `save()` que también adquiría `Lock()`. Fix: `threading.RLock()` (reentrant lock).
- **Base64 decode vacío**: `"!!!"` es base64 válido que decodifica a string vacío. Fix: validar que el resultado no sea vacío.

- **120 core modules, 39 test files, 92 tests (suite v5.6)**
- **Total: ~5,130 tests, 39 suites, 120 archivos, ~84,000+ líneas**

---

### v5.7.0 — JARVIS Intelligence (2026-03-15)
**Tema:** Comportamiento proactivo de asistente inteligente. GENESIS deja de ser reactivo y pasa a ser un co-piloto del sistema.

**Nuevos módulos (4):**
- `core/window_manager.py` (~270 líneas) — Control de ventanas via Win32 API (user32.dll). Snap left/right/top/bottom, maximize, minimize, minimize all, restore, focus, tile two windows, close, screen info. Parser de lenguaje natural para comandos de ventana.
- `core/smart_launcher.py` (~220 líneas) — Búsqueda unificada con fuzzy matching (SequenceMatcher) en 6 fuentes: apps instaladas, archivos recientes, desktop, notas, clipboard, procesos activos. Score 0-1 con ranking visual.
- `core/daily_briefing.py` (~180 líneas) — Briefing contextual: saludo por hora, sistema (CPU/RAM/uptime/disco), notas pendientes, recordatorios activos, pomodoro, cita motivacional random. Se activa con "buenos días" o "briefing".
- `core/macro_system.py` (~260 líneas) — Macros nombradas que ejecutan secuencias de comandos auto-detect. Parser NLP: "macro trabajo: abre Chrome, abre VS Code, inicia pomodoro". Persistencia JSON, fuzzy name matching, historial de ejecuciones.

**Nuevos auto-detect blocks (20):**
1-12. Windows: snap left/right, maximize, minimize, minimize all, restore, focus, list, screen info, tile, close
13-14. Launcher: search unified, launch best
15. Briefing: buenos días, resumen del día, estado general
16-20. Macros: create, execute, list, delete, show, history

**Highlights técnicos:**
- **Win32 API sin pywin32**: Usa `Add-Type` de PowerShell + `DllImport` para cargar `user32.dll` directamente. Cero dependencias externas.
- **Fuzzy matching stdlib**: `difflib.SequenceMatcher` + boosting por iniciales y posición.
- **Macro executor pattern**: `set_executor(callback)` permite que genesis.py inyecte `_auto_detect_tool()` sin acoplamiento.

- **124 core modules, 40 test files, 67 tests (suite v5.7)**
- **Total: ~5,197 tests, 40 suites, 124 archivos, ~86,000+ líneas**

---

### v5.8.0 — Autonomous Orchestration (2026-03-15)

**Tema: GENESIS se vuelve proactivo — vigila, programa, trackea y aprende.**

**Nuevos módulos (4):**

1. **`core/file_watcher.py` — FileWatcher**
   - Monitor de directorios con reglas configurables (patrón glob + acción)
   - Acciones: move, copy, notify, execute
   - Background daemon thread con scan cada 3 segundos
   - Snapshot inicial para no disparar en archivos existentes
   - Log de eventos, persistencia JSON, enable/disable por regla

2. **`core/smart_scheduler.py` — SmartScheduler**
   - Scheduler tipo cron con parsing NLP en español e inglés
   - Tipos: intervalo ("cada 30 minutos"), diario ("daily 09:00"), semanal ("cada lunes a las 10")
   - Patrón tick() cooperativo — se llama desde el loop principal
   - Executor callback pattern (mismo que MacroSystem)
   - Historial de ejecuciones, enable/disable por tarea

3. **`core/habit_tracker.py` — HabitTracker**
   - Hábitos diarios/semanales con tracking de completaciones
   - Cálculo de streaks (racha actual + mejor histórica)
   - Vista de hoy, estadísticas por hábito, tasa de completación 30 días
   - Mensajes motivacionales adaptativos según racha (3d, 7d, 14d, 30d)
   - Integración con DailyBriefing (get_summary → sección PRODUCTIVIDAD)
   - Prevención de doble-completación, fuzzy matching en nombres

4. **`core/context_engine.py` — ContextEngine**
   - Registra interacciones (tipo, hora, query) con max 500 historial
   - Top commands: frecuencia con barras visuales
   - Time report: heatmap textual por hora del día, detección de hora pico
   - Day report: uso por día de la semana
   - Sugerencias proactivas: si a las 9:00 siempre pedís briefing → te lo sugiere
   - Full report: análisis completo combinando todo

**Integración en genesis.py (20 nuevos auto-detect blocks):**
- FileWatcher: vigilar carpeta, listar/agregar reglas, start/stop monitoreo, eventos
- SmartScheduler: programar tarea, listar tareas, historial
- HabitTracker: crear/completar/listar/eliminar hábito, hábitos de hoy, estadísticas, rachas
- ContextEngine: top comandos, patrones de uso, sugerencias, borrar datos

**Patrones técnicos:**
- **fnmatch para file matching**: stdlib, sin dependencias — `fnmatch.fnmatch(filename, "*.pdf")`
- **Cooperative tick()**: SmartScheduler no usa threads — se llama desde el loop principal
- **Streak calculation**: Cuenta días consecutivos desde hoy/ayer hacia atrás, maneja gaps
- **Proactive suggestions**: Solo sugiere si el patrón es fuerte (>40% de interacciones a esa hora)

- **128 core modules, 41 test files, 123 tests (suite v5.8)**
- **Total: ~5,320 tests, 41 suites, 128 archivos, ~90,000+ líneas**

---

### v5.9.0 — System Mastery (2026-03-15)

**Tema: GENESIS domina tu entorno — genera proyectos, gestiona snippets, aplica templates, audita el sistema.**

**Nuevos módulos (4):**

1. **`core/project_scaffolder.py` — ProjectScaffolder**
   - 6 templates: Python (basic), Flask (MVC), FastAPI (REST), Node (Express), React (Vite), HTML (estática)
   - Cada template genera estructura completa: main, config, README, .gitignore, tests
   - Variables dinámicas: {name}, {name_slug}, {description}
   - Historial de proyectos generados
   - Bug fix: CSS braces `{}` deben escaparse como `{{}}` para `.format()`

2. **`core/code_snippets.py` — CodeSnippets**
   - Biblioteca personal de fragmentos de código
   - Tags, lenguaje, fuzzy search (nombre + tag + contenido + lenguaje)
   - Agrupación por lenguaje, contador de usos
   - Persistencia JSON, export ready

3. **`core/template_engine.py` — TemplateEngine**
   - 5 templates predefinidos: email_formal, email_seguimiento, bug_report, acta_reunion, changelog
   - Templates custom con extracción automática de variables `{var}`
   - Apply con valores parciales (variables no proporcionadas quedan como placeholder)
   - Auto-fill `{fecha}` con la fecha actual
   - Protección contra eliminación de templates predefinidos

4. **`core/system_profiler.py` — SystemProfiler**
   - 7 reportes: software instalado, startup programs, env vars, disk usage, network connections, services, full report
   - Software vía Windows Registry (WOW6432Node + native)
   - Disk usage con barras visuales y estimación de primer nivel
   - Network connections vía Get-NetTCPConnection
   - Servicios con estado (running/stopped) y tipo de inicio

**Integración en genesis.py (~20 nuevos auto-detect blocks):**
- ProjectScaffolder: crear proyecto, templates disponibles, historial
- CodeSnippets: guardar, obtener, buscar, listar, eliminar snippet
- TemplateEngine: listar, preview, aplicar template
- SystemProfiler: software, startup, env vars, disco, red, servicios, reporte completo

- **132 core modules, 42 test files, 105 tests (suite v5.9)**
- **Total: ~5,425 tests, 42 suites, 132 archivos, ~95,000+ líneas**

---

### v6.0.0 — Digital Sovereignty (2026-04-17)

**Tema: GENESIS libera su cerebro — corre 100% local por defecto sin dependencia de APIs externas.**

**Contexto estratégico**: el usuario está financiando hardware superior (meta RTX 4060 Ti 16GB)
vía bots de trading (Forex +200% en 3 días con $50 → $150). La migración a soberanía digital
es progresiva: Phase 0 crea la abstracción, Phase 1 activa multi-modelo local, Phases 2-4
agregan RAG semántico, auto-evolución activa y fine-tuning LoRA nocturno.

**Phase 0 — Multi-Provider Routing**:

1. **`core/provider_router.py` (NUEVO, ~420 líneas)**
   - **`_CircuitBreaker`**: marca provider DOWN tras N fallos consecutivos (default 3),
     cooldown configurable (default 5 min), auto-recuperación con request de prueba.
     - `is_up(provider)`, `record_success()`, `record_failure()`, `status()`
   - **`_TaskClassifier`**: heurística keyword+length sin LLM (no recursivo).
     - Clasifica en `'simple'` | `'coding'` | `'reasoning'`
     - `_CODING_KW`: python, javascript, codigo, funcion, bug, script, regex...
     - `_REASONING_KW`: analiza, evalua, compara, estrategia, arquitectura...
     - Textos >3000 chars → `'reasoning'` automático
   - **`ProviderRouter`**: facade con contrato compatible con `Brain`.
     - `STRATEGIES`: `local_first` (default), `quality_first`, `cost_first`, `speed_first`
     - `think()`: failover automático por el orden de la estrategia, respetando circuit breaker
     - `from_config()`: factory que lee `config.py`, solo incluye providers con API key / con Ollama up
     - Pass-through props: `provider`, `model`, `total_tokens_used` → drop-in para Brain

2. **`config.py` (extendido)**:
   - `LLM_STRATEGY = os.getenv("GENESIS_LLM_STRATEGY", "local_first")`
   - `LLM_TASK_CLASSIFIER = os.getenv("GENESIS_LLM_CLASSIFIER", "true").lower() == "true"`
   - Backwards compatible: `LLM_PROVIDER` sigue existiendo para single-provider legacy

3. **`genesis.py` (modificado)**:
   - `self.brain = ProviderRouter.from_config()` con fallback grácil al Brain legacy
   - Imprime providers configurados y estrategia al arrancar

**Phase 1 — Multi-Model Ollama**:

1. **`config.py` (extendido)**:
   ```python
   OLLAMA_MODEL_BY_TASK = {
       "coding":    "qwen2.5-coder:7b",  # especializado en código
       "reasoning": "genesis",            # Llama 3.1 custom sin restricciones
       "default":   "genesis",
   }
   ```
   Sobreescribible vía env vars `GENESIS_OLLAMA_CODING`, `GENESIS_OLLAMA_REASONING`,
   `GENESIS_OLLAMA_DEFAULT`.

2. **`core/provider_router.py` (extendido)**:
   - `_get_brain_for(provider, task_type)`: elige Brain según tipo de tarea.
     - Para Ollama: resuelve modelo y cachea instancia por **nombre de modelo** (no por task).
     - Fallback en cascada: task_type específico → "default" → modelo del Brain base
   - `think()` usa `_get_brain_for()` en vez de `self.brains[provider]` directo
   - Nueva telemetría: `calls_by_model`, `last_model_used`, `ollama_models_cached`

3. **Modelos Ollama instalados**:
   - `genesis:latest` (Llama 3.1 8B custom Q4_K_M, 4.58GB) — conversación general
   - `qwen2.5-coder:7b` (Q4_K_M, 4.36GB) — especializado en código
   - Total en disco: ~13.5GB

**Tests**:
- `tests/test_provider_router.py` (NUEVO, ~300 líneas):
  - 48 tests, 48 passed, 0 failed
  - 5 secciones: CircuitBreaker, TaskClassifier, failover automático, estrategias, multi-model
  - Usa `FakeBrain` stub (sin HTTP real)
- `tests/test_qwen_e2e.py` (NUEVO, ~100 líneas):
  - Integración real con Ollama: valida que coding prompt → Qwen, general → Genesis
  - Resultado PASS: `qwen2.5-coder:7b` 17.7s (carga fría), `genesis` 10.3s

**VRAM** (RTX 3060 Ti 8GB):
- Genesis (4.58GB) + Qwen Coder (4.36GB) = 8.94GB → no caben simultáneos
- Ollama hace unload/reload (~2-3s overhead en switches)
- Con 4060 Ti 16GB coexistirían calientes

**Resultado**: Genesis corre 100% local sin necesidad de GOOGLE_API_KEY/OPENAI_API_KEY/
ANTHROPIC_API_KEY. Single point of failure: que Ollama esté corriendo. Recomendación:
configurar Gemini como backup silencioso (gratis 15 RPM).

**Archivos nuevos/modificados**:
- NUEVO: `core/provider_router.py` (~420 líneas)
- NUEVO: `tests/test_provider_router.py` (~300 líneas)
- NUEVO: `tests/test_qwen_e2e.py` (~100 líneas)
- MODIFICADO: `config.py` (+~20 líneas)
- MODIFICADO: `genesis.py` (+~20 líneas en `__init__`)

- **133 core modules, 44 test files, ~5,473 tests totales**
- **Total: ~5,473 tests, 44 suites, 133 archivos, ~96,000+ líneas**

---

### v6.1.0 — Senses & Studio (2026-06-13)

**Tema: GENESIS gana sentidos creativos locales (imagen + voz clonada) y una cabina
rediseñada — todo offline, en la GPU del usuario.**

**Contexto**: tras v6.0 (soberanía del cerebro), esta fase suma **medios generativos
locales** y control de dispositivos/UX, manteniendo la regla de 8GB VRAM como restricción
de diseño central.

**Generación de imágenes (Stable Diffusion local)**:
- Pollinations.ai (gratis) pasó a pago (HTTP 402) → migración a **SD local**.
- `core/media_generator._try_local_sd`: pipeline **sd-turbo** (diffusers, fp16, CUDA,
  attention_slicing), cacheado en VRAM. Prioridad sobre Pollinations; placeholder solo como
  último recurso.
- torch reinstalado a **2.5.1+cu121** (venía +cpu). 1ª imagen ~20s (carga), **warm ~0.6s**.

**Voz clonada local (XTTS-v2)**:
- `core/voice_clone.py`: clonación con **coqui-tts** (XTTS-v2) en GPU. `clone_say` (defaults)
  y `clone_say_hq` (API bajo nivel: `gpt_cond_len=30` + `temperature` ajustable).
- Shim `_patch_transformers()` resuelve incompatibilidad `isin_mps_friendly` (transformers 5.x)
  sin downgradear.
- Voz **JARVIS/Milton** clonada desde muestra limpia (editada por el usuario en Audacity).
  Wired a `/api/tts/speak` con `voice="clon:milton"` + fallback a `es-ES-AlvaroNeural`.
- **Demucs** instalado para aislar voz de música/efectos en muestras.

**Cabina rediseñada (hub `/core`)**:
- Layout "JARVIS MARK 5" centrado: núcleo de plasma reactivo, **dock de 6 botones**
  (BUSCAR/WEBS/MÚSICA/CREAR/VER/NÚCLEO) con modales, tablero de evidencias flotante,
  barra de stats GPU/CPU. Todo desbloqueado (sin gating PRO).

**Control de dispositivos / medios**:
- `core/system_control.py` (volumen, brillo, energía, impresión, multi-monitor),
  `core/connections.py` (WiFi/BT/USB), `core/casting.py` (Chromecast/YouTube),
  `core/netflix.py` (app Store: abrir/reproducir/castear, unificado en una sola app),
  `core/email_sender.py` + `core/email_reader.py` (Gmail), despertador con voz + música,
  `core/folder_index.py` + `core/program_index.py` (abrir apps/carpetas por nombre).

**Robustez**:
- Fix parpadeo `nvidia-smi` (`CREATE_NO_WINDOW`) y cabina duplicada (matar TODAS las
  instancias antes de relanzar).
- Regex de intención tolerante a voseo/typos (stems `repro\w*`, `caste\w*`).

**VRAM (RTX 3060 Ti 8GB) — restricción central**:
- Ollama (6.2GB) + XTTS (2GB) NO coexisten → la voz clonada cae a CPU (~8s/frase) o se
  evalúa orquestación de carga/descarga. *(Decisión de UX pendiente.)*

**Archivos nuevos**: `core/{casting,connections,netflix,voice_clone,system_control,`
`folder_index,program_index,email_sender,email_reader,jarvis_routines,music_player,`
`ui_automation,builder_engine}.py`, `ROADMAP.md`, `SETUP.md`,
`tests/test_v3_0_capabilities.py`.

**Resultado**: GENESIS ve (analiza imágenes), **crea** (imágenes SD) y **habla con voz
clonada** — 100% local. Próximo foco: orquestador de VRAM y capa de tools (N4).

---

### v6.1.1 — más sentidos + cabina + fixes (2026-06-14/15)

**Tema: GENESIS suma un sentido nuevo (la cámara del celular), pule la cabina y la voz,
y se le arreglan bugs reales de Netflix y de mover ventanas.**

**Cámara del celular (nuevo sentido, `core/mobile_cam.py`)**: el celular transmite su
cámara a GENESIS por la **red local**, sin instalar app. Server HTTPS propio (puerto 5443,
cert autofirmado generado con `cryptography`), página `/movil` (getUserMedia) que sube
frames JPEG; emparejamiento por **QR** desde la cabina. Comandos: «conectá la cámara del
celular», «qué ve la cámara del celular» (llava), sacar foto, y **modo monitoreo**
(auto-análisis periódico). HTTPS es obligatorio porque getUserMedia solo va en contexto seguro.

**Visión de pantalla afinada (`core/image_analyzer.py`)**: llava:latest se **negaba** a
describir capturas con un `system` prompt largo → se quita el system (idioma va en el prompt) +
temp 0.2; la respuesta combina la descripción de llava con los **títulos reales de ventana**.

**Cabina (`web_ui.py`)**: núcleo de plasma **seleccionable** (Superficie/Combo/Onda/Anillo3D/
Aurora) con selector en vivo + **color de usuario** (degradado centro→borde); **estaciones de
agentes** tipo oficina en Mission Control; TTS que ya no pronuncia emojis.

**Voz**: manos-libres con **match difuso** de wake-word (nombres que vosk transcribe mal:
lexus→lexis/nexus); **voiceprint** enroll de 60s + texto fonético; **comandos personalizados**
(`core/user_commands.py`: «cuando diga X → hacé Y»).

**Netflix (fixes reales, `core/netflix.py`)**: (1) reproducía el título **equivocado** —
`_FIND_PLAY` agarraba el botón del **billboard** (hero promocionado) → ahora lo excluye y usa
el `detailsPagePlayButton` del título correcto; (2) declaraba falso «reproduciendo» → ahora
**verifica el `<video>` runtime**; (3) «movela a la otra pantalla» **reabría** en vez de mover →
fix de regex (stems) + mover la ventana existente por CDP.

**Mover ventanas instantáneo (`core/window_manager.py`)**: `move_to_screen` lanzaba
PowerShell+`Add-Type` (recompila C# ~2-4s) → parecía que «no se movía». Reescrito a **`ctypes`
in-process** → instantáneo.

**Commits**: 9 temáticos (`git log`): netflix x2, window-manager, cabina, voz, agentes,
mobile-cam, tools, vision. Bugs detallados en `ERRORS_AND_SOLUTIONS.md` (ERR-2026-06-15a/b/c).

---

### v7.0.0 — Unbound (Mente Orquestada) 🔜 EN DESARROLLO

**Tema: GENESIS rompe sus límites — usa todos sus recursos sin pelear por ellos, suma
sentidos en tiempo real, actúa con autonomía y se controla desde cualquier lado.**

**Contexto**: v6.1 sumó sentidos (imagen SD + voz clonada) pero chocaron con el techo de
**8GB VRAM**. v7.0 ataca eso de raíz y construye sobre la capacidad liberada. 4 tracks
ordenados — **Track 1 es la base que desbloquea el resto**.

#### 🎛️ Track 1 — Conductor (orquestación de recursos + plataforma de tools) — *base, primero*
- **`core/vram_manager.py` (NUEVO)**: orquestador de VRAM. Carga/descarga LLM (Ollama),
  SD y XTTS según la tarea, con prioridades, políticas anti-OOM y telemetría en vivo.
  → desbloquea **voz + imagen + LLM** funcionando juntos sin colgarse.
- **Voz clonada integrada al orquestador**: XTTS en GPU cuando hay espacio; fallback
  automático a CPU (~8s) o a voz Álvaro (edge-tts) — resuelve el pendiente de v6.1.
- **N4 — Capa de function-calling**: migración *aditiva* del dispatcher por regex a tools
  declarativas (registro, esquema, validación). Base para escalar capacidades sin regex frágiles.

#### 👁️ Track 2 — Sentidos en tiempo real
- **Visión continua**: cámara/pantalla en streaming → Genesis describe y reacciona (llava +
  análisis periódico). Hoy la visión es puntual; pasa a ser continua.
- **Imágenes en el hub**: mostrar la imagen generada *inline* (hoy devuelve la ruta).
- Más integraciones de apps + automatización de UI más profunda.

#### 🤖 Track 3 — Autonomía (agente)
- **Agente multi-paso**: planifica → ejecuta cadenas de tools (sobre Track 1) → verifica.
- Scheduling avanzado, proactividad fuerte, **alarmas/recordatorios persistentes** entre reinicios.

#### 📱 Track 4 — Alcance (remoto / móvil)
- **API segura** + control desde el celular (web responsive / app liviana), notificaciones push,
  sincronización de estado. Genesis accesible fuera de la PC.

**Orden de ejecución**: Track 1 (desbloquea) → Tracks 2 y 3 en paralelo → Track 4 al final.
**Restricción central**: respetar siempre los principios de escalado (local-first, guardrails de
auto-modificación, degradación grácil, audit-first). El techo de 8GB VRAM guía todo el diseño
de Track 1 hasta migrar a más VRAM.

---

## Resumen del Roadmap

| Version | Tema | Modulos | Tests |
|---------|------|---------|-------|
| v3.0 ✅ | Unified Consciousness | 58 | 4,023 |
| v3.1 ✅ | Social Intelligence | 61 | 4,337 |
| v3.2 ✅ | Creative Genesis | 64 | 4,337 |
| v3.3 ✅ | Sensory Expansion | 67 | 4,337 |
| v3.4 ✅ | Collaborative Mind | 70 | 4,388 |
| v3.5 ✅ | Autonomous Research | 73 | 4,440 |
| v4.0 ✅ | Autonomous Evolution | 76 | 4,492 |
| v4.1 ✅ | Temporal Intelligence | 79 | 4,544 |
| v4.2 ✅ | Ethical Framework | 82 | 4,596 |
| v4.3 ✅ | Knowledge Mastery | 85 | 4,648 |
| v4.4 ✅ | Distributed Genesis | 88 | 4,700 |
| v5.0 ✅ | Singularity | 91 | 4,752 |
| v5.1 ✅ | Device Control & Anti-Hallucination | 92 | 4,752 |
| v5.4 ✅ | JARVIS — Gemini + Desktop App | 113 | 4,993 |
| v5.5 ✅ | Smart Productivity | 116 | 5,038 |
| v5.6 ✅ | Smart Utilities | 120 | 5,130 |
| v5.7 ✅ | JARVIS Intelligence | 124 | 5,197 |
| v5.8 ✅ | Autonomous Orchestration | 128 | 5,320 |
| v5.9 ✅ | System Mastery | 132 | 5,425 |
| v6.0 ✅ | Digital Sovereignty | 133 | 5,473 |
| **v6.1** ✅ | **Senses & Studio (imagen SD + voz clonada + hub)** | **~146** | **5,473+** |
| **v7.0** 🔜 | **Unbound — orquestación VRAM + tools + sentidos RT + autonomía + remoto** | *en desarrollo* | — |

**GENESIS v6.0 COMPLETADO.** 133 módulos, 125+ auto-detect sections, **router multi-provider
con failover**, 2 modelos Ollama en producción (Genesis + Qwen Coder), desktop app, project
scaffolder, snippets, templates, system profiler — ~96,000+ líneas de código.
**Corre 100% local sin dependencia de APIs externas.**

---

## Decisiones Técnicas Clave

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| ctransformers sobre llama-cpp-python | llama-cpp-python | Mejor soporte CUDA directo en el momento de inicio |
| Flask sobre FastAPI | FastAPI | Más ligero, sin necesidad de async para SSE simple |
| JSON files sobre SQLite | SQLite | Simplicidad para datos pequeños, sin ORM |
| TF-IDF propio sobre sklearn | sklearn | Cero dependencias adicionales para búsqueda |
| Unittest sobre pytest | unittest incluido | pytest más expresivo, mejor output |
| **Ollama sobre llama-cpp-python directo** (v6.0) | llama-cpp-python directo | Ollama gestiona unload/reload de modelos, HTTP API estable, multi-modelo en paralelo |
| **ProviderRouter como Facade sobre Brain** (v6.0) | Refactor de Brain | Zero breaking changes — `self.brain` sigue siendo drop-in replaceable |
| **Multi-model Ollama por task_type** (v6.0) | Un solo modelo Ollama | Qwen Coder 7B es ~15% mejor en código que Llama 3.1 8B general (según benchmarks HumanEval+); separar tareas aprovecha especialización |
| **Circuit Breaker en vez de retry con backoff** (v6.0) | Retry simple | Con múltiples providers, el failover es más rápido que reintentar el caído — el circuit breaker evita gastar latencia en providers conocidos down |
| **Task Classifier heurístico sin LLM** (v6.0) | LLM pequeño (BERT-tiny) | Para MVP, keywords son suficientes y cero dependencias. Phase futura: fine-tunear BERT-tiny sobre conversaciones reales |
