"""
GENESIS Task Scheduler — Programacion de tareas periodicas tipo cron.

Problema:
Genesis tiene muchas acciones que deberian ejecutarse periodicamente
(health checks, backups, learning analysis, RAG reindex) pero no hay
un sistema centralizado para programarlas.

Solucion:
Un scheduler ligero que:
1. Registra tareas con intervalos (cada N segundos/minutos/horas)
2. Ejecuta tareas cuando llega su momento
3. Mantiene historial de ejecuciones con resultados
4. Se puede pausar/reanudar sin perder estado

Uso:
    scheduler = TaskScheduler()
    scheduler.add_task("health_check", check_fn, interval_seconds=60)
    scheduler.add_task("backup", backup_fn, interval_seconds=3600)
    scheduler.tick()  # Llamar en cada ciclo del loop principal
"""
import time
import json
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime


class ScheduledTask:
    """Una tarea programada para ejecucion periodica."""

    def __init__(self, name: str, callback: Optional[Callable] = None,
                 interval_seconds: float = 60.0,
                 description: str = "", enabled: bool = True):
        self.name = name
        self.callback = callback
        self.interval_seconds = max(1.0, interval_seconds)
        self.description = description
        self.enabled = enabled

        # Timing
        self.last_run: float = 0.0
        self.next_run: float = time.time() + interval_seconds
        self.created_at: float = time.time()

        # Stats
        self.run_count: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.last_result: str = ""
        self.last_error: str = ""
        self.last_duration_ms: float = 0.0
        self.total_duration_ms: float = 0.0

    def is_due(self) -> bool:
        """Verifica si la tarea debe ejecutarse ahora."""
        if not self.enabled:
            return False
        return time.time() >= self.next_run

    def execute(self) -> dict:
        """
        Ejecuta la tarea y actualiza stats.

        Returns:
            dict con resultado de la ejecucion
        """
        start = time.time()
        result = {
            "task": self.name,
            "timestamp": start,
            "success": False,
            "result": "",
            "error": "",
            "duration_ms": 0.0,
        }

        try:
            if self.callback:
                output = self.callback()
                result["result"] = str(output) if output else "OK"
                result["success"] = True
                self.success_count += 1
                self.last_result = result["result"]
            else:
                result["result"] = "No callback"
                result["success"] = True
                self.success_count += 1
        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            self.failure_count += 1
            self.last_error = str(e)

        elapsed = (time.time() - start) * 1000
        result["duration_ms"] = round(elapsed, 2)
        self.last_duration_ms = result["duration_ms"]
        self.total_duration_ms += result["duration_ms"]

        self.run_count += 1
        self.last_run = time.time()
        self.next_run = time.time() + self.interval_seconds

        return result

    def time_until_next(self) -> float:
        """Segundos hasta la proxima ejecucion."""
        return max(0.0, self.next_run - time.time())

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(
                self.success_count / self.run_count * 100, 1
            ) if self.run_count > 0 else 0.0,
            "avg_duration_ms": round(
                self.total_duration_ms / self.run_count, 2
            ) if self.run_count > 0 else 0.0,
            "last_duration_ms": self.last_duration_ms,
            "time_until_next": round(self.time_until_next(), 1),
        }

    def format_interval(self) -> str:
        """Formato legible del intervalo."""
        s = self.interval_seconds
        if s >= 3600:
            return f"{s/3600:.0f}h"
        elif s >= 60:
            return f"{s/60:.0f}m"
        return f"{s:.0f}s"


