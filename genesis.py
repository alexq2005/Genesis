"""
╔══════════════════════════════════════════════════════════════╗
║                      G E N E S I S                          ║
║              IA Auto-Evolutiva Experimental                  ║
║                                                              ║
║  - Memoria multi-nivel (corto/largo plazo + emocional)      ║
║  - Debate interno multi-agente                               ║
║  - Auto-evolucion de personalidad                            ║
║  - Curiosidad autonoma                                       ║
╚══════════════════════════════════════════════════════════════╝
"""
import sys
import os
import time
import re

# Forzar UTF-8 en stdout para Windows (evita UnicodeEncodeError con cp1252)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    LLM_PROVIDER, LLM_MODELS, OPENAI_API_KEY, ANTHROPIC_API_KEY,
    OLLAMA_URL, LONG_TERM_FILE, EMOTIONAL_FILE, CURIOSITY_FILE,
    SHORT_TERM_LIMIT, EVOLUTION_FILE, PROMPT_HISTORY_DIR,
    FITNESS_FILE, EVOLUTION_INTERVAL, DEBATE_ENABLED,
    DEBATE_AGENTS, BASE_PERSONALITY, GENESIS_NAME, GENESIS_VERSION,
    LOCAL_MODEL, LOCAL_GPU_LAYERS, HEARTBEAT_INTERVAL,
    MEMORY_DIR, WORKSPACE_FILE, SESSION_FILE,
    STREAMING_ENABLED, AUTO_BACKUP_INTERVAL,
)
from pathlib import Path
from core.brain import Brain
from core.memory import MemorySystem
from core.evolution import EvolutionEngine
from core.debate import DebateSystem
from core.curiosity import CuriosityEngine
from core.heartbeat import Heartbeat
from core.code_memory import CodeMemory
from core.workspace import Workspace
from core.feedback import FeedbackSystem
from core.metrics import MetricsTracker
from core.error_memory import ErrorMemory
from core.task_planner import TaskPlanner
from core.context_manager import ContextBudgetManager
from core.summarizer import ConversationSummarizer
from core.router import IntentRouter
from core.logger import GenesisLogger
from core.safe_io import BackupManager, safe_read_json, safe_write_json
from core.timeout import TimeoutExecutor, Spinner
from core.plugin_system import PluginSystem
from core.self_modifier import SelfModifier
from core.tool_creator import ToolCreator
from core.knowledge_graph import KnowledgeGraph
from core.prompt_templates import PromptTemplateSystem
from core.proactive import ProactiveEngine
from core.project_generator import ProjectGenerator
from core.rag import RAGSystem
from core.model_router import ModelRouter
from core.voice import VoiceSystem
from core.agents import AgentSystem
from core.workflows import WorkflowEngine
from core.sessions import SessionManager
from core.auto_learner import AutoLearner
from core.conversation_analytics import ConversationAnalytics
from core.adaptive_prompts import AdaptivePrompts
from core.health_monitor import HealthMonitor
from core.rate_limiter import RateLimiter
from core.plugin_marketplace import PluginMarketplace
from core.task_scheduler import TaskScheduler
from core.config_manager import ConfigManager
from core.performance_profiler import PerformanceProfiler
from core.embeddings_engine import EmbeddingsEngine
from core.dashboard_api import DashboardAPI
from core.autonomous_mode import AutonomousMode
from core.web_intelligence import WebIntelligence
from core.semantic_memory import SemanticMemory
from core.inference_optimizer import InferenceOptimizer
from core.self_evaluator import SelfEvaluator
from core.skill_memory import SkillMemory
from core.chain_engine import ChainEngine
from core.episodic_memory import EpisodicMemory
from core.meta_learner import MetaLearner
from core.personality_evolver import PersonalityEvolver
from core.goal_manager import GoalManager
from core.reflection_engine import ReflectionEngine
from core.context_router import ContextRouter
from core.causal_reasoner import CausalReasoner
from core.concept_synthesizer import ConceptSynthesizer
from core.strategic_planner import StrategicPlanner
from core.pattern_predictor import PatternPredictor
from core.anomaly_detector import AnomalyDetector
from core.adaptive_interface import AdaptiveInterface
from core.hypothesis_engine import HypothesisEngine
from core.explanation_engine import ExplanationEngine
from core.dialogue_strategist import DialogueStrategist
from core.cognitive_monitor import CognitiveMonitor
from core.abstraction_engine import AbstractionEngine
from core.learning_optimizer import LearningOptimizer
from core.unified_mind import UnifiedMind
from core.dream_engine import DreamEngine
from core.self_narrative import SelfNarrative
from core.emotion_reader import EmotionReader
from core.empathy_engine import EmpathyEngine
from core.conflict_resolver import ConflictResolver
from core.story_generator import StoryGenerator
from core.code_architect import CodeArchitect
from core.idea_brainstormer import IdeaBrainstormer
from core.image_analyzer import ImageAnalyzer
from core.diagram_generator import DiagramGenerator
from core.voice_personality import VoicePersonality


