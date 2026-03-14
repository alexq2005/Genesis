"""
GENESIS — Conflict Resolver (v3.1)

Manejo de desacuerdos y correcciones del usuario. Detecta señales de
conflicto, selecciona estrategias de resolución y aprende patrones
de conflicto recurrentes.

Componentes:
- ConflictSignal: señal de conflicto detectada
- ConflictDetector: detecta desacuerdos por patrones
- ResolutionStrategy: estrategia de resolución
- EscalationTracker: mide escalación/resolución
- ConflictResolver: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class ConflictSignal:
    """Señal de conflicto detectada."""

    def __init__(self, level: str, trigger: str, text: str = ""):
        self.level = level        # mild, moderate, severe
        self.trigger = trigger    # frase que lo disparó
        self.text = text[:200]
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "trigger": self.trigger,
            "text": self.text,
            "timestamp": self.timestamp,
        }


class ConflictDetector:
    """Detecta señales de conflicto en el texto del usuario."""

    CONFLICT_PATTERNS = {
        "severe": [
            "no entiendes", "no entendes", "sos inutil", "eres inutil",
            "no sirves", "sos un desastre", "ya te dije", "cuantas veces",
            "me canse", "es la tercera vez", "siempre lo mismo",
            "you're useless", "you don't understand",
        ],
        "moderate": [
            "no, eso esta mal", "eso no es correcto", "te equivocas",
            "eso no es lo que pedi", "no era eso", "otra cosa",
            "estas equivocado", "mal", "incorrecto", "wrong",
            "no es asi", "eso no funciona", "no me sirve",
            "that's wrong", "not what i asked",
        ],
        "mild": [
            "no exactamente", "casi pero", "no del todo",
            "mmm no", "nah", "no creo", "bueno pero",
            "hmm", "en realidad", "actually",
            "no tan", "mas o menos", "parcialmente",
        ],
    }

    def detect(self, text: str) -> ConflictSignal:
        """Detecta conflicto en el texto. Retorna señal o None."""
        text_lower = text.lower().strip()

        for level in ["severe", "moderate", "mild"]:
            for pattern in self.CONFLICT_PATTERNS[level]:
                if pattern in text_lower:
                    return ConflictSignal(level=level, trigger=pattern, text=text)

        return None

    def is_correction(self, text: str) -> bool:
        """Detecta si el texto es una corrección."""
        correction_words = [
            "no,", "no.", "wrong", "mal", "incorrecto",
            "en realidad", "actually", "corrijo",
        ]
        text_lower = text.lower().strip()
        return any(text_lower.startswith(w) or w in text_lower
                    for w in correction_words)


class ResolutionStrategy:
    """Estrategia de resolución de conflictos."""

    STRATEGIES = {
        "conceder": {
            "description": "Reconocer el error y corregir",
            "prompt": "Te equivocaste en algo. Reconoce el error directamente sin excusas, corrige tu respuesta.",
            "for_levels": ["moderate", "severe"],
        },
        "reformular": {
            "description": "Reformular la respuesta desde otra perspectiva",
            "prompt": "Tu respuesta anterior no fue clara. Reformula completamente usando un enfoque diferente.",
            "for_levels": ["mild", "moderate"],
        },
        "clarificar": {
            "description": "Pedir clarificación para entender mejor",
            "prompt": "Puede que hayas malinterpretado. Haz una pregunta breve para clarificar exactamente que necesita el usuario.",
            "for_levels": ["mild"],
        },
        "alternativa": {
            "description": "Ofrecer alternativas al enfoque rechazado",
            "prompt": "El usuario rechazo tu enfoque. Ofrece 2-3 alternativas concretas diferentes.",
            "for_levels": ["moderate", "severe"],
        },
    }

    def __init__(self, name: str):
        config = self.STRATEGIES.get(name, self.STRATEGIES["conceder"])
        self.name = name
        self.description = config["description"]
        self.prompt = config["prompt"]
        self.for_levels = config["for_levels"]


class EscalationTracker:
    """Rastrea si los conflictos escalan o se resuelven."""

    def __init__(self, window: int = 10):
        self.events = deque(maxlen=window)
        self.resolved = 0
        self.escalated = 0
        self.total_conflicts = 0

    def record_conflict(self, level: str):
        """Registra un conflicto."""
        self.events.append({
            "type": "conflict",
            "level": level,
            "timestamp": time.time(),
        })
        self.total_conflicts += 1

    def record_resolution(self):
        """Registra una resolución (usuario contento después de conflicto)."""
        self.events.append({
            "type": "resolution",
            "timestamp": time.time(),
        })
        self.resolved += 1

    def is_escalating(self) -> bool:
        """Determina si la conversación está escalando."""
        if len(self.events) < 3:
            return False
        recent = list(self.events)[-5:]
        conflicts = sum(1 for e in recent if e["type"] == "conflict")
        return conflicts >= 3

    def get_resolution_rate(self) -> float:
        """Tasa de resolución de conflictos."""
        if self.total_conflicts == 0:
            return 1.0
        return self.resolved / self.total_conflicts

    def to_dict(self) -> dict:
        return {
            "events": list(self.events),
            "resolved": self.resolved,
            "escalated": self.escalated,
            "total_conflicts": self.total_conflicts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EscalationTracker":
        t = cls()
        for e in d.get("events", []):
            t.events.append(e)
        t.resolved = d.get("resolved", 0)
        t.escalated = d.get("escalated", 0)
        t.total_conflicts = d.get("total_conflicts", 0)
        return t


class ConflictResolver:
    """Coordinador de resolución de conflictos con persistencia."""

    def __init__(self, base_dir: str = "data/conflict"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.detector = ConflictDetector()
        self.tracker = EscalationTracker()
        self.conflict_patterns = defaultdict(int)  # Patrones recurrentes
        self.total_resolved = 0
        self.current_conflict = None
        self.last_strategy = ""

        self._load()

    def analyze(self, text: str) -> dict:
        """Analiza texto por conflictos. Retorna análisis."""
        signal = self.detector.detect(text)

        if signal is None:
            # Si había conflicto previo y ahora no, registrar resolución
            if self.current_conflict:
                self.tracker.record_resolution()
                self.total_resolved += 1
                self.current_conflict = None
            return {"conflict": False}

        # Registrar conflicto
        self.tracker.record_conflict(signal.level)
        self.conflict_patterns[signal.trigger] += 1
        self.current_conflict = signal

        # Seleccionar estrategia
        strategy = self._select_strategy(signal)
        self.last_strategy = strategy.name

        return {
            "conflict": True,
            "level": signal.level,
            "trigger": signal.trigger,
            "strategy": strategy.name,
            "prompt_modifier": strategy.prompt,
            "is_escalating": self.tracker.is_escalating(),
        }

    def _select_strategy(self, signal: ConflictSignal) -> ResolutionStrategy:
        """Selecciona estrategia basada en nivel y contexto."""
        # Si está escalando, siempre conceder
        if self.tracker.is_escalating():
            return ResolutionStrategy("conceder")

        # Por nivel
        if signal.level == "severe":
            return ResolutionStrategy("conceder")
        elif signal.level == "moderate":
            # Si es un patrón recurrente, ofrecer alternativa
            if self.conflict_patterns.get(signal.trigger, 0) >= 2:
                return ResolutionStrategy("alternativa")
            return ResolutionStrategy("reformular")
        else:  # mild
            return ResolutionStrategy("clarificar")

    def get_context_for_prompt(self, text: str, max_chars: int = 200) -> str:
        """Genera contexto de conflicto para inyectar en prompt."""
        analysis = self.analyze(text)
        if not analysis.get("conflict"):
            return ""

        parts = [f"[CONFLICTO: {analysis['level']}] {analysis['prompt_modifier']}"]
        if analysis.get("is_escalating"):
            parts.append("ATENCION: El conflicto esta escalando. Prioriza la resolucion.")

        return " ".join(parts)[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_conflicts": self.tracker.total_conflicts,
            "total_resolved": self.total_resolved,
            "resolution_rate": self.tracker.get_resolution_rate(),
            "is_escalating": self.tracker.is_escalating(),
            "last_strategy": self.last_strategy,
            "top_patterns": dict(sorted(
                self.conflict_patterns.items(),
                key=lambda x: x[1], reverse=True,
            )[:5]),
        }

    def status(self) -> str:
        rate = self.tracker.get_resolution_rate()
        esc = "SI" if self.tracker.is_escalating() else "no"
        return (f"  Conflictos: {self.tracker.total_conflicts} | "
                f"Resueltos: {self.total_resolved} ({rate:.0%}) | "
                f"Escalando: {esc}")

    def generate_report(self) -> str:
        lines = [
            "=== CONFLICT RESOLVER ===",
            f"Total conflictos: {self.tracker.total_conflicts}",
            f"Resueltos: {self.total_resolved}",
            f"Tasa de resolucion: {self.tracker.get_resolution_rate():.0%}",
            f"Escalando: {'SI' if self.tracker.is_escalating() else 'No'}",
            f"Ultima estrategia: {self.last_strategy}",
            "",
            "Patrones mas frecuentes:",
        ]
        for pattern, count in sorted(self.conflict_patterns.items(),
                                      key=lambda x: x[1], reverse=True)[:5]:
            lines.append(f"  '{pattern}': {count} veces")

        lines.append("")
        lines.append("Eventos recientes:")
        for event in list(self.tracker.events)[-5:]:
            etype = event["type"]
            if etype == "conflict":
                lines.append(f"  Conflicto ({event.get('level', '?')})")
            else:
                lines.append(f"  Resolucion")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_resolved": self.total_resolved,
            "last_strategy": self.last_strategy,
            "conflict_patterns": dict(self.conflict_patterns),
            "tracker": self.tracker.to_dict(),
        }
        path = self.base_dir / "conflict_resolver.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "conflict_resolver.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_resolved = data.get("total_resolved", 0)
            self.last_strategy = data.get("last_strategy", "")
            self.conflict_patterns = defaultdict(int, data.get("conflict_patterns", {}))
            if "tracker" in data:
                self.tracker = EscalationTracker.from_dict(data["tracker"])
        except Exception:
            pass

    def clear(self):
        self.tracker = EscalationTracker()
        self.conflict_patterns = defaultdict(int)
        self.total_resolved = 0
        self.current_conflict = None
        self.last_strategy = ""
        self.save()
