"""
GENESIS Daily Briefing — Resumen inteligente del estado del sistema.
Genera un briefing matutino con: sistema, disco, notas pendientes,
recordatorios, motivación. Se activa con "buenos días" o "briefing".
"""
import os
import time
import random
import subprocess
from datetime import datetime


class DailyBriefing:
    """Genera briefings contextuales del estado del sistema."""

    GREETINGS = {
        range(5, 12): "Buenos días",
        range(12, 19): "Buenas tardes",
        range(19, 24): "Buenas noches",
        range(0, 5): "Buenas noches (¿trasnochando?)",
    }

    MOTIVATIONAL = [
        "💪 \"El único modo de hacer un gran trabajo es amar lo que haces.\" — Steve Jobs",
        "🚀 \"El futuro pertenece a quienes creen en la belleza de sus sueños.\" — Eleanor Roosevelt",
        "🧠 \"La inteligencia es la habilidad de adaptarse al cambio.\" — Stephen Hawking",
        "⭐ \"No cuentes los días, haz que los días cuenten.\" — Muhammad Ali",
        "🔥 \"El éxito no es definitivo, el fracaso no es fatal: lo que cuenta es el coraje de continuar.\" — Churchill",
        "🎯 \"La única forma de predecir el futuro es creándolo.\" — Peter Drucker",
        "💡 \"La creatividad es la inteligencia divirtiéndose.\" — Einstein",
        "🌟 \"Cada día es una nueva oportunidad para cambiar tu vida.\" — Anónimo",
        "🏆 \"Los grandes logros requieren tiempo, dedicación y persistencia.\" — Anónimo",
        "🌱 \"El mejor momento para plantar un árbol fue hace 20 años. El segundo mejor es ahora.\" — Proverbio chino",
    ]

    def _get_greeting(self) -> str:
        """Saludo contextual según la hora."""
        hour = datetime.now().hour
        for time_range, greeting in self.GREETINGS.items():
            if hour in time_range:
                return greeting
        return "Hola"

    @staticmethod
    def _get_system_status() -> dict:
        """Obtiene estado del sistema."""
        info = {}

        # Uptime
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | "
                 "ForEach-Object { \"$($_.Days)d $($_.Hours)h $($_.Minutes)m\" }"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            info["uptime"] = r.stdout.strip()
        except Exception:
            info["uptime"] = "?"

        # CPU & RAM (via powershell)
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$cpu = (Get-CimInstance Win32_Processor).LoadPercentage; "
                 "$os = Get-CimInstance Win32_OperatingSystem; "
                 "$ram_total = [math]::Round($os.TotalVisibleMemorySize/1MB, 1); "
                 "$ram_free = [math]::Round($os.FreePhysicalMemory/1MB, 1); "
                 "$ram_used = $ram_total - $ram_free; "
                 "$ram_pct = [math]::Round(($ram_used/$ram_total)*100, 0); "
                 "Write-Output \"$cpu|$ram_used|$ram_total|$ram_pct\""],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            parts = r.stdout.strip().split("|")
            if len(parts) >= 4:
                info["cpu"] = f"{parts[0]}%"
                info["ram"] = f"{parts[1]}/{parts[2]} GB ({parts[3]}%)"
        except Exception:
            info["cpu"] = "?"
            info["ram"] = "?"

        # Disco
        try:
            import shutil
            total, used, free = shutil.disk_usage("C:\\")
            free_gb = free // (1024 ** 3)
            total_gb = total // (1024 ** 3)
            used_pct = int((used / total) * 100)
            info["disk"] = f"{free_gb} GB libres de {total_gb} GB ({used_pct}% usado)"
            info["disk_warning"] = free_gb < 20
        except Exception:
            info["disk"] = "?"
            info["disk_warning"] = False

        return info

    @staticmethod
    def _get_notes_summary() -> str:
        """Resumen de notas pendientes."""
        try:
            from core.quick_notes import QuickNotes
            qn = QuickNotes()
            total = len(qn._notes)
            pinned = sum(1 for n in qn._notes if n.get("pinned"))
            if total == 0:
                return "Sin notas"
            return f"{total} notas ({pinned} fijadas)" if pinned else f"{total} notas"
        except Exception:
            return "Sin acceso"

    @staticmethod
    def _get_reminders_summary() -> str:
        """Resumen de recordatorios activos."""
        try:
            from core.reminder_system import ReminderSystem
            rs = ReminderSystem()
            st = rs.status()
            active = st.get("active", 0)
            if active == 0:
                return "Sin recordatorios activos"
            return f"{active} recordatorio(s) activo(s)"
        except Exception:
            return "Sin acceso"

    @staticmethod
    def _get_pomodoro_summary() -> str:
        """Resumen del Pomodoro."""
        try:
            from core.pomodoro import pomodoro
            if pomodoro._state != "idle":
                return f"Pomodoro activo: {pomodoro._state_text()}"
            return None
        except Exception:
            return None

    @staticmethod
    def _get_habits_summary() -> str:
        """Resumen de hábitos del día."""
        try:
            from core.habit_tracker import habit_tracker
            summary = habit_tracker.get_summary()
            return summary if summary else None
        except Exception:
            return None

    def generate(self, full: bool = True) -> str:
        """Genera el briefing completo."""
        now = datetime.now()
        greeting = self._get_greeting()
        username = os.getenv("USERNAME", os.getenv("USER", "usuario"))

        days_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        date_str = f"{days_es[now.weekday()]} {now.day} de {months_es[now.month]} de {now.year}"
        time_str = now.strftime("%H:%M")

        lines = [
            f"☀️ **{greeting}, {username}!**",
            f"📅 {date_str} — {time_str}",
            "",
        ]

        if full:
            # Sistema
            sys_info = self._get_system_status()
            lines.append("🖥️ **SISTEMA:**")
            lines.append(f"  ⏱️ Uptime: {sys_info.get('uptime', '?')}")
            lines.append(f"  🔲 CPU: {sys_info.get('cpu', '?')}")
            lines.append(f"  🧠 RAM: {sys_info.get('ram', '?')}")
            disk = sys_info.get("disk", "?")
            disk_icon = "⚠️" if sys_info.get("disk_warning") else "💾"
            lines.append(f"  {disk_icon} Disco: {disk}")
            lines.append("")

            # Notas y Recordatorios
            notes = self._get_notes_summary()
            reminders = self._get_reminders_summary()
            pomo = self._get_pomodoro_summary()

            habits = self._get_habits_summary()

            lines.append("📊 **PRODUCTIVIDAD:**")
            lines.append(f"  📝 {notes}")
            lines.append(f"  ⏰ {reminders}")
            if pomo:
                lines.append(f"  🍅 {pomo}")
            if habits:
                lines.append(f"  🎯 {habits}")
            lines.append("")

            # Motivación
            quote = random.choice(self.MOTIVATIONAL)
            lines.append(f"✨ {quote}")

        return "\n".join(lines)

    def quick_status(self) -> str:
        """Status rápido del sistema (sin motivación)."""
        return self.generate(full=False) + "\n" + self._quick_sys()

    def _quick_sys(self) -> str:
        """Status rápido mínimo."""
        sys_info = self._get_system_status()
        return (f"🖥️ CPU: {sys_info.get('cpu', '?')} | "
                f"RAM: {sys_info.get('ram', '?')} | "
                f"Uptime: {sys_info.get('uptime', '?')}")


# Singleton
daily_briefing = DailyBriefing()
