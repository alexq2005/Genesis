"""
GENESIS Reminder System — Temporizadores y recordatorios con notificación.
Los recordatorios corren en background threads y notifican al usuario
via desktop notification o callback.
"""
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional


class Reminder:
    """Un recordatorio individual."""

    def __init__(self, message: str, seconds: int, reminder_id: int = 0):
        self.id = reminder_id
        self.message = message
        self.seconds = seconds
        self.created = datetime.now()
        self.trigger_at = self.created + timedelta(seconds=seconds)
        self.fired = False
        self.cancelled = False
        self._timer: Optional[threading.Timer] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message": self.message,
            "seconds": self.seconds,
            "created": self.created.isoformat(),
            "trigger_at": self.trigger_at.isoformat(),
            "fired": self.fired,
            "cancelled": self.cancelled,
        }

    def time_remaining(self) -> float:
        """Segundos restantes hasta que se dispare."""
        if self.fired or self.cancelled:
            return 0
        remaining = (self.trigger_at - datetime.now()).total_seconds()
        return max(0, remaining)


class ReminderSystem:
    """Sistema de recordatorios con notificaciones desktop."""

    def __init__(self, data_dir: str = None):
        if data_dir:
            self._file = Path(data_dir) / "reminders.json"
        else:
            self._file = Path(__file__).parent.parent / "memory_data" / "reminders.json"
        self._reminders: list[Reminder] = []
        self._next_id = 1
        self._callback: Optional[Callable] = None
        self._lock = threading.Lock()

    def set_callback(self, callback: Callable):
        """Configura callback para cuando un recordatorio se dispara.
        callback(reminder: Reminder) se llama en un thread separado."""
        self._callback = callback

    def add(self, message: str, seconds: int) -> str:
        """Agrega un recordatorio que se dispara en N segundos."""
        if seconds <= 0:
            return "El tiempo debe ser mayor a 0."
        if seconds > 86400:  # 24 horas max
            return "El máximo es 24 horas (86400 segundos)."
        if not message.strip():
            return "El recordatorio necesita un mensaje."

        with self._lock:
            reminder = Reminder(message.strip(), seconds, self._next_id)
            self._next_id += 1
            self._reminders.append(reminder)

            # Iniciar timer en background
            timer = threading.Timer(seconds, self._fire, args=[reminder])
            timer.daemon = True
            timer.name = f"reminder-{reminder.id}"
            reminder._timer = timer
            timer.start()

        # Formatear tiempo legible
        time_str = self._format_time(seconds)
        return (f"⏰ Recordatorio #{reminder.id} configurado\n"
                f"  📝 \"{message.strip()}\"\n"
                f"  ⏱️ En {time_str} ({reminder.trigger_at.strftime('%H:%M:%S')})")

    def _fire(self, reminder: Reminder):
        """Se ejecuta cuando el timer llega a cero."""
        with self._lock:
            if reminder.cancelled:
                return
            reminder.fired = True

        # Notificación por callback
        if self._callback:
            try:
                self._callback(reminder)
            except Exception:
                pass

        # Intentar notificación desktop nativa
        self._desktop_notify(reminder)

    def _desktop_notify(self, reminder: Reminder):
        """Envía notificación desktop nativa."""
        try:
            # Método 1: plyer (cross-platform)
            from plyer import notification
            notification.notify(
                title="⏰ Genesis — Recordatorio",
                message=reminder.message,
                app_name="Genesis AI",
                timeout=10,
            )
            return
        except ImportError:
            pass

        try:
            # Método 2: win10toast
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "Genesis — Recordatorio",
                reminder.message,
                duration=10,
                threaded=True,
            )
            return
        except ImportError:
            pass

        try:
            # Método 3: PowerShell toast (Windows, sin dependencias)
            import subprocess
            ps_script = (
                f'[Windows.UI.Notifications.ToastNotificationManager, '
                f'Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; '
                f'$template = [Windows.UI.Notifications.ToastNotificationManager]::'
                f'GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); '
                f'$text = $template.GetElementsByTagName("text"); '
                f'$text[0].AppendChild($template.CreateTextNode("Genesis - Recordatorio")) | Out-Null; '
                f'$text[1].AppendChild($template.CreateTextNode("{reminder.message}")) | Out-Null; '
                f'$toast = [Windows.UI.Notifications.ToastNotification]::new($template); '
                f'[Windows.UI.Notifications.ToastNotificationManager]::'
                f'CreateToastNotifier("Genesis").Show($toast)'
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", ps_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            # Último recurso: print al stdout
            print(f"\n⏰ RECORDATORIO: {reminder.message}\n")

    def cancel(self, reminder_id: int) -> str:
        """Cancela un recordatorio pendiente."""
        with self._lock:
            for r in self._reminders:
                if r.id == reminder_id and not r.fired:
                    r.cancelled = True
                    if r._timer:
                        r._timer.cancel()
                    return f"⏰ Recordatorio #{reminder_id} cancelado."
        return f"No encontré recordatorio #{reminder_id} activo."

    def list_active(self) -> str:
        """Lista recordatorios activos (no disparados ni cancelados)."""
        with self._lock:
            active = [r for r in self._reminders if not r.fired and not r.cancelled]

        if not active:
            return "⏰ No hay recordatorios activos."

        lines = [f"⏰ **RECORDATORIOS ACTIVOS** ({len(active)})\n"]
        for r in active:
            remaining = r.time_remaining()
            time_str = self._format_time(int(remaining))
            lines.append(
                f"  **#{r.id}** — \"{r.message}\" — en {time_str} "
                f"({r.trigger_at.strftime('%H:%M:%S')})"
            )
        return "\n".join(lines)

    def list_history(self, limit: int = 10) -> str:
        """Lista todos los recordatorios (incluidos los disparados)."""
        if not self._reminders:
            return "⏰ Sin historial de recordatorios."

        lines = [f"⏰ **HISTORIAL** ({len(self._reminders)} total)\n"]
        for r in self._reminders[-limit:]:
            status = "✅ Disparado" if r.fired else ("❌ Cancelado" if r.cancelled else "⏳ Pendiente")
            lines.append(f"  #{r.id} — {status} — \"{r.message[:60]}\"")
        return "\n".join(lines)

    @staticmethod
    def _format_time(seconds: int) -> str:
        """Convierte segundos a formato legible."""
        if seconds < 60:
            return f"{seconds} segundos"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins} minuto{'s' if mins > 1 else ''}" + (f" {secs}s" if secs else "")
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours} hora{'s' if hours > 1 else ''}" + (f" {mins}min" if mins else "")

    @staticmethod
    def parse_time_expression(text: str) -> Optional[int]:
        """Parsea expresiones de tiempo en español a segundos.
        Ejemplos: '5 minutos', '1 hora', '30 segundos', '2h30m'
        """
        import re
        text = text.lower().strip()

        # Patrón compuesto: 2h30m, 1h, 30m, 45s
        compound = re.findall(r'(\d+)\s*(h|hora|horas|m|min|minuto|minutos|s|seg|segundo|segundos)', text)
        if compound:
            total = 0
            for value, unit in compound:
                v = int(value)
                if unit in ("h", "hora", "horas"):
                    total += v * 3600
                elif unit in ("m", "min", "minuto", "minutos"):
                    total += v * 60
                elif unit in ("s", "seg", "segundo", "segundos"):
                    total += v
            return total if total > 0 else None

        # Patrón simple: "5 minutos", "una hora", "medio minuto"
        if "media hora" in text or "medio hora" in text:
            return 1800
        if "un cuarto de hora" in text or "cuarto de hora" in text:
            return 900
        if "un minuto" in text or "1 minuto" in text:
            return 60
        if "una hora" in text or "1 hora" in text:
            return 3600

        return None

    def save(self):
        """Guarda historial de recordatorios."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            data = [r.to_dict() for r in self._reminders[-50:]]  # Últimos 50
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def status(self) -> dict:
        with self._lock:
            active = sum(1 for r in self._reminders if not r.fired and not r.cancelled)
            fired = sum(1 for r in self._reminders if r.fired)
        return {"active": active, "fired": fired, "total": len(self._reminders)}

    def get_stats(self) -> dict:
        return self.status()

    def clear(self):
        """Cancela todos los recordatorios activos."""
        with self._lock:
            for r in self._reminders:
                if not r.fired and not r.cancelled:
                    r.cancelled = True
                    if r._timer:
                        r._timer.cancel()
