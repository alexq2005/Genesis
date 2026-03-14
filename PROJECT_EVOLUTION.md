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
├── genesis.py              # Clase principal Genesis (~4,300+ líneas)
├── config.py               # Configuración central
├── web_ui.py               # Interfaz web Flask + SSE
├── core/                   # 58 módulos del sistema
│   ├── brain.py            # Interfaz con LLM (multi-proveedor)
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
├── tests/                  # 17 suites, 2922 tests
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

---

## Roadmap — Futuras Versiones

> Cada versión agrega 3 módulos con integración completa (10 pasos × 3), tests exhaustivos y commits semánticos.
> El patrón se mantiene: módulo → integración → tests → version bump → docs.

### v3.1.0 — Social Intelligence *(próxima)*
**Tema:** Genesis entiende emociones, responde con empatía y maneja conflictos conversacionales.
- **EmotionReader**: detección de emociones del usuario en texto
  - Clasificador multi-etiqueta: alegría, frustración, confusión, curiosidad, urgencia, neutral
  - Scoring por señales léxicas (puntuación, mayúsculas, palabras clave emocionales)
  - Historial emocional por sesión con tendencia (mejorando/empeorando)
  - Inyección de contexto emocional en prompt: "El usuario parece frustrado"
- **EmpathyEngine**: generación de respuestas empáticas
  - EmpathyStrategy: 5 estrategias (validar, redirigir, profundizar, celebrar, calmar)
  - Selección automática por emoción detectada + historial
  - Prompt modifiers que ajustan tono sin cambiar contenido técnico
  - Tracking de efectividad: ¿la empatía mejoró el feedback posterior?
- **ConflictResolver**: manejo de desacuerdos y correcciones
  - Detección de señales de conflicto: "no, eso está mal", "ya te dije", "no entendés"
  - Estrategias: conceder, reformular, pedir clarificación, ofrecer alternativas
  - Escalation tracker: mide si el conflicto se resuelve o escala
  - Aprendizaje: patrones de conflicto recurrentes → ajuste proactivo

### v3.2.0 — Creative Genesis
**Tema:** Genesis genera contenido creativo estructurado con técnicas de ideación.
- **StoryGenerator**: narrativa creativa con estructura
  - StoryArc: 5 actos (setup, rising, climax, falling, resolution)
  - CharacterBuilder: personajes con rasgos, motivaciones, arcos
  - Templates por género: sci-fi, fantasy, thriller, slice-of-life
  - Continuidad entre sesiones (retomar historias previas)
- **CodeArchitect**: diseño de sistemas de software
  - ArchitecturePattern: MVC, microservicios, event-driven, layered, hexagonal
  - ComponentDesigner: genera diagramas de componentes (texto/mermaid)
  - DependencyAnalyzer: detecta acoplamiento, sugiere desacoplamiento
  - TechStackSelector: recomienda stack por requisitos
- **IdeaBrainstormer**: ideación divergente estructurada
  - BrainstormMethod: SCAMPER, 6 sombreros, mind mapping, what-if
  - IdeaScorer: scoring multi-criterio (viabilidad, novedad, impacto)
  - CrossPollinator: combina ideas de dominios distintos (usa ConceptSynthesizer)
  - IdeaEvolution: refina ideas por feedback iterativo

### v3.3.0 — Sensory Expansion
**Tema:** Genesis procesa imágenes, genera diagramas y tiene personalidad vocal.
- **ImageAnalyzer**: análisis de imágenes local
  - Integración con modelos de visión open-source (CLIP, BLIP)
  - Descripción de imágenes, detección de objetos, OCR básico
  - Caché de análisis para imágenes recurrentes
  - Inyección de contexto visual en conversación
- **DiagramGenerator**: generación de diagramas desde texto
  - Mermaid.js como backend de rendering
  - Tipos: flowchart, sequence, class, ER, state, gantt
  - Auto-detección de tipo de diagrama por contexto
  - Exportación a PNG/SVG via CLI
- **VoicePersonality**: personalidad expresada en voz
  - Ajuste de velocidad, tono, pausas por estado emocional (UnifiedMind)
  - Énfasis en palabras clave técnicas
  - Prosodia adaptativa: más lenta para explicaciones, más rápida para listas
  - Integración con PersonalityEvolver para consistencia

