"""
GENESIS — Tutor Engine (v4.3)

Motor de tutoría adaptativa: Genesis gestiona currículos personalizados,
repasa lecciones con repetición espaciada (SM-2), y guía al usuario
paso a paso según su progreso.

Componentes:
- CurriculumNode: nodo de un currículo con prerrequisitos y maestría
- SpacedRepetition: cálculo de intervalos de repaso con algoritmo SM-2
- TutorEngine: coordinador con gestión de currículos y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class CurriculumNode:
    """Un nodo de currículo (lección/tema)."""

    def __init__(self, topic: str, prerequisites: list = None,
                 difficulty: int = 1, domain: str = "general",
                 node_id: str = None):
        self.node_id = node_id or hashlib.md5(
            f"{domain}:{topic}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.topic = topic
        self.prerequisites = prerequisites or []
        self.difficulty = max(1, min(5, difficulty))
        self.domain = domain
        self.completed = False
        self.mastery = 0.0          # 0.0 - 1.0
        self.attempts = 0
        self.correct_count = 0
        self.created_at = time.time()
        self.last_reviewed = 0.0
        # SM-2 parameters
        self.ease_factor = 2.5
        self.interval = 1           # days
        self.repetitions = 0
        self.next_review_at = 0.0

    @property
    def accuracy(self) -> float:
        """Precisión del usuario en esta lección."""
        if self.attempts == 0:
            return 0.0
        return self.correct_count / self.attempts

    def prerequisites_met(self, completed_ids: set) -> bool:
        """Verifica si los prerrequisitos están cumplidos."""
        if not self.prerequisites:
            return True
        return all(pid in completed_ids for pid in self.prerequisites)

    def update_mastery(self):
        """Actualiza el nivel de maestría basado en intentos y precisión."""
        if self.attempts == 0:
            self.mastery = 0.0
            return
        # Mastery = accuracy weighted by repetitions (more reps = more confident)
        rep_factor = min(1.0, self.repetitions / 5.0)
        self.mastery = self.accuracy * (0.5 + 0.5 * rep_factor)
        if self.mastery >= 0.85 and self.repetitions >= 2:
            self.completed = True

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "topic": self.topic,
            "prerequisites": self.prerequisites,
            "difficulty": self.difficulty,
            "domain": self.domain,
            "completed": self.completed,
            "mastery": round(self.mastery, 4),
            "attempts": self.attempts,
            "correct_count": self.correct_count,
            "created_at": self.created_at,
            "last_reviewed": self.last_reviewed,
            "ease_factor": round(self.ease_factor, 4),
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review_at": self.next_review_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CurriculumNode":
        node = cls(
            topic=data.get("topic", ""),
            prerequisites=data.get("prerequisites", []),
            difficulty=data.get("difficulty", 1),
            domain=data.get("domain", "general"),
            node_id=data.get("id"),
        )
        node.completed = data.get("completed", False)
        node.mastery = data.get("mastery", 0.0)
        node.attempts = data.get("attempts", 0)
        node.correct_count = data.get("correct_count", 0)
        node.created_at = data.get("created_at", time.time())
        node.last_reviewed = data.get("last_reviewed", 0.0)
        node.ease_factor = data.get("ease_factor", 2.5)
        node.interval = data.get("interval", 1)
        node.repetitions = data.get("repetitions", 0)
        node.next_review_at = data.get("next_review_at", 0.0)
        return node


class SpacedRepetition:
    """
    Implementación del algoritmo SM-2 para repetición espaciada.
    Calcula el siguiente intervalo de repaso basado en rendimiento.
    """

    MIN_EASE_FACTOR = 1.3
    MAX_INTERVAL_DAYS = 365

    def calculate_next_review(self, node: CurriculumNode,
                               quality: int) -> float:
        """
        Calcula el próximo momento de repaso usando SM-2.

        quality: 0-5 (0=apagón total, 5=respuesta perfecta)
        Retorna timestamp del próximo repaso.
        """
        quality = max(0, min(5, quality))

        if quality < 3:
            # Respuesta incorrecta: reiniciar repeticiones
            node.repetitions = 0
            node.interval = 1
        else:
            # Respuesta correcta: actualizar intervalo
            if node.repetitions == 0:
                node.interval = 1
            elif node.repetitions == 1:
                node.interval = 6
            else:
                node.interval = int(node.interval * node.ease_factor)

            node.repetitions += 1

        # Actualizar ease factor: EF' = EF + (0.1 - (5-q)*(0.08+(5-q)*0.02))
        node.ease_factor = node.ease_factor + (
            0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )
        node.ease_factor = max(self.MIN_EASE_FACTOR, node.ease_factor)

        # Cap interval
        node.interval = min(node.interval, self.MAX_INTERVAL_DAYS)

        # Calcular timestamp de próximo repaso
        node.last_reviewed = time.time()
        node.next_review_at = node.last_reviewed + (node.interval * 86400)

        return node.next_review_at

    def quality_from_correct(self, correct: bool, difficulty: int) -> int:
        """Convierte un resultado correcto/incorrecto a quality SM-2."""
        if correct:
            # Difficulty 1-5 maps to quality 5-3
            return max(3, 6 - difficulty)
        else:
            # Incorrect: difficulty 1-5 maps to quality 2-0
            return max(0, 3 - difficulty)

    def get_due_nodes(self, nodes: list) -> list:
        """Retorna nodos que necesitan repaso (due for review)."""
        now = time.time()
        due = []
        for node in nodes:
            if node.completed:
                # Even completed nodes may need review
                if node.next_review_at > 0 and now >= node.next_review_at:
                    due.append(node)
            elif not node.completed:
                # Not completed: always due if never reviewed or past due
                if node.next_review_at == 0 or now >= node.next_review_at:
                    due.append(node)
        # Sort by overdue-ness (most overdue first)
        due.sort(key=lambda n: n.next_review_at)
        return due


class TutorEngine:
    """
    Coordinador de tutoría adaptativa.
    Gestiona currículos, repaso espaciado, y progreso.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/tutor_engine")
        self.data_file = self.base_dir / "tutor_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.curricula = {}         # domain -> list of CurriculumNode
        self.sr = SpacedRepetition()
        self.max_nodes_per_domain = 100
        self.total_lessons = 0
        self.total_correct = 0
        self.total_incorrect = 0
        self.enabled = True

        self._load()

    def create_curriculum(self, domain: str, topics: list) -> list:
        """
        Crea un currículo para un dominio.
        topics: list of dicts {topic, prerequisites, difficulty}
        o list of strings (simple topics sin prerrequisitos).
        Retorna lista de node_ids creados.
        """
        domain_lower = domain.lower().strip()
        if domain_lower not in self.curricula:
            self.curricula[domain_lower] = []

        created_ids = []
        existing_topics = {
            n.topic.lower() for n in self.curricula[domain_lower]
        }

        for i, topic_data in enumerate(topics):
            if isinstance(topic_data, str):
                topic_data = {
                    "topic": topic_data,
                    "prerequisites": [],
                    "difficulty": min(5, 1 + i // 3),
                }

            topic_name = topic_data.get("topic", "")
            if topic_name.lower() in existing_topics:
                continue

            node = CurriculumNode(
                topic=topic_name,
                prerequisites=topic_data.get("prerequisites", []),
                difficulty=topic_data.get("difficulty", 1),
                domain=domain_lower,
            )
            self.curricula[domain_lower].append(node)
            created_ids.append(node.node_id)
            existing_topics.add(topic_name.lower())

        # Trim si excede máximo
        if len(self.curricula[domain_lower]) > self.max_nodes_per_domain:
            self.curricula[domain_lower] = \
                self.curricula[domain_lower][-self.max_nodes_per_domain:]

        return created_ids

    def get_next_lesson(self, domain: str = None) -> CurriculumNode:
        """
        Obtiene la siguiente lección a estudiar.
        Prioridad: 1) due for review, 2) next incomplete with prereqs met.
        """
        nodes = []
        if domain:
            nodes = self.curricula.get(domain.lower().strip(), [])
        else:
            for domain_nodes in self.curricula.values():
                nodes.extend(domain_nodes)

        if not nodes:
            return None

        completed_ids = {n.node_id for n in nodes if n.completed}

        # First: check for due reviews
        due = self.sr.get_due_nodes(nodes)
        if due:
            return due[0]

        # Second: next incomplete node with prerequisites met
        for node in nodes:
            if not node.completed and node.prerequisites_met(completed_ids):
                return node

        return None

    def record_answer(self, node_id: str, correct: bool,
                      domain: str = None) -> dict:
        """
        Registra la respuesta del usuario a una lección.
        Retorna dict con mastery actualizado y próximo repaso.
        """
        node = self._find_node(node_id, domain)
        if not node:
            return {"error": "node_not_found"}

        self.total_lessons += 1
        node.attempts += 1
        if correct:
            node.correct_count += 1
            self.total_correct += 1
        else:
            self.total_incorrect += 1

        # Calcular quality SM-2 y actualizar intervalo
        quality = self.sr.quality_from_correct(correct, node.difficulty)
        next_review = self.sr.calculate_next_review(node, quality)

        # Actualizar mastery
        node.update_mastery()

        return {
            "node_id": node.node_id,
            "topic": node.topic,
            "mastery": round(node.mastery, 3),
            "completed": node.completed,
            "next_review_at": next_review,
            "interval_days": node.interval,
            "ease_factor": round(node.ease_factor, 3),
        }

    def get_progress(self, domain: str = None) -> dict:
        """Obtiene el progreso del currículo."""
        nodes = []
        if domain:
            nodes = self.curricula.get(domain.lower().strip(), [])
        else:
            for domain_nodes in self.curricula.values():
                nodes.extend(domain_nodes)

        if not nodes:
            return {"total": 0, "completed": 0, "progress": 0.0}

        completed = sum(1 for n in nodes if n.completed)
        avg_mastery = sum(n.mastery for n in nodes) / len(nodes)
        due_count = len(self.sr.get_due_nodes(nodes))

        return {
            "total": len(nodes),
            "completed": completed,
            "progress": round(completed / len(nodes), 3),
            "avg_mastery": round(avg_mastery, 3),
            "due_for_review": due_count,
            "domains": list(self.curricula.keys()),
        }

    def get_context_for_prompt(self, user_input: str = "",
                               max_chars: int = 500) -> str:
        """Genera contexto de tutoría para inyectar en el prompt."""
        if not self.enabled:
            return ""

        next_lesson = self.get_next_lesson()
        if not next_lesson:
            return ""

        progress = self.get_progress()
        lines = ["[CONTEXTO DE TUTORIA]"]
        lines.append(
            f"Siguiente lección: {next_lesson.topic} "
            f"(dificultad {next_lesson.difficulty}/5, "
            f"maestría {next_lesson.mastery:.0%})"
        )
        lines.append(
            f"Progreso general: {progress['completed']}/{progress['total']} "
            f"completados ({progress['progress']:.0%})"
        )
        if progress["due_for_review"] > 0:
            lines.append(
                f"Lecciones pendientes de repaso: {progress['due_for_review']}"
            )

        result = "\n".join(lines)
        return result[:max_chars]

    def _find_node(self, node_id: str,
                   domain: str = None) -> CurriculumNode:
        """Busca un nodo por ID."""
        if domain:
            for node in self.curricula.get(domain.lower().strip(), []):
                if node.node_id == node_id:
                    return node
        else:
            for domain_nodes in self.curricula.values():
                for node in domain_nodes:
                    if node.node_id == node_id:
                        return node
        return None

    def get_stats(self) -> dict:
        total_nodes = sum(
            len(nodes) for nodes in self.curricula.values()
        )
        return {
            "total_domains": len(self.curricula),
            "total_nodes": total_nodes,
            "total_lessons": self.total_lessons,
            "total_correct": self.total_correct,
            "accuracy": round(
                self.total_correct / max(self.total_lessons, 1), 3
            ),
        }

    def status(self) -> str:
        total_nodes = sum(
            len(nodes) for nodes in self.curricula.values()
        )
        return (f"Dominios: {len(self.curricula)} | "
                f"Lecciones: {total_nodes} | "
                f"Respondidas: {self.total_lessons} | "
                f"Correctas: {self.total_correct}")

    def generate_report(self) -> str:
        lines = ["=== TUTOR ENGINE REPORT ==="]
        lines.append(f"Dominios: {len(self.curricula)}")
        lines.append(f"Total lecciones respondidas: {self.total_lessons}")
        lines.append(f"Correctas: {self.total_correct}")
        lines.append(f"Incorrectas: {self.total_incorrect}")
        if self.total_lessons > 0:
            acc = self.total_correct / self.total_lessons
            lines.append(f"Precisión: {acc:.1%}")

        for domain, nodes in sorted(self.curricula.items()):
            completed = sum(1 for n in nodes if n.completed)
            avg_mastery = sum(n.mastery for n in nodes) / max(len(nodes), 1)
            lines.append(f"\n  [{domain}] {completed}/{len(nodes)} completados, "
                         f"maestría promedio: {avg_mastery:.1%}")
            for node in nodes[:10]:
                status = "OK" if node.completed else f"mastery={node.mastery:.0%}"
                lines.append(
                    f"    {node.topic} (d={node.difficulty}) [{status}] "
                    f"intentos={node.attempts}"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_lessons": self.total_lessons,
            "total_correct": self.total_correct,
            "total_incorrect": self.total_incorrect,
            "curricula": {
                domain: [n.to_dict() for n in nodes]
                for domain, nodes in self.curricula.items()
            },
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
            self.total_lessons = data.get("total_lessons", 0)
            self.total_correct = data.get("total_correct", 0)
            self.total_incorrect = data.get("total_incorrect", 0)
            for domain, nodes_data in data.get("curricula", {}).items():
                self.curricula[domain] = [
                    CurriculumNode.from_dict(nd) for nd in nodes_data
                ]
        except Exception:
            pass

    def clear(self):
        self.curricula = {}
        self.total_lessons = 0
        self.total_correct = 0
        self.total_incorrect = 0
