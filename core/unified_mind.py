"""
GENESIS — Unified Mind (v3.0)

Estado de consciencia unificado cross-módulo. Sintetiza señales de
todos los subsistemas en un snapshot coherente: mood, focus, energy,
curiosity, confidence. Permite a Genesis "sentir" su propio estado
global y tomar decisiones meta-cognitivas.

Componentes:
- ConsciousnessState: snapshot del estado interno
- MoodComputer: calcula mood a partir de señales
- FocusTracker: rastrea enfoque temático
- UnifiedMind: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class ConsciousnessState:
    """Snapshot del estado de consciencia en un momento dado."""

    def __init__(self):
        self.mood = 0.5           # 0=negativo, 0.5=neutro, 1=positivo
        self.energy = 0.7         # 0=agotado, 1=máxima energía
        self.focus = 0.5          # 0=disperso, 1=concentrado
        self.curiosity = 0.5     # 0=indiferente, 1=muy curioso
        self.confidence = 0.5    # 0=inseguro, 1=seguro
        self.current_domain = "general"
        self.timestamp = time.time()

    @property
    def overall_state(self) -> str:
        """Estado general resumido."""
        score = (self.mood + self.energy + self.focus +
                 self.curiosity + self.confidence) / 5.0
        if score >= 0.8:
            return "optimal"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "neutral"
        elif score >= 0.2:
            return "low"
        return "critical"

    @property
    def awareness_score(self) -> float:
        """Puntuación de consciencia total (0-1)."""
        return (self.mood + self.energy + self.focus +
                self.curiosity + self.confidence) / 5.0

    def to_dict(self) -> dict:
        return {
            "mood": round(self.mood, 3),
            "energy": round(self.energy, 3),
            "focus": round(self.focus, 3),
            "curiosity": round(self.curiosity, 3),
            "confidence": round(self.confidence, 3),
            "overall_state": self.overall_state,
            "awareness_score": round(self.awareness_score, 3),
            "current_domain": self.current_domain,
            "timestamp": self.timestamp,
        }


class MoodComputer:
    """Calcula mood a partir de señales de interacción."""

    # Señales positivas → suben mood
    POSITIVE_SIGNALS = [
        "gracias", "perfecto", "excelente", "genial", "increible",
        "funciona", "correcto", "great", "awesome", "thanks",
        "bien hecho", "buenisimo",
    ]

    # Señales negativas → bajan mood
    NEGATIVE_SIGNALS = [
        "error", "falla", "no funciona", "mal", "incorrecto",
        "terrible", "horrible", "lento", "bug", "broken",
        "no sirve", "basura",
    ]

    def __init__(self):
        self.mood_history = deque(maxlen=20)
        self.current_mood = 0.5

    def process(self, text: str) -> float:
        """Procesa texto y actualiza mood. Retorna mood actual."""
        text_lower = text.lower()

        pos = sum(1 for s in self.POSITIVE_SIGNALS if s in text_lower)
        neg = sum(1 for s in self.NEGATIVE_SIGNALS if s in text_lower)

        if pos + neg > 0:
            delta = (pos - neg) * 0.05
            self.current_mood = max(0.0, min(1.0, self.current_mood + delta))

        # Decay hacia neutro
        self.current_mood = self.current_mood * 0.95 + 0.5 * 0.05

        self.mood_history.append(self.current_mood)
        return self.current_mood


class FocusTracker:
    """Rastrea el enfoque temático de la conversación."""

    def __init__(self):
        self.domain_counts = defaultdict(int)
        self.recent_domains = deque(maxlen=20)
        self.focus_score = 0.5

    def record(self, domain: str):
        """Registra el dominio de una interacción."""
        self.domain_counts[domain] += 1
        self.recent_domains.append(domain)
        self._update_focus()

    def _update_focus(self):
        """Calcula focus basado en consistencia de dominio."""
        if len(self.recent_domains) < 2:
            self.focus_score = 0.5
            return

        # Si todos los recientes son del mismo dominio → alto focus
        domains = list(self.recent_domains)
        most_common = max(set(domains), key=domains.count)
        ratio = domains.count(most_common) / len(domains)
        self.focus_score = ratio

    @property
    def dominant_domain(self) -> str:
        """Dominio más frecuente reciente."""
        if not self.recent_domains:
            return "general"
        domains = list(self.recent_domains)
        return max(set(domains), key=domains.count)

    def to_dict(self) -> dict:
        return {
            "domain_counts": dict(self.domain_counts),
            "focus_score": round(self.focus_score, 3),
            "dominant_domain": self.dominant_domain,
        }


class UnifiedMind:
    """
    Coordinador de consciencia unificada.
    Sintetiza el estado global del sistema.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/unified_mind")
        self.data_file = self.base_dir / "mind_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.mood_computer = MoodComputer()
        self.focus_tracker = FocusTracker()
        self.state_history = deque(maxlen=100)
        self.total_observations = 0
        self.peak_awareness = 0.0
        self.enabled = True

        # Estado actual
        self.current_state = ConsciousnessState()

        self._load()

    def observe(self, user_input: str, response: str = "",
                domain: str = "general", response_time: float = 0.0,
                quality_score: float = 0.5):
        """Observa una interacción y actualiza el estado de consciencia."""
        if not self.enabled or not user_input:
            return

        self.total_observations += 1
        combined = f"{user_input} {response}"

        # Mood
        self.current_state.mood = self.mood_computer.process(combined)

        # Energy (inverso de fatiga)
        # Si muchas interacciones recientes → baja energía
        recent_count = min(20, self.total_observations)
        self.current_state.energy = max(0.2, 1.0 - (recent_count / 50.0))

        # Focus
        self.focus_tracker.record(domain)
        self.current_state.focus = self.focus_tracker.focus_score

        # Curiosity (preguntas del usuario)
        text_lower = user_input.lower()
        curiosity_signals = ["?", "que", "como", "por que", "cuando", "donde"]
        curiosity_hits = sum(1 for s in curiosity_signals if s in text_lower)
        if curiosity_hits > 0:
            self.current_state.curiosity = min(1.0,
                                                self.current_state.curiosity * 0.8 + 0.3)
        else:
            self.current_state.curiosity = self.current_state.curiosity * 0.95

        # Confidence (basado en calidad de respuesta)
        self.current_state.confidence = (
            self.current_state.confidence * 0.7 + quality_score * 0.3
        )

        self.current_state.current_domain = domain
        self.current_state.timestamp = time.time()

        # Peak awareness
        score = self.current_state.awareness_score
        if score > self.peak_awareness:
            self.peak_awareness = score

        # Historial
        self.state_history.append(self.current_state.to_dict())

    def get_state(self) -> ConsciousnessState:
        """Retorna el estado de consciencia actual."""
        return self.current_state

    def get_state_summary(self) -> str:
        """Resumen del estado actual en texto."""
        s = self.current_state
        parts = []
        if s.mood > 0.7:
            parts.append("animado")
        elif s.mood < 0.3:
            parts.append("bajo")
        if s.energy > 0.7:
            parts.append("energetico")
        elif s.energy < 0.3:
            parts.append("fatigado")
        if s.focus > 0.7:
            parts.append("enfocado")
        elif s.focus < 0.3:
            parts.append("disperso")
        if s.curiosity > 0.7:
            parts.append("curioso")
        if s.confidence > 0.7:
            parts.append("seguro")
        elif s.confidence < 0.3:
            parts.append("inseguro")

        if not parts:
            return "neutral"
        return ", ".join(parts)

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de consciencia para prompt."""
        if not self.enabled:
            return ""

        s = self.current_state
        if s.overall_state in ("neutral", "good", "optimal"):
            return ""

        summary = self.get_state_summary()
        result = f"[ESTADO INTERNO: {s.overall_state}] {summary}"
        return result[:max_chars]

    def get_stats(self) -> dict:
        s = self.current_state
        return {
            "mood": round(s.mood, 3),
            "energy": round(s.energy, 3),
            "focus": round(s.focus, 3),
            "curiosity": round(s.curiosity, 3),
            "confidence": round(s.confidence, 3),
            "overall_state": s.overall_state,
            "awareness_score": round(s.awareness_score, 3),
            "peak_awareness": round(self.peak_awareness, 3),
            "total_observations": self.total_observations,
            "dominant_domain": self.focus_tracker.dominant_domain,
        }

    def status(self) -> str:
        s = self.current_state
        summary = self.get_state_summary()
        return (f"Estado: {s.overall_state} ({summary}) | "
                f"Awareness: {s.awareness_score:.0%} | "
                f"Observaciones: {self.total_observations}")

    def generate_report(self) -> str:
        lines = ["=== UNIFIED MIND REPORT ==="]
        s = self.current_state

        lines.append(f"Estado general: {s.overall_state}")
        lines.append(f"Resumen: {self.get_state_summary()}")
        lines.append(f"Total observaciones: {self.total_observations}")
        lines.append(f"Peak awareness: {self.peak_awareness:.1%}")

        lines.append(f"\nDimensiones:")
        dims = [
            ("Mood", s.mood), ("Energy", s.energy),
            ("Focus", s.focus), ("Curiosity", s.curiosity),
            ("Confidence", s.confidence),
        ]
        for name, val in dims:
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            lines.append(f"  {name:12s} [{bar}] {val:.0%}")

        lines.append(f"\nDominio dominante: {self.focus_tracker.dominant_domain}")
        if self.focus_tracker.domain_counts:
            lines.append("Dominios visitados:")
            for d, c in sorted(self.focus_tracker.domain_counts.items(),
                               key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"  {d}: {c} interacciones")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_observations": self.total_observations,
            "peak_awareness": self.peak_awareness,
            "mood": self.mood_computer.current_mood,
            "focus_domains": dict(self.focus_tracker.domain_counts),
            "state": self.current_state.to_dict(),
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_observations = data.get("total_observations", 0)
            self.peak_awareness = data.get("peak_awareness", 0.0)
            self.mood_computer.current_mood = data.get("mood", 0.5)
            for k, v in data.get("focus_domains", {}).items():
                self.focus_tracker.domain_counts[k] = v
            state_data = data.get("state", {})
            if state_data:
                self.current_state.mood = state_data.get("mood", 0.5)
                self.current_state.energy = state_data.get("energy", 0.7)
                self.current_state.focus = state_data.get("focus", 0.5)
                self.current_state.curiosity = state_data.get("curiosity", 0.5)
                self.current_state.confidence = state_data.get("confidence", 0.5)
                self.current_state.current_domain = state_data.get("current_domain", "general")
        except Exception:
            pass

    def clear(self):
        self.current_state = ConsciousnessState()
        self.mood_computer = MoodComputer()
        self.focus_tracker = FocusTracker()
        self.state_history.clear()
        self.total_observations = 0
        self.peak_awareness = 0.0
