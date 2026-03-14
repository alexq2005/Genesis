"""
GENESIS — Autonomous Research Loop (v5.0)

Ciclo autónomo de investigación: Genesis identifica gaps de conocimiento,
formula hipótesis, diseña experimentos, ejecuta ciclos de investigación,
analiza resultados y publica insights de forma autónoma.

Componentes:
- ResearchCycle: ciclo completo de investigación con fases
- PriorityQueue: cola de preguntas priorizada por impacto * novedad
- AutonomousResearchLoop: coordinador con ciclos activos y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import deque, defaultdict


class ResearchCycle:
    """Un ciclo completo de investigación autónoma."""

    STAGES = [
        "identifying", "hypothesizing", "designing",
        "executing", "analyzing", "publishing",
    ]

    def __init__(self, question: str, domain: str = "general",
                 cycle_id: str = None):
        self.cycle_id = cycle_id or hashlib.md5(
            f"{question[:50]}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.question = question[:500]
        self.domain = domain
        self.hypothesis = ""
        self.experiment_design = ""
        self.results = ""
        self.insight = ""
        self.status = "identifying"
        self.cycle_number = 0
        self.created_at = time.time()
        self.completed_at = 0.0
        self.impact_score = 0.5
        self.novelty_score = 0.5
        self.stage_timestamps = {"identifying": time.time()}
        self.notes = []             # observaciones durante el ciclo

    @property
    def priority(self) -> float:
        """Prioridad = impacto * novedad."""
        return self.impact_score * self.novelty_score

    @property
    def is_complete(self) -> bool:
        return self.status == "publishing" and self.completed_at > 0

    @property
    def progress(self) -> float:
        """Progreso como fracción (0-1)."""
        idx = self.STAGES.index(self.status) if self.status in self.STAGES else 0
        return (idx + 1) / len(self.STAGES)

    @property
    def duration_seconds(self) -> float:
        """Duración total del ciclo."""
        end = self.completed_at if self.completed_at else time.time()
        return end - self.created_at

    def advance(self) -> bool:
        """Avanza al siguiente stage."""
        if self.status not in self.STAGES:
            return False
        idx = self.STAGES.index(self.status)
        if idx >= len(self.STAGES) - 1:
            return False
        self.status = self.STAGES[idx + 1]
        self.stage_timestamps[self.status] = time.time()
        if self.status == "publishing":
            self.completed_at = time.time()
        return True

    def add_note(self, note: str):
        """Agrega una nota de observación."""
        self.notes.append({
            "text": note[:300],
            "stage": self.status,
            "timestamp": time.time(),
        })
        if len(self.notes) > 20:
            self.notes = self.notes[-20:]

    def to_dict(self) -> dict:
        return {
            "id": self.cycle_id,
            "question": self.question,
            "domain": self.domain,
            "hypothesis": self.hypothesis,
            "experiment_design": self.experiment_design,
            "results": self.results,
            "insight": self.insight,
            "status": self.status,
            "cycle_number": self.cycle_number,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "impact_score": round(self.impact_score, 4),
            "novelty_score": round(self.novelty_score, 4),
            "stage_timestamps": self.stage_timestamps,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResearchCycle":
        cycle = cls(
            question=data.get("question", ""),
            domain=data.get("domain", "general"),
            cycle_id=data.get("id"),
        )
        cycle.hypothesis = data.get("hypothesis", "")
        cycle.experiment_design = data.get("experiment_design", "")
        cycle.results = data.get("results", "")
        cycle.insight = data.get("insight", "")
        cycle.status = data.get("status", "identifying")
        cycle.cycle_number = data.get("cycle_number", 0)
        cycle.created_at = data.get("created_at", time.time())
        cycle.completed_at = data.get("completed_at", 0.0)
        cycle.impact_score = data.get("impact_score", 0.5)
        cycle.novelty_score = data.get("novelty_score", 0.5)
        cycle.stage_timestamps = data.get("stage_timestamps", {})
        cycle.notes = data.get("notes", [])
        return cycle


class PriorityQueue:
    """Cola de preguntas de investigación priorizada."""

    def __init__(self, max_size: int = 50):
        self.questions = deque(maxlen=max_size)
        self.max_size = max_size

    def add(self, question: str, impact: float = 0.5,
            novelty: float = 0.5, domain: str = "general"):
        """Agrega una pregunta con scoring de prioridad."""
        impact = max(0.0, min(1.0, impact))
        novelty = max(0.0, min(1.0, novelty))

        # Verificar duplicados por similitud simple
        q_lower = question.lower().strip()
        for existing in self.questions:
            if self._text_overlap(q_lower, existing["question"].lower()) > 0.8:
                # Actualizar scores si son mejores
                existing["impact"] = max(existing["impact"], impact)
                existing["novelty"] = max(existing["novelty"], novelty)
                existing["priority"] = existing["impact"] * existing["novelty"]
                return

        self.questions.append({
            "question": question[:300],
            "impact": impact,
            "novelty": novelty,
            "priority": impact * novelty,
            "domain": domain,
            "added_at": time.time(),
        })

    def get_top(self, n: int = 5) -> list:
        """Retorna top N preguntas por prioridad."""
        sorted_q = sorted(
            self.questions,
            key=lambda q: q["priority"],
            reverse=True,
        )
        return sorted_q[:n]

    def pop_top(self) -> dict:
        """Saca la pregunta de mayor prioridad."""
        if not self.questions:
            return None
        sorted_q = sorted(
            self.questions,
            key=lambda q: q["priority"],
            reverse=True,
        )
        top = sorted_q[0]
        self.questions.remove(top)
        return top

    @property
    def size(self) -> int:
        return len(self.questions)

    def _text_overlap(self, a: str, b: str) -> float:
        """Overlap simple de palabras."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        min_size = min(len(words_a), len(words_b))
        return len(intersection) / min_size if min_size else 0.0

    def to_list(self) -> list:
        return list(self.questions)


