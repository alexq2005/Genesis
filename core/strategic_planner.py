"""
GENESIS — Strategic Planner (v2.6)

Planificación estratégica jerárquica: Genesis puede crear planes
multi-fase con dependencias, milestones y adaptación dinámica.

Componentes:
- Phase: una fase del plan con prerequisitos y acciones
- Milestone: punto de control con criterio de completitud
- PlanGraph: grafo DAG de fases con dependencias
- AdaptiveScheduler: ajusta prioridades según progreso real
- StrategicPlanner: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict, deque


class Phase:
    """Una fase del plan estratégico."""

    STATUSES = ("pending", "ready", "in_progress", "completed", "blocked", "skipped")

    def __init__(self, name: str, description: str = "",
                 priority: int = 5, estimated_effort: float = 1.0):
        self.phase_id = hashlib.md5(
            f"phase_{name}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.name = name.lower().strip()
        self.description = description[:300]
        self.priority = max(1, min(10, priority))     # 1-10
        self.estimated_effort = max(0.1, estimated_effort)  # Horas estimadas
        self.status = "pending"
        self.progress = 0.0                           # 0.0 - 1.0
        self.prerequisites = []                       # Lista de phase_ids
        self.actions = []                             # Acciones concretas (strings)
        self.notes = []                               # Notas adicionales
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None

    def is_ready(self, completed_phases: set) -> bool:
        """¿Está lista para iniciar? (todos los prereqs completados)."""
        if self.status in ("completed", "skipped"):
            return False
        if not self.prerequisites:
            return True
        return all(pid in completed_phases for pid in self.prerequisites)

    def start(self):
        """Marca como en progreso."""
        if self.status in ("pending", "ready"):
            self.status = "in_progress"
            self.started_at = time.time()

    def complete(self):
        """Marca como completada."""
        self.status = "completed"
        self.progress = 1.0
        self.completed_at = time.time()

    def block(self, reason: str = ""):
        """Marca como bloqueada."""
        self.status = "blocked"
        if reason:
            self.notes.append(f"Bloqueado: {reason[:100]}")

    def update_progress(self, progress: float):
        """Actualiza progreso (0.0 - 1.0)."""
        self.progress = max(0.0, min(1.0, progress))
        if self.progress >= 1.0:
            self.complete()
        elif self.progress > 0 and self.status == "pending":
            self.start()

    @property
    def elapsed_hours(self) -> float:
        """Horas transcurridas desde el inicio."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or time.time()
        return (end - self.started_at) / 3600

    @property
    def efficiency(self) -> float:
        """Eficiencia: estimated / actual (>1 = más rápido que estimado)."""
        if self.elapsed_hours <= 0:
            return 1.0
        return self.estimated_effort / self.elapsed_hours

    def to_dict(self) -> dict:
        return {
            "id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "status": self.status,
            "progress": round(self.progress, 3),
            "prerequisites": self.prerequisites,
            "actions": self.actions[:20],
            "notes": self.notes[:10],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Phase":
        p = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            priority=data.get("priority", 5),
            estimated_effort=data.get("estimated_effort", 1.0),
        )
        p.phase_id = data.get("id", p.phase_id)
        p.status = data.get("status", "pending")
        p.progress = data.get("progress", 0.0)
        p.prerequisites = data.get("prerequisites", [])
        p.actions = data.get("actions", [])
        p.notes = data.get("notes", [])
        p.created_at = data.get("created_at", time.time())
        p.started_at = data.get("started_at")
        p.completed_at = data.get("completed_at")
        return p


