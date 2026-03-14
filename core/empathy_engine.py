"""
GENESIS — Empathy Engine (v3.1)

Generación de respuestas empáticas basadas en emociones detectadas.
Selecciona estrategias de empatía y modifica el prompt para ajustar
el tono sin cambiar el contenido técnico.

Componentes:
- EmpathyStrategy: estrategia de respuesta empática
- StrategySelector: selección automática por emoción
- EffectivenessTracker: tracking de efectividad
- EmpathyEngine: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class EmpathyStrategy:
    """Estrategia de respuesta empática."""

    STRATEGIES = {
        "validar": {
            "description": "Reconocer y validar la emocion del usuario",
            "triggers": ["frustracion", "confusion"],
            "prompt_modifier": "Antes de responder, reconoce brevemente lo que el usuario siente. Muestra que entiendes su situacion.",
            "priority": 5,
        },
        "redirigir": {
            "description": "Redirigir de emocion negativa hacia solucion",
            "triggers": ["frustracion", "urgencia"],
            "prompt_modifier": "El usuario esta frustrado. Enfocate directamente en la solucion, se conciso y practico. Evita explicaciones largas.",
            "priority": 4,
        },
        "profundizar": {
            "description": "Explorar mas la necesidad emocional del usuario",
            "triggers": ["curiosidad", "confusion"],
            "prompt_modifier": "El usuario tiene curiosidad genuina. Responde con profundidad educativa, usando analogias claras.",
            "priority": 3,
        },
        "celebrar": {
            "description": "Compartir la alegria o logro del usuario",
            "triggers": ["alegria"],
            "prompt_modifier": "El usuario esta contento con algo. Responde con entusiasmo genuino, refuerza su logro.",
            "priority": 4,
        },
        "calmar": {
            "description": "Reducir la urgencia o ansiedad",
            "triggers": ["urgencia"],
            "prompt_modifier": "El usuario siente urgencia. Se directo y estructurado. Prioriza la accion inmediata, luego explica.",
            "priority": 5,
        },
    }

    def __init__(self, name: str):
        config = self.STRATEGIES.get(name, self.STRATEGIES["validar"])
        self.name = name
        self.description = config["description"]
        self.triggers = config["triggers"]
        self.prompt_modifier = config["prompt_modifier"]
        self.priority = config["priority"]

    @classmethod
    def get_all(cls) -> list:
        return list(cls.STRATEGIES.keys())


class StrategySelector:
    """Selecciona estrategia de empatía por emoción detectada."""

    def __init__(self):
        self.strategies = {name: EmpathyStrategy(name)
                           for name in EmpathyStrategy.STRATEGIES}

    def select(self, emotion: str, intensity: float = 0.5,
               history: list = None) -> str:
        """Selecciona la mejor estrategia para la emoción dada."""
        candidates = []

        for name, strategy in self.strategies.items():
            if emotion in strategy.triggers:
                score = strategy.priority * intensity
                candidates.append((name, score))

        if not candidates:
            # Fallback: si es positivo → celebrar, si no → validar
            if emotion == "alegria":
                return "celebrar"
            return "validar"

        # Si hay historial y la emoción es recurrente, preferir redirigir
        if history and len(history) >= 3:
            recent = history[-3:]
            recent_emotions = [e.get("emotion", "") for e in recent]
            if recent_emotions.count(emotion) >= 2 and emotion in ("frustracion", "confusion"):
                return "redirigir"

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]


class EffectivenessTracker:
    """Rastrea la efectividad de cada estrategia."""

    def __init__(self):
        self.usage = defaultdict(int)
        self.feedback_positive = defaultdict(int)
        self.feedback_negative = defaultdict(int)
        self.total_uses = 0

    def record_use(self, strategy: str):
        """Registra uso de estrategia."""
        self.usage[strategy] += 1
        self.total_uses += 1

    def record_feedback(self, strategy: str, positive: bool):
        """Registra feedback para la estrategia usada."""
        if positive:
            self.feedback_positive[strategy] += 1
        else:
            self.feedback_negative[strategy] += 1

    def get_effectiveness(self, strategy: str) -> float:
        """Retorna efectividad (0-1) de una estrategia."""
        pos = self.feedback_positive.get(strategy, 0)
        neg = self.feedback_negative.get(strategy, 0)
        total = pos + neg
        if total == 0:
            return 0.5  # Sin datos, asumir neutral
        return pos / total

    def get_best_strategy(self) -> str:
        """Retorna la estrategia más efectiva."""
        if not self.usage:
            return "validar"
        best = max(self.usage.keys(), key=lambda s: self.get_effectiveness(s))
        return best

    def to_dict(self) -> dict:
        return {
            "usage": dict(self.usage),
            "feedback_positive": dict(self.feedback_positive),
            "feedback_negative": dict(self.feedback_negative),
            "total_uses": self.total_uses,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EffectivenessTracker":
        t = cls()
        t.usage = defaultdict(int, d.get("usage", {}))
        t.feedback_positive = defaultdict(int, d.get("feedback_positive", {}))
        t.feedback_negative = defaultdict(int, d.get("feedback_negative", {}))
        t.total_uses = d.get("total_uses", 0)
        return t


class EmpathyEngine:
    """Coordinador de empatía con persistencia."""

    def __init__(self, base_dir: str = "data/empathy"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.selector = StrategySelector()
        self.tracker = EffectivenessTracker()
        self.current_strategy = "validar"
        self.total_empathy_responses = 0
        self.last_emotion = "neutral"

        self._load()

    def respond(self, emotion: str, intensity: float = 0.5,
                history: list = None) -> dict:
        """Genera respuesta empática para la emoción dada."""
        strategy_name = self.selector.select(emotion, intensity, history)
        strategy = self.selector.strategies[strategy_name]

        self.current_strategy = strategy_name
        self.last_emotion = emotion
        self.tracker.record_use(strategy_name)
        self.total_empathy_responses += 1

        return {
            "strategy": strategy_name,
            "prompt_modifier": strategy.prompt_modifier,
            "description": strategy.description,
            "emotion": emotion,
            "intensity": intensity,
        }

    def record_feedback(self, positive: bool):
        """Registra feedback sobre la última respuesta empática."""
        if self.current_strategy:
            self.tracker.record_feedback(self.current_strategy, positive)

    def get_context_for_prompt(self, emotion: str = "",
                                intensity: float = 0.0,
                                max_chars: int = 200) -> str:
        """Genera modificador de prompt basado en la emoción."""
        if not emotion or emotion == "neutral" or intensity < 0.3:
            return ""

        result = self.respond(emotion, intensity)
        context = f"[EMPATIA] {result['prompt_modifier']}"
        return context[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_empathy_responses": self.total_empathy_responses,
            "current_strategy": self.current_strategy,
            "last_emotion": self.last_emotion,
            "effectiveness": {
                name: self.tracker.get_effectiveness(name)
                for name in EmpathyStrategy.STRATEGIES
            },
            "usage": dict(self.tracker.usage),
            "best_strategy": self.tracker.get_best_strategy(),
        }

    def status(self) -> str:
        best = self.tracker.get_best_strategy()
        eff = self.tracker.get_effectiveness(best)
        return (f"  Respuestas: {self.total_empathy_responses} | "
                f"Estrategia actual: {self.current_strategy} | "
                f"Mejor: {best} ({eff:.0%})")

    def generate_report(self) -> str:
        lines = [
            "=== EMPATHY ENGINE ===",
            f"Total respuestas empaticas: {self.total_empathy_responses}",
            f"Estrategia actual: {self.current_strategy}",
            f"Ultima emocion: {self.last_emotion}",
            "",
            "Efectividad por estrategia:",
        ]
        for name in EmpathyStrategy.STRATEGIES:
            uses = self.tracker.usage.get(name, 0)
            eff = self.tracker.get_effectiveness(name)
            pos = self.tracker.feedback_positive.get(name, 0)
            neg = self.tracker.feedback_negative.get(name, 0)
            lines.append(f"  {name}: {uses} usos, {eff:.0%} efectividad ({pos}+/{neg}-)")

        lines.append(f"\nMejor estrategia: {self.tracker.get_best_strategy()}")
        return "\n".join(lines)

    def save(self):
        data = {
            "total_empathy_responses": self.total_empathy_responses,
            "current_strategy": self.current_strategy,
            "last_emotion": self.last_emotion,
            "tracker": self.tracker.to_dict(),
        }
        path = self.base_dir / "empathy_engine.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "empathy_engine.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_empathy_responses = data.get("total_empathy_responses", 0)
            self.current_strategy = data.get("current_strategy", "validar")
            self.last_emotion = data.get("last_emotion", "neutral")
            if "tracker" in data:
                self.tracker = EffectivenessTracker.from_dict(data["tracker"])
        except Exception:
            pass

    def clear(self):
        self.tracker = EffectivenessTracker()
        self.current_strategy = "validar"
        self.last_emotion = "neutral"
        self.total_empathy_responses = 0
        self.save()
