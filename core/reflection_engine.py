"""
GENESIS — Reflection Engine (v2.5)

Motor de auto-reflexión profunda: Genesis periódicamente analiza
sus propios patrones de comportamiento, detecta puntos ciegos,
identifica fortalezas y genera planes de mejora.

Diferente del SelfEvaluator (que califica respuestas individuales),
esto es reflexión de ALTO NIVEL sobre tendencias y comportamiento general.

Componentes:
- ReflectionEntry: una reflexión (observaciones, fortalezas, puntos ciegos, plan)
- SelfAnalyzer: analiza patrones desde datos de subsistemas
- ReflectionEngine: coordinador con reflexión periódica y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class ReflectionEntry:
    """Una reflexión completa sobre el estado actual del sistema."""

    def __init__(self, reflection_id: str = None):
        self.reflection_id = reflection_id or hashlib.md5(
            f"ref_{time.time()}".encode()
        ).hexdigest()[:10]
        self.timestamp = time.time()
        self.trigger = ""            # "periodic", "feedback_threshold", "manual"
        self.observations = []       # Lista de observaciones textuales
        self.strengths = []          # Fortalezas detectadas
        self.blind_spots = []        # Puntos ciegos o debilidades
        self.improvement_plan = []   # Acciones de mejora sugeridas
        self.confidence = 0.0        # Confianza en la reflexión (0.0-1.0)
        self.data_points = 0         # Cuántos datos se usaron

    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600

    def to_text(self, max_chars: int = 500) -> str:
        """Representación textual para prompts."""
        lines = [f"[Reflexión {self._date_str()}]"]

        if self.strengths:
            lines.append(f"  Fortalezas: {', '.join(self.strengths[:3])}")
        if self.blind_spots:
            lines.append(f"  Puntos ciegos: {', '.join(self.blind_spots[:3])}")
        if self.improvement_plan:
            lines.append(f"  Plan: {self.improvement_plan[0][:100]}")

        result = "\n".join(lines)
        return result[:max_chars]

    def _date_str(self) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M")

    def to_dict(self) -> dict:
        return {
            "id": self.reflection_id,
            "timestamp": self.timestamp,
            "trigger": self.trigger,
            "observations": self.observations[:20],
            "strengths": self.strengths[:10],
            "blind_spots": self.blind_spots[:10],
            "improvement_plan": self.improvement_plan[:10],
            "confidence": self.confidence,
            "data_points": self.data_points,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReflectionEntry":
        r = cls(reflection_id=data.get("id"))
        r.timestamp = data.get("timestamp", time.time())
        r.trigger = data.get("trigger", "")
        r.observations = data.get("observations", [])
        r.strengths = data.get("strengths", [])
        r.blind_spots = data.get("blind_spots", [])
        r.improvement_plan = data.get("improvement_plan", [])
        r.confidence = data.get("confidence", 0.0)
        r.data_points = data.get("data_points", 0)
        return r


class SelfAnalyzer:
    """
    Analiza datos de subsistemas para detectar patrones de alto nivel.
    Opera sobre datos agregados, no sobre interacciones individuales.
    """

    def analyze_quality_trend(self, eval_scores: list) -> dict:
        """
        Analiza tendencia de calidad.
        eval_scores: lista de scores recientes (0.0-1.0)
        """
        if len(eval_scores) < 10:
            return {"sufficient_data": False}

        # Dividir en primera y segunda mitad
        mid = len(eval_scores) // 2
        first_half = eval_scores[:mid]
        second_half = eval_scores[mid:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        trend = "stable"
        if avg_second > avg_first + 0.05:
            trend = "improving"
        elif avg_second < avg_first - 0.05:
            trend = "declining"

        return {
            "sufficient_data": True,
            "avg_first_half": round(avg_first, 3),
            "avg_second_half": round(avg_second, 3),
            "trend": trend,
            "change": round(avg_second - avg_first, 3),
        }

    def analyze_intent_distribution(self, intent_counts: dict) -> dict:
        """Analiza la distribución de intents para detectar sesgos."""
        if not intent_counts:
            return {"sufficient_data": False}

        total = sum(intent_counts.values())
        if total < 20:
            return {"sufficient_data": False}

        distribution = {k: round(v / total, 3) for k, v in intent_counts.items()}

        # Detectar concentración excesiva (> 60% en un solo intent)
        dominant = max(distribution, key=distribution.get)
        concentration = distribution[dominant]

        # Detectar intents sub-representados
        under_served = [k for k, v in distribution.items() if v < 0.05]

        return {
            "sufficient_data": True,
            "distribution": distribution,
            "dominant_intent": dominant,
            "concentration": concentration,
            "high_concentration": concentration > 0.6,
            "under_served": under_served,
            "total_intents": len(intent_counts),
        }

    def analyze_feedback_ratio(self, positive: int, negative: int) -> dict:
        """Analiza ratio de feedback positivo/negativo."""
        total = positive + negative
        if total < 10:
            return {"sufficient_data": False}

        ratio = positive / total if total > 0 else 0

        sentiment = "neutral"
        if ratio > 0.8:
            sentiment = "excellent"
        elif ratio > 0.6:
            sentiment = "good"
        elif ratio > 0.4:
            sentiment = "mixed"
        else:
            sentiment = "poor"

        return {
            "sufficient_data": True,
            "positive": positive,
            "negative": negative,
            "ratio": round(ratio, 3),
            "sentiment": sentiment,
        }

    def analyze_personality_drift(self, distance: float, evolutions: int) -> dict:
        """Analiza cuánto ha cambiado la personalidad."""
        if evolutions < 10:
            return {"sufficient_data": False}

        stability = "stable"
        if distance > 0.3:
            stability = "high_drift"
        elif distance > 0.15:
            stability = "moderate_drift"
        elif distance < 0.05:
            stability = "very_stable"

        return {
            "sufficient_data": True,
            "distance": round(distance, 3),
            "evolutions": evolutions,
            "stability": stability,
        }

    def generate_reflection(self, quality_data: dict = None,
                            intent_data: dict = None,
                            feedback_data: dict = None,
                            personality_data: dict = None) -> ReflectionEntry:
        """Genera una reflexión completa desde datos de análisis."""
        entry = ReflectionEntry()
        entry.trigger = "periodic"
        data_points = 0

        observations = []
        strengths = []
        blind_spots = []
        plan = []

        # --- Calidad ---
        if quality_data and quality_data.get("sufficient_data"):
            data_points += 1
            trend = quality_data["trend"]
            change = quality_data["change"]

            if trend == "improving":
                observations.append(
                    f"La calidad de respuestas está mejorando ({change:+.3f})"
                )
                strengths.append("Tendencia de calidad positiva")
            elif trend == "declining":
                observations.append(
                    f"La calidad de respuestas está decayendo ({change:+.3f})"
                )
                blind_spots.append("Calidad en declive")
                plan.append("Revisar temperature y templates de intents con bajo score")
            else:
                observations.append("La calidad de respuestas se mantiene estable")

        # --- Intents ---
        if intent_data and intent_data.get("sufficient_data"):
            data_points += 1

            if intent_data.get("high_concentration"):
                dominant = intent_data["dominant_intent"]
                conc = intent_data["concentration"]
                observations.append(
                    f"Alta concentración en intent '{dominant}' ({conc:.0%})"
                )
                blind_spots.append(f"Posible sobre-especialización en '{dominant}'")

            under = intent_data.get("under_served", [])
            if under:
                observations.append(
                    f"Intents poco atendidos: {', '.join(under[:3])}"
                )
                plan.append(f"Explorar y mejorar capacidades en: {', '.join(under[:3])}")

        # --- Feedback ---
        if feedback_data and feedback_data.get("sufficient_data"):
            data_points += 1
            sentiment = feedback_data["sentiment"]
            ratio = feedback_data["ratio"]

            if sentiment in ("excellent", "good"):
                strengths.append(f"Buena recepción del usuario (ratio: {ratio:.0%} positivo)")
            elif sentiment == "mixed":
                observations.append(f"Feedback mixto ({ratio:.0%} positivo)")
                plan.append("Analizar patrones de feedback negativo para mejorar")
            elif sentiment == "poor":
                blind_spots.append(f"Feedback mayormente negativo ({ratio:.0%} positivo)")
                plan.append("Urgente: revisar calidad de respuestas y ajustar estrategia")

        # --- Personalidad ---
        if personality_data and personality_data.get("sufficient_data"):
            data_points += 1
            stability = personality_data["stability"]
            distance = personality_data["distance"]

            if stability == "high_drift":
                observations.append(
                    f"Personalidad con alta deriva (distancia: {distance:.3f})"
                )
                blind_spots.append("Personalidad inestable — puede confundir al usuario")
                plan.append("Considerar aumentar decay rate para estabilizar personalidad")
            elif stability == "very_stable":
                observations.append("Personalidad muy estable")
                strengths.append("Consistencia de personalidad")

        # Ensamble
        entry.observations = observations
        entry.strengths = strengths
        entry.blind_spots = blind_spots
        entry.improvement_plan = plan
        entry.data_points = data_points
        entry.confidence = min(0.9, data_points * 0.2) if data_points > 0 else 0.1

        return entry


class ReflectionEngine:
    """
    Coordinador de auto-reflexión.
    Genera reflexiones periódicas y mantiene historial.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/reflection")
        self.data_file = self.base_dir / "reflection_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.reflections = []  # Historial de ReflectionEntry
        self.analyzer = SelfAnalyzer()
        self.max_reflections = 100
        self.total_reflections = 0
        self.enabled = True

        # Cada cuántas interacciones generar una reflexión
        self.reflection_interval = 25
        self.interaction_counter = 0

        self._load()

    def tick(self):
        """Llamado cada interacción. Genera reflexión si toca."""
        self.interaction_counter += 1

    def should_reflect(self) -> bool:
        """¿Es momento de reflexionar?"""
        return (self.enabled and
                self.interaction_counter > 0 and
                self.interaction_counter % self.reflection_interval == 0)

    def reflect(self, eval_scores: list = None, intent_counts: dict = None,
                positive_feedback: int = 0, negative_feedback: int = 0,
                personality_distance: float = 0.0,
                personality_evolutions: int = 0) -> ReflectionEntry:
        """
        Genera una reflexión completa.
        Recibe datos de otros subsistemas para analizar.
        """
        if not self.enabled:
            return None

        # Analizar cada dimensión
        quality_data = self.analyzer.analyze_quality_trend(eval_scores or [])
        intent_data = self.analyzer.analyze_intent_distribution(intent_counts or {})
        feedback_data = self.analyzer.analyze_feedback_ratio(
            positive_feedback, negative_feedback
        )
        personality_data = self.analyzer.analyze_personality_drift(
            personality_distance, personality_evolutions
        )

        # Generar reflexión
        entry = self.analyzer.generate_reflection(
            quality_data=quality_data,
            intent_data=intent_data,
            feedback_data=feedback_data,
            personality_data=personality_data,
        )

        self.reflections.append(entry)
        self.total_reflections += 1

        # Trim
        if len(self.reflections) > self.max_reflections:
            self.reflections = self.reflections[-self.max_reflections:]

        return entry

    def get_latest(self) -> ReflectionEntry:
        """Retorna la reflexión más reciente."""
        return self.reflections[-1] if self.reflections else None

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de reflexión para inyectar en prompt."""
        if not self.enabled or not self.reflections:
            return ""

        latest = self.reflections[-1]
        if latest.age_hours > 24:
            return ""  # Reflexión demasiado vieja

        lines = ["[AUTO-REFLEXIÓN RECIENTE]"]

        if latest.blind_spots:
            lines.append(f"  ⚠️ Puntos ciegos: {', '.join(latest.blind_spots[:2])}")
        if latest.improvement_plan:
            lines.append(f"  📋 Plan: {latest.improvement_plan[0][:150]}")
        if latest.strengths:
            lines.append(f"  ✓ Fortalezas: {', '.join(latest.strengths[:2])}")

        result = "\n".join(lines)
        return result[:max_chars] if len(result) > len("[AUTO-REFLEXIÓN RECIENTE]") + 2 else ""

    def get_stats(self) -> dict:
        """Estadísticas de reflexión."""
        latest = self.get_latest()
        return {
            "total_reflections": self.total_reflections,
            "stored_reflections": len(self.reflections),
            "interaction_counter": self.interaction_counter,
            "next_reflection_in": self.reflection_interval - (self.interaction_counter % self.reflection_interval),
            "latest_confidence": latest.confidence if latest else 0,
            "latest_blind_spots": len(latest.blind_spots) if latest else 0,
            "latest_strengths": len(latest.strengths) if latest else 0,
        }

    def status(self) -> str:
        """Status de una línea."""
        latest = self.get_latest()
        if latest:
            spots = len(latest.blind_spots)
            strengths = len(latest.strengths)
            return (f"Reflexiones: {self.total_reflections} | "
                    f"Fortalezas: {strengths} | Puntos ciegos: {spots} | "
                    f"Próxima en: {self.reflection_interval - (self.interaction_counter % self.reflection_interval)} msgs")
        return f"Reflexiones: 0 | Esperando {self.reflection_interval} interacciones"

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = ["=== REFLECTION ENGINE REPORT ==="]
        lines.append(f"Total reflexiones: {self.total_reflections}")
        lines.append(f"Reflexiones almacenadas: {len(self.reflections)}")
        lines.append(f"Intervalo: cada {self.reflection_interval} interacciones")
        lines.append(f"Interacciones desde última: {self.interaction_counter % self.reflection_interval}")

        latest = self.get_latest()
        if latest:
            lines.append(f"\nÚltima reflexión ({latest._date_str()}):")
            lines.append(f"  Confianza: {latest.confidence:.0%}")
            lines.append(f"  Datos analizados: {latest.data_points}")

            if latest.observations:
                lines.append(f"\n  Observaciones:")
                for obs in latest.observations:
                    lines.append(f"    • {obs}")

            if latest.strengths:
                lines.append(f"\n  Fortalezas:")
                for s in latest.strengths:
                    lines.append(f"    ✓ {s}")

            if latest.blind_spots:
                lines.append(f"\n  Puntos ciegos:")
                for b in latest.blind_spots:
                    lines.append(f"    ⚠️ {b}")

            if latest.improvement_plan:
                lines.append(f"\n  Plan de mejora:")
                for p in latest.improvement_plan:
                    lines.append(f"    → {p}")

        # Historial resumido
        if len(self.reflections) > 1:
            lines.append(f"\nHistorial (últimas 5):")
            for entry in self.reflections[-5:]:
                spots = len(entry.blind_spots)
                strengths_count = len(entry.strengths)
                lines.append(
                    f"  [{entry._date_str()}] "
                    f"confianza={entry.confidence:.0%} "
                    f"fortalezas={strengths_count} ciegos={spots}"
                )

        return "\n".join(lines)

    def save(self):
        """Persiste estado a disco."""
        data = {
            "total_reflections": self.total_reflections,
            "interaction_counter": self.interaction_counter,
            "reflections": [r.to_dict() for r in self.reflections[-self.max_reflections:]],
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
            self.total_reflections = data.get("total_reflections", 0)
            self.interaction_counter = data.get("interaction_counter", 0)
            self.reflections = [
                ReflectionEntry.from_dict(r) for r in data.get("reflections", [])
            ]
        except Exception:
            pass

    def clear(self):
        """Limpia todas las reflexiones."""
        self.reflections = []
        self.total_reflections = 0
        self.interaction_counter = 0
