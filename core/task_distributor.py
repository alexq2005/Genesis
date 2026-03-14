"""
GENESIS — Task Distributor (v4.4)

Distribución de tareas: Genesis gestiona workers con capacidad variable,
asigna tareas por prioridad y balancea la carga entre nodos disponibles.

Componentes:
- WorkerNode: nodo de trabajo con capacidad, carga y estado
- TaskItem: tarea con payload, prioridad y asignación
- LoadBalancer: asigna tareas al worker con menor carga
- TaskDistributor: coordinador con registro de workers y persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict, deque


class WorkerNode:
    """Un nodo de trabajo con capacidad y carga."""

    VALID_STATUSES = ("idle", "busy", "offline")

    def __init__(self, worker_id: str = None, capacity: float = 1.0,
                 name: str = ""):
        self.worker_id = worker_id or hashlib.md5(
            f"worker:{name}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.name = name or self.worker_id
        self.capacity = max(0.0, min(1.0, capacity))
        self.current_load = 0.0
        self.status = "idle"
        self.last_heartbeat = time.time()
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.created_at = time.time()
        self.assigned_task_ids = []  # current task IDs

    @property
    def load_ratio(self) -> float:
        """Ratio de carga actual vs capacidad."""
        if self.capacity <= 0:
            return 1.0
        return min(1.0, self.current_load / self.capacity)

    @property
    def available(self) -> bool:
        """Worker disponible para recibir tareas."""
        return (self.status != "offline" and
                self.load_ratio < 0.95 and
                self.is_alive)

    @property
    def is_alive(self) -> bool:
        """Worker vivo (heartbeat reciente, < 5 minutos)."""
        return (time.time() - self.last_heartbeat) < 300

    def heartbeat(self):
        """Actualiza el heartbeat."""
        self.last_heartbeat = time.time()
        if self.status == "offline":
            self.status = "idle"

    def assign_task(self, task_id: str, load_cost: float = 0.1):
        """Asigna una tarea a este worker."""
        self.assigned_task_ids.append(task_id)
        self.current_load = min(1.0, self.current_load + load_cost)
        self.status = "busy" if self.load_ratio > 0.5 else "idle"

    def complete_task(self, task_id: str, load_cost: float = 0.1):
        """Marca una tarea como completada."""
        if task_id in self.assigned_task_ids:
            self.assigned_task_ids.remove(task_id)
        self.current_load = max(0.0, self.current_load - load_cost)
        self.tasks_completed += 1
        self.status = "idle" if self.load_ratio < 0.5 else "busy"

    def fail_task(self, task_id: str, load_cost: float = 0.1):
        """Marca una tarea como fallida."""
        if task_id in self.assigned_task_ids:
            self.assigned_task_ids.remove(task_id)
        self.current_load = max(0.0, self.current_load - load_cost)
        self.tasks_failed += 1
        self.status = "idle" if self.load_ratio < 0.5 else "busy"

    def to_dict(self) -> dict:
        return {
            "id": self.worker_id,
            "name": self.name,
            "capacity": round(self.capacity, 4),
            "current_load": round(self.current_load, 4),
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "created_at": self.created_at,
            "assigned_task_ids": self.assigned_task_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerNode":
        worker = cls(
            worker_id=data.get("id"),
            capacity=data.get("capacity", 1.0),
            name=data.get("name", ""),
        )
        worker.current_load = data.get("current_load", 0.0)
        worker.status = data.get("status", "idle")
        worker.last_heartbeat = data.get("last_heartbeat", time.time())
        worker.tasks_completed = data.get("tasks_completed", 0)
        worker.tasks_failed = data.get("tasks_failed", 0)
        worker.created_at = data.get("created_at", time.time())
        worker.assigned_task_ids = data.get("assigned_task_ids", [])
        return worker


class TaskItem:
    """Una tarea para distribuir."""

    VALID_STATUSES = ("queued", "running", "done", "failed")

    def __init__(self, payload: str, priority: int = 5,
                 task_id: str = None):
        self.task_id = task_id or hashlib.md5(
            f"task:{payload[:50]}:{time.time()}".encode()
        ).hexdigest()[:10]
        self.payload = payload[:1000]
        self.priority = max(1, min(10, priority))
        self.assigned_to = ""       # worker_id
        self.status = "queued"
        self.created_at = time.time()
        self.started_at = 0.0
        self.completed_at = 0.0
        self.result = ""
        self.retries = 0
        self.max_retries = 3

    @property
    def duration(self) -> float:
        """Duración de ejecución en segundos."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return time.time() - self.started_at
        return 0.0

    @property
    def can_retry(self) -> bool:
        return self.retries < self.max_retries

    def assign(self, worker_id: str):
        """Asigna a un worker."""
        self.assigned_to = worker_id
        self.status = "running"
        self.started_at = time.time()

    def complete(self, result: str = ""):
        """Marca como completada."""
        self.status = "done"
        self.completed_at = time.time()
        self.result = result[:500]

    def fail(self, reason: str = ""):
        """Marca como fallida."""
        self.retries += 1
        if self.can_retry:
            self.status = "queued"
            self.assigned_to = ""
        else:
            self.status = "failed"
            self.completed_at = time.time()
        self.result = reason[:500]

    def to_dict(self) -> dict:
        return {
            "id": self.task_id,
            "payload": self.payload,
            "priority": self.priority,
            "assigned_to": self.assigned_to,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "retries": self.retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskItem":
        task = cls(
            payload=data.get("payload", ""),
            priority=data.get("priority", 5),
            task_id=data.get("id"),
        )
        task.assigned_to = data.get("assigned_to", "")
        task.status = data.get("status", "queued")
        task.created_at = data.get("created_at", time.time())
        task.started_at = data.get("started_at", 0.0)
        task.completed_at = data.get("completed_at", 0.0)
        task.result = data.get("result", "")
        task.retries = data.get("retries", 0)
        return task


class LoadBalancer:
    """Balancea carga asignando tareas al worker con menor carga."""

    def __init__(self):
        self._round_robin_index = 0

    def select_worker(self, workers: list, task: TaskItem = None) -> WorkerNode:
        """
        Selecciona el mejor worker para una tarea.
        Estrategia: menor load_ratio. Fallback: round-robin.
        """
        available = [w for w in workers if w.available]
        if not available:
            return None

        # Primary: worker con menor load_ratio
        by_load = sorted(available, key=lambda w: w.load_ratio)
        # If multiple workers with same load, use round-robin
        min_load = by_load[0].load_ratio
        candidates = [w for w in by_load if w.load_ratio <= min_load + 0.05]

        if len(candidates) == 1:
            return candidates[0]

        # Round-robin entre candidatos con carga similar
        idx = self._round_robin_index % len(candidates)
        self._round_robin_index += 1
        return candidates[idx]

    def get_load_distribution(self, workers: list) -> dict:
        """Retorna distribución de carga."""
        if not workers:
            return {"workers": 0, "avg_load": 0, "max_load": 0}
        loads = [w.load_ratio for w in workers]
        return {
            "workers": len(workers),
            "avg_load": round(sum(loads) / len(loads), 3),
            "max_load": round(max(loads), 3),
            "min_load": round(min(loads), 3),
            "available": sum(1 for w in workers if w.available),
        }


class TaskDistributor:
    """
    Coordinador de distribución de tareas.
    Gestiona workers, cola de tareas, y asignación con balanceo.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/task_distributor")
        self.data_file = self.base_dir / "task_distributor_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.workers = {}          # worker_id -> WorkerNode
        self.tasks = {}            # task_id -> TaskItem
        self.task_queue = deque(maxlen=500)  # queue of task_ids by priority
        self.balancer = LoadBalancer()
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.enabled = True

        self._load()

    def register_worker(self, name: str = "", capacity: float = 1.0,
                        worker_id: str = None) -> str:
        """Registra un nuevo worker."""
        worker = WorkerNode(
            worker_id=worker_id,
            capacity=capacity,
            name=name,
        )
        self.workers[worker.worker_id] = worker
        return worker.worker_id

    def submit_task(self, payload: str, priority: int = 5) -> str:
        """Envía una tarea a la cola."""
        task = TaskItem(payload=payload, priority=priority)
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)
        self.total_tasks += 1
        return task.task_id

    def assign_tasks(self) -> list:
        """
        Asigna tareas pendientes a workers disponibles.
        Retorna lista de (task_id, worker_id) asignados.
        """
        if not self.enabled:
            return []

        # Actualizar workers offline
        for worker in self.workers.values():
            if not worker.is_alive and worker.status != "offline":
                worker.status = "offline"

        # Obtener tareas pendientes ordenadas por prioridad
        pending = []
        for tid in list(self.task_queue):
            task = self.tasks.get(tid)
            if task and task.status == "queued":
                pending.append(task)
        pending.sort(key=lambda t: t.priority, reverse=True)

        assignments = []
        workers_list = list(self.workers.values())

        for task in pending:
            worker = self.balancer.select_worker(workers_list, task)
            if not worker:
                break

            task.assign(worker.worker_id)
            load_cost = 0.1 + (task.priority / 100.0)
            worker.assign_task(task.task_id, load_cost)

            if task.task_id in self.task_queue:
                self.task_queue.remove(task.task_id)

            assignments.append((task.task_id, worker.worker_id))

        return assignments

    def complete_task(self, task_id: str, result: str = "") -> bool:
        """Marca una tarea como completada."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        worker = self.workers.get(task.assigned_to)
        task.complete(result)
        self.completed_tasks += 1

        if worker:
            load_cost = 0.1 + (task.priority / 100.0)
            worker.complete_task(task_id, load_cost)

        return True

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """Marca una tarea como fallida."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        worker = self.workers.get(task.assigned_to)
        task.fail(reason)

        if worker:
            load_cost = 0.1 + (task.priority / 100.0)
            worker.fail_task(task_id, load_cost)

        if task.status == "queued":
            # Re-enqueue for retry
            self.task_queue.append(task_id)
        else:
            self.failed_tasks += 1

        return True

    def get_worker_status(self, worker_id: str = None) -> dict:
        """Obtiene estado de un worker o todos."""
        if worker_id:
            worker = self.workers.get(worker_id)
            if not worker:
                return {}
            return worker.to_dict()

        return {
            wid: w.to_dict() for wid, w in self.workers.items()
        }

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de distribución para el prompt."""
        if not self.enabled or not self.workers:
            return ""

        dist = self.balancer.get_load_distribution(
            list(self.workers.values())
        )
        pending = sum(1 for t in self.tasks.values() if t.status == "queued")
        running = sum(1 for t in self.tasks.values() if t.status == "running")

        if pending == 0 and running == 0:
            return ""

        lines = ["[DISTRIBUCION DE TAREAS]"]
        lines.append(
            f"Workers: {dist['available']}/{dist['workers']} disponibles, "
            f"carga promedio: {dist['avg_load']:.0%}"
        )
        lines.append(f"Tareas: {pending} en cola, {running} ejecutando")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_workers": len(self.workers),
            "available_workers": sum(
                1 for w in self.workers.values() if w.available
            ),
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "queued": sum(1 for t in self.tasks.values() if t.status == "queued"),
            "running": sum(1 for t in self.tasks.values() if t.status == "running"),
        }

    def status(self) -> str:
        available = sum(1 for w in self.workers.values() if w.available)
        queued = sum(1 for t in self.tasks.values() if t.status == "queued")
        return (f"Workers: {available}/{len(self.workers)} | "
                f"Tasks: {self.total_tasks} total, "
                f"{queued} en cola, "
                f"{self.completed_tasks} completadas")

    def generate_report(self) -> str:
        lines = ["=== TASK DISTRIBUTOR REPORT ==="]
        lines.append(f"Workers registrados: {len(self.workers)}")
        lines.append(f"Total tareas: {self.total_tasks}")
        lines.append(f"Completadas: {self.completed_tasks}")
        lines.append(f"Fallidas: {self.failed_tasks}")

        if self.workers:
            lines.append(f"\nWorkers:")
            for worker in sorted(self.workers.values(),
                                 key=lambda w: w.tasks_completed, reverse=True):
                alive = "ALIVE" if worker.is_alive else "DEAD"
                lines.append(
                    f"  {worker.name} [{worker.status}/{alive}]: "
                    f"carga={worker.load_ratio:.0%}, "
                    f"completadas={worker.tasks_completed}, "
                    f"fallidas={worker.tasks_failed}"
                )

        # Task status breakdown
        status_counts = defaultdict(int)
        for task in self.tasks.values():
            status_counts[task.status] += 1
        if status_counts:
            lines.append(f"\nTareas por estado:")
            for status, count in sorted(status_counts.items()):
                lines.append(f"  {status}: {count}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "workers": {wid: w.to_dict() for wid, w in self.workers.items()},
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "queue": list(self.task_queue),
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
            self.total_tasks = data.get("total_tasks", 0)
            self.completed_tasks = data.get("completed_tasks", 0)
            self.failed_tasks = data.get("failed_tasks", 0)
            for wid, wdata in data.get("workers", {}).items():
                self.workers[wid] = WorkerNode.from_dict(wdata)
            for tid, tdata in data.get("tasks", {}).items():
                self.tasks[tid] = TaskItem.from_dict(tdata)
            for tid in data.get("queue", []):
                if tid in self.tasks:
                    self.task_queue.append(tid)
        except Exception:
            pass

    def clear(self):
        self.workers = {}
        self.tasks = {}
        self.task_queue = deque(maxlen=500)
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