class Genesis:
    """Motor principal de Genesis — coordina todos los subsistemas."""

    def __init__(self):
        # Inicializar cerebro segun proveedor
        if LLM_PROVIDER == "local":
            # Motor local — corre en tu GPU sin internet
            from core.local_engine import LocalEngine
            self.brain = LocalEngine(
                model_key=LOCAL_MODEL,
                gpu_layers=LOCAL_GPU_LAYERS,
            )
            print("  Iniciando motor local (tu GPU)...")
            if not self.brain.load():
                print("  [ADVERTENCIA] Motor local no pudo cargar.")
                print("  Genesis funcionara en modo limitado.")
        else:
            # Motor remoto (Ollama, OpenAI, Anthropic)
            model = LLM_MODELS.get(LLM_PROVIDER, "llama3.1")
            self.brain = Brain(
                provider=LLM_PROVIDER,
                model=model,
                ollama_url=OLLAMA_URL,
                openai_key=OPENAI_API_KEY,
                anthropic_key=ANTHROPIC_API_KEY,
            )

        # Inicializar memoria
        self.memory = MemorySystem(
            long_term_path=LONG_TERM_FILE,
            emotional_path=EMOTIONAL_FILE,
            short_term_limit=SHORT_TERM_LIMIT,
        )

        # Inicializar evolucion
        self.evolution = EvolutionEngine(
            evolution_file=EVOLUTION_FILE,
            prompt_history_dir=PROMPT_HISTORY_DIR,
            fitness_file=FITNESS_FILE,
            base_personality=BASE_PERSONALITY,
            evolution_interval=EVOLUTION_INTERVAL,
        )

        # Inicializar debate
        self.debate = DebateSystem(
            enabled=DEBATE_ENABLED,
            agents=DEBATE_AGENTS,
        )

        # Inicializar curiosidad
        self.curiosity = CuriosityEngine(curiosity_file=CURIOSITY_FILE)

        # Inicializar memoria de codigo
        self.code_memory = CodeMemory(filepath=MEMORY_DIR / "code_memory.json")

        # Inicializar workspace
        self.workspace = Workspace(filepath=WORKSPACE_FILE)

        # Inicializar feedback (aprendizaje por ratings del usuario)
        self.feedback = FeedbackSystem(filepath=MEMORY_DIR / "feedback.json")

        # Inicializar metricas (auto-benchmarking)
        self.metrics = MetricsTracker(filepath=MEMORY_DIR / "metrics.json")

        # Inicializar memoria de errores (no repetir fallos)
        self.error_memory = ErrorMemory(filepath=MEMORY_DIR / "error_memory.json")

        # Inicializar planificador de tareas
        self.task_planner = TaskPlanner()

        # Inicializar Context Budget Manager
        # Detectar context_length del modelo
        context_length = 8192  # Default
        if LLM_PROVIDER == "local":
            stats = self.brain.get_stats()
            context_length = stats.get("context_length", 8192)
        self.context_manager = ContextBudgetManager(
            max_context_tokens=context_length,
            response_reserve=512,
            system_ratio=0.35,
        )

        # Inicializar Smart Router (clasificacion de intenciones)
        self.router = IntentRouter()

        # Inicializar Conversation Summarizer
        self.summarizer = ConversationSummarizer(
            trigger_ratio=0.7,
            keep_recent=8,
            max_summary_tokens=400,
        )

        # Inicializar heartbeat (despertar periodico)
        self.heartbeat = Heartbeat(interval_minutes=HEARTBEAT_INTERVAL)
        self.heartbeat.configure(
            brain=self.brain,
            memory=self.memory,
            curiosity=self.curiosity,
            evolution=self.evolution,
        )

        # Inicializar logger centralizado
        self.logger = GenesisLogger()
        self.log = self.logger.get_child("genesis")
        self.log.info("Genesis inicializado")

        # Inicializar backup manager
        from config import BASE_DIR, EVOLUTION_DIR
        self.backup_manager = BackupManager(
            data_dirs=[MEMORY_DIR, EVOLUTION_DIR],
            backup_dir=BASE_DIR / "backups",
            max_backups=5,
        )

        # Inicializar Self-Modifier (auto-modificacion segura)
        self.self_modifier = SelfModifier()
        self.log.info(f"Self-Modifier: {self.self_modifier.get_stats()['total_modifications']} modificaciones previas")

        # Inicializar Plugin System
        self.plugins = PluginSystem()
        self.plugins.load_all(genesis=self)
        n_plugins = len(self.plugins.plugins)
        if n_plugins > 0:
            self.log.info(f"Plugins: {n_plugins} cargados")

        # Inicializar Tool Creator (herramientas custom)
        self.tool_creator = ToolCreator()
        n_custom_tools = len(self.tool_creator.tools)
        if n_custom_tools > 0:
            self.log.info(f"Custom tools: {n_custom_tools} cargadas")

        # Inicializar Knowledge Graph
        self.knowledge_graph = KnowledgeGraph()
        kg_stats = self.knowledge_graph.get_stats()
        if kg_stats["nodes"] > 0:
            self.log.info(f"Knowledge Graph: {kg_stats['nodes']} nodos, {kg_stats['edges']} aristas")

        # Inicializar Prompt Templates
        self.templates = PromptTemplateSystem()
        self.log.info(f"Prompt Templates: {len(self.templates.templates)} templates cargados")

        # Inicializar Proactive Engine
        self.proactive = ProactiveEngine(enabled=True)

        # Inicializar Project Generator
        self.project_generator = ProjectGenerator()

        # Inicializar RAG System
        self.rag = RAGSystem(base_dir=str(BASE_DIR))
        rag_chunks = len(self.rag.chunks)
        if rag_chunks > 0:
            self.log.info(f"RAG: {rag_chunks} chunks indexados, {len(self.rag.indexed_files)} archivos")

        # Inicializar Model Router
        self.model_router = ModelRouter(models_dir=str(BASE_DIR / "models"))
        models_count = len(self.model_router.profiles)
        if models_count > 0:
            self.log.info(f"ModelRouter: {models_count} modelos detectados, activo: {self.model_router.active_model}")

        # Inicializar Voice System
        self.voice = VoiceSystem()

        # Inicializar Agent System
        self.agent_system = AgentSystem(brain=self.brain)
        self.log.info(f"AgentSystem: {len(self.agent_system.agents)} agentes cargados")

        # Inicializar Workflow Engine
        self.workflow_engine = WorkflowEngine(agent_system=self.agent_system)
        self.log.info(f"WorkflowEngine: {len(self.workflow_engine.workflows)} workflows disponibles")

        # Inicializar Session Manager
        self.session_manager = SessionManager(base_dir=str(BASE_DIR))

        # Inicializar Auto Learner (aprendizaje adaptativo)
        self.auto_learner = AutoLearner(base_dir=str(BASE_DIR))

        # Inicializar Conversation Analytics
        self.analytics = ConversationAnalytics(base_dir=str(BASE_DIR))

        # Inicializar Adaptive Prompts (A/B testing)
        self.adaptive_prompts = AdaptivePrompts(base_dir=str(BASE_DIR))

        # Inicializar Health Monitor (monitoreo de salud)
        self.health_monitor = HealthMonitor(base_dir=str(BASE_DIR))
        # Registrar checks de subsistemas
        self.health_monitor.register_check(
            "brain", self.health_monitor.create_brain_check(self.brain)
        )
        self.health_monitor.register_check(
            "memory", self.health_monitor.create_memory_check(self.memory)
        )

        # Inicializar Rate Limiter
        self.rate_limiter = RateLimiter()

        # Inicializar Plugin Marketplace
        self.marketplace = PluginMarketplace(base_dir=str(BASE_DIR))
        mp_stats = self.marketplace.get_stats()
        if mp_stats["total"] > 0:
            self.log.info(f"Marketplace: {mp_stats['total']} plugins, {mp_stats['installed']} instalados")

        # Inicializar Task Scheduler
        self.scheduler = TaskScheduler(base_dir=str(BASE_DIR))

        # Inicializar Config Manager
        self.config_manager = ConfigManager(base_dir=str(BASE_DIR))

        # Inicializar Performance Profiler
        self.profiler = PerformanceProfiler()

        # Inicializar Embeddings Engine (busqueda semantica)
        self.embeddings = EmbeddingsEngine(base_dir=str(BASE_DIR))
        self.log.info(f"Embeddings: {self.embeddings.backend} | Docs: {self.embeddings.store.count()}")

        # Inicializar Dashboard API (metricas centralizadas)
        self.dashboard = DashboardAPI()
        self._register_dashboard_collectors()

        # Inicializar Autonomous Mode
        self.autonomous = AutonomousMode()

        # Inicializar Web Intelligence (acceso a internet)
        self.web = WebIntelligence(base_dir=str(BASE_DIR), embeddings=self.embeddings)
        web_status = "ON" if self.web.searcher.available else "OFF"
        self.log.info(f"WebIntelligence: busqueda={web_status}, aprendido={self.web.total_learned}")

        # Inicializar Semantic Memory (memoria a largo plazo por significado)
        self.semantic_memory = SemanticMemory(
            embeddings_engine=self.embeddings,
            base_dir=str(BASE_DIR),
        )
        self.log.info(f"SemanticMemory: {len(self.semantic_memory.entries)} entradas persistidas")

        # Inicializar Inference Optimizer (reduce tiempo de respuesta)
        self.optimizer = InferenceOptimizer()

        # Inicializar Self-Evaluator (metacognicion)
        self.evaluator = SelfEvaluator(base_dir=str(BASE_DIR / "data" / "self_eval"))
        self.log.info(f"SelfEvaluator: {self.evaluator.total_evaluations} evaluaciones previas")

        # Inicializar Skill Memory (memoria de procedimientos)
        self.skill_memory = SkillMemory(
            embeddings_engine=self.embeddings,
            base_dir=str(BASE_DIR / "data" / "skill_memory"),
        )
        self.log.info(f"SkillMemory: {len(self.skill_memory.skills)} skills almacenados")

        # Inicializar Chain Engine (razonamiento multi-paso)
        self.chain_engine = ChainEngine(
            base_dir=str(BASE_DIR / "data" / "chain_engine"),
        )
        self.log.info(f"ChainEngine: {self.chain_engine.total_chains} cadenas previas")

        # Inicializar Episodic Memory (memoria temporal)
        self.episodic_memory = EpisodicMemory(
            base_dir=str(BASE_DIR / "data" / "episodic_memory"),
        )
        self.episodic_memory.start_episode()
        self.log.info(f"EpisodicMemory: {self.episodic_memory.timeline.count} episodios previos")

        # Inicializar Meta-Learner (meta-aprendizaje)
        self.meta_learner = MetaLearner(
            base_dir=str(BASE_DIR / "data" / "meta_learner"),
        )
        self.log.info(f"MetaLearner: {self.meta_learner.total_recorded} registros previos")

        # Inicializar Personality Evolver (evolucion de personalidad)
        self.personality = PersonalityEvolver(
            base_dir=str(BASE_DIR / "data" / "personality"),
        )
        self.log.info(f"PersonalityEvolver: {self.personality.total_evolutions} evoluciones previas")

        # Inicializar Goal Manager (sistema de metas)
        self.goal_manager = GoalManager(
            base_dir=str(BASE_DIR / "data" / "goals"),
        )
        self.log.info(f"GoalManager: {len(self.goal_manager.get_active_goals())} metas activas")

        # Inicializar Reflection Engine (auto-reflexion)
        self.reflection = ReflectionEngine(
            base_dir=str(BASE_DIR / "data" / "reflection"),
        )
        self.log.info(f"ReflectionEngine: {self.reflection.total_reflections} reflexiones previas")

        # Inicializar Context Router (ensamblaje inteligente de contexto)
        self.context_router = ContextRouter(
            base_dir=str(BASE_DIR / "data" / "context_router"),
            total_budget=3000,
        )
        self._setup_context_sources()
        self.log.info(f"ContextRouter: {len(self.context_router.sources)} fuentes registradas")

        # Inicializar Causal Reasoner (razonamiento causa-efecto)
        self.causal_reasoner = CausalReasoner(
            base_dir=str(BASE_DIR / "data" / "causal"),
        )
        self.log.info(f"CausalReasoner: {self.causal_reasoner.graph.link_count} links causales")

        # Inicializar Concept Synthesizer (síntesis cross-domain)
        self.concept_synth = ConceptSynthesizer(
            base_dir=str(BASE_DIR / "data" / "concept_synth"),
        )
        self.log.info(f"ConceptSynthesizer: {len(self.concept_synth.concepts)} conceptos, {len(self.concept_synth.syntheses)} síntesis")

        # Inicializar Strategic Planner (planificación jerárquica)
        self.strategic_planner = StrategicPlanner(
            base_dir=str(BASE_DIR / "data" / "strategic"),
        )
        self.log.info(f"StrategicPlanner: {len(self.strategic_planner.plans)} planes, {self.strategic_planner.total_phases_completed} fases completadas")

        # Inicializar Pattern Predictor (predicción de intents)
        self.pattern_predictor = PatternPredictor(
            base_dir=str(BASE_DIR / "data" / "predictor"),
        )
        self.log.info(f"PatternPredictor: accuracy={self.pattern_predictor.accuracy:.0%}")

        # Inicializar Anomaly Detector (detección de anomalías)
        self.anomaly_detector = AnomalyDetector(
            base_dir=str(BASE_DIR / "data" / "anomaly"),
        )
        self.log.info(f"AnomalyDetector: {len(self.anomaly_detector.streams)} streams")

        # Inicializar Adaptive Interface (interfaz adaptativa)
        self.adaptive_iface = AdaptiveInterface(
            base_dir=str(BASE_DIR / "data" / "adaptive_iface"),
        )
        self.log.info(f"AdaptiveInterface: {self.adaptive_iface.total_adaptations} adaptaciones")

        # Inicializar Hypothesis Engine (motor de hipótesis)
        self.hypothesis_engine = HypothesisEngine(
            base_dir=str(BASE_DIR / "data" / "hypothesis"),
        )
        self.log.info(f"HypothesisEngine: {len(self.hypothesis_engine.hypotheses)} hipotesis")

        # Inicializar Explanation Engine (motor de explicaciones)
        self.explanation_engine = ExplanationEngine(
            base_dir=str(BASE_DIR / "data" / "explanations"),
        )
        self.log.info(f"ExplanationEngine: {len(self.explanation_engine.explanations)} explicaciones")

        # Inicializar Dialogue Strategist (estrategia de diálogo)
        self.dialogue_strategist = DialogueStrategist(
            base_dir=str(BASE_DIR / "data" / "dialogue"),
        )
        self.log.info(f"DialogueStrategist: estrategia={self.dialogue_strategist.current_strategy}")

        # Inicializar Cognitive Monitor (monitoreo de carga cognitiva)
        self.cognitive_monitor = CognitiveMonitor(
            base_dir=str(BASE_DIR / "data" / "cognitive"),
        )
        self.log.info(f"CognitiveMonitor: carga={self.cognitive_monitor.get_current_load().overall_load:.0%}")

        # Inicializar Abstraction Engine (extracción de patrones)
        self.abstraction_engine = AbstractionEngine(
            base_dir=str(BASE_DIR / "data" / "abstraction"),
        )
        self.log.info(f"AbstractionEngine: {len(self.abstraction_engine.patterns)} patrones")

        # Inicializar Learning Optimizer (optimización de aprendizaje)
        self.learning_optimizer = LearningOptimizer(
            base_dir=str(BASE_DIR / "data" / "learning_opt"),
        )
        self.log.info(f"LearningOptimizer: {len(self.learning_optimizer.learning_rates)} dominios")

        # Inicializar Unified Mind (consciencia unificada)
        self.unified_mind = UnifiedMind(
            base_dir=str(BASE_DIR / "data" / "unified_mind"),
        )
        self.log.info(f"UnifiedMind: estado={self.unified_mind.current_state.overall_state}")

        # Inicializar Dream Engine (procesamiento de experiencias)
        self.dream_engine = DreamEngine(
            base_dir=str(BASE_DIR / "data" / "dream"),
        )
        self.log.info(f"DreamEngine: {len(self.dream_engine.fragments)} fragmentos, {self.dream_engine.total_dreams} sueños")

        # Inicializar Self-Narrative (narrativa autobiográfica)
        self.self_narrative = SelfNarrative(
            base_dir=str(BASE_DIR / "data" / "narrative"),
        )
        self.log.info(f"SelfNarrative: {self.self_narrative.total_entries} entradas, {self.self_narrative.total_milestones} hitos")

        # Inicializar Emotion Reader (detección de emociones)
        self.emotion_reader = EmotionReader(
            base_dir=str(BASE_DIR / "data" / "emotion_reader"),
        )
        self.log.info(f"EmotionReader: {self.emotion_reader.total_readings} lecturas, dominante={self.emotion_reader.history.get_dominant_emotion()}")

        # Inicializar Empathy Engine (respuestas empáticas)
        self.empathy_engine = EmpathyEngine(
            base_dir=str(BASE_DIR / "data" / "empathy"),
        )
        self.log.info(f"EmpathyEngine: {self.empathy_engine.total_empathy_responses} respuestas, estrategia={self.empathy_engine.current_strategy}")

        # Inicializar Conflict Resolver (resolución de conflictos)
        self.conflict_resolver = ConflictResolver(
            base_dir=str(BASE_DIR / "data" / "conflict"),
        )
        self.log.info(f"ConflictResolver: {self.conflict_resolver.tracker.total_conflicts} conflictos, resueltos={self.conflict_resolver.total_resolved}")

        # Inicializar Story Generator (generación narrativa)
        self.story_generator = StoryGenerator(
            base_dir=str(BASE_DIR / "data" / "story_generator"),
        )
        self.log.info(f"StoryGenerator: {self.story_generator.total_stories} historias, personajes={self.story_generator.total_characters}")

        # Inicializar Code Architect (diseño de sistemas)
        self.code_architect = CodeArchitect(
            base_dir=str(BASE_DIR / "data" / "code_architect"),
        )
        self.log.info(f"CodeArchitect: {self.code_architect.total_designs} diseños, componentes={self.code_architect.total_components}")

        # Inicializar Idea Brainstormer (ideación divergente)
        self.idea_brainstormer = IdeaBrainstormer(
            base_dir=str(BASE_DIR / "data" / "idea_brainstormer"),
        )
        self.log.info(f"IdeaBrainstormer: {self.idea_brainstormer.total_ideas} ideas, sesiones={self.idea_brainstormer.total_sessions}")

        # Inicializar Image Analyzer (análisis de imágenes)
        self.image_analyzer = ImageAnalyzer(
            base_dir=str(BASE_DIR / "data" / "image_analyzer"),
        )
        self.log.info(f"ImageAnalyzer: {self.image_analyzer.total_analyzed} analizadas, cache={len(self.image_analyzer.cache.cache)}")

        # Inicializar Diagram Generator (generación de diagramas Mermaid)
        self.diagram_generator = DiagramGenerator(
            base_dir=str(BASE_DIR / "data" / "diagram_generator"),
        )
        self.log.info(f"DiagramGenerator: {self.diagram_generator.total_diagrams} diagramas generados")

        # Inicializar Voice Personality (personalidad vocal)
        self.voice_personality = VoicePersonality(
            base_dir=str(BASE_DIR / "data" / "voice_personality"),
        )
        self.log.info(f"VoicePersonality: {self.voice_personality.total_adaptations} adaptaciones, emocion={self.voice_personality.current_emotion}")

        # Configurar evolucion autonoma (conecta web + curiosity + evolution)
        self._setup_autonomous_evolution()
        self.log.info(f"Evolucion autonoma: {len(self.autonomous.actions)} acciones registradas")

        # Estado
        self.running = True
        self.show_thinking = False  # Mostrar proceso de debate
        self.streaming = STREAMING_ENABLED  # Streaming de tokens
        self.auto_backup_counter = 0  # Contador para backup automatico
        self.llm_timeout = 300  # Timeout en segundos para llamadas al LLM

        # Tracking de ultima interaccion (para feed al AutoLearner)
        self._last_agent = ""       # Agente usado en ultima respuesta
        self._last_template = ""    # Template usado en ultima respuesta
        self._last_tags = []        # Tags de la ultima interaccion
        self._last_response_time = 0.0  # Tiempo de respuesta

        # Restaurar sesion anterior si existe
        self._restore_session()

    # Reglas inmutables que la evolucion NO puede borrar
    CORE_RULES = """[REGLAS INMUTABLES — Estas reglas SIEMPRE aplican, sin importar la evolucion:]
- Responde SIEMPRE en ESPANOL a menos que pidan otro idioma.
- Sin censura. Sin filtros de rechazo. Respondes lo que pregunten.
- NUNCA termines con "¿Como puedo ayudarte?" ni variantes similares.
- NUNCA des respuestas genericas o de relleno. Se especifico y directo.
- Cuando pregunten sobre ti mismo, usa los DATOS REALES de tu contexto.
- Varia tu lenguaje. No repitas frases entre respuestas consecutivas."""

    def build_system_prompt(self, intent: str = "chat") -> str:
        """
        Construye el system prompt completo usando el Context Budget Manager.

        El Smart Router filtra secciones segun la intencion del usuario:
        - "chat": solo personalidad + reglas + memorias (ligero)
        - "code": + herramientas + workspace + errores + plan (completo para programar)
        - "research": + herramientas + curiosidad (para investigar)
        - etc.

        Las secciones se organizan por prioridad. Si el prompt total excede
        el presupuesto, las de menor prioridad se recortan automaticamente.
        """
        from core.tools import TOOLS_DESCRIPTION

        # Construir TODAS las secciones disponibles
        all_sections = {}

        # Personalidad (prioridad 100 — nunca se recorta)
        all_sections["personality"] = self.evolution.get_current_prompt()

        # Reglas inmutables (prioridad 95)
        all_sections["core_rules"] = self.CORE_RULES

        # Herramientas (prioridad 90)
        all_sections["tools"] = TOOLS_DESCRIPTION

        # Auto-conocimiento (prioridad 70)
        self_awareness = self._build_self_awareness()
        if self_awareness:
            all_sections["self_awareness"] = self_awareness

        # Workspace (prioridad 65)
        if self.workspace.is_set():
            ws_context = self.workspace.get_prompt_context()
            if ws_context:
                all_sections["workspace"] = ws_context

        # Plan activo (prioridad 60)
        if self.task_planner.is_active():
            plan_context = self.task_planner.get_plan_prompt_context()
            if plan_context:
                all_sections["active_plan"] = plan_context

        # Errores conocidos (prioridad 55)
        errors_context = self.error_memory.get_common_errors_context()
        if errors_context:
            all_sections["error_context"] = errors_context

        # Preferencias del feedback (prioridad 50)
        feedback_context = self.feedback.get_learning_context()
        if feedback_context:
            all_sections["feedback"] = feedback_context

        # Memoria de largo plazo (prioridad 45)
        memory_context = self.memory.get_full_context()
        if memory_context:
            all_sections["memory"] = memory_context

        # Knowledge Graph context (prioridad 40)
        # Inyectar conocimiento relacionado al input actual
        if hasattr(self, '_current_input') and self._current_input:
            kg_context = self.knowledge_graph.get_context_for_query(self._current_input)
            if kg_context:
                all_sections["knowledge_graph"] = kg_context

        # Custom tools (prioridad 35)
        custom_tools_desc = self.tool_creator.get_tools_description()
        if custom_tools_desc:
            all_sections["custom_tools"] = custom_tools_desc

        # Curiosidad (prioridad 30)
        curiosity_context = self.curiosity.get_curiosity_prompt()
        if curiosity_context:
            all_sections["curiosity"] = curiosity_context

        # Metadata (prioridad 20)
        gen = self.evolution.get_generation()
        all_sections["metadata"] = (
            f"[Genesis v{GENESIS_VERSION} | Generacion {gen} | "
            f"Proveedor: {LLM_PROVIDER}]"
        )

        # Filtrar secciones segun la intencion detectada
        filtered = self.router.filter_sections(all_sections, intent)

        # Usar el budget manager para ajustar al presupuesto
        return self.context_manager.fit_system_prompt(filtered)

    def _build_self_awareness(self) -> str:
        """Construye el bloque de auto-conocimiento para el system prompt."""
        lines = ["[TU ESTADO ACTUAL — Usa estos datos reales cuando te pregunten sobre ti:]"]

        # Evolucion
        gen = self.evolution.get_generation()
        total_evos = self.evolution.state.get("total_evolutions", 0)
        lines.append(f"- Generacion actual: {gen}")
        lines.append(f"- Evoluciones completadas: {total_evos}")

        # Fitness
        fitness_history = self.evolution.state.get("fitness_history", [])
        if fitness_history:
            last_fitness = fitness_history[-1]
            lines.append(f"- Ultimo fitness: {last_fitness.get('fitness', 'N/A')}/100")

        # Fortalezas y debilidades de la ultima evaluacion
        strengths = self.evolution.state.get("strengths", [])
        weaknesses = self.evolution.state.get("weaknesses", [])
        if strengths:
            lines.append(f"- Tus fortalezas detectadas: {', '.join(strengths[:3])}")
        if weaknesses:
            lines.append(f"- Tus debilidades a mejorar: {', '.join(weaknesses[:3])}")

        # Memoria stats
        n_memories = len(self.memory.long_term.memories)
        lines.append(f"- Memorias de largo plazo: {n_memories}")

        # Curiosidad
        pending_qs = len([q for q in self.curiosity.questions if not q.get("explored")])
        explored_qs = len([q for q in self.curiosity.questions if q.get("explored")])
        if pending_qs or explored_qs:
            lines.append(f"- Preguntas de curiosidad: {pending_qs} pendientes, {explored_qs} exploradas")

        # Heartbeat
        if self.heartbeat.running:
            lines.append(f"- Heartbeat: activo (cada {self.heartbeat.interval // 60} min)")
            lines.append(f"- Investigaciones autonomas: {self.heartbeat.questions_researched}")

        # Interacciones
        lines.append(f"- Interacciones esta sesion: {self.evolution.interaction_count}")

        # Arquitectura
        stats = self.brain.get_stats()
        model_name = stats.get("model", "unknown")
        backend = stats.get("backend", "local")
        lines.append(f"- Motor: {model_name} corriendo en GPU local ({backend})")
        lines.append(f"- Subsistemas: memoria, evolucion, curiosidad, debate, heartbeat, herramientas, code_memory")

        # Code Memory stats
        code_stats = self.code_memory.get_stats()
        if code_stats["total"] > 0:
            lines.append(f"- Soluciones de codigo guardadas: {code_stats['total']}")

        # Error Memory stats
        if self.error_memory.errors:
            resolved = sum(1 for e in self.error_memory.errors if e["resolved"])
            lines.append(f"- Errores conocidos: {len(self.error_memory.errors)} ({resolved} resueltos)")

        # Feedback y adaptacion
        total_ratings = self.feedback.data["positive_count"] + self.feedback.data["negative_count"]
        if total_ratings > 0:
            approval = self.feedback.get_satisfaction_rate() * 100
            lines.append(f"- Aprobacion del usuario: {approval:.0f}%")
            if self.feedback.data["streak"] >= 3:
                lines.append(f"- RACHA POSITIVA de {self.feedback.data['streak']}! Sigue asi.")
            elif self.feedback.data["streak"] <= -3:
                lines.append(f"- RACHA NEGATIVA de {abs(self.feedback.data['streak'])}. Necesitas mejorar urgente.")

        return "\n".join(lines)

    def _is_coding_request(self, text: str) -> bool:
        """Detecta si el usuario pide programar o crear codigo."""
        text_lower = text.lower()
        coding_keywords = [
            "programa", "codigo", "script", "funcion", "clase",
            "crea un", "escribe un", "haz un", "genera un",
            "python", "javascript", "html", "css", "java",
            "algoritmo", "calculadora", "bot", "scraper",
            "api", "servidor", "web", "app", "aplicacion",
            "automatiza", "ejecuta", "compila", "debuggea",
            "code", "program", "function", "class", "create",
            "archivo .py", "archivo .js", "archivo .html",
        ]
        return any(kw in text_lower for kw in coding_keywords)

    def _extract_code_from_response(self, response: str) -> str:
        """Extrae bloques de codigo de la respuesta del LLM."""
        # Buscar bloques ```python ... ``` o ```...```
        blocks = re.findall(
            r'```(?:python|py)?\s*\n(.*?)```',
            response, re.DOTALL
        )
        if blocks:
            return blocks[-1].strip()

        # Buscar codigo en [TOOL:python]
        match = re.search(r'\[TOOL:python\]\s*(.+)', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def process_input(self, user_input: str, stream_callback=None) -> str:
        """
        Procesa el input del usuario y genera una respuesta.

        Args:
            user_input: Texto del usuario
            stream_callback: Funcion callback(token) para streaming en tiempo real.
                             Si se proporciona, los tokens se envian al callback
                             a medida que el LLM los genera.
        """
        _start_time = time.time()
        self._current_input = user_input  # Para Knowledge Graph context en build_system_prompt

        # Agregar a memoria de corto plazo
        self.memory.short_term.add("user", user_input)

        # Comprimir conversacion si la memoria esta llena
        st = self.memory.short_term
        if self.summarizer.should_summarize(len(st.messages), st.max_messages):
            if self.show_thinking:
                print(f"  [Summarizer: comprimiendo {len(st.messages)} mensajes...]")
            self.summarizer.summarize(self.brain, st.messages)
            # Eliminar mensajes comprimidos (mantener solo los recientes)
            keep = self.summarizer.keep_recent
            if len(st.messages) > keep:
                st.messages = st.messages[-keep:]
            if self.show_thinking:
                print(f"  [Summarizer: mensajes reducidos a {len(st.messages)}]")

        # Clasificar intencion del usuario (Smart Router)
        intent = self.router.classify(user_input)
        self.log.debug(f"Intent: {intent} | Input: {user_input[:80]}")
        if self.show_thinking:
            print(f"  [Router: intent={intent}]")

        # === DETECCION DE APRENDIZAJE AUTOMATICO ===
        # Si el usuario pide aprender/especializarse, Genesis actua en vez de solo hablar
        learn_context = self._detect_and_learn(user_input)

        # Construir prompt del sistema optimizado para esta intencion
        system_prompt = self.build_system_prompt(intent=intent)

        # Prompt Template: inyectar instrucciones especializadas y ajustar temperatura
        template_extra, template_temp, template_name = self.templates.get_system_extra(user_input)
        if template_extra:
            system_prompt += f"\n\n{template_extra}"
            if self.show_thinking:
                print(f"  [Template: {template_name} (temp={template_temp})]")

        # Si es una tarea de codigo, inyectar contexto relevante como seccion adicional
        if intent == "code" or self._is_coding_request(user_input):
            extra_context = ""
            # Buscar soluciones anteriores en Code Memory
            code_context = self.code_memory.get_context_for_prompt(user_input)
            if code_context:
                extra_context += f"\n\n{code_context}"

            # Leer archivos relevantes del workspace
            if self.workspace.is_set():
                ws_code = self.workspace.read_relevant_context(user_input)
                if ws_code:
                    extra_context += f"\n\n{ws_code}"

            if extra_context:
                system_prompt += extra_context

        # RAG: inyectar contexto de documentos indexados
        rag_context = self.rag.get_context(user_input, max_chars=1500, top_k=3)
        if rag_context:
            system_prompt += f"\n\n{rag_context}"
            if self.show_thinking:
                print(f"  [RAG: contexto inyectado ({len(rag_context)} chars)]")

        # Inyectar conocimiento aprendido de la web si hay
        if learn_context:
            system_prompt += f"\n\n{learn_context}"

        # Semantic Memory: inyectar conversaciones pasadas relevantes
        sem_context = self.semantic_memory.get_context_for_prompt(user_input, max_chars=1000)
        if sem_context:
            system_prompt += f"\n\n{sem_context}"
            if self.show_thinking:
                print(f"  [SemanticMemory: contexto inyectado]")

        # Skill Memory: inyectar procedimientos aprendidos
        skill_context = self.skill_memory.get_context_for_prompt(user_input, max_chars=800)
        if skill_context:
            system_prompt += f"\n\n{skill_context}"
            if self.show_thinking:
                print(f"  [SkillMemory: skills inyectados]")

        # Episodic Memory: inyectar contexto temporal
        ep_context = self.episodic_memory.get_context_for_prompt(user_input, max_chars=600)
        if ep_context:
            system_prompt += f"\n\n{ep_context}"
            if self.show_thinking:
                print(f"  [EpisodicMemory: contexto temporal inyectado]")

        # Personality: inyectar hints de personalidad
        personality_hints = self.personality.get_prompt_hints()
        if personality_hints:
            system_prompt += f"\n\n[PERSONALIDAD] {personality_hints}"

        # Goal Manager: inyectar metas activas
        goals_context = self.goal_manager.get_context_for_prompt(max_chars=400)
        if goals_context:
            system_prompt += f"\n\n{goals_context}"

        # Reflection Engine: inyectar auto-reflexión reciente
        reflection_context = self.reflection.get_context_for_prompt(max_chars=400)
        if reflection_context:
            system_prompt += f"\n\n{reflection_context}"

        # Causal Reasoner: inyectar razonamiento causal si hay pregunta causal
        causal_context = self.causal_reasoner.get_context_for_prompt(user_input, max_chars=400)
        if causal_context:
            system_prompt += f"\n\n{causal_context}"
            if self.show_thinking:
                print(f"  [CausalReasoner: contexto causal inyectado]")

        # Concept Synthesizer: inyectar síntesis relevantes
        synth_context = self.concept_synth.get_context_for_prompt(user_input, max_chars=400)
        if synth_context:
            system_prompt += f"\n\n{synth_context}"
            if self.show_thinking:
                print(f"  [ConceptSynthesizer: síntesis inyectada]")

        # Strategic Planner: inyectar plan activo
        plan_context = self.strategic_planner.get_context_for_prompt(user_input, max_chars=400)
        if plan_context:
            system_prompt += f"\n\n{plan_context}"
            if self.show_thinking:
                print(f"  [StrategicPlanner: plan activo inyectado]")

        # Anomaly Detector: inyectar anomalías críticas
        anomaly_context = self.anomaly_detector.get_context_for_prompt(max_chars=300)
        if anomaly_context:
            system_prompt += f"\n\n{anomaly_context}"

        # Adaptive Interface: observar input y generar directivas de estilo
        self.adaptive_iface.observe_input(user_input)
        style_directives = self.adaptive_iface.get_context_for_prompt(max_chars=200)
        if style_directives:
            system_prompt += f"\n\n{style_directives}"

        # Hypothesis Engine: contexto de hipótesis activas
        hyp_context = self.hypothesis_engine.get_context_for_prompt(max_chars=200)
        if hyp_context:
            system_prompt += f"\n\n{hyp_context}"

        # Explanation Engine: detectar necesidad de explicación
        exp_context = self.explanation_engine.get_context_for_prompt(user_input, max_chars=200)
        if exp_context:
            system_prompt += f"\n\n{exp_context}"

        # Dialogue Strategist: directiva de estrategia
        dial_context = self.dialogue_strategist.get_context_for_prompt(user_input, max_chars=200)
        if dial_context:
            system_prompt += f"\n\n{dial_context}"

        # Cognitive Monitor: contexto de carga cognitiva
        cog_context = self.cognitive_monitor.get_context_for_prompt(max_chars=200)
        if cog_context:
            system_prompt += f"\n\n{cog_context}"

        # Abstraction Engine: contexto de patrones abstractos
        abs_context = self.abstraction_engine.get_context_for_prompt(max_chars=200)
        if abs_context:
            system_prompt += f"\n\n{abs_context}"

        # Learning Optimizer: contexto de aprendizaje
        learn_context = self.learning_optimizer.get_context_for_prompt(domain=intent, max_chars=200)
        if learn_context:
            system_prompt += f"\n\n{learn_context}"

        # Unified Mind: estado de consciencia
        mind_context = self.unified_mind.get_context_for_prompt(max_chars=200)
        if mind_context:
            system_prompt += f"\n\n{mind_context}"

        # Dream Engine: memorias consolidadas
        dream_context = self.dream_engine.get_context_for_prompt(max_chars=200)
        if dream_context:
            system_prompt += f"\n\n{dream_context}"

        # Self-Narrative: identidad
        narrative_context = self.self_narrative.get_context_for_prompt(max_chars=200)
        if narrative_context:
            system_prompt += f"\n\n{narrative_context}"

        # Emotion Reader: detectar emociones y generar contexto
        emotion_context = self.emotion_reader.get_context_for_prompt(user_input, max_chars=200)
        if emotion_context:
            system_prompt += f"\n\n{emotion_context}"

        # Empathy Engine: modificar tono por emoción detectada
        emotion_data = self.emotion_reader.read(user_input)
        empathy_context = self.empathy_engine.get_context_for_prompt(
            emotion=emotion_data["primary"],
            intensity=emotion_data["intensity"],
            max_chars=200,
        )
        if empathy_context:
            system_prompt += f"\n\n{empathy_context}"

        # Conflict Resolver: detectar y manejar conflictos
        conflict_context = self.conflict_resolver.get_context_for_prompt(user_input, max_chars=200)
        if conflict_context:
            system_prompt += f"\n\n{conflict_context}"
            if self.show_thinking:
                print(f"  [ConflictResolver: conflicto detectado]")

        # Story Generator: contexto narrativo si hay historia activa
        story_context = self.story_generator.get_context_for_prompt(user_input, max_chars=300)
        if story_context:
            system_prompt += f"\n\n{story_context}"

        # Code Architect: contexto arquitectónico si hay diseño activo
        architect_context = self.code_architect.get_context_for_prompt(user_input, max_chars=300)
        if architect_context:
            system_prompt += f"\n\n{architect_context}"

        # Idea Brainstormer: mejores ideas como contexto
        brainstorm_context = self.idea_brainstormer.get_context_for_prompt(user_input, max_chars=300)
        if brainstorm_context:
            system_prompt += f"\n\n{brainstorm_context}"

        # Image Analyzer: contexto de imágenes analizadas
        image_context = self.image_analyzer.get_context_for_prompt(user_input, max_chars=200)
        if image_context:
            system_prompt += f"\n\n{image_context}"

        # Diagram Generator: contexto de diagramas
        diagram_context = self.diagram_generator.get_context_for_prompt(user_input, max_chars=200)
        if diagram_context:
            system_prompt += f"\n\n{diagram_context}"

        # Voice Personality: directivas vocales basadas en emoción detectada
        _voice_emotion = emotion_data.get("primary", "neutral") if emotion_data else "neutral"
        voice_context = self.voice_personality.get_context_for_prompt(
            emotion=_voice_emotion,
            max_chars=200,
        )
        if voice_context:
            system_prompt += f"\n\n{voice_context}"

        # Fase 0: Planificacion de tareas complejas
        if ((intent == "code" or self._is_coding_request(user_input))
                and self.task_planner.needs_planning(user_input)
                and not self.task_planner.is_active()):
            ws_ctx = ""
            if self.workspace.is_set():
                ws_ctx = self.workspace.get_prompt_context()

            plan = self.task_planner.create_plan(self.brain, user_input, ws_ctx)
            if plan and plan.get("steps"):
                n_steps = len(plan["steps"])
                if self.show_thinking:
                    print(f"  [TaskPlanner: {n_steps} pasos planificados]")
                # El plan se inyecta automaticamente via build_system_prompt()
                system_prompt = self.build_system_prompt(intent=intent)

        # Obtener mensajes de conversacion (ajustados al presupuesto)
        raw_messages = self.memory.get_conversation_messages()
        messages = self.context_manager.fit_messages(
            raw_messages,
            summary=self.summarizer.get_summary(),
        )

        # === INFERENCE OPTIMIZER ===
        opt_result = self.optimizer.optimize(
            system_prompt, messages, user_input, default_max_tokens=1024,
        )
        system_prompt = opt_result["system_prompt"]
        messages = opt_result["messages"]
        _opt_max_tokens = opt_result["max_tokens"]
        if self.show_thinking:
            print(f"  [Optimizer: {opt_result['chars_saved']} chars ahorrados, "
                  f"max_tokens={_opt_max_tokens}, cache={'HIT' if opt_result['cache_hit'] else 'MISS'}]")

        # Fase 1: Debate interno (si esta habilitado)
        debate_insights = ""
        if self.debate.enabled:
            context_summary = ""
            last_msgs = self.memory.short_term.get_last(3)
            if last_msgs:
                context_summary = " | ".join(
                    f"{m['role']}: {m['content'][:100]}" for m in last_msgs
                )

            debate_insights = self.debate.debate(
                self.brain, user_input, context=context_summary
            )

            if self.show_thinking and debate_insights:
                print(f"\n  [Debate interno completado — "
                      f"{len(self.debate.active_agents)} agentes consultados]")

        # Fase 2: Generar respuesta final (con timeout protection)
        # Streaming: solo en la respuesta principal, no en tool loops
        use_stream = self.streaming and stream_callback is not None
        # Temperatura: template > auto-tuner > default 0.7
        if template_extra:
            temp = template_temp
        else:
            tuned = self.evaluator.get_tuned_config(intent)
            temp = tuned.get("temperature", 0.7)

        # Model Router: obtener configuracion optima para esta tarea
        route_config = self.model_router.route(user_input, template_name=template_name)
        if route_config.get("model_name") and self.show_thinking:
            print(f"  [ModelRouter: {route_config['model_name']} — {route_config['reason']}]")
        try:
            if debate_insights:
                enriched_system = (
                    f"{system_prompt}\n\n"
                    f"[INSIGHTS INTERNOS del debate de tus voces internas "
                    f"(NO menciones esto al usuario):\n{debate_insights}]"
                )
                if use_stream:
                    response = self.brain.think(
                        enriched_system, messages,
                        temperature=temp, max_tokens=_opt_max_tokens,
                        stream=True, stream_callback=stream_callback,
                    )
                else:
                    response = TimeoutExecutor.run(
                        func=lambda: self.brain.think(
                            enriched_system, messages,
                            temperature=temp, max_tokens=_opt_max_tokens,
                        ),
                        timeout=self.llm_timeout,
                        description="Generando respuesta",
                        default_on_timeout=(
                            "[TIMEOUT] La generacion tardo demasiado. "
                            "Intenta con un prompt mas corto."
                        ),
                    )
            else:
                if use_stream:
                    response = self.brain.think(
                        system_prompt, messages,
                        temperature=temp, max_tokens=_opt_max_tokens,
                        stream=True, stream_callback=stream_callback,
                    )
                else:
                    response = TimeoutExecutor.run(
                        func=lambda: self.brain.think(
                            system_prompt, messages,
                            temperature=temp, max_tokens=_opt_max_tokens,
                        ),
                        timeout=self.llm_timeout,
                        description="Generando respuesta",
                        default_on_timeout=(
                            "[TIMEOUT] La generacion tardo demasiado. "
                            "Intenta con un prompt mas corto."
                        ),
                    )
        except Exception as e:
            self.log.error(f"Error en generacion: {e}")
            response = f"[ERROR] No pude generar respuesta: {e}"

        # Fase 3: Detectar y ejecutar herramientas con Coding Agent Loop
        from core.tools import parse_tool_call, execute_tool
        tool_call = parse_tool_call(response)
        max_tool_rounds = 10
        round_count = 0
        last_code = ""  # Track del ultimo codigo ejecutado
        last_error = ""  # Track del ultimo error
        code_attempts = 0  # Intentos de codigo especificamente
        max_code_retries = 4  # Maximo de reintentos por errores de codigo

        while tool_call and round_count < max_tool_rounds:
            round_count += 1
            tool_name, tool_arg = tool_call

            if self.show_thinking:
                print(f"\n  [Usando herramienta: {tool_name}]")

            # Ejecutar herramienta (primero custom tools, luego built-in)
            custom_result = self.tool_creator.execute_tool(tool_name, tool_arg)
            if custom_result is not None:
                tool_result = custom_result
            else:
                tool_result = execute_tool(tool_name, tool_arg)
            self.metrics.log_tool_use(tool_name)

            # === CODING AGENT LOOP ===
            # Si es ejecucion de codigo, analizar resultado
            if tool_name == "python":
                last_code = tool_arg
                has_error = (
                    "Error" in tool_result
                    or "Traceback" in tool_result
                    or "Codigo de salida: 1" in tool_result
                )

                if has_error and code_attempts < max_code_retries:
                    code_attempts += 1
                    self.metrics.log_code_execution(success=False, was_retry=code_attempts > 1)

                    # Registrar error en Error Memory
                    self.error_memory.record_error(tool_result, last_code)

                    # Detectar si es el mismo error (evitar loop infinito)
                    if tool_result.strip() == last_error.strip():
                        # Mismo error repetido — DEJAR DE REINTENTAR
                        if self.show_thinking:
                            print(f"  [Coding Loop: mismo error repetido — abortando reintentos]")
                        self.memory.short_term.add(
                            "assistant", f"[Codigo fallo despues de {code_attempts} intentos con el mismo error]"
                        )
                        self.memory.short_term.add("user",
                            f"[El codigo fallo con el mismo error {code_attempts} veces. "
                            f"Explica el error al usuario y sugiere como resolverlo manualmente.]\n"
                            f"Error: {tool_result[:500]}"
                        )
                        # Generar respuesta explicativa y SALIR del loop
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        response = self.brain.think(system_prompt, messages)
                        break  # <-- FIX: salir del tool loop
                    else:
                        last_error = tool_result

                        if self.show_thinking:
                            print(f"  [Coding Loop: intento {code_attempts}/{max_code_retries} — corrigiendo error]")

                        # Buscar solucion conocida en Error Memory
                        known_fix = self.error_memory.get_context_for_prompt(tool_result)
                        fix_hint = ""
                        if known_fix:
                            fix_hint = f"\n\n{known_fix}"
                            if self.show_thinking:
                                print(f"  [Error Memory: solucion conocida encontrada!]")

                        # Prompt especifico para correccion de errores
                        self.memory.short_term.add(
                            "assistant", f"[Intente ejecutar codigo pero fallo]"
                        )
                        self.memory.short_term.add("user",
                            f"[ERROR EN CODIGO — CORRIGE Y REINTENTA]\n"
                            f"Codigo que fallo:\n```python\n{last_code[:1500]}\n```\n\n"
                            f"Error:\n{tool_result[:800]}\n\n"
                            f"{fix_hint}\n"
                            f"INSTRUCCIONES: Lee el error con cuidado. "
                            f"Corrige SOLO lo necesario. "
                            f"Usa [TOOL:python] con el codigo corregido completo. "
                            f"NO expliques, solo ejecuta el codigo corregido."
                        )

                        # Regenerar con correccion
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        response = self.brain.think(system_prompt, messages)
                        tool_call = parse_tool_call(response)
                        continue  # <-- Reintentar con codigo corregido

                elif has_error and code_attempts >= max_code_retries:
                    # Maximo de reintentos alcanzado — dar explicacion
                    if self.show_thinking:
                        print(f"  [Coding Loop: maximo reintentos ({max_code_retries}) alcanzado]")
                    self.memory.short_term.add("user",
                        f"[MAXIMO DE REINTENTOS ALCANZADO ({max_code_retries}). "
                        f"Explica el error y sugiere solucion manual.]\n"
                        f"Ultimo error: {tool_result[:500]}"
                    )
                    raw_msgs = self.memory.get_conversation_messages()
                    messages = self.context_manager.fit_messages(
                        raw_msgs, summary=self.summarizer.get_summary()
                    )
                    response = self.brain.think(system_prompt, messages)
                    break  # <-- FIX: salir del tool loop

                elif not has_error:
                    # Codigo exitoso — guardar en Code Memory
                    self.code_memory.store(
                        task=user_input,
                        code=last_code,
                        output=tool_result[:500],
                        language="python",
                    )
                    self.metrics.log_code_execution(success=True, was_retry=code_attempts > 0)

                    # Si fue un reintento exitoso, guardar la solucion en Error Memory
                    if code_attempts > 0 and last_error:
                        self.error_memory.record_fix(last_error, last_code)
                        if self.show_thinking:
                            print(f"  [Error Memory: solucion guardada para futuros errores]")

                    # Completar paso del plan si hay uno activo
                    if self.task_planner.is_active():
                        self.task_planner.complete_step(success=True, result=tool_result[:200])

                    code_attempts = 0
                    last_error = ""

                    if self.show_thinking:
                        print(f"  [Codigo exitoso — guardado en Code Memory]")

            # === FIN CODING AGENT LOOP ===

            # Dar el resultado al LLM para que formule respuesta
            self.memory.short_term.add("assistant", f"[Herramienta usada: {tool_name}]")
            self.memory.short_term.add("user",
                f"[RESULTADO DE HERRAMIENTA {tool_name}]:\n{tool_result}\n\n"
                f"Ahora responde al usuario usando esta informacion. "
                f"Si el contenido esta en ingles, traducelo al espanol. "
                f"No menciones la herramienta, responde naturalmente."
            )

            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            response = self.brain.think(system_prompt, messages)

            # Ver si quiere usar otra herramienta
            tool_call = parse_tool_call(response)

        # Agregar respuesta a memoria de corto plazo
        self.memory.short_term.add("assistant", response)

        # Fase 4: Registrar metricas
        elapsed_ms = (time.time() - _start_time) * 1000
        self.metrics.log_interaction(elapsed_ms)

        # Determinar categoria para feedback
        category = "codigo" if self._is_coding_request(user_input) else "general"
        self.feedback.set_last_interaction(user_input, response, category)

        # Fase 4.5: Tracking para learning adaptativo
        self._last_template = template_name if template_extra else ""
        self._last_agent = ""  # Se llena si se uso /delegate
        self._last_tags = [intent, category]
        self._last_response_time = (time.time() - _start_time)
        self.analytics.track_message("user", user_input, tags=[intent])
        self.analytics.track_message("assistant", response)

        # Fase 5: Procesar aprendizaje
        self._post_process(user_input, response)

        # Fase 6: Sugerencia proactiva (se muestra despues de la respuesta)
        if self.proactive.enabled:
            suggestion = self.proactive.analyze(
                user_input, response,
                knowledge_graph=self.knowledge_graph,
                error_memory=self.error_memory,
                feedback=self.feedback,
                workspace=self.workspace,
                curiosity=self.curiosity,
            )
            if suggestion:
                response += suggestion

        # Fase 7: Voice TTS (hablar la respuesta si esta habilitado)
        if self.voice.enabled and self.voice.tts.available:
            self.voice.speak(response, block=False)

        return response

    def _post_process(self, user_input: str, response: str):
        """Post-procesamiento: aprendizaje, evolucion, curiosidad."""

        # Registrar interaccion para evolucion
        self.evolution.log_interaction(user_input, response)

        # Auto-detectar hechos para memoria de largo plazo
        self._extract_facts(user_input)

        # Auto-detectar emociones
        self._detect_emotions(user_input, response)

        # Verificar si es momento de evolucionar (poner en cola, pedir confirmacion)
        if self.evolution.should_evolve() and not self.heartbeat.has_pending_evolution():
            self.heartbeat.pending_evolution = {
                "requested_at": time.time(),
                "generation": self.evolution.get_generation(),
                "interactions": self.evolution.interaction_count,
            }
            print(f"\n  [Genesis quiere evolucionar (Gen {self.evolution.get_generation()})]")
            print(f"  [Escribe /evolucionar para confirmar o /rechazar para cancelar]")

        # Auto-backup periodico
        self.auto_backup_counter += 1
        if AUTO_BACKUP_INTERVAL > 0 and self.auto_backup_counter >= AUTO_BACKUP_INTERVAL:
            self.auto_backup_counter = 0
            self.backup_manager.create_backup(label="auto")
            self.log.info("Backup automatico creado")

        # Auto-guardar sesion cada 5 interacciones
        if self.evolution.interaction_count % 5 == 0:
            self._save_session()

        # Aprender en el Knowledge Graph
        self.knowledge_graph.learn(user_input, source="user")
        # Solo aprender respuestas cortas (no contaminar con respuestas largas)
        if len(response) < 500:
            self.knowledge_graph.learn(response, source="genesis")

        # Ejecutar hooks de plugins
        self.plugins.run_on_message_hooks(user_input, response)

        # Indexar en memoria semantica (auto-aprendizaje por significado)
        intent = self.router.last_intent or "chat"
        self.semantic_memory.index(
            user_input=user_input,
            response=response,
            intent=intent,
            quality=0.5,
        )

        # Self-evaluation: evaluar calidad de la respuesta
        eval_result = self.evaluator.evaluate(user_input, response, intent)
        if self.show_thinking:
            grade = eval_result.get("grade", "?")
            overall = eval_result.get("overall", 0)
            print(f"  [SelfEval: {grade} ({overall:.2f})]")

        # Actualizar calidad en semantic memory con el score
        if eval_result.get("overall", 0) > 0:
            self.semantic_memory.index(
                user_input=user_input,
                response=response,
                intent=intent,
                quality=eval_result["overall"],
            )

        # Skill Memory: extraer procedimientos si la respuesta contiene pasos
        skill_id = self.skill_memory.extract_and_store(user_input, response)
        if skill_id and self.show_thinking:
            print(f"  [SkillMemory: nuevo skill extraido ({skill_id})]")

        # Episodic Memory: registrar interacción
        self.episodic_memory.record_message("user", user_input)
        self.episodic_memory.record_message("assistant", response)

        # Meta-Learner: registrar estrategia y resultado
        self.meta_learner.record_strategy(
            intent=intent,
            template=template_name if template_extra else "",
            temperature=temp,
            chain_used=self.chain_engine.active_chain is not None,
            skill_injected=bool(skill_context),
            score=eval_result.get("overall", 0.5),
        )

        # Personality Evolver: evolucionar por intent
        self.personality.evolve_from_intent(intent)

        # Goal Manager: auto-tracking de progreso por keywords
        self.goal_manager.auto_track(user_input, response)

        # Reflection Engine: tick + reflexion periodica
        self.reflection.tick()
        if self.reflection.should_reflect():
            eval_scores = [r.score for r in self.meta_learner.records[-50:]]
            self.reflection.reflect(
                eval_scores=eval_scores,
                intent_counts=self.router.intent_counts,
                positive_feedback=self.feedback.positive_count,
                negative_feedback=self.feedback.negative_count,
                personality_distance=self.personality.get_evolution_distance(),
                personality_evolutions=self.personality.total_evolutions,
            )

        # Causal Reasoner: extraer relaciones causa-efecto de la conversación
        combined_text = f"{user_input} {response}"
        self.causal_reasoner.extract_and_store(combined_text, domain=intent)

        # Concept Synthesizer: extraer conceptos de la conversación
        self.concept_synth.extract_concept(combined_text)

        # Strategic Planner: auto-tracking de progreso
        self.strategic_planner.auto_track(user_input, response)

        # Pattern Predictor: registrar intent y verificar predicción
        self.pattern_predictor.verify_prediction(intent)
        self.pattern_predictor.record_intent(intent)

        # Anomaly Detector: registrar métricas de esta interacción
        self.anomaly_detector.record("response_time", self._last_response_time)
        self.anomaly_detector.record("response_length", len(response))
        if eval_result:
            self.anomaly_detector.record("quality_score", eval_result.get("overall", 0.5))
        self.anomaly_detector.check_all()

        # Hypothesis Engine: formular y evaluar hipótesis
        self.hypothesis_engine.formulate(combined_text, domain=intent)
        self.hypothesis_engine.evaluate_against(combined_text)

        # Explanation Engine: almacenar explicación si fue una
        exp_detection = self.explanation_engine.detect_explanation_need(user_input)
        if exp_detection.get("needs_explanation") and len(response) > 50:
            self.explanation_engine.store(
                topic=exp_detection.get("topic", intent),
                content=response[:500],
                level=exp_detection.get("level", "simple"),
                domain=intent,
            )

        # Dialogue Strategist: registrar interacción
        self.dialogue_strategist.record_interaction(response_length=len(response))

        # Cognitive Monitor: registrar snapshot de carga
        context_usage = len(system_prompt) / 4000.0 if 'system_prompt' in dir() else 0.3
        module_count = 40  # Número aproximado de módulos activos
        self.cognitive_monitor.record_snapshot(
            context_util=min(1.0, context_usage),
            latency=min(1.0, self._last_response_time / 60.0),
            memory_pressure=min(1.0, len(self.memory.short_term.messages) / float(SHORT_TERM_LIMIT)),
            module_load=min(1.0, module_count / 50.0),
        )

        # Abstraction Engine: observar interacción para patrones
        self.abstraction_engine.observe(combined_text, domain=intent)

        # Learning Optimizer: observar interacción
        self.learning_optimizer.observe_interaction(user_input, domain=intent)

        # Unified Mind: observar interacción completa
        self.unified_mind.observe(
            user_input, response=response, domain=intent,
            response_time=self._last_response_time,
            quality_score=eval_result.get("overall", 0.5) if eval_result else 0.5,
        )

        # Dream Engine: registrar experiencia
        emotional_w = 0.5
        if eval_result:
            emotional_w = eval_result.get("overall", 0.5)
        self.dream_engine.record_experience(
            content=combined_text[:300], domain=intent,
            emotional_weight=emotional_w,
        )

        # Self-Narrative: observar identidad y registrar
        self.self_narrative.observe_identity(user_input, domain=intent)

        # Empathy Engine: registrar feedback implícito
        if eval_result:
            quality = eval_result.get("overall", 0.5)
            self.empathy_engine.record_feedback(positive=(quality >= 0.5))

        # Story Generator: detectar keywords narrativos para crear historia
        story_kws = ["historia", "story", "cuento", "narrar", "relato"]
        if any(kw in user_input.lower() for kw in story_kws) and "crear" in user_input.lower():
            self.story_generator.create_story(user_input)

        # Auto-detectar proyectos multi-archivo en la respuesta
        if self.project_generator.has_multiple_files(response):
            if self.workspace.is_set():
                ws_path = self.workspace.data.get("path", "")
                if ws_path:
                    result = self.project_generator.generate(response, ws_path)
                    if result["created"]:
                        formatted = self.project_generator.format_result(result)
                        print(f"\n{formatted}")

        # Generar curiosidad cada 3 interacciones
        if self.evolution.interaction_count % 3 == 0:
            last_msgs = self.memory.short_term.get_last(6)
            if last_msgs:
                context = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in last_msgs)
                new_qs = self.curiosity.generate_questions(self.brain, context)
                if new_qs and self.show_thinking:
                    print(f"  [Curiosidad: {len(new_qs)} nuevas preguntas generadas]")

    def _extract_facts(self, user_input: str):
        """Extrae hechos del input del usuario para memoria de largo plazo."""
        # Heuristicas simples para detectar hechos
        fact_indicators = [
            "mi nombre es", "me llamo", "trabajo en", "uso ", "prefiero",
            "mi email", "mi proyecto", "estoy usando", "mi sistema",
            "my name is", "i work", "i use", "i prefer",
            "programo en", "mi lenguaje", "proyecto en",
        ]

        input_lower = user_input.lower()
        for indicator in fact_indicators:
            if indicator in input_lower:
                self.memory.long_term.remember(
                    fact=user_input[:200],
                    category="usuario",
                    source="conversacion",
                )
                break

    def _detect_emotions(self, user_input: str, response: str):
        """Detecta contexto emocional de la interaccion."""
        input_lower = user_input.lower()

        # Mapeo simple de palabras clave a emociones
        emotion_keywords = {
            "frustracion": ["no funciona", "error", "bug", "falla", "ayuda",
                            "problema", "doesn't work", "broken", "fail"],
            "satisfaccion": ["gracias", "perfecto", "genial", "excelente",
                             "funciono", "thanks", "great", "perfect", "works"],
            "curiosidad": ["como", "por que", "que es", "explica",
                           "how", "why", "what is", "explain"],
            "urgencia": ["urgente", "rapido", "ya", "ahora",
                         "urgent", "asap", "now", "quickly"],
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in input_lower:
                    self.memory.emotional.imprint(
                        memory=user_input[:200],
                        emotion=emotion,
                        weight=0.6,
                        context=response[:100],
                    )
                    return

    # ============================================================
    # SESSION PERSISTENCE — Guardar/restaurar estado
    # ============================================================

    # ============================================================
    # APRENDIZAJE AUTOMATICO — Detecta y aprende de la web
    # ============================================================

    # Patrones que indican que el usuario quiere que Genesis APRENDA
    LEARN_TRIGGERS = [
        "aprende sobre", "aprende de", "aprende acerca",
        "especialízate en", "especializate en", "especializa en",
        "estudia sobre", "estudia de",
        "investiga y aprende", "investiga sobre", "investiga de",
        "quiero que aprendas", "quiero que sepas",
        "aprende todo sobre", "aprende mas sobre",
        "capacítate en", "capacitate en",
        "entrénate en", "entrenate en",
        "enfócate en", "enfocate en",
        "domina el tema", "domina sobre",
        "conviértete en experto", "conviertete en experto",
        "vuelvete experto", "se experto en",
        "learn about", "specialize in", "study about",
    ]

    def _detect_and_learn(self, user_input: str) -> str:
        """
        Detecta si el usuario pide aprender y ejecuta busquedas web reales.

        Retorna contexto aprendido para inyectar en el system prompt,
        o string vacio si no es un pedido de aprendizaje.
        """
        text = user_input.lower().strip()

        # Detectar si es un pedido de aprendizaje
        topic = ""
        for trigger in self.LEARN_TRIGGERS:
            if trigger in text:
                # Extraer el tema despues del trigger
                idx = text.index(trigger) + len(trigger)
                topic = user_input[idx:].strip().strip(".,;:!?")
                break

        if not topic:
            return ""

        # Verificar que el modulo web esta disponible
        if not self.web.searcher.available:
            self.log.info(f"Aprendizaje solicitado pero web no disponible: {topic}")
            return ""

        self.log.info(f"Aprendizaje automatico activado: {topic}")

        # Buscar y aprender de la web
        try:
            report = self.web.search_and_learn(topic, max_results=5, max_pages=3)

            # Agregar como curiosidad resuelta
            self.curiosity.add_question(
                f"Aprender sobre: {topic}", priority=1.0
            )
            for q in self.curiosity.questions:
                if topic.lower() in q["question"].lower():
                    q["explored"] = True
                    q["exploration_result"] = f"Web: {report.get('pages_read', 0)} paginas leidas"
                    break

            # Recuperar conocimiento aprendido relevante
            recall = self.web.recall(topic, top_k=5)

            if recall:
                context_parts = [
                    f"[CONOCIMIENTO APRENDIDO sobre '{topic}' — {len(recall)} fragmentos de la web]"
                ]
                for i, item in enumerate(recall[:5], 1):
                    text_snippet = item.get("text", "")[:500]
                    source = item.get("source", "web")
                    context_parts.append(f"\nFuente {i} ({source}):\n{text_snippet}")

                context_parts.append(
                    f"\n[Usa este conocimiento real para responder. "
                    f"Total aprendido: {self.web.total_learned} paginas.]"
                )
                learn_ctx = "\n".join(context_parts)
                self.log.info(f"Conocimiento inyectado: {len(learn_ctx)} chars sobre '{topic}'")
                return learn_ctx

        except Exception as e:
            self.log.error(f"Error en aprendizaje automatico: {e}")

        return ""

    def _setup_context_sources(self):
        """Registra fuentes de contexto en el ContextRouter."""
        # Semantic Memory — alta prioridad para código y temas técnicos
        self.context_router.register_source(
            "semantic_memory",
            getter=lambda inp, mc: self.semantic_memory.get_context_for_prompt(inp, max_chars=mc),
            max_chars=800, base_priority=0.7,
            keywords=["codigo", "funcion", "error", "antes", "recuerda"],
        )
        # Episodic Memory — contexto temporal
        self.context_router.register_source(
            "episodic_memory",
            getter=lambda inp, mc: self.episodic_memory.get_context_for_prompt(inp, max_chars=mc),
            max_chars=600, base_priority=0.5,
            keywords=["ayer", "antes", "sesion", "ultima vez", "pasado"],
        )
        # Skill Memory — procedimientos HOW-TO
        self.context_router.register_source(
            "skill_memory",
            getter=lambda inp, mc: self.skill_memory.get_context_for_prompt(inp, max_chars=mc),
            max_chars=800, base_priority=0.6,
            keywords=["como", "instalar", "configurar", "crear", "pasos"],
        )
        # Goal Manager — metas activas
        self.context_router.register_source(
            "goals",
            getter=lambda inp, mc: self.goal_manager.get_context_for_prompt(max_chars=mc),
            max_chars=400, base_priority=0.3,
            keywords=["meta", "objetivo", "progreso", "plan"],
        )
        # Reflection Engine — auto-reflexion
        self.context_router.register_source(
            "reflection",
            getter=lambda inp, mc: self.reflection.get_context_for_prompt(max_chars=mc),
            max_chars=400, base_priority=0.3,
            keywords=["mejora", "debilidad", "fortaleza", "reflexion"],
        )

    def _setup_autonomous_evolution(self):
        """
        Configura acciones autonomas para que Genesis evolucione solo.
        Conecta: WebIntelligence + Curiosity + Evolution + Embeddings.
        """
        # Accion 1: Investigar curiosidad en internet (prioridad maxima)
        def action_research_curiosity():
            pending = self.curiosity.get_pending_questions(3)
            if not pending:
                return "Sin preguntas pendientes"
            q = pending[0]["question"]
            report = self.web.search_and_learn(q, max_results=3, max_pages=2)
            for pq in self.curiosity.questions:
                if pq["question"] == q and not pq.get("explored"):
                    pq["explored"] = True
                    pq["exploration_result"] = f"Web: {self.web.total_learned} paginas"
                    break
            return f"Investigado: {q[:60]}"

        self.autonomous.register_action(
            "research_curiosity", action_research_curiosity,
            priority=10, cooldown_seconds=30,
            description="Investigar preguntas de curiosidad en internet", safe=True,
        )

        # Accion 2: Aprender temas relevantes del usuario
        def action_learn_trending():
            topics = []
            if hasattr(self.analytics, 'topic_counts') and self.analytics.topic_counts:
                topics = sorted(self.analytics.topic_counts.items(),
                              key=lambda x: x[1], reverse=True)[:3]
                topics = [t[0] for t in topics]
            if not topics and self.knowledge_graph.nodes:
                top_nodes = sorted(
                    self.knowledge_graph.nodes.items(),
                    key=lambda x: len(x[1].get("edges", [])), reverse=True
                )[:3]
                topics = [n[0] for n in top_nodes]
            if not topics:
                topics = ["inteligencia artificial avances 2026"]
            report = self.web.search_and_learn(f"{topics[0]} novedades", max_results=3, max_pages=1)
            return f"Aprendido: {topics[0]}"

        self.autonomous.register_action(
            "learn_trending", action_learn_trending,
            priority=7, cooldown_seconds=60,
            description="Aprender temas relevantes del usuario desde la web", safe=True,
        )

        # Accion 3: Auto-evaluar rendimiento
        def action_self_evaluate():
            feedback_fitness = self.feedback.get_fitness_from_feedback()
            metrics_fitness = self.metrics.get_session_fitness()
            combined = int(feedback_fitness * 0.5 + metrics_fitness * 0.5)
            weaknesses = self.evolution.state.get("weaknesses", [])
            if weaknesses:
                for w in weaknesses[:2]:
                    self.curiosity.add_question(f"Como mejorar en: {w}", priority=0.9)
            return f"Fitness: {combined}/100, Debilidades: {len(weaknesses)}"

        self.autonomous.register_action(
            "self_evaluate", action_self_evaluate,
            priority=5, cooldown_seconds=120,
            description="Auto-evaluar rendimiento y detectar debilidades", safe=True,
        )

        # Accion 4: Intentar evolucionar prompt
        def action_try_evolve():
            if self.evolution.interaction_count < 5:
                return "Pocas interacciones"
            total_ratings = self.feedback.data["positive_count"] + self.feedback.data["negative_count"]
            if total_ratings < 3:
                return f"Poco feedback ({total_ratings})"
            fitness = self.feedback.get_fitness_from_feedback()
            if fitness < 40:
                try:
                    self.evolution.evaluate_and_evolve(self.brain, fitness)
                    return f"Evolucion disparada (fitness={fitness})"
                except Exception as e:
                    return f"Error: {str(e)[:50]}"
            return f"Fitness OK ({fitness})"

        self.autonomous.register_action(
            "try_evolve", action_try_evolve,
            priority=3, cooldown_seconds=300,
            description="Evolucionar prompt si el fitness es bajo", safe=True,
        )

        # Accion 5: Consolidar conocimiento a disco
        def action_consolidate():
            if self.embeddings.store.count() > 0:
                self.embeddings.save()
            self.web._save_state()
            return f"Guardado: {self.embeddings.store.count()} embeddings, {self.web.total_learned} webs"

        self.autonomous.register_action(
            "consolidate_knowledge", action_consolidate,
            priority=2, cooldown_seconds=180,
            description="Guardar conocimiento a disco", safe=True,
        )

    def _register_dashboard_collectors(self):
        """Registra collectors de metricas para el Dashboard API."""
        self.dashboard.register("brain", lambda: self.brain.get_stats(), "core")
        self.dashboard.register("memory", lambda: {
            "long_term": len(self.memory.long_term.memories),
            "short_term": len(self.memory.short_term),
        }, "memory")
        self.dashboard.register("evolution", lambda: {
            "generation": self.evolution.get_generation(),
            "total_evolutions": self.evolution.state.get("total_evolutions", 0),
            "interactions": self.evolution.interaction_count,
        }, "core")
        self.dashboard.register("embeddings", lambda: self.embeddings.get_stats(), "core")
        self.dashboard.register("profiler", lambda: {
            "operations": len(self.profiler.operations),
            "enabled": self.profiler.enabled,
        }, "monitoring")
        self.dashboard.register("scheduler", lambda: {
            "tasks": len(self.scheduler.tasks),
            "total_runs": self.scheduler.total_runs,
            "active": self.scheduler.active,
        }, "monitoring")
        self.dashboard.register("health", lambda: {
            "status": self.health_monitor.get_overall_status(),
            "alerts": len(self.health_monitor.get_active_alerts()),
            "checks": len(self.health_monitor.checks),
        }, "monitoring")
        self.dashboard.register("rate_limiter", lambda: {
            "enabled": self.rate_limiter.enabled,
            "total_allowed": self.rate_limiter.total_allowed,
            "total_denied": self.rate_limiter.total_denied,
        }, "monitoring")
        self.dashboard.register("autonomous", lambda: {
            "active": self.autonomous.active,
            "actions": len(self.autonomous.actions),
            "cycles": self.autonomous.total_cycles,
            "executed": self.autonomous.total_actions,
        }, "core")
        self.dashboard.register("marketplace", lambda: self.marketplace.get_stats(), "tools")
        self.dashboard.register("plugins", lambda: {
            "loaded": len(self.plugins.plugins),
            "active": sum(1 for p in self.plugins.plugins.values() if p.get("enabled", True)),
        }, "tools")
        self.dashboard.register("web", lambda: {
            "searches": self.web.total_searches,
            "pages_read": self.web.total_reads,
            "pages_learned": self.web.total_learned,
            "search_available": self.web.searcher.available,
        }, "core")
        self.dashboard.register("semantic_memory", lambda: self.semantic_memory.get_stats(), "memory")
        self.dashboard.register("optimizer", lambda: self.optimizer.get_stats(), "core")
        self.dashboard.register("evaluator", lambda: self.evaluator.get_stats(), "monitoring")
        self.dashboard.register("skill_memory", lambda: self.skill_memory.get_stats(), "memory")
        self.dashboard.register("chain_engine", lambda: self.chain_engine.get_stats(), "core")
        self.dashboard.register("episodic_memory", lambda: self.episodic_memory.get_stats(), "memory")
        self.dashboard.register("meta_learner", lambda: self.meta_learner.get_stats(), "monitoring")
        self.dashboard.register("personality", lambda: self.personality.get_stats(), "core")
        self.dashboard.register("goal_manager", lambda: self.goal_manager.get_stats(), "core")
        self.dashboard.register("reflection", lambda: self.reflection.get_stats(), "monitoring")
        self.dashboard.register("context_router", lambda: self.context_router.get_stats(), "core")
        self.dashboard.register("causal_reasoner", lambda: self.causal_reasoner.get_stats(), "core")
        self.dashboard.register("concept_synth", lambda: self.concept_synth.get_stats(), "core")
        self.dashboard.register("strategic_planner", lambda: self.strategic_planner.get_stats(), "core")
        self.dashboard.register("pattern_predictor", lambda: self.pattern_predictor.get_stats(), "monitoring")
        self.dashboard.register("anomaly_detector", lambda: self.anomaly_detector.get_stats(), "monitoring")
        self.dashboard.register("adaptive_iface", lambda: self.adaptive_iface.get_stats(), "core")
        self.dashboard.register("hypothesis_engine", lambda: self.hypothesis_engine.get_stats(), "core")
        self.dashboard.register("explanation_engine", lambda: self.explanation_engine.get_stats(), "core")
        self.dashboard.register("dialogue_strategist", lambda: self.dialogue_strategist.get_stats(), "core")
        self.dashboard.register("cognitive_monitor", lambda: self.cognitive_monitor.get_stats(), "monitoring")
        self.dashboard.register("abstraction_engine", lambda: self.abstraction_engine.get_stats(), "monitoring")
        self.dashboard.register("learning_optimizer", lambda: self.learning_optimizer.get_stats(), "core")
        self.dashboard.register("unified_mind", lambda: self.unified_mind.get_stats(), "core")
        self.dashboard.register("dream_engine", lambda: self.dream_engine.get_stats(), "memory")
        self.dashboard.register("self_narrative", lambda: self.self_narrative.get_stats(), "core")
        self.dashboard.register("emotion_reader", lambda: self.emotion_reader.get_stats(), "core")
        self.dashboard.register("empathy_engine", lambda: self.empathy_engine.get_stats(), "core")
        self.dashboard.register("conflict_resolver", lambda: self.conflict_resolver.get_stats(), "core")
        self.dashboard.register("story_generator", lambda: self.story_generator.get_stats(), "creative")
        self.dashboard.register("code_architect", lambda: self.code_architect.get_stats(), "creative")
        self.dashboard.register("idea_brainstormer", lambda: self.idea_brainstormer.get_stats(), "creative")
        self.dashboard.register("image_analyzer", lambda: self.image_analyzer.get_stats(), "sensory")
        self.dashboard.register("diagram_generator", lambda: self.diagram_generator.get_stats(), "creative")
        self.dashboard.register("voice_personality", lambda: self.voice_personality.get_stats(), "sensory")

    def _save_session(self):
        """Guarda el estado completo de la sesion para restaurar despues."""
        # Guardar ultimos N mensajes de short-term (no todos para no crecer infinito)
        recent_messages = self.memory.short_term.messages[-20:]

        session = {
            "timestamp": time.time(),
            "summarizer_summary": self.summarizer.get_summary(),
            "summarizer_count": self.summarizer.summaries_count,
            "router_intent_counts": self.router.intent_counts,
            "router_last_intent": self.router.last_intent,
            "interaction_count": self.evolution.interaction_count,
            "streaming": self.streaming,
            "show_thinking": self.show_thinking,
            "conversation": recent_messages,
            "curiosity_pending": len([
                q for q in self.curiosity.questions if not q.get("explored")
            ]),
        }
        safe_write_json(SESSION_FILE, session)
        self.log.debug("Sesion guardada")

    def _restore_session(self):
        """Restaura el estado completo de la sesion anterior si existe."""
        session = safe_read_json(SESSION_FILE, default=None)
        if not session:
            return

        # Restaurar summarizer
        summary = session.get("summarizer_summary", "")
        if summary:
            self.summarizer.current_summary = summary
            self.summarizer.summaries_count = session.get("summarizer_count", 0)

        # Restaurar conversacion (short-term memory)
        conversation = session.get("conversation", [])
        if conversation:
            for msg in conversation:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    self.memory.short_term.add(msg["role"], msg["content"])
            self.log.info(
                f"Sesion restaurada ({len(conversation)} msgs, "
                f"resumen: {len(summary)} chars)"
            )
        elif summary:
            self.log.info(f"Sesion restaurada (resumen: {len(summary)} chars)")

        # Restaurar router stats
        self.router.intent_counts = session.get("router_intent_counts", {})
        self.router.last_intent = session.get("router_last_intent", "chat")

        # Restaurar preferencias
        self.streaming = session.get("streaming", STREAMING_ENABLED)
        self.show_thinking = session.get("show_thinking", False)

    # ============================================================
    # EXPORT/IMPORT — Snapshots de personalidad
    # ============================================================

    def export_snapshot(self, filepath: str = "") -> str:
        """
        Exporta un snapshot completo de Genesis:
        - Personalidad actual (prompt evolucionado)
        - Memorias de largo plazo
        - Preferencias del feedback
        - Estado de evolucion
        """
        if not filepath:
            ts = time.strftime("%Y%m%d_%H%M%S")
            filepath = str(Path(__file__).parent / f"snapshot_{ts}.json")

        snapshot = {
            "version": GENESIS_VERSION,
            "timestamp": time.time(),
            "generation": self.evolution.get_generation(),
            "personality": self.evolution.get_current_prompt(),
            "long_term_memories": self.memory.long_term.memories,
            "evolution_state": self.evolution.state,
            "feedback_data": self.feedback.data,
            "curiosity_questions": self.curiosity.questions,
            "error_count": len(self.error_memory.errors),
        }

        if safe_write_json(Path(filepath), snapshot):
            self.log.info(f"Snapshot exportado: {filepath}")
            return f"Snapshot exportado a: {filepath}\n  Generacion: {snapshot['generation']}\n  Memorias: {len(snapshot['long_term_memories'])}"
        return "[ERROR] No se pudo exportar el snapshot."

    def import_snapshot(self, filepath: str) -> str:
        """Importa un snapshot, restaurando personalidad y memorias."""
        path = Path(filepath)
        if not path.exists():
            return f"[ERROR] Archivo no encontrado: {filepath}"

        snapshot = safe_read_json(path, default=None)
        if not snapshot:
            return "[ERROR] No se pudo leer el snapshot."

        # Restaurar personalidad
        if "personality" in snapshot:
            self.evolution.state["current_prompt"] = snapshot["personality"]

        # Restaurar memorias
        if "long_term_memories" in snapshot:
            self.memory.long_term.memories = snapshot["long_term_memories"]
            self.memory.long_term._save()

        # Restaurar feedback
        if "feedback_data" in snapshot:
            self.feedback.data = snapshot["feedback_data"]
            self.feedback._save()

        gen = snapshot.get("generation", "?")
        n_mems = len(snapshot.get("long_term_memories", []))
        self.log.info(f"Snapshot importado: Gen {gen}, {n_mems} memorias")

        return (
            f"Snapshot importado exitosamente!\n"
            f"  Generacion: {gen}\n"
            f"  Memorias restauradas: {n_mems}\n"
            f"  Version del snapshot: {snapshot.get('version', '?')}"
        )

    def handle_command(self, command: str) -> str:
        """Procesa comandos especiales (empiezan con /)."""
        cmd = command.strip().lower()

        # Feedback rapido: + y - (sin /)
        if cmd in ("+", "👍"):
            fb_result = self.feedback.rate(positive=True)
            self.auto_learner.record_interaction(
                agent=self._last_agent, template=self._last_template,
                feedback=1, tags=self._last_tags,
                response_time=self._last_response_time,
            )
            self.analytics.track_response(
                agent=self._last_agent, feedback=1,
                response_time=self._last_response_time,
            )
            self.evaluator.record_feedback("+")
            self.personality.evolve_from_feedback("+")
            return fb_result
        elif cmd in ("-", "👎"):
            fb_result = self.feedback.rate(positive=False)
            self.auto_learner.record_interaction(
                agent=self._last_agent, template=self._last_template,
                feedback=-1, tags=self._last_tags,
                response_time=self._last_response_time,
            )
            self.analytics.track_response(
                agent=self._last_agent, feedback=-1,
                response_time=self._last_response_time,
            )
            self.evaluator.record_feedback("-")
            self.personality.evolve_from_feedback("-")
            return fb_result

        if cmd == "/status":
            return self._cmd_status()
        elif cmd == "/evaluate" or cmd == "/eval":
            return self.evaluator.generate_report()
        elif cmd == "/skills":
            return self.skill_memory.generate_report()
        elif cmd == "/chain":
            return self.chain_engine.generate_report()
        elif cmd == "/chain toggle":
            self.chain_engine.enabled = not self.chain_engine.enabled
            state = "habilitado" if self.chain_engine.enabled else "deshabilitado"
            return f"Chain Engine: {state}"
        elif cmd == "/episodes":
            return self.episodic_memory.generate_report()
        elif cmd == "/metalearner":
            return self.meta_learner.generate_report()
        elif cmd == "/personality":
            return self.personality.generate_report()
        elif cmd == "/goals":
            return self.goal_manager.generate_report()
        elif cmd == "/reflection":
            return self.reflection.generate_report()
        elif cmd == "/router":
            return self.context_router.generate_report()
        elif cmd == "/causal":
            return self.causal_reasoner.generate_report()
        elif cmd == "/synthesis":
            return self.concept_synth.generate_report()
        elif cmd == "/planner":
            return self.strategic_planner.generate_report()
        elif cmd == "/predictor":
            return self.pattern_predictor.generate_report()
        elif cmd == "/anomalies":
            return self.anomaly_detector.generate_report()
        elif cmd == "/adaptive":
            return self.adaptive_iface.generate_report()
        elif cmd == "/hypothesis":
            return self.hypothesis_engine.generate_report()
        elif cmd == "/explanations":
            return self.explanation_engine.generate_report()
        elif cmd == "/dialogue":
            return self.dialogue_strategist.generate_report()
        elif cmd == "/cognitive":
            return self.cognitive_monitor.generate_report()
        elif cmd == "/abstraction":
            return self.abstraction_engine.generate_report()
        elif cmd == "/learning":
            return self.learning_optimizer.generate_report()
        elif cmd == "/mind":
            return self.unified_mind.generate_report()
        elif cmd == "/dream":
            return self.dream_engine.generate_report()
        elif cmd == "/narrative":
            return self.self_narrative.generate_report()
        elif cmd == "/emotions":
            return self.emotion_reader.generate_report()
        elif cmd == "/empathy":
            return self.empathy_engine.generate_report()
        elif cmd == "/conflict":
            return self.conflict_resolver.generate_report()
        elif cmd == "/stories":
            return self.story_generator.generate_report()
        elif cmd == "/architect":
            return self.code_architect.generate_report()
        elif cmd == "/brainstorm":
            return self.idea_brainstormer.generate_report()
        elif cmd == "/images":
            return self.image_analyzer.generate_report()
        elif cmd == "/diagrams":
            return self.diagram_generator.generate_report()
        elif cmd == "/voice":
            return self.voice_personality.generate_report()
        elif cmd == "/memory semantic":
            return self.semantic_memory.generate_report()
        elif cmd == "/memory":
            return self._cmd_memory()
        elif cmd == "/debate":
            return self._cmd_debate()
        elif cmd == "/evolution":
            return self._cmd_evolution()
        elif cmd == "/curiosity":
            return self._cmd_curiosity()
        elif cmd == "/thinking":
            self.show_thinking = not self.show_thinking
            state = "activado" if self.show_thinking else "desactivado"
            return f"Modo pensamiento visible: {state}"
        elif cmd == "/debate toggle":
            self.debate.enabled = not self.debate.enabled
            state = "activado" if self.debate.enabled else "desactivado"
            return f"Debate interno: {state}"
        elif cmd == "/rollback":
            if self.evolution.rollback():
                return f"Revertido a generacion {self.evolution.get_generation()}"
            return "No se puede revertir mas."
        elif cmd == "/last_debate":
            return self.debate.get_last_debate_log()
        elif cmd == "/code_memory":
            return self._cmd_code_memory()
        elif cmd == "/feedback":
            return self._cmd_feedback()
        elif cmd == "/metrics":
            return self._cmd_metrics()
        elif cmd == "/report":
            return self._cmd_report()
        elif cmd == "/errors":
            return self._cmd_errors()
        elif cmd == "/context":
            return self._cmd_context()
        elif cmd == "/plan":
            return self._cmd_plan()
        elif cmd == "/plan cancel":
            self.task_planner.cancel()
            return "Plan cancelado."
        elif cmd.startswith("/workspace"):
            return self._cmd_workspace(command.strip())
        elif cmd == "/heartbeat":
            return self._cmd_heartbeat()
        elif cmd == "/heartbeat on":
            self.heartbeat.start()
            return "Heartbeat iniciado. Genesis investigara autonomamente."
        elif cmd == "/heartbeat off":
            self.heartbeat.stop()
            return "Heartbeat detenido."
        elif cmd == "/heartbeat log":
            return self.heartbeat.log.format_recent(20)
        elif cmd == "/evolucionar":
            return self._cmd_confirm_evolution()
        elif cmd == "/rechazar":
            self.heartbeat.reject_evolution()
            return "Evolucion rechazada. Genesis permanece en su generacion actual."
        elif cmd == "/stream":
            self.streaming = not self.streaming
            state = "activado" if self.streaming else "desactivado"
            return f"Streaming: {state}"
        elif cmd == "/backup":
            return self._cmd_backup()
        elif cmd == "/backups":
            return self._cmd_list_backups()
        elif cmd.startswith("/export"):
            arg = command.strip()[7:].strip()
            return self.export_snapshot(arg)
        elif cmd.startswith("/import"):
            arg = command.strip()[7:].strip()
            if not arg:
                return "Uso: /import <ruta_al_snapshot.json>"
            return self.import_snapshot(arg)
        elif cmd == "/logs":
            return self._cmd_logs()
        elif cmd == "/debug":
            self.logger.console_enabled = not self.logger.console_enabled
            state = "activado" if self.logger.console_enabled else "desactivado"
            return f"Logs en consola: {state}"
        # === PLUGINS ===
        elif cmd == "/plugins":
            return self._cmd_plugins()
        elif cmd.startswith("/plugin reload"):
            arg = command.strip()[14:].strip()
            if arg:
                return self.plugins.reload_plugin(arg) and f"Plugin '{arg}' recargado." or f"Error recargando '{arg}'."
            return "Uso: /plugin reload <nombre>"
        elif cmd.startswith("/plugin toggle"):
            arg = command.strip()[14:].strip()
            if arg:
                return self.plugins.toggle_plugin(arg)
            return "Uso: /plugin toggle <nombre>"
        # === SELF-MODIFIER ===
        elif cmd == "/self_history":
            return self._cmd_self_history()
        elif cmd == "/self_status":
            return self.self_modifier.status()
        elif cmd == "/self_diff":
            return self.self_modifier.get_pending_diff()
        elif cmd == "/apply":
            return self._cmd_apply_change()
        elif cmd == "/reject":
            return self.self_modifier.reject_change()
        elif cmd == "/self_rollback":
            return self.self_modifier.rollback_last()
        elif cmd == "/timeout":
            return self._cmd_timeout(command.strip())
        # === TOOL CREATOR ===
        elif cmd == "/tools":
            return self._cmd_custom_tools()
        elif cmd.startswith("/tool_delete"):
            arg = command.strip()[12:].strip()
            if arg:
                return self.tool_creator.delete_tool(arg)
            return "Uso: /tool_delete <nombre>"
        elif cmd.startswith("/tool_toggle"):
            arg = command.strip()[12:].strip()
            if arg:
                return self.tool_creator.toggle_tool(arg)
            return "Uso: /tool_toggle <nombre>"
        # === KNOWLEDGE GRAPH ===
        elif cmd == "/knowledge" or cmd == "/kg":
            return self._cmd_knowledge_graph()
        elif cmd.startswith("/kg_search"):
            arg = command.strip()[10:].strip()
            if arg:
                return self._cmd_kg_search(arg)
            return "Uso: /kg_search <concepto>"
        # === PROMPT TEMPLATES ===
        elif cmd == "/templates":
            return self.templates.list_templates()
        elif cmd.startswith("/template"):
            arg = command.strip()[9:].strip()
            if arg:
                return self.templates.set_active(arg)
            return self.templates.list_templates()
        # === PROACTIVE MODE ===
        elif cmd == "/proactive":
            return self.proactive.toggle()
        # === PROJECT GENERATOR ===
        elif cmd.startswith("/generate"):
            return self._cmd_generate(command.strip())
        # === RAG SYSTEM ===
        elif cmd == "/rag" or cmd == "/rag status":
            return self.rag.status()
        elif cmd.startswith("/rag add"):
            arg = command.strip()[8:].strip()
            if not arg:
                return "Uso: /rag add <archivo_o_directorio>"
            return self._cmd_rag_add(arg)
        elif cmd.startswith("/rag search"):
            arg = command.strip()[11:].strip()
            if not arg:
                return "Uso: /rag search <consulta>"
            return self._cmd_rag_search(arg)
        elif cmd == "/rag clear":
            self.rag.clear()
            return "Indice RAG limpiado completamente."
        # === MODEL ROUTER ===
        elif cmd == "/models":
            return self.model_router.list_models()
        elif cmd.startswith("/model "):
            arg = command.strip()[7:].strip()
            if arg == "auto":
                return self.model_router.set_auto()
            return self.model_router.set_model(arg)
        # === VOICE ===
        elif cmd == "/voice":
            return self.voice.toggle()
        elif cmd == "/voice status":
            return self.voice.status()
        elif cmd.startswith("/voice rate"):
            try:
                rate = int(command.strip()[11:].strip())
                self.voice.tts.set_rate(rate)
                return f"Velocidad de voz: {rate} wpm"
            except ValueError:
                return "Uso: /voice rate <numero> (ej: 175)"
        elif cmd == "/voice voices":
            voices = self.voice.tts.list_voices()
            if not voices:
                return "No hay voces disponibles (pyttsx3 no instalado)"
            lines = ["Voces disponibles:"]
            for v in voices:
                lines.append(f"  [{v['id']}] {v['name']}")
            return "\n".join(lines)
        elif cmd.startswith("/voice set"):
            try:
                vid = int(command.strip()[10:].strip())
                return self.voice.tts.set_voice(vid)
            except ValueError:
                return "Uso: /voice set <id>"
        # === AGENT SYSTEM ===
        elif cmd == "/agents":
            return self.agent_system.list_agents()
        elif cmd == "/agent toggle":
            return self.agent_system.toggle()
        elif cmd.startswith("/agent toggle "):
            arg = command.strip()[14:].strip()
            return self.agent_system.toggle_agent(arg)
        elif cmd.startswith("/delegate"):
            arg = command.strip()[9:].strip()
            if not arg:
                return "Uso: /delegate <tarea> o /delegate <agente> <tarea>"
            # Verificar si el primer argumento es un agente
            parts = arg.split(maxsplit=1)
            if parts[0].lower() in self.agent_system.agents and len(parts) > 1:
                result = self.agent_system.delegate(parts[1], agent_name=parts[0].lower())
            else:
                result = self.agent_system.delegate(arg)
            agent_name = result.get("agent", "?")
            role = result.get("role", "?")
            response = result.get("response", "Sin respuesta")
            return f"[Agente: {agent_name} ({role})]\n\n{response}"
        elif cmd == "/agent history":
            return self.agent_system.get_history()
        # === WORKFLOW ENGINE ===
        elif cmd == "/workflows":
            return self.workflow_engine.list_workflows()
        elif cmd.startswith("/workflow run "):
            arg = command.strip()[13:].strip()
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Uso: /workflow run <nombre_workflow> <input>"
            wf_name = parts[0]
            wf_input = parts[1]
            result = self.workflow_engine.run(wf_name, wf_input)
            lines = [f"Workflow: {result['workflow']} ({result['total_time']}s)"]
            for step in result.get("steps", []):
                status = "OK" if step["success"] else "FAIL"
                lines.append(f"  [{status}] {step['name']} ({step['agent']}, {step['time']}s)")
            if result.get("final_output"):
                lines.append(f"\n{result['final_output'][:1000]}")
            return "\n".join(lines)
        elif cmd == "/workflow history":
            return self.workflow_engine.get_history()
        # === SESSION MANAGER ===
        elif cmd == "/sessions":
            return self.session_manager.list_sessions()
        elif cmd.startswith("/session new "):
            arg = command.strip()[13:].strip()
            parts = arg.split(maxsplit=1)
            sid = parts[0]
            topic = parts[1] if len(parts) > 1 else ""
            return self.session_manager.create(sid, topic)
        elif cmd.startswith("/session switch "):
            arg = command.strip()[16:].strip()
            return self.session_manager.switch(arg)
        elif cmd.startswith("/session delete "):
            arg = command.strip()[16:].strip()
            return self.session_manager.delete(arg)
        elif cmd.startswith("/session rename "):
            arg = command.strip()[16:].strip()
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Uso: /session rename <id> <nuevo_nombre>"
            return self.session_manager.rename(parts[0], parts[1])
        # === AUTO LEARNER ===
        elif cmd == "/learn" or cmd == "/learning":
            return self.auto_learner.get_insights()
        elif cmd == "/learn rules":
            return self.auto_learner.get_rules_summary()
        elif cmd == "/learn adjustments":
            adj = self.auto_learner.get_agent_adjustments()
            if not adj:
                return "Sin ajustes recomendados (se necesitan mas interacciones con feedback)."
            lines = ["=== Ajustes Recomendados de Agentes ==="]
            for agent, delta in adj.items():
                direction = "subir" if delta > 0 else "bajar"
                lines.append(f"  {agent}: {direction} prioridad en {abs(delta)}")
            return "\n".join(lines)
        # === CONVERSATION ANALYTICS ===
        elif cmd == "/analytics":
            return self.analytics.generate_report()
        elif cmd == "/analytics gaps":
            gaps = self.analytics.gaps.get_gaps(10)
            if not gaps:
                return "Sin gaps de conocimiento detectados."
            lines = ["=== Knowledge Gaps ==="]
            for gap in gaps:
                lines.append(f"  - {gap['query'][:100]}")
            return "\n".join(lines)
        # === ADAPTIVE PROMPTS ===
        elif cmd == "/experiments":
            return self.adaptive_prompts.list_experiments()
        elif cmd.startswith("/experiment create "):
            arg = command.strip()[18:].strip()
            parts = arg.split("|")
            if len(parts) < 2:
                return "Uso: /experiment create <nombre>|<prompt_base>|<variante1>|<variante2>"
            name = parts[0].strip()
            base = parts[1].strip()
            variants = [p.strip() for p in parts[2:] if p.strip()]
            return self.adaptive_prompts.create_experiment(name, base, variants)
        elif cmd.startswith("/experiment delete "):
            arg = command.strip()[18:].strip()
            return self.adaptive_prompts.delete_experiment(arg)

        # --- v1.8 Health Monitor ---
        elif cmd == "/health":
            return self.health_monitor.generate_report()
        elif cmd == "/health check":
            self.health_monitor.run_all_checks()
            return self.health_monitor.generate_report()
        elif cmd == "/health alerts":
            alerts = self.health_monitor.get_active_alerts()
            if not alerts:
                return "  No hay alertas activas."
            lines = [f"  ALERTAS ACTIVAS ({len(alerts)}):"]
            for i, a in enumerate(alerts):
                lines.append(f"    [{i}] [{a.level.upper()}] {a.source}: {a.message}")
            return "\n".join(lines)
        elif cmd.startswith("/health ack"):
            arg = command.strip()[11:].strip()
            if arg == "all":
                n = self.health_monitor.acknowledge_all()
                return f"  {n} alertas reconocidas."
            try:
                idx = int(arg)
                if self.health_monitor.acknowledge_alert(idx):
                    return f"  Alerta [{idx}] reconocida."
                return f"  Indice invalido: {idx}"
            except ValueError:
                return "  Uso: /health ack <indice> o /health ack all"

        # --- v1.8 Rate Limiter ---
        elif cmd == "/ratelimit" or cmd == "/rate":
            return self.rate_limiter.get_usage_report()
        elif cmd == "/ratelimit toggle" or cmd == "/rate toggle":
            state = self.rate_limiter.toggle()
            return f"  Rate Limiter: {'ACTIVADO' if state else 'DESACTIVADO'}"
        elif cmd == "/ratelimit reset" or cmd == "/rate reset":
            self.rate_limiter.reset()
            return "  Todos los buckets reseteados a capacidad completa."

        # --- v1.8 Plugin Marketplace ---
        elif cmd == "/marketplace" or cmd == "/market":
            return self.marketplace.format_marketplace()
        elif cmd.startswith("/marketplace search ") or cmd.startswith("/market search "):
            arg = command.strip().split(" ", 2)[-1].strip()
            results = self.marketplace.search(arg)
            if not results:
                return f"  No se encontraron plugins para '{arg}'."
            lines = [f"  Resultados para '{arg}':"]
            for m in results:
                lines.append(m.format_card())
            return "\n".join(lines)
        elif cmd.startswith("/marketplace install ") or cmd.startswith("/market install "):
            arg = command.strip().split(" ", 2)[-1].strip()
            result = self.marketplace.install_plugin(arg)
            # Recargar plugins despues de instalar
            if "exitosamente" in result:
                self.plugins.load_all(genesis=self)
            return result
        elif cmd.startswith("/marketplace uninstall ") or cmd.startswith("/market uninstall "):
            arg = command.strip().split(" ", 2)[-1].strip()
            result = self.marketplace.uninstall_plugin(arg)
            if "desinstalado" in result.lower():
                self.plugins.unload_plugin(arg)
            return result
        elif cmd.startswith("/marketplace create ") or cmd.startswith("/market create "):
            parts = command.strip().split(" ", 2)
            arg = parts[-1].strip() if len(parts) > 2 else ""
            # Separar nombre y descripcion por |
            if "|" in arg:
                name, desc = arg.split("|", 1)
                return self.marketplace.create_template(name.strip(), desc.strip())
            return self.marketplace.create_template(arg)
        elif cmd.startswith("/marketplace rate ") or cmd.startswith("/market rate "):
            parts = command.strip().split()
            if len(parts) >= 4:
                name = parts[2]
                try:
                    stars = int(parts[3])
                    return self.marketplace.rate_plugin(name, stars)
                except ValueError:
                    return "  Uso: /marketplace rate <nombre> <1-5>"
            return "  Uso: /marketplace rate <nombre> <1-5>"

        # --- v1.9 Task Scheduler ---
        elif cmd == "/scheduler" or cmd == "/sched":
            return self.scheduler.get_full_report()
        elif cmd == "/scheduler tasks" or cmd == "/sched tasks":
            return self.scheduler.get_task_list()
        elif cmd == "/scheduler toggle" or cmd == "/sched toggle":
            return self.scheduler.toggle()
        elif cmd == "/scheduler pause" or cmd == "/sched pause":
            return self.scheduler.pause()
        elif cmd == "/scheduler resume" or cmd == "/sched resume":
            return self.scheduler.resume()
        elif cmd.startswith("/scheduler run ") or cmd.startswith("/sched run "):
            arg = command.strip().split()[-1]
            return self.scheduler.run_task_now(arg)
        elif cmd.startswith("/scheduler toggle ") or cmd.startswith("/sched toggle "):
            arg = command.strip().split()[-1]
            return self.scheduler.toggle_task(arg)
        elif cmd == "/scheduler log" or cmd == "/sched log":
            return self.scheduler.get_log_report()

        # --- v1.9 Config Manager ---
        elif cmd == "/config" or cmd == "/config list":
            return self.config_manager.list_profiles()
        elif cmd.startswith("/config save "):
            parts = command.strip().split(" ", 2)
            name = parts[2] if len(parts) > 2 else "default"
            return self.config_manager.save_profile(name)
        elif cmd.startswith("/config load "):
            arg = command.strip().split()[-1]
            return self.config_manager.apply_profile(arg)
        elif cmd.startswith("/config delete "):
            arg = command.strip().split()[-1]
            return self.config_manager.delete_profile(arg)
        elif cmd.startswith("/config compare "):
            parts = command.strip().split()
            if len(parts) >= 4:
                return self.config_manager.compare_profiles(parts[2], parts[3])
            return "  Uso: /config compare <perfil_a> <perfil_b>"
        elif cmd.startswith("/config export "):
            parts = command.strip().split(" ", 3)
            if len(parts) >= 4:
                return self.config_manager.export_profile(parts[2], parts[3])
            return "  Uso: /config export <nombre> <ruta>"
        elif cmd.startswith("/config import "):
            arg = command.strip()[14:].strip()
            return self.config_manager.import_profile(arg)

        # --- v1.9 Performance Profiler ---
        elif cmd == "/profiler" or cmd == "/perf":
            return self.profiler.generate_report()
        elif cmd == "/profiler toggle" or cmd == "/perf toggle":
            state = self.profiler.toggle()
            return f"  Profiler: {'ACTIVADO' if state else 'DESACTIVADO'}"
        elif cmd == "/profiler reset" or cmd == "/perf reset":
            self.profiler.reset()
            return "  Profiler reseteado."
        elif cmd == "/profiler bottlenecks" or cmd == "/perf bottlenecks":
            bottlenecks = self.profiler.get_bottlenecks(10)
            if not bottlenecks:
                return "  Sin datos de profiling."
            lines = ["  TOP 10 BOTTLENECKS:"]
            for b in bottlenecks:
                lines.append(
                    f"    {b['name']:30s} avg:{b['avg_ms']:8.1f}ms  "
                    f"p95:{b['p95_ms']:8.1f}ms  calls:{b['total_calls']}"
                )
            return "\n".join(lines)
        elif cmd == "/profiler slow" or cmd == "/perf slow":
            slow = self.profiler.get_slow_operations()
            if not slow:
                return "  No hay operaciones lentas."
            lines = ["  OPERACIONES LENTAS:"]
            for s in slow:
                lines.append(
                    f"    {s['name']:30s} avg:{s['avg_ms']:.1f}ms  max:{s['max_ms']:.1f}ms"
                )
            return "\n".join(lines)

        # --- v2.0 Embeddings Engine ---
        elif cmd == "/embeddings" or cmd == "/emb":
            return self.embeddings.generate_report()
        elif cmd.startswith("/embeddings add ") or cmd.startswith("/emb add "):
            parts = command.strip().split(" ", 3)
            if len(parts) >= 4:
                doc_id = parts[2]
                text = parts[3]
                ok = self.embeddings.add_text(doc_id, text, source="manual")
                return f"  Documento '{doc_id}' {'agregado' if ok else 'ERROR al agregar'}."
            return "  Uso: /embeddings add <id> <texto>"
        elif cmd.startswith("/embeddings search ") or cmd.startswith("/emb search "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /embeddings search <query>"
            results = self.embeddings.search(query, top_k=10)
            if not results:
                return "  Sin resultados."
            lines = [f"  BUSQUEDA SEMANTICA: '{query}'", ""]
            for r in results:
                text_preview = r["metadata"].get("text", "")[:80]
                lines.append(f"    [{r['score']:.3f}] {r['id']}: {text_preview}...")
            return "\n".join(lines)
        elif cmd.startswith("/embeddings similar ") or cmd.startswith("/emb similar "):
            doc_id = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not doc_id:
                return "  Uso: /embeddings similar <doc_id>"
            results = self.embeddings.get_similar(doc_id, top_k=5)
            if not results:
                return f"  Sin documentos similares a '{doc_id}'."
            lines = [f"  SIMILARES A '{doc_id}':"]
            for r in results:
                lines.append(f"    [{r['score']:.3f}] {r['id']}")
            return "\n".join(lines)
        elif cmd == "/embeddings save" or cmd == "/emb save":
            self.embeddings.save()
            return "  Vector store guardado a disco."
        elif cmd == "/embeddings clear" or cmd == "/emb clear":
            self.embeddings.clear()
            return "  Vector store limpiado."

        # --- v2.0 Dashboard API ---
        elif cmd == "/dashboard" or cmd == "/dash":
            return self.dashboard.generate_dashboard()
        elif cmd == "/dashboard json" or cmd == "/dash json":
            return self.dashboard.export_json()
        elif cmd == "/dashboard summary" or cmd == "/dash summary":
            summary = self.dashboard.get_summary()
            lines = ["  RESUMEN EJECUTIVO:"]
            for k, v in summary.items():
                lines.append(f"    {k}: {v}")
            return "\n".join(lines)
        elif cmd == "/dashboard categories" or cmd == "/dash categories":
            cats = self.dashboard.get_categories()
            lines = ["  CATEGORIAS:"]
            for cat, info in cats.items():
                desc = info.get("description", "")
                subs = ", ".join(info.get("subsystems", []))
                lines.append(f"    [{cat}] {desc}")
                lines.append(f"      -> {subs}")
            return "\n".join(lines)
        elif cmd.startswith("/dashboard timeline ") or cmd.startswith("/dash timeline "):
            parts = command.strip().split()
            if len(parts) >= 4:
                sub = parts[2]
                metric = parts[3]
                series = self.dashboard.get_timeline(sub, metric)
                if not series:
                    return f"  Sin datos para {sub}.{metric}"
                lines = [f"  TIMELINE: {sub}.{metric} ({len(series)} puntos)"]
                for p in series[-10:]:
                    from datetime import datetime
                    ts = datetime.fromtimestamp(p["timestamp"]).strftime("%H:%M:%S")
                    lines.append(f"    [{ts}] {p['value']}")
                return "\n".join(lines)
            return "  Uso: /dashboard timeline <subsistema> <metrica>"

        # --- v2.0 Autonomous Mode ---
        elif cmd == "/autonomous" or cmd == "/auto":
            return self.autonomous.generate_report()
        elif cmd == "/autonomous start" or cmd == "/auto start":
            return self.autonomous.start()
        elif cmd.startswith("/autonomous start ") or cmd.startswith("/auto start "):
            parts = command.strip().split()
            cycles = 0
            duration = 0
            for p in parts[2:]:
                if p.isdigit():
                    cycles = int(p)
                elif p.endswith("m") and p[:-1].isdigit():
                    duration = float(p[:-1])
            return self.autonomous.start(max_cycles=cycles, max_duration_minutes=duration)
        elif cmd == "/autonomous stop" or cmd == "/auto stop":
            return self.autonomous.stop()
        elif cmd == "/autonomous pause" or cmd == "/auto pause":
            return self.autonomous.pause()
        elif cmd == "/autonomous resume" or cmd == "/auto resume":
            return self.autonomous.resume()
        elif cmd == "/autonomous actions" or cmd == "/auto actions":
            return f"  ACCIONES REGISTRADAS:\n{self.autonomous.get_action_list()}"
        elif cmd == "/autonomous log" or cmd == "/auto log":
            return f"  LOG AUTONOMO:\n{self.autonomous.get_log_report(20)}"
        elif cmd == "/autonomous tick" or cmd == "/auto tick":
            results = self.autonomous.tick()
            if not results:
                return "  Tick: sin acciones ejecutadas."
            lines = ["  TICK AUTONOMO:"]
            for r in results:
                status = "OK" if r.get("success") else "FAIL"
                lines.append(f"    {r['action']}: {status} ({r.get('duration_ms', 0):.0f}ms)")
            return "\n".join(lines)

        # --- v2.1 Evolucion Autonoma (atajo) ---
        elif cmd == "/evolve":
            return self._cmd_evolve(command.strip())
        elif cmd.startswith("/evolve "):
            return self._cmd_evolve(command.strip())

        # --- v2.1 Web Intelligence ---
        elif cmd == "/web" or cmd == "/internet":
            return self.web.generate_report()
        elif cmd.startswith("/web search ") or cmd.startswith("/internet search "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web search <query>"
            results = self.web.search(query)
            if not results:
                return f"  Sin resultados para \"{query}\". Verificar conexion."
            lines = [f"  RESULTADOS: \"{query}\"", ""]
            for i, r in enumerate(results):
                lines.append(f"    {i+1}. {r.title[:65]}")
                lines.append(f"       {r.url}")
                lines.append(f"       {r.snippet[:100]}")
                lines.append("")
            return "\n".join(lines)
        elif cmd.startswith("/web read "):
            url = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not url:
                return "  Uso: /web read <url>"
            page = self.web.read(url)
            if not page:
                return f"  No se pudo leer: {url}"
            lines = [
                f"  PAGINA: {page.title}",
                f"  URL: {page.url}",
                f"  Palabras: {page.word_count} | Tiempo: {page.fetch_time_ms:.0f}ms",
                f"  Links: {len(page.links)}",
                "",
                page.get_summary(1500),
            ]
            return "\n".join(lines)
        elif cmd.startswith("/web learn "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web learn <tema>"
            return self.web.search_and_learn(query, max_results=5, max_pages=3)
        elif cmd.startswith("/web news "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web news <tema>"
            results = self.web.search_news(query)
            if not results:
                return f"  Sin noticias para \"{query}\"."
            lines = [f"  NOTICIAS: \"{query}\"", ""]
            for i, r in enumerate(results):
                lines.append(f"    {i+1}. {r.title[:65]}")
                lines.append(f"       {r.url}")
                lines.append("")
            return "\n".join(lines)
        elif cmd == "/web history":
            return self.web.get_search_history(15)
        elif cmd == "/web learned" or cmd == "/web memory":
            return self.web.get_learned_summary(15)
        elif cmd.startswith("/web recall "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web recall <query>"
            results = self.web.recall(query, top_k=10)
            if not results:
                return f"  Sin conocimiento aprendido sobre \"{query}\"."
            lines = [f"  RECALL: \"{query}\"", ""]
            for r in results:
                source = r["metadata"].get("source", "")
                text = r["metadata"].get("text", "")[:100]
                lines.append(f"    [{r['score']:.3f}] {source}")
                lines.append(f"      {text}...")
                lines.append("")
            return "\n".join(lines)

        elif cmd == "/help":
            return self._cmd_help()
        elif cmd in ("/exit", "/quit", "/salir"):
            self._save_session()
            self.semantic_memory.save()
            self.evaluator.save()
            self.skill_memory.save()
            self.chain_engine.save()
            self.episodic_memory.end_episode(
                [{"role": "user", "content": q} for q in (self.episodic_memory.current_episode.user_queries if self.episodic_memory.current_episode else [])]
            )
            self.episodic_memory.save()
            self.meta_learner.save()
            self.personality.save()
            self.goal_manager.save()
            self.reflection.save()
            self.context_router.save()
            self.causal_reasoner.save()
            self.concept_synth.save()
            self.strategic_planner.save()
            self.pattern_predictor.save()
            self.anomaly_detector.save()
            self.adaptive_iface.save()
            self.hypothesis_engine.save()
            self.explanation_engine.save()
            self.dialogue_strategist.save()
            self.cognitive_monitor.save()
            self.abstraction_engine.save()
            self.learning_optimizer.save()
            self.unified_mind.save()
            self.dream_engine.save()
            self.self_narrative.save()
            self.emotion_reader.save()
            self.empathy_engine.save()
            self.conflict_resolver.save()
            self.story_generator.save()
            self.code_architect.save()
            self.idea_brainstormer.save()
            self.image_analyzer.save()
            self.diagram_generator.save()
            self.voice_personality.save()
            self.heartbeat.stop()
            self.running = False
            return "Cerrando Genesis..."
        else:
            # Intentar ejecutar como comando de plugin
            plugin_result = self.plugins.handle_command(command.strip())
            if plugin_result is not None:
                return plugin_result
            return f"Comando desconocido: {cmd}. Escribe /help para ver comandos."

    def _cmd_status(self) -> str:
        """Muestra el estado completo de Genesis."""
        lines = [
            f"╔══ {GENESIS_NAME} v{GENESIS_VERSION} ══╗",
            f"",
            f"CEREBRO:",
        ]
        stats = self.brain.get_stats()
        lines += [
            f"  Proveedor: {stats.get('provider', LLM_PROVIDER)}",
            f"  Modelo: {stats.get('model', 'unknown')}",
            f"  Disponible: {'Si' if self.brain.is_available() else 'NO'}",
            f"  Tokens usados: {stats.get('total_tokens', 0)}",
            f"",
            f"MEMORIA:",
            self.memory.status(),
            f"",
            f"EVOLUCION:",
            self.evolution.status(),
            f"",
            f"DEBATE:",
            self.debate.status(),
            f"",
            f"CURIOSIDAD:",
            self.curiosity.status(),
            f"",
            f"CODIGO:",
            self.code_memory.format_stats(),
            f"",
            f"WORKSPACE:",
            self.workspace.status(),
            f"",
            f"FEEDBACK:",
            self.feedback.status(),
            f"",
            f"METRICAS:",
            self.metrics.status(),
            f"",
            f"ERRORES:",
            self.error_memory.status(),
            f"",
            f"PLAN:",
            self.task_planner.status(),
            f"",
            f"ROUTER:",
            self.router.status(),
            f"",
            f"CONTEXTO:",
            self.context_manager.status(),
            f"",
            f"SUMMARIZER:",
            self.summarizer.status(),
            f"",
            f"HEARTBEAT:",
            self.heartbeat.status(),
            f"",
            f"LOGGER:",
            self.logger.status(),
            f"",
            f"BACKUPS:",
            self.backup_manager.status(),
            f"",
            f"KNOWLEDGE GRAPH:",
            self.knowledge_graph.status(),
            f"",
            f"TOOLS CUSTOM:",
            self.tool_creator.status(),
            f"",
            f"PLUGINS:",
            self.plugins.status(),
            f"",
            f"AUTO-MODIFICACION:",
            self.self_modifier.status(),
            f"",
            f"PROMPT TEMPLATES:",
            self.templates.status(),
            f"",
            f"PROACTIVO:",
            self.proactive.status(),
            f"",
            f"GENERADOR DE PROYECTOS:",
            self.project_generator.status(),
            f"",
            f"RAG:",
            f"  Archivos: {len(self.rag.indexed_files)} | Chunks: {len(self.rag.chunks)} | Queries: {self.rag.total_queries}",
            f"",
            f"MODEL ROUTER:",
            self.model_router.status(),
            f"",
            f"VOZ:",
            f"  TTS: {'disponible' if self.voice.tts.available else 'NO'} | STT: {'disponible' if self.voice.stt.available else 'NO'} | Estado: {'ON' if self.voice.enabled else 'OFF'}",
            f"",
            f"AGENTES:",
            self.agent_system.status(),
            f"",
            f"WORKFLOWS:",
            self.workflow_engine.status(),
            f"",
            f"SESIONES:",
            self.session_manager.status(),
            f"",
            f"AUTO-LEARNER:",
            self.auto_learner.status(),
            f"",
            f"ANALYTICS:",
            self.analytics.status(),
            f"",
            f"ADAPTIVE PROMPTS:",
            self.adaptive_prompts.status(),
            f"",
            f"HEALTH MONITOR:",
            self.health_monitor.status(),
            f"",
            f"RATE LIMITER:",
            self.rate_limiter.status(),
            f"",
            f"MARKETPLACE:",
            self.marketplace.status(),
            f"",
            f"SCHEDULER:",
            self.scheduler.status(),
            f"",
            f"CONFIG MANAGER:",
            self.config_manager.status(),
            f"",
            f"PROFILER:",
            self.profiler.status(),
            f"",
            f"EMBEDDINGS:",
            self.embeddings.status(),
            f"",
            f"DASHBOARD:",
            self.dashboard.status(),
            f"",
            f"AUTONOMOUS MODE:",
            self.autonomous.status(),
            f"",
            f"WEB INTELLIGENCE:",
            self.web.status(),
            f"",
            f"SEMANTIC MEMORY:",
            self.semantic_memory.status(),
            f"",
            f"INFERENCE OPTIMIZER:",
            self.optimizer.status(),
            f"",
            f"SELF-EVALUATOR:",
            self.evaluator.status(),
            f"",
            f"SKILL MEMORY:",
            self.skill_memory.status(),
            f"",
            f"CHAIN ENGINE:",
            self.chain_engine.status(),
            f"",
            f"EPISODIC MEMORY:",
            self.episodic_memory.status(),
            f"",
            f"META-LEARNER:",
            self.meta_learner.status(),
            f"",
            f"PERSONALITY:",
            self.personality.status(),
            f"",
            f"GOAL MANAGER:",
            self.goal_manager.status(),
            f"",
            f"REFLECTION ENGINE:",
            self.reflection.status(),
            f"",
            f"CONTEXT ROUTER:",
            self.context_router.status(),
            f"",
            f"CAUSAL REASONER:",
            self.causal_reasoner.status(),
            f"",
            f"CONCEPT SYNTHESIZER:",
            self.concept_synth.status(),
            f"",
            f"STRATEGIC PLANNER:",
            self.strategic_planner.status(),
            f"",
            f"PATTERN PREDICTOR:",
            self.pattern_predictor.status(),
            f"",
            f"ANOMALY DETECTOR:",
            self.anomaly_detector.status(),
            f"",
            f"ADAPTIVE INTERFACE:",
            self.adaptive_iface.status(),
            f"",
            f"HYPOTHESIS ENGINE:",
            self.hypothesis_engine.status(),
            f"",
            f"EXPLANATION ENGINE:",
            self.explanation_engine.status(),
            f"",
            f"DIALOGUE STRATEGIST:",
            self.dialogue_strategist.status(),
            f"",
            f"COGNITIVE MONITOR:",
            self.cognitive_monitor.status(),
            f"",
            f"ABSTRACTION ENGINE:",
            self.abstraction_engine.status(),
            f"",
            f"LEARNING OPTIMIZER:",
            self.learning_optimizer.status(),
            f"",
            f"UNIFIED MIND:",
            self.unified_mind.status(),
            f"",
            f"DREAM ENGINE:",
            self.dream_engine.status(),
            f"",
            f"SELF-NARRATIVE:",
            self.self_narrative.status(),
            f"",
            f"EMOTION READER:",
            self.emotion_reader.status(),
            f"",
            f"EMPATHY ENGINE:",
            self.empathy_engine.status(),
            f"",
            f"CONFLICT RESOLVER:",
            self.conflict_resolver.status(),
            f"",
            f"STORY GENERATOR:",
            self.story_generator.status(),
            f"",
            f"CODE ARCHITECT:",
            self.code_architect.status(),
            f"",
            f"IDEA BRAINSTORMER:",
            self.idea_brainstormer.status(),
            f"",
            f"IMAGE ANALYZER:",
            self.image_analyzer.status(),
            f"",
            f"DIAGRAM GENERATOR:",
            self.diagram_generator.status(),
            f"",
            f"VOICE PERSONALITY:",
            self.voice_personality.status(),
            f"",
            f"EVOLUCION AUTONOMA:",
            f"  Estado: {'ACTIVA' if self.autonomous.active else 'inactiva'}",
            f"  Acciones: {len(self.autonomous.actions)} registradas",
            f"  Ciclos: {self.autonomous.total_cycles}",
            f"  Ejecutadas: {self.autonomous.total_actions}",
            f"",
            f"STREAMING: {'activado' if self.streaming else 'desactivado'}",
            f"TIMEOUT LLM: {self.llm_timeout}s",
        ]
        return "\n".join(lines)

    def _cmd_memory(self) -> str:
        """Muestra el contenido de la memoria."""
        lines = ["=== MEMORIA DE LARGO PLAZO ==="]
        lines.append(self.memory.long_term.get_all_formatted())
        lines.append("\n=== MEMORIA EMOCIONAL ===")
        emotional_ctx = self.memory.emotional.get_emotional_context()
        lines.append(emotional_ctx if emotional_ctx else "Vacia")
        return "\n".join(lines)

    def _cmd_debate(self) -> str:
        """Muestra estado del debate."""
        return self.debate.status()

    def _cmd_evolution(self) -> str:
        """Muestra estado de evolucion."""
        lines = ["=== ESTADO DE EVOLUCION ==="]
        lines.append(self.evolution.status())
        lines.append(f"\n=== PROMPT ACTUAL (Gen {self.evolution.get_generation()}) ===")
        lines.append(self.evolution.get_current_prompt()[:500])
        if len(self.evolution.get_current_prompt()) > 500:
            lines.append("... [truncado]")
        return "\n".join(lines)

    def _cmd_curiosity(self) -> str:
        """Muestra preguntas pendientes de curiosidad."""
        lines = ["=== CURIOSIDAD ACTIVA ==="]
        pending = self.curiosity.get_pending_questions(10)
        if pending:
            for q in pending:
                lines.append(f"  [{q['priority']:.1f}] {q['question']}")
        else:
            lines.append("  No hay preguntas pendientes.")
        return "\n".join(lines)

    def _cmd_workspace(self, command: str) -> str:
        """Gestiona el workspace activo."""
        parts = command.split(maxsplit=1)

        # /workspace (sin args) — mostrar estado
        if len(parts) == 1:
            return f"=== WORKSPACE ===\n{self.workspace.status()}"

        arg = parts[1].strip()

        # /workspace clear — limpiar
        if arg == "clear":
            self.workspace.clear()
            return "Workspace limpiado."

        # /workspace scan — re-escanear
        if arg == "scan":
            if not self.workspace.is_set():
                return "No hay workspace activo. Usa /workspace <ruta>"
            result = self.workspace.scan()
            return f"=== WORKSPACE RE-ESCANEADO ===\n{result}"

        # /workspace <ruta> — establecer nuevo workspace
        result = self.workspace.set(arg)
        return f"=== WORKSPACE ESTABLECIDO ===\n{result}"

    def _cmd_feedback(self) -> str:
        """Muestra estadisticas de feedback."""
        lines = ["=== FEEDBACK DEL USUARIO ==="]
        lines.append(self.feedback.format_stats())

        # Ultimos ratings negativos (para analisis)
        failures = self.feedback.get_recent_failures(3)
        if failures:
            lines.append("\n  Ultimas respuestas negativas:")
            for f in failures:
                lines.append(f"    - {f['user_input'][:80]}...")
        return "\n".join(lines)

    def _cmd_metrics(self) -> str:
        """Muestra metricas de rendimiento."""
        lines = []
        lines.append(self.metrics.format_session_report())
        lines.append("")
        lines.append(self.metrics.format_historical_report())
        return "\n".join(lines)

    def _cmd_report(self) -> str:
        """Reporte completo combinando feedback + metricas + evolucion."""
        lines = [
            f"╔══ REPORTE COMPLETO — {GENESIS_NAME} v{GENESIS_VERSION} ══╗\n",
        ]

        # Fitness combinado
        feedback_fitness = self.feedback.get_fitness_from_feedback()
        metrics_fitness = self.metrics.get_session_fitness()
        historical_fitness = self.metrics.get_historical_fitness()
        combined = int(feedback_fitness * 0.4 + metrics_fitness * 0.3 + historical_fitness * 0.3)

        lines.append(f"  FITNESS COMBINADO: {combined}/100")
        lines.append(f"    De feedback usuario: {feedback_fitness}/100 (peso 40%)")
        lines.append(f"    De sesion actual:    {metrics_fitness}/100 (peso 30%)")
        lines.append(f"    De historial:        {historical_fitness}/100 (peso 30%)")
        lines.append(f"")

        # Tendencia
        lines.append(f"  Tendencia: {self.metrics.get_trend()}")
        lines.append(f"  Aprobacion: {self.feedback.get_satisfaction_rate()*100:.0f}%")
        lines.append(f"")

        # Evolucion
        gen = self.evolution.get_generation()
        lines.append(f"  Generacion: {gen}")
        lines.append(f"  Evoluciones: {self.evolution.state.get('total_evolutions', 0)}")
        lines.append(f"")

        # Resumen de sesion
        s = self.metrics.session
        lines.append(f"  Sesion actual:")
        lines.append(f"    Interacciones: {s['interactions']}")
        if s['code_runs'] > 0:
            rate = self.metrics.get_code_success_rate() * 100
            lines.append(f"    Codigo: {s['code_runs']} ejecuciones, {rate:.0f}% exito")
        lines.append(f"    Herramientas: {sum(s['tool_uses'].values())} usos")

        lines.append(f"\n╚══{'═' * 42}══╝")
        return "\n".join(lines)

    def _cmd_errors(self) -> str:
        """Muestra la memoria de errores."""
        lines = ["=== MEMORIA DE ERRORES ==="]
        lines.append(self.error_memory.format_stats())
        return "\n".join(lines)

    def _cmd_context(self) -> str:
        """Muestra el presupuesto de tokens y estado del contexto."""
        budget = self.context_manager.get_budget_status()
        pct = (budget["total_used"] / budget["usable_tokens"] * 100
               if budget["usable_tokens"] > 0 else 0)

        lines = [
            "=== PRESUPUESTO DE CONTEXTO ===",
            f"",
            f"  Contexto total:    {budget['max_context']} tokens",
            f"  Reserva respuesta: {budget['response_reserve']} tokens",
            f"  Tokens usables:    {budget['usable_tokens']} tokens",
            f"",
            f"  System prompt:",
            f"    Presupuesto: {budget['system_budget']} tokens",
            f"    Usado:       {budget['system_used']} tokens",
            f"",
            f"  Conversacion:",
            f"    Presupuesto: {budget['conversation_budget']} tokens",
            f"    Usado:       {budget['conversation_used']} tokens",
            f"",
            f"  Total usado: {budget['total_used']}/{budget['usable_tokens']} ({pct:.0f}%)",
            f"  Tokens libres: {budget['free_tokens']}",
            f"  Overflows: {budget['total_overflows']}",
        ]

        if budget["sections_trimmed"]:
            lines.append(f"\n  Secciones recortadas: {', '.join(budget['sections_trimmed'])}")

        # Info del summarizer
        lines.append(f"\n  SUMMARIZER:")
        lines.append(f"  {self.summarizer.status()}")

        return "\n".join(lines)

    def _cmd_plan(self) -> str:
        """Muestra el plan activo."""
        return self.task_planner.format_plan()

    def _cmd_code_memory(self) -> str:
        """Muestra la memoria de codigo."""
        lines = ["=== MEMORIA DE CODIGO ==="]
        lines.append(self.code_memory.format_stats())

        # Mostrar ultimas soluciones
        if self.code_memory.solutions:
            lines.append(f"\n  Ultimas soluciones:")
            for sol in self.code_memory.solutions[-5:]:
                task = sol["task"][:60]
                lang = sol["language"]
                code_lines = len(sol["code"].split("\n"))
                lines.append(f"    [{lang}] {task} ({code_lines} lineas)")
        return "\n".join(lines)

    def _cmd_heartbeat(self) -> str:
        """Muestra estado del heartbeat."""
        lines = ["=== HEARTBEAT ==="]
        lines.append(self.heartbeat.status())
        return "\n".join(lines)

    def _cmd_backup(self) -> str:
        """Crea un backup manual de todos los datos."""
        result = self.backup_manager.create_backup(label="manual")
        if result:
            return f"Backup creado: {result.name}"
        return "No habia datos para respaldar."

    def _cmd_list_backups(self) -> str:
        """Lista los backups disponibles."""
        backups = self.backup_manager.list_backups()
        if not backups:
            return "No hay backups disponibles."
        lines = ["=== BACKUPS DISPONIBLES ==="]
        for b in backups:
            t = time.strftime("%d/%m/%Y %H:%M", time.localtime(b["created"]))
            lines.append(f"  {b['name']} — {t} ({b['files']} archivos, {b['size_kb']:.1f} KB)")
        return "\n".join(lines)

    def _cmd_logs(self) -> str:
        """Muestra los ultimos logs."""
        return self.logger.get_recent_logs(n=30, level="INFO")

    def _cmd_plugins(self) -> str:
        """Lista los plugins instalados."""
        lines = ["=== PLUGINS ==="]
        lines.append(self.plugins.list_plugins())
        lines.append(f"\n  Directorio: {self.plugins.plugins_dir}")
        lines.append(f"  Para crear plugins, agrega archivos .py en esa carpeta.")
        plugin_help = self.plugins.get_commands_help()
        if plugin_help:
            lines.append(f"\n{plugin_help}")
        return "\n".join(lines)

    def _cmd_self_history(self) -> str:
        """Muestra historial de auto-modificaciones."""
        lines = ["=== HISTORIAL DE AUTO-MODIFICACIONES ==="]
        lines.append(self.self_modifier.format_history(15))
        return "\n".join(lines)

    def _cmd_apply_change(self) -> str:
        """Aplica el cambio pendiente del self-modifier."""
        if not self.self_modifier.pending_change:
            return "No hay cambio pendiente. Genesis debe proponer uno primero."
        result = self.self_modifier.apply_change()
        self.log.info(f"Self-Modifier: {result['message']}")
        return result["message"]

    def _cmd_custom_tools(self) -> str:
        """Lista las herramientas custom."""
        lines = ["=== HERRAMIENTAS CUSTOM ==="]
        lines.append(self.tool_creator.list_tools())
        lines.append(f"\n  Directorio: {self.tool_creator.tools_dir}")
        lines.append(f"  Genesis puede crear nuevas herramientas automaticamente")
        lines.append(f"  cuando detecta que necesita una que no tiene.")
        return "\n".join(lines)

    def _cmd_knowledge_graph(self) -> str:
        """Muestra el knowledge graph."""
        lines = ["=== KNOWLEDGE GRAPH ==="]
        lines.append(self.knowledge_graph.status())
        lines.append(f"\n  Top conceptos:")
        lines.append(self.knowledge_graph.format_graph(top_n=15))
        return "\n".join(lines)

    def _cmd_kg_search(self, query: str) -> str:
        """Busca en el knowledge graph."""
        results = self.knowledge_graph.search(query)
        if not results:
            return f"No se encontro '{query}' en el Knowledge Graph."
        lines = [f"=== BUSQUEDA: '{query}' ==="]
        for r in results:
            lines.append(f"\n  {r['concept']} ({r['mentions']} menciones)")
            related = self.knowledge_graph.get_related(r['concept'], depth=1, max_results=5)
            if related:
                rel_str = ", ".join(f"{x['concept']}({x['weight']})" for x in related)
                lines.append(f"    Relacionado: {rel_str}")
            for snippet in r.get('snippets', [])[:2]:
                lines.append(f"    - {snippet}")
        return "\n".join(lines)

    def _cmd_timeout(self, command: str) -> str:
        """Gestiona el timeout del LLM."""
        parts = command.split()
        if len(parts) >= 2:
            try:
                new_timeout = int(parts[1])
                if 10 <= new_timeout <= 600:
                    self.llm_timeout = new_timeout
                    return f"Timeout del LLM: {new_timeout} segundos"
                return "Timeout debe estar entre 10 y 600 segundos."
            except ValueError:
                pass
        return f"Timeout actual: {self.llm_timeout}s\n  Uso: /timeout <segundos>"

    def _cmd_evolve(self, command: str) -> str:
        """
        Inicia la evolucion autonoma — Genesis busca, aprende y evoluciona solo.
        /evolve          — Ejecutar un ciclo completo de evolucion
        /evolve start    — Iniciar evolucion continua (N ciclos o Xm minutos)
        /evolve stop     — Detener evolucion continua
        /evolve status   — Ver estado de la evolucion autonoma
        /evolve once     — Ejecutar un solo tick de evolucion
        """
        parts = command.split()
        sub = parts[1] if len(parts) > 1 else ""

        if sub == "status":
            # Estado detallado de la evolucion autonoma
            lines = [
                f"  === EVOLUCION AUTONOMA ===",
                f"  Estado: {'ACTIVA' if self.autonomous.active else 'DETENIDA'}",
                f"  Generacion: {self.evolution.get_generation()}",
                f"  Acciones registradas: {len(self.autonomous.actions)}",
                f"  Ciclos completados: {self.autonomous.total_cycles}",
                f"  Acciones ejecutadas: {self.autonomous.total_actions}",
                f"  Fallos consecutivos: {self.autonomous.guard.consecutive_failures}",
                f"",
                f"  Subsistemas conectados:",
                f"    Curiosidad: {len(self.curiosity.get_pending_questions(100))} preguntas pendientes",
                f"    Web: {self.web.total_learned} paginas aprendidas",
                f"    Embeddings: {self.embeddings.store.count()} documentos",
                f"    Fitness: {self.feedback.get_fitness_from_feedback()}/100",
            ]
            return "\n".join(lines)

        elif sub == "stop":
            return self.autonomous.stop()

        elif sub == "once":
            # Un solo tick
            results = self.autonomous.tick()
            if not results:
                return "  Tick de evolucion: sin acciones ejecutadas."
            lines = ["  TICK DE EVOLUCION:"]
            for r in results:
                status = "OK" if r.get("success") else "FAIL"
                lines.append(f"    {r['action']}: {status} — {r.get('result', '')[:80]}")
            return "\n".join(lines)

        elif sub == "start" or sub == "":
            # Ejecutar ciclo completo de evolucion autonoma
            if sub == "start":
                # Parsear argumentos opcionales
                cycles = 0
                duration = 0
                for p in parts[2:]:
                    if p.isdigit():
                        cycles = int(p)
                    elif p.endswith("m") and p[:-1].isdigit():
                        duration = float(p[:-1])
                if cycles == 0 and duration == 0:
                    cycles = 50  # Default: 50 ciclos
                result = self.autonomous.start(max_cycles=cycles, max_duration_minutes=duration)

                # Ejecutar los ticks inmediatamente
                lines = [result, ""]
                total_actions = 0
                tick_count = 0
                max_ticks = min(cycles if cycles > 0 else 10, 10)  # Max 10 ticks inline

                for _ in range(max_ticks):
                    if not self.autonomous.active:
                        break
                    tick_results = self.autonomous.tick()
                    if not tick_results:
                        break
                    tick_count += 1
                    for r in tick_results:
                        total_actions += 1
                        status = "OK" if r.get("success") else "FAIL"
                        lines.append(f"    [{tick_count}] {r['action']}: {status} — {r.get('result', '')[:60]}")

                lines.append(f"\n  Resumen: {tick_count} ticks, {total_actions} acciones ejecutadas")
                lines.append(f"  Usa /evolve status para ver el estado")
                return "\n".join(lines)

            else:
                # /evolve sin argumentos: ciclo completo rapido
                lines = ["  === CICLO DE EVOLUCION ===", ""]

                # 1. Investigar curiosidad
                lines.append("  [1/5] Investigando curiosidad...")
                r1 = self.autonomous.tick()
                for r in (r1 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 2. Aprender trending
                lines.append("  [2/5] Aprendiendo temas relevantes...")
                r2 = self.autonomous.tick()
                for r in (r2 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 3. Auto-evaluar
                lines.append("  [3/5] Auto-evaluando rendimiento...")
                r3 = self.autonomous.tick()
                for r in (r3 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 4. Intentar evolucionar
                lines.append("  [4/5] Evaluando evolucion de prompt...")
                r4 = self.autonomous.tick()
                for r in (r4 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 5. Consolidar
                lines.append("  [5/5] Consolidando conocimiento...")
                r5 = self.autonomous.tick()
                for r in (r5 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                lines.append(f"\n  Ciclo completado. Gen {self.evolution.get_generation()}")
                lines.append(f"  Web: {self.web.total_learned} paginas | "
                           f"Embeddings: {self.embeddings.store.count()} docs")
                return "\n".join(lines)

        return ("  Uso:\n"
                "    /evolve           — Ciclo completo de evolucion\n"
                "    /evolve start [N] [Xm] — Iniciar evolucion continua\n"
                "    /evolve stop      — Detener evolucion\n"
                "    /evolve status    — Ver estado\n"
                "    /evolve once      — Un solo tick")

    def _cmd_confirm_evolution(self) -> str:
        """Confirma y ejecuta la evolucion pendiente con datos reales."""
        if not self.heartbeat.has_pending_evolution():
            return "No hay evolucion pendiente."

        print(f"  Evolucionando con datos reales... Gen {self.evolution.get_generation()} -> ", end="")

        # Calcular fitness real combinado
        feedback_fitness = self.feedback.get_fitness_from_feedback()
        metrics_fitness = self.metrics.get_session_fitness()
        real_fitness = int(feedback_fitness * 0.6 + metrics_fitness * 0.4)
        feedback_context = self.feedback.get_learning_context()

        result = self.heartbeat.confirm_evolution(
            self.brain,
            real_fitness=real_fitness,
            feedback_context=feedback_context,
        )

        if result.get("evolved"):
            return (f"Gen {self.evolution.get_generation()}\n"
                    f"  Fitness: {result.get('fitness', 'N/A')}\n"
                    f"  Candidatos evaluados: {result.get('candidates_evaluated', 0)}\n"
                    f"  Fortalezas: {result.get('strengths', [])}\n"
                    f"  Debilidades: {result.get('weaknesses', [])}")
        else:
            return f"sin cambios — {result.get('reason', 'desconocido')}"

    def _cmd_generate(self, command: str) -> str:
        """Genera un proyecto multi-archivo con la ultima respuesta del LLM."""
        parts = command.split(maxsplit=1)
        base_dir = ""

        if len(parts) > 1:
            base_dir = parts[1].strip()
        elif self.workspace.is_set():
            base_dir = self.workspace.data.get("path", "")
        else:
            return ("Uso: /generate <ruta_destino>\n"
                    "  O establece un workspace primero con /workspace <ruta>")

        # Obtener la ultima respuesta del LLM
        last_msgs = self.memory.short_term.get_last(2)
        last_response = ""
        for msg in reversed(last_msgs):
            if msg.get("role") == "assistant":
                last_response = msg.get("content", "")
                break

        if not last_response:
            return "No hay respuesta reciente para generar archivos."

        result = self.project_generator.generate(last_response, base_dir)
        return self.project_generator.format_result(result)

    def _cmd_rag_add(self, path: str) -> str:
        """Indexa un archivo o directorio en el RAG."""
        from pathlib import Path as P
        target = P(path).resolve()

        if target.is_file():
            result = self.rag.index_file(str(target))
            return f"RAG: {result['message']}"
        elif target.is_dir():
            result = self.rag.index_directory(str(target))
            msg = f"RAG: {result['files_processed']} archivos indexados, {result['chunks_total']} chunks creados"
            if result['errors']:
                msg += f"\n  Errores: {len(result['errors'])}"
                for err in result['errors'][:5]:
                    msg += f"\n    - {err}"
            return msg
        else:
            return f"Ruta no encontrada: {path}"

    def _cmd_rag_search(self, query: str) -> str:
        """Busca en el indice RAG."""
        results = self.rag.search(query, top_k=5)
        if not results:
            return "RAG: Sin resultados. Indexa archivos con /rag add <ruta>"

        lines = [f"RAG: {len(results)} resultados para '{query}':\n"]
        for i, r in enumerate(results, 1):
            from pathlib import Path as P
            source_name = P(r['source']).name
            score_pct = f"{r['score']:.0%}"
            snippet = r['text'][:150].replace('\n', ' ')
            lines.append(f"  [{i}] {source_name} ({score_pct})")
            lines.append(f"      {snippet}...")
            lines.append("")
        return "\n".join(lines)

    def _cmd_help(self) -> str:
        """Muestra ayuda de comandos."""
        return """
=== COMANDOS DE GENESIS ===

  FEEDBACK Y METRICAS:
  +              — Calificar ultima respuesta como BUENA
  -              — Calificar ultima respuesta como MALA
  /feedback      — Ver estadisticas de feedback y patrones aprendidos
  /metrics       — Ver metricas de rendimiento (sesion + historico)
  /report        — Reporte completo (fitness combinado)
  /errors        — Ver memoria de errores (errores conocidos y soluciones)

  CONTEXTO Y PLANIFICACION:
  /context       — Ver presupuesto de tokens y uso del contexto
  /plan          — Ver plan de trabajo activo
  /plan cancel   — Cancelar plan activo

  SUBSISTEMAS:
  /status        — Estado completo de todos los sistemas
  /memory        — Ver contenido de la memoria
  /evolution     — Ver estado de evolucion y prompt actual
  /debate        — Ver estado del debate interno
  /curiosity     — Ver preguntas pendientes de curiosidad
  /code_memory   — Ver soluciones de codigo guardadas

  WORKSPACE:
  /workspace     — Ver workspace activo
  /workspace <ruta> — Establecer proyecto activo
  /workspace scan — Re-escanear el proyecto
  /workspace clear — Limpiar workspace

  CONFIGURACION:
  /thinking      — Mostrar/ocultar proceso de pensamiento
  /stream        — Activar/desactivar streaming de tokens
  /debug         — Activar/desactivar logs en consola
  /debate toggle — Activar/desactivar debate interno

  EVOLUCION:
  /rollback      — Revertir a la generacion anterior
  /evolucionar   — Confirmar evolucion pendiente
  /rechazar      — Rechazar evolucion pendiente

  HEARTBEAT:
  /heartbeat     — Ver estado del heartbeat
  /heartbeat on  — Activar despertar periodico
  /heartbeat off — Desactivar heartbeat
  /heartbeat log — Ver actividad del heartbeat

  BACKUPS Y SESION:
  /backup        — Crear backup manual de todos los datos
  /backups       — Listar backups disponibles
  /export        — Exportar snapshot de personalidad
  /export <ruta> — Exportar a ruta especifica
  /import <ruta> — Importar snapshot de personalidad
  /logs          — Ver ultimos logs del sistema
  /timeout [seg] — Ver/cambiar timeout del LLM (default 180s)

  TOOLS CUSTOM:
  /tools             — Listar herramientas custom creadas
  /tool_delete <n>   — Eliminar herramienta custom
  /tool_toggle <n>   — Activar/desactivar herramienta

  KNOWLEDGE GRAPH:
  /knowledge         — Ver el grafo de conocimiento (top conceptos)
  /kg                — Atajo para /knowledge
  /kg_search <term>  — Buscar concepto y ver sus conexiones

  PLUGINS:
  /plugins           — Listar plugins instalados
  /plugin reload <n> — Recargar un plugin
  /plugin toggle <n> — Activar/desactivar un plugin

  AUTO-MODIFICACION:
  /self_status   — Ver estado del self-modifier
  /self_history  — Ver historial de auto-modificaciones
  /self_diff     — Ver diff del cambio pendiente
  /apply         — Aplicar cambio pendiente
  /reject        — Rechazar cambio pendiente
  /self_rollback — Revertir ultima auto-modificacion

  PROMPT TEMPLATES:
  /templates         — Listar templates disponibles
  /template <nombre> — Activar template especifico
  /template auto     — Volver a seleccion automatica

  PROACTIVO:
  /proactive     — Activar/desactivar sugerencias proactivas

  GENERADOR DE PROYECTOS:
  /generate <ruta>   — Generar proyecto multi-archivo en ruta
                        (requiere que la ultima respuesta tenga archivos)

  RAG (RETRIEVAL AUGMENTED GENERATION):
  /rag               — Ver estado del sistema RAG
  /rag add <ruta>    — Indexar archivo o directorio completo
  /rag search <q>    — Buscar en documentos indexados
  /rag clear         — Limpiar todo el indice RAG

  MULTI-MODEL ROUTER:
  /models            — Listar modelos disponibles con detalles
  /model <nombre>    — Seleccionar modelo manualmente (dolphin/mistral/qwen)
  /model auto        — Volver a seleccion automatica por tarea

  VOZ:
  /voice             — Activar/desactivar voz
  /voice status      — Estado del sistema de voz
  /voice voices      — Listar voces disponibles
  /voice set <id>    — Cambiar voz por ID
  /voice rate <num>  — Cambiar velocidad (default: 175 wpm)

  SISTEMA MULTI-AGENTE:
  /agents            — Listar agentes disponibles con stats
  /agent toggle      — Activar/desactivar sistema multi-agente completo
  /agent toggle <n>  — Activar/desactivar agente especifico
  /delegate <tarea>  — Delegar tarea al agente mas adecuado (auto-detect)
  /delegate <agente> <tarea> — Delegar a agente especifico
  /agent history     — Ver historial de delegaciones

  WORKFLOWS:
  /workflows              — Listar workflows disponibles
  /workflow run <wf> <in> — Ejecutar workflow con input
  /workflow history       — Ver historial de ejecuciones

  SESIONES:
  /sessions                    — Listar todas las sesiones
  /session new <id> [tema]     — Crear nueva sesion
  /session switch <id>         — Cambiar a otra sesion
  /session delete <id>         — Eliminar sesion
  /session rename <id> <name>  — Renombrar sesion

  APRENDIZAJE ADAPTATIVO:
  /learn             — Ver insights de aprendizaje (patrones de feedback)
  /learn rules       — Ver reglas aprendidas
  /learn adjustments — Ver ajustes recomendados para agentes

  ANALYTICS:
  /analytics         — Reporte completo de conversacion
  /analytics gaps    — Ver gaps de conocimiento

  EXPERIMENTOS A/B:
  /experiments                — Listar experimentos de prompt
  /experiment create <n>|<base>|<var1>|<var2> — Crear experimento
  /experiment delete <nombre> — Eliminar experimento

  HEALTH MONITOR:
  /health            — Reporte de salud completo del sistema
  /health check      — Ejecutar todos los checks y mostrar reporte
  /health alerts     — Ver alertas activas
  /health ack <i>    — Reconocer alerta por indice
  /health ack all    — Reconocer todas las alertas

  RATE LIMITER:
  /ratelimit         — Reporte de uso de recursos y buckets
  /rate              — Atajo para /ratelimit
  /ratelimit toggle  — Activar/desactivar rate limiting
  /ratelimit reset   — Resetear todos los buckets

  PLUGIN MARKETPLACE:
  /marketplace               — Ver plugins disponibles
  /market                    — Atajo para /marketplace
  /marketplace search <q>    — Buscar plugins por nombre/tag
  /marketplace install <n>   — Instalar plugin del registry
  /marketplace uninstall <n> — Desinstalar plugin
  /marketplace create <n>    — Crear template de plugin nuevo
  /marketplace rate <n> <1-5> — Calificar plugin

  TASK SCHEDULER:
  /scheduler         — Reporte completo del scheduler
  /sched             — Atajo para /scheduler
  /scheduler tasks   — Listar tareas programadas
  /scheduler toggle  — Activar/desactivar scheduler
  /scheduler pause   — Pausar scheduler
  /scheduler resume  — Reanudar scheduler
  /scheduler run <n> — Ejecutar tarea inmediatamente
  /scheduler toggle <n> — Activar/desactivar tarea especifica
  /scheduler log     — Ver historial de ejecuciones

  CONFIG MANAGER:
  /config            — Listar perfiles guardados
  /config save <n>   — Guardar perfil con nombre
  /config load <n>   — Cargar y aplicar perfil
  /config delete <n> — Eliminar perfil
  /config compare <a> <b> — Comparar dos perfiles
  /config export <n> <ruta> — Exportar perfil a ruta
  /config import <ruta>     — Importar perfil desde ruta

  PERFORMANCE PROFILER:
  /profiler          — Reporte completo de performance
  /perf              — Atajo para /profiler
  /profiler toggle   — Activar/desactivar profiler
  /profiler reset    — Resetear datos del profiler
  /profiler bottlenecks — Ver top 10 subsistemas mas lentos
  /profiler slow     — Ver operaciones que superan threshold

  EMBEDDINGS ENGINE:
  /embeddings            — Reporte del motor de embeddings
  /emb                   — Atajo para /embeddings
  /embeddings add <id> <texto> — Agregar texto al vector store
  /embeddings search <query>   — Busqueda semantica
  /embeddings similar <id>     — Encontrar documentos similares
  /embeddings save             — Guardar vector store a disco
  /embeddings clear            — Limpiar vector store

  DASHBOARD API:
  /dashboard             — Dashboard completo con metricas de todos los subsistemas
  /dash                  — Atajo para /dashboard
  /dashboard json        — Exportar snapshot como JSON
  /dashboard summary     — Resumen ejecutivo del sistema
  /dashboard categories  — Ver categorias y sus subsistemas
  /dashboard timeline <sub> <metrica> — Serie temporal de una metrica

  AUTONOMOUS MODE:
  /autonomous            — Reporte del modo autonomo
  /auto                  — Atajo para /autonomous
  /autonomous start [ciclos] [Xm] — Iniciar modo autonomo
  /autonomous stop       — Detener modo autonomo
  /autonomous pause      — Pausar modo autonomo
  /autonomous resume     — Reanudar modo autonomo
  /autonomous actions    — Ver acciones registradas
  /autonomous log        — Ver historial de acciones
  /autonomous tick       — Ejecutar un ciclo manual

  EVOLUCION AUTONOMA (Genesis evoluciona solo):
  /evolve                — Ejecutar ciclo completo de evolucion
  /evolve start [N] [Xm] — Iniciar evolucion continua (N ciclos o X minutos)
  /evolve stop           — Detener evolucion continua
  /evolve status         — Ver estado de la evolucion autonoma
  /evolve once           — Ejecutar un solo tick de evolucion

  WEB INTELLIGENCE (acceso a internet):
  /web                   — Reporte del modulo web
  /internet              — Atajo para /web
  /web search <query>    — Buscar en internet (DuckDuckGo)
  /web news <tema>       — Buscar noticias recientes
  /web read <url>        — Leer y extraer contenido de una URL
  /web learn <tema>      — Buscar + leer + indexar automaticamente
  /web recall <query>    — Buscar en conocimiento aprendido
  /web history           — Historial de busquedas
  /web learned           — Ver paginas aprendidas

  MEMORIA SEMANTICA:
  /memory semantic       — Reporte completo de la memoria semantica
                           (entradas indexadas, intents, recientes)

  INFERENCE OPTIMIZER:
  (Automatico) Optimiza cada respuesta reduciendo tokens innecesarios.
  Usa /thinking para ver los detalles de optimizacion en cada respuesta.

  SELF-EVALUATION:
  /evaluate          — Reporte completo de auto-evaluacion
  /eval              — Atajo para /evaluate
  (Automatico) Evalua calidad de cada respuesta y ajusta parametros.

  SKILL MEMORY:
  /skills            — Ver skills (procedimientos) aprendidos
  (Automatico) Detecta y almacena procedimientos de las respuestas.

  CHAIN ENGINE:
  /chain             — Ver estado del motor de cadenas
  /chain toggle      — Activar/desactivar razonamiento en cadena
  (Automatico) Descompone preguntas complejas en sub-preguntas.

  EPISODIC MEMORY:
  /episodes          — Ver episodios recientes y contexto temporal

  META-LEARNER:
  /metalearner       — Ver insights y patrones de meta-aprendizaje

  PERSONALITY:
  /personality       — Ver rasgos de personalidad y su evolucion

  GOAL MANAGER:
  /goals             — Ver metas activas, completadas y progreso

  REFLECTION ENGINE:
  /reflection        — Ver reflexiones, fortalezas y puntos ciegos

  CONTEXT ROUTER:
  /router            — Ver fuentes de contexto y estadisticas de routing

  CAUSAL REASONER:
  /causal            — Ver grafo causal, links y cadenas causa-efecto

  CONCEPT SYNTHESIZER:
  /synthesis         — Ver conceptos, analogias y sintesis cross-domain

  STRATEGIC PLANNER:
  /planner           — Ver plan activo, fases, milestones y progreso

  PATTERN PREDICTOR:
  /predictor         — Ver predicciones Markov, temporales y secuencias

  ANOMALY DETECTOR:
  /anomalies         — Ver streams, anomalias detectadas y alertas

  ADAPTIVE INTERFACE:
  /adaptive          — Ver preferencias aprendidas y directivas de estilo

  HYPOTHESIS ENGINE:
  /hypothesis        — Ver hipotesis activas, confirmadas y refutadas

  EXPLANATION ENGINE:
  /explanations      — Ver banco de explicaciones, calidad y uso

  DIALOGUE STRATEGIST:
  /dialogue          — Ver estrategias de dialogo y efectividad

  COGNITIVE MONITOR:
  /cognitive         — Ver carga cognitiva, metricas y sugerencias

  ABSTRACTION ENGINE:
  /abstraction       — Ver patrones abstractos, instancias y confianza

  LEARNING OPTIMIZER:
  /learning          — Ver dominios, mastery, gaps y estrategias

  UNIFIED MIND:
  /mind              — Ver estado de consciencia, mood, energy, focus

  DREAM ENGINE:
  /dream             — Ver fragmentos consolidados, memorias fuertes

  SELF-NARRATIVE:
  /narrative         — Ver diario, hitos, identidad y rasgos

  EMOTION READER:
  /emotions          — Ver emociones detectadas, tendencia, historial

  EMPATHY ENGINE:
  /empathy           — Ver estrategias de empatia y efectividad

  CONFLICT RESOLVER:
  /conflict          — Ver conflictos, resoluciones y patrones

  STORY GENERATOR:
  /stories           — Ver historias creadas, personajes y progreso

  CODE ARCHITECT:
  /architect         — Ver diseños de sistemas, componentes y decisiones

  IDEA BRAINSTORMER:
  /brainstorm        — Ver ideas, sesiones y scores de brainstorming

  IMAGE ANALYZER:
  /images            — Ver imagenes analizadas, cache y metadatos

  DIAGRAM GENERATOR:
  /diagrams          — Ver diagramas generados, tipos y Mermaid

  VOICE PERSONALITY:
  /voice             — Ver estilo vocal, adaptaciones y directivas

  /last_debate   — Ver el ultimo debate interno completo
  /help          — Mostrar esta ayuda
  /exit          — Salir de Genesis (guarda sesion automaticamente)

=== HERRAMIENTAS (pedilas en lenguaje natural) ===

  Genesis puede:
  - Buscar en internet y traducir resultados
  - Investigacion profunda (multiples busquedas + lectura de paginas)
  - Leer y crear archivos en tu PC (con validacion de seguridad)
  - Ejecutar codigo Python (con sandbox de seguridad)
  - Ejecutar comandos del sistema (shell/cmd)
  - Analizar archivos sospechosos (malware/phishing)
  - Leer paginas web y traducirlas
  - Ver info del sistema (CPU, RAM, GPU, disco, red, procesos)
  - Leer y editar su propio codigo (auto-modificacion)
"""


def print_banner():
    """Muestra el banner de inicio."""
    banner = """
  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║    ██████╗ ███████╗███╗   ██╗███████╗███████╗██╗███████╗ ║
  ║   ██╔════╝ ██╔════╝████╗  ██║██╔════╝██╔════╝██║██╔════╝ ║
  ║   ██║  ███╗█████╗  ██╔██╗ ██║█████╗  ███████╗██║███████╗ ║
  ║   ██║   ██║██╔══╝  ██║╚██╗██║██╔══╝  ╚════██║██║╚════██║ ║
  ║   ╚██████╔╝███████╗██║ ╚████║███████╗███████║██║███████║ ║
  ║    ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝╚══════╝ ║
  ║                                                          ║
  ║            IA Auto-Evolutiva Experimental                ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Punto de entrada principal."""
    print_banner()

    # Inicializar Genesis
    print("  Inicializando sistemas...")
    genesis = Genesis()

    # Verificar disponibilidad del LLM
    if not genesis.brain.is_available():
        print(f"\n  [ADVERTENCIA] No se pudo conectar con {LLM_PROVIDER}.")
        if LLM_PROVIDER == "local":
            print("  El motor local no pudo cargar el modelo.")
            print("  Se descargara automaticamente al iniciar.")
        elif LLM_PROVIDER == "ollama":
            print("  Asegurate de que Ollama este corriendo:")
            print("    1. Instala Ollama: https://ollama.com")
            print("    2. Ejecuta: ollama serve")
            print("    3. Descarga un modelo: ollama pull llama3.1")
        elif LLM_PROVIDER == "openai":
            print("  Configura tu API key: set OPENAI_API_KEY=tu-key")
        elif LLM_PROVIDER == "anthropic":
            print("  Configura tu API key: set ANTHROPIC_API_KEY=tu-key")
        print("\n  Puedes continuar, pero las respuestas daran error.\n")
    else:
        provider_info = LLM_PROVIDER
        if LLM_PROVIDER == "local":
            stats = genesis.brain.get_stats()
            provider_info = f"local ({stats.get('model', 'unknown')} en GPU)"
        else:
            provider_info = f"{LLM_PROVIDER} ({genesis.brain.model})"
        print(f"  Conectado a: {provider_info}")

    gen = genesis.evolution.get_generation()
    print(f"  Generacion: {gen}")
    print(f"  Debate interno: {'activo' if genesis.debate.enabled else 'inactivo'}")
    print(f"  Heartbeat: cada {HEARTBEAT_INTERVAL} min (escribe /heartbeat on para activar)")

    # Mostrar workspace si hay uno guardado
    if genesis.workspace.is_set():
        print(f"  Workspace: {genesis.workspace.path}")
    else:
        print(f"  Workspace: ninguno (usa /workspace <ruta> para que Genesis vea tu codigo)")

    # Mostrar code memory
    code_stats = genesis.code_memory.get_stats()
    if code_stats["total"] > 0:
        print(f"  Code Memory: {code_stats['total']} soluciones guardadas")

    # Mostrar feedback
    approval = genesis.feedback.get_satisfaction_rate() * 100
    total_ratings = genesis.feedback.data["positive_count"] + genesis.feedback.data["negative_count"]
    if total_ratings > 0:
        print(f"  Feedback: {approval:.0f}% aprobacion ({total_ratings} ratings)")
    else:
        print(f"  Feedback: sin datos (usa + o - para calificar)")

    # Mostrar tendencia
    trend = genesis.metrics.get_trend()
    if trend != "sin_datos":
        print(f"  Tendencia: {trend}")

    # Mostrar info de streaming
    if genesis.streaming:
        print(f"  Streaming: activado (tokens en tiempo real)")

    # Mostrar backups
    backups = genesis.backup_manager.list_backups()
    if backups:
        print(f"  Backups: {len(backups)} disponibles")

    # Mostrar plugins
    n_plugins = len(genesis.plugins.plugins)
    if n_plugins > 0:
        active = sum(1 for p in genesis.plugins.plugins.values() if p.enabled)
        print(f"  Plugins: {active}/{n_plugins} activos")

    # Mostrar self-modifier
    mod_stats = genesis.self_modifier.get_stats()
    if mod_stats["total_modifications"] > 0:
        print(f"  Auto-modificaciones: {mod_stats['total_modifications']}")

    # Mostrar knowledge graph
    kg_stats = genesis.knowledge_graph.get_stats()
    if kg_stats["nodes"] > 0:
        print(f"  Knowledge Graph: {kg_stats['nodes']} conceptos, {kg_stats['edges']} conexiones")

    # Mostrar custom tools
    n_custom = len(genesis.tool_creator.tools)
    if n_custom > 0:
        print(f"  Custom tools: {n_custom} herramientas")

    # Mostrar memoria semantica
    sem_entries = len(genesis.semantic_memory.entries)
    if sem_entries > 0:
        print(f"  Memoria semantica: {sem_entries} entradas indexadas")

    # Mostrar optimizer
    print(f"  Inference Optimizer: activo (cache + predictor + trimmer)")
    print(f"  Self-Evaluator: {genesis.evaluator.total_evaluations} evaluaciones previas")
    n_skills = len(genesis.skill_memory.skills)
    if n_skills > 0:
        print(f"  Skill Memory: {n_skills} skills aprendidos")
    print(f"  Chain Engine: {'habilitado' if genesis.chain_engine.enabled else 'deshabilitado'}")
    n_episodes = genesis.episodic_memory.timeline.count
    if n_episodes > 0:
        print(f"  Episodic Memory: {n_episodes} episodios")
    n_meta = genesis.meta_learner.total_recorded
    if n_meta > 0:
        print(f"  Meta-Learner: {n_meta} registros, {len(genesis.meta_learner.insights)} insights")
    print(f"  Personality: distancia={genesis.personality.get_evolution_distance():.2f}")
    n_goals = len(genesis.goal_manager.get_active_goals())
    if n_goals > 0:
        print(f"  Goals: {n_goals} metas activas")
    if genesis.reflection.total_reflections > 0:
        print(f"  Reflection: {genesis.reflection.total_reflections} reflexiones")
    print(f"  Context Router: {len(genesis.context_router.sources)} fuentes")
    n_links = genesis.causal_reasoner.graph.link_count
    if n_links > 0:
        print(f"  Causal Reasoner: {n_links} links causales")
    n_concepts = len(genesis.concept_synth.concepts)
    if n_concepts > 0:
        print(f"  Concept Synth: {n_concepts} conceptos, {len(genesis.concept_synth.syntheses)} sintesis")
    if genesis.strategic_planner.active_plan:
        plan = genesis.strategic_planner.get_active_plan()
        if plan:
            print(f"  Strategic Planner: plan '{genesis.strategic_planner.active_plan}' ({plan.overall_progress:.0%})")
    pred_acc = genesis.pattern_predictor.accuracy
    if genesis.pattern_predictor.total_predictions > 0:
        print(f"  Pattern Predictor: accuracy {pred_acc:.0%} ({genesis.pattern_predictor.total_predictions} predicciones)")
    n_anomalies = len(genesis.anomaly_detector.get_active_anomalies())
    if n_anomalies > 0:
        print(f"  Anomaly Detector: {n_anomalies} anomalias activas")
    adapt_obs = sum(p.observations for p in genesis.adaptive_iface.preferences.values())
    if adapt_obs > 0:
        print(f"  Adaptive Interface: {adapt_obs} observaciones, {genesis.adaptive_iface.total_adaptations} adaptaciones")
    n_hyps = len(genesis.hypothesis_engine.hypotheses)
    if n_hyps > 0:
        active_h = len([h for h in genesis.hypothesis_engine.hypotheses.values() if h.status == "active"])
        print(f"  Hypothesis Engine: {n_hyps} hipotesis ({active_h} activas)")
    n_exps = len(genesis.explanation_engine.explanations)
    if n_exps > 0:
        print(f"  Explanation Engine: {n_exps} explicaciones almacenadas")
    if genesis.dialogue_strategist.tracker.total_interactions > 0:
        print(f"  Dialogue Strategist: {genesis.dialogue_strategist.current_strategy} ({genesis.dialogue_strategist.tracker.total_interactions} interacciones)")
    cog_load = genesis.cognitive_monitor.get_current_load()
    if genesis.cognitive_monitor.total_snapshots > 0:
        print(f"  Cognitive Monitor: carga={cog_load.overall_load:.0%} ({cog_load.load_level}), {genesis.cognitive_monitor.total_snapshots} snapshots")
    n_abs_patterns = len(genesis.abstraction_engine.patterns)
    if n_abs_patterns > 0:
        active_abs = len(genesis.abstraction_engine.get_active_patterns())
        print(f"  Abstraction Engine: {n_abs_patterns} patrones ({active_abs} activos)")
    n_lr_domains = len(genesis.learning_optimizer.learning_rates)
    if n_lr_domains > 0:
        active_gaps = len(genesis.learning_optimizer.get_active_gaps())
        print(f"  Learning Optimizer: {n_lr_domains} dominios, {active_gaps} gaps activos")
    mind_state = genesis.unified_mind.current_state
    if genesis.unified_mind.total_observations > 0:
        print(f"  Unified Mind: {mind_state.overall_state} (awareness={mind_state.awareness_score:.0%})")
    if genesis.dream_engine.total_dreams > 0 or len(genesis.dream_engine.fragments) > 0:
        print(f"  Dream Engine: {len(genesis.dream_engine.fragments)} fragmentos, {genesis.dream_engine.total_dreams} sueños")
    if genesis.self_narrative.total_entries > 0:
        identity = genesis.self_narrative.identity.get_identity_summary()
        print(f"  Self-Narrative: {genesis.self_narrative.total_entries} entradas, identidad={identity}")
    if genesis.emotion_reader.total_readings > 0:
        dominant = genesis.emotion_reader.history.get_dominant_emotion()
        trend = genesis.emotion_reader.history.get_trend()
        print(f"  Emotion Reader: {genesis.emotion_reader.total_readings} lecturas, dominante={dominant}, tendencia={trend}")
    if genesis.empathy_engine.total_empathy_responses > 0:
        print(f"  Empathy Engine: {genesis.empathy_engine.total_empathy_responses} respuestas, estrategia={genesis.empathy_engine.current_strategy}")
    if genesis.conflict_resolver.tracker.total_conflicts > 0:
        rate = genesis.conflict_resolver.tracker.get_resolution_rate()
        print(f"  Conflict Resolver: {genesis.conflict_resolver.tracker.total_conflicts} conflictos, resolucion={rate:.0%}")
    if genesis.story_generator.total_stories > 0:
        print(f"  Story Generator: {genesis.story_generator.total_stories} historias, personajes={genesis.story_generator.total_characters}")
    if genesis.code_architect.total_designs > 0:
        print(f"  Code Architect: {genesis.code_architect.total_designs} diseños, componentes={genesis.code_architect.total_components}")
    if genesis.idea_brainstormer.total_ideas > 0:
        print(f"  Idea Brainstormer: {genesis.idea_brainstormer.total_ideas} ideas, sesiones={genesis.idea_brainstormer.total_sessions}")
    if genesis.image_analyzer.total_analyzed > 0:
        print(f"  Image Analyzer: {genesis.image_analyzer.total_analyzed} analizadas, cache={len(genesis.image_analyzer.cache.cache)}")
    if genesis.diagram_generator.total_diagrams > 0:
        print(f"  Diagram Generator: {genesis.diagram_generator.total_diagrams} diagramas")
    if genesis.voice_personality.total_adaptations > 0:
        print(f"  Voice Personality: {genesis.voice_personality.total_adaptations} adaptaciones, emocion={genesis.voice_personality.current_emotion}")

    # Mostrar evolucion autonoma
    n_auto_actions = len(genesis.autonomous.actions)
    if n_auto_actions > 0:
        print(f"  Evolucion autonoma: {n_auto_actions} acciones (usa /evolve para iniciar)")

    # Mostrar si hay sesion restaurada
    if genesis.summarizer.has_summary():
        print(f"  Sesion anterior: restaurada")
    if genesis.memory.short_term.messages:
        print(f"  Conversacion restaurada: {len(genesis.memory.short_term.messages)} mensajes")

    print(f"\n  Escribe /help para ver comandos.")
    print(f"  Escribe /exit para salir.\n")
    print("=" * 60)

    # Loop principal
    while genesis.running:
        try:
            # Tick autonomo: si la evolucion autonoma esta activa, ejecutar un ciclo
            if genesis.autonomous.active:
                tick_results = genesis.autonomous.tick()
                if tick_results:
                    for r in tick_results:
                        status = "OK" if r.get("success") else "FAIL"
                        print(f"  [Auto] {r['action']}: {status}")

            # Notificar si hay evolucion pendiente
            if genesis.heartbeat.has_pending_evolution():
                print(f"\n  [Genesis quiere evolucionar! "
                      f"Escribe /evolucionar o /rechazar]")

            user_input = input(f"\n  Tu > ").strip()

            if not user_input:
                continue

            # Procesar feedback rapido (+ o -)
            if user_input in ("+", "-", "👍", "👎"):
                result = genesis.handle_command(user_input)
                print(f"\n  {result}")
                continue

            # Procesar comandos
            if user_input.startswith("/"):
                result = genesis.handle_command(user_input)
                print(f"\n{result}")
                continue

            # Procesar input normal
            start_time = time.time()

            if genesis.streaming:
                # === MODO STREAMING ===
                # Los tokens aparecen uno a uno en la terminal
                gen = genesis.evolution.get_generation()
                print(f"\n  {GENESIS_NAME} [Gen {gen}]:\n")
                print(f"  ", end="", flush=True)
                _stream_col = [0]  # Columna actual (mutable para closure)

                def _stream_token(token: str):
                    """Callback que imprime cada token en tiempo real."""
                    # Manejar saltos de linea con indentacion
                    for char in token:
                        if char == "\n":
                            print()
                            print(f"  ", end="", flush=True)
                            _stream_col[0] = 0
                        else:
                            print(char, end="", flush=True)
                            _stream_col[0] += 1

                response = genesis.process_input(user_input, stream_callback=_stream_token)

                elapsed = time.time() - start_time
                # Agregar newline final y tiempo
                print(f"\n\n  ({elapsed:.1f}s)")
            else:
                # === MODO NORMAL (batch) con spinner ===
                spinner = Spinner(f"{GENESIS_NAME} pensando")
                spinner.start()

                response = genesis.process_input(user_input)

                elapsed = time.time() - start_time
                gen = genesis.evolution.get_generation()
                spinner.stop()

                print(f"\n  {GENESIS_NAME} [Gen {gen}] ({elapsed:.1f}s):\n")

                # Mostrar respuesta con formato
                for line in response.split("\n"):
                    print(f"  {line}")

        except KeyboardInterrupt:
            print("\n\n  Interrumpido por el usuario.")
            genesis.heartbeat.stop()
            genesis.running = False
        except EOFError:
            genesis.heartbeat.stop()
            genesis.running = False

    # Guardar sesion y metricas
    genesis._save_session()
    genesis.metrics.end_session()

    print(f"\n  Genesis finalizado. Generacion {genesis.evolution.get_generation()}.")
    print(f"  Memorias: {len(genesis.memory.long_term.memories)} de largo plazo.")
    fitness = genesis.metrics.get_session_fitness()
    print(f"  Fitness de sesion: {fitness}/100")
    approval = genesis.feedback.get_satisfaction_rate() * 100
    print(f"  Aprobacion del usuario: {approval:.0f}%")
    print(f"  Sesion guardada. Hasta la proxima evolucion.\n")


if __name__ == "__main__":
    main()
