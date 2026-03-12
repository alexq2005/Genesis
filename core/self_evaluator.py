"""
GENESIS — Self-Evaluation Engine (v2.3)

Metacognición: Genesis evalúa la calidad de sus propias respuestas,
detecta patrones de éxito/fallo, y auto-ajusta parámetros.

Componentes:
- QualityScorer: Evalúa coherencia, relevancia, longitud, completitud
- PatternTracker: Detecta qué tipos de preguntas responde bien/mal
- AutoTuner: Ajusta temperatura, max_tokens, system_prompt según patrones
"""
import time
import json
import re
from pathlib import Path


class QualityScorer:
    """
    Evalúa la calidad de una respuesta sin necesitar el LLM.
    Usa heurísticas rápidas para scoring en tiempo real.
    """

    # Frases genéricas que indican baja calidad
    GENERIC_PHRASES = [
        "como puedo ayudarte",
        "hay algo mas que",
        "no dudes en preguntar",
        "espero que esto te ayude",
        "si tienes alguna otra pregunta",
        "estoy aqui para ayudarte",
        "quieres saber mas",
        "let me know if",
        "hope this helps",
        "feel free to ask",
        "is there anything else",
        "happy to help",
    ]

    # Indicadores de respuesta con errores
    ERROR_INDICATORS = [
        "[error]", "[timeout]", "traceback", "exception",
        "no pude", "no puedo generar", "lo siento, no",
    ]

    def score(self, user_input: str, response: str, intent: str = "chat") -> dict:
        """
        Evalúa una respuesta y retorna scores detallados.

        Returns:
            dict con 'overall' (0.0-1.0) y desglose por categoría.
        """
        scores = {}

        # Respuesta vacía = score mínimo
        if not response or len(response.strip()) < 3:
            return {
                "overall": 0.05,
                "scores": {"relevance": 0, "length": 0, "specificity": 0,
                           "completeness": 0, "error_free": 0},
                "grade": "F",
            }

        # 1. Relevancia: ¿la respuesta menciona conceptos de la pregunta?
        scores["relevance"] = self._score_relevance(user_input, response)

        # 2. Longitud: ¿es apropiada para el tipo de pregunta?
        scores["length"] = self._score_length(user_input, response, intent)

        # 3. Genericidad: ¿evita frases genéricas/repetitivas?
        scores["specificity"] = self._score_specificity(response)

        # 4. Completitud: ¿tiene estructura y contenido sustancial?
        scores["completeness"] = self._score_completeness(response, intent)

        # 5. Error-free: ¿no contiene indicadores de error?
        scores["error_free"] = self._score_error_free(response)

        # Overall: promedio ponderado
        weights = {
            "relevance": 0.30,
            "length": 0.15,
            "specificity": 0.20,
            "completeness": 0.20,
            "error_free": 0.15,
        }
        overall = sum(scores[k] * weights[k] for k in weights)

        return {
            "overall": round(overall, 3),
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "grade": self._grade(overall),
        }

    def _score_relevance(self, user_input: str, response: str) -> float:
        """Mide cuántos conceptos del input aparecen en la respuesta."""
        # Extraer palabras significativas (>3 chars) del input
        input_words = set(
            w.lower() for w in re.findall(r'\b\w+\b', user_input)
            if len(w) > 3
        )
        if not input_words:
            return 0.7  # Sin palabras significativas, neutral

        response_lower = response.lower()
        matches = sum(1 for w in input_words if w in response_lower)
        ratio = matches / len(input_words)

        # Escalar: 0% match -> 0.2, 50% -> 0.7, 100% -> 1.0
        return min(1.0, 0.2 + ratio * 0.8)

    def _score_length(self, user_input: str, response: str, intent: str) -> float:
        """Evalúa si la longitud es apropiada para el tipo de pregunta."""
        resp_len = len(response)
        input_len = len(user_input)

        # Expectativas por intent
        ideal_ranges = {
            "chat": (50, 500),
            "code": (100, 3000),
            "research": (200, 2000),
            "creative": (100, 2000),
            "analysis": (150, 2500),
        }
        min_len, max_len = ideal_ranges.get(intent, (50, 1500))

        if resp_len < 20:
            return 0.1  # Demasiado corta
        elif resp_len < min_len:
            return 0.4 + 0.3 * (resp_len / min_len)
        elif resp_len <= max_len:
            return 1.0  # Rango ideal
        else:
            # Penalizar exceso gradualmente
            excess = (resp_len - max_len) / max_len
            return max(0.3, 1.0 - excess * 0.5)

    def _score_specificity(self, response: str) -> float:
        """Penaliza respuestas genéricas o con frases de relleno."""
        response_lower = response.lower()
        generic_count = sum(
            1 for phrase in self.GENERIC_PHRASES
            if phrase in response_lower
        )

        if generic_count == 0:
            return 1.0
        elif generic_count == 1:
            return 0.6
        elif generic_count == 2:
            return 0.3
        else:
            return 0.1

    def _score_completeness(self, response: str, intent: str) -> float:
        """Evalúa si la respuesta tiene estructura y contenido sustancial."""
        score = 0.5  # Base

        # Tiene párrafos o estructura?
        if '\n' in response:
            score += 0.1

        # Tiene listas o pasos?
        if re.search(r'^\s*[-*\d]+[.)]\s', response, re.MULTILINE):
            score += 0.1

        # Tiene código (para intent code)?
        if intent == "code" and ('```' in response or '    ' in response):
            score += 0.15

        # Longitud sustancial
        words = len(response.split())
        if words >= 20:
            score += 0.1
        if words >= 50:
            score += 0.05

        return min(1.0, score)

    def _score_error_free(self, response: str) -> float:
        """Verifica que no haya indicadores de error en la respuesta."""
        response_lower = response.lower()
        for indicator in self.ERROR_INDICATORS:
            if indicator in response_lower:
                return 0.1
        return 1.0

    def _grade(self, score: float) -> str:
        """Convierte score numérico en letra."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.65:
            return "C"
        elif score >= 0.5:
            return "D"
        else:
            return "F"


class PatternTracker:
    """
    Rastrea patrones de calidad por intent, longitud de input,
    y otros factores para detectar fortalezas y debilidades.
    """

    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.history = []  # Lista de evaluaciones recientes
        self.intent_stats = {}  # intent -> {total, sum_score, count_good, count_bad}
        self.total_evaluated = 0

    def record(self, user_input: str, response: str, intent: str,
               quality_score: dict, user_feedback: str = None):
        """Registra una evaluación para análisis de patrones."""
        record = {
            "timestamp": time.time(),
            "intent": intent,
            "input_len": len(user_input),
            "response_len": len(response),
            "overall": quality_score["overall"],
            "grade": quality_score["grade"],
            "scores": quality_score["scores"],
            "user_feedback": user_feedback,  # "+", "-", or None
        }

        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        # Actualizar stats por intent
        if intent not in self.intent_stats:
            self.intent_stats[intent] = {
                "total": 0, "sum_score": 0.0,
                "count_good": 0, "count_bad": 0,
                "sum_length": 0,
            }
        stats = self.intent_stats[intent]
        stats["total"] += 1
        stats["sum_score"] += quality_score["overall"]
        stats["sum_length"] += len(response)
        if quality_score["overall"] >= 0.75:
            stats["count_good"] += 1
        elif quality_score["overall"] < 0.5:
            stats["count_bad"] += 1

        # Incorporar feedback del usuario si existe
        if user_feedback == "+":
            stats["count_good"] += 1
        elif user_feedback == "-":
            stats["count_bad"] += 1

        self.total_evaluated += 1

    def get_strengths(self) -> list:
        """Retorna los intents donde Genesis responde mejor."""
        strengths = []
        for intent, stats in self.intent_stats.items():
            if stats["total"] >= 3:  # Minimo 3 samples
                avg = stats["sum_score"] / stats["total"]
                if avg >= 0.75:
                    strengths.append({
                        "intent": intent,
                        "avg_score": round(avg, 3),
                        "samples": stats["total"],
                    })
        return sorted(strengths, key=lambda x: x["avg_score"], reverse=True)

    def get_weaknesses(self) -> list:
        """Retorna los intents donde Genesis responde peor."""
        weaknesses = []
        for intent, stats in self.intent_stats.items():
            if stats["total"] >= 3:
                avg = stats["sum_score"] / stats["total"]
                if avg < 0.6:
                    weaknesses.append({
                        "intent": intent,
                        "avg_score": round(avg, 3),
                        "samples": stats["total"],
                        "bad_ratio": round(stats["count_bad"] / stats["total"], 2),
                    })
        return sorted(weaknesses, key=lambda x: x["avg_score"])

    def get_average_score(self) -> float:
        """Score promedio global."""
        if not self.history:
            return 0.0
        return sum(r["overall"] for r in self.history) / len(self.history)

    def get_trend(self, window: int = 20) -> str:
        """Detecta si la calidad está mejorando, empeorando, o estable."""
        if len(self.history) < window * 2:
            return "insufficient_data"

        recent = self.history[-window:]
        older = self.history[-window * 2:-window]

        avg_recent = sum(r["overall"] for r in recent) / len(recent)
        avg_older = sum(r["overall"] for r in older) / len(older)

        diff = avg_recent - avg_older
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"

    def get_intent_report(self) -> dict:
        """Reporte completo por intent."""
        report = {}
        for intent, stats in self.intent_stats.items():
            if stats["total"] > 0:
                report[intent] = {
                    "total": stats["total"],
                    "avg_score": round(stats["sum_score"] / stats["total"], 3),
                    "good_ratio": round(stats["count_good"] / stats["total"], 2),
                    "bad_ratio": round(stats["count_bad"] / stats["total"], 2),
                    "avg_response_len": int(stats["sum_length"] / stats["total"]),
                }
        return report

    def to_dict(self) -> dict:
        """Serializa para persistencia."""
        return {
            "history": self.history[-100:],  # Solo últimos 100
            "intent_stats": self.intent_stats,
            "total_evaluated": self.total_evaluated,
        }

    def load_dict(self, data: dict):
        """Restaura desde dict."""
        self.history = data.get("history", [])
        self.intent_stats = data.get("intent_stats", {})
        self.total_evaluated = data.get("total_evaluated", 0)


class AutoTuner:
    """
    Ajusta parámetros de inferencia basándose en patrones de calidad.
    Aprende la configuración óptima para cada tipo de tarea.
    """

    def __init__(self):
        # Configuraciones por intent (se ajustan con el tiempo)
        self.intent_configs = {
            "chat": {"temperature": 0.7, "max_tokens_hint": 512},
            "code": {"temperature": 0.3, "max_tokens_hint": 1536},
            "research": {"temperature": 0.5, "max_tokens_hint": 1024},
            "creative": {"temperature": 0.9, "max_tokens_hint": 1024},
            "analysis": {"temperature": 0.4, "max_tokens_hint": 1024},
        }
        self.adjustments_made = 0
        self.adjustment_log = []

    def get_config(self, intent: str) -> dict:
        """Retorna la configuración optimizada para un intent."""
        return self.intent_configs.get(intent, {
            "temperature": 0.7,
            "max_tokens_hint": 1024,
        }).copy()

    def adjust(self, intent: str, pattern_tracker: PatternTracker):
        """
        Ajusta la configuración de un intent basándose en sus patrones.
        Solo ajusta si hay suficiente data (>= 5 samples).
        """
        if intent not in pattern_tracker.intent_stats:
            return

        stats = pattern_tracker.intent_stats[intent]
        if stats["total"] < 5:
            return  # No hay suficiente data

        avg_score = stats["sum_score"] / stats["total"]
        avg_len = stats["sum_length"] / stats["total"]
        bad_ratio = stats["count_bad"] / stats["total"]

        config = self.intent_configs.setdefault(intent, {
            "temperature": 0.7,
            "max_tokens_hint": 1024,
        })

        adjustments = []

        # Si muchas respuestas son malas, bajar temperatura (más determinista)
        if bad_ratio > 0.3 and config["temperature"] > 0.2:
            old_temp = config["temperature"]
            config["temperature"] = max(0.2, config["temperature"] - 0.1)
            adjustments.append(f"temp {old_temp:.1f}->{config['temperature']:.1f}")

        # Si las respuestas son muy buenas, subir ligeramente la temperatura
        if avg_score > 0.85 and bad_ratio < 0.1 and config["temperature"] < 0.95:
            old_temp = config["temperature"]
            config["temperature"] = min(0.95, config["temperature"] + 0.05)
            adjustments.append(f"temp {old_temp:.1f}->{config['temperature']:.1f}")

        # Si las respuestas son muy cortas y el score de length es bajo
        recent = [r for r in pattern_tracker.history[-20:] if r["intent"] == intent]
        if recent:
            avg_length_score = sum(r["scores"].get("length", 0.5) for r in recent) / len(recent)
            if avg_length_score < 0.5 and avg_len < 200:
                old_hint = config["max_tokens_hint"]
                config["max_tokens_hint"] = min(2048, config["max_tokens_hint"] + 256)
                adjustments.append(f"tokens {old_hint}->{config['max_tokens_hint']}")

        # Si las respuestas son excesivamente largas
        if avg_len > 2000 and intent not in ("code", "creative"):
            old_hint = config["max_tokens_hint"]
            config["max_tokens_hint"] = max(256, config["max_tokens_hint"] - 128)
            adjustments.append(f"tokens {old_hint}->{config['max_tokens_hint']}")

        if adjustments:
            self.adjustments_made += 1
            log_entry = {
                "timestamp": time.time(),
                "intent": intent,
                "adjustments": adjustments,
                "avg_score": round(avg_score, 3),
                "bad_ratio": round(bad_ratio, 2),
            }
            self.adjustment_log.append(log_entry)
            if len(self.adjustment_log) > 50:
                self.adjustment_log = self.adjustment_log[-50:]

    def to_dict(self) -> dict:
        return {
            "intent_configs": self.intent_configs,
            "adjustments_made": self.adjustments_made,
            "adjustment_log": self.adjustment_log[-20:],
        }

    def load_dict(self, data: dict):
        saved_configs = data.get("intent_configs", {})
        for intent, config in saved_configs.items():
            self.intent_configs[intent] = config
        self.adjustments_made = data.get("adjustments_made", 0)
        self.adjustment_log = data.get("adjustment_log", [])


class SelfEvaluator:
    """
    Motor de auto-evaluación que coordina QualityScorer,
    PatternTracker, y AutoTuner.
    """

    def __init__(self, base_dir: str = None):
        self.scorer = QualityScorer()
        self.tracker = PatternTracker()
        self.tuner = AutoTuner()

        self.base_dir = Path(base_dir) if base_dir else Path("data/self_eval")
        self.data_file = self.base_dir / "evaluator_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.total_evaluations = 0
        self.auto_tune_interval = 10  # Auto-tune cada N evaluaciones
        self.enabled = True

        # Cargar estado previo
        self._load()

    def evaluate(self, user_input: str, response: str,
                 intent: str = "chat", user_feedback: str = None) -> dict:
        """
        Evalúa una respuesta y registra los resultados.

        Args:
            user_input: Pregunta del usuario
            response: Respuesta generada
            intent: Intent clasificado por el router
            user_feedback: "+", "-", o None

        Returns:
            dict con score, grade, y desglose
        """
        if not self.enabled:
            return {"overall": 0.5, "grade": "?", "scores": {}}

        # Evaluar calidad
        quality = self.scorer.score(user_input, response, intent)

        # Registrar en pattern tracker
        self.tracker.record(user_input, response, intent, quality, user_feedback)

        self.total_evaluations += 1

        # Auto-tune periódico
        if self.total_evaluations % self.auto_tune_interval == 0:
            self._auto_tune_all()

        # Persistir periódicamente
        if self.total_evaluations % 20 == 0:
            self.save()

        return quality

    def record_feedback(self, user_feedback: str):
        """Registra feedback del usuario para la última respuesta."""
        if self.tracker.history:
            self.tracker.history[-1]["user_feedback"] = user_feedback
            # Re-trigger auto-tune si hay feedback negativo
            if user_feedback == "-":
                intent = self.tracker.history[-1].get("intent", "chat")
                self.tuner.adjust(intent, self.tracker)

    def get_tuned_config(self, intent: str) -> dict:
        """Retorna la configuración optimizada para un intent."""
        return self.tuner.get_config(intent)

    def _auto_tune_all(self):
        """Ejecuta auto-tune para todos los intents con suficiente data."""
        for intent in self.tracker.intent_stats:
            self.tuner.adjust(intent, self.tracker)

    def get_stats(self) -> dict:
        """Retorna estadísticas completas."""
        return {
            "total_evaluations": self.total_evaluations,
            "avg_score": round(self.tracker.get_average_score(), 3),
            "trend": self.tracker.get_trend(),
            "strengths": self.tracker.get_strengths(),
            "weaknesses": self.tracker.get_weaknesses(),
            "auto_adjustments": self.tuner.adjustments_made,
            "enabled": self.enabled,
        }

    def status(self) -> str:
        """Status string para /status."""
        avg = self.tracker.get_average_score()
        trend = self.tracker.get_trend()
        trend_symbol = {"improving": "+", "declining": "-", "stable": "=",
                        "insufficient_data": "?"}
        lines = [
            f"  Evaluaciones: {self.total_evaluations}",
            f"  Score promedio: {avg:.2f} ({trend_symbol.get(trend, '?')} {trend})",
            f"  Auto-ajustes: {self.tuner.adjustments_made}",
            f"  Habilitado: {'si' if self.enabled else 'no'}",
        ]
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Reporte completo para el comando /evaluate."""
        lines = ["=== SELF-EVALUATION ENGINE ===", ""]

        # General
        avg = self.tracker.get_average_score()
        trend = self.tracker.get_trend()
        lines.append(f"Total evaluaciones: {self.total_evaluations}")
        lines.append(f"Score promedio: {avg:.3f}")
        lines.append(f"Tendencia: {trend}")
        lines.append(f"Auto-ajustes realizados: {self.tuner.adjustments_made}")
        lines.append("")

        # Por intent
        intent_report = self.tracker.get_intent_report()
        if intent_report:
            lines.append("RENDIMIENTO POR INTENT:")
            for intent, data in sorted(intent_report.items(),
                                        key=lambda x: x[1]["avg_score"], reverse=True):
                lines.append(f"  {intent}: avg={data['avg_score']:.2f} "
                             f"good={data['good_ratio']:.0%} "
                             f"bad={data['bad_ratio']:.0%} "
                             f"n={data['total']}")
            lines.append("")

        # Fortalezas
        strengths = self.tracker.get_strengths()
        if strengths:
            lines.append("FORTALEZAS:")
            for s in strengths[:3]:
                lines.append(f"  + {s['intent']}: {s['avg_score']:.2f} ({s['samples']} samples)")
            lines.append("")

        # Debilidades
        weaknesses = self.tracker.get_weaknesses()
        if weaknesses:
            lines.append("DEBILIDADES:")
            for w in weaknesses[:3]:
                lines.append(f"  - {w['intent']}: {w['avg_score']:.2f} "
                             f"({w['bad_ratio']:.0%} malas)")
            lines.append("")

        # Últimos ajustes
        if self.tuner.adjustment_log:
            lines.append("ULTIMOS AJUSTES:")
            for adj in self.tuner.adjustment_log[-5:]:
                lines.append(f"  [{adj['intent']}] {', '.join(adj['adjustments'])} "
                             f"(score={adj['avg_score']:.2f})")
            lines.append("")

        # Configuración actual
        lines.append("CONFIGURACION ACTUAL POR INTENT:")
        for intent, config in sorted(self.tuner.intent_configs.items()):
            lines.append(f"  {intent}: temp={config['temperature']:.2f} "
                         f"tokens_hint={config['max_tokens_hint']}")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado completo."""
        data = {
            "total_evaluations": self.total_evaluations,
            "tracker": self.tracker.to_dict(),
            "tuner": self.tuner.to_dict(),
            "enabled": self.enabled,
        }
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """Carga estado previo si existe."""
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.total_evaluations = data.get("total_evaluations", 0)
            self.enabled = data.get("enabled", True)
            if "tracker" in data:
                self.tracker.load_dict(data["tracker"])
            if "tuner" in data:
                self.tuner.load_dict(data["tuner"])
        except Exception:
            pass

    def clear(self):
        """Resetea todo el estado."""
        self.tracker = PatternTracker()
        self.tuner = AutoTuner()
        self.total_evaluations = 0
        if self.data_file.exists():
            self.data_file.unlink()
