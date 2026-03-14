# GENESIS v3.0 — Configuración para Claude Code

## Idioma
- **SIEMPRE responder en español.** Todo: explicaciones, insights, comentarios en código, mensajes de error, nombres de variables descriptivas — todo en español.

## Contexto del Proyecto
- GENESIS es un sistema de IA auto-evolutivo que corre 100% local
- Hardware: RTX 3060 Ti (8GB VRAM), 16GB RAM
- Modelo actual: Dolphin 2.8 Mistral 7B vía ctransformers con CUDA
- NO usar APIs externas (Groq, OpenAI, etc.) — todo debe ser local
- Python 3.10, Windows

## Arquitectura (v3.0 — 58 módulos, 4023 tests)

### Archivos principales
- `genesis.py` — Motor principal (~4,300 líneas), loop de interacción, integración de 58 módulos
- `config.py` — Configuración central (GENESIS_VERSION, LLM_PROVIDER, rutas)
- `web_ui.py` — Interfaz web Flask + SSE (~880 líneas)
- `Makefile` — Targets de tests por versión (test-v10 a test-v30)

### Core modules (core/) — 75 archivos, 58 módulos activos

#### Era 1: Foundations (v1.0-v1.4)
- `brain.py` — Cerebro (inferencia LLM local, multi-proveedor)
- `local_engine.py` — Motor ctransformers/llama-cpp con CUDA
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
