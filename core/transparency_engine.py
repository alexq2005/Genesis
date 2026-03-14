"""
GENESIS — Transparency Engine (v4.2)

Explicación de decisiones internas. Registra trazas de decisiones
con factores ponderados, genera explicaciones legibles, calcula
intervalos de confianza y responde preguntas "por qué" buscando
en el historial de trazas.

Componentes:
- DecisionTrace: traza completa de una decisión con factores
- TraceExplainer: generador de explicaciones legibles
- ConfidenceInterval: intervalo de confianza calculado desde factores
- TransparencyEngine: coordinador con búsqueda y persistencia
"""
import time
import json
import re
import math
from pathlib import Path
from collections import defaultdict


class DecisionTrace:
    """Traza completa de una decisión con factores ponderados."""

    _next_id = 1

    def __init__(self, decision: str, factors: list, chosen_option: str,
                 alternatives: list = None):
        self.decision_id = DecisionTrace._next_id
        DecisionTrace._next_id += 1
        self.decision = decision[:300]
        self.factors = factors  # [{factor_name, weight, value}]
        self.chosen_option = chosen_option[:200]
        self.alternatives = (alternatives or [])[:10]
        self.confidence = self._compute_confidence()
        self.timestamp = time.time()

    def _compute_confidence(self) -> float:
        """Calcula confianza basada en pesos y valores de factores."""
        if not self.factors:
            return 0.5

        weighted_sum = 0.0
        weight_total = 0.0

        for factor in self.factors:
            w = factor.get("weight", 0.5)
            v = factor.get("value", 0.5)
            weighted_sum += w * v
            weight_total += w

        if weight_total == 0:
            return 0.5

        raw = weighted_sum / weight_total

        # Penalizar si hay muchas alternativas competitivas
        alt_penalty = min(0.2, len(self.alternatives) * 0.04)

        return round(max(0.1, min(1.0, raw - alt_penalty)), 3)

    def get_dominant_factor(self) -> dict:
        """Retorna el factor con mayor peso * valor."""
        if not self.factors:
            return {"factor_name": "ninguno", "weight": 0, "value": 0}
        return max(self.factors,
                   key=lambda f: f.get("weight", 0) * f.get("value", 0))

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "decision": self.decision,
            "factors": self.factors,
            "chosen_option": self.chosen_option,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionTrace":
        trace = cls(
            decision=d.get("decision", ""),
            factors=d.get("factors", []),
            chosen_option=d.get("chosen_option", ""),
            alternatives=d.get("alternatives", []),
        )
        trace.decision_id = d.get("decision_id", trace.decision_id)
        trace.confidence = d.get("confidence", trace.confidence)
        trace.timestamp = d.get("timestamp", time.time())
        # Actualizar el contador global para evitar colisiones
        if trace.decision_id >= DecisionTrace._next_id:
            DecisionTrace._next_id = trace.decision_id + 1
        return trace


