"""
GENESIS Pomodoro Timer — Técnica de productividad con ciclos trabajo/descanso.
25 min trabajo → 5 min descanso → repetir (cada 4 ciclos: 15 min descanso largo).
"""
import threading
import time
from datetime import datetime
from typing import Optional, Callable


class PomodoroTimer:
    """Timer Pomodoro con ciclos de trabajo y descanso."""

    def __init__(self,
                 work_min: int = 25,
                 short_break_min: int = 5,
                 long_break_min: int = 15,
                 long_break_every: int = 4):
        self.work_sec = work_min * 60
        self.short_break_sec = short_break_min * 60
        self.long_break_sec = long_break_min * 60
        self.long_break_every = long_break_every

        self._state = "idle"  # idle, working, short_break, long_break, paused
        self._paused_state = ""  # state before pause
        self._cycle = 0  # completed work cycles
        self._total_work_sec = 0
        self._session_start: Optional[float] = None
        self._phase_start: Optional[float] = None
        self._phase_duration: int = 0
        self._remaining_at_pause: float = 0
        self._timer: Optional[threading.Timer] = None
        self._tick_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callback: Optional[Callable] = None
        self._history: list[dict] = []

    def set_callback(self, fn: Callable):
        """Callback llamado al terminar cada fase (work/break)."""
        self._callback = fn

    def _notify(self, message: str, phase: str):
        """Envía notificación de cambio de fase."""
        if self._callback:
            try:
                self._callback(message, phase)
            except Exception:
                pass

        # Intentar notificación de escritorio
        try:
            self._desktop_notify(message)
        except Exception:
            pass

    @staticmethod
    def _desktop_notify(message: str):
        """Notificación de escritorio (best-effort)."""
        try:
            import subprocess
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command",
                 f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                 f"$n = New-Object System.Windows.Forms.NotifyIcon; "
                 f"$n.Icon = [System.Drawing.SystemIcons]::Information; "
                 f"$n.Visible = $true; "
                 f"$n.ShowBalloonTip(5000, 'GENESIS Pomodoro', "
                 f"'{message.replace(chr(39), chr(39)+chr(39))}', "
                 f"[System.Windows.Forms.ToolTipIcon]::Info); "
                 f"Start-Sleep -Seconds 6; $n.Dispose()"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    # ── Control principal ─────────────────────────────
    def start(self, work_min: Optional[int] = None) -> str:
        """Inicia un ciclo Pomodoro."""
        with self._lock:
            if self._state not in ("idle", "paused"):
                return f"🍅 Ya hay un Pomodoro en curso ({self._state_text()}). Usá 'parar pomodoro' primero."

            if work_min:
                self.work_sec = work_min * 60

            self._state = "working"
            self._session_start = self._session_start or time.time()
            self._phase_start = time.time()
            self._phase_duration = self.work_sec

        self._schedule_phase_end(self.work_sec)

        work_mins = self.work_sec // 60
        return (f"🍅 **POMODORO INICIADO** — Ciclo #{self._cycle + 1}\n\n"
                f"  ⏱️ Trabajo: {work_mins} minutos\n"
                f"  🔔 Te aviso cuando termine\n"
                f"  💡 Enfocate en una sola tarea!")

    def pause(self) -> str:
        """Pausa el Pomodoro actual."""
        with self._lock:
            if self._state in ("idle", "paused"):
                return "🍅 No hay Pomodoro activo para pausar."

            self._paused_state = self._state
            elapsed = time.time() - self._phase_start
            self._remaining_at_pause = max(0, self._phase_duration - elapsed)
            self._state = "paused"

        if self._timer:
            self._timer.cancel()

        remaining_min = self._remaining_at_pause / 60
        return f"🍅 Pomodoro **pausado** — Quedan {remaining_min:.1f} min de {self._paused_state_text()}."

    def resume(self) -> str:
        """Reanuda un Pomodoro pausado."""
        with self._lock:
            if self._state != "paused":
                return "🍅 No hay Pomodoro pausado para reanudar."

            self._state = self._paused_state
            self._phase_start = time.time()
            self._phase_duration = self._remaining_at_pause

        self._schedule_phase_end(self._remaining_at_pause)
        remaining_min = self._remaining_at_pause / 60
        return f"🍅 Pomodoro **reanudado** — {remaining_min:.1f} min restantes."

    def stop(self) -> str:
        """Detiene el Pomodoro completamente."""
        with self._lock:
            if self._state == "idle":
                return "🍅 No hay Pomodoro activo."

            if self._timer:
                self._timer.cancel()
                self._timer = None

            # Registrar sesión
            if self._session_start:
                self._history.append({
                    "cycles": self._cycle,
                    "total_work_min": round(self._total_work_sec / 60, 1),
                    "started": datetime.fromtimestamp(self._session_start).strftime("%H:%M"),
                    "stopped": datetime.now().strftime("%H:%M"),
                })

            cycles = self._cycle
            work_min = round(self._total_work_sec / 60, 1)
            self._reset()

        return (f"🍅 **POMODORO DETENIDO**\n\n"
                f"  ✅ Ciclos completados: {cycles}\n"
                f"  ⏱️ Tiempo trabajado: {work_min} min")

    def skip(self) -> str:
        """Salta la fase actual (trabajo o descanso)."""
        with self._lock:
            if self._state == "idle":
                return "🍅 No hay Pomodoro activo."
            if self._state == "paused":
                return "🍅 Pomodoro pausado — reanudalo primero."

        if self._timer:
            self._timer.cancel()

        self._on_phase_complete()
        return f"🍅 Fase saltada — ahora en {self._state_text()}."

    # ── Fases internas ────────────────────────────────
    def _schedule_phase_end(self, seconds: float):
        """Programa el fin de la fase actual."""
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(seconds, self._on_phase_complete)
        self._timer.daemon = True
        self._timer.start()

    def _on_phase_complete(self):
        """Callback cuando una fase termina."""
        with self._lock:
            if self._state == "working":
                self._cycle += 1
                self._total_work_sec += self.work_sec

                if self._cycle % self.long_break_every == 0:
                    self._state = "long_break"
                    self._phase_duration = self.long_break_sec
                    msg = f"🍅 ¡Trabajo #{self._cycle} completado! Descanso largo: {self.long_break_sec // 60} min"
                    phase = "long_break"
                else:
                    self._state = "short_break"
                    self._phase_duration = self.short_break_sec
                    msg = f"🍅 ¡Trabajo #{self._cycle} completado! Descanso: {self.short_break_sec // 60} min"
                    phase = "short_break"

                self._phase_start = time.time()
                self._schedule_phase_end(self._phase_duration)
                self._notify(msg, phase)

            elif self._state in ("short_break", "long_break"):
                self._state = "working"
                self._phase_duration = self.work_sec
                self._phase_start = time.time()
                msg = f"🍅 ¡Descanso terminado! Comenzando ciclo #{self._cycle + 1} de trabajo ({self.work_sec // 60} min)"
                self._schedule_phase_end(self.work_sec)
                self._notify(msg, "working")

    def _reset(self):
        """Reset completo."""
        self._state = "idle"
        self._paused_state = ""
        self._cycle = 0
        self._total_work_sec = 0
        self._session_start = None
        self._phase_start = None
        self._phase_duration = 0
        self._remaining_at_pause = 0

    # ── Estado ────────────────────────────────────────
    def _state_text(self) -> str:
        return {
            "idle": "inactivo",
            "working": "trabajando",
            "short_break": "descanso corto",
            "long_break": "descanso largo",
            "paused": "pausado",
        }.get(self._state, self._state)

    def _paused_state_text(self) -> str:
        return {
            "working": "trabajo",
            "short_break": "descanso corto",
            "long_break": "descanso largo",
        }.get(self._paused_state, self._paused_state)

    def status(self) -> str:
        """Estado actual del Pomodoro."""
        with self._lock:
            if self._state == "idle":
                lines = ["🍅 **POMODORO** — Inactivo\n"]
                lines.append(f"  Configuración: {self.work_sec // 60}min trabajo / "
                             f"{self.short_break_sec // 60}min descanso / "
                             f"{self.long_break_sec // 60}min descanso largo")
                if self._history:
                    last = self._history[-1]
                    lines.append(f"\n  📊 Última sesión: {last['cycles']} ciclos, "
                                 f"{last['total_work_min']} min trabajados ({last['started']}-{last['stopped']})")
                lines.append("\n  💡 Decí 'inicia pomodoro' para comenzar")
                return "\n".join(lines)

            # Calcular tiempo restante
            if self._state == "paused":
                remaining = self._remaining_at_pause
            else:
                elapsed = time.time() - self._phase_start
                remaining = max(0, self._phase_duration - elapsed)

            remaining_min = int(remaining // 60)
            remaining_sec = int(remaining % 60)

            emoji = {"working": "💪", "short_break": "☕",
                     "long_break": "🌴", "paused": "⏸️"}.get(self._state, "🍅")

            return (f"🍅 **POMODORO** — {emoji} {self._state_text().upper()}\n\n"
                    f"  ⏱️ Restante: {remaining_min}:{remaining_sec:02d}\n"
                    f"  🔄 Ciclo: #{self._cycle + 1}\n"
                    f"  ✅ Completados: {self._cycle}\n"
                    f"  📊 Trabajado: {round(self._total_work_sec / 60, 1)} min total")

    def history(self) -> str:
        """Historial de sesiones Pomodoro."""
        if not self._history:
            return "🍅 No hay sesiones Pomodoro registradas aún."

        lines = ["🍅 **HISTORIAL POMODORO**\n"]
        total_cycles = 0
        total_work = 0
        for i, h in enumerate(reversed(self._history[-10:]), 1):
            lines.append(f"  #{i} — {h['started']}-{h['stopped']} | "
                         f"{h['cycles']} ciclos | {h['total_work_min']} min")
            total_cycles += h['cycles']
            total_work += h['total_work_min']

        lines.append(f"\n  📊 Total: {total_cycles} ciclos, {total_work:.0f} min trabajados")
        return "\n".join(lines)

    def configure(self, work: Optional[int] = None, short_break: Optional[int] = None,
                  long_break: Optional[int] = None) -> str:
        """Configura los tiempos del Pomodoro."""
        if self._state != "idle":
            return "🍅 No se puede configurar mientras hay un Pomodoro activo."

        if work:
            self.work_sec = work * 60
        if short_break:
            self.short_break_sec = short_break * 60
        if long_break:
            self.long_break_sec = long_break * 60

        return (f"🍅 **Pomodoro configurado:**\n"
                f"  💪 Trabajo: {self.work_sec // 60} min\n"
                f"  ☕ Descanso: {self.short_break_sec // 60} min\n"
                f"  🌴 Descanso largo: {self.long_break_sec // 60} min (cada {self.long_break_every} ciclos)")


# Singleton
pomodoro = PomodoroTimer()
