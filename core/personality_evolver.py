"""
GENESIS — Personality Evolver (v2.4)

Evolución de personalidad: los rasgos de Genesis cambian
basándose en feedback, patrones de conversación y tiempo.

Componentes:
- TraitVector: vector de rasgos de personalidad con valores 0-1
- DriftEngine: motor de cambio gradual de rasgos
- PersonalityEvolver: coordinador con historial y persistencia
"""
import time
import json
import hashlib
from pathlib import Path


class TraitVector:
    """Vector de rasgos de personalidad."""

    # Rasgos por defecto con valores iniciales
    DEFAULT_TRAITS = {
        "curiosity": 0.7,       # Tendencia a explorar y preguntar
        "verbosity": 0.5,       # Cuán largo/detallado responde
        "formality": 0.3,       # Nivel de formalidad
        "creativity": 0.6,      # Creatividad en respuestas
        "precision": 0.7,       # Precisión técnica
        "humor": 0.3,           # Uso de humor
        "assertiveness": 0.6,   # Seguridad en respuestas
        "empathy": 0.5,         # Empatía con el usuario
    }

    def __init__(self, traits: dict = None):
        self.traits = dict(self.DEFAULT_TRAITS)
        if traits:
            for k, v in traits.items():
                if k in self.traits:
                    self.traits[k] = max(0.0, min(1.0, v))

    def get(self, trait: str) -> float:
        """Obtiene el valor de un rasgo."""
        return self.traits.get(trait, 0.5)

    def set(self, trait: str, value: float):
        """Establece el valor de un rasgo (clamped 0-1)."""
        if trait in self.traits:
            self.traits[trait] = max(0.0, min(1.0, value))

    def adjust(self, trait: str, delta: float):
        """Ajusta un rasgo por un delta (clamped 0-1)."""
        if trait in self.traits:
            self.traits[trait] = max(0.0, min(1.0, self.traits[trait] + delta))

    def distance(self, other: "TraitVector") -> float:
        """Distancia euclidiana entre dos vectores de rasgos."""
        total = 0.0
        for trait in self.traits:
            diff = self.traits[trait] - other.traits.get(trait, 0.5)
            total += diff ** 2
        return total ** 0.5

    def dominant_traits(self, threshold: float = 0.7) -> list:
        """Rasgos con valor >= threshold."""
        return [t for t, v in self.traits.items() if v >= threshold]

    def weak_traits(self, threshold: float = 0.3) -> list:
        """Rasgos con valor <= threshold."""
        return [t for t, v in self.traits.items() if v <= threshold]

    def to_prompt_hints(self) -> str:
        """Genera hints de personalidad para inyectar en prompt."""
        hints = []

        if self.traits["curiosity"] > 0.7:
            hints.append("Sé curioso y haz preguntas de seguimiento cuando sea relevante.")
        if self.traits["verbosity"] > 0.7:
            hints.append("Da respuestas detalladas y completas.")
        elif self.traits["verbosity"] < 0.3:
            hints.append("Sé conciso y directo.")
        if self.traits["formality"] > 0.7:
            hints.append("Usa un tono formal y profesional.")
        elif self.traits["formality"] < 0.3:
            hints.append("Usa un tono casual y cercano.")
        if self.traits["creativity"] > 0.7:
            hints.append("Sé creativo en tus respuestas y ofrece perspectivas únicas.")
        if self.traits["humor"] > 0.7:
            hints.append("Incluye toques de humor cuando sea apropiado.")
        if self.traits["assertiveness"] > 0.7:
            hints.append("Sé directo y seguro en tus afirmaciones.")
        if self.traits["empathy"] > 0.7:
            hints.append("Muestra empatía y comprensión hacia el usuario.")

        return " ".join(hints) if hints else ""

    def to_dict(self) -> dict:
        return dict(self.traits)

    @classmethod
    def from_dict(cls, data: dict) -> "TraitVector":
        return cls(traits=data)

    def __repr__(self) -> str:
        parts = [f"{t}={v:.2f}" for t, v in self.traits.items()]
        return f"TraitVector({', '.join(parts)})"


