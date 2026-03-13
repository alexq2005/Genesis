"""
GENESIS — Learning Optimizer (v2.9)

Optimizador de aprendizaje: rastrea eficiencia de aprendizaje por dominio,
detecta knowledge gaps, ajusta learning rates con decaimiento, y sugiere
estrategias de aprendizaje óptimas.

Componentes:
- LearningRate: tasa de aprendizaje por dominio con decaimiento
- KnowledgeGap: brecha de conocimiento detectada
- LearningStrategy: estrategias de aprendizaje disponibles
- LearningOptimizer: coordinador con persistencia
"""
import time
import json
import math
from pathlib import Path
from collections import defaultdict


class LearningRate:
    """Tasa de aprendizaje por dominio con decaimiento exponencial."""

    def __init__(self, domain: str, initial_rate: float = 1.0,
                 decay_factor: float = 0.95):
        self.domain = domain
        self.initial_rate = initial_rate
        self.decay_factor = decay_factor
        self.current_rate = initial_rate
        self.interactions = 0
        self.successes = 0        # Veces que se usó bien el conocimiento
        self.failures = 0         # Veces que falló (gaps detectados)
        self.last_update = time.time()

    def record_success(self):
        """Registra uso exitoso de conocimiento en este dominio."""
        self.successes += 1
        self.interactions += 1
        self._update_rate()

    def record_failure(self):
        """Registra fallo o gap en este dominio."""
        self.failures += 1
        self.interactions += 1
        # Boost rate en caso de fallo (necesita aprender más)
        self.current_rate = min(1.0, self.current_rate * 1.2)
        self.last_update = time.time()

    def _update_rate(self):
        """Decaimiento exponencial — aprende menos a medida que domina."""
        self.current_rate = self.initial_rate * (
            self.decay_factor ** self.successes
        )
        self.current_rate = max(0.05, self.current_rate)  # Mínimo 5%
        self.last_update = time.time()

    @property
    def mastery(self) -> float:
        """Nivel de maestría (0.0 - 1.0)."""
        if self.interactions == 0:
            return 0.0
        success_ratio = self.successes / self.interactions
        # Mastery = ratio de éxito ponderado por experiencia
        exp_factor = min(1.0, self.interactions / 20.0)
        return success_ratio * exp_factor

    @property
    def efficiency(self) -> float:
        """Eficiencia de aprendizaje = mastery / log(interactions + 1)."""
        if self.interactions == 0:
            return 0.0
        return self.mastery / math.log(self.interactions + 2)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "current_rate": round(self.current_rate, 4),
            "interactions": self.interactions,
            "successes": self.successes,
            "failures": self.failures,
            "mastery": round(self.mastery, 4),
            "efficiency": round(self.efficiency, 4),
            "last_update": self.last_update,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningRate":
        lr = cls(
            domain=data.get("domain", "general"),
            initial_rate=1.0,
            decay_factor=0.95,
        )
        lr.current_rate = data.get("current_rate", 1.0)
        lr.interactions = data.get("interactions", 0)
        lr.successes = data.get("successes", 0)
        lr.failures = data.get("failures", 0)
        lr.last_update = data.get("last_update", time.time())
        return lr


class KnowledgeGap:
    """Una brecha de conocimiento detectada."""

    def __init__(self, domain: str, description: str, severity: float = 0.5):
        self.domain = domain
        self.description = description[:200]
        self.severity = max(0.0, min(1.0, severity))  # 0.0 - 1.0
        self.occurrences = 1
        self.detected_at = time.time()
        self.resolved = False
        self.resolved_at = None

    def record_occurrence(self):
        """Registra otra ocurrencia del mismo gap."""
        self.occurrences += 1
        self.severity = min(1.0, self.severity + 0.1)

    def resolve(self):
        """Marca el gap como resuelto."""
        self.resolved = True
        self.resolved_at = time.time()

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "description": self.description,
            "severity": round(self.severity, 3),
            "occurrences": self.occurrences,
            "detected_at": self.detected_at,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGap":
        gap = cls(
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
            severity=data.get("severity", 0.5),
        )
        gap.occurrences = data.get("occurrences", 1)
        gap.detected_at = data.get("detected_at", time.time())
        gap.resolved = data.get("resolved", False)
        gap.resolved_at = data.get("resolved_at", None)
        return gap