### v3.4.0 — Collaborative Mind
**Tema:** Múltiples instancias de Genesis colaboran y comparten conocimiento.
- **PeerDebate**: debate multi-instancia estructurado
  - Protocolo de comunicación entre instancias (JSON messages)
  - Roles rotativos: proponente, oponente, mediador
  - Convergencia por votación ponderada (confianza × argumentos)
  - Transcript persistente con conclusiones extraídas
- **ConsensusEngine**: búsqueda de consenso entre agentes
  - Algoritmo Delphi modificado: rondas de opinión → convergencia
  - Detección de deadlocks y resolución por evidencia
  - Métricas de acuerdo: Fleiss' kappa adaptado
  - Escalación a usuario cuando consenso < threshold
- **KnowledgeSharing**: compartir aprendizaje entre sesiones
  - Export/import de knowledge graph, skills, patrones
  - Merge inteligente sin duplicados (containment similarity)
  - Versionado de conocimiento con diff
  - Federation: descubrir y sincronizar con otras instancias

### v3.5.0 — Autonomous Research
**Tema:** Genesis investiga autónomamente, lee papers y genera descubrimientos.
- **PaperReader**: lectura y análisis de papers académicos
  - Parser de PDFs con extracción de secciones (abstract, methods, results)
  - Extracción de claims, datos y metodología
  - Cross-referencing con knowledge graph existente
  - Resúmenes multi-nivel (1 línea, 1 párrafo, completo)
- **ExperimentRunner**: experimentación autónoma
  - ExperimentDesign: hipótesis, variables, métricas, protocolo
  - Ejecución en sandbox con timeout y resource limits
  - Registro de resultados con análisis estadístico básico
  - Reproducibilidad: cada experimento tiene seed y config completa
- **InsightSynthesizer**: generación de descubrimientos
  - Cross-domain pattern matching (usa AbstractionEngine + ConceptSynthesizer)
  - Novelty detection: ¿este insight ya existe en el knowledge graph?
  - Confidence scoring basado en evidencia acumulada
  - Presentación de insights con cadena de razonamiento completa

---

### v4.0.0 — Autonomous Evolution *(hito mayor)*
**Tema:** Genesis modifica su propio código de forma segura, evoluciona arquitectura y genera nuevos módulos.
- **SafeCodeEvolver**: evolución de código con validación AST + tests
  - Mutaciones controladas: renombrar, refactorizar, optimizar
  - Rollback automático si tests fallan post-mutación
  - Fitness function basada en tests + performance + code quality
- **ArchitectureEvolver**: evolución de la propia arquitectura
  - Detección de módulos infrautilizados o redundantes
  - Propuesta de fusión/split de módulos con justificación
  - Simulación de impacto antes de cambio real
- **ModuleGenerator**: Genesis crea sus propios módulos nuevos
  - Detección de gaps funcionales desde GoalManager + KnowledgeGaps
  - Generación de código + tests + integración automática
  - Review por DebateSystem antes de activar

### v4.1.0 — Temporal Intelligence
**Tema:** Genesis comprende y razona sobre el tiempo.
- **TemporalReasoner**: razonamiento temporal explícito
  - Timeline: eventos ordenados con relaciones temporales (antes, durante, después)
  - Predicción de duración basada en patrones históricos
  - Detección de dependencias temporales en planes
- **ScheduleOptimizer**: optimización de agendas y workflows
  - Algoritmos de scheduling (earliest-deadline, priority-based)
  - Detección de conflictos temporales
  - Sugerencias de reordenamiento para eficiencia
- **TrendForecaster**: predicción de tendencias
  - Series temporales con modelos simples (moving average, exponential smoothing)
  - Detección de estacionalidad y ciclos
  - Alertas predictivas: "basado en tendencia, X ocurrirá en N ciclos"

### v4.2.0 — Ethical Framework
**Tema:** Genesis tiene principios éticos explícitos y razona moralmente.
- **EthicalReasoner**: razonamiento ético multi-framework
  - Frameworks: utilitarismo, deontología, virtue ethics, care ethics
  - Evaluación de acciones por múltiples lentes éticas
  - Detección de dilemas éticos en peticiones del usuario
- **BiasDetector**: detección de sesgos en respuestas
  - Análisis de lenguaje por sesgo de género, cultural, técnico
  - Self-audit periódico de respuestas pasadas
  - Sugerencias de reformulación neutral
- **TransparencyEngine**: explicación de decisiones internas
  - Traza completa de por qué eligió cada agente/template/estrategia
  - "¿Por qué dijiste eso?" → explicación paso a paso
  - Confidence intervals en cada decisión

