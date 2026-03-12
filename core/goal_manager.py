"""
GENESIS — Goal Manager (v2.5)

Sistema de metas auto-dirigidas: Genesis se pone objetivos propios,
los trackea, y prioriza su atención.

Componentes:
- Goal: una meta con título, prioridad, progreso y sub-goals
- GoalTracker: seguimiento de progreso con auto-complete y abandono
- GoalSuggester: sugiere metas basándose en patrones y knowledge gaps
- GoalManager: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class Goal:
    """Una meta con estado, prioridad y progreso."""

    STATUSES = ("active", "completed", "abandoned", "paused")

    def __init__(self, goal_id: str = None, title: str = "",
                 description: str = "", priority: int = 5):
        self.goal_id = goal_id or hashlib.md5(
            f"goal_{time.time()}_{title}".encode()
        ).hexdigest()[:10]
        self.title = title
        self.description = description
        self.priority = max(1, min(10, priority))  # 1-10
        self.status = "active"
        self.progress = 0.0              # 0.0 a 1.0
        self.sub_goals = []              # Lista de sub-goal IDs
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at = 0
        self.tags = []
        self.notes = []                  # Notas de progreso
        self.source = ""                 # "user", "suggested", "auto"

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_stale(self) -> bool:
        """Meta sin actualización en más de 48 horas."""
        return (time.time() - self.updated_at) > 48 * 3600

    def update_progress(self, progress: float, note: str = ""):
        """Actualiza progreso (0.0 a 1.0)."""
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = time.time()
        if note:
            self.notes.append({
                "timestamp": time.time(),
                "text": note[:200],
            })
            if len(self.notes) > 20:
                self.notes = self.notes[-20:]
        # Auto-complete
        if self.progress >= 1.0 and self.status == "active":
            self.status = "completed"
            self.completed_at = time.time()

    def complete(self, note: str = ""):
        """Marca como completado."""
        self.status = "completed"
        self.progress = 1.0
        self.completed_at = time.time()
        self.updated_at = time.time()
        if note:
            self.notes.append({"timestamp": time.time(), "text": note[:200]})

    def abandon(self, reason: str = ""):
        """Marca como abandonado."""
        self.status = "abandoned"
        self.updated_at = time.time()
        if reason:
            self.notes.append({"timestamp": time.time(), "text": f"Abandonado: {reason[:200]}"})

    def pause(self):
        """Pausa la meta."""
        self.status = "paused"
        self.updated_at = time.time()

    def resume(self):
        """Reanuda la meta."""
        self.status = "active"
        self.updated_at = time.time()

    def to_text(self) -> str:
        """Representación textual para inyectar en prompts."""
        bar = "█" * int(self.progress * 10) + "░" * (10 - int(self.progress * 10))
        return f"[Meta P{self.priority}] {self.title} [{bar}] {self.progress:.0%}"

    def to_dict(self) -> dict:
        return {
            "id": self.goal_id,
            "title": self.title[:200],
            "description": self.description[:500],
            "priority": self.priority,
            "status": self.status,
            "progress": self.progress,
            "sub_goals": self.sub_goals[:10],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "tags": self.tags[:10],
            "notes": self.notes[-10:],
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Goal":
        g = cls(
            goal_id=data.get("id"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=data.get("priority", 5),
        )
        g.status = data.get("status", "active")
        g.progress = data.get("progress", 0.0)
        g.sub_goals = data.get("sub_goals", [])
        g.created_at = data.get("created_at", time.time())
        g.updated_at = data.get("updated_at", time.time())
        g.completed_at = data.get("completed_at", 0)
        g.tags = data.get("tags", [])
        g.notes = data.get("notes", [])
        g.source = data.get("source", "")
        return g


class GoalTracker:
    """Seguimiento automático de progreso y estado de metas."""

    def __init__(self, stale_hours: float = 48, max_active: int = 10):
        self.stale_hours = stale_hours
        self.max_active = max_active

    def check_stale(self, goals: list) -> list:
        """Detecta metas que llevan mucho sin actualización."""
        cutoff = time.time() - (self.stale_hours * 3600)
        return [g for g in goals if g.is_active and g.updated_at < cutoff]

    def auto_progress_from_keywords(self, goal: Goal, text: str) -> float:
        """
        Estima progreso basándose en keywords relevantes del texto.
        Retorna delta de progreso (puede ser 0).
        """
        if not goal.is_active or not text:
            return 0.0

        title_words = set(goal.title.lower().split())
        tag_words = set(t.lower() for t in goal.tags)
        relevant_words = title_words | tag_words

        if not relevant_words:
            return 0.0

        text_lower = text.lower()
        matches = sum(1 for w in relevant_words if w in text_lower and len(w) > 3)

        if matches >= 3:
            return 0.1  # Avance significativo
        elif matches >= 1:
            return 0.03  # Avance mínimo
        return 0.0

    def prioritize(self, goals: list) -> list:
        """Ordena metas activas por prioridad (alta primero), luego por progreso (más avanzada primero)."""
        active = [g for g in goals if g.is_active]
        return sorted(active, key=lambda g: (-g.priority, -g.progress))

    def get_focus_goal(self, goals: list) -> "Goal":
        """Retorna la meta de mayor prioridad activa."""
        prioritized = self.prioritize(goals)
        return prioritized[0] if prioritized else None


class GoalSuggester:
    """Sugiere metas basándose en patrones de uso y knowledge gaps."""

    # Templates de sugerencias por categoría
    SUGGESTION_TEMPLATES = {
        "knowledge_gap": {
            "title_template": "Aprender sobre {topic}",
            "description": "Investigar y profundizar en {topic} basado en preguntas recurrentes.",
            "priority": 6,
        },
        "skill_improvement": {
            "title_template": "Mejorar calidad en {intent}",
            "description": "Mejorar la calidad de respuestas para el intent '{intent}'.",
            "priority": 7,
        },
        "consistency": {
            "title_template": "Mantener consistencia en {area}",
            "description": "Mantener buen rendimiento en {area} donde ya se tiene éxito.",
            "priority": 4,
        },
        "exploration": {
            "title_template": "Explorar {topic}",
            "description": "Explorar proactivamente el tema {topic} que aparece frecuentemente.",
            "priority": 5,
        },
    }

    def suggest_from_meta_learner(self, insights: list) -> list:
        """Genera sugerencias desde insights del meta-learner."""
        suggestions = []

        for ins in insights:
            if ins.confidence < 0.5:
                continue

            if "bajo rendimiento" in ins.description.lower():
                # Extraer intent del insight
                intent = ins.category
                if "'" in ins.description:
                    intent = ins.description.split("'")[1]

                tmpl = self.SUGGESTION_TEMPLATES["skill_improvement"]
                goal = Goal(
                    title=tmpl["title_template"].format(intent=intent),
                    description=tmpl["description"].format(intent=intent),
                    priority=tmpl["priority"],
                )
                goal.source = "suggested"
                goal.tags = ["meta-learner", intent]
                suggestions.append(goal)

            elif "excelente rendimiento" in ins.description.lower():
                intent = ins.category
                if "'" in ins.description:
                    intent = ins.description.split("'")[1]

                tmpl = self.SUGGESTION_TEMPLATES["consistency"]
                goal = Goal(
                    title=tmpl["title_template"].format(area=intent),
                    description=tmpl["description"].format(area=intent),
                    priority=tmpl["priority"],
                )
                goal.source = "suggested"
                goal.tags = ["meta-learner", intent]
                suggestions.append(goal)

        return suggestions[:5]

    def suggest_from_topics(self, topic_counts: dict) -> list:
        """Sugiere metas basándose en temas frecuentes."""
        suggestions = []

        # Temas con alta frecuencia → exploración
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)

        for topic, count in sorted_topics[:3]:
            if count >= 5:
                tmpl = self.SUGGESTION_TEMPLATES["exploration"]
                goal = Goal(
                    title=tmpl["title_template"].format(topic=topic),
                    description=tmpl["description"].format(topic=topic),
                    priority=tmpl["priority"],
                )
                goal.source = "suggested"
                goal.tags = ["exploration", topic]
                suggestions.append(goal)

        return suggestions

    def suggest_from_gaps(self, negative_topics: list) -> list:
        """Sugiere metas de aprendizaje desde temas con feedback negativo."""
        suggestions = []

        for topic in negative_topics[:3]:
            tmpl = self.SUGGESTION_TEMPLATES["knowledge_gap"]
            goal = Goal(
                title=tmpl["title_template"].format(topic=topic),
                description=tmpl["description"].format(topic=topic),
                priority=tmpl["priority"],
            )
            goal.source = "suggested"
            goal.tags = ["knowledge_gap", topic]
            suggestions.append(goal)

        return suggestions


class GoalManager:
    """
    Coordinador de sistema de metas.
    Gestiona goals con seguimiento, sugerencias y persistencia.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/goals")
        self.data_file = self.base_dir / "goals_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.goals = []  # Lista de Goal
        self.tracker = GoalTracker()
        self.suggester = GoalSuggester()
        self.max_goals = 50
        self.total_created = 0
        self.total_completed = 0
        self.total_abandoned = 0
        self.enabled = True

        self._load()

    def create_goal(self, title: str, description: str = "",
                    priority: int = 5, tags: list = None,
                    source: str = "user") -> Goal:
        """Crea una nueva meta."""
        if not self.enabled:
            return None

        # Verificar duplicados por título similar
        for existing in self.goals:
            if existing.is_active and self._title_similarity(existing.title, title) > 0.8:
                return existing  # Ya existe

        goal = Goal(title=title, description=description, priority=priority)
        goal.source = source
        if tags:
            goal.tags = tags[:10]

        self.goals.append(goal)
        self.total_created += 1

        # Evicción si excede máximo
        if len(self.goals) > self.max_goals:
            self._evict()

        return goal

    def update_progress(self, goal_id: str, progress: float, note: str = "") -> bool:
        """Actualiza progreso de una meta."""
        goal = self._find_goal(goal_id)
        if not goal:
            return False
        goal.update_progress(progress, note)
        if goal.status == "completed":
            self.total_completed += 1
        return True

    def complete_goal(self, goal_id: str, note: str = "") -> bool:
        """Marca una meta como completada."""
        goal = self._find_goal(goal_id)
        if not goal:
            return False
        goal.complete(note)
        self.total_completed += 1
        return True

    def abandon_goal(self, goal_id: str, reason: str = "") -> bool:
        """Abandona una meta."""
        goal = self._find_goal(goal_id)
        if not goal:
            return False
        goal.abandon(reason)
        self.total_abandoned += 1
        return True

    def get_active_goals(self) -> list:
        """Retorna metas activas ordenadas por prioridad."""
        return self.tracker.prioritize(self.goals)

    def get_focus_goal(self) -> Goal:
        """Retorna la meta de mayor prioridad."""
        return self.tracker.get_focus_goal(self.goals)

    def get_stale_goals(self) -> list:
        """Retorna metas estancadas."""
        return self.tracker.check_stale(self.goals)

    def auto_track(self, user_input: str, response: str):
        """Actualiza progreso automáticamente basándose en contenido."""
        if not self.enabled:
            return

        combined_text = f"{user_input} {response}"

        for goal in self.goals:
            if not goal.is_active:
                continue
            delta = self.tracker.auto_progress_from_keywords(goal, combined_text)
            if delta > 0:
                old_progress = goal.progress
                goal.update_progress(min(1.0, goal.progress + delta),
                                     note=f"Auto-progreso por keywords ({delta:.0%})")
                if goal.status == "completed" and old_progress < 1.0:
                    self.total_completed += 1

    def suggest_goals(self, insights: list = None, topic_counts: dict = None,
                      negative_topics: list = None) -> list:
        """Genera sugerencias de metas."""
        suggestions = []

        if insights:
            suggestions.extend(self.suggester.suggest_from_meta_learner(insights))
        if topic_counts:
            suggestions.extend(self.suggester.suggest_from_topics(topic_counts))
        if negative_topics:
            suggestions.extend(self.suggester.suggest_from_gaps(negative_topics))

        return suggestions[:5]

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de metas para inyectar en prompt."""
        if not self.enabled:
            return ""

        active = self.get_active_goals()
        if not active:
            return ""

        lines = ["[METAS ACTIVAS]"]
        total_chars = 0

        for goal in active[:5]:
            text = goal.to_text()
            if total_chars + len(text) > max_chars:
                break
            lines.append(text)
            total_chars += len(text)

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        """Estadísticas del sistema de metas."""
        active = [g for g in self.goals if g.status == "active"]
        return {
            "total_created": self.total_created,
            "total_completed": self.total_completed,
            "total_abandoned": self.total_abandoned,
            "active_goals": len(active),
            "stored_goals": len(self.goals),
            "focus_goal": self.get_focus_goal().title if self.get_focus_goal() else "ninguno",
            "stale_count": len(self.get_stale_goals()),
        }

    def status(self) -> str:
        """Status de una línea."""
        active = len([g for g in self.goals if g.status == "active"])
        focus = self.get_focus_goal()
        focus_str = focus.title[:30] if focus else "ninguno"
        return (f"Metas activas: {active} | "
                f"Completadas: {self.total_completed} | "
                f"Foco: {focus_str}")

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = ["=== GOAL MANAGER REPORT ==="]
        lines.append(f"Total creadas: {self.total_created}")
        lines.append(f"Completadas: {self.total_completed}")
        lines.append(f"Abandonadas: {self.total_abandoned}")
        lines.append(f"Almacenadas: {len(self.goals)}")

        active = self.get_active_goals()
        if active:
            lines.append(f"\nMetas activas ({len(active)}):")
            for g in active[:10]:
                bar = "█" * int(g.progress * 10) + "░" * (10 - int(g.progress * 10))
                stale_mark = " ⚠️STALE" if g.is_stale else ""
                lines.append(f"  P{g.priority} [{bar}] {g.title}{stale_mark}")
                if g.description:
                    lines.append(f"       {g.description[:80]}")

        completed = [g for g in self.goals if g.status == "completed"][-5:]
        if completed:
            lines.append(f"\nÚltimas completadas:")
            for g in completed:
                lines.append(f"  ✓ {g.title}")

        stale = self.get_stale_goals()
        if stale:
            lines.append(f"\n⚠️ Metas estancadas ({len(stale)}):")
            for g in stale[:5]:
                hours = (time.time() - g.updated_at) / 3600
                lines.append(f"  {g.title} (sin actualizar hace {int(hours)}h)")

        return "\n".join(lines)

    def save(self):
        """Persiste estado a disco."""
        data = {
            "total_created": self.total_created,
            "total_completed": self.total_completed,
            "total_abandoned": self.total_abandoned,
            "goals": [g.to_dict() for g in self.goals[-self.max_goals:]],
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
            self.total_created = data.get("total_created", 0)
            self.total_completed = data.get("total_completed", 0)
            self.total_abandoned = data.get("total_abandoned", 0)
            self.goals = [Goal.from_dict(g) for g in data.get("goals", [])]
        except Exception:
            pass

    def clear(self):
        """Limpia todas las metas."""
        self.goals = []
        self.total_created = 0
        self.total_completed = 0
        self.total_abandoned = 0

    def _find_goal(self, goal_id: str) -> Goal:
        """Busca una meta por ID."""
        for g in self.goals:
            if g.goal_id == goal_id:
                return g
        return None

    def _title_similarity(self, a: str, b: str) -> float:
        """Containment similarity entre títulos."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        min_size = min(len(words_a), len(words_b))
        return len(intersection) / min_size if min_size else 0.0

    def _evict(self):
        """Elimina metas antiguas completadas/abandonadas."""
        # Primero remover abandonadas antiguas
        self.goals = [g for g in self.goals
                      if not (g.status == "abandoned" and g.age_hours > 168)]

        # Si sigue excediendo, remover completadas más antiguas
        if len(self.goals) > self.max_goals:
            completed = [(i, g) for i, g in enumerate(self.goals)
                         if g.status == "completed"]
            completed.sort(key=lambda x: x[1].completed_at)
            to_remove = len(self.goals) - self.max_goals
            remove_indices = set(i for i, _ in completed[:to_remove])
            self.goals = [g for i, g in enumerate(self.goals)
                          if i not in remove_indices]
