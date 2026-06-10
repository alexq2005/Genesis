"""
GENESIS Habit Tracker — Seguimiento de hábitos diarios con rachas.
Crea hábitos, trackea completaciones, calcula streaks y estadísticas.
Se integra con DailyBriefing para resumen matutino.
"""
import os
import json
import threading
from datetime import date, timedelta, datetime
from typing import Optional
from difflib import SequenceMatcher


class HabitTracker:
    """Tracker de hábitos con streaks y estadísticas."""

    def __init__(self, data_dir: str = "memory_data"):
        self._habits: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._data_file = os.path.join(data_dir, "habits.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga hábitos desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    self._habits = json.load(f)
        except Exception:
            pass

    def save(self):
        """Guarda hábitos a disco."""
        with self._lock:
            try:
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(self._habits, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── CRUD ─────────────────────────────────────────
    def add(self, name: str, frequency: str = "daily") -> str:
        """Crea un nuevo hábito."""
        if not name or not name.strip():
            return "🎯 Necesita un nombre para el hábito."

        name = name.strip()
        key = name.lower()

        if frequency not in ("daily", "weekly", "diario", "semanal"):
            frequency = "daily"
        if frequency in ("diario",):
            frequency = "daily"
        if frequency in ("semanal",):
            frequency = "weekly"

        with self._lock:
            if key in self._habits:
                return f"🎯 El hábito '{name}' ya existe."

            self._habits[key] = {
                "name": name,
                "frequency": frequency,
                "created": date.today().isoformat(),
                "completions": [],
                "enabled": True
            }
            self.save()

        freq_es = "diario" if frequency == "daily" else "semanal"
        return f"🎯 **Hábito '{name}' creado** — frecuencia: {freq_es}."

    def complete(self, name: str) -> str:
        """Marca un hábito como completado hoy."""
        key = name.strip().lower()

        with self._lock:
            habit = self._habits.get(key)
            if not habit:
                # Fuzzy match
                match = self._fuzzy_find(key)
                if match:
                    habit = self._habits[match]
                    key = match
                else:
                    return f"🎯 No encontré el hábito '{name}'."

            today = date.today().isoformat()
            if today in habit["completions"]:
                return f"🎯 '{habit['name']}' ya está completado hoy. ¡Bien hecho!"

            habit["completions"].append(today)
            streak = self._calculate_streak(habit["completions"])
            best = self._calculate_best_streak(habit["completions"])
            self.save()

        # Mensaje motivacional según racha
        if streak >= 30:
            msg = f"🏆 ¡¡{streak} DÍAS SEGUIDOS!! Sos imparable."
        elif streak >= 14:
            msg = f"🔥🔥 ¡{streak} días de racha! Increíble constancia."
        elif streak >= 7:
            msg = f"🔥 ¡{streak} días seguidos! Una semana completa."
        elif streak >= 3:
            msg = f"💪 ¡{streak} días seguidos! Seguí así."
        else:
            msg = f"✅ ¡Hecho! Racha actual: {streak} día(s)."

        return f"🎯 **'{habit['name']}'** completado.\n  {msg}"

    def uncomplete(self, name: str) -> str:
        """Remueve la completación de hoy."""
        key = name.strip().lower()

        with self._lock:
            habit = self._habits.get(key)
            if not habit:
                match = self._fuzzy_find(key)
                if match:
                    habit = self._habits[match]
                    key = match
                else:
                    return f"🎯 No encontré el hábito '{name}'."

            today = date.today().isoformat()
            if today in habit["completions"]:
                habit["completions"].remove(today)
                self.save()
                return f"🎯 Completación de '{habit['name']}' para hoy removida."
            return f"🎯 '{habit['name']}' no estaba completado hoy."

    def remove(self, name: str) -> str:
        """Elimina un hábito."""
        key = name.strip().lower()

        with self._lock:
            if key in self._habits:
                removed = self._habits.pop(key)
                self.save()
                return f"🎯 Hábito '{removed['name']}' eliminado."

            match = self._fuzzy_find(key)
            if match:
                return f"🎯 No encontré '{name}'. ¿Quisiste decir '{self._habits[match]['name']}'?"

            return f"🎯 No encontré el hábito '{name}'."

    # ── Consultas ────────────────────────────────────
    def today(self) -> str:
        """Vista de hoy: qué hábitos hay que hacer."""
        with self._lock:
            if not self._habits:
                return "🎯 No hay hábitos configurados. Creá uno con 'nuevo hábito [nombre]'."

            today_str = date.today().isoformat()
            done = 0
            total = 0
            lines = [f"🎯 **HÁBITOS DE HOY** — {date.today().strftime('%d/%m/%Y')}\n"]

            for key, habit in sorted(self._habits.items()):
                if not habit.get("enabled", True):
                    continue

                # Filtrar weekly (solo aplica si hoy es el día de la semana de creación)
                if habit["frequency"] == "weekly":
                    created = date.fromisoformat(habit["created"])
                    if date.today().weekday() != created.weekday():
                        continue

                total += 1
                is_done = today_str in habit.get("completions", [])
                streak = self._calculate_streak(habit["completions"])

                if is_done:
                    done += 1
                    check = "✅"
                else:
                    check = "⬜"

                streak_txt = f"🔥{streak}" if streak >= 3 else f"({streak}d)"
                lines.append(f"  {check} **{habit['name']}** {streak_txt}")

            if total == 0:
                return "🎯 No hay hábitos pendientes para hoy."

            lines.insert(1, f"  Progreso: {done}/{total} completados\n")
            return "\n".join(lines)

    def list_habits(self) -> str:
        """Lista todos los hábitos con estadísticas."""
        with self._lock:
            if not self._habits:
                return "🎯 No hay hábitos. Creá uno con 'nuevo hábito [nombre]'."

            lines = [f"🎯 **TODOS LOS HÁBITOS** — {len(self._habits)} hábito(s)\n"]

            for key, habit in sorted(self._habits.items()):
                streak = self._calculate_streak(habit["completions"])
                best = self._calculate_best_streak(habit["completions"])
                total_done = len(habit["completions"])
                freq = "diario" if habit["frequency"] == "daily" else "semanal"

                lines.append(f"  🎯 **{habit['name']}** ({freq})")
                lines.append(f"     Racha: {streak}d | Mejor: {best}d | Total: {total_done} completaciones")

            return "\n".join(lines)

    def stats(self, name: str = "") -> str:
        """Estadísticas detalladas de un hábito o de todos."""
        with self._lock:
            if name:
                key = name.strip().lower()
                habit = self._habits.get(key)
                if not habit:
                    match = self._fuzzy_find(key)
                    if match:
                        habit = self._habits[match]
                    else:
                        return f"🎯 No encontré el hábito '{name}'."

                return self._habit_stats(habit)

            # Estadísticas generales
            if not self._habits:
                return "🎯 No hay hábitos para mostrar estadísticas."

            total_habits = len(self._habits)
            today_str = date.today().isoformat()
            done_today = sum(
                1 for h in self._habits.values()
                if today_str in h.get("completions", [])
            )
            total_completions = sum(len(h.get("completions", [])) for h in self._habits.values())
            best_overall = max(
                (self._calculate_best_streak(h["completions"]) for h in self._habits.values()),
                default=0
            )
            best_habit = ""
            for h in self._habits.values():
                if self._calculate_best_streak(h["completions"]) == best_overall and best_overall > 0:
                    best_habit = h["name"]
                    break

            lines = [
                f"🎯 **ESTADÍSTICAS GENERALES**\n",
                f"  📊 Total hábitos: {total_habits}",
                f"  ✅ Completados hoy: {done_today}/{total_habits}",
                f"  🏆 Total completaciones: {total_completions}",
                f"  🔥 Mejor racha global: {best_overall}d" + (f" ({best_habit})" if best_habit else ""),
            ]
            return "\n".join(lines)

    def _habit_stats(self, habit: dict) -> str:
        """Estadísticas detalladas de un hábito específico."""
        completions = habit.get("completions", [])
        streak = self._calculate_streak(completions)
        best = self._calculate_best_streak(completions)
        total = len(completions)

        # Tasa de completación (últimos 30 días)
        today = date.today()
        last_30 = set()
        for i in range(30):
            d = (today - timedelta(days=i)).isoformat()
            if d in completions:
                last_30.add(d)
        rate_30 = (len(last_30) / 30 * 100) if total > 0 else 0

        # Últimos 7 días visual
        week_visual = ""
        for i in range(6, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            week_visual += "✅" if d in completions else "⬜"

        # Días desde creación
        created = date.fromisoformat(habit["created"])
        days_since = (today - created).days + 1

        lines = [
            f"🎯 **ESTADÍSTICAS: {habit['name']}**\n",
            f"  📅 Creado: {habit['created']} ({days_since} días)",
            f"  🔥 Racha actual: {streak} días",
            f"  🏆 Mejor racha: {best} días",
            f"  ✅ Total completaciones: {total}",
            f"  📊 Tasa (30 días): {rate_30:.0f}%",
            f"  📅 Última semana: {week_visual}",
        ]
        return "\n".join(lines)

    # ── Integración con DailyBriefing ────────────────
    def get_summary(self) -> str:
        """Resumen breve para DailyBriefing."""
        with self._lock:
            if not self._habits:
                return ""

            today_str = date.today().isoformat()
            total = len(self._habits)
            done = sum(
                1 for h in self._habits.values()
                if today_str in h.get("completions", [])
            )
            best = max(
                (self._calculate_streak(h["completions"]) for h in self._habits.values()),
                default=0
            )

            return f"Hábitos: {done}/{total} hoy | Mejor racha activa: {best}d"

    # ── Cálculo de streaks ───────────────────────────
    @staticmethod
    def _calculate_streak(completions: list) -> int:
        """Calcula racha consecutiva actual desde hoy hacia atrás."""
        if not completions:
            return 0

        dates = sorted(set(completions), reverse=True)
        today = date.today()
        yesterday = today - timedelta(days=1)

        # La racha puede empezar hoy o ayer
        first = date.fromisoformat(dates[0])
        if first != today and first != yesterday:
            return 0

        streak = 1
        for i in range(len(dates) - 1):
            d1 = date.fromisoformat(dates[i])
            d2 = date.fromisoformat(dates[i + 1])
            if (d1 - d2).days == 1:
                streak += 1
            else:
                break

        return streak

    @staticmethod
    def _calculate_best_streak(completions: list) -> int:
        """Calcula la mejor racha histórica."""
        if not completions:
            return 0

        dates = sorted(set(date.fromisoformat(d) for d in completions))
        best = 1
        current = 1

        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1

        return best

    # ── Fuzzy matching ───────────────────────────────
    def _fuzzy_find(self, query: str) -> Optional[str]:
        """Busca hábito por nombre aproximado."""
        best_score = 0.0
        best_match = None
        for key in self._habits:
            score = SequenceMatcher(None, query, key).ratio()
            name_score = SequenceMatcher(None, query, self._habits[key]["name"].lower()).ratio()
            score = max(score, name_score)
            if score > best_score and score >= 0.5:
                best_score = score
                best_match = key
        return best_match

    # ── Status ───────────────────────────────────────
    def status(self) -> dict:
        """Estado del tracker."""
        with self._lock:
            today_str = date.today().isoformat()
            return {
                "total_habits": len(self._habits),
                "completed_today": sum(
                    1 for h in self._habits.values()
                    if today_str in h.get("completions", [])
                ),
                "longest_active_streak": max(
                    (self._calculate_streak(h["completions"]) for h in self._habits.values()),
                    default=0
                )
            }


# Singleton
habit_tracker = HabitTracker()
