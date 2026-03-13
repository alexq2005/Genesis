"""
GENESIS — Adaptive Interface (v2.7)

Interfaz adaptativa: aprende las preferencias del usuario
(verbosidad, nivel técnico, formato) y ajusta las respuestas.

Componentes:
- UserPreference: preferencia con valor bayesiano
- PreferenceTracker: tracking de preferencias por señales
- ResponseAdapter: genera directivas de estilo para el prompt
- AdaptiveInterface: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict


class UserPreference:
    """Una preferencia del usuario con tracking bayesiano."""

    def __init__(self, name: str, value: float = 0.5, confidence: float = 0.1):
        self.name = name
        self.value = max(0.0, min(1.0, value))    # 0.0 - 1.0
        self.confidence = max(0.0, min(1.0, confidence))
        self.observations = 0
        self.last_updated = time.time()

    def update(self, signal: float, weight: float = 1.0):
        """Actualiza la preferencia con una nueva observación."""
        self.observations += 1
        # Bayesian update: peso de la nueva observación decrece con más datos
        learning_rate = weight / (1 + self.observations * 0.1)
        self.value += learning_rate * (signal - self.value)
        self.value = max(0.0, min(1.0, self.value))
        self.confidence = min(1.0, self.confidence + 0.02)
        self.last_updated = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "confidence": round(self.confidence, 4),
            "observations": self.observations,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreference":
        p = cls(
            name=data.get("name", ""),
            value=data.get("value", 0.5),
            confidence=data.get("confidence", 0.1),
        )
        p.observations = data.get("observations", 0)
        p.last_updated = data.get("last_updated", time.time())
        return p


class PreferenceTracker:
    """Detecta preferencias del usuario desde señales implícitas."""

    # Señales de verbosidad
    VERBOSE_SIGNALS = ["explica", "detalla", "mas info", "como funciona",
                       "por que", "explain", "elaborate"]
    CONCISE_SIGNALS = ["resumen", "breve", "corto", "directo", "rapido",
                       "solo el codigo", "summary", "brief", "tldr"]

    # Señales de nivel técnico
    TECHNICAL_SIGNALS = ["implementa", "algoritmo", "complejidad", "optimiza",
                         "arquitectura", "patron", "benchmark", "refactoriza"]
    SIMPLE_SIGNALS = ["simple", "facil", "basico", "principiante", "eli5",
                      "para dummies", "sencillo"]

    # Señales de formato
    CODE_FORMAT_SIGNALS = ["codigo", "code", "script", "funcion", "implementa"]
    LIST_FORMAT_SIGNALS = ["lista", "pasos", "steps", "enumera", "bullet"]
    PROSE_FORMAT_SIGNALS = ["explica", "cuenta", "describe", "narra"]

    def detect_signals(self, text: str) -> dict:
        """Detecta señales de preferencia en el texto."""
        text_lower = text.lower()
        signals = {}

        # Verbosidad
        verbose_hits = sum(1 for s in self.VERBOSE_SIGNALS if s in text_lower)
        concise_hits = sum(1 for s in self.CONCISE_SIGNALS if s in text_lower)
        if verbose_hits > concise_hits:
            signals["verbosity"] = 0.8
        elif concise_hits > verbose_hits:
            signals["verbosity"] = 0.2
        elif verbose_hits > 0:
            signals["verbosity"] = 0.5

        # Nivel técnico
        tech_hits = sum(1 for s in self.TECHNICAL_SIGNALS if s in text_lower)
        simple_hits = sum(1 for s in self.SIMPLE_SIGNALS if s in text_lower)
        if tech_hits > simple_hits:
            signals["technical_level"] = 0.8
        elif simple_hits > tech_hits:
            signals["technical_level"] = 0.2
        elif tech_hits > 0:
            signals["technical_level"] = 0.5

        # Formato preferido
        code_hits = sum(1 for s in self.CODE_FORMAT_SIGNALS if s in text_lower)
        list_hits = sum(1 for s in self.LIST_FORMAT_SIGNALS if s in text_lower)
        prose_hits = sum(1 for s in self.PROSE_FORMAT_SIGNALS if s in text_lower)

        max_hits = max(code_hits, list_hits, prose_hits)
        if max_hits > 0:
            if code_hits == max_hits:
                signals["format_code"] = 0.8
            elif list_hits == max_hits:
                signals["format_list"] = 0.8
            elif prose_hits == max_hits:
                signals["format_prose"] = 0.8

        # Largo de input como señal de verbosidad esperada
        word_count = len(text.split())
        if word_count > 30:
            signals.setdefault("verbosity", 0.6)
        elif word_count < 5:
            signals.setdefault("verbosity", 0.3)

        return signals

    def detect_feedback_signals(self, feedback_positive: bool,
                                response_length: int) -> dict:
        """Señales desde feedback del usuario."""
        signals = {}
        if feedback_positive:
            # Si dio +, la verbosidad actual es buena
            if response_length > 500:
                signals["verbosity"] = 0.7
            elif response_length < 100:
                signals["verbosity"] = 0.3
        else:
            # Si dio -, invertir la señal de verbosidad
            if response_length > 500:
                signals["verbosity"] = 0.3  # Probablemente muy largo
            elif response_length < 100:
                signals["verbosity"] = 0.7  # Probablemente muy corto
        return signals


class ResponseAdapter:
    """Genera directivas de estilo para el prompt."""

    def generate_directives(self, preferences: dict) -> str:
        """Genera instrucciones de estilo basadas en preferencias."""
        directives = []

        # Verbosidad
        verbosity = preferences.get("verbosity", {})
        if isinstance(verbosity, UserPreference) and verbosity.confidence > 0.2:
            if verbosity.value > 0.7:
                directives.append("Responde de forma detallada y exhaustiva.")
            elif verbosity.value < 0.3:
                directives.append("Se breve y directo. Sin explicaciones innecesarias.")

        # Nivel técnico
        tech = preferences.get("technical_level", {})
        if isinstance(tech, UserPreference) and tech.confidence > 0.2:
            if tech.value > 0.7:
                directives.append("Usa terminologia tecnica avanzada.")
            elif tech.value < 0.3:
                directives.append("Explica en terminos simples, sin jerga.")

        # Formato
        for fmt_key in ["format_code", "format_list", "format_prose"]:
            fmt = preferences.get(fmt_key, {})
            if isinstance(fmt, UserPreference) and fmt.confidence > 0.2 and fmt.value > 0.6:
                if "code" in fmt_key:
                    directives.append("Prioriza ejemplos de codigo.")
                elif "list" in fmt_key:
                    directives.append("Organiza en listas/pasos numerados.")
                elif "prose" in fmt_key:
                    directives.append("Responde en prosa narrativa fluida.")

        if not directives:
            return ""

        return "[ESTILO ADAPTADO] " + " ".join(directives)


class AdaptiveInterface:
    """
    Coordinador de interfaz adaptativa.
    Aprende preferencias del usuario y adapta las respuestas.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/adaptive_iface")
        self.data_file = self.base_dir / "adaptive_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.preferences = {}     # name -> UserPreference
        self.tracker = PreferenceTracker()
        self.adapter = ResponseAdapter()
        self.total_adaptations = 0
        self.enabled = True

        # Inicializar preferencias default
        self._init_defaults()
        self._load()

    def _init_defaults(self):
        """Inicializa preferencias con valores neutros."""
        defaults = [
            ("verbosity", 0.5),
            ("technical_level", 0.5),
            ("format_code", 0.3),
            ("format_list", 0.3),
            ("format_prose", 0.3),
        ]
        for name, value in defaults:
            if name not in self.preferences:
                self.preferences[name] = UserPreference(name, value)

    def observe_input(self, user_input: str):
        """Observa el input del usuario para detectar preferencias."""
        if not self.enabled or not user_input:
            return

        signals = self.tracker.detect_signals(user_input)
        for pref_name, signal_value in signals.items():
            if pref_name not in self.preferences:
                self.preferences[pref_name] = UserPreference(pref_name)
            self.preferences[pref_name].update(signal_value)

    def observe_feedback(self, positive: bool, response_length: int):
        """Observa feedback del usuario."""
        if not self.enabled:
            return

        signals = self.tracker.detect_feedback_signals(positive, response_length)
        for pref_name, signal_value in signals.items():
            if pref_name in self.preferences:
                self.preferences[pref_name].update(signal_value, weight=1.5)

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera directivas de estilo para inyectar en prompt."""
        if not self.enabled:
            return ""

        directives = self.adapter.generate_directives(self.preferences)
        self.total_adaptations += 1 if directives else 0
        return directives[:max_chars]

    def get_preference_value(self, name: str) -> float:
        """Obtiene el valor actual de una preferencia."""
        pref = self.preferences.get(name)
        return pref.value if pref else 0.5

    def get_stats(self) -> dict:
        return {
            "preferences": {
                name: {"value": round(p.value, 3), "confidence": round(p.confidence, 3),
                       "observations": p.observations}
                for name, p in self.preferences.items()
            },
            "total_adaptations": self.total_adaptations,
        }

    def status(self) -> str:
        parts = []
        for name, pref in self.preferences.items():
            if pref.confidence > 0.15:
                parts.append(f"{name}={pref.value:.1f}")
        prefs_str = ", ".join(parts) if parts else "aprendiendo..."
        return f"Preferencias: {prefs_str} | Adaptaciones: {self.total_adaptations}"

    def generate_report(self) -> str:
        lines = ["=== ADAPTIVE INTERFACE REPORT ==="]
        lines.append(f"Total adaptaciones: {self.total_adaptations}")
        lines.append(f"\nPreferencias:")
        for name, pref in sorted(self.preferences.items()):
            bar = "█" * int(pref.value * 20) + "░" * (20 - int(pref.value * 20))
            conf = "★" * int(pref.confidence * 5)
            lines.append(f"  {name:20s} [{bar}] {pref.value:.2f} "
                         f"conf={conf} obs={pref.observations}")

        # Directivas actuales
        directives = self.adapter.generate_directives(self.preferences)
        if directives:
            lines.append(f"\nDirectivas actuales:")
            lines.append(f"  {directives}")
        else:
            lines.append(f"\nSin directivas (confianza insuficiente)")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_adaptations": self.total_adaptations,
            "preferences": {n: p.to_dict() for n, p in self.preferences.items()},
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
            self.total_adaptations = data.get("total_adaptations", 0)
            for name, pd in data.get("preferences", {}).items():
                self.preferences[name] = UserPreference.from_dict(pd)
        except Exception:
            pass

    def clear(self):
        self.preferences = {}
        self.total_adaptations = 0
        self._init_defaults()