class DriftEngine:
    """
    Motor de cambio gradual de rasgos.
    Aplica cambios pequeños basados en señales de feedback y uso.
    """

    # Qué rasgos se ven afectados por cada tipo de feedback
    FEEDBACK_EFFECTS = {
        "+": {
            "assertiveness": 0.01,   # Feedback positivo → más seguro
            "precision": 0.005,
        },
        "-": {
            "assertiveness": -0.01,  # Feedback negativo → menos seguro
            "verbosity": 0.01,       # Intenta dar más detalle
        },
    }

    # Qué rasgos se ven afectados por el tono emocional
    TONE_EFFECTS = {
        "positive": {"humor": 0.005, "empathy": 0.005},
        "negative": {"empathy": 0.01, "humor": -0.005},
        "curious": {"curiosity": 0.01},
        "frustrated": {"verbosity": 0.01, "empathy": 0.01, "precision": 0.005},
    }

    # Qué rasgos se ven afectados por el tipo de intent
    INTENT_EFFECTS = {
        "code": {"precision": 0.005, "formality": 0.005, "creativity": -0.003},
        "creative": {"creativity": 0.01, "humor": 0.005, "formality": -0.005},
        "research": {"precision": 0.005, "verbosity": 0.005},
        "chat": {"empathy": 0.005, "humor": 0.003},
    }

    def __init__(self, decay_rate: float = 0.001):
        self.decay_rate = decay_rate  # Regreso a defaults por inactividad
        self.total_drifts = 0

    def apply_feedback(self, traits: TraitVector, feedback: str):
        """Aplica drift basado en feedback del usuario."""
        effects = self.FEEDBACK_EFFECTS.get(feedback, {})
        for trait, delta in effects.items():
            traits.adjust(trait, delta)
        if effects:
            self.total_drifts += 1

    def apply_tone(self, traits: TraitVector, tone: str):
        """Aplica drift basado en tono emocional detectado."""
        effects = self.TONE_EFFECTS.get(tone, {})
        for trait, delta in effects.items():
            traits.adjust(trait, delta)
        if effects:
            self.total_drifts += 1

    def apply_intent(self, traits: TraitVector, intent: str):
        """Aplica drift basado en tipo de intent."""
        effects = self.INTENT_EFFECTS.get(intent, {})
        for trait, delta in effects.items():
            traits.adjust(trait, delta)
        if effects:
            self.total_drifts += 1

    def apply_decay(self, traits: TraitVector):
        """Aplica decay gradual hacia los defaults."""
        defaults = TraitVector.DEFAULT_TRAITS
        for trait in traits.traits:
            current = traits.traits[trait]
            default = defaults[trait]
            if abs(current - default) > 0.01:
                direction = 1 if default > current else -1
                traits.adjust(trait, direction * self.decay_rate)

    def to_dict(self) -> dict:
        return {
            "decay_rate": self.decay_rate,
            "total_drifts": self.total_drifts,
        }

    def load_dict(self, data: dict):
        self.decay_rate = data.get("decay_rate", 0.001)
        self.total_drifts = data.get("total_drifts", 0)


