"""
GENESIS — Schedule Optimizer (v4.1)

Optimización de agendas y workflows: Genesis gestiona items
con prioridades, deadlines y dependencias, resuelve conflictos
y sugiere reordenamiento óptimo usando earliest-deadline-first.

Componentes:
- ScheduleItem: tarea con prioridad, duración, deadline y dependencias
- ScheduleSlot: slot temporal asignado a un item
- Scheduler: algoritmo EDF con detección de conflictos
- ScheduleOptimizer: coordinador con persistencia y optimización
"""
import time
import json
from pathlib import Path
from collections import defaultdict


class ScheduleItem:
    """Una tarea planificable con prioridad, duración y dependencias."""

    VALID_STATUSES = ("pending", "in_progress", "done")

    def __init__(self, name: str, priority: int = 5,
                 estimated_duration_minutes: float = 30.0,
                 deadline: float = None, dependencies: list = None,
                 status: str = "pending"):
        self.name = name.strip()
        self.priority = max(1, min(10, priority))
        self.estimated_duration_minutes = max(1.0, estimated_duration_minutes)
        self.deadline = deadline          # timestamp o None
        self.dependencies = list(dependencies) if dependencies else []
        self.status = status if status in self.VALID_STATUSES else "pending"
        self.created_at = time.time()
        self.completed_at = None

    @property
    def is_overdue(self) -> bool:
        """Verifica si la tarea pasó su deadline."""
        if self.deadline is None or self.status == "done":
            return False
        return time.time() > self.deadline

    @property
    def urgency_score(self) -> float:
        """Score de urgencia combinando prioridad y proximidad al deadline."""
        base = self.priority / 10.0
        if self.deadline is None:
            return base * 0.5  # Sin deadline = menos urgente
        remaining = self.deadline - time.time()
        if remaining <= 0:
            return 1.0  # Overdue = máxima urgencia
        # Urgencia crece exponencialmente al acercarse al deadline
        hours_left = remaining / 3600.0
        deadline_factor = 1.0 / (1.0 + hours_left * 0.1)
        return min(1.0, base * 0.4 + deadline_factor * 0.6)

    def mark_done(self):
        """Marca la tarea como completada."""
        self.status = "done"
        self.completed_at = time.time()

    def mark_in_progress(self):
        """Marca la tarea como en progreso."""
        self.status = "in_progress"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "priority": self.priority,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "deadline": self.deadline,
            "dependencies": self.dependencies,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleItem":
        item = cls(
            name=data.get("name", ""),
            priority=data.get("priority", 5),
            estimated_duration_minutes=data.get("estimated_duration_minutes", 30.0),
            deadline=data.get("deadline"),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "pending"),
        )
        item.created_at = data.get("created_at", time.time())
        item.completed_at = data.get("completed_at")
        return item


class ScheduleSlot:
    """Un slot temporal asignado a un item en el schedule."""

    def __init__(self, start_time: float, end_time: float,
                 item_name: str, conflict: bool = False):
        self.start_time = start_time
        self.end_time = end_time
        self.item_name = item_name
        self.conflict = conflict

    @property
    def duration_minutes(self) -> float:
        return (self.end_time - self.start_time) / 60.0

    def overlaps_with(self, other: "ScheduleSlot") -> bool:
        """Verifica si dos slots se solapan."""
        return (self.start_time < other.end_time and
                self.end_time > other.start_time)

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "item_name": self.item_name,
            "conflict": self.conflict,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleSlot":
        return cls(
            start_time=data.get("start_time", 0),
            end_time=data.get("end_time", 0),
            item_name=data.get("item_name", ""),
            conflict=data.get("conflict", False),
        )


