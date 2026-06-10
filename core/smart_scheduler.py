"""
GENESIS Smart Scheduler — Programación de tareas persistente tipo cron.
Soporta: intervalos, diario, semanal. NLP en español e inglés.
Patrón cooperativo tick() — no necesita thread propio.
"""
import os
import re
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable
from difflib import SequenceMatcher


class SmartScheduler:
    """Scheduler persistente con parsing NLP."""

    # Mapeo de días en español/inglés a weekday (0=lunes)
    _DAYS_MAP = {
        "lun": 0, "lunes": 0, "mon": 0, "monday": 0,
        "mar": 1, "martes": 1, "tue": 1, "tuesday": 1,
        "mie": 2, "miér": 2, "miércoles": 2, "miercoles": 2,
        "wed": 2, "wednesday": 2,
        "jue": 3, "jueves": 3, "thu": 3, "thursday": 3,
        "vie": 4, "viernes": 4, "fri": 4, "friday": 4,
        "sab": 5, "sáb": 5, "sábado": 5, "sabado": 5,
        "sat": 5, "saturday": 5,
        "dom": 6, "domingo": 6, "sun": 6, "sunday": 6,
    }

    def __init__(self, data_dir: str = "memory_data"):
        self._tasks: dict[str, dict] = {}
        self._history: list[dict] = []
        self._executor: Optional[Callable] = None
        self._lock = threading.RLock()
        self._max_history: int = 100
        self._data_file = os.path.join(data_dir, "smart_scheduler.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga tareas desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._tasks = data.get("tasks", {})
                self._history = data.get("history", [])[-self._max_history:]
                # Recalcular next_run para todas las tareas
                for name, task in self._tasks.items():
                    if task.get("enabled", True):
                        task["next_run"] = self._calculate_next_run(task)
        except Exception:
            pass

    def save(self):
        """Guarda tareas a disco."""
        with self._lock:
            try:
                data = {
                    "tasks": self._tasks,
                    "history": self._history[-self._max_history:]
                }
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── Executor ─────────────────────────────────────
    def set_executor(self, fn: Callable):
        """Establece la función que ejecuta comandos (inyectada desde genesis.py)."""
        self._executor = fn

    # ── Parsing de schedule ──────────────────────────
    @staticmethod
    def parse_schedule(text: str) -> Optional[dict]:
        """Parsea expresión de schedule.
        Retorna: {type: 'interval'|'daily'|'weekly', interval_sec, hour, minute, day_of_week}
        """
        if not text or not text.strip():
            return None

        t = text.strip().lower()

        # Intervalo: "every 30m", "cada 30 minutos", "every 2h", "cada 1 hora"
        m = re.search(
            r'(?:every|cada)\s+(\d+)\s*(m|min|minutos?|h|horas?|s|seg|segundos?)',
            t
        )
        if m:
            value = int(m.group(1))
            unit = m.group(2)[0]  # m, h, s
            multiplier = {"m": 60, "h": 3600, "s": 1}.get(unit, 60)
            return {
                "type": "interval",
                "interval_sec": value * multiplier,
                "hour": None,
                "minute": None,
                "day_of_week": None,
                "original": text.strip()
            }

        # Diario: "daily 09:00", "diario 09:00", "todos los días a las 9"
        m = re.search(
            r'(?:daily|diario|todos los d[ií]as)\s*(?:a las\s*)?(\d{1,2}):?(\d{2})?',
            t
        )
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            return {
                "type": "daily",
                "interval_sec": None,
                "hour": hour,
                "minute": minute,
                "day_of_week": None,
                "original": text.strip()
            }

        # Semanal: "weekly mon 10:00", "cada lunes a las 10", "semanal viernes 18:00"
        m = re.search(
            r'(?:weekly|semanal|cada)\s+(\w+)\s*(?:a las\s*)?(\d{1,2}):?(\d{2})?',
            t
        )
        if m:
            day_str = m.group(1).lower()
            # Buscar en el mapa de días
            day = None
            for key, val in SmartScheduler._DAYS_MAP.items():
                if day_str.startswith(key[:3]):
                    day = val
                    break
            if day is not None:
                hour = int(m.group(2)) if m.group(2) else 9
                minute = int(m.group(3)) if m.group(3) else 0
                return {
                    "type": "weekly",
                    "interval_sec": None,
                    "hour": hour,
                    "minute": minute,
                    "day_of_week": day,
                    "original": text.strip()
                }

        return None

    def _calculate_next_run(self, task: dict) -> float:
        """Calcula el próximo timestamp de ejecución."""
        schedule = task.get("schedule", {})
        now = datetime.now()

        stype = schedule.get("type", "interval")

        if stype == "interval":
            interval = schedule.get("interval_sec", 3600)
            last = task.get("last_run", 0)
            if last:
                return last + interval
            return time.time() + interval

        elif stype == "daily":
            hour = schedule.get("hour", 9)
            minute = schedule.get("minute", 0)
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            return target.timestamp()

        elif stype == "weekly":
            hour = schedule.get("hour", 9)
            minute = schedule.get("minute", 0)
            day = schedule.get("day_of_week", 0)
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = day - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and target <= now):
                days_ahead += 7
            target += timedelta(days=days_ahead)
            return target.timestamp()

        return time.time() + 3600

    # ── CRUD de tareas ───────────────────────────────
    def add(self, name: str, schedule_text: str, command: str) -> str:
        """Agrega una tarea programada."""
        if not name or not name.strip():
            return "📅 Necesita un nombre para la tarea."
        if not command or not command.strip():
            return "📅 Necesita un comando para ejecutar."

        schedule = self.parse_schedule(schedule_text)
        if schedule is None:
            return (f"📅 No entendí el schedule '{schedule_text}'.\n"
                    "  Ejemplos: 'cada 30 minutos', 'daily 09:00', 'cada lunes a las 10'")

        name = name.strip().lower()

        with self._lock:
            is_update = name in self._tasks
            task = {
                "name": name,
                "schedule": schedule,
                "command": command.strip(),
                "enabled": True,
                "created": datetime.now().isoformat(),
                "last_run": 0,
                "run_count": 0,
                "next_run": 0
            }
            task["next_run"] = self._calculate_next_run(task)
            self._tasks[name] = task
            self.save()

        next_dt = datetime.fromtimestamp(task["next_run"]).strftime("%Y-%m-%d %H:%M")
        action = "actualizada" if is_update else "programada"
        return (f"📅 **Tarea '{name}' {action}:**\n"
                f"  ⏰ Schedule: {schedule.get('original', schedule_text)}\n"
                f"  🔧 Comando: `{command}`\n"
                f"  ▶️ Próxima ejecución: {next_dt}")

    def remove(self, name: str) -> str:
        """Elimina una tarea."""
        name = name.strip().lower()
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                self.save()
                return f"📅 Tarea '{name}' eliminada."

            # Fuzzy match
            best_match = self._fuzzy_find(name)
            if best_match:
                return f"📅 No encontré '{name}'. ¿Quisiste decir '{best_match}'?"

            return f"📅 No encontré la tarea '{name}'."

    def list_tasks(self) -> str:
        """Lista todas las tareas programadas."""
        with self._lock:
            if not self._tasks:
                return "📅 No hay tareas programadas."

            lines = [f"📅 **TAREAS PROGRAMADAS** — {len(self._tasks)} tarea(s)\n"]
            for name, task in self._tasks.items():
                status = "✅" if task["enabled"] else "⏸️"
                schedule = task["schedule"]
                next_dt = datetime.fromtimestamp(task["next_run"]).strftime("%H:%M %d/%m")
                runs = task.get("run_count", 0)
                lines.append(f"  {status} **{name}** ({schedule.get('original', '?')})")
                lines.append(f"     🔧 `{task['command']}`")
                lines.append(f"     ▶️ Próxima: {next_dt} | Ejecuciones: {runs}")

            return "\n".join(lines)

    def enable(self, name: str) -> str:
        """Habilita una tarea."""
        name = name.strip().lower()
        with self._lock:
            if name in self._tasks:
                self._tasks[name]["enabled"] = True
                self._tasks[name]["next_run"] = self._calculate_next_run(self._tasks[name])
                self.save()
                return f"📅 Tarea '{name}' habilitada."
            return f"📅 No encontré la tarea '{name}'."

    def disable(self, name: str) -> str:
        """Deshabilita una tarea."""
        name = name.strip().lower()
        with self._lock:
            if name in self._tasks:
                self._tasks[name]["enabled"] = False
                self.save()
                return f"📅 Tarea '{name}' pausada."
            return f"📅 No encontré la tarea '{name}'."

    # ── Tick cooperativo ─────────────────────────────
    def tick(self) -> list[str]:
        """Verifica y ejecuta tareas pendientes. Llamar desde el loop principal."""
        results = []
        now = time.time()

        with self._lock:
            due_tasks = [
                (name, task) for name, task in self._tasks.items()
                if task["enabled"] and task["next_run"] <= now
            ]

        for name, task in due_tasks:
            result = self._execute_task(name, task)
            if result:
                results.append(result)

        return results

    def _execute_task(self, name: str, task: dict) -> str:
        """Ejecuta una tarea programada."""
        command = task["command"]

        if self._executor is None:
            result = f"📅 Tarea '{name}' lista pero no hay ejecutor configurado."
        else:
            try:
                exec_result = self._executor(command)
                result = f"📅 Tarea '{name}' ejecutada: {str(exec_result)[:100]}"
            except Exception as e:
                result = f"📅 Tarea '{name}' falló: {e}"

        # Actualizar tarea
        with self._lock:
            if name in self._tasks:
                self._tasks[name]["last_run"] = time.time()
                self._tasks[name]["run_count"] = self._tasks[name].get("run_count", 0) + 1
                self._tasks[name]["next_run"] = self._calculate_next_run(self._tasks[name])

            # Registrar en historial
            self._history.append({
                "timestamp": datetime.now().isoformat(),
                "task": name,
                "command": command,
                "result": result[:200]
            })
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            self.save()

        return result

    def history(self) -> str:
        """Muestra historial de ejecuciones."""
        with self._lock:
            if not self._history:
                return "📅 No hay historial de ejecuciones."

            lines = [f"📅 **HISTORIAL DE EJECUCIONES** — últimas {min(len(self._history), 20)}\n"]
            for entry in reversed(self._history[-20:]):
                ts = entry["timestamp"][:16].replace("T", " ")
                lines.append(f"  [{ts}] **{entry['task']}** → `{entry['command']}`")
                lines.append(f"    {entry.get('result', '')[:80]}")

            return "\n".join(lines)

    # ── Fuzzy matching ───────────────────────────────
    def _fuzzy_find(self, query: str) -> Optional[str]:
        """Busca tarea por nombre aproximado."""
        best_score = 0.0
        best_match = None
        for name in self._tasks:
            score = SequenceMatcher(None, query, name).ratio()
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = name
        return best_match

    # ── Status ───────────────────────────────────────
    def status(self) -> dict:
        """Estado del scheduler."""
        with self._lock:
            return {
                "total_tasks": len(self._tasks),
                "active_tasks": sum(1 for t in self._tasks.values() if t["enabled"]),
                "total_runs": sum(t.get("run_count", 0) for t in self._tasks.values())
            }


# Singleton
smart_scheduler = SmartScheduler()