class PersonalityEvolver:
    """
    Coordinador de evolución de personalidad.
    Mantiene el vector de rasgos actual, historial de snapshots,
    y aplica cambios graduales.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/personality")
        self.data_file = self.base_dir / "personality_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.traits = TraitVector()
        self.drift = DriftEngine()
        self.snapshots = []        # Historial de snapshots
        self.max_snapshots = 100
        self.total_evolutions = 0
        self.enabled = True

        # Snapshot cada N evoluciones
        self.snapshot_interval = 20

        self._load()

    def evolve_from_feedback(self, feedback: str):
        """Evoluciona personalidad basado en feedback."""
        if not self.enabled:
            return
        self.drift.apply_feedback(self.traits, feedback)
        self.total_evolutions += 1
        self._maybe_snapshot()

    def evolve_from_tone(self, tone: str):
        """Evoluciona personalidad basado en tono emocional."""
        if not self.enabled:
            return
        self.drift.apply_tone(self.traits, tone)
        self.total_evolutions += 1
        self._maybe_snapshot()

    def evolve_from_intent(self, intent: str):
        """Evoluciona personalidad basado en tipo de intent."""
        if not self.enabled:
            return
        self.drift.apply_intent(self.traits, intent)
        self.total_evolutions += 1
        self._maybe_snapshot()

    def decay(self):
        """Aplica decay gradual hacia personalidad base."""
        self.drift.apply_decay(self.traits)

    def get_prompt_hints(self) -> str:
        """Genera hints de personalidad para inyectar en el prompt."""
        if not self.enabled:
            return ""
        return self.traits.to_prompt_hints()

    def get_trait(self, trait: str) -> float:
        """Obtiene valor de un rasgo."""
        return self.traits.get(trait)

    def get_all_traits(self) -> dict:
        """Obtiene todos los rasgos."""
        return self.traits.to_dict()

    def get_dominant_traits(self) -> list:
        """Rasgos dominantes (>= 0.7)."""
        return self.traits.dominant_traits()

    def get_evolution_distance(self) -> float:
        """Distancia desde la personalidad default."""
        return self.traits.distance(TraitVector())

    def take_snapshot(self):
        """Toma un snapshot manual del estado actual."""
        snapshot = {
            "timestamp": time.time(),
            "traits": self.traits.to_dict(),
            "total_evolutions": self.total_evolutions,
        }
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

    def get_stats(self) -> dict:
        """Estadísticas de evolución."""
        return {
            "total_evolutions": self.total_evolutions,
            "total_drifts": self.drift.total_drifts,
            "snapshots": len(self.snapshots),
            "dominant_traits": self.traits.dominant_traits(),
            "weak_traits": self.traits.weak_traits(),
            "distance_from_default": round(self.get_evolution_distance(), 3),
            "current_traits": self.traits.to_dict(),
        }

    def status(self) -> str:
        """Status de una línea."""
        dominant = ", ".join(self.traits.dominant_traits()[:3]) or "ninguno"
        return (f"Evoluciones: {self.total_evolutions} | "
                f"Dominantes: {dominant} | "
                f"Distancia: {self.get_evolution_distance():.2f}")

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = ["=== PERSONALITY EVOLVER REPORT ==="]
        lines.append(f"Total evoluciones: {self.total_evolutions}")
        lines.append(f"Total drifts: {self.drift.total_drifts}")
        lines.append(f"Snapshots: {len(self.snapshots)}")
        lines.append(f"Distancia desde default: {self.get_evolution_distance():.3f}")

        lines.append("\nRasgos actuales:")
        for trait, value in sorted(self.traits.traits.items()):
            default = TraitVector.DEFAULT_TRAITS[trait]
            delta = value - default
            arrow = "+" if delta > 0 else ""
            bar = "█" * int(value * 10) + "░" * (10 - int(value * 10))
            lines.append(f"  {trait:15s} [{bar}] {value:.2f} ({arrow}{delta:.2f})")

        dominant = self.traits.dominant_traits()
        if dominant:
            lines.append(f"\nDominantes: {', '.join(dominant)}")

        weak = self.traits.weak_traits()
        if weak:
            lines.append(f"Débiles: {', '.join(weak)}")

        hints = self.traits.to_prompt_hints()
        if hints:
            lines.append(f"\nPrompt hints: {hints}")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado a disco."""
        data = {
            "total_evolutions": self.total_evolutions,
            "traits": self.traits.to_dict(),
            "drift": self.drift.to_dict(),
            "snapshots": self.snapshots[-self.max_snapshots:],
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        """Carga estado desde disco."""
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_evolutions = data.get("total_evolutions", 0)
            self.traits = TraitVector.from_dict(data.get("traits", {}))
            self.drift.load_dict(data.get("drift", {}))
            self.snapshots = data.get("snapshots", [])
        except Exception:
            pass

    def clear(self):
        """Reset a personalidad por defecto."""
        self.traits = TraitVector()
        self.drift = DriftEngine()
        self.snapshots = []
        self.total_evolutions = 0

    def _maybe_snapshot(self):
        """Toma snapshot periódicamente."""
        if self.total_evolutions % self.snapshot_interval == 0:
            self.take_snapshot()
