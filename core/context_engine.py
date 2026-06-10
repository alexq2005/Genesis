"""
GENESIS Context Engine — Motor de contexto que aprende patrones de uso.
Registra interacciones, analiza frecuencias y horarios, sugiere proactivamente.
"""
import os
import json
import threading
from datetime import datetime, date
from typing import Optional
from collections import Counter


class ContextEngine:
    """Motor de aprendizaje contextual de patrones de uso."""

    def __init__(self, data_dir: str = "memory_data"):
        self._interactions: list[dict] = []
        self._lock = threading.RLock()
        self._max_interactions: int = 500
        self._data_file = os.path.join(data_dir, "context_engine.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga interacciones desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._interactions = data.get("interactions", [])[-self._max_interactions:]
        except Exception:
            pass

    def save(self):
        """Guarda interacciones a disco."""
        with self._lock:
            try:
                data = {
                    "interactions": self._interactions[-self._max_interactions:]
                }
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── Registro ─────────────────────────────────────
    def record(self, command_type: str, query: str, auto_detected: bool = False):
        """Registra una interacción del usuario."""
        now = datetime.now()

        interaction = {
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
            "hour": now.hour,
            "minute": now.minute,
            "weekday": now.weekday(),
            "command_type": command_type,
            "query_preview": query[:80] if query else "",
            "auto_detected": auto_detected
        }

        with self._lock:
            self._interactions.append(interaction)
            if len(self._interactions) > self._max_interactions:
                self._interactions = self._interactions[-self._max_interactions:]

    # ── Análisis ─────────────────────────────────────
    def top_commands(self, limit: int = 10) -> str:
        """Muestra los comandos más usados."""
        with self._lock:
            if not self._interactions:
                return "🧠 No hay datos de uso registrados aún."

            counter = Counter(i["command_type"] for i in self._interactions)
            total = len(self._interactions)
            top = counter.most_common(limit)

            lines = [f"🧠 **COMANDOS MÁS USADOS** — {total} interacciones totales\n"]
            for i, (cmd, count) in enumerate(top, 1):
                pct = count / total * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                lines.append(f"  {i}. **{cmd}** — {count}x ({pct:.1f}%)")
                lines.append(f"     {bar}")

            return "\n".join(lines)

    def time_report(self) -> str:
        """Muestra patrones de uso por hora del día."""
        with self._lock:
            if not self._interactions:
                return "🧠 No hay datos de uso para analizar."

            # Contar por hora
            hour_counts: dict[int, int] = {}
            for i in self._interactions:
                h = i["hour"]
                hour_counts[h] = hour_counts.get(h, 0) + 1

            if not hour_counts:
                return "🧠 Sin datos suficientes."

            max_count = max(hour_counts.values())
            peak_hour = max(hour_counts, key=hour_counts.get)

            # Encontrar horas pico (>50% del máximo)
            peak_hours = sorted(h for h, c in hour_counts.items() if c >= max_count * 0.5)

            lines = [f"🧠 **PATRONES DE USO POR HORA**\n"]

            # Heatmap textual (6:00 - 23:00)
            for h in range(6, 24):
                count = hour_counts.get(h, 0)
                if max_count > 0:
                    bar_len = int(count / max_count * 20)
                else:
                    bar_len = 0
                bar = "█" * bar_len + "░" * (20 - bar_len)
                marker = " ◀ PICO" if h == peak_hour else ""
                lines.append(f"  {h:02d}:00 {bar} {count}{marker}")

            # Resumen
            if len(peak_hours) >= 2:
                range_str = f"{peak_hours[0]:02d}:00 - {peak_hours[-1]:02d}:59"
            else:
                range_str = f"{peak_hour:02d}:00"

            lines.append(f"\n  📊 Hora pico: {range_str}")
            lines.append(f"  📊 Total interacciones: {len(self._interactions)}")

            return "\n".join(lines)

    def day_report(self) -> str:
        """Muestra patrones por día de la semana."""
        with self._lock:
            if not self._interactions:
                return "🧠 No hay datos de uso para analizar."

            days_es = ["Lunes", "Martes", "Miércoles", "Jueves",
                       "Viernes", "Sábado", "Domingo"]

            day_counts: dict[int, int] = {}
            for i in self._interactions:
                d = i["weekday"]
                day_counts[d] = day_counts.get(d, 0) + 1

            max_count = max(day_counts.values()) if day_counts else 1

            lines = [f"🧠 **PATRONES POR DÍA DE LA SEMANA**\n"]
            for d in range(7):
                count = day_counts.get(d, 0)
                bar_len = int(count / max_count * 15) if max_count > 0 else 0
                bar = "█" * bar_len + "░" * (15 - bar_len)
                lines.append(f"  {days_es[d]:12s} {bar} {count}")

            return "\n".join(lines)

    def suggest(self) -> Optional[str]:
        """Sugiere acciones basadas en patrones aprendidos."""
        with self._lock:
            if len(self._interactions) < 10:
                return None

            now = datetime.now()
            current_hour = now.hour

            # Encontrar qué se hace normalmente a esta hora
            same_hour = [
                i for i in self._interactions
                if i["hour"] == current_hour
            ]

            if len(same_hour) < 3:
                return None

            # Comando más frecuente a esta hora
            counter = Counter(i["command_type"] for i in same_hour)
            most_common_cmd, count = counter.most_common(1)[0]

            # Solo sugerir si es un patrón fuerte (>40% de las veces a esta hora)
            if count / len(same_hour) >= 0.4:
                return (f"🧠 **Sugerencia:** A las {current_hour}:00 normalmente usás "
                        f"'{most_common_cmd}' ({count} veces). ¿Lo ejecuto?")

            return None

    def full_report(self) -> str:
        """Reporte completo de análisis de uso."""
        with self._lock:
            if not self._interactions:
                return "🧠 No hay datos de uso registrados aún."

        lines = []

        # Top commands
        lines.append(self.top_commands(5))
        lines.append("")

        # Time report
        lines.append(self.time_report())
        lines.append("")

        # Day report
        lines.append(self.day_report())

        # Sugerencia
        suggestion = self.suggest()
        if suggestion:
            lines.append("")
            lines.append(suggestion)

        return "\n".join(lines)

    def clear(self) -> str:
        """Borra todos los datos de interacciones."""
        with self._lock:
            count = len(self._interactions)
            self._interactions = []
            self.save()
        return f"🧠 {count} interacciones borradas."

    # ── Status ───────────────────────────────────────
    def status(self) -> dict:
        """Estado del motor de contexto."""
        with self._lock:
            if not self._interactions:
                return {
                    "total_interactions": 0,
                    "unique_commands": 0,
                    "peak_hour": None
                }

            counter = Counter(i["command_type"] for i in self._interactions)
            hour_counts = Counter(i["hour"] for i in self._interactions)

            return {
                "total_interactions": len(self._interactions),
                "unique_commands": len(counter),
                "peak_hour": hour_counts.most_common(1)[0][0] if hour_counts else None
            }


# Singleton
context_engine = ContextEngine()
