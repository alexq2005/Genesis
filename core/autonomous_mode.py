"""
GENESIS Autonomous Mode — Operacion autonoma sin input humano.

Problema:
Genesis necesita input humano para cada accion. Pero muchas tareas
son rutinarias y podrian ejecutarse automaticamente: health checks,
backups, learning analysis, curiosity research, self-optimization.

Solucion:
Un modo autonomo que:
1. Ejecuta un ciclo de acciones predefinidas sin input
2. Monitorea salud y reacciona a alertas automaticamente
3. Genera reportes de actividad autonoma
4. Se detiene cuando hay problemas criticos o el usuario interviene
5. Tiene limites de seguridad (max acciones, max tiempo, acciones prohibidas)

Uso:
    auto = AutonomousMode()
    auto.register_action("health_check", check_fn, priority=10)
    auto.start(max_cycles=100, max_duration_minutes=60)
    # ... Genesis opera autonomamente ...
    auto.stop()
"""
import time
from typing import Callable, Optional
from datetime import datetime


class AutonomousAction:
    """Una accion que Genesis puede ejecutar autonomamente."""

    def __init__(self, name: str, callback: Callable,
                 priority: int = 5, cooldown_seconds: float = 60.0,
                 description: str = "", safe: bool = True):
        self.name = name
        self.callback = callback
        self.priority = priority  # 1-10, mayor = mas prioritario
        self.cooldown_seconds = cooldown_seconds
        self.description = description
        self.safe = safe  # Si es safe, se puede ejecutar sin preguntar
        self.enabled = True

        # Timing
        self.last_run: float = 0.0
        self.next_eligible: float = 0.0

        # Stats
        self.run_count: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.total_duration_ms: float = 0.0

    def is_eligible(self) -> bool:
        """Verifica si la accion puede ejecutarse ahora."""
        if not self.enabled:
            return False
        return time.time() >= self.next_eligible

    def execute(self) -> dict:
        """Ejecuta la accion."""
        start = time.time()
        result = {
            "action": self.name,
            "timestamp": start,
            "success": False,
            "result": "",
            "error": "",
            "duration_ms": 0.0,
        }

        try:
            output = self.callback()
            result["result"] = str(output)[:200] if output else "OK"
            result["success"] = True
            self.success_count += 1
        except Exception as e:
            result["error"] = str(e)[:200]
            self.failure_count += 1

        elapsed = (time.time() - start) * 1000
        result["duration_ms"] = round(elapsed, 2)
        self.total_duration_ms += elapsed
        self.run_count += 1
        self.last_run = time.time()
        self.next_eligible = time.time() + self.cooldown_seconds

        return result


class SafetyGuard:
    """
    Guardian de seguridad para el modo autonomo.

    Previene que Genesis haga dano cuando opera sin supervision.
    """

    def __init__(self):
        # Limites
        self.max_cycles = 1000
        self.max_duration_minutes = 120  # 2 horas
        self.max_consecutive_failures = 5
        self.max_actions_per_cycle = 10

        # Acciones prohibidas en modo autonomo
        self.forbidden_actions: set = {
            "delete_files",
            "modify_core",
            "send_network",
            "execute_shell",
        }

        # Estado
        self.consecutive_failures = 0
        self.violations: list[str] = []

    def check_action(self, action: AutonomousAction) -> tuple[bool, str]:
        """Verifica si una accion es segura."""
        if action.name in self.forbidden_actions:
            self.violations.append(
                f"Accion prohibida: {action.name} ({datetime.now().isoformat()})"
            )
            return False, f"Accion '{action.name}' prohibida en modo autonomo"

        if not action.safe:
            return False, f"Accion '{action.name}' marcada como no-safe"

        return True, "OK"

    def check_cycle(self, cycle: int, start_time: float,
                    actions_this_cycle: int) -> tuple[bool, str]:
        """Verifica si el ciclo es seguro."""
        # Max ciclos
        if cycle >= self.max_cycles:
            return False, f"Limite de ciclos alcanzado ({self.max_cycles})"

        # Max duracion
        elapsed_min = (time.time() - start_time) / 60
        if elapsed_min >= self.max_duration_minutes:
            return False, f"Limite de tiempo alcanzado ({self.max_duration_minutes}min)"

        # Fallas consecutivas
        if self.consecutive_failures >= self.max_consecutive_failures:
            return False, (
                f"Demasiadas fallas consecutivas "
                f"({self.consecutive_failures}/{self.max_consecutive_failures})"
            )

        # Acciones por ciclo
        if actions_this_cycle >= self.max_actions_per_cycle:
            return False, f"Limite de acciones por ciclo ({self.max_actions_per_cycle})"

        return True, "OK"

    def record_result(self, success: bool):
        """Registra el resultado de una accion."""
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1

    def reset(self):
        """Resetea el estado del guardian."""
        self.consecutive_failures = 0
        self.violations.clear()