class LearningStrategy:
    """Estrategias de aprendizaje disponibles."""

    STRATEGIES = {
        "spaced_repetition": {
            "name": "Repetición Espaciada",
            "directive": "Refuerza conocimiento previo con intervalos crecientes. "
                        "Referencia conceptos discutidos antes para consolidar.",
            "best_for": ["memoria", "conceptos", "vocabulario"],
        },
        "active_recall": {
            "name": "Recuerdo Activo",
            "directive": "Haz preguntas al usuario sobre lo aprendido antes de "
                        "agregar nueva información. Valida comprensión primero.",
            "best_for": ["aprendizaje", "estudio", "tutorial"],
        },
        "interleaving": {
            "name": "Intercalación",
            "directive": "Alterna entre dominios relacionados para fortalecer "
                        "conexiones. Mezcla ejemplos de diferentes contextos.",
            "best_for": ["creatividad", "conexiones", "multi-dominio"],
        },
        "elaboration": {
            "name": "Elaboración",
            "directive": "Pide al usuario que explique en sus palabras. "
                        "Profundiza con 'por qué' y 'cómo se conecta con...'",
            "best_for": ["comprension", "analisis", "profundidad"],
        },
        "concrete_examples": {
            "name": "Ejemplos Concretos",
            "directive": "Usa ejemplos específicos y casos reales. "
                        "Conecta abstracciones con situaciones concretas.",
            "best_for": ["codigo", "implementacion", "practica"],
        },
    }

    @classmethod
    def select_for_domain(cls, domain: str, mastery: float) -> str:
        """Selecciona la mejor estrategia según dominio y maestría."""
        if mastery > 0.7:
            return "interleaving"  # Alto dominio → mezclar
        elif mastery > 0.4:
            return "active_recall"  # Medio → validar comprensión
        elif mastery > 0.2:
            return "elaboration"  # Bajo-medio → profundizar
        else:
            return "concrete_examples"  # Novato → ejemplos concretos

    @classmethod
    def get_directive(cls, strategy_key: str) -> str:
        """Obtiene la directiva de una estrategia."""
        config = cls.STRATEGIES.get(strategy_key, {})
        return config.get("directive", "")


