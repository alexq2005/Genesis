"""
GENESIS — Voice Personality (v3.3)

Personalidad expresada en voz: genera directivas de estilo vocal basadas
en emocion detectada y tipo de contenido. Sin audio real, produce
instrucciones textuales de prosodia y estilo.

Componentes:
- VocalStyle: parametros de estilo vocal (velocidad, tono, enfasis, pausas)
- EmotionalVoice: mapeo emocion -> ajustes de VocalStyle
- ProsodyRule: regla condicional de prosodia
- VoicePersonality: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class VocalStyle:
    """Parametros de estilo vocal."""

    DEFAULTS = {
        "speed": 1.0,        # 0.5 (lento) a 2.0 (rapido)
        "pitch": 1.0,        # 0.5 (grave) a 2.0 (agudo)
        "emphasis_level": 0.5,  # 0.0 (monotono) a 1.0 (muy enfatico)
        "pause_frequency": 0.3, # 0.0 (sin pausas) a 1.0 (pausas constantes)
    }

    def __init__(self, speed: float = 1.0, pitch: float = 1.0,
                 emphasis_level: float = 0.5, pause_frequency: float = 0.3):
        self.speed = max(0.5, min(2.0, speed))
        self.pitch = max(0.5, min(2.0, pitch))
        self.emphasis_level = max(0.0, min(1.0, emphasis_level))
        self.pause_frequency = max(0.0, min(1.0, pause_frequency))

    def apply_adjustment(self, speed_delta: float = 0.0, pitch_delta: float = 0.0,
                          emphasis_delta: float = 0.0, pause_delta: float = 0.0):
        """Aplica ajustes incrementales a los parametros."""
        self.speed = max(0.5, min(2.0, self.speed + speed_delta))
        self.pitch = max(0.5, min(2.0, self.pitch + pitch_delta))
        self.emphasis_level = max(0.0, min(1.0, self.emphasis_level + emphasis_delta))
        self.pause_frequency = max(0.0, min(1.0, self.pause_frequency + pause_delta))

    def describe(self) -> str:
        """Descripcion legible del estilo vocal actual."""
        parts = []

        # Velocidad
        if self.speed < 0.8:
            parts.append("habla lenta y pausada")
        elif self.speed > 1.3:
            parts.append("habla rapida y energica")
        else:
            parts.append("velocidad normal")

        # Tono
        if self.pitch < 0.8:
            parts.append("tono grave y serio")
        elif self.pitch > 1.3:
            parts.append("tono alto y animado")
        else:
            parts.append("tono medio")

        # Enfasis
        if self.emphasis_level > 0.7:
            parts.append("con enfasis marcado en puntos clave")
        elif self.emphasis_level < 0.3:
            parts.append("tono parejo sin enfasis especial")

        # Pausas
        if self.pause_frequency > 0.7:
            parts.append("con pausas frecuentes para dar espacio")
        elif self.pause_frequency < 0.2:
            parts.append("fluido sin pausas")

        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "emphasis_level": self.emphasis_level,
            "pause_frequency": self.pause_frequency,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VocalStyle":
        return cls(
            speed=d.get("speed", 1.0),
            pitch=d.get("pitch", 1.0),
            emphasis_level=d.get("emphasis_level", 0.5),
            pause_frequency=d.get("pause_frequency", 0.3),
        )


class EmotionalVoice:
    """Mapeo de emociones a ajustes de estilo vocal."""

    EMOTION_ADJUSTMENTS = {
        "frustracion": {
            "speed_delta": -0.2,
            "pitch_delta": -0.15,
            "emphasis_delta": 0.2,
            "pause_delta": 0.2,
            "description": "Mas lento, tono bajo, pausas comprensivas",
        },
        "alegria": {
            "speed_delta": 0.15,
            "pitch_delta": 0.2,
            "emphasis_delta": 0.15,
            "pause_delta": -0.1,
            "description": "Mas rapido, tono alto, fluido y animado",
        },
        "confusion": {
            "speed_delta": -0.15,
            "pitch_delta": 0.0,
            "emphasis_delta": 0.25,
            "pause_delta": 0.3,
            "description": "Mas lento, pausas para claridad, enfasis en puntos clave",
        },
        "curiosidad": {
            "speed_delta": 0.0,
            "pitch_delta": 0.1,
            "emphasis_delta": 0.2,
            "pause_delta": 0.1,
            "description": "Tono ligeramente elevado, enfasis educativo",
        },
        "urgencia": {
            "speed_delta": 0.25,
            "pitch_delta": 0.1,
            "emphasis_delta": 0.3,
            "pause_delta": -0.2,
            "description": "Rapido, directo, sin pausas innecesarias",
        },
        "neutral": {
            "speed_delta": 0.0,
            "pitch_delta": 0.0,
            "emphasis_delta": 0.0,
            "pause_delta": 0.0,
            "description": "Sin ajuste, estilo base",
        },
        "tristeza": {
            "speed_delta": -0.25,
            "pitch_delta": -0.2,
            "emphasis_delta": -0.1,
            "pause_delta": 0.25,
            "description": "Lento, tono bajo, pausas empaticas",
        },
        "entusiasmo": {
            "speed_delta": 0.2,
            "pitch_delta": 0.25,
            "emphasis_delta": 0.3,
            "pause_delta": -0.15,
            "description": "Rapido, tono alto, muy enfatico",
        },
    }

    def get_adjustment(self, emotion: str) -> dict:
        """Retorna ajustes para la emocion dada."""
        return self.EMOTION_ADJUSTMENTS.get(
            emotion, self.EMOTION_ADJUSTMENTS["neutral"]
        )

    def apply_to_style(self, style: VocalStyle, emotion: str,
                        intensity: float = 1.0) -> VocalStyle:
        """Aplica ajuste emocional al estilo, escalado por intensidad."""
        adj = self.get_adjustment(emotion)
        style.apply_adjustment(
            speed_delta=adj["speed_delta"] * intensity,
            pitch_delta=adj["pitch_delta"] * intensity,
            emphasis_delta=adj["emphasis_delta"] * intensity,
            pause_delta=adj["pause_delta"] * intensity,
        )
        return style

    @classmethod
    def list_emotions(cls) -> list:
        return list(cls.EMOTION_ADJUSTMENTS.keys())


class ProsodyRule:
    """Regla condicional de prosodia para tipos de contenido."""

    CONTENT_RULES = {
        "explanation": {
            "condition": "Contenido explicativo o educativo",
            "adjustment": {"speed_delta": -0.15, "pause_delta": 0.2, "emphasis_delta": 0.15},
            "description": "Mas lento con pausas, enfasis en conceptos clave",
        },
        "list": {
            "condition": "Enumeracion o lista de items",
            "adjustment": {"speed_delta": 0.1, "pause_delta": 0.15, "emphasis_delta": 0.1},
            "description": "Ritmo consistente, pausa entre items",
        },
        "code": {
            "condition": "Codigo fuente o comandos tecnicos",
            "adjustment": {"speed_delta": -0.1, "emphasis_delta": -0.2, "pause_delta": 0.1},
            "description": "Monotono y preciso, sin enfasis emocional",
        },
        "warning": {
            "condition": "Advertencia o alerta importante",
            "adjustment": {"speed_delta": -0.1, "pitch_delta": -0.1, "emphasis_delta": 0.3},
            "description": "Tono serio, enfasis fuerte en la advertencia",
        },
        "greeting": {
            "condition": "Saludo o inicio de conversacion",
            "adjustment": {"speed_delta": 0.05, "pitch_delta": 0.15, "emphasis_delta": 0.1},
            "description": "Tono calido y amigable",
        },
        "summary": {
            "condition": "Resumen o conclusion",
            "adjustment": {"speed_delta": 0.0, "pause_delta": 0.1, "emphasis_delta": 0.2},
            "description": "Enfasis en puntos principales, pausas entre secciones",
        },
    }

    def __init__(self, content_type: str):
        config = self.CONTENT_RULES.get(content_type, {})
        self.content_type = content_type
        self.condition = config.get("condition", "General")
        self.adjustment = config.get("adjustment", {})
        self.description = config.get("description", "Sin ajuste especial")

    def apply(self, style: VocalStyle) -> VocalStyle:
        """Aplica la regla de prosodia al estilo."""
        style.apply_adjustment(**self.adjustment)
        return style

    @classmethod
    def list_content_types(cls) -> list:
        return list(cls.CONTENT_RULES.keys())


class VoicePersonality:
    """Coordinador de personalidad vocal con persistencia."""

    def __init__(self, base_dir: str = "data/voice_personality"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.style = VocalStyle()
        self.emotional_voice = EmotionalVoice()
        self.total_adaptations = 0
        self.current_emotion = "neutral"
        self.current_content_type = ""
        self.adaptation_history = deque(maxlen=50)
        self.emotion_counts = defaultdict(int)
        self.content_type_counts = defaultdict(int)

        self._load()

    def adapt_to_emotion(self, emotion: str, intensity: float = 1.0) -> dict:
        """Ajusta estilo vocal basado en emocion detectada."""
        intensity = max(0.0, min(1.0, intensity))

        # Reset a defaults antes de aplicar
        self.style = VocalStyle()
        self.emotional_voice.apply_to_style(self.style, emotion, intensity)

        self.current_emotion = emotion
        self.total_adaptations += 1
        self.emotion_counts[emotion] += 1

        adj = self.emotional_voice.get_adjustment(emotion)

        self.adaptation_history.append({
            "type": "emotion",
            "value": emotion,
            "intensity": intensity,
            "timestamp": time.time(),
        })

        return {
            "emotion": emotion,
            "intensity": intensity,
            "style": self.style.to_dict(),
            "description": adj["description"],
            "vocal_directives": self.style.describe(),
        }

    def adapt_to_content(self, content_type: str) -> dict:
        """Ajusta estilo vocal para el tipo de contenido."""
        rule = ProsodyRule(content_type)
        rule.apply(self.style)

        self.current_content_type = content_type
        self.total_adaptations += 1
        self.content_type_counts[content_type] += 1

        self.adaptation_history.append({
            "type": "content",
            "value": content_type,
            "timestamp": time.time(),
        })

        return {
            "content_type": content_type,
            "rule_description": rule.description,
            "style": self.style.to_dict(),
            "vocal_directives": self.style.describe(),
        }

    def get_vocal_directives(self) -> str:
        """Retorna directivas de estilo vocal legibles."""
        parts = [f"Estilo vocal: {self.style.describe()}"]

        if self.current_emotion and self.current_emotion != "neutral":
            adj = self.emotional_voice.get_adjustment(self.current_emotion)
            parts.append(f"Ajuste emocional ({self.current_emotion}): {adj['description']}")

        if self.current_content_type:
            rule = ProsodyRule(self.current_content_type)
            parts.append(f"Ajuste de contenido ({self.current_content_type}): {rule.description}")

        return ". ".join(parts)

    def get_context_for_prompt(self, content_type: str = "",
                                emotion: str = "", max_chars: int = 200) -> str:
        """Inyecta directivas vocales si son relevantes."""
        if not content_type and not emotion:
            # Si no hay input, usar estado actual
            if self.current_emotion == "neutral" and not self.current_content_type:
                return ""

        # Aplicar adaptaciones si se proporcionan
        if emotion and emotion != "neutral":
            self.adapt_to_emotion(emotion)
        if content_type:
            self.adapt_to_content(content_type)

        directives = self.get_vocal_directives()
        if not directives:
            return ""

        context = f"[VOZ] {directives}"
        return context[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_adaptations": self.total_adaptations,
            "current_emotion": self.current_emotion,
            "current_content_type": self.current_content_type,
            "current_style": self.style.to_dict(),
            "emotion_counts": dict(self.emotion_counts),
            "content_type_counts": dict(self.content_type_counts),
            "history_size": len(self.adaptation_history),
        }

    def status(self) -> str:
        return (f"  Adaptaciones: {self.total_adaptations} | "
                f"Emocion: {self.current_emotion} | "
                f"Contenido: {self.current_content_type or 'ninguno'} | "
                f"Estilo: {self.style.describe()[:60]}")

    def generate_report(self) -> str:
        lines = [
            "=== VOICE PERSONALITY ===",
            f"Total adaptaciones: {self.total_adaptations}",
            f"Emocion actual: {self.current_emotion}",
            f"Contenido actual: {self.current_content_type or 'ninguno'}",
            "",
            "Estilo vocal actual:",
            f"  Velocidad: {self.style.speed:.2f}",
            f"  Tono: {self.style.pitch:.2f}",
            f"  Enfasis: {self.style.emphasis_level:.2f}",
            f"  Pausas: {self.style.pause_frequency:.2f}",
            f"  Descripcion: {self.style.describe()}",
            "",
            "Adaptaciones por emocion:",
        ]
        for emotion, count in sorted(self.emotion_counts.items(),
                                       key=lambda x: x[1], reverse=True):
            pct = count / max(1, self.total_adaptations) * 100
            lines.append(f"  {emotion}: {count} ({pct:.0f}%)")

        lines.append("")
        lines.append("Adaptaciones por contenido:")
        for ctype, count in sorted(self.content_type_counts.items(),
                                     key=lambda x: x[1], reverse=True):
            lines.append(f"  {ctype}: {count}")

        lines.append("")
        lines.append("Historial reciente:")
        for entry in list(self.adaptation_history)[-5:]:
            atype = entry["type"]
            val = entry["value"]
            if atype == "emotion":
                lines.append(f"  Emocion: {val} (int: {entry.get('intensity', 0):.0%})")
            else:
                lines.append(f"  Contenido: {val}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_adaptations": self.total_adaptations,
            "current_emotion": self.current_emotion,
            "current_content_type": self.current_content_type,
            "style": self.style.to_dict(),
            "emotion_counts": dict(self.emotion_counts),
            "content_type_counts": dict(self.content_type_counts),
            "history": list(self.adaptation_history),
        }
        path = self.base_dir / "voice_personality.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "voice_personality.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_adaptations = data.get("total_adaptations", 0)
            self.current_emotion = data.get("current_emotion", "neutral")
            self.current_content_type = data.get("current_content_type", "")
            if "style" in data:
                self.style = VocalStyle.from_dict(data["style"])
            self.emotion_counts = defaultdict(int, data.get("emotion_counts", {}))
            self.content_type_counts = defaultdict(int, data.get("content_type_counts", {}))
            for entry in data.get("history", []):
                self.adaptation_history.append(entry)
        except Exception:
            pass

    def clear(self):
        self.style = VocalStyle()
        self.current_emotion = "neutral"
        self.current_content_type = ""
        self.total_adaptations = 0
        self.emotion_counts = defaultdict(int)
        self.content_type_counts = defaultdict(int)
        self.adaptation_history = deque(maxlen=50)
        self.save()