class TraceExplainer:
    """Genera explicaciones legibles desde DecisionTrace."""

    def explain(self, trace: DecisionTrace) -> str:
        """Genera explicación textual completa de una decisión."""
        lines = [f"[DECISION #{trace.decision_id}] {trace.decision}"]
        lines.append(f"Opcion elegida: {trace.chosen_option}")
        lines.append(f"Confianza: {trace.confidence:.0%}")
        lines.append("")

        # Factores ordenados por impacto (weight * value)
        if trace.factors:
            lines.append("Factores considerados (de mayor a menor impacto):")
            sorted_factors = sorted(
                trace.factors,
                key=lambda f: f.get("weight", 0) * f.get("value", 0),
                reverse=True,
            )
            for i, factor in enumerate(sorted_factors, 1):
                name = factor.get("factor_name", "?")
                weight = factor.get("weight", 0)
                value = factor.get("value", 0)
                impact = weight * value
                bar = self._make_bar(impact, 10)
                lines.append(
                    f"  {i}. {name}: peso={weight:.1f}, valor={value:.1f}, "
                    f"impacto={impact:.2f} {bar}"
                )

        # Alternativas descartadas
        if trace.alternatives:
            lines.append("")
            lines.append("Alternativas descartadas:")
            for alt in trace.alternatives:
                lines.append(f"  - {alt}")

        return "\n".join(lines)

    def explain_brief(self, trace: DecisionTrace) -> str:
        """Explicación breve de una sola línea."""
        dominant = trace.get_dominant_factor()
        return (
            f"Decision #{trace.decision_id}: '{trace.chosen_option[:50]}' "
            f"(confianza {trace.confidence:.0%}, "
            f"factor clave: {dominant.get('factor_name', '?')})"
        )

    def explain_chain(self, traces: list) -> str:
        """Explica una cadena de decisiones relacionadas."""
        if not traces:
            return "Sin decisiones registradas."

        lines = ["Cadena de razonamiento:"]
        for i, trace in enumerate(traces):
            connector = "→" if i > 0 else "•"
            dominant = trace.get_dominant_factor()
            lines.append(
                f"  {connector} [{trace.confidence:.0%}] {trace.decision[:60]} "
                f"=> {trace.chosen_option[:40]} "
                f"(por: {dominant.get('factor_name', '?')})"
            )
        return "\n".join(lines)

    def _make_bar(self, value: float, width: int = 10) -> str:
        """Genera barra visual de impacto."""
        filled = int(max(0, min(width, value * width)))
        return "[" + "#" * filled + "." * (width - filled) + "]"


class ConfidenceInterval:
    """Intervalo de confianza calculado desde factores de decisión."""

    def __init__(self, lower: float, upper: float, point_estimate: float):
        self.lower = round(max(0.0, lower), 3)
        self.upper = round(min(1.0, upper), 3)
        self.point_estimate = round(max(0.0, min(1.0, point_estimate)), 3)

    @classmethod
    def from_factors(cls, factors: list) -> "ConfidenceInterval":
        """Calcula intervalo de confianza desde lista de factores."""
        if not factors:
            return cls(0.3, 0.7, 0.5)

        values = [f.get("weight", 0.5) * f.get("value", 0.5)
                  for f in factors]
        n = len(values)
        mean = sum(values) / n

        if n == 1:
            # Con un solo factor, margen amplio
            return cls(
                lower=max(0.0, mean - 0.25),
                upper=min(1.0, mean + 0.25),
                point_estimate=mean,
            )

        # Desviación estándar
        variance = sum((v - mean) ** 2 for v in values) / n
        std_dev = math.sqrt(variance)

        # Intervalo basado en std_dev y tamaño de muestra
        margin = std_dev / math.sqrt(n) * 1.96  # ~95% confianza

        return cls(
            lower=max(0.0, mean - margin),
            upper=min(1.0, mean + margin),
            point_estimate=mean,
        )

    @property
    def width(self) -> float:
        """Ancho del intervalo (menor = más certeza)."""
        return round(self.upper - self.lower, 3)

    @property
    def certainty(self) -> str:
        """Nivel de certeza textual."""
        w = self.width
        if w < 0.1:
            return "muy alta"
        elif w < 0.2:
            return "alta"
        elif w < 0.35:
            return "moderada"
        elif w < 0.5:
            return "baja"
        return "muy baja"

    def to_dict(self) -> dict:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "point_estimate": self.point_estimate,
            "width": self.width,
            "certainty": self.certainty,
        }