class AutonomousResearchLoop:
    """
    Coordinador de investigación autónoma.
    Gestiona ciclos de investigación, cola de preguntas,
    y publicación de insights.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/research_loop")
        self.data_file = self.base_dir / "research_loop_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.cycles = {}            # cycle_id -> ResearchCycle
        self.queue = PriorityQueue(max_size=50)
        self.published_insights = []
        self.max_cycles = 200
        self.total_cycles = 0
        self.completed_cycles = 0
        self.insights_published = 0
        self.enabled = True

        self._load()

    def identify_gap(self, domain: str, question: str,
                     impact: float = 0.5, novelty: float = 0.5) -> None:
        """Identifica un gap de conocimiento como pregunta de investigación."""
        if not self.enabled or not question:
            return
        self.queue.add(question, impact, novelty, domain)

    def formulate_hypothesis(self, cycle_id: str,
                              hypothesis: str) -> bool:
        """Formula una hipótesis para un ciclo."""
        cycle = self.cycles.get(cycle_id)
        if not cycle or cycle.status != "identifying":
            return False
        cycle.hypothesis = hypothesis[:500]
        cycle.advance()
        return True

    def design_experiment(self, cycle_id: str,
                          design: str) -> bool:
        """Diseña un experimento para un ciclo."""
        cycle = self.cycles.get(cycle_id)
        if not cycle or cycle.status != "hypothesizing":
            return False
        cycle.experiment_design = design[:500]
        cycle.advance()
        return True

    def execute_cycle(self, cycle_id: str = None,
                      question: str = "",
                      domain: str = "general") -> ResearchCycle:
        """
        Inicia o continúa un ciclo de investigación.
        Si no se da cycle_id, crea uno nuevo.
        """
        if not self.enabled:
            return None

        if cycle_id and cycle_id in self.cycles:
            cycle = self.cycles[cycle_id]
            if cycle.status in ("designing", "hypothesizing"):
                cycle.advance()
            return cycle

        # Crear nuevo ciclo
        if not question:
            top = self.queue.pop_top()
            if top:
                question = top["question"]
                domain = top.get("domain", "general")
            else:
                return None

        cycle = ResearchCycle(question=question, domain=domain)
        cycle.cycle_number = self.total_cycles + 1
        self.total_cycles += 1
        self.cycles[cycle.cycle_id] = cycle

        # Trim si excede máximo
        if len(self.cycles) > self.max_cycles:
            self._evict()

        return cycle

    def record_results(self, cycle_id: str, results: str) -> bool:
        """Registra resultados de un ciclo."""
        cycle = self.cycles.get(cycle_id)
        if not cycle:
            return False
        cycle.results = results[:1000]
        if cycle.status == "designing":
            cycle.advance()  # to executing
        if cycle.status == "executing":
            cycle.advance()  # to analyzing
        return True

    def publish_insight(self, cycle_id: str, insight: str = "") -> bool:
        """Publica el insight de un ciclo completado."""
        cycle = self.cycles.get(cycle_id)
        if not cycle:
            return False

        if insight:
            cycle.insight = insight[:500]

        if not cycle.insight:
            cycle.insight = f"Insight derivado de: {cycle.question[:80]}"

        # Avanzar hasta publishing si no está ahí
        while cycle.status != "publishing" and cycle.status in ResearchCycle.STAGES:
            if not cycle.advance():
                break

        self.published_insights.append({
            "cycle_id": cycle.cycle_id,
            "insight": cycle.insight,
            "question": cycle.question,
            "domain": cycle.domain,
            "impact": cycle.impact_score,
            "novelty": cycle.novelty_score,
            "published_at": time.time(),
        })
        self.completed_cycles += 1
        self.insights_published += 1

        # Mantener solo últimos 100 insights
        if len(self.published_insights) > 100:
            self.published_insights = self.published_insights[-100:]

        return True

    def get_active_cycles(self) -> list:
        """Retorna ciclos no completados."""
        return [c for c in self.cycles.values() if not c.is_complete]

    def get_cycle(self, cycle_id: str) -> ResearchCycle:
        """Obtiene un ciclo por ID."""
        return self.cycles.get(cycle_id)

    def get_context_for_prompt(self, max_chars: int = 500) -> str:
        """Genera contexto de investigación para el prompt."""
        if not self.enabled:
            return ""

        active = self.get_active_cycles()
        if not active:
            # Verificar si hay preguntas en cola
            if self.queue.size > 0:
                top = self.queue.get_top(1)
                return f"[INVESTIGACION] {self.queue.size} preguntas en cola. Top: {top[0]['question'][:60]}"[:max_chars]
            return ""

        lines = ["[INVESTIGACION ACTIVA]"]
        for cycle in active[:3]:
            lines.append(
                f"  Ciclo #{cycle.cycle_number}: {cycle.question[:60]}... "
                f"[{cycle.status}] progreso={cycle.progress:.0%}"
            )

        if self.queue.size > 0:
            lines.append(f"  +{self.queue.size} preguntas en cola")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_cycles": self.total_cycles,
            "completed_cycles": self.completed_cycles,
            "active_cycles": len(self.get_active_cycles()),
            "insights_published": self.insights_published,
            "queue_size": self.queue.size,
        }

    def status(self) -> str:
        active = len(self.get_active_cycles())
        return (f"Ciclos: {self.total_cycles} | "
                f"Completados: {self.completed_cycles} | "
                f"Activos: {active} | "
                f"Insights: {self.insights_published}")

    def generate_report(self) -> str:
        lines = ["=== AUTONOMOUS RESEARCH LOOP REPORT ==="]
        lines.append(f"Total ciclos: {self.total_cycles}")
        lines.append(f"Completados: {self.completed_cycles}")
        lines.append(f"Activos: {len(self.get_active_cycles())}")
        lines.append(f"Insights publicados: {self.insights_published}")
        lines.append(f"Preguntas en cola: {self.queue.size}")

        # Ciclos activos
        active = self.get_active_cycles()
        if active:
            lines.append(f"\nCiclos activos:")
            for cycle in active[:10]:
                lines.append(
                    f"  #{cycle.cycle_number} [{cycle.status}] "
                    f"{cycle.question[:50]}... "
                    f"(impacto={cycle.impact_score:.1f}, "
                    f"novedad={cycle.novelty_score:.1f})"
                )

        # Insights recientes
        if self.published_insights:
            lines.append(f"\nInsights recientes:")
            for ins in self.published_insights[-5:]:
                lines.append(
                    f"  [{ins['domain']}] {ins['insight'][:60]}..."
                )

        # Cola de preguntas
        top_q = self.queue.get_top(5)
        if top_q:
            lines.append(f"\nTop preguntas en cola:")
            for q in top_q:
                lines.append(
                    f"  [{q['domain']}] {q['question'][:50]}... "
                    f"(prioridad={q['priority']:.2f})"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_cycles": self.total_cycles,
            "completed_cycles": self.completed_cycles,
            "insights_published": self.insights_published,
            "cycles": {cid: c.to_dict() for cid, c in self.cycles.items()},
            "published_insights": self.published_insights,
            "queue": self.queue.to_list(),
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_cycles = data.get("total_cycles", 0)
            self.completed_cycles = data.get("completed_cycles", 0)
            self.insights_published = data.get("insights_published", 0)
            for cid, cdata in data.get("cycles", {}).items():
                self.cycles[cid] = ResearchCycle.from_dict(cdata)
            self.published_insights = data.get("published_insights", [])
            for q in data.get("queue", []):
                self.queue.questions.append(q)
        except Exception:
            pass

    def clear(self):
        self.cycles = {}
        self.queue = PriorityQueue(max_size=50)
        self.published_insights = []
        self.total_cycles = 0
        self.completed_cycles = 0
        self.insights_published = 0

    def _evict(self):
        """Elimina ciclos completados más antiguos."""
        if len(self.cycles) <= self.max_cycles:
            return
        # Primero eliminar completados, luego por antigüedad
        sorted_cycles = sorted(
            self.cycles.items(),
            key=lambda x: (
                0 if x[1].is_complete else 1,
                x[1].created_at,
            ),
        )
        to_remove = len(self.cycles) - self.max_cycles
        for cid, _ in sorted_cycles[:to_remove]:
            del self.cycles[cid]
