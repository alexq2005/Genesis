"""
GENESIS — Hypothesis Engine (v2.8)

Motor de generación y evaluación de hipótesis. Genesis formula
hipótesis a partir de observaciones, las evalúa con evidencia,
y las refina iterativamente.

Componentes:
- Evidence: pieza de evidencia a favor o en contra
- Hypothesis: hipótesis con estado, evidencia, plausibility score
- HypothesisGenerator: genera hipótesis desde patrones de texto
- HypothesisEvaluator: evalúa y rankea hipótesis
- HypothesisEngine: coordinador con persistencia
"""
import time
import json
import hashlib
import re
from pathlib import Path
from collections import defaultdict


class Evidence:
    """Una pieza de evidencia que soporta o contradice una hipótesis."""

    def __init__(self, text: str, supports: bool = True,
                 weight: float = 1.0, source: str = ""):
        self.text = text
        self.supports = supports
        self.weight = max(0.0, min(2.0, weight))
        self.source = source
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "supports": self.supports,
            "weight": round(self.weight, 4),
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Evidence":
        e = cls(
            text=data.get("text", ""),
            supports=data.get("supports", True),
            weight=data.get("weight", 1.0),
            source=data.get("source", ""),
        )
        e.timestamp = data.get("timestamp", time.time())
        return e