class Scheduler:
    """
    Algoritmo de planificación earliest-deadline-first
    con resolución de dependencias y detección de conflictos.
    """

    def schedule_edf(self, items: list, start_time: float = None) -> list:
        """
        Planifica items usando earliest-deadline-first.
        Items sin deadline van al final, ordenados por prioridad descendente.
        Respeta dependencias: un item no se programa hasta que sus deps estén antes.
        """
        if not items:
            return []

        current_time = start_time or time.time()
        pending = [i for i in items if i.status != "done"]
        scheduled = []
        scheduled_names = set()
        max_iterations = len(pending) * len(pending)
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1
            # Filtrar items cuyas dependencias ya están programadas
            ready = []
            for item in pending:
                deps_met = all(d in scheduled_names for d in item.dependencies)
                if deps_met:
                    ready.append(item)

            if not ready:
                # Dependencias cíclicas o imposibles: forzar programación
                ready = list(pending)

            # Ordenar: deadline first (None = infinito), luego por prioridad desc
            def sort_key(item):
                dl = item.deadline if item.deadline is not None else float('inf')
                return (dl, -item.priority)

            ready.sort(key=sort_key)

            chosen = ready[0]
            duration_secs = chosen.estimated_duration_minutes * 60.0
            slot = ScheduleSlot(
                start_time=current_time,
                end_time=current_time + duration_secs,
                item_name=chosen.name,
                conflict=False,
            )

            # Detectar si excede deadline
            if chosen.deadline is not None and slot.end_time > chosen.deadline:
                slot.conflict = True

            scheduled.append(slot)
            scheduled_names.add(chosen.name)
            current_time = slot.end_time
            pending.remove(chosen)

        return scheduled

    def detect_conflicts(self, slots: list, items: dict) -> list:
        """
        Detecta conflictos en el schedule:
        - Slots que se solapan
        - Items que exceden su deadline
        - Dependencias violadas (dep programada después del item)
        """
        conflicts = []

        # Solapamiento
        for i, slot_a in enumerate(slots):
            for j, slot_b in enumerate(slots):
                if i >= j:
                    continue
                if slot_a.overlaps_with(slot_b):
                    conflicts.append({
                        "type": "overlap",
                        "items": [slot_a.item_name, slot_b.item_name],
                        "detail": f"{slot_a.item_name} y {slot_b.item_name} se solapan",
                    })

        # Deadline exceeded
        for slot in slots:
            item = items.get(slot.item_name)
            if item and item.deadline is not None and slot.end_time > item.deadline:
                overdue_min = (slot.end_time - item.deadline) / 60.0
                conflicts.append({
                    "type": "deadline_exceeded",
                    "items": [slot.item_name],
                    "detail": f"{slot.item_name} excede deadline por {overdue_min:.0f}min",
                })

        # Dependency violations
        name_order = {slot.item_name: idx for idx, slot in enumerate(slots)}
        for slot in slots:
            item = items.get(slot.item_name)
            if not item:
                continue
            for dep in item.dependencies:
                if dep in name_order and name_order[dep] > name_order[slot.item_name]:
                    conflicts.append({
                        "type": "dependency_violation",
                        "items": [slot.item_name, dep],
                        "detail": f"{slot.item_name} depende de {dep} pero está programado antes",
                    })

        return conflicts

    def suggest_reorder(self, items: list) -> list:
        """Sugiere orden óptimo como lista de nombres."""
        slots = self.schedule_edf(items)
        return [slot.item_name for slot in slots]