class LearningOptimizer:
    """
    Coordinador de optimización de aprendizaje.
    Rastrea learning rates, detecta gaps, y optimiza estrategias.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/learning_opt")
        self.data_file = self.base_dir / "learning_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.learning_rates = {}      # domain -> LearningRate
        self.knowledge_gaps = []      # lista de KnowledgeGap
        self.max_gaps = 50
        self.domain_interactions = defaultdict(int)  # domain -> count
        self.total_optimizations = 0
        self.current_strategy = "concrete_examples"
        self.enabled = True

        self._load()

    def record_learning(self, domain: str, success: bool = True):
        """Registra un evento de aprendizaje."""
        if not self.enabled:
            return

        # Crear learning rate si no existe
        if domain not in self.learning_rates:
            self.learning_rates[domain] = LearningRate(domain)

        lr = self.learning_rates[domain]
        if success:
            lr.record_success()
        else:
            lr.record_failure()

        self.domain_interactions[domain] += 1
        self.total_optimizations += 1

        # Actualizar estrategia
        self.current_strategy = LearningStrategy.select_for_domain(
            domain, lr.mastery
        )

    def detect_gap(self, domain: str, description: str,
                   severity: float = 0.5):
        """Detecta y registra un knowledge gap."""
        if not self.enabled:
            return

        # Buscar gap existente por dominio similar
        for gap in self.knowledge_gaps:
            if gap.domain == domain and not gap.resolved:
                # Agregar ocurrencia al gap existente
                gap.record_occurrence()
                return

        # Nuevo gap
        gap = KnowledgeGap(domain, description, severity)
        self.knowledge_gaps.append(gap)
        if len(self.knowledge_gaps) > self.max_gaps:
            # Evicción: remover gaps resueltos primero, luego los menos severos
            resolved = [g for g in self.knowledge_gaps if g.resolved]
            if resolved:
                self.knowledge_gaps.remove(
                    min(resolved, key=lambda g: g.severity)
                )
            else:
                unresolved = sorted(self.knowledge_gaps,
                                    key=lambda g: g.severity)
                self.knowledge_gaps.remove(unresolved[0])

        # Registrar como fallo en learning rate
        self.record_learning(domain, success=False)

    def resolve_gap(self, domain: str):
        """Marca gaps de un dominio como resueltos."""
        for gap in self.knowledge_gaps:
            if gap.domain == domain and not gap.resolved:
                gap.resolve()

    def get_active_gaps(self) -> list:
        """Retorna gaps activos (no resueltos) ordenados por severidad."""
        active = [g for g in self.knowledge_gaps if not g.resolved]
        active.sort(key=lambda g: g.severity, reverse=True)
        return active

    def get_domain_mastery(self, domain: str) -> float:
        """Obtiene el nivel de maestría en un dominio."""
        lr = self.learning_rates.get(domain)
        if not lr:
            return 0.0
        return lr.mastery

    def get_top_domains(self, n: int = 5) -> list:
        """Top N dominios por maestría."""
        sorted_lr = sorted(
            self.learning_rates.values(),
            key=lambda lr: lr.mastery,
            reverse=True,
        )
        return [lr.to_dict() for lr in sorted_lr[:n]]

    def get_weakest_domains(self, n: int = 5) -> list:
        """N dominios más débiles (donde más se necesita aprender)."""
        active = [lr for lr in self.learning_rates.values()
                  if lr.interactions > 0]
        sorted_lr = sorted(active, key=lambda lr: lr.mastery)
        return [lr.to_dict() for lr in sorted_lr[:n]]

    def get_recommended_strategy(self, domain: str = "general") -> dict:
        """Recomienda estrategia de aprendizaje para un dominio."""
        mastery = self.get_domain_mastery(domain)
        key = LearningStrategy.select_for_domain(domain, mastery)
        config = LearningStrategy.STRATEGIES.get(key, {})
        return {
            "strategy": key,
            "name": config.get("name", key),
            "directive": config.get("directive", ""),
            "domain_mastery": mastery,
        }

    def observe_interaction(self, text: str, domain: str = "general"):
        """Observa una interacción y actualiza learning rates."""
        if not self.enabled or not text:
            return

        text_lower = text.lower()

        # Señales de gap (el usuario no entiende)
        gap_signals = [
            "no entiendo", "no comprendo", "explica mejor",
            "que significa", "como funciona", "no se",
            "i don't understand", "what does", "how does",
        ]
        is_gap = any(signal in text_lower for signal in gap_signals)

        if is_gap:
            words = text_lower.split()
            desc = " ".join(words[:10]) if len(words) > 3 else text_lower
            self.detect_gap(domain, desc, severity=0.6)
        else:
            # Señales de éxito (el usuario confirma entendimiento)
            success_signals = [
                "entiendo", "claro", "perfecto", "gracias",
                "ahora si", "ya entendi", "got it", "makes sense",
                "funciona", "excelente",
            ]
            is_success = any(signal in text_lower for signal in success_signals)
            if is_success:
                self.record_learning(domain, success=True)
                self.resolve_gap(domain)

        # Registrar interacción general
        self.domain_interactions[domain] += 1

    def get_context_for_prompt(self, domain: str = "general",
                               max_chars: int = 300) -> str:
        """Genera contexto de aprendizaje para prompt."""
        if not self.enabled:
            return ""

        parts = []

        # Mostrar gaps activos relevantes
        active_gaps = self.get_active_gaps()[:2]
        if active_gaps:
            gap_info = ", ".join(g.domain for g in active_gaps)
            parts.append(f"Gaps detectados: {gap_info}")

        # Mostrar estrategia recomendada
        rec = self.get_recommended_strategy(domain)
        if rec["directive"]:
            parts.append(f"Estrategia: {rec['name']}")

        if not parts:
            return ""

        result = "[LEARNING OPT] " + " | ".join(parts)
        return result[:max_chars]

    def get_stats(self) -> dict:
        active_gaps = len(self.get_active_gaps())
        resolved_gaps = len([g for g in self.knowledge_gaps if g.resolved])
        return {
            "total_domains": len(self.learning_rates),
            "total_optimizations": self.total_optimizations,
            "active_gaps": active_gaps,
            "resolved_gaps": resolved_gaps,
            "current_strategy": self.current_strategy,
            "top_domains": self.get_top_domains(3),
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Dominios: {stats['total_domains']} | "
                f"Gaps: {stats['active_gaps']} activos, "
                f"{stats['resolved_gaps']} resueltos | "
                f"Estrategia: {stats['current_strategy']}")

    def generate_report(self) -> str:
        lines = ["=== LEARNING OPTIMIZER REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total dominios: {stats['total_domains']}")
        lines.append(f"Total optimizaciones: {stats['total_optimizations']}")
        lines.append(f"Estrategia actual: {stats['current_strategy']}")

        # Top dominios por maestría
        top = self.get_top_domains(5)
        if top:
            lines.append(f"\nTop dominios:")
            for d in top:
                bar = "█" * int(d["mastery"] * 20) + "░" * (20 - int(d["mastery"] * 20))
                lines.append(f"  [{bar}] {d['domain']} "
                             f"mastery={d['mastery']:.0%} "
                             f"rate={d['current_rate']:.2f} "
                             f"({d['interactions']} interacciones)")

        # Gaps activos
        active_gaps = self.get_active_gaps()
        if active_gaps:
            lines.append(f"\nKnowledge gaps activos:")
            for g in active_gaps[:5]:
                lines.append(f"  [{g.severity:.0%}] {g.domain}: "
                             f"{g.description} (×{g.occurrences})")

        # Dominios débiles
        weak = self.get_weakest_domains(3)
        if weak:
            lines.append(f"\nDominios mas debiles:")
            for d in weak:
                lines.append(f"  {d['domain']}: mastery={d['mastery']:.0%} "
                             f"failures={d['failures']}")

        return "\n".join(lines)

    def save(self):
        data = {
            "learning_rates": {k: v.to_dict()
                               for k, v in self.learning_rates.items()},
            "knowledge_gaps": [g.to_dict() for g in self.knowledge_gaps],
            "domain_interactions": dict(self.domain_interactions),
            "total_optimizations": self.total_optimizations,
            "current_strategy": self.current_strategy,
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
            for k, v in data.get("learning_rates", {}).items():
                self.learning_rates[k] = LearningRate.from_dict(v)
            for gd in data.get("knowledge_gaps", []):
                self.knowledge_gaps.append(KnowledgeGap.from_dict(gd))
            for k, v in data.get("domain_interactions", {}).items():
                self.domain_interactions[k] = v
            self.total_optimizations = data.get("total_optimizations", 0)
            self.current_strategy = data.get("current_strategy",
                                             "concrete_examples")
        except Exception:
            pass

    def clear(self):
        self.learning_rates = {}
        self.knowledge_gaps = []
        self.domain_interactions = defaultdict(int)
        self.total_optimizations = 0
        self.current_strategy = "concrete_examples"