class AutonomousMode:
    """
    Modo autonomo de Genesis.

    Ejecuta acciones registradas en ciclos, respetando
    prioridades, cooldowns y limites de seguridad.
    """

    def __init__(self):
        # Acciones registradas
        self.actions: dict[str, AutonomousAction] = {}

        # Guardian de seguridad
        self.guard = SafetyGuard()

        # Estado
        self.active = False
        self.paused = False
        self.started_at: float = 0.0
        self.stopped_at: float = 0.0

        # Historial
        self.action_log: list[dict] = []
        self.max_log = 500

        # Stats
        self.total_cycles: int = 0
        self.total_actions: int = 0
        self.stop_reason: str = ""

    def register_action(self, name: str, callback: Callable,
                        priority: int = 5, cooldown_seconds: float = 60.0,
                        description: str = "", safe: bool = True) -> str:
        """Registra una accion autonoma."""
        if name in self.actions:
            return f"Accion '{name}' ya existe."

        self.actions[name] = AutonomousAction(
            name=name,
            callback=callback,
            priority=priority,
            cooldown_seconds=cooldown_seconds,
            description=description,
            safe=safe,
        )
        return f"Accion '{name}' registrada (prioridad: {priority}, cooldown: {cooldown_seconds}s)"

    def remove_action(self, name: str) -> str:
        """Elimina una accion."""
        if name not in self.actions:
            return f"Accion '{name}' no encontrada."
        del self.actions[name]
        return f"Accion '{name}' eliminada."

    def toggle_action(self, name: str) -> str:
        """Activa/desactiva una accion."""
        if name not in self.actions:
            return f"Accion '{name}' no encontrada."
        action = self.actions[name]
        action.enabled = not action.enabled
        state = "activada" if action.enabled else "desactivada"
        return f"Accion '{name}': {state}"

    def start(self, max_cycles: int = 0, max_duration_minutes: float = 0) -> str:
        """
        Inicia el modo autonomo.

        No bloquea — simplemente marca como activo. Las acciones
        se ejecutan cuando se llama a tick().
        """
        if self.active:
            return "Modo autonomo ya esta activo."

        if max_cycles > 0:
            self.guard.max_cycles = max_cycles
        if max_duration_minutes > 0:
            self.guard.max_duration_minutes = max_duration_minutes

        self.active = True
        self.paused = False
        self.started_at = time.time()
        self.stop_reason = ""
        self.guard.reset()

        return (
            f"Modo autonomo INICIADO.\n"
            f"  Acciones: {len(self.actions)} registradas\n"
            f"  Limites: {self.guard.max_cycles} ciclos, "
            f"{self.guard.max_duration_minutes}min max"
        )

    def stop(self, reason: str = "manual") -> str:
        """Detiene el modo autonomo."""
        if not self.active:
            return "Modo autonomo no esta activo."

        self.active = False
        self.stopped_at = time.time()
        self.stop_reason = reason

        duration = self.stopped_at - self.started_at
        dur_str = f"{duration/60:.1f}min" if duration >= 60 else f"{duration:.0f}s"

        return (
            f"Modo autonomo DETENIDO ({reason}).\n"
            f"  Duracion: {dur_str}\n"
            f"  Ciclos: {self.total_cycles}\n"
            f"  Acciones ejecutadas: {self.total_actions}"
        )

    def pause(self) -> str:
        """Pausa el modo autonomo."""
        if not self.active:
            return "Modo autonomo no esta activo."
        self.paused = True
        return "Modo autonomo PAUSADO."

    def resume(self) -> str:
        """Reanuda el modo autonomo."""
        if not self.active:
            return "Modo autonomo no esta activo."
        self.paused = False
        return "Modo autonomo REANUDADO."

    def tick(self) -> list[dict]:
        """
        Ejecuta un ciclo del modo autonomo.

        Selecciona acciones elegibles ordenadas por prioridad
        y las ejecuta respetando los limites de seguridad.

        Returns:
            Lista de resultados de acciones ejecutadas
        """
        if not self.active or self.paused:
            return []

        # Verificar limites del ciclo
        safe, reason = self.guard.check_cycle(
            self.total_cycles, self.started_at, 0
        )
        if not safe:
            self.stop(reason)
            return [{"action": "_system", "result": f"Auto-stop: {reason}"}]

        self.total_cycles += 1
        results = []
        actions_this_cycle = 0

        # Obtener acciones elegibles ordenadas por prioridad
        eligible = [
            a for a in self.actions.values()
            if a.is_eligible()
        ]
        eligible.sort(key=lambda a: a.priority, reverse=True)

        for action in eligible:
            # Verificar seguridad
            safe, reason = self.guard.check_action(action)
            if not safe:
                continue

            # Verificar limite por ciclo
            safe, reason = self.guard.check_cycle(
                self.total_cycles - 1,  # Ya incrementamos
                self.started_at,
                actions_this_cycle,
            )
            if not safe:
                break

            # Ejecutar
            result = action.execute()
            results.append(result)
            actions_this_cycle += 1
            self.total_actions += 1

            # Registrar en log
            self._log_action(result)

            # Informar al guardian
            self.guard.record_result(result["success"])

        return results

    def _log_action(self, result: dict):
        """Registra una accion en el log."""
        self.action_log.append(result)
        if len(self.action_log) > self.max_log:
            self.action_log = self.action_log[-self.max_log:]

    def get_action_list(self) -> str:
        """Lista de acciones registradas."""
        if not self.actions:
            return "  No hay acciones registradas."

        lines = []
        for action in sorted(self.actions.values(),
                              key=lambda a: a.priority, reverse=True):
            icon = ">" if action.enabled else "x"
            rate = (
                f"{action.success_count}/{action.run_count}"
                if action.run_count > 0 else "0/0"
            )
            cd = f"{action.cooldown_seconds:.0f}s"
            lines.append(
                f"  [{icon}] P{action.priority} {action.name:25s} "
                f"cd:{cd:>6s} | runs: {rate}"
            )
            if action.description:
                lines.append(f"       {action.description}")

        return "\n".join(lines)

    def get_log_report(self, n: int = 20) -> str:
        """Reporte del historial de acciones autonomas."""
        if not self.action_log:
            return "  Sin acciones autonomas registradas."

        recent = self.action_log[-n:]
        lines = []
        for entry in recent:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
            status = "OK" if entry["success"] else "FAIL"
            dur = f"{entry['duration_ms']:.0f}ms"
            lines.append(
                f"  [{ts}] {entry['action']:25s} {status:4s} {dur:>8s}"
            )
            if not entry["success"] and entry.get("error"):
                lines.append(f"          -> {entry['error'][:60]}")

        return "\n".join(lines)

    def generate_report(self) -> str:
        """Reporte completo del modo autonomo."""
        lines = [
            "=== AUTONOMOUS MODE ===",
            f"  Estado: {'ACTIVO' if self.active else 'INACTIVO'}"
            f"{'  (PAUSADO)' if self.paused else ''}",
        ]

        if self.started_at > 0:
            if self.active:
                elapsed = time.time() - self.started_at
            else:
                elapsed = self.stopped_at - self.started_at if self.stopped_at > 0 else 0
            dur_str = f"{elapsed/60:.1f}min"
            lines.append(f"  Duracion: {dur_str}")

        lines.extend([
            f"  Ciclos: {self.total_cycles} | Acciones: {self.total_actions}",
            f"  Limites: {self.guard.max_cycles} ciclos, "
            f"{self.guard.max_duration_minutes}min max",
        ])

        if self.stop_reason:
            lines.append(f"  Razon de parada: {self.stop_reason}")

        # Violaciones de seguridad
        if self.guard.violations:
            lines.append(f"\n  VIOLACIONES DE SEGURIDAD ({len(self.guard.violations)}):")
            for v in self.guard.violations[-5:]:
                lines.append(f"    - {v}")

        # Acciones
        lines.append(f"\n  ACCIONES ({len(self.actions)}):")
        lines.append(self.get_action_list())

        # Log reciente
        if self.action_log:
            lines.append(f"\n  LOG RECIENTE:")
            lines.append(self.get_log_report(10))

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen para /status."""
        state = "ACTIVO" if self.active else "OFF"
        if self.paused:
            state = "PAUSADO"
        n_actions = len(self.actions)
        return (
            f"  Estado: {state} | Acciones: {n_actions} | "
            f"Ciclos: {self.total_cycles} | Ejecutadas: {self.total_actions}"
        )
