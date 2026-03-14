"""
GENESIS — Emotion Reader (v3.1)

Detección de emociones del usuario en texto. Clasificador multi-etiqueta
basado en señales léxicas (palabras clave, puntuación, patrones).
Historial emocional por sesión con tendencia.

Componentes:
- EmotionSignal: señal emocional detectada
- EmotionClassifier: clasificador multi-etiqueta por keywords
- EmotionHistory: historial con tendencia
- EmotionReader: coordinador con persistencia
"""
import time
import json
import re
from pathlib import Path
from collections import defaultdict, deque


class EmotionSignal:
    """Señal emocional detectada en un texto."""

    def __init__(self, emotion: str, intensity: float, source: str = ""):
        self.emotion = emotion        # alegría, frustración, confusión, etc.
        self.intensity = intensity    # 0.0 a 1.0
        self.source = source          # palabra/patrón que la generó
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "emotion": self.emotion,
            "intensity": self.intensity,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionSignal":
        s = cls(d["emotion"], d["intensity"], d.get("source", ""))
        s.timestamp = d.get("timestamp", time.time())
        return s


class EmotionClassifier:
    """Clasificador multi-etiqueta de emociones por señales léxicas."""

    EMOTION_KEYWORDS = {
        "alegria": [
            "gracias", "genial", "perfecto", "excelente", "increible",
            "fantastico", "buenisimo", "me encanta", "funciona", "funciono",
            "lo logre", "bien hecho", "great", "perfect", "awesome",
            "thanks", "amazing", "love it", "works", "jaja", "haha",
        ],
        "frustracion": [
            "no funciona", "no anda", "error", "falla", "bug", "roto",
            "no puedo", "imposible", "no entiendo", "no sirve",
            "otra vez", "de nuevo", "sigue sin", "no se arregla",
            "broken", "doesn't work", "failed", "crash",
        ],
        "confusion": [
            "no entiendo", "que significa", "como es eso", "no me queda claro",
            "me confunde", "que quiere decir", "perdido", "confundido",
            "confused", "don't understand", "what does", "how come",
            "no se que", "no se como", "que es",
        ],
        "curiosidad": [
            "como funciona", "por que", "que pasa si", "como se hace",
            "me gustaria saber", "quiero aprender", "enseñame",
            "como puedo", "es posible", "se puede", "hay forma",
            "how does", "why", "what if", "can i", "is it possible",
        ],
        "urgencia": [
            "urgente", "rapido", "ya", "ahora mismo", "cuanto antes",
            "es para hoy", "necesito ya", "apurate", "pronto",
            "asap", "hurry", "quickly", "right now", "immediately",
        ],
        "neutral": [],  # Fallback cuando no se detecta nada
    }

    # Patrones de puntuación que amplifican emociones
    PUNCTUATION_SIGNALS = {
        "!!!": ("frustracion", 0.2),      # Múltiples exclamaciones → frustración
        "???": ("confusion", 0.2),         # Múltiples interrogaciones → confusión
        "...": ("frustracion", 0.1),       # Puntos suspensivos → incertidumbre
    }

    def classify(self, text: str) -> list:
        """Clasifica texto y retorna lista de EmotionSignal."""
        signals = []
        text_lower = text.lower()

        # Detectar emociones por keywords
        emotion_scores = defaultdict(float)
        emotion_sources = defaultdict(str)

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            if emotion == "neutral":
                continue
            for keyword in keywords:
                if keyword in text_lower:
                    weight = min(1.0, len(keyword) / 15.0 + 0.3)
                    if weight > emotion_scores[emotion]:
                        emotion_scores[emotion] = weight
                        emotion_sources[emotion] = keyword

        # Señales de puntuación
        for pattern, (emotion, boost) in self.PUNCTUATION_SIGNALS.items():
            if pattern in text:
                emotion_scores[emotion] = min(1.0, emotion_scores.get(emotion, 0) + boost)

        # Mayúsculas → intensidad amplificada (frustración o urgencia)
        upper_ratio = sum(1 for c in text if c.isupper()) / max(1, len(text))
        if upper_ratio > 0.5 and len(text) > 5:
            if emotion_scores.get("frustracion", 0) > 0:
                emotion_scores["frustracion"] = min(1.0, emotion_scores["frustracion"] + 0.2)
            elif emotion_scores.get("urgencia", 0) > 0:
                emotion_scores["urgencia"] = min(1.0, emotion_scores["urgencia"] + 0.2)

        # Construir señales
        for emotion, intensity in emotion_scores.items():
            if intensity > 0:
                signals.append(EmotionSignal(
                    emotion=emotion,
                    intensity=min(1.0, intensity),
                    source=emotion_sources.get(emotion, "pattern"),
                ))

        # Si no hay señales, devolver neutral
        if not signals:
            signals.append(EmotionSignal("neutral", 0.3, "default"))

        # Ordenar por intensidad descendente
        signals.sort(key=lambda s: s.intensity, reverse=True)
        return signals

    def get_primary_emotion(self, text: str) -> str:
        """Retorna la emoción primaria detectada."""
        signals = self.classify(text)
        return signals[0].emotion if signals else "neutral"