class Milestone:
    """Punto de control en el plan."""

    def __init__(self, name: str, target_phases: list = None,
                 description: str = ""):
        self.milestone_id = hashlib.md5(
            f"ms_{name}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.name = name
        self.description = description[:200]
        self.target_phases = target_phases or []  # phase_ids que lo componen
        self.reached = False
        self.reached_at = None
        self.created_at = time.time()

    def check(self, completed_phases: set) -> bool:
        """Verifica si el milestone fue alcanzado."""
        if not self.target_phases:
            return False
        reached = all(pid in completed_phases for pid in self.target_phases)
        if reached and not self.reached:
            self.reached = True
            self.reached_at = time.time()
        return reached

    def to_dict(self) -> dict:
        return {
            "id": self.milestone_id,
            "name": self.name,
            "description": self.description,
            "target_phases": self.target_phases,
            "reached": self.reached,
            "reached_at": self.reached_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Milestone":
        m = cls(
            name=data.get("name", ""),
            target_phases=data.get("target_phases", []),
            description=data.get("description", ""),
        )
        m.milestone_id = data.get("id", m.milestone_id)
        m.reached = data.get("reached", False)
        m.reached_at = data.get("reached_at")
        m.created_at = data.get("created_at", time.time())
        return m


class PlanGraph:
    """Grafo DAG de fases con dependencias."""

    def __init__(self):
        self.phases = {}          # phase_id -> Phase
        self.milestones = {}      # milestone_id -> Milestone

    def add_phase(self, phase: Phase) -> str:
        """Agrega una fase al plan."""
        self.phases[phase.phase_id] = phase
        return phase.phase_id

    def add_dependency(self, phase_id: str, depends_on: str):
        """Agrega una dependencia: phase_id depende de depends_on."""
        phase = self.phases.get(phase_id)
        if phase and depends_on in self.phases:
            if depends_on not in phase.prerequisites:
                phase.prerequisites.append(depends_on)

    def add_milestone(self, milestone: Milestone) -> str:
        """Agrega un milestone."""
        self.milestones[milestone.milestone_id] = milestone
        return milestone.milestone_id

    @property
    def completed_phase_ids(self) -> set:
        """IDs de fases completadas."""
        return {pid for pid, p in self.phases.items()
                if p.status == "completed"}

    def get_ready_phases(self) -> list:
        """Fases listas para iniciar (prereqs completados)."""
        completed = self.completed_phase_ids
        ready = []
        for phase in self.phases.values():
            if phase.status in ("pending", "ready") and phase.is_ready(completed):
                phase.status = "ready"
                ready.append(phase)
        # Ordenar por prioridad (mayor primero)
        return sorted(ready, key=lambda p: p.priority, reverse=True)

    def get_blocked_phases(self) -> list:
        """Fases bloqueadas."""
        return [p for p in self.phases.values() if p.status == "blocked"]

    def get_in_progress(self) -> list:
        """Fases en progreso."""
        return [p for p in self.phases.values() if p.status == "in_progress"]

    def get_critical_path(self) -> list:
        """
        Calcula el camino crítico (secuencia más larga de dependencias).
        Usa BFS desde fases sin prereqs hasta fases terminales.
        """
        # Encontrar fases raíz (sin prereqs)
        roots = [p for p in self.phases.values() if not p.prerequisites]
        if not roots:
            return []

        longest_path = []
        for root in roots:
            path = self._bfs_longest(root.phase_id)
            if len(path) > len(longest_path):
                longest_path = path

        return longest_path

    def _bfs_longest(self, start_id: str) -> list:
        """BFS para encontrar el camino más largo desde start_id."""
        # Construir índice forward: phase -> [dependientes]
        forward = defaultdict(list)
        for pid, phase in self.phases.items():
            for prereq in phase.prerequisites:
                forward[prereq].append(pid)

        # BFS
        longest = [start_id]
        queue = deque([(start_id, [start_id])])

        while queue:
            current, path = queue.popleft()
            dependents = forward.get(current, [])
            if not dependents:
                if len(path) > len(longest):
                    longest = path
            else:
                for dep in dependents:
                    if dep not in path:  # Evitar ciclos
                        queue.append((dep, path + [dep]))

        return longest

    @property
    def overall_progress(self) -> float:
        """Progreso general del plan (0.0 - 1.0)."""
        if not self.phases:
            return 0.0
        total = sum(p.progress for p in self.phases.values())
        return total / len(self.phases)

    def topological_sort(self) -> list:
        """Ordena fases topológicamente (respetando dependencias)."""
        in_degree = defaultdict(int)
        forward = defaultdict(list)

        for pid, phase in self.phases.items():
            if pid not in in_degree:
                in_degree[pid] = 0
            for prereq in phase.prerequisites:
                forward[prereq].append(pid)
                in_degree[pid] += 1

        queue = deque([pid for pid in self.phases if in_degree[pid] == 0])
        result = []

        while queue:
            pid = queue.popleft()
            result.append(pid)
            for dependent in forward[pid]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def check_milestones(self) -> list:
        """Verifica todos los milestones y retorna los recién alcanzados."""
        completed = self.completed_phase_ids
        newly_reached = []
        for ms in self.milestones.values():
            if not ms.reached and ms.check(completed):
                newly_reached.append(ms)
        return newly_reached

    def to_dict(self) -> dict:
        return {
            "phases": [p.to_dict() for p in self.phases.values()],
            "milestones": [m.to_dict() for m in self.milestones.values()],
        }

    def load_dict(self, data: dict):
        self.phases = {}
        self.milestones = {}
        for pd in data.get("phases", []):
            p = Phase.from_dict(pd)
            self.phases[p.phase_id] = p
        for md in data.get("milestones", []):
            m = Milestone.from_dict(md)
            self.milestones[m.milestone_id] = m


class AdaptiveScheduler:
    """Ajusta prioridades de fases según progreso y feedback."""

    def adapt(self, plan: PlanGraph, feedback: dict = None) -> list:
        """
        Adapta prioridades según:
        - Fases bloqueadas (bajar prioridad)
        - Fases con buen progreso (mantener/subir)
        - Feedback del usuario (ajustar)
        Retorna lista de cambios realizados.
        """
        changes = []
        feedback = feedback or {}

        for phase in plan.phases.values():
            original_priority = phase.priority

            # Fases bloqueadas: bajar prioridad temporalmente
            if phase.status == "blocked":
                phase.priority = max(1, phase.priority - 2)

            # Fases con buen progreso pero lentas: subir prioridad
            elif phase.status == "in_progress":
                if phase.progress > 0.5 and phase.elapsed_hours > 0:
                    if phase.efficiency < 0.5:
                        # Está tardando más del doble — subir prioridad
                        phase.priority = min(10, phase.priority + 1)

            # Feedback del usuario
            if phase.phase_id in feedback:
                user_priority = feedback[phase.phase_id]
                if isinstance(user_priority, (int, float)):
                    phase.priority = max(1, min(10, int(user_priority)))

            if phase.priority != original_priority:
                changes.append({
                    "phase": phase.name,
                    "old_priority": original_priority,
                    "new_priority": phase.priority,
                })

        return changes

    def suggest_next(self, plan: PlanGraph) -> list:
        """Sugiere las próximas fases a iniciar, considerando capacidad."""
        ready = plan.get_ready_phases()
        in_progress = plan.get_in_progress()

        # Limitar trabajo en paralelo (max 3 fases simultáneas)
        max_parallel = 3
        slots = max(0, max_parallel - len(in_progress))

        return ready[:slots]

    def estimate_completion(self, plan: PlanGraph) -> float:
        """Estima horas restantes hasta completar el plan."""
        remaining = 0.0
        for phase in plan.phases.values():
            if phase.status not in ("completed", "skipped"):
                remaining_effort = phase.estimated_effort * (1.0 - phase.progress)
                remaining += remaining_effort
        return remaining


class StrategicPlanner:
    """
    Coordinador de planificación estratégica.
    Crea, gestiona y adapta planes multi-fase con dependencias.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/strategic")
        self.data_file = self.base_dir / "planner_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.plans = {}           # plan_name -> PlanGraph
        self.active_plan = None   # Nombre del plan activo
        self.scheduler = AdaptiveScheduler()
        self.max_plans = 20
        self.total_plans_created = 0
        self.total_phases_completed = 0
        self.total_milestones_reached = 0
        self.enabled = True

        self._load()

    def create_plan(self, name: str, description: str = "") -> PlanGraph:
        """Crea un nuevo plan."""
        if not self.enabled:
            return None

        name_key = name.lower().strip()

        plan = PlanGraph()
        self.plans[name_key] = plan
        self.active_plan = name_key
        self.total_plans_created += 1

        # Evicción si excede máximo
        if len(self.plans) > self.max_plans:
            self._evict_plans()

        return plan

    def get_active_plan(self) -> PlanGraph:
        """Retorna el plan activo."""
        if self.active_plan and self.active_plan in self.plans:
            return self.plans[self.active_plan]
        return None

    def add_phase(self, name: str, description: str = "",
                  priority: int = 5, estimated_effort: float = 1.0,
                  depends_on: list = None, actions: list = None) -> str:
        """Agrega una fase al plan activo."""
        plan = self.get_active_plan()
        if not plan:
            return ""

        phase = Phase(name=name, description=description,
                      priority=priority, estimated_effort=estimated_effort)
        if actions:
            phase.actions = actions[:20]

        phase_id = plan.add_phase(phase)

        # Agregar dependencias
        if depends_on:
            for dep_name in depends_on:
                dep_id = self._find_phase_id(plan, dep_name)
                if dep_id:
                    plan.add_dependency(phase_id, dep_id)

        return phase_id

    def add_milestone(self, name: str, phase_names: list = None,
                      description: str = "") -> str:
        """Agrega un milestone al plan activo."""
        plan = self.get_active_plan()
        if not plan:
            return ""

        target_ids = []
        if phase_names:
            for pname in phase_names:
                pid = self._find_phase_id(plan, pname)
                if pid:
                    target_ids.append(pid)

        ms = Milestone(name=name, target_phases=target_ids,
                       description=description)
        return plan.add_milestone(ms)

    def complete_phase(self, phase_name: str) -> dict:
        """Marca una fase como completada."""
        plan = self.get_active_plan()
        if not plan:
            return {"success": False, "reason": "no active plan"}

        pid = self._find_phase_id(plan, phase_name)
        if not pid:
            return {"success": False, "reason": "phase not found"}

        phase = plan.phases[pid]
        phase.complete()
        self.total_phases_completed += 1

        # Verificar milestones
        newly_reached = plan.check_milestones()
        self.total_milestones_reached += len(newly_reached)

        # Verificar si el plan está completo
        plan_complete = plan.overall_progress >= 1.0

        return {
            "success": True,
            "phase": phase.name,
            "milestones_reached": [m.name for m in newly_reached],
            "plan_complete": plan_complete,
            "overall_progress": plan.overall_progress,
        }

    def update_phase_progress(self, phase_name: str, progress: float) -> bool:
        """Actualiza el progreso de una fase."""
        plan = self.get_active_plan()
        if not plan:
            return False

        pid = self._find_phase_id(plan, phase_name)
        if not pid:
            return False

        phase = plan.phases[pid]
        phase.update_progress(progress)

        if phase.status == "completed":
            self.total_phases_completed += 1
            plan.check_milestones()

        return True

    def block_phase(self, phase_name: str, reason: str = "") -> bool:
        """Bloquea una fase."""
        plan = self.get_active_plan()
        if not plan:
            return False

        pid = self._find_phase_id(plan, phase_name)
        if not pid:
            return False

        plan.phases[pid].block(reason)
        return True

    def adapt(self, feedback: dict = None) -> list:
        """Adapta prioridades del plan activo."""
        plan = self.get_active_plan()
        if not plan:
            return []
        return self.scheduler.adapt(plan, feedback)

    def suggest_next(self) -> list:
        """Sugiere próximas fases a iniciar."""
        plan = self.get_active_plan()
        if not plan:
            return []
        return self.scheduler.suggest_next(plan)

    def get_context_for_prompt(self, user_input: str = "",
                               max_chars: int = 500) -> str:
        """Genera contexto del plan activo para inyectar en prompt."""
        plan = self.get_active_plan()
        if not self.enabled or not plan or not plan.phases:
            return ""

        lines = [f"[PLAN ESTRATÉGICO: {self.active_plan}]"]
        lines.append(f"Progreso: {plan.overall_progress:.0%}")

        # Fases en progreso
        in_progress = plan.get_in_progress()
        if in_progress:
            lines.append("En progreso:")
            for p in in_progress[:3]:
                lines.append(f"  • {p.name} ({p.progress:.0%})")

        # Próximas fases listas
        ready = plan.get_ready_phases()
        if ready:
            lines.append("Listas:")
            for p in ready[:3]:
                lines.append(f"  → {p.name} (prioridad {p.priority})")

        # Bloqueadas
        blocked = plan.get_blocked_phases()
        if blocked:
            lines.append(f"Bloqueadas: {len(blocked)}")

        result = "\n".join(lines)
        return result[:max_chars]

    def auto_track(self, user_input: str, response: str):
        """Auto-tracking de progreso por keywords en la conversación."""
        plan = self.get_active_plan()
        if not plan or not plan.phases:
            return

        input_lower = user_input.lower() + " " + response.lower()

        # Keywords de completitud
        completion_keywords = ["terminado", "completado", "listo", "hecho",
                               "finished", "completed", "done"]

        # Keywords de progreso
        progress_keywords = ["avanzando", "progresando", "working on",
                             "implementando", "desarrollando"]

        # Keywords de bloqueo
        block_keywords = ["bloqueado", "no puedo", "error", "fallo",
                          "blocked", "stuck"]

        for phase in plan.phases.values():
            name_in_text = phase.name in input_lower

            if not name_in_text:
                continue

            if any(kw in input_lower for kw in completion_keywords):
                if phase.status != "completed":
                    phase.complete()
                    self.total_phases_completed += 1
                    plan.check_milestones()
            elif any(kw in input_lower for kw in block_keywords):
                if phase.status not in ("completed", "blocked"):
                    phase.block("detectado por auto-tracking")
            elif any(kw in input_lower for kw in progress_keywords):
                if phase.status in ("pending", "ready"):
                    phase.start()
                if phase.progress < 0.5:
                    phase.update_progress(phase.progress + 0.1)

    def get_stats(self) -> dict:
        plan = self.get_active_plan()
        plan_info = {}
        if plan:
            plan_info = {
                "phases": len(plan.phases),
                "milestones": len(plan.milestones),
                "progress": round(plan.overall_progress, 3),
                "completed": len([p for p in plan.phases.values()
                                  if p.status == "completed"]),
                "in_progress": len(plan.get_in_progress()),
                "blocked": len(plan.get_blocked_phases()),
            }

        return {
            "total_plans": len(self.plans),
            "total_created": self.total_plans_created,
            "total_phases_completed": self.total_phases_completed,
            "total_milestones_reached": self.total_milestones_reached,
            "active_plan": self.active_plan or "ninguno",
            "active_plan_info": plan_info,
        }

    def status(self) -> str:
        plan = self.get_active_plan()
        if not plan:
            return "Sin plan activo"

        phases = len(plan.phases)
        completed = len([p for p in plan.phases.values()
                         if p.status == "completed"])
        in_prog = len(plan.get_in_progress())
        blocked = len(plan.get_blocked_phases())

        return (f"Plan: {self.active_plan} | "
                f"Fases: {completed}/{phases} completadas | "
                f"En progreso: {in_prog} | Bloqueadas: {blocked} | "
                f"Progreso: {plan.overall_progress:.0%}")

    def generate_report(self) -> str:
        lines = ["=== STRATEGIC PLANNER REPORT ==="]
        lines.append(f"Planes creados: {self.total_plans_created}")
        lines.append(f"Planes almacenados: {len(self.plans)}")
        lines.append(f"Fases completadas total: {self.total_phases_completed}")
        lines.append(f"Milestones alcanzados: {self.total_milestones_reached}")

        plan = self.get_active_plan()
        if plan:
            lines.append(f"\n--- Plan activo: {self.active_plan} ---")
            lines.append(f"Progreso total: {plan.overall_progress:.0%}")

            # Ordenar por topología
            topo = plan.topological_sort()
            if topo:
                lines.append("\nFases (orden de dependencias):")
                for pid in topo:
                    phase = plan.phases.get(pid)
                    if not phase:
                        continue
                    status_icon = {
                        "pending": "○",
                        "ready": "◎",
                        "in_progress": "◉",
                        "completed": "●",
                        "blocked": "✗",
                        "skipped": "—",
                    }.get(phase.status, "?")
                    deps = ""
                    if phase.prerequisites:
                        dep_names = [plan.phases[d].name
                                     for d in phase.prerequisites
                                     if d in plan.phases]
                        if dep_names:
                            deps = f" (depende: {', '.join(dep_names)})"
                    lines.append(
                        f"  {status_icon} {phase.name} | "
                        f"prioridad={phase.priority} | "
                        f"progreso={phase.progress:.0%}{deps}"
                    )
                    if phase.actions:
                        for action in phase.actions[:3]:
                            lines.append(f"      → {action}")

            # Milestones
            if plan.milestones:
                lines.append("\nMilestones:")
                for ms in plan.milestones.values():
                    icon = "✓" if ms.reached else "○"
                    lines.append(f"  {icon} {ms.name}")

            # Camino crítico
            critical = plan.get_critical_path()
            if len(critical) > 1:
                names = [plan.phases[pid].name for pid in critical
                         if pid in plan.phases]
                lines.append(f"\nCamino crítico: {' → '.join(names)}")

            # Estimación de tiempo restante
            remaining = self.scheduler.estimate_completion(plan)
            if remaining > 0:
                lines.append(f"Tiempo estimado restante: {remaining:.1f}h")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_plans_created": self.total_plans_created,
            "total_phases_completed": self.total_phases_completed,
            "total_milestones_reached": self.total_milestones_reached,
            "active_plan": self.active_plan,
            "plans": {name: plan.to_dict() for name, plan in self.plans.items()},
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
            self.total_plans_created = data.get("total_plans_created", 0)
            self.total_phases_completed = data.get("total_phases_completed", 0)
            self.total_milestones_reached = data.get("total_milestones_reached", 0)
            self.active_plan = data.get("active_plan")

            for name, plan_data in data.get("plans", {}).items():
                plan = PlanGraph()
                plan.load_dict(plan_data)
                self.plans[name] = plan
        except Exception:
            pass

    def clear(self):
        self.plans = {}
        self.active_plan = None
        self.total_plans_created = 0
        self.total_phases_completed = 0
        self.total_milestones_reached = 0

    def _find_phase_id(self, plan: PlanGraph, name: str) -> str:
        """Busca una fase por nombre (exacto o parcial)."""
        name_lower = name.lower().strip()
        # Exacto
        for pid, phase in plan.phases.items():
            if phase.name == name_lower:
                return pid
        # Parcial
        for pid, phase in plan.phases.items():
            if name_lower in phase.name or phase.name in name_lower:
                return pid
        # Por ID directo
        if name_lower in plan.phases:
            return name_lower
        return ""

    def _evict_plans(self):
        """Elimina planes más antiguos completados."""
        if len(self.plans) <= self.max_plans:
            return
        # Priorizar eliminar planes 100% completados
        completed_plans = [
            (name, plan) for name, plan in self.plans.items()
            if plan.overall_progress >= 1.0 and name != self.active_plan
        ]
        completed_plans.sort(
            key=lambda x: max((p.completed_at or 0) for p in x[1].phases.values()) if x[1].phases else 0
        )
        for name, _ in completed_plans:
            if len(self.plans) <= self.max_plans:
                break
            del self.plans[name]
