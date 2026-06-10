"""
GENESIS Metrics — Auto-benchmarking con datos reales.

Rastrea metricas objetivas de rendimiento:
- Tiempo de respuesta promedio
- Tasa de exito en codigo (ejecuto sin errores?)
- Uso de herramientas (cuales y con que frecuencia)
- Errores por sesion
- Tendencia historica (mejorando o empeorando?)

A diferencia del sistema de evolucion original (que usaba el LLM
para evaluarse a si mismo), esto usa DATOS REALES medibles.
"""
import json
import time
from pathlib import Path
from typing import Optional


class MetricsTracker:
    """Rastrea metricas de rendimiento de Genesis."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.data = self._load()
        # Metricas de la sesion actual
        self.session = self._new_session()

    def _load(self) -> dict:
        """Carga metricas historicas desde disco."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {
            "sessions": [],         # Historial de sesiones
            "totals": {             # Totales acumulados
                "total_interactions": 0,
                "total_tool_uses": 0,
                "total_code_runs": 0,
                "total_code_successes": 0,
                "total_code_failures": 0,
                "total_errors": 0,
                "total_response_time_ms": 0,
                "total_sessions": 0,
            },
            "records": {            # Records historicos
                "fastest_response_ms": float("inf"),
                "longest_streak_no_errors": 0,
                "max_tools_one_session": 0,
                "max_code_success_rate": 0.0,
            },
            "created": time.time(),
        }

    def _save(self):
        """Persiste metricas a disco."""
        # Limpiar infinitos para JSON
        records = self.data.get("records", {})
        if records.get("fastest_response_ms") == float("inf"):
            records["fastest_response_ms"] = 0

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def _new_session(self) -> dict:
        """Crea metricas para una nueva sesion."""
        return {
            "started": time.time(),
            "interactions": 0,
            "tool_uses": {},         # {nombre_herramienta: conteo}
            "code_runs": 0,
            "code_successes": 0,
            "code_failures": 0,
            "code_retries": 0,       # Veces que el coding loop reintento
            "errors": 0,
            "response_times_ms": [],  # Tiempos de respuesta
            "consecutive_no_error": 0,  # Racha sin errores
        }

    def log_interaction(self, response_time_ms: float):
        """Registra una interaccion completada."""
        self.session["interactions"] += 1
        self.session["response_times_ms"].append(round(response_time_ms))
        self.data["totals"]["total_interactions"] += 1
        self.data["totals"]["total_response_time_ms"] += round(response_time_ms)

        # Record de velocidad
        if response_time_ms > 0:
            current_fastest = self.data["records"].get("fastest_response_ms", float("inf"))
            if current_fastest == 0:
                current_fastest = float("inf")
            if response_time_ms < current_fastest:
                self.data["records"]["fastest_response_ms"] = round(response_time_ms)

    def log_tool_use(self, tool_name: str):
        """Registra uso de una herramienta."""
        tools = self.session["tool_uses"]
        tools[tool_name] = tools.get(tool_name, 0) + 1
        self.data["totals"]["total_tool_uses"] += 1

    def log_code_execution(self, success: bool, was_retry: bool = False):
        """Registra ejecucion de codigo."""
        self.session["code_runs"] += 1
        self.data["totals"]["total_code_runs"] += 1

        if was_retry:
            self.session["code_retries"] += 1

        if success:
            self.session["code_successes"] += 1
            self.session["consecutive_no_error"] += 1
            self.data["totals"]["total_code_successes"] += 1

            # Actualizar record de racha sin errores
            current_record = self.data["records"].get("longest_streak_no_errors", 0)
            if self.session["consecutive_no_error"] > current_record:
                self.data["records"]["longest_streak_no_errors"] = self.session["consecutive_no_error"]
        else:
            self.session["code_failures"] += 1
            self.session["consecutive_no_error"] = 0
            self.data["totals"]["total_code_failures"] += 1

    def log_error(self):
        """Registra un error general."""
        self.session["errors"] += 1
        self.data["totals"]["total_errors"] += 1

    def get_code_success_rate(self) -> float:
        """Tasa de exito de codigo en la sesion actual (0.0 a 1.0)."""
        total = self.session["code_runs"]
        if total == 0:
            return 1.0  # Sin ejecuciones = sin errores
        return self.session["code_successes"] / total

    def get_avg_response_time(self) -> float:
        """Tiempo de respuesta promedio en la sesion (ms)."""
        times = self.session["response_times_ms"]
        if not times:
            return 0.0
        return sum(times) / len(times)

    def get_session_fitness(self) -> int:
        """
        Calcula fitness basado en metricas objetivas de la sesion.
        Retorna 0-100.
        """
        score = 50  # Base

        # Tasa de exito de codigo (+/- 20 puntos)
        if self.session["code_runs"] > 0:
            code_rate = self.get_code_success_rate()
            score += int((code_rate - 0.5) * 40)  # 0% = -20, 100% = +20

        # Reintentos de codigo (-5 por cada reintento excesivo)
        excessive_retries = max(0, self.session["code_retries"] - 2)
        score -= excessive_retries * 5

        # Errores generales (-10 cada uno)
        score -= self.session["errors"] * 10

        # Uso de herramientas (bonus por variedad, max +10)
        unique_tools = len(self.session["tool_uses"])
        score += min(10, unique_tools * 2)

        # Velocidad promedio (bonus si < 5s, penalidad si > 30s)
        avg_time = self.get_avg_response_time()
        if avg_time > 0:
            if avg_time < 5000:
                score += 5
            elif avg_time > 30000:
                score -= 5

        return max(0, min(100, score))

    def get_historical_fitness(self) -> int:
        """
        Calcula fitness basado en todo el historial.
        Retorna 0-100.
        """
        totals = self.data["totals"]
        total_code = totals["total_code_runs"]

        score = 50

        # Tasa de exito de codigo historica
        if total_code > 0:
            code_rate = totals["total_code_successes"] / total_code
            score += int((code_rate - 0.5) * 30)

        # Tasa de errores por interaccion
        total_interactions = totals["total_interactions"]
        if total_interactions > 0:
            error_rate = totals["total_errors"] / total_interactions
            score -= int(error_rate * 20)

        return max(0, min(100, score))

    def get_trend(self) -> str:
        """
        Analiza la tendencia: mejorando, estable o empeorando.
        Compara las ultimas 3 sesiones con las 3 anteriores.
        """
        sessions = self.data["sessions"]
        if len(sessions) < 4:
            return "sin_datos"

        def session_score(s: dict) -> float:
            """Calcula score basico de una sesion."""
            code_runs = s.get("code_runs", 0)
            if code_runs > 0:
                code_rate = s.get("code_successes", 0) / code_runs
            else:
                code_rate = 1.0
            errors = s.get("errors", 0)
            return code_rate * 100 - errors * 10

        recent = sessions[-3:]
        older = sessions[-6:-3] if len(sessions) >= 6 else sessions[:3]

        avg_recent = sum(session_score(s) for s in recent) / len(recent)
        avg_older = sum(session_score(s) for s in older) / len(older)

        diff = avg_recent - avg_older
        if diff > 5:
            return "mejorando 📈"
        elif diff < -5:
            return "empeorando 📉"
        else:
            return "estable ➡️"

    def end_session(self):
        """Finaliza la sesion actual y guarda metricas."""
        self.session["ended"] = time.time()
        self.session["duration_s"] = round(
            self.session["ended"] - self.session["started"]
        )

        # Guardar sesion en historial (max 50 sesiones)
        self.data["sessions"].append(self.session)
        if len(self.data["sessions"]) > 50:
            self.data["sessions"] = self.data["sessions"][-50:]

        self.data["totals"]["total_sessions"] += 1

        # Actualizar records
        tool_count = sum(self.session["tool_uses"].values())
        if tool_count > self.data["records"].get("max_tools_one_session", 0):
            self.data["records"]["max_tools_one_session"] = tool_count

        code_rate = self.get_code_success_rate()
        if self.session["code_runs"] > 0:
            if code_rate > self.data["records"].get("max_code_success_rate", 0):
                self.data["records"]["max_code_success_rate"] = round(code_rate, 3)

        self._save()

    def format_session_report(self) -> str:
        """Genera reporte de la sesion actual."""
        s = self.session
        lines = ["=== METRICAS DE SESION ===\n"]

        # Tiempo
        duration = time.time() - s["started"]
        mins = int(duration // 60)
        secs = int(duration % 60)
        lines.append(f"  Duracion: {mins}m {secs}s")
        lines.append(f"  Interacciones: {s['interactions']}")

        # Respuestas
        avg_time = self.get_avg_response_time()
        if avg_time > 0:
            lines.append(f"  Tiempo promedio: {avg_time/1000:.1f}s")

        # Codigo
        if s["code_runs"] > 0:
            rate = self.get_code_success_rate() * 100
            lines.append(f"\n  Codigo ejecutado: {s['code_runs']} veces")
            lines.append(f"  Exitos: {s['code_successes']}")
            lines.append(f"  Fallos: {s['code_failures']}")
            lines.append(f"  Reintentos: {s['code_retries']}")
            lines.append(f"  Tasa de exito: {rate:.0f}%")

        # Herramientas
        if s["tool_uses"]:
            lines.append(f"\n  Herramientas usadas:")
            for tool, count in sorted(s["tool_uses"].items(),
                                       key=lambda x: x[1], reverse=True):
                lines.append(f"    {tool}: {count}x")

        # Errores
        if s["errors"] > 0:
            lines.append(f"\n  Errores: {s['errors']}")

        # Fitness
        fitness = self.get_session_fitness()
        lines.append(f"\n  Fitness de sesion: {fitness}/100")

        return "\n".join(lines)

    def format_historical_report(self) -> str:
        """Genera reporte historico completo."""
        totals = self.data["totals"]
        records = self.data["records"]
        lines = ["=== METRICAS HISTORICAS ===\n"]

        lines.append(f"  Sesiones totales: {totals['total_sessions']}")
        lines.append(f"  Interacciones totales: {totals['total_interactions']}")

        # Codigo
        total_code = totals["total_code_runs"]
        if total_code > 0:
            rate = totals["total_code_successes"] / total_code * 100
            lines.append(f"\n  Codigo ejecutado: {total_code} veces")
            lines.append(f"  Tasa de exito historica: {rate:.1f}%")

        # Herramientas
        lines.append(f"  Herramientas usadas: {totals['total_tool_uses']} veces")

        # Records
        lines.append(f"\n  === RECORDS ===")
        fastest = records.get("fastest_response_ms", 0)
        if fastest > 0:
            lines.append(f"  Respuesta mas rapida: {fastest/1000:.1f}s")
        lines.append(f"  Mejor racha sin errores: {records.get('longest_streak_no_errors', 0)}")
        lines.append(f"  Max herramientas en sesion: {records.get('max_tools_one_session', 0)}")
        max_code_rate = records.get("max_code_success_rate", 0)
        if max_code_rate > 0:
            lines.append(f"  Mejor tasa de codigo: {max_code_rate*100:.0f}%")

        # Tendencia
        trend = self.get_trend()
        lines.append(f"\n  Tendencia: {trend}")

        # Fitness historico
        fitness = self.get_historical_fitness()
        lines.append(f"  Fitness historico: {fitness}/100")

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen corto para /status."""
        s = self.session
        fitness = self.get_session_fitness()
        code_info = ""
        if s["code_runs"] > 0:
            rate = self.get_code_success_rate() * 100
            code_info = f" | Codigo: {rate:.0f}% exito"

        return (
            f"  Interacciones: {s['interactions']}"
            f"{code_info}"
            f" | Fitness: {fitness}/100"
            f" | Tendencia: {self.get_trend()}"
        )