class EmotionHistory:
    """Historial emocional con tendencia por sesión."""

    def __init__(self, max_entries: int = 100):
        self.entries = deque(maxlen=max_entries)
        self.emotion_counts = defaultdict(int)
        self.total_readings = 0

    def record(self, signals: list):
        """Registra señales emocionales."""
        if not signals:
            return
        primary = signals[0]
        self.entries.append(primary.to_dict())
        self.emotion_counts[primary.emotion] += 1
        self.total_readings += 1

    def get_trend(self) -> str:
        """Determina la tendencia emocional reciente."""
        if len(self.entries) < 3:
            return "insufficient_data"

        recent = list(self.entries)[-5:]
        positive_emotions = {"alegria"}
        negative_emotions = {"frustracion", "confusion", "urgencia"}

        recent_positive = sum(1 for e in recent if e["emotion"] in positive_emotions)
        recent_negative = sum(1 for e in recent if e["emotion"] in negative_emotions)

        if recent_positive > recent_negative:
            return "mejorando"
        elif recent_negative > recent_positive:
            return "empeorando"
        return "estable"

    def get_dominant_emotion(self) -> str:
        """Retorna la emoción más frecuente."""
        if not self.emotion_counts:
            return "neutral"
        return max(self.emotion_counts, key=self.emotion_counts.get)

    def get_recent_emotions(self, n: int = 5) -> list:
        """Retorna las últimas n emociones."""
        return list(self.entries)[-n:]


class EmotionReader:
    """Coordinador de detección emocional con persistencia."""

    def __init__(self, base_dir: str = "data/emotion_reader"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.classifier = EmotionClassifier()
        self.history = EmotionHistory()
        self.total_readings = 0

        self._load()

    def read(self, text: str) -> dict:
        """Lee emociones del texto. Retorna dict con análisis."""
        signals = self.classifier.classify(text)
        self.history.record(signals)
        self.total_readings += 1

        return {
            "primary": signals[0].emotion if signals else "neutral",
            "intensity": signals[0].intensity if signals else 0.0,
            "all_emotions": [s.to_dict() for s in signals],
            "trend": self.history.get_trend(),
            "dominant": self.history.get_dominant_emotion(),
        }

    def get_context_for_prompt(self, text: str = "", max_chars: int = 200) -> str:
        """Genera contexto emocional para inyectar en prompt."""
        if not text and not self.history.entries:
            return ""

        parts = []

        if text:
            signals = self.classifier.classify(text)
            primary = signals[0] if signals else None
            if primary and primary.emotion != "neutral":
                parts.append(f"El usuario parece {primary.emotion} (intensidad: {primary.intensity:.0%})")

        trend = self.history.get_trend()
        if trend in ("mejorando", "empeorando"):
            parts.append(f"Tendencia emocional: {trend}")

        if not parts:
            return ""

        context = "[CONTEXTO EMOCIONAL] " + ". ".join(parts)
        return context[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_readings": self.total_readings,
            "dominant_emotion": self.history.get_dominant_emotion(),
            "trend": self.history.get_trend(),
            "emotion_counts": dict(self.history.emotion_counts),
            "history_size": len(self.history.entries),
        }

    def status(self) -> str:
        dominant = self.history.get_dominant_emotion()
        trend = self.history.get_trend()
        return (f"  Lecturas: {self.total_readings} | "
                f"Dominante: {dominant} | Tendencia: {trend}")

    def generate_report(self) -> str:
        lines = [
            "=== EMOTION READER ===",
            f"Lecturas totales: {self.total_readings}",
            f"Emocion dominante: {self.history.get_dominant_emotion()}",
            f"Tendencia: {self.history.get_trend()}",
            "",
            "Conteo por emocion:",
        ]
        for emotion, count in sorted(self.history.emotion_counts.items(),
                                      key=lambda x: x[1], reverse=True):
            pct = count / max(1, self.total_readings) * 100
            lines.append(f"  {emotion}: {count} ({pct:.0f}%)")

        lines.append("")
        lines.append("Ultimas lecturas:")
        for entry in self.history.get_recent_emotions(5):
            lines.append(f"  {entry['emotion']} ({entry['intensity']:.0%}) via '{entry.get('source', '?')}'")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_readings": self.total_readings,
            "history": list(self.history.entries),
            "emotion_counts": dict(self.history.emotion_counts),
        }
        path = self.base_dir / "emotion_reader.json"
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "emotion_reader.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_readings = data.get("total_readings", 0)
            for entry in data.get("history", []):
                self.history.entries.append(entry)
            self.history.emotion_counts = defaultdict(int, data.get("emotion_counts", {}))
            self.history.total_readings = self.total_readings
        except Exception:
            pass

    def clear(self):
        self.history = EmotionHistory()
        self.total_readings = 0
        self.save()