class ScheduleOptimizer:
    """
    Coordinador de optimización de agendas.
    Gestiona items con prioridades, deadlines y dependencias,
    optimiza el orden y detecta conflictos.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/schedule")
        self.data_file = self.base_dir / "schedule_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.items = {}            # name -> ScheduleItem
        self.slots = []            # Último schedule generado
        self.scheduler = Scheduler()
        self.total_items = 0
        self.total_optimizations = 0
        self.conflicts_resolved = 0
        self.enabled = True

        self._load()

    def add_item(self, name: str, priority: int = 5,
                 duration: float = 30.0, deadline: float = None,
                 dependencies: list = None) -> ScheduleItem:
        """Agrega un item al schedule."""
        if not self.enabled or not name:
            return None

        item = ScheduleItem(
            name=name,
            priority=priority,
            estimated_duration_minutes=duration,
            deadline=deadline,
            dependencies=dependencies,
        )
        self.items[name] = item
        self.total_items += 1
        return item

    def remove_item(self, name: str) -> bool:
        """Elimina un item del schedule."""
        if name in self.items:
            del self.items[name]
            return True
        return False

    def complete_item(self, name: str) -> bool:
        """Marca un item como completado."""
        item = self.items.get(name)
        if item:
            item.mark_done()
            return True
        return False

    def optimize(self) -> list:
        """Genera schedule optimizado con todos los items pendientes."""
        if not self.enabled:
            return []

        pending = [i for i in self.items.values() if i.status != "done"]
        if not pending:
            return []

        self.slots = self.scheduler.schedule_edf(pending)
        self.total_optimizations += 1
        return self.slots

    def detect_conflicts(self) -> list:
        """Detecta conflictos en el schedule actual."""
        if not self.slots:
            self.optimize()
        return self.scheduler.detect_conflicts(self.slots, self.items)

    def suggest_reorder(self) -> list:
        """Retorna orden optimizado como lista de nombres."""
        pending = [i for i in self.items.values() if i.status != "done"]
        return self.scheduler.suggest_reorder(pending)

    def resolve_conflicts(self) -> int:
        """Intenta resolver conflictos re-optimizando el schedule."""
        conflicts_before = len(self.detect_conflicts())
        if conflicts_before == 0:
            return 0

        # Re-optimizar: ya ordena por EDF y respeta dependencias
        self.optimize()
        conflicts_after = len(self.detect_conflicts())
        resolved = max(0, conflicts_before - conflicts_after)
        self.conflicts_resolved += resolved
        return resolved

    def get_pending(self) -> list:
        """Retorna items pendientes ordenados por urgencia."""
        pending = [i for i in self.items.values() if i.status != "done"]
        return sorted(pending, key=lambda i: i.urgency_score, reverse=True)

    def get_overdue(self) -> list:
        """Retorna items que excedieron su deadline."""
        return [i for i in self.items.values() if i.is_overdue]

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de schedule para inyectar en prompt."""
        if not self.enabled:
            return ""

        pending = self.get_pending()
        if not pending:
            return ""

        lines = ["[SCHEDULE PENDIENTE]"]
        lines.append(f"Items pendientes: {len(pending)}")

        # Overdue
        overdue = self.get_overdue()
        if overdue:
            lines.append(f"VENCIDOS ({len(overdue)}):")
            for item in overdue[:3]:
                lines.append(f"  ! {item.name} (prioridad {item.priority})")

        # Próximos por urgencia
        top = [i for i in pending if i not in overdue][:3]
        if top:
            lines.append("Próximos:")
            for item in top:
                dur_str = f"{item.estimated_duration_minutes:.0f}min"
                dl_str = ""
                if item.deadline:
                    remaining = item.deadline - time.time()
                    if remaining > 0:
                        hours = remaining / 3600.0
                        dl_str = f", deadline en {hours:.1f}h"
                lines.append(f"  {item.name} ({dur_str}, p={item.priority}{dl_str})")

        # Sugerencia de orden
        order = self.suggest_reorder()
        if order:
            lines.append(f"Orden sugerido: {' > '.join(order[:5])}")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        pending = [i for i in self.items.values() if i.status != "done"]
        done = [i for i in self.items.values() if i.status == "done"]
        return {
            "total_items": self.total_items,
            "current_items": len(self.items),
            "pending": len(pending),
            "done": len(done),
            "overdue": len(self.get_overdue()),
            "total_optimizations": self.total_optimizations,
            "conflicts_resolved": self.conflicts_resolved,
        }

    def status(self) -> str:
        pending = len([i for i in self.items.values() if i.status != "done"])
        overdue = len(self.get_overdue())
        return (f"Items: {len(self.items)} ({pending} pendientes) | "
                f"Vencidos: {overdue} | "
                f"Optimizaciones: {self.total_optimizations} | "
                f"Conflictos resueltos: {self.conflicts_resolved}")

    def generate_report(self) -> str:
        lines = ["=== SCHEDULE OPTIMIZER REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total items registrados: {stats['total_items']}")
        lines.append(f"Items actuales: {stats['current_items']}")
        lines.append(f"Pendientes: {stats['pending']}")
        lines.append(f"Completados: {stats['done']}")
        lines.append(f"Vencidos: {stats['overdue']}")
        lines.append(f"Optimizaciones: {stats['total_optimizations']}")
        lines.append(f"Conflictos resueltos: {stats['conflicts_resolved']}")

        # Items pendientes por urgencia
        pending = self.get_pending()
        if pending:
            lines.append(f"\nItems pendientes (por urgencia):")
            for item in pending[:10]:
                dl_str = ""
                if item.deadline:
                    remaining = item.deadline - time.time()
                    if remaining > 0:
                        dl_str = f" deadline={remaining / 3600:.1f}h"
                    else:
                        dl_str = " VENCIDO"
                deps_str = f" deps=[{', '.join(item.dependencies)}]" if item.dependencies else ""
                lines.append(
                    f"  {item.name}: p={item.priority} "
                    f"dur={item.estimated_duration_minutes:.0f}min"
                    f"{dl_str}{deps_str} urgencia={item.urgency_score:.0%}"
                )

        # Orden sugerido
        order = self.suggest_reorder()
        if order:
            lines.append(f"\nOrden sugerido:")
            for i, name in enumerate(order, 1):
                lines.append(f"  {i}. {name}")

        # Conflictos
        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append(f"\nConflictos detectados ({len(conflicts)}):")
            for c in conflicts[:5]:
                lines.append(f"  [{c['type']}] {c['detail']}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_items": self.total_items,
            "total_optimizations": self.total_optimizations,
            "conflicts_resolved": self.conflicts_resolved,
            "items": {n: i.to_dict() for n, i in self.items.items()},
            "slots": [s.to_dict() for s in self.slots],
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
            self.total_items = data.get("total_items", 0)
            self.total_optimizations = data.get("total_optimizations", 0)
            self.conflicts_resolved = data.get("conflicts_resolved", 0)
            for name, item_data in data.get("items", {}).items():
                self.items[name] = ScheduleItem.from_dict(item_data)
            for slot_data in data.get("slots", []):
                self.slots.append(ScheduleSlot.from_dict(slot_data))
        except Exception:
            pass

    def clear(self):
        self.items = {}
        self.slots = []
        self.total_items = 0
        self.total_optimizations = 0
        self.conflicts_resolved = 0