class TransparencyEngine:
    """
    Coordinador de transparencia y explicación de decisiones.
    Registra trazas, genera explicaciones, calcula confianza
    y responde preguntas "por qué".
    """

    def __init__(self, base_dir: str = "data/transparency"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.explainer = TraceExplainer()
        self.traces = []             # Historial de trazas
        self.max_traces = 300
        self.total_decisions = 0
        self.total_explanations = 0
        self.total_why_queries = 0
        self.enabled = True

        self._load()

    def record_decision(self, decision: str, factors: list,
                        chosen: str, alternatives: list = None) -> DecisionTrace:
        """Registra una traza de decisión."""
        trace = DecisionTrace(
            decision=decision,
            factors=factors,
            chosen_option=chosen,
            alternatives=alternatives,
        )
        self.traces.append(trace)
        self.total_decisions += 1

        if len(self.traces) > self.max_traces:
            self.traces = self.traces[-self.max_traces:]

        return trace

    def explain(self, decision_id: int = None) -> str:
        """Genera explicación para una decisión específica o la más reciente."""
        self.total_explanations += 1

        if decision_id is not None:
            trace = self._find_trace(decision_id)
            if not trace:
                return f"Decision #{decision_id} no encontrada."
            return self.explainer.explain(trace)

        if not self.traces:
            return "Sin decisiones registradas."

        return self.explainer.explain(self.traces[-1])

    def get_confidence(self, decision_id: int = None) -> ConfidenceInterval:
        """Retorna intervalo de confianza de una decisión."""
        if decision_id is not None:
            trace = self._find_trace(decision_id)
        elif self.traces:
            trace = self.traces[-1]
        else:
            trace = None

        if not trace:
            return ConfidenceInterval(0.3, 0.7, 0.5)

        return ConfidenceInterval.from_factors(trace.factors)

    def why(self, question: str) -> str:
        """Busca trazas relevantes y explica la cadena de razonamiento."""
        self.total_why_queries += 1

        if not self.traces:
            return "No hay decisiones registradas para explicar."

        question_lower = question.lower()

        # Buscar trazas relevantes por similitud textual
        scored_traces = []
        for trace in self.traces:
            score = self._relevance_score(question_lower, trace)
            if score > 0:
                scored_traces.append((trace, score))

        if not scored_traces:
            # Fallback: mostrar las últimas 3 decisiones
            recent = self.traces[-3:]
            return (
                f"No se encontro una decision directamente relevante a '{question[:50]}'.\n\n"
                + self.explainer.explain_chain(recent)
            )

        # Ordenar por relevancia y tomar las más relevantes
        scored_traces.sort(key=lambda x: x[1], reverse=True)
        relevant = [t for t, s in scored_traces[:5]]

        lines = [f"[TRANSPARENCIA] Respuesta a: {question[:80]}"]
        lines.append("")

        # Explicar la traza más relevante en detalle
        lines.append(self.explainer.explain(relevant[0]))

        # Si hay más trazas relacionadas, mostrar cadena
        if len(relevant) > 1:
            lines.append("")
            lines.append(self.explainer.explain_chain(relevant))

        return "\n".join(lines)

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Inyecta contexto de transparencia si hay decisiones recientes."""
        if not self.enabled or not self.traces:
            return ""

        # Mostrar las últimas 2 decisiones como contexto
        recent = self.traces[-2:]
        parts = ["[TRANSPARENCIA]"]

        for trace in recent:
            dominant = trace.get_dominant_factor()
            ci = ConfidenceInterval.from_factors(trace.factors)
            parts.append(
                f"Decision reciente: '{trace.decision[:50]}' "
                f"-> {trace.chosen_option[:30]} "
                f"(confianza: {ci.certainty}, "
                f"factor clave: {dominant.get('factor_name', '?')})"
            )

        return " | ".join(parts)[:max_chars]

    def get_stats(self) -> dict:
        avg_confidence = 0.0
        if self.traces:
            avg_confidence = sum(t.confidence for t in self.traces) / len(self.traces)

        return {
            "total_decisions": self.total_decisions,
            "total_explanations": self.total_explanations,
            "total_why_queries": self.total_why_queries,
            "traces_stored": len(self.traces),
            "avg_confidence": round(avg_confidence, 3),
            "recent_decisions": [
                {
                    "id": t.decision_id,
                    "decision": t.decision[:50],
                    "confidence": t.confidence,
                }
                for t in self.traces[-5:]
            ],
        }

    def status(self) -> str:
        avg = 0.0
        if self.traces:
            avg = sum(t.confidence for t in self.traces) / len(self.traces)
        return (f"  Decisiones: {self.total_decisions} | "
                f"Explicaciones: {self.total_explanations} | "
                f"Why queries: {self.total_why_queries} | "
                f"Confianza promedio: {avg:.0%}")

    def generate_report(self) -> str:
        lines = [
            "=== TRANSPARENCY ENGINE REPORT ===",
            f"Total decisiones: {self.total_decisions}",
            f"Total explicaciones: {self.total_explanations}",
            f"Total why queries: {self.total_why_queries}",
            f"Trazas almacenadas: {len(self.traces)}",
        ]

        if self.traces:
            avg_conf = sum(t.confidence for t in self.traces) / len(self.traces)
            lines.append(f"Confianza promedio: {avg_conf:.0%}")

            # Distribución de confianza
            high = sum(1 for t in self.traces if t.confidence > 0.7)
            med = sum(1 for t in self.traces if 0.4 <= t.confidence <= 0.7)
            low = sum(1 for t in self.traces if t.confidence < 0.4)
            lines.append(f"\nDistribucion de confianza:")
            lines.append(f"  Alta (>70%): {high}")
            lines.append(f"  Media (40-70%): {med}")
            lines.append(f"  Baja (<40%): {low}")

            # Factores más frecuentes
            factor_counts = defaultdict(int)
            for trace in self.traces:
                for factor in trace.factors:
                    factor_counts[factor.get("factor_name", "?")] += 1

            if factor_counts:
                lines.append(f"\nFactores mas frecuentes:")
                for fname, count in sorted(
                    factor_counts.items(), key=lambda x: x[1], reverse=True
                )[:8]:
                    lines.append(f"  {fname}: {count} usos")

            # Últimas decisiones
            lines.append(f"\nUltimas 5 decisiones:")
            for trace in self.traces[-5:]:
                lines.append(
                    f"  #{trace.decision_id}: {trace.decision[:50]} "
                    f"-> {trace.chosen_option[:30]} "
                    f"(confianza={trace.confidence:.0%})"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_decisions": self.total_decisions,
            "total_explanations": self.total_explanations,
            "total_why_queries": self.total_why_queries,
            "next_id": DecisionTrace._next_id,
            "traces": [t.to_dict() for t in self.traces[-200:]],
        }
        path = self.base_dir / "transparency_engine.json"
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "transparency_engine.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.total_decisions = data.get("total_decisions", 0)
            self.total_explanations = data.get("total_explanations", 0)
            self.total_why_queries = data.get("total_why_queries", 0)
            DecisionTrace._next_id = data.get("next_id", 1)
            self.traces = [
                DecisionTrace.from_dict(d)
                for d in data.get("traces", [])
            ]
        except Exception:
            pass

    def clear(self):
        self.traces = []
        self.total_decisions = 0
        self.total_explanations = 0
        self.total_why_queries = 0
        DecisionTrace._next_id = 1
        self.save()

    def _find_trace(self, decision_id: int) -> DecisionTrace:
        """Busca una traza por ID."""
        for trace in self.traces:
            if trace.decision_id == decision_id:
                return trace
        return None

    def _relevance_score(self, question: str, trace: DecisionTrace) -> float:
        """Calcula score de relevancia entre pregunta y traza."""
        # Tokenizar pregunta (palabras > 2 caracteres)
        q_words = set(w for w in question.split() if len(w) > 2)
        if not q_words:
            return 0.0

        # Campos a buscar
        searchable = (
            trace.decision.lower() + " " +
            trace.chosen_option.lower() + " " +
            " ".join(trace.alternatives).lower() + " " +
            " ".join(f.get("factor_name", "") for f in trace.factors).lower()
        )

        # Contar coincidencias
        matches = sum(1 for w in q_words if w in searchable)
        if matches == 0:
            return 0.0

        # Score normalizado por total de palabras de la pregunta
        score = matches / len(q_words)

        # Bonus por recencia (trazas más recientes son más relevantes)
        age = time.time() - trace.timestamp
        recency_bonus = max(0, 0.2 - age / 86400 * 0.01)  # Decae ~0.01/día

        return round(score + recency_bonus, 3)