class ExecutionLog:
    """Historial de ejecuciones de tareas."""

    def __init__(self, max_entries: int = 200):
        self.entries: list[dict] = []
        self.max_entries = max_entries

    def add(self, entry: dict):
        """Agrega una entrada al log."""
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

    def get_recent(self, n: int = 20) -> list[dict]:
        """Ultimas N entradas."""
        return self.entries[-n:]

    def get_by_task(self, task_name: str, n: int = 10) -> list[dict]:
        """Entradas de una tarea especifica."""
        filtered = [e for e in self.entries if e.get("task") == task_name]
        return filtered[-n:]

    def get_failures(self, n: int = 20) -> list[dict]:
        """Ultimas N fallas."""
        failures = [e for e in self.entries if not e.get("success")]
        return failures[-n:]

    def get_stats(self) -> dict:
        """Estadisticas del log."""
        total = len(self.entries)
        successes = sum(1 for e in self.entries if e.get("success"))
        failures = total - successes
        return {
            "total_entries": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(
                successes / total * 100, 1
            ) if total > 0 else 0.0,
        }

    def clear(self):
        """Limpia el historial."""
        self.entries.clear()


class TaskScheduler:
    """
    Scheduler de tareas periodicas para Genesis.

    Registra tareas con intervalos y las ejecuta automaticamente
    cuando tick() es llamado en el loop principal.
    """

    def __init__(self, base_dir: str = ""):
        if not base_dir:
            base_dir = str(Path(__file__).parent.parent)
        self.base_dir = Path(base_dir)

        # Tareas registradas
        self.tasks: dict[str, ScheduledTask] = {}

        # Historial de ejecuciones
        self.log = ExecutionLog(max_entries=200)

        # Estado global
        self.enabled = True
        self.paused = False
        self.total_ticks = 0
        self.total_executions = 0
        self.started_at = time.time()

    def add_task(self, name: str, callback: Optional[Callable] = None,
                 interval_seconds: float = 60.0,
                 description: str = "", enabled: bool = True) -> str:
        """
        Registra una nueva tarea periodica.

        Args:
            name: Nombre unico de la tarea
            callback: Funcion a ejecutar
            interval_seconds: Intervalo entre ejecuciones
            description: Descripcion de la tarea
            enabled: Si la tarea esta activa

        Returns:
            Mensaje de confirmacion
        """
        if name in self.tasks:
            return f"Tarea '{name}' ya existe. Usa remove_task primero."

        task = ScheduledTask(
            name=name,
            callback=callback,
            interval_seconds=interval_seconds,
            description=description,
            enabled=enabled,
        )
        self.tasks[name] = task
        return f"Tarea '{name}' registrada (cada {task.format_interval()})"

    def remove_task(self, name: str) -> str:
        """Elimina una tarea."""
        if name not in self.tasks:
            return f"Tarea '{name}' no encontrada."
        del self.tasks[name]
        return f"Tarea '{name}' eliminada."

    def toggle_task(self, name: str) -> str:
        """Activa/desactiva una tarea."""
        if name not in self.tasks:
            return f"Tarea '{name}' no encontrada."
        task = self.tasks[name]
        task.enabled = not task.enabled
        state = "activada" if task.enabled else "desactivada"
        return f"Tarea '{name}': {state}"

    def run_task_now(self, name: str) -> str:
        """Ejecuta una tarea inmediatamente, sin esperar al intervalo."""
        if name not in self.tasks:
            return f"Tarea '{name}' no encontrada."

        task = self.tasks[name]
        result = task.execute()
        self.log.add(result)
        self.total_executions += 1

        if result["success"]:
            return f"Tarea '{name}' ejecutada OK ({result['duration_ms']}ms): {result['result'][:100]}"
        return f"Tarea '{name}' fallo: {result['error'][:100]}"

    def set_interval(self, name: str, seconds: float) -> str:
        """Cambia el intervalo de una tarea."""
        if name not in self.tasks:
            return f"Tarea '{name}' no encontrada."
        task = self.tasks[name]
        task.interval_seconds = max(1.0, seconds)
        task.next_run = time.time() + task.interval_seconds
        return f"Tarea '{name}': intervalo cambiado a {task.format_interval()}"

    def tick(self) -> list[dict]:
        """
        Revisa todas las tareas y ejecuta las que correspondan.

        Debe llamarse periodicamente desde el loop principal.

        Returns:
            Lista de resultados de tareas ejecutadas
        """
        self.total_ticks += 1

        if not self.enabled or self.paused:
            return []

        results = []
        for name, task in self.tasks.items():
            if task.is_due():
                result = task.execute()
                self.log.add(result)
                self.total_executions += 1
                results.append(result)

        return results

    def pause(self) -> str:
        """Pausa el scheduler (las tareas no se ejecutan)."""
        self.paused = True
        return "Scheduler pausado."

    def resume(self) -> str:
        """Reanuda el scheduler."""
        self.paused = False
        return "Scheduler reanudado."

    def toggle(self) -> str:
        """Activa/desactiva el scheduler globalmente."""
        self.enabled = not self.enabled
        state = "ACTIVADO" if self.enabled else "DESACTIVADO"
        return f"Scheduler: {state}"

    def get_upcoming(self, n: int = 10) -> list[dict]:
        """Proximas N tareas a ejecutarse."""
        upcoming = []
        for task in self.tasks.values():
            if task.enabled:
                upcoming.append({
                    "name": task.name,
                    "time_until": task.time_until_next(),
                    "interval": task.format_interval(),
                })
        upcoming.sort(key=lambda x: x["time_until"])
        return upcoming[:n]

    def get_task_list(self) -> str:
        """Formato lista de tareas para mostrar."""
        if not self.tasks:
            return "  No hay tareas programadas."

        lines = []
        for name, task in sorted(self.tasks.items()):
            icon = ">" if task.enabled else "x"
            next_in = f"{task.time_until_next():.0f}s"
            rate = f"{task.success_count}/{task.run_count}" if task.run_count > 0 else "0/0"
            lines.append(
                f"  [{icon}] {name:20s} cada {task.format_interval():>5s} | "
                f"next: {next_in:>6s} | runs: {rate}"
            )
            if task.description:
                lines.append(f"      {task.description}")
        return "\n".join(lines)

    def get_log_report(self, n: int = 15) -> str:
        """Reporte del historial de ejecuciones."""
        recent = self.log.get_recent(n)
        if not recent:
            return "  Sin ejecuciones registradas."

        lines = []
        for entry in recent:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
            status = "OK" if entry["success"] else "FAIL"
            dur = f"{entry['duration_ms']:.0f}ms"
            lines.append(f"  [{ts}] {entry['task']:20s} {status:4s} {dur:>8s}")
            if not entry["success"] and entry.get("error"):
                lines.append(f"           -> {entry['error'][:60]}")
        return "\n".join(lines)

    def get_full_report(self) -> str:
        """Reporte completo del scheduler."""
        uptime = time.time() - self.started_at
        uptime_str = f"{uptime/3600:.1f}h" if uptime >= 3600 else f"{uptime/60:.0f}m"

        lines = [
            "=== TASK SCHEDULER ===",
            f"  Estado: {'ACTIVO' if self.enabled else 'DESACTIVADO'}"
            f"{' (PAUSADO)' if self.paused else ''}",
            f"  Uptime: {uptime_str} | Ticks: {self.total_ticks} | "
            f"Ejecuciones: {self.total_executions}",
            f"  Tareas: {len(self.tasks)} registradas, "
            f"{sum(1 for t in self.tasks.values() if t.enabled)} activas",
            "",
            "  TAREAS:",
            self.get_task_list(),
        ]

        log_stats = self.log.get_stats()
        if log_stats["total_entries"] > 0:
            lines.append(f"\n  HISTORIAL (ultimas 10):")
            lines.append(self.get_log_report(10))
            lines.append(
                f"\n  Log: {log_stats['total_entries']} entradas, "
                f"{log_stats['success_rate']}% exito"
            )

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen breve para /status."""
        active = sum(1 for t in self.tasks.values() if t.enabled)
        total = len(self.tasks)
        state = "ON" if self.enabled and not self.paused else "OFF"
        if self.paused:
            state = "PAUSED"
        return (
            f"  Estado: {state} | Tareas: {active}/{total} | "
            f"Ejecuciones: {self.total_executions}"
        )
