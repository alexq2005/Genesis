"""
GENESIS — Explanation Engine (v2.8)

Motor de explicaciones multi-nivel. Genesis genera explicaciones
adaptadas al nivel del usuario (simple, técnico, analógico),
evalúa su calidad y mantiene un banco de explicaciones reutilizables.

Componentes:
- Explanation: una explicación con nivel, calidad y metadata
- ExplanationTemplate: plantilla para generar explicaciones
- QualityScorer: evalúa calidad de explicaciones
- ExplanationEngine: coordinador con banco de explicaciones
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class Explanation:
    """Una explicación generada por Genesis."""

    LEVELS = ("simple", "technical", "analogical", "step_by_step")

    def __init__(self, topic: str, content: str, level: str = "simple",
                 domain: str = "general"):
        self.exp_id = hashlib.md5(
            f"{topic}{level}{time.time()}".encode()).hexdigest()[:10]
        self.topic = topic
        self.content = content
        self.level = level if level in self.LEVELS else "simple"
        self.domain = domain
        self.quality_score = 0.0
        self.uses = 0
        self.positive_feedback = 0
        self.negative_feedback = 0
        self.created_at = time.time()
        self.updated_at = time.time()

    @property
    def effectiveness(self) -> float:
        """Ratio de feedback positivo."""
        total = self.positive_feedback + self.negative_feedback
        if total == 0:
            return 0.5
        return self.positive_feedback / total

    @property
    def relevance_score(self) -> float:
        """Score combinado de calidad y efectividad."""
        return (self.quality_score * 0.6 + self.effectiveness * 0.4)

    def record_feedback(self, positive: bool):
        """Registra feedback del usuario."""
        if positive:
            self.positive_feedback += 1
        else:
            self.negative_feedback += 1
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "exp_id": self.exp_id,
            "topic": self.topic,
            "content": self.content,
            "level": self.level,
            "domain": self.domain,
            "quality_score": round(self.quality_score, 4),
            "uses": self.uses,
            "positive_feedback": self.positive_feedback,
            "negative_feedback": self.negative_feedback,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Explanation":
        e = cls(
            topic=data.get("topic", ""),
            content=data.get("content", ""),
            level=data.get("level", "simple"),
            domain=data.get("domain", "general"),
        )
        e.exp_id = data.get("exp_id", e.exp_id)
        e.quality_score = data.get("quality_score", 0.0)
        e.uses = data.get("uses", 0)
        e.positive_feedback = data.get("positive_feedback", 0)
        e.negative_feedback = data.get("negative_feedback", 0)
        e.created_at = data.get("created_at", time.time())
        e.updated_at = data.get("updated_at", time.time())
        return e


class ExplanationTemplate:
    """Plantilla para generar directivas de explicación."""

    TEMPLATES = {
        "simple": (
            "Explica '{topic}' de forma simple y accesible. "
            "Usa analogías cotidianas. Sin jerga técnica. "
            "Máximo 3 oraciones."
        ),
        "technical": (
            "Explica '{topic}' con detalle técnico. "
            "Incluye terminología correcta, mecanismos internos, "
            "y referencias a conceptos avanzados."
        ),
        "analogical": (
            "Explica '{topic}' usando una analogía creativa. "
            "Compara con algo familiar del mundo cotidiano. "
            "Haz que el concepto sea intuitivo."
        ),
        "step_by_step": (
            "Explica '{topic}' paso a paso. "
            "Numera cada paso. Sé claro y secuencial. "
            "Incluye ejemplos en cada paso."
        ),
    }

    def get_directive(self, topic: str, level: str) -> str:
        """Genera directiva de explicación para prompt."""
        template = self.TEMPLATES.get(level, self.TEMPLATES["simple"])
        return template.format(topic=topic)

    def get_all_levels(self, topic: str) -> dict:
        """Genera directivas para todos los niveles."""
        return {level: self.get_directive(topic, level)
                for level in self.TEMPLATES}


class QualityScorer:
    """Evalúa la calidad de una explicación."""

    def score(self, explanation: Explanation) -> float:
        """Calcula un score de calidad (0.0 - 1.0)."""
        content = explanation.content
        score = 0.0

        # Longitud apropiada (ni muy corta ni muy larga)
        length = len(content)
        if 50 <= length <= 500:
            score += 0.25
        elif 20 <= length < 50 or 500 < length <= 1000:
            score += 0.15
        elif length > 1000:
            score += 0.05

        # Tiene estructura (puntos, comas, oraciones múltiples)
        sentences = content.count(".") + content.count("!") + content.count("?")
        if sentences >= 2:
            score += 0.2
        elif sentences >= 1:
            score += 0.1

        # Nivel adecuado
        if explanation.level == "simple":
            # Penalizar jerga técnica
            technical_words = {"implementar", "algoritmo", "instanciar",
                              "refactorizar", "overhead", "throughput"}
            has_jargon = any(w in content.lower() for w in technical_words)
            score += 0.25 if not has_jargon else 0.1
        elif explanation.level == "technical":
            # Recompensar detalle técnico
            has_detail = len(content.split()) > 30
            score += 0.25 if has_detail else 0.1
        elif explanation.level == "analogical":
            # Recompensar analogías
            analogy_markers = ["como", "similar a", "es como",
                              "imagina", "piensa en", "like"]
            has_analogy = any(m in content.lower() for m in analogy_markers)
            score += 0.25 if has_analogy else 0.1
        elif explanation.level == "step_by_step":
            # Recompensar numeración
            has_steps = any(f"{i}." in content or f"{i})" in content
                           for i in range(1, 10))
            score += 0.25 if has_steps else 0.1

        # Feedback histórico
        score += explanation.effectiveness * 0.3

        return min(1.0, score)


class ExplanationEngine:
    """
    Coordinador del motor de explicaciones.
    Genera, evalúa y almacena explicaciones multi-nivel.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/explanations")
        self.data_file = self.base_dir / "explanation_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.explanations = {}      # exp_id -> Explanation
        self.topic_index = defaultdict(list)  # topic -> [exp_id, ...]
        self.templates = ExplanationTemplate()
        self.scorer = QualityScorer()
        self.max_explanations = 200
        self.total_generated = 0
        self.enabled = True

        self._load()

    def store(self, topic: str, content: str, level: str = "simple",
              domain: str = "general") -> Explanation:
        """Almacena una nueva explicación."""
        if not self.enabled or not topic or not content:
            return None

        exp = Explanation(topic=topic, content=content,
                         level=level, domain=domain)
        exp.quality_score = self.scorer.score(exp)
        self.explanations[exp.exp_id] = exp
        self.topic_index[topic.lower()].append(exp.exp_id)
        self.total_generated += 1
        self._evict()
        return exp

    def find(self, topic: str, level: str = None) -> list:
        """Busca explicaciones por tópico y opcionalmente nivel."""
        topic_lower = topic.lower()
        results = []

        # Búsqueda exacta
        for exp_id in self.topic_index.get(topic_lower, []):
            exp = self.explanations.get(exp_id)
            if exp and (level is None or exp.level == level):
                results.append(exp)

        # Búsqueda parcial si no hay exacta
        if not results:
            for key, exp_ids in self.topic_index.items():
                if topic_lower in key or key in topic_lower:
                    for exp_id in exp_ids:
                        exp = self.explanations.get(exp_id)
                        if exp and (level is None or exp.level == level):
                            results.append(exp)

        # Rankear por relevance_score
        results.sort(key=lambda e: e.relevance_score, reverse=True)
        return results

    def get_best(self, topic: str, level: str = None) -> Explanation:
        """Obtiene la mejor explicación para un tópico."""
        results = self.find(topic, level)
        if results:
            results[0].uses += 1
            return results[0]
        return None

    def get_directive(self, topic: str, level: str = "simple") -> str:
        """Genera directiva de explicación para el prompt."""
        return self.templates.get_directive(topic, level)

    def record_feedback(self, exp_id: str, positive: bool):
        """Registra feedback para una explicación."""
        exp = self.explanations.get(exp_id)
        if exp:
            exp.record_feedback(positive)
            exp.quality_score = self.scorer.score(exp)

    def detect_explanation_need(self, text: str) -> dict:
        """Detecta si el texto necesita una explicación y a qué nivel."""
        text_lower = text.lower()
        result = {"needs_explanation": False, "topic": "", "level": "simple"}

        # Patrones de solicitud de explicación
        patterns = {
            "simple": ["que es", "que significa", "explica", "explain",
                      "para dummies", "eli5", "sencillo"],
            "technical": ["como funciona internamente", "implementacion",
                         "arquitectura de", "detalle tecnico"],
            "analogical": ["analogia", "comparacion", "es como",
                          "a que se parece"],
            "step_by_step": ["paso a paso", "como hago", "tutorial",
                            "pasos para", "guia"],
        }

        for level, keywords in patterns.items():
            for kw in keywords:
                if kw in text_lower:
                    result["needs_explanation"] = True
                    result["level"] = level
                    # Extraer tópico (texto después del keyword)
                    idx = text_lower.index(kw) + len(kw)
                    topic = text[idx:].strip().strip("?").strip()
                    if len(topic) > 3:
                        result["topic"] = topic[:100]
                    break
            if result["needs_explanation"]:
                break

        return result

    def get_context_for_prompt(self, user_input: str, max_chars: int = 300) -> str:
        """Genera contexto de explicación para prompt."""
        if not self.enabled:
            return ""

        detection = self.detect_explanation_need(user_input)
        if not detection["needs_explanation"]:
            return ""

        topic = detection["topic"]
        level = detection["level"]

        # Buscar explicación existente
        existing = self.get_best(topic, level)
        if existing:
            return (f"[EXPLICACION PREVIA RELEVANTE]\n"
                    f"Nivel: {level} | Calidad: {existing.quality_score:.0%}\n"
                    f"{existing.content[:200]}")[:max_chars]

        # Generar directiva
        directive = self.get_directive(topic, level)
        return f"[ESTILO DE EXPLICACION] {directive}"[:max_chars]

    def _evict(self):
        """Elimina explicaciones de menor calidad."""
        if len(self.explanations) <= self.max_explanations:
            return
        sorted_exps = sorted(
            self.explanations.values(),
            key=lambda e: e.relevance_score,
            reverse=True,
        )
        keep = sorted_exps[:self.max_explanations]
        self.explanations = {e.exp_id: e for e in keep}
        # Reconstruir topic_index
        self.topic_index = defaultdict(list)
        for exp in keep:
            self.topic_index[exp.topic.lower()].append(exp.exp_id)

    def get_stats(self) -> dict:
        levels = defaultdict(int)
        for exp in self.explanations.values():
            levels[exp.level] += 1
        avg_quality = 0.0
        if self.explanations:
            avg_quality = sum(e.quality_score for e in self.explanations.values()) / len(self.explanations)
        return {
            "total_explanations": len(self.explanations),
            "total_generated": self.total_generated,
            "topics": len(self.topic_index),
            "levels": dict(levels),
            "avg_quality": round(avg_quality, 3),
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Explicaciones: {stats['total_explanations']} | "
                f"Topics: {stats['topics']} | "
                f"Generadas: {stats['total_generated']} | "
                f"Calidad avg: {stats['avg_quality']:.0%}")

    def generate_report(self) -> str:
        lines = ["=== EXPLANATION ENGINE REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total explicaciones: {stats['total_explanations']}")
        lines.append(f"Total generadas: {stats['total_generated']}")
        lines.append(f"Topics cubiertos: {stats['topics']}")
        lines.append(f"Calidad promedio: {stats['avg_quality']:.1%}")

        if stats["levels"]:
            lines.append(f"\nPor nivel:")
            for level, count in sorted(stats["levels"].items()):
                lines.append(f"  {level}: {count}")

        # Top explicaciones
        top = sorted(self.explanations.values(),
                     key=lambda e: e.relevance_score, reverse=True)[:5]
        if top:
            lines.append(f"\nTop explicaciones:")
            for exp in top:
                lines.append(f"  [{exp.level}] {exp.topic}: "
                             f"quality={exp.quality_score:.2f} "
                             f"uses={exp.uses} eff={exp.effectiveness:.0%}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_generated": self.total_generated,
            "explanations": {k: v.to_dict() for k, v in self.explanations.items()},
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
            for exp_id, ed in data.get("explanations", {}).items():
                exp = Explanation.from_dict(ed)
                self.explanations[exp_id] = exp
                self.topic_index[exp.topic.lower()].append(exp_id)
        except Exception:
            pass

    def clear(self):
        self.explanations = {}
        self.topic_index = defaultdict(list)
        self.total_generated = 0
