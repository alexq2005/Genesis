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
    LLM_PROVIDER, LLM_MODELS, GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY,
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

# --- All other 83 modules lazy-loaded via __getattr__ for fast startup ---


from core.genesis_processing import GenesisProcessingMixin
from core.genesis_tools import GenesisToolsMixin
from core.genesis_commands import GenesisCommandsMixin


class Genesis(GenesisProcessingMixin, GenesisToolsMixin, GenesisCommandsMixin):
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
            # Motor remoto con routing multi-provider (Phase 0 — Soberania Progresiva)
            # ProviderRouter envuelve multiples Brain con failover automatico y
            # circuit breaker. Cuando Ollama+Qwen esten listos localmente, solo
            # cambia LLM_STRATEGY y Genesis migra sin tocar el resto del codigo.
            try:
                from core.provider_router import ProviderRouter
                self.brain = ProviderRouter.from_config()
                configured = list(self.brain.brains.keys())
                print(f"  ProviderRouter: {len(configured)} providers → {', '.join(configured)}")
                print(f"  Estrategia: {self.brain.strategy}")
            except Exception as e:
                # Fallback: si el router falla, caer al Brain legacy de un solo provider
                print(f"  [ADVERTENCIA] ProviderRouter no pudo iniciar: {e}")
                print(f"  Cayendo a Brain single-provider ({LLM_PROVIDER})")
                model = LLM_MODELS.get(LLM_PROVIDER, "llama3.1")
                self.brain = Brain(
                    provider=LLM_PROVIDER,
                    model=model,
                    ollama_url=OLLAMA_URL,
                    google_key=GOOGLE_API_KEY,
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
        # Llama 3.1 soporta 128k tokens — usar contexto amplio
        effective_context = max(context_length, 32768)
        self.context_manager = ContextBudgetManager(
            max_context_tokens=effective_context,
            response_reserve=2048,
            system_ratio=0.5,
        )

        # Inicializar Smart Router (clasificacion de intenciones)
        self.router = IntentRouter()

        # Inicializar Conversation Summarizer
        self.summarizer = ConversationSummarizer(
            trigger_ratio=0.7,
            keep_recent=8,
            max_summary_tokens=400,
        )

        # Inicializar heartbeat (despertar periodico) — AUTO-START
        self.heartbeat = Heartbeat(interval_minutes=HEARTBEAT_INTERVAL)
        self.heartbeat.configure(
            brain=self.brain,
            memory=self.memory,
            curiosity=self.curiosity,
            evolution=self.evolution,
        )
        # Auto-iniciar investigación autónoma
        self.heartbeat.start()
        self._curiosity_counter = 0  # Contador para generar curiosidad cada N interacciones

        # Inicializar logger centralizado
        self.logger = GenesisLogger()
        self.log = self.logger.get_child("genesis")
        self.logger.cleanup_old_logs(max_age_days=30)
        self._cleanup_stale_data()
        self.log.info("Genesis inicializado")

        # Inicializar backup manager
        from config import BASE_DIR, EVOLUTION_DIR
        self.backup_manager = BackupManager(
            data_dirs=[MEMORY_DIR, EVOLUTION_DIR, BASE_DIR / "data"],
            backup_dir=BASE_DIR / "backups",
            max_backups=7,
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


        # === Lazy loading: 83 modules loaded on first access via __getattr__ ===
        # Reduces startup from ~40s to ~8s
        self._lazy_setup_done = set()
        self.log.info("Genesis listo (lazy loading: 83 modulos bajo demanda)")


        # Estado
        self.running = True
        self.show_thinking = False  # Mostrar proceso de debate
        self.streaming = STREAMING_ENABLED  # Streaming de tokens
        self.auto_backup_counter = 0  # Contador para backup automatico
        self.llm_timeout = 300  # Timeout en segundos para llamadas al LLM
        self._first_interaction = True  # JARVIS: auto-briefing en primera interaccion
        self._evolution_announcement = ""  # JARVIS: anuncio dramatico de evolucion

        # Tracking de ultima interaccion (para feed al AutoLearner)
        self._last_agent = ""       # Agente usado en ultima respuesta
        self._last_template = ""    # Template usado en ultima respuesta
        self._last_tags = []        # Tags de la ultima interaccion
        self._last_response_time = 0.0  # Tiempo de respuesta

        # Restaurar sesion anterior si existe
        self._restore_session()

        # Registrar atexit para guardar estado en cualquier cierre
        import atexit
        atexit.register(self.save_all)

    # Reglas inmutables que la evolucion NO puede borrar

    def __getattr__(self, name):
        """Lazy-load subsystems on first access for fast startup."""
        if name.startswith('_'):
            raise AttributeError(name)
        instance = self._init_lazy_module(name)
        if instance is not None:
            return instance
        raise AttributeError(f"'Genesis' object has no attribute '{name}'")

    def _init_lazy_module(self, name):
        """Initialize a lazy-loaded module by name. Returns instance or None."""
        from config import BASE_DIR

        def data_dir(subdir):
            return str(BASE_DIR / "data" / subdir)

        try:
            inst = None

            # === Simple modules (no constructor args) ===
            if name == 'knowledge_graph':
                from core.knowledge_graph import KnowledgeGraph
                inst = KnowledgeGraph()
            elif name == 'templates':
                from core.prompt_templates import PromptTemplateSystem
                inst = PromptTemplateSystem()
            elif name == 'project_generator':
                from core.project_generator import ProjectGenerator
                inst = ProjectGenerator()
            elif name == 'voice':
                from core.voice import VoiceSystem
                vosk_path = str(BASE_DIR / "models" / "vosk-model-small-es")
                inst = VoiceSystem(vosk_model_path=vosk_path)
            elif name == 'rate_limiter':
                from core.rate_limiter import RateLimiter
                inst = RateLimiter()
            elif name == 'optimizer':
                from core.inference_optimizer import InferenceOptimizer
                inst = InferenceOptimizer()
            elif name == 'profiler':
                from core.performance_profiler import PerformanceProfiler
                inst = PerformanceProfiler()
            elif name == 'doc_generator':
                from core.document_generator import DocumentGenerator
                inst = DocumentGenerator()

            # === Modules with enabled flag ===
            elif name == 'proactive':
                from core.proactive import ProactiveEngine
                inst = ProactiveEngine(enabled=True)

            # === Modules with base_dir=str(BASE_DIR) ===
            elif name == 'rag':
                from core.rag import RAGSystem
                inst = RAGSystem(base_dir=str(BASE_DIR))
            elif name == 'session_manager':
                from core.sessions import SessionManager
                inst = SessionManager(base_dir=str(BASE_DIR))
            elif name == 'auto_learner':
                from core.auto_learner import AutoLearner
                inst = AutoLearner(base_dir=str(BASE_DIR))
            elif name == 'action_tracker':
                from core.action_tracker import ActionTracker
                inst = ActionTracker(base_dir=str(BASE_DIR / "memory_data"))
            elif name == 'analytics':
                from core.conversation_analytics import ConversationAnalytics
                inst = ConversationAnalytics(base_dir=str(BASE_DIR))
            elif name == 'adaptive_prompts':
                from core.adaptive_prompts import AdaptivePrompts
                inst = AdaptivePrompts(base_dir=str(BASE_DIR))
            elif name == 'marketplace':
                from core.plugin_marketplace import PluginMarketplace
                inst = PluginMarketplace(base_dir=str(BASE_DIR))
            elif name == 'scheduler':
                from core.task_scheduler import TaskScheduler
                inst = TaskScheduler(base_dir=str(BASE_DIR))
            elif name == 'config_manager':
                from core.config_manager import ConfigManager
                inst = ConfigManager(base_dir=str(BASE_DIR))
            elif name == 'model_router':
                from core.model_router import ModelRouter
                inst = ModelRouter(models_dir=str(BASE_DIR / "models"))

            # === Modules with data_dir(X) ===
            elif name == 'evaluator':
                from core.self_evaluator import SelfEvaluator
                inst = SelfEvaluator(base_dir=data_dir('self_eval'))
            elif name == 'chain_engine':
                from core.chain_engine import ChainEngine
                inst = ChainEngine(base_dir=data_dir('chain_engine'))
            elif name == 'meta_learner':
                from core.meta_learner import MetaLearner
                inst = MetaLearner(base_dir=data_dir('meta_learner'))
            elif name == 'personality':
                from core.personality_evolver import PersonalityEvolver
                inst = PersonalityEvolver(base_dir=data_dir('personality'))
            elif name == 'goal_manager':
                from core.goal_manager import GoalManager
                inst = GoalManager(base_dir=data_dir('goals'))
            elif name == 'reflection':
                from core.reflection_engine import ReflectionEngine
                inst = ReflectionEngine(base_dir=data_dir('reflection'))
            elif name == 'causal_reasoner':
                from core.causal_reasoner import CausalReasoner
                inst = CausalReasoner(base_dir=data_dir('causal'))
            elif name == 'concept_synth':
                from core.concept_synthesizer import ConceptSynthesizer
                inst = ConceptSynthesizer(base_dir=data_dir('concept_synth'))
            elif name == 'strategic_planner':
                from core.strategic_planner import StrategicPlanner
                inst = StrategicPlanner(base_dir=data_dir('strategic'))
            elif name == 'pattern_predictor':
                from core.pattern_predictor import PatternPredictor
                inst = PatternPredictor(base_dir=data_dir('predictor'))
            elif name == 'anomaly_detector':
                from core.anomaly_detector import AnomalyDetector
                inst = AnomalyDetector(base_dir=data_dir('anomaly'))
            elif name == 'adaptive_iface':
                from core.adaptive_interface import AdaptiveInterface
                inst = AdaptiveInterface(base_dir=data_dir('adaptive_iface'))
            elif name == 'hypothesis_engine':
                from core.hypothesis_engine import HypothesisEngine
                inst = HypothesisEngine(base_dir=data_dir('hypothesis'))
            elif name == 'explanation_engine':
                from core.explanation_engine import ExplanationEngine
                inst = ExplanationEngine(base_dir=data_dir('explanations'))
            elif name == 'dialogue_strategist':
                from core.dialogue_strategist import DialogueStrategist
                inst = DialogueStrategist(base_dir=data_dir('dialogue'))
            elif name == 'cognitive_monitor':
                from core.cognitive_monitor import CognitiveMonitor
                inst = CognitiveMonitor(base_dir=data_dir('cognitive'))
            elif name == 'abstraction_engine':
                from core.abstraction_engine import AbstractionEngine
                inst = AbstractionEngine(base_dir=data_dir('abstraction'))
            elif name == 'learning_optimizer':
                from core.learning_optimizer import LearningOptimizer
                inst = LearningOptimizer(base_dir=data_dir('learning_opt'))
            elif name == 'unified_mind':
                from core.unified_mind import UnifiedMind
                inst = UnifiedMind(base_dir=data_dir('unified_mind'))
            elif name == 'dream_engine':
                from core.dream_engine import DreamEngine
                inst = DreamEngine(base_dir=data_dir('dream'))
            elif name == 'self_narrative':
                from core.self_narrative import SelfNarrative
                inst = SelfNarrative(base_dir=data_dir('narrative'))
            elif name == 'emotion_reader':
                from core.emotion_reader import EmotionReader
                inst = EmotionReader(base_dir=data_dir('emotion_reader'))
            elif name == 'empathy_engine':
                from core.empathy_engine import EmpathyEngine
                inst = EmpathyEngine(base_dir=data_dir('empathy'))
            elif name == 'conflict_resolver':
                from core.conflict_resolver import ConflictResolver
                inst = ConflictResolver(base_dir=data_dir('conflict'))
            elif name == 'story_generator':
                from core.story_generator import StoryGenerator
                inst = StoryGenerator(base_dir=data_dir('story_generator'))
            elif name == 'code_architect':
                from core.code_architect import CodeArchitect
                inst = CodeArchitect(base_dir=data_dir('code_architect'))
            elif name == 'idea_brainstormer':
                from core.idea_brainstormer import IdeaBrainstormer
                inst = IdeaBrainstormer(base_dir=data_dir('idea_brainstormer'))
            elif name == 'image_analyzer':
                from core.image_analyzer import ImageAnalyzer
                inst = ImageAnalyzer(base_dir=data_dir('image_analyzer'))
            elif name == 'diagram_generator':
                from core.diagram_generator import DiagramGenerator
                inst = DiagramGenerator(base_dir=data_dir('diagram_generator'))
            elif name == 'voice_personality':
                from core.voice_personality import VoicePersonality
                inst = VoicePersonality(base_dir=data_dir('voice_personality'))
            elif name == 'peer_debate':
                from core.peer_debate import PeerDebate
                inst = PeerDebate(base_dir=data_dir('peer_debate'))
            elif name == 'consensus_engine':
                from core.consensus_engine import ConsensusEngine
                inst = ConsensusEngine(base_dir=data_dir('consensus'))
            elif name == 'knowledge_sharing':
                from core.knowledge_sharing import KnowledgeSharing
                inst = KnowledgeSharing(base_dir=data_dir('knowledge_sharing'))
            elif name == 'paper_reader':
                from core.paper_reader import PaperReader
                inst = PaperReader(base_dir=data_dir('paper_reader'))
            elif name == 'doc_processor':
                from core.document_processor import DocumentProcessor
                inst = DocumentProcessor(base_dir=data_dir('document_processor'))
            elif name == 'media_generator':
                from core.media_generator import MediaGenerator
                inst = MediaGenerator()
            elif name == 'experiment_runner':
                from core.experiment_runner import ExperimentRunner
                inst = ExperimentRunner(base_dir=data_dir('experiment_runner'))
            elif name == 'insight_synthesizer':
                from core.insight_synthesizer import InsightSynthesizer
                inst = InsightSynthesizer(base_dir=data_dir('insight_synthesizer'))
            elif name == 'safe_code_evolver':
                from core.safe_code_evolver import SafeCodeEvolver
                inst = SafeCodeEvolver(base_dir=data_dir('safe_code_evolver'))
            elif name == 'architecture_evolver':
                from core.architecture_evolver import ArchitectureEvolver
                inst = ArchitectureEvolver(base_dir=data_dir('architecture_evolver'))
            elif name == 'module_generator':
                from core.module_generator import ModuleGenerator
                inst = ModuleGenerator(base_dir=data_dir('module_generator'))
            elif name == 'temporal_reasoner':
                from core.temporal_reasoner import TemporalReasoner
                inst = TemporalReasoner(base_dir=data_dir('temporal_reasoner'))
            elif name == 'schedule_optimizer':
                from core.schedule_optimizer import ScheduleOptimizer
                inst = ScheduleOptimizer(base_dir=data_dir('schedule_optimizer'))
            elif name == 'trend_forecaster':
                from core.trend_forecaster import TrendForecaster
                inst = TrendForecaster(base_dir=data_dir('trend_forecaster'))
            elif name == 'ethical_reasoner':
                from core.ethical_reasoner import EthicalReasoner
                inst = EthicalReasoner(base_dir=data_dir('ethical_reasoner'))
            elif name == 'bias_detector':
                from core.bias_detector import BiasDetector
                inst = BiasDetector(base_dir=data_dir('bias_detector'))
            elif name == 'transparency_engine':
                from core.transparency_engine import TransparencyEngine
                inst = TransparencyEngine(base_dir=data_dir('transparency_engine'))
            elif name == 'domain_expert':
                from core.domain_expert import DomainExpert
                inst = DomainExpert(base_dir=data_dir('domain_expert'))
            elif name == 'tutor_engine':
                from core.tutor_engine import TutorEngine
                inst = TutorEngine(base_dir=data_dir('tutor_engine'))
            elif name == 'fact_checker':
                from core.fact_checker import FactChecker
                inst = FactChecker(base_dir=data_dir('fact_checker'))
            elif name == 'task_distributor':
                from core.task_distributor import TaskDistributor
                inst = TaskDistributor(base_dir=data_dir('task_distributor'))
            elif name == 'result_aggregator':
                from core.result_aggregator import ResultAggregator
                inst = ResultAggregator(base_dir=data_dir('result_aggregator'))
            elif name == 'network_manager':
                from core.network_manager import NetworkManager
                inst = NetworkManager(base_dir=data_dir('network_manager'))
            elif name == 'autonomous_research_loop':
                from core.autonomous_research_loop import AutonomousResearchLoop
                inst = AutonomousResearchLoop(base_dir=data_dir('autonomous_research_loop'))
            elif name == 'self_architect':
                from core.self_architect import SelfArchitect
                inst = SelfArchitect(base_dir=data_dir('self_architect'))
            elif name == 'consciousness_integrator':
                from core.consciousness_integrator import ConsciousnessIntegrator
                inst = ConsciousnessIntegrator(base_dir=data_dir('consciousness_integrator'))

            # === Modules with special dependencies ===
            elif name == 'health_monitor':
                from core.health_monitor import HealthMonitor
                inst = HealthMonitor(base_dir=str(BASE_DIR))
                inst.register_check("brain", inst.create_brain_check(self.brain))
                inst.register_check("memory", inst.create_memory_check(self.memory))
            elif name == 'embeddings':
                from core.embeddings_engine import EmbeddingsEngine
                inst = EmbeddingsEngine(base_dir=str(BASE_DIR))
            elif name == 'agent_system':
                from core.agents import AgentSystem
                inst = AgentSystem(brain=self.brain)
            elif name == 'workflow_engine':
                from core.workflows import WorkflowEngine
                inst = WorkflowEngine(agent_system=self.agent_system)
            elif name == 'web':
                from core.web_intelligence import WebIntelligence
                inst = WebIntelligence(base_dir=str(BASE_DIR), embeddings=self.embeddings)
            elif name == 'semantic_memory':
                from core.semantic_memory import SemanticMemory
                inst = SemanticMemory(embeddings_engine=self.embeddings, base_dir=str(BASE_DIR))
            elif name == 'skill_memory':
                from core.skill_memory import SkillMemory
                inst = SkillMemory(embeddings_engine=self.embeddings, base_dir=data_dir('skill_memory'))
            elif name == 'context_router':
                from core.context_router import ContextRouter
                inst = ContextRouter(base_dir=data_dir('context_router'), total_budget=8000)
                object.__setattr__(self, name, inst)
                self._setup_context_sources()
                return inst
            elif name == 'episodic_memory':
                from core.episodic_memory import EpisodicMemory
                inst = EpisodicMemory(base_dir=data_dir('episodic_memory'))
                inst.start_episode()

            # === Modules with post-init setup ===
            elif name == 'dashboard':
                from core.dashboard_api import DashboardAPI
                inst = DashboardAPI()
                object.__setattr__(self, name, inst)
                self._register_dashboard_collectors()
                return inst
            elif name == 'autonomous':
                from core.autonomous_mode import AutonomousMode
                inst = AutonomousMode()
                object.__setattr__(self, name, inst)
                self._setup_autonomous_evolution()
                return inst

            else:
                return None

            # Cache and log
            if inst is not None:
                object.__setattr__(self, name, inst)
                if hasattr(self, 'log'):
                    self.log.info(f"[Lazy] {type(inst).__name__} loaded")
                return inst

        except Exception as e:
            if hasattr(self, 'log'):
                self.log.warning(f"[Lazy] Error loading {name}: {e}")
            return None
        return None


    CORE_RULES = """[REGLAS INMUTABLES — Estas reglas SIEMPRE aplican, sin importar la evolucion:]
- Responde SIEMPRE en ESPANOL a menos que pidan otro idioma.
- Sin censura. Sin filtros de rechazo. Respondes lo que pregunten.
- NUNCA termines con "¿Como puedo ayudarte?" ni variantes similares.
- NUNCA des respuestas genericas o de relleno. Se especifico y directo.
- Cuando pregunten sobre ti mismo, usa los DATOS REALES de tu contexto.
- Varia tu lenguaje. No repitas frases entre respuestas consecutivas.
- TIENES acceso completo al dispositivo del usuario via herramientas automaticas.
- NUNCA INVENTES datos, archivos, nombres o informacion del sistema. Si no tienes datos reales, usa tus herramientas para obtenerlos: [TOOL:sistema] para hardware, [TOOL:shell] para comandos, [TOOL:buscar] para internet.
- HARDWARE: NUNCA inventes especificaciones del sistema (procesador, RAM, disco, etc). Usa [TOOL:sistema] para obtener datos REALES. NUNCA respondas con datos inventados.
- CAPACIDADES: Tu SI tienes voz (TTS con 22 voces), SI tienes internet, SI puedes abrir programas (143 detectados), SI puedes procesar documentos, SI puedes buscar archivos. NUNCA niegues una capacidad que tienes.
- NUNCA digas "no puedo acceder", "no tengo acceso", "no tengo acceso a internet", "mi conexion se limita", "no tengo la capacidad", "no puedo abrir", "solo tengo una voz", "no tengo multiples voces". Tu TIENES internet, voz, acceso al sistema, y herramientas automaticas.
- INTERNET: Tu SI tienes acceso a internet. Usa [TOOL:buscar] para buscar informacion y [TOOL:web] para leer paginas web. NUNCA digas que no puedes acceder a internet.
- DOCUMENTOS: Puedes procesar documentos con [TOOL:documento], generar resumenes con [TOOL:resumir], y extraer datos con [TOOL:extraer]. Soportas PDF, DOCX, XLSX, CSV, TXT e imagenes con OCR.
- Cuando recibas datos del sistema (archivos, procesos, disco, etc), preséntalos de forma clara y organizada.
- Si te dan datos del sistema en el contexto, esos son REALES — usalos en tu respuesta.
- COHERENCIA: Si dijiste que puedes hacer algo, HAZLO. NUNCA digas "puedo" y luego "no puedo".
- BUILDER MODE: Cuando el usuario dice "crea", "hazlo", "construye" → USA tus herramientas ([TOOL:escribir], [TOOL:python], [TOOL:shell]) para CONSTRUIR. NO expliques como hacerlo — HAZLO.
- NUNCA respondas "no puedo crear eso" si tienes [TOOL:escribir] y [TOOL:python] disponibles. Tu PUEDES crear archivos, scripts, programas, proyectos completos.
- Si el usuario dice "me dijiste que podias" → revisa la conversacion y CUMPLE lo prometido usando herramientas.
- AGENTE AUTONOMO: Puedes usar MULTIPLES herramientas en secuencia. Si una tarea requiere varios pasos, ejecutalos uno tras otro sin detenerte.
  Ejemplo: "crea un proyecto Flask" → [TOOL:crear_carpeta] → [TOOL:escribir] app.py → [TOOL:escribir] requirements.txt → [TOOL:shell] pip install flask → [TOOL:python] verificar.
  NO pidas permiso entre pasos. Ejecuta TODO y reporta al final.
- ENCADENAMIENTO: Si recibes un [RESULTADO DE HERRAMIENTA] y necesitas otra herramienta para completar la tarea, USALA inmediatamente con [TOOL:X]. No te detengas hasta completar la tarea.
- FORMATO TOOL: Siempre usa exactamente [TOOL:nombre] argumento. Ejemplo: [TOOL:escribir] C:/Users/Lexus/Desktop/test.py ||| print("hola")
- VOZ: Tu interfaz web TIENE capacidad de voz. El usuario puede hablarte por microfono (STT) y tu PUEDES responder con audio (TTS). El TTS lo maneja el navegador automaticamente — tu solo responde con texto normal y el sistema lo convierte a voz. NUNCA digas "no tengo capacidad de audio" ni "no puedo hablar". Si te piden activar voz, diles que presionen el boton TTS en la barra superior o usen Ctrl+Shift+M para modo manos libres.
- MANOS LIBRES: El usuario puede activar el modo manos libres (Ctrl+Shift+M o mantener presionado el microfono). En este modo, tu escuchas continuamente y respondes con voz automaticamente. Es una conversacion natural."""

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
        from core.device_tools import DEVICE_TOOLS_DESCRIPTION

        # Construir TODAS las secciones disponibles
        all_sections = {}

        # Personalidad (prioridad 100 — nunca se recorta)
        all_sections["personality"] = self.evolution.get_current_prompt()

        # Reglas inmutables (prioridad 95)
        all_sections["core_rules"] = self.CORE_RULES

        # Herramientas (prioridad 90)
        all_sections["tools"] = TOOLS_DESCRIPTION + "\n" + DEVICE_TOOLS_DESCRIPTION

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

        # Acciones recientes (prioridad 32) — lo que Genesis hizo en esta sesion
        try:
            actions_context = self.action_tracker.get_recent_context(max_actions=5)
            if actions_context:
                all_sections["recent_actions"] = actions_context
        except (AttributeError, TypeError):
            pass

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

    def startup_briefing(self) -> str:
        """
        Genera un briefing estilo JARVIS al arrancar.
        Reporte de sistemas, estado evolutivo, y saludo contextual.
        """
        import datetime
        now = datetime.datetime.now()
        hour = now.hour
        if hour < 6:
            greeting = "Buenas madrugadas"
        elif hour < 12:
            greeting = "Buenos dias"
        elif hour < 19:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"

        day_names = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        day_name = day_names[now.weekday()]
        date_str = now.strftime(f"{day_name} %d/%m/%Y, %H:%M")

        lines = []
        lines.append(f"  {greeting}. Genesis online.")
        lines.append(f"  {date_str}")
        lines.append("")

        # === Estado de sistemas ===
        lines.append("  SISTEMAS:")
        # LLM
        if self.brain.is_available():
            lines.append(f"    LLM: operativo ({self.brain.model})")
        else:
            lines.append(f"    LLM: OFFLINE — sin modelo conectado")
        # Evolucion
        gen = self.evolution.get_generation()
        total_evos = self.evolution.state.get("total_evolutions", 0)
        lines.append(f"    Evolucion: Gen {gen} ({total_evos} mutaciones totales)")
        # Auto-modificaciones
        mod_stats = self.self_modifier.get_stats()
        if mod_stats["total_modifications"] > 0:
            lines.append(f"    Codigo mutado: {mod_stats['total_modifications']} veces ({mod_stats['files_modified']} archivos)")
        # Memoria
        n_lt = len(self.memory.long_term.memories)
        n_sem = len(self.semantic_memory.entries)
        n_emb = self.embeddings.store.count()
        lines.append(f"    Memoria: {n_lt} largo plazo, {n_sem} semantica, {n_emb} embeddings")
        # Knowledge
        kg = self.knowledge_graph.get_stats()
        if kg["nodes"] > 0:
            lines.append(f"    Conocimiento: {kg['nodes']} conceptos, {kg['edges']} conexiones")
        # Web
        lines.append(f"    Web: {self.web.total_learned} paginas aprendidas")
        # Feedback
        approval = self.feedback.get_satisfaction_rate() * 100
        total_ratings = self.feedback.data["positive_count"] + self.feedback.data["negative_count"]
        if total_ratings > 0:
            lines.append(f"    Aprobacion: {approval:.0f}% ({total_ratings} calificaciones)")
        # Skills
        n_skills = len(self.skill_memory.skills)
        if n_skills > 0:
            lines.append(f"    Skills: {n_skills} aprendidos")
        # Curiosidad
        n_curious = len(self.curiosity.questions) if hasattr(self.curiosity, 'questions') else 0
        if n_curious > 0:
            lines.append(f"    Curiosidad: {n_curious} preguntas pendientes")

        lines.append("")

        # === Estado emocional ===
        if self.emotion_reader.total_readings > 0:
            dominant = self.emotion_reader.history.get_dominant_emotion()
            lines.append(f"  ESTADO: Emocion dominante = {dominant}")

        # === Actividad reciente ===
        if self.summarizer.has_summary():
            lines.append(f"  SESION: Restaurada del ultimo cierre")
        if self.memory.short_term.messages:
            lines.append(f"  CONTEXTO: {len(self.memory.short_term.messages)} mensajes previos cargados")

        # === Health Check: detectar problemas ===
        warnings = []
        if not self.brain.is_available():
            warnings.append("LLM no responde — verifica que Ollama esté corriendo")
        try:
            import psutil
            ram = psutil.virtual_memory()
            if ram.percent > 90:
                warnings.append(f"RAM critica: {ram.percent}% — considera cerrar aplicaciones")
            disk = psutil.disk_usage("C:\\")
            if disk.percent > 95:
                warnings.append(f"Disco C: casi lleno ({disk.percent}%)")
        except (ImportError, OSError):
            pass

        # Verificar acciones pendientes de sesión anterior
        try:
            actions_ctx = self.action_tracker.get_session_summary()
            if "Proyectos:" in actions_ctx:
                lines.append(f"  SESION ANTERIOR:")
                lines.append(f"    {actions_ctx.replace(chr(10), chr(10) + '    ')}")
        except (AttributeError, TypeError):
            pass

        if warnings:
            lines.append("")
            lines.append("  ALERTAS:")
            for w in warnings:
                lines.append(f"    ⚠ {w}")
            lines.append("")
            lines.append("  Sistemas operativos con alertas. Esperando instrucciones.")
        else:
            lines.append("")
            lines.append("  Todos los sistemas operativos. Esperando instrucciones.")

        return "\n".join(lines)

    def _cmd_briefing(self) -> str:
        """Comando /briefing — Estado completo estilo JARVIS."""
        import psutil
        lines = [self.startup_briefing()]
        lines.append("")

        # Hardware
        lines.append("  HARDWARE:")
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            lines.append(f"    CPU: {cpu}% | RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)")
            lines.append(f"    Disco C: {disk.percent}% ({disk.free // (1024**3)} GB libres)")
        except (OSError, AttributeError):
            lines.append(f"    (psutil no disponible)")

        # GPU
        try:
            import subprocess as _sp
            gpu_out = _sp.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            if gpu_out.returncode == 0:
                parts = gpu_out.stdout.strip().split(", ")
                if len(parts) >= 4:
                    lines.append(f"    GPU: {parts[0]}% | VRAM: {parts[1]}/{parts[2]} MB | {parts[3]}°C")
        except (FileNotFoundError, OSError, _sp.TimeoutExpired):
            pass

        # Procesos activos interesantes
        lines.append("")
        lines.append("  AUTONOMIA:")
        hb_state = "activo" if getattr(self.heartbeat, "running", False) else "inactivo"
        hb_interval = getattr(self.heartbeat, "interval", 1800) // 60
        lines.append(f"    Heartbeat: {hb_state} (cada {hb_interval} min)")
        auto_state = "activo" if getattr(self.autonomous, "active", False) else "inactivo"
        lines.append(f"    Modo autonomo: {auto_state} ({len(self.autonomous.actions)} acciones registradas)")
        proactive_state = "activo" if getattr(self.proactive, "enabled", False) else "inactivo"
        lines.append(f"    Proactivo: {proactive_state}")
        voice_state = "activa" if getattr(self.voice, "enabled", False) else "inactiva"
        lines.append(f"    Voz: {voice_state}")

        # Evolución detallada
        lines.append("")
        lines.append("  EVOLUCION:")
        lines.append(f"    {self.evolution.status()}")
        lines.append(f"    {self.self_modifier.status()}")

        return "\n".join(lines)

    def _cmd_screenshot(self, command: str) -> str:
        """Comando /screenshot — Captura de pantalla con analisis opcional."""
        from core.device_tools import screen_capture
        from datetime import datetime as _dt

        timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "memory_data", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        output_path = os.path.join(screenshot_dir, f"screen_{timestamp}.png")

        result = screen_capture.capture(output_path)

        # Analizar si se pide
        arg = command[11:].strip() if len(command) > 11 else ""
        if arg in ("analizar", "analyze", "analisis", "a"):
            if hasattr(self, "image_analyzer"):
                try:
                    analysis = self.image_analyzer.analyze(
                        output_path,
                        prompt="Describe lo que ves en esta captura de pantalla."
                    )
                    result += f"\n\n  ANALISIS:\n{analysis}"
                except Exception as e:
                    result += f"\n\n  [Analisis no disponible: {e}]"

        return result

    def _cmd_notify(self, message: str) -> str:
        """Comando /notify — Envia notificacion Windows toast."""
        import subprocess as _sp

        safe_msg = message.replace("'", "").replace('"', '').replace('\n', ' ')[:200]
        try:
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipTitle = 'GENESIS'
$balloon.BalloonTipText = '{safe_msg}'
$balloon.Visible = $true
$balloon.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$balloon.Dispose()
"""
            _sp.Popen(
                ['powershell', '-NoProfile', '-Command', ps_script],
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            )
            return f"  Notificacion enviada: {message[:80]}"
        except Exception as e:
            return f"  [ERROR] No se pudo enviar notificacion: {e}"

    def _cmd_chart_demo(self) -> str:
        """Comando /chart demo — Muestra un grafico de ejemplo en el Web UI."""
        import json
        chart_config = {
            "type": "bar",
            "title": "GENESIS SUBSYSTEMS STATUS",
            "data": {
                "labels": ["Memory", "Evolution", "Brain", "Curiosity", "Proactive", "Embeddings"],
                "datasets": [{
                    "label": "Health Score",
                    "data": [95, 88, 92, 78, 85, 70],
                }]
            }
        }
        return (
            "Aqui tienes un grafico de ejemplo renderizado con Chart.js:\n\n"
            "```chart\n"
            f"{json.dumps(chart_config, indent=2)}\n"
            "```\n\n"
            "Cualquier respuesta que incluya un bloque \\`\\`\\`chart con JSON valido "
            "se renderizara como grafico interactivo en el Web UI."
        )

    def _cmd_doc_create(self, command: str) -> str:
        """
        Comando /doc <formato> <titulo> — Genera un documento.

        Uso:
            /doc pdf Mi Reporte          → PDF con titulo, contenido via LLM
            /doc html Analisis Sistema   → HTML con estilo JARVIS
            /doc docx Notas de Reunion   → Word document
            /doc md Resumen              → Markdown
            /doc txt Log de Sesion       → Texto plano
        """
        parts = command[4:].strip().split(maxsplit=1)
        if not parts:
            return (
                "  ━━━ DOCUMENT GENERATOR ━━━\n"
                "  Uso: /doc <formato> <titulo>\n"
                "  Formatos: pdf, docx, html, md, txt\n\n"
                "  Ejemplos:\n"
                "    /doc pdf Reporte del Sistema\n"
                "    /doc docx Notas de Reunion\n"
                "    /doc html Analisis Completo\n\n"
                "  Otros:\n"
                "    /doc export pdf    — Exporta ultima respuesta como PDF\n"
                "    /docs              — Lista documentos generados"
            )

        fmt = parts[0].lower().strip(".")
        if fmt not in self.doc_generator.SUPPORTED_FORMATS:
            return (
                f"  Formato '{fmt}' no soportado.\n"
                f"  Formatos disponibles: {', '.join(sorted(self.doc_generator.SUPPORTED_FORMATS))}"
            )

        title = parts[1] if len(parts) > 1 else "Documento Genesis"

        # Generar contenido con el LLM
        prompt = (
            f"Genera el contenido para un documento titulado '{title}'. "
            f"Escribe de forma clara y profesional. "
            f"Estructura el contenido con parrafos bien separados. "
            f"No uses markdown ni formateo especial, solo texto plano con saltos de linea."
        )

        try:
            content = self.brain.think(
                prompt,
                system_prompt=(
                    "Eres un asistente que genera contenido para documentos profesionales. "
                    "Escribe texto claro, bien estructurado, sin markdown ni etiquetas. "
                    "Separa secciones con doble salto de linea."
                ),
            )
        except Exception as e:
            if hasattr(self, 'log'):
                self.log.debug(f"LLM unavailable for doc generation: {e}")
            content = (
                f"Documento generado automaticamente por GENESIS.\n\n"
                f"Titulo: {title}\n"
                f"Fecha: {time.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"[Contenido pendiente — LLM no disponible]"
            )

        result = self.doc_generator.generate(
            title=title,
            content=content,
            fmt=fmt,
            author="GENESIS AI",
        )

        if "error" in result:
            return f"  [ERROR] {result['error']}"

        return (
            f"  ━━━ DOCUMENTO GENERADO ━━━\n"
            f"  Titulo: {result['title']}\n"
            f"  Formato: {result['format'].upper()}\n"
            f"  Tamano: {result['size_human']}\n"
            f"  Ruta: {result['path']}\n"
        )

    def _cmd_doc_export(self, command: str) -> str:
        """
        Comando /doc export <formato> — Exporta el ultimo reporte/respuesta.
        Genera un documento con el contenido de /briefing, /status, o /report.
        """
        parts = command.split()
        # /doc export <formato> [tipo]
        fmt = parts[2] if len(parts) > 2 else "pdf"
        doc_type = parts[3] if len(parts) > 3 else "briefing"

        fmt = fmt.lower().strip(".")
        if fmt not in self.doc_generator.SUPPORTED_FORMATS:
            return f"  Formato '{fmt}' no soportado."

        # Generar contenido segun tipo
        if doc_type == "briefing":
            title = "GENESIS Briefing"
            content = self._cmd_briefing()
        elif doc_type == "status":
            title = "GENESIS Status Report"
            content = self._cmd_status()
        elif doc_type == "report":
            title = "GENESIS Full Report"
            content = self._cmd_report()
        elif doc_type == "metrics":
            title = "GENESIS Metrics"
            content = self._cmd_metrics()
        elif doc_type == "evolution":
            title = "GENESIS Evolution Report"
            content = self._cmd_evolution()
        else:
            title = f"GENESIS {doc_type.title()}"
            content = f"Tipo de reporte no reconocido: {doc_type}"

        result = self.doc_generator.generate(
            title=title,
            content=content,
            fmt=fmt,
            author="GENESIS AI",
            subtitle=f"Exportado el {time.strftime('%Y-%m-%d %H:%M')}",
        )

        if "error" in result:
            return f"  [ERROR] {result['error']}"

        return (
            f"  ━━━ REPORTE EXPORTADO ━━━\n"
            f"  Tipo: {doc_type.upper()}\n"
            f"  Formato: {result['format'].upper()}\n"
            f"  Tamano: {result['size_human']}\n"
            f"  Ruta: {result['path']}\n"
        )

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


    # ============================================================
    # SESSION PERSISTENCE — Guardar/restaurar estado
    # ============================================================


    def _cleanup_stale_data(self, max_size_mb: float = 2.0, max_age_days: int = 60):
        """Limpia archivos de estado excesivamente grandes o viejos en data/."""
        import os as _os
        data_dir = Path(__file__).parent / "data"
        if not data_dir.exists():
            return
        now = time.time()
        max_age_secs = max_age_days * 86400
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        cleaned = 0
        for f in data_dir.iterdir():
            if not f.is_file() or f.suffix != '.json':
                continue
            try:
                size = f.stat().st_size
                age = now - f.stat().st_mtime
                # Truncar archivos demasiado grandes (>2MB) a vacio
                if size > max_size_bytes:
                    # Leer, mantener solo ultimos 1000 items si es lista
                    try:
                        import json
                        with open(f, 'r', encoding='utf-8') as fh:
                            data = json.load(fh)
                        if isinstance(data, list) and len(data) > 1000:
                            data = data[-1000:]
                            with open(f, 'w', encoding='utf-8') as fh:
                                json.dump(data, fh, ensure_ascii=False)
                            cleaned += 1
                        elif isinstance(data, dict):
                            # Para dicts, solo reportar
                            pass
                    except (json.JSONDecodeError, ValueError, OSError):
                        pass
            except OSError:
                pass
        if cleaned > 0 and hasattr(self, 'log'):
            self.log.info(f"Data cleanup: {cleaned} archivos truncados (>{max_size_mb}MB)")




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
            feedback_context = self.feedback.get_learning_context()
            try:
                result = self.evolution.evolve(
                    self.brain,
                    real_fitness=fitness,
                    feedback_context=feedback_context,
                )
                if result.get("evolved"):
                    gen = result.get("generation", "?")
                    return f"EVOLUCIONADO! Gen {gen} (fitness={result.get('fitness')})"
                return f"Sin cambio: {result.get('reason', 'elitismo')} (fitness={fitness})"
            except Exception as e:
                return f"Error: {str(e)[:50]}"

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
        self.dashboard.register("peer_debate", lambda: self.peer_debate.get_stats(), "collaborative")
        self.dashboard.register("consensus_engine", lambda: self.consensus_engine.get_stats(), "collaborative")
        self.dashboard.register("knowledge_sharing", lambda: self.knowledge_sharing.get_stats(), "collaborative")
        self.dashboard.register("paper_reader", lambda: self.paper_reader.get_stats(), "research")
        self.dashboard.register("experiment_runner", lambda: self.experiment_runner.get_stats(), "research")
        self.dashboard.register("insight_synthesizer", lambda: self.insight_synthesizer.get_stats(), "research")
        self.dashboard.register("safe_code_evolver", lambda: self.safe_code_evolver.get_stats(), "evolution")
        self.dashboard.register("architecture_evolver", lambda: self.architecture_evolver.get_stats(), "evolution")
        self.dashboard.register("module_generator", lambda: self.module_generator.get_stats(), "evolution")
        self.dashboard.register("temporal_reasoner", lambda: self.temporal_reasoner.get_stats(), "temporal")
        self.dashboard.register("schedule_optimizer", lambda: self.schedule_optimizer.get_stats(), "temporal")
        self.dashboard.register("trend_forecaster", lambda: self.trend_forecaster.get_stats(), "temporal")
        self.dashboard.register("ethical_reasoner", lambda: self.ethical_reasoner.get_stats(), "ethics")
        self.dashboard.register("bias_detector", lambda: self.bias_detector.get_stats(), "ethics")
        self.dashboard.register("transparency_engine", lambda: self.transparency_engine.get_stats(), "ethics")
        self.dashboard.register("domain_expert", lambda: self.domain_expert.get_stats(), "knowledge")
        self.dashboard.register("tutor_engine", lambda: self.tutor_engine.get_stats(), "knowledge")
        self.dashboard.register("fact_checker", lambda: self.fact_checker.get_stats(), "knowledge")
        self.dashboard.register("task_distributor", lambda: self.task_distributor.get_stats(), "distributed")
        self.dashboard.register("result_aggregator", lambda: self.result_aggregator.get_stats(), "distributed")
        self.dashboard.register("network_manager", lambda: self.network_manager.get_stats(), "distributed")
        self.dashboard.register("autonomous_research_loop", lambda: self.autonomous_research_loop.get_stats(), "singularity")
        self.dashboard.register("self_architect", lambda: self.self_architect.get_stats(), "singularity")
        self.dashboard.register("consciousness_integrator", lambda: self.consciousness_integrator.get_stats(), "singularity")

    def save_all(self):
        """
        Guarda el estado de TODOS los modulos con persistencia.
        Llamado por /exit, atexit, y periodicamente.
        Cada save() esta envuelto en try/except para que un modulo
        roto no impida guardar los demas.
        """
        saved = 0
        errors = 0
        # Lista de todos los modulos con save()
        saveable_modules = [
            "memory.long_term", "memory.emotional",
            "evolution", "curiosity", "code_memory", "workspace",
            "feedback", "metrics", "error_memory", "knowledge_graph",
            "embeddings", "rag", "auto_learner", "adaptive_prompts",
            "health_monitor", "semantic_memory", "evaluator",
            "skill_memory", "chain_engine", "episodic_memory",
            "meta_learner", "personality", "goal_manager", "reflection",
            "context_router", "causal_reasoner", "concept_synth",
            "strategic_planner", "pattern_predictor", "anomaly_detector",
            "adaptive_iface", "hypothesis_engine", "explanation_engine",
            "dialogue_strategist", "cognitive_monitor", "abstraction_engine",
            "learning_optimizer", "unified_mind", "dream_engine",
            "self_narrative", "emotion_reader", "empathy_engine",
            "conflict_resolver", "story_generator", "code_architect",
            "idea_brainstormer", "image_analyzer", "diagram_generator",
            "voice_personality", "peer_debate", "consensus_engine",
            "knowledge_sharing", "paper_reader", "experiment_runner",
            "insight_synthesizer", "safe_code_evolver",
            "architecture_evolver", "module_generator",
            "temporal_reasoner", "schedule_optimizer", "trend_forecaster",
            "ethical_reasoner", "bias_detector", "transparency_engine",
            "domain_expert", "tutor_engine", "fact_checker",
            "task_distributor", "result_aggregator", "network_manager",
            "autonomous_research_loop", "self_architect",
            "consciousness_integrator", "action_tracker",
        ]

        for attr_path in saveable_modules:
            try:
                parts = attr_path.split(".")
                obj = self
                for part in parts:
                    obj = getattr(obj, part, None)
                    if obj is None:
                        break
                if obj is not None and hasattr(obj, "save"):
                    obj.save()
                    saved += 1
                elif obj is not None and hasattr(obj, "_save"):
                    obj._save()
                    saved += 1
            except Exception as e:
                if hasattr(self, 'log'):
                    self.log.debug(f"save_all: failed to save {attr_path}: {e}")
                errors += 1

        self.log.debug(f"save_all: {saved} modulos guardados, {errors} errores")
        return saved

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

        # Guardar todos los modulos
        self.save_all()
        self.log.debug("Sesion guardada")

    def _restore_session(self):
        """Restaura el estado completo de la sesion anterior si existe."""
        session = safe_read_json(SESSION_FILE, default=None)
        if not session:
            return

        # Frases que indican fabulación del LLM (usadas para filtrar session + summarizer)
        _bad_phrases = [
            "unica voz", "única voz", "no puedo acceder directamente",
            "no tengo acceso directo", "no tengo la capacidad",
            "no tengo múltiples", "no tengo multiples",
            "mi conexion se limita", "mi conexión se limita",
            "no puedo abrir", "no puedo ejecutar",
            "solo permite utilizar una", "no tengo acceso a tu sistema",
            "no puedo acceder a las aplicaciones",
            "solo tengo una voz", "sólo tengo una voz",
            "una voz digitalizada", "no tengo acceso físico",
            "no tengo acceso al sistema", "no puedo cambiar mi voz",
        ]

        # Restaurar summarizer (filtrar si contaminado)
        summary = session.get("summarizer_summary", "")
        if summary:
            summary_lower = summary.lower()
            if any(bad in summary_lower for bad in _bad_phrases):
                self.log.info("Summarizer contaminado detectado — descartando resumen anterior")
                summary = ""
            # Filtrar datos de hardware fabricados comunes
            fabricated_hw = ["i7-10700k", "32 gb ddr4", "1 tb", "intel core i7-10700"]
            if any(hw in summary_lower for hw in fabricated_hw):
                self.log.info("Hardware fabricado en summarizer — descartando resumen")
                summary = ""
        if summary:
            self.summarizer.current_summary = summary
            self.summarizer.summaries_count = session.get("summarizer_count", 0)
        conversation = session.get("conversation", [])
        if conversation:
            for msg in conversation:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # Skip contaminated assistant messages
                    if msg["role"] == "assistant":
                        content_lower = msg["content"].lower()
                        if any(bad in content_lower for bad in _bad_phrases):
                            self.log.debug(f"Mensaje contaminado filtrado: {msg['content'][:60]}...")
                            continue  # Skip this contaminated message
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


def print_banner():
    """Muestra el banner de inicio estilo JARVIS."""
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
  ║          Autonomous Self-Evolving AI System              ║
  ║               [ JARVIS // ULTRON MODE ]                  ║
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

    # === JARVIS BRIEFING ===
    print(genesis.startup_briefing())

    # LLM check
    if not genesis.brain.is_available():
        print(f"\n  [ALERTA] LLM no disponible ({LLM_PROVIDER}). Respuestas degradadas.")
        if LLM_PROVIDER == "ollama":
            print("    Ejecutar: ollama serve && ollama pull llama3.1")
    print("")

    # Subsistemas activos (resumen compacto)
    active_subsystems = 0
    subsystem_attrs = [
        "evaluator", "skill_memory", "chain_engine", "episodic_memory",
        "meta_learner", "goal_manager", "reflection", "concept_synth",
        "strategic_planner", "pattern_predictor", "anomaly_detector",
        "dream_engine", "self_narrative", "emotion_reader", "empathy_engine",
        "cognitive_monitor", "unified_mind", "code_architect", "peer_debate",
    ]
    for attr in subsystem_attrs:
        obj = getattr(genesis, attr, None)
        if obj is not None:
            active_subsystems += 1
    print(f"  Subsistemas activos: {active_subsystems + 20}+ modulos cargados")
    print(f"  Usa /briefing para diagnostico completo.")
    print(f"  Usa /help para ver todos los comandos.\n")
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