class Hypothesis:
    """Una hipótesis formulada por Genesis."""

    def __init__(self, statement: str, domain: str = "general",
                 context: str = ""):
        self.hyp_id = hashlib.md5(
            f"{statement}{time.time()}".encode()).hexdigest()[:10]
        self.statement = statement
        self.domain = domain
        self.context = context
        self.evidence_for = []      # Evidence que soporta
        self.evidence_against = []  # Evidence que contradice
        self.status = "active"      # active, confirmed, refuted, suspended
        self.confidence = 0.5       # 0.0 - 1.0
        self.created_at = time.time()
        self.updated_at = time.time()
        self.evaluations = 0

    def add_evidence(self, evidence: Evidence):
        """Agrega evidencia y recalcula confianza."""
        if evidence.supports:
            self.evidence_for.append(evidence)
        else:
            self.evidence_against.append(evidence)
        self._recalculate_confidence()
        self.updated_at = time.time()

    def _recalculate_confidence(self):
        """Recalcula la confianza basado en evidencia."""
        support_weight = sum(e.weight for e in self.evidence_for)
        against_weight = sum(e.weight for e in self.evidence_against)
        total = support_weight + against_weight
        if total == 0:
            self.confidence = 0.5
            return
        self.confidence = support_weight / total
        # Auto-update status
        if self.confidence > 0.85 and len(self.evidence_for) >= 3:
            self.status = "confirmed"
        elif self.confidence < 0.15 and len(self.evidence_against) >= 3:
            self.status = "refuted"

    @property
    def plausibility(self) -> float:
        """Score de plausibilidad combinando confianza y cantidad de evidencia."""
        evidence_count = len(self.evidence_for) + len(self.evidence_against)
        if evidence_count == 0:
            return 0.5
        # Más evidencia = más certeza sobre la dirección
        certainty = min(1.0, evidence_count / 10.0)
        return self.confidence * certainty + 0.5 * (1 - certainty)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    def to_dict(self) -> dict:
        return {
            "hyp_id": self.hyp_id,
            "statement": self.statement,
            "domain": self.domain,
            "context": self.context,
            "evidence_for": [e.to_dict() for e in self.evidence_for],
            "evidence_against": [e.to_dict() for e in self.evidence_against],
            "status": self.status,
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "evaluations": self.evaluations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Hypothesis":
        h = cls(
            statement=data.get("statement", ""),
            domain=data.get("domain", "general"),
            context=data.get("context", ""),
        )
        h.hyp_id = data.get("hyp_id", h.hyp_id)
        h.status = data.get("status", "active")
        h.confidence = data.get("confidence", 0.5)
        h.created_at = data.get("created_at", time.time())
        h.updated_at = data.get("updated_at", time.time())
        h.evaluations = data.get("evaluations", 0)
        h.evidence_for = [Evidence.from_dict(e) for e in data.get("evidence_for", [])]
        h.evidence_against = [Evidence.from_dict(e) for e in data.get("evidence_against", [])]
        return h


class HypothesisGenerator:
    """Genera hipótesis desde patrones de texto."""

    # Patrones que sugieren hipótesis
    HYPOTHESIS_PATTERNS = [
        (r"(?:quizas?|tal vez|puede que|probablemente|posiblemente)\s+(.+)",
         "speculative"),
        (r"(?:creo que|pienso que|me parece que|supongo que)\s+(.+)",
         "belief"),
        (r"(?:si|cuando)\s+(.+?)\s+(?:entonces|,)\s+(.+)",
         "conditional"),
        (r"(?:porque|debido a|ya que)\s+(.+?)\s*[,\.]\s*(.+)",
         "causal_hyp"),
        (r"(?:maybe|perhaps|probably|possibly)\s+(.+)",
         "speculative_en"),
    ]

    def extract_hypotheses(self, text: str) -> list:
        """Extrae posibles hipótesis del texto."""
        hypotheses = []
        text_lower = text.lower().strip()

        for pattern, hyp_type in self.HYPOTHESIS_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                if hyp_type == "conditional":
                    statement = f"Si {match.group(1)}, entonces {match.group(2)}"
                elif hyp_type == "causal_hyp":
                    statement = f"{match.group(2)} se debe a {match.group(1)}"
                else:
                    statement = match.group(1).strip().rstrip(".")
                if len(statement) > 10:
                    hypotheses.append({
                        "statement": statement,
                        "type": hyp_type,
                        "source_text": text[:200],
                    })
        return hypotheses

    def generate_from_observations(self, observations: list) -> list:
        """Genera hipótesis desde una lista de observaciones."""
        if len(observations) < 2:
            return []
        hypotheses = []
        # Buscar patrones repetidos
        word_freq = defaultdict(int)
        for obs in observations:
            for word in obs.lower().split():
                if len(word) > 4:
                    word_freq[word] += 1
        common = [w for w, c in word_freq.items() if c >= 2]
        if common:
            theme = common[0]
            hypotheses.append({
                "statement": f"el tema recurrente '{theme}' indica un patron de interes",
                "type": "pattern",
                "source_text": f"Basado en {len(observations)} observaciones",
            })
        return hypotheses


class HypothesisEvaluator:
    """Evalúa y rankea hipótesis."""

    def evaluate(self, hypothesis: Hypothesis, new_text: str) -> dict:
        """Evalúa una hipótesis contra nuevo texto."""
        hypothesis.evaluations += 1
        result = {
            "hyp_id": hypothesis.hyp_id,
            "supports": False,
            "contradicts": False,
            "relevance": 0.0,
        }

        # Verificar relevancia por overlap de palabras
        hyp_words = set(hypothesis.statement.lower().split())
        text_words = set(new_text.lower().split())
        if not hyp_words:
            return result
        overlap = len(hyp_words & text_words)
        result["relevance"] = overlap / len(hyp_words) if hyp_words else 0.0

        if result["relevance"] < 0.2:
            return result

        # Detectar soporte o contradicción
        negation_words = {"no", "nunca", "jamas", "tampoco", "sin",
                          "not", "never", "without", "isn't", "doesn't"}
        has_negation = bool(negation_words & text_words)

        if has_negation:
            result["contradicts"] = True
        else:
            result["supports"] = True

        return result

    def rank_hypotheses(self, hypotheses: list) -> list:
        """Rankea hipótesis por plausibilidad."""
        active = [h for h in hypotheses if h.status == "active"]
        return sorted(active, key=lambda h: h.plausibility, reverse=True)


class HypothesisEngine:
    """
    Coordinador del motor de hipótesis.
    Genera, evalúa y refina hipótesis iterativamente.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/hypothesis")
        self.data_file = self.base_dir / "hypothesis_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.hypotheses = {}    # hyp_id -> Hypothesis
        self.generator = HypothesisGenerator()
        self.evaluator = HypothesisEvaluator()
        self.max_hypotheses = 100
        self.total_generated = 0
        self.total_confirmed = 0
        self.total_refuted = 0
        self.enabled = True

        self._load()

    def formulate(self, text: str, domain: str = "general") -> list:
        """Formula nuevas hipótesis desde texto."""
        if not self.enabled or not text:
            return []

        raw = self.generator.extract_hypotheses(text)
        created = []

        for item in raw:
            hyp = Hypothesis(
                statement=item["statement"],
                domain=domain,
                context=item.get("source_text", ""),
            )
            self.hypotheses[hyp.hyp_id] = hyp
            self.total_generated += 1
            created.append(hyp)

        self._evict()
        return created

    def evaluate_against(self, text: str):
        """Evalúa todas las hipótesis activas contra nuevo texto."""
        if not self.enabled or not text:
            return

        active = [h for h in self.hypotheses.values() if h.status == "active"]
        for hyp in active:
            result = self.evaluator.evaluate(hyp, text)
            if result["supports"] and result["relevance"] > 0.3:
                hyp.add_evidence(Evidence(
                    text=text[:200],
                    supports=True,
                    weight=result["relevance"],
                    source="conversation",
                ))
            elif result["contradicts"] and result["relevance"] > 0.3:
                hyp.add_evidence(Evidence(
                    text=text[:200],
                    supports=False,
                    weight=result["relevance"],
                    source="conversation",
                ))
            # Actualizar contadores globales
            if hyp.status == "confirmed":
                self.total_confirmed += 1
            elif hyp.status == "refuted":
                self.total_refuted += 1

    def get_active_hypotheses(self) -> list:
        """Retorna hipótesis activas rankeadas."""
        return self.evaluator.rank_hypotheses(list(self.hypotheses.values()))

    def get_hypothesis(self, hyp_id: str) -> Hypothesis:
        """Busca una hipótesis por ID."""
        return self.hypotheses.get(hyp_id)

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de hipótesis para prompt."""
        if not self.enabled:
            return ""
        ranked = self.get_active_hypotheses()[:3]
        if not ranked:
            return ""

        lines = ["[HIPOTESIS ACTIVAS]"]
        for h in ranked:
            ev = len(h.evidence_for) + len(h.evidence_against)
            lines.append(f"  H: {h.statement} (conf={h.confidence:.0%}, ev={ev})")
        return "\n".join(lines)[:max_chars]

    def _evict(self):
        """Elimina hipótesis antiguas refutadas o de baja plausibilidad."""
        if len(self.hypotheses) <= self.max_hypotheses:
            return
        # Ordenar por prioridad: activas > confirmadas > suspended > refutadas
        priority = {"confirmed": 4, "active": 3, "suspended": 2, "refuted": 1}
        sorted_hyps = sorted(
            self.hypotheses.values(),
            key=lambda h: (priority.get(h.status, 0), h.updated_at),
            reverse=True,
        )
        keep = sorted_hyps[:self.max_hypotheses]
        self.hypotheses = {h.hyp_id: h for h in keep}

    def get_stats(self) -> dict:
        active = len([h for h in self.hypotheses.values() if h.status == "active"])
        confirmed = len([h for h in self.hypotheses.values() if h.status == "confirmed"])
        refuted = len([h for h in self.hypotheses.values() if h.status == "refuted"])
        return {
            "total_hypotheses": len(self.hypotheses),
            "active": active,
            "confirmed": confirmed,
            "refuted": refuted,
            "total_generated": self.total_generated,
            "total_confirmed": self.total_confirmed,
            "total_refuted": self.total_refuted,
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Hipotesis: {stats['total_hypotheses']} "
                f"(activas={stats['active']}, confirmadas={stats['confirmed']}, "
                f"refutadas={stats['refuted']}) | "
                f"Generadas: {stats['total_generated']}")

    def generate_report(self) -> str:
        lines = ["=== HYPOTHESIS ENGINE REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total hipotesis: {stats['total_hypotheses']}")
        lines.append(f"Activas: {stats['active']}")
        lines.append(f"Confirmadas: {stats['confirmed']}")
        lines.append(f"Refutadas: {stats['refuted']}")
        lines.append(f"Total generadas: {stats['total_generated']}")

        ranked = self.get_active_hypotheses()[:10]
        if ranked:
            lines.append(f"\nTop hipotesis activas:")
            for h in ranked:
                ev_for = len(h.evidence_for)
                ev_against = len(h.evidence_against)
                bar = "█" * int(h.plausibility * 20) + "░" * (20 - int(h.plausibility * 20))
                lines.append(f"  [{bar}] {h.plausibility:.2f} — {h.statement}")
                lines.append(f"    Evidencia: +{ev_for} -{ev_against} | "
                             f"Conf: {h.confidence:.0%} | Evals: {h.evaluations}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_generated": self.total_generated,
            "total_confirmed": self.total_confirmed,
            "total_refuted": self.total_refuted,
            "hypotheses": {k: v.to_dict() for k, v in self.hypotheses.items()},
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
            self.total_generated = data.get("total_generated", 0)
            self.total_confirmed = data.get("total_confirmed", 0)
            self.total_refuted = data.get("total_refuted", 0)
            for hyp_id, hd in data.get("hypotheses", {}).items():
                self.hypotheses[hyp_id] = Hypothesis.from_dict(hd)
        except Exception:
            pass

    def clear(self):
        self.hypotheses = {}
        self.total_generated = 0
        self.total_confirmed = 0
        self.total_refuted = 0
