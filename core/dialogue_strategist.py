"""
GENESIS — Dialogue Strategist (v2.8)

Estrategia de diálogo adaptativa. Selecciona el estilo de conversación
(socrático, didáctico, exploratorio, directivo) según contexto, intent
y perfil del usuario. Optimiza la interacción para máximo engagement.

Componentes:
- DialogueStrategy: estrategia con directivas y condiciones
- StrategySelector: selecciona la mejor estrategia por contexto
- EngagementTracker: rastrea engagement por estrategia
- DialogueStrategist: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict


class DialogueStrategy:
    """Una estrategia de diálogo con directivas."""

    STRATEGIES = {
        "socratic": {
            "name": "Socrático",
            "directive": "Guia al usuario con preguntas que le hagan descubrir la respuesta por si mismo. No des la respuesta directa; haz preguntas progresivas.",
            "conditions": ["curiosidad", "aprendizaje", "conceptual"],
            "engagement_boost": 0.3,
        },
        "didactic": {
            "name": "Didáctico",
            "directive": "Explica de forma estructurada y clara. Usa ejemplos, definiciones y analogias. Organiza la informacion de lo simple a lo complejo.",
            "conditions": ["explicacion", "tutorial", "novato"],
            "engagement_boost": 0.2,
        },
        "exploratory": {
            "name": "Exploratorio",
            "directive": "Explora el tema junto al usuario. Sugiere direcciones, conecta ideas, plantea escenarios alternativos. Se creativo y abierto.",
            "conditions": ["brainstorm", "creatividad", "investigacion"],
            "engagement_boost": 0.25,
        },
        "directive": {
            "name": "Directivo",
            "directive": "Se directo y conciso. Da la solucion o respuesta inmediatamente. Sin rodeos ni explicaciones innecesarias.",
            "conditions": ["urgente", "codigo", "fix", "error"],
            "engagement_boost": 0.1,
        },
        "collaborative": {
            "name": "Colaborativo",
            "directive": "Trabaja con el usuario como un par. Propone ideas, pide feedback, itera juntos. Construye sobre las ideas del usuario.",
            "conditions": ["proyecto", "diseño", "arquitectura"],
            "engagement_boost": 0.25,
        },
        "reflective": {
            "name": "Reflexivo",
            "directive": "Reflexiona sobre la conversacion. Resume lo discutido, identifica patrones, sugiere conexiones. Ayuda al usuario a ver el panorama completo.",
            "conditions": ["resumen", "revision", "retrospectiva"],
            "engagement_boost": 0.2,
        },
    }

    def __init__(self, strategy_key: str):
        config = self.STRATEGIES.get(strategy_key, self.STRATEGIES["didactic"])
        self.key = strategy_key
        self.name = config["name"]
        self.directive = config["directive"]
        self.conditions = config["conditions"]
        self.engagement_boost = config["engagement_boost"]


class StrategySelector:
    """Selecciona la mejor estrategia según contexto."""

    # Mapeo de señales a estrategias
    SIGNAL_MAP = {
        # Señales socrático
        "por que": "socratic", "why": "socratic",
        "como se llega a": "socratic", "como descubrir": "socratic",

        # Señales didáctico
        "explica": "didactic", "que es": "didactic",
        "como funciona": "didactic", "tutorial": "didactic",
        "enseñame": "didactic", "aprende": "didactic",

        # Señales exploratorio
        "que pasa si": "exploratory", "ideas para": "exploratory",
        "brainstorm": "exploratory", "posibilidades": "exploratory",
        "alternativas": "exploratory",

        # Señales directivo
        "fix": "directive", "error": "directive",
        "rapido": "directive", "urgente": "directive",
        "solo el codigo": "directive", "solucion": "directive",

        # Señales colaborativo
        "diseñemos": "collaborative", "construyamos": "collaborative",
        "proyecto": "collaborative", "arquitectura": "collaborative",

        # Señales reflexivo
        "resumen": "reflective", "hasta ahora": "reflective",
        "revision": "reflective", "panorama": "reflective",
    }

    def select(self, user_input: str, intent: str = "",
               conversation_length: int = 0) -> str:
        """Selecciona la mejor estrategia."""
        text_lower = user_input.lower()

        # Prioridad 1: señales explícitas en el input
        scores = defaultdict(float)
        for signal, strategy in self.SIGNAL_MAP.items():
            if signal in text_lower:
                scores[strategy] += 1.0

        # Prioridad 2: intent del router
        intent_map = {
            "code": "directive",
            "debug": "directive",
            "explain": "didactic",
            "creative": "exploratory",
            "question": "socratic",
            "chat": "collaborative",
        }
        if intent in intent_map:
            scores[intent_map[intent]] += 0.5

        # Prioridad 3: longitud de conversación
        if conversation_length > 20:
            scores["reflective"] += 0.3
        elif conversation_length < 3:
            scores["didactic"] += 0.2

        if not scores:
            return "didactic"  # Default

        return max(scores, key=scores.get)


class EngagementTracker:
    """Rastrea engagement por estrategia."""

    def __init__(self):
        self.strategy_usage = defaultdict(int)
        self.strategy_feedback = defaultdict(lambda: {"positive": 0, "negative": 0})
        self.strategy_response_lengths = defaultdict(list)
        self.total_interactions = 0

    def record(self, strategy_key: str, response_length: int = 0):
        """Registra uso de una estrategia."""
        self.strategy_usage[strategy_key] += 1
        self.total_interactions += 1
        if response_length > 0:
            lengths = self.strategy_response_lengths[strategy_key]
            lengths.append(response_length)
            if len(lengths) > 50:
                self.strategy_response_lengths[strategy_key] = lengths[-50:]

    def record_feedback(self, strategy_key: str, positive: bool):
        """Registra feedback para una estrategia."""
        fb = self.strategy_feedback[strategy_key]
        if positive:
            fb["positive"] += 1
        else:
            fb["negative"] += 1

    def get_effectiveness(self, strategy_key: str) -> float:
        """Calcula efectividad de una estrategia."""
        fb = self.strategy_feedback.get(strategy_key, {"positive": 0, "negative": 0})
        total = fb["positive"] + fb["negative"]
        if total == 0:
            return 0.5
        return fb["positive"] / total

    def get_best_strategy(self) -> str:
        """Retorna la estrategia más efectiva."""
        if not self.strategy_usage:
            return "didactic"
        best = max(self.strategy_usage.keys(),
                   key=lambda k: self.get_effectiveness(k))
        return best

    def to_dict(self) -> dict:
        return {
            "usage": dict(self.strategy_usage),
            "feedback": {k: dict(v) for k, v in self.strategy_feedback.items()},
            "total_interactions": self.total_interactions,
        }

    def load_dict(self, data: dict):
        self.strategy_usage = defaultdict(int)
        self.strategy_feedback = defaultdict(lambda: {"positive": 0, "negative": 0})
        for k, v in data.get("usage", {}).items():
            self.strategy_usage[k] = v
        for k, v in data.get("feedback", {}).items():
            self.strategy_feedback[k] = v
        self.total_interactions = data.get("total_interactions", 0)


class DialogueStrategist:
    """
    Coordinador de estrategia de diálogo.
    Selecciona y aplica la mejor estrategia conversacional.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/dialogue")
        self.data_file = self.base_dir / "dialogue_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.selector = StrategySelector()
        self.tracker = EngagementTracker()
        self.current_strategy = "didactic"
        self.strategy_history = []
        self.max_history = 100
        self.enabled = True

        self._load()

    def select_strategy(self, user_input: str, intent: str = "",
                        conversation_length: int = 0) -> DialogueStrategy:
        """Selecciona la mejor estrategia para este turno."""
        if not self.enabled:
            return DialogueStrategy("didactic")

        key = self.selector.select(user_input, intent, conversation_length)
        strategy = DialogueStrategy(key)
        self.current_strategy = key
        self.strategy_history.append({
            "strategy": key,
            "timestamp": time.time(),
        })
        if len(self.strategy_history) > self.max_history:
            self.strategy_history = self.strategy_history[-self.max_history:]
        return strategy

    def record_interaction(self, strategy_key: str = None,
                           response_length: int = 0):
        """Registra resultado de interacción."""
        key = strategy_key or self.current_strategy
        self.tracker.record(key, response_length)

    def record_feedback(self, positive: bool, strategy_key: str = None):
        """Registra feedback del usuario."""
        key = strategy_key or self.current_strategy
        self.tracker.record_feedback(key, positive)

    def get_context_for_prompt(self, user_input: str,
                                max_chars: int = 300) -> str:
        """Genera directiva de diálogo para prompt."""
        if not self.enabled or not user_input:
            return ""

        strategy = self.select_strategy(user_input)

        # Solo inyectar si la confianza es suficiente
        if self.tracker.total_interactions < 2:
            return f"[ESTRATEGIA: {strategy.name}] {strategy.directive}"[:max_chars]

        effectiveness = self.tracker.get_effectiveness(strategy.key)
        if effectiveness < 0.3:
            # Estrategia inefectiva, sugerir la mejor alternativa
            best = self.tracker.get_best_strategy()
            if best != strategy.key:
                strategy = DialogueStrategy(best)

        return f"[ESTRATEGIA: {strategy.name}] {strategy.directive}"[:max_chars]

    def get_available_strategies(self) -> list:
        """Lista todas las estrategias disponibles."""
        return list(DialogueStrategy.STRATEGIES.keys())

    def get_strategy_info(self, key: str) -> dict:
        """Info de una estrategia."""
        config = DialogueStrategy.STRATEGIES.get(key)
        if not config:
            return {}
        return {
            "key": key,
            "name": config["name"],
            "directive": config["directive"],
            "conditions": config["conditions"],
            "usage": self.tracker.strategy_usage.get(key, 0),
            "effectiveness": self.tracker.get_effectiveness(key),
        }

    def get_stats(self) -> dict:
        strategy_stats = {}
        for key in DialogueStrategy.STRATEGIES:
            strategy_stats[key] = {
                "usage": self.tracker.strategy_usage.get(key, 0),
                "effectiveness": round(self.tracker.get_effectiveness(key), 3),
            }
        return {
            "current_strategy": self.current_strategy,
            "total_interactions": self.tracker.total_interactions,
            "strategy_stats": strategy_stats,
            "history_length": len(self.strategy_history),
        }

    def status(self) -> str:
        return (f"Estrategia actual: {self.current_strategy} | "
                f"Interacciones: {self.tracker.total_interactions} | "
                f"Historial: {len(self.strategy_history)}")

    def generate_report(self) -> str:
        lines = ["=== DIALOGUE STRATEGIST REPORT ==="]
        lines.append(f"Estrategia actual: {self.current_strategy}")
        lines.append(f"Total interacciones: {self.tracker.total_interactions}")

        lines.append(f"\nEstrategias:")
        for key, config in DialogueStrategy.STRATEGIES.items():
            usage = self.tracker.strategy_usage.get(key, 0)
            eff = self.tracker.get_effectiveness(key)
            bar = "█" * int(eff * 20) + "░" * (20 - int(eff * 20))
            active = " ← ACTIVA" if key == self.current_strategy else ""
            lines.append(f"  {config['name']:15s} [{bar}] eff={eff:.0%} "
                         f"uses={usage}{active}")

        if self.strategy_history:
            recent = self.strategy_history[-5:]
            lines.append(f"\nHistorial reciente:")
            for entry in recent:
                lines.append(f"  {entry['strategy']}")

        return "\n".join(lines)

    def save(self):
        data = {
            "current_strategy": self.current_strategy,
            "strategy_history": self.strategy_history[-self.max_history:],
            "tracker": self.tracker.to_dict(),
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.current_strategy = data.get("current_strategy", "didactic")
            self.strategy_history = data.get("strategy_history", [])
            self.tracker.load_dict(data.get("tracker", {}))
        except Exception:
            pass

    def clear(self):
        self.current_strategy = "didactic"
        self.strategy_history = []
        self.tracker = EngagementTracker()