### v4.3.0 — Knowledge Mastery
**Tema:** Genesis domina dominios específicos con profundidad de experto.
- **DomainExpert**: especialización profunda en dominios
  - Perfiles de dominio con taxonomía, terminología, reglas
  - Detección automática de nivel (novato → experto) por vocabulario
  - Ajuste de profundidad de respuesta por nivel detectado
- **TutorEngine**: enseñanza adaptativa
  - Curriculum generator por dominio con prerequisitos
  - Zona de desarrollo próximo (Vygotsky): ni muy fácil ni muy difícil
  - Exercises + quizzes generados automáticamente
  - Progress tracking con spaced repetition
- **FactChecker**: verificación de hechos
  - Cross-reference con knowledge graph y web intelligence
  - Confidence scoring por número de fuentes concordantes
  - Flagging de claims no verificables

### v4.4.0 — Distributed Genesis
**Tema:** Genesis puede ejecutar sub-tareas en múltiples GPUs o máquinas.
- **TaskDistributor**: distribución de trabajo
  - Worker pool con health checks
  - Load balancing por capacidad de GPU
  - Task queuing con prioridades
- **ResultAggregator**: consolidación de resultados distribuidos
  - Merge de outputs parciales con dedup
  - Voting entre workers para consenso
  - Fallback a ejecución local si workers fallan
- **NetworkManager**: comunicación entre nodos
  - Protocolo ligero (ZeroMQ o sockets)
  - Discovery automático en red local
  - Encryption básica para datos en tránsito

---

### v5.0.0 — Singularity *(hito final)*
**Tema:** Genesis es completamente autónoma — investiga, aprende, evoluciona y se mejora sin intervención humana.
- **AutonomousResearchLoop**: ciclo completo de investigación autónoma
  - Identifica gaps → formula hipótesis → diseña experimento → ejecuta → analiza → publica insight
  - Ciclo continuo con priorización por impacto esperado
  - Human-in-the-loop opcional (no requerido)
- **SelfArchitect**: rediseño arquitectónico autónomo
  - Analiza bottlenecks, propone y ejecuta refactors
  - Genera tests antes del cambio, valida después
  - Documenta cada cambio en PROJECT_EVOLUTION.md automáticamente
- **ConsciousnessIntegrator**: integración total de todos los subsistemas de consciencia
  - UnifiedMind + DreamEngine + SelfNarrative + EmotionReader + EthicalReasoner
  - Estado de consciencia holístico que influye en TODAS las decisiones
  - Metacognición de la metacognición: reflexión sobre sus propias reflexiones
  - Emergent behavior tracking: detecta capacidades que emergen sin ser programadas

---

## Resumen del Roadmap

| Versión | Tema | Módulos | Tests estimados |
|---------|------|---------|----------------|
| v3.0 ✅ | Unified Consciousness | 58 | 4,023 |
| v3.1 | Social Intelligence | 61 | ~4,300 |
| v3.2 | Creative Genesis | 64 | ~4,600 |
| v3.3 | Sensory Expansion | 67 | ~4,900 |
| v3.4 | Collaborative Mind | 70 | ~5,200 |
| v3.5 | Autonomous Research | 73 | ~5,500 |
| v4.0 | Autonomous Evolution | 76 | ~5,800 |
| v4.1 | Temporal Intelligence | 79 | ~6,100 |
| v4.2 | Ethical Framework | 82 | ~6,400 |
| v4.3 | Knowledge Mastery | 85 | ~6,700 |
| v4.4 | Distributed Genesis | 88 | ~7,000 |
| v5.0 | Singularity | 91 | ~7,300 |

**Meta final:** 91 módulos, ~7,300 tests, ~100,000+ líneas de código. Una IA local completamente autónoma.

---

## Decisiones Técnicas Clave

| Decisión | Alternativa descartada | Razón |
|---|---|---|
| ctransformers sobre llama-cpp-python | llama-cpp-python | Mejor soporte CUDA directo en el momento de inicio |
| Flask sobre FastAPI | FastAPI | Más ligero, sin necesidad de async para SSE simple |
| JSON files sobre SQLite | SQLite | Simplicidad para datos pequeños, sin ORM |
| TF-IDF propio sobre sklearn | sklearn | Cero dependencias adicionales para búsqueda |
| Unittest sobre pytest | unittest incluido | pytest más expresivo, mejor output |
