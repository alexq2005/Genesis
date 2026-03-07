"""
GENESIS Performance Profiler — Profiling de subsistemas y deteccion de bottlenecks.

Problema:
Con 40+ subsistemas, Genesis puede volverse lento sin que sepamos
cual subsistema es el culpable. Necesitamos medir tiempos de ejecucion
por componente y detectar degradacion.

Solucion:
Un profiler que:
1. Registra tiempos de ejecucion por subsistema
2. Detecta bottlenecks (subsistemas mas lentos)
3. Genera reportes de performance con tendencias
4. Alerta cuando un subsistema se degrada

Uso:
    profiler = PerformanceProfiler()
    with profiler.measure("brain.generate"):
        response = brain.generate(prompt)
    # o bien:
    profiler.start("brain.generate")
    response = brain.generate(prompt)
    profiler.stop("brain.generate")
"""
import time
from contextlib import contextmanager
from typing import Optional
from datetime import datetime


class TimingRecord:
    """Registro de tiempos de un subsistema."""

    def __init__(self, name: str, max_samples: int = 100):
        self.name = name
        self.max_samples = max_samples
        self.samples: list[float] = []  # Duraciones en ms
        self.timestamps: list[float] = []  # Cuando se registro
        self.total_calls: int = 0
        self.total_time_ms: float = 0.0
        self.min_time_ms: float = float("inf")
        self.max_time_ms: float = 0.0
        self.errors: int = 0

    def record(self, duration_ms: float, error: bool = False):
        """Registra una medicion."""
        self.samples.append(duration_ms)
        self.timestamps.append(time.time())

        if len(self.samples) > self.max_samples:
            self.samples = self.samples[-self.max_samples:]
            self.timestamps = self.timestamps[-self.max_samples:]

        self.total_calls += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)

        if error:
            self.errors += 1

    @property
    def avg_ms(self) -> float:
        """Promedio de las ultimas muestras."""
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    @property
    def p95_ms(self) -> float:
        """Percentil 95 de las ultimas muestras."""
        if not self.samples:
            return 0.0
        sorted_s = sorted(self.samples)
        idx = int(len(sorted_s) * 0.95)
        return sorted_s[min(idx, len(sorted_s) - 1)]

    @property
    def p50_ms(self) -> float:
        """Mediana (percentil 50)."""
        if not self.samples:
            return 0.0
        sorted_s = sorted(self.samples)
        idx = len(sorted_s) // 2
        return sorted_s[idx]

    @property
    def error_rate(self) -> float:
        """Tasa de errores."""
        if self.total_calls == 0:
            return 0.0
        return round(self.errors / self.total_calls * 100, 1)

    def trend(self) -> str:
        """Tendencia: mejorando, estable, o degradando."""
        if len(self.samples) < 10:
            return "insufficient_data"

        half = len(self.samples) // 2
        first_half = sum(self.samples[:half]) / half
        second_half = sum(self.samples[half:]) / (len(self.samples) - half)

        if first_half == 0:
            return "stable"

        change = (second_half - first_half) / first_half * 100

        if change > 20:
            return "degrading"
        elif change < -20:
            return "improving"
        return "stable"

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "avg_ms": round(self.avg_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "min_ms": round(self.min_time_ms, 2) if self.min_time_ms != float("inf") else 0,
            "max_ms": round(self.max_time_ms, 2),
            "total_time_ms": round(self.total_time_ms, 2),
            "errors": self.errors,
            "error_rate": self.error_rate,
            "samples": len(self.samples),
            "trend": self.trend(),
        }


class PerformanceProfiler:
    """
    Profiler de rendimiento para subsistemas de Genesis.

    Mide tiempos de ejecucion, detecta bottlenecks y genera reportes.
    """

    def __init__(self):
        # Registros por subsistema
        self.records: dict[str, TimingRecord] = {}

        # Mediciones en progreso
        self._active: dict[str, float] = {}

        # Estado
        self.enabled = True
        self.started_at = time.time()

        # Thresholds para alertas (ms)
        self.slow_threshold_ms = 5000.0  # 5 segundos = lento
        self.very_slow_threshold_ms = 30000.0  # 30 segundos = muy lento

    def _get_record(self, name: str) -> TimingRecord:
        """Obtiene o crea un registro."""
        if name not in self.records:
            self.records[name] = TimingRecord(name)
        return self.records[name]

    def start(self, name: str):
        """Inicia una medicion."""
        if not self.enabled:
            return
        self._active[name] = time.time()

    def stop(self, name: str, error: bool = False) -> float:
        """
        Detiene una medicion y registra el resultado.

        Returns:
            Duracion en ms
        """
        if not self.enabled or name not in self._active:
            return 0.0

        start_time = self._active.pop(name)
        duration_ms = (time.time() - start_time) * 1000
        self._get_record(name).record(duration_ms, error=error)
        return duration_ms

    @contextmanager
    def measure(self, name: str):
        """
        Context manager para medir tiempo.

        Uso:
            with profiler.measure("brain.generate"):
                result = brain.generate(prompt)
        """
        self.start(name)
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            self.stop(name, error=error)

    def record_direct(self, name: str, duration_ms: float, error: bool = False):
        """Registra una medicion directa (sin start/stop)."""
        if not self.enabled:
            return
        self._get_record(name).record(duration_ms, error=error)

    def get_bottlenecks(self, top_n: int = 5) -> list[dict]:
        """
        Identifica los subsistemas mas lentos.

        Returns:
            Lista de los top_n subsistemas ordenados por avg_ms desc
        """
        all_stats = [r.get_stats() for r in self.records.values()]
        all_stats.sort(key=lambda x: x["avg_ms"], reverse=True)
        return all_stats[:top_n]

    def get_most_called(self, top_n: int = 5) -> list[dict]:
        """Subsistemas con mas llamadas."""
        all_stats = [r.get_stats() for r in self.records.values()]
        all_stats.sort(key=lambda x: x["total_calls"], reverse=True)
        return all_stats[:top_n]

    def get_highest_error_rate(self, top_n: int = 5) -> list[dict]:
        """Subsistemas con mayor tasa de error."""
        all_stats = [
            r.get_stats() for r in self.records.values()
            if r.total_calls > 0
        ]
        all_stats.sort(key=lambda x: x["error_rate"], reverse=True)
        return all_stats[:top_n]

    def get_degrading(self) -> list[dict]:
        """Subsistemas que estan degradandose."""
        degrading = []
        for record in self.records.values():
            if record.trend() == "degrading":
                degrading.append(record.get_stats())
        return degrading

    def get_slow_operations(self) -> list[dict]:
        """Operaciones que superan el threshold de lentitud."""
        slow = []
        for record in self.records.values():
            stats = record.get_stats()
            if stats["avg_ms"] > self.slow_threshold_ms:
                slow.append(stats)
        slow.sort(key=lambda x: x["avg_ms"], reverse=True)
        return slow

    def reset(self, name: str = ""):
        """Resetea registros de un subsistema o todos."""
        if name:
            self.records.pop(name, None)
        else:
            self.records.clear()
            self._active.clear()

    def toggle(self) -> bool:
        """Activa/desactiva el profiler."""
        self.enabled = not self.enabled
        return self.enabled

    def generate_report(self) -> str:
        """Genera reporte completo de performance."""
        if not self.records:
            return "  Sin datos de profiling. Interactua con Genesis para generar datos."

        uptime = time.time() - self.started_at
        uptime_str = f"{uptime/3600:.1f}h" if uptime >= 3600 else f"{uptime/60:.0f}m"

        lines = [
            "=== PERFORMANCE REPORT ===",
            f"  Estado: {'ACTIVO' if self.enabled else 'DESACTIVADO'}",
            f"  Uptime: {uptime_str} | Subsistemas: {len(self.records)}",
        ]

        # Total time
        total_time = sum(r.total_time_ms for r in self.records.values())
        lines.append(f"  Tiempo total medido: {total_time/1000:.1f}s")

        # Bottlenecks
        bottlenecks = self.get_bottlenecks(5)
        if bottlenecks:
            lines.append(f"\n  TOP 5 MAS LENTOS (avg):")
            for b in bottlenecks:
                trend_icon = {"improving": "v", "stable": "=", "degrading": "^"}.get(
                    b["trend"], "?"
                )
                lines.append(
                    f"    [{trend_icon}] {b['name']:30s} "
                    f"avg:{b['avg_ms']:8.1f}ms  p95:{b['p95_ms']:8.1f}ms  "
                    f"calls:{b['total_calls']}"
                )

        # Most called
        most_called = self.get_most_called(5)
        if most_called:
            lines.append(f"\n  TOP 5 MAS LLAMADOS:")
            for m in most_called:
                lines.append(
                    f"    {m['name']:30s} "
                    f"calls:{m['total_calls']:6d}  avg:{m['avg_ms']:8.1f}ms  "
                    f"errors:{m['errors']}"
                )

        # Degrading
        degrading = self.get_degrading()
        if degrading:
            lines.append(f"\n  [!] DEGRADANDOSE ({len(degrading)}):")
            for d in degrading:
                lines.append(f"    {d['name']:30s} avg:{d['avg_ms']:.1f}ms")

        # Slow operations
        slow = self.get_slow_operations()
        if slow:
            lines.append(f"\n  [!] OPERACIONES LENTAS (>{self.slow_threshold_ms:.0f}ms):")
            for s in slow:
                lines.append(
                    f"    {s['name']:30s} avg:{s['avg_ms']:.1f}ms  "
                    f"max:{s['max_ms']:.1f}ms"
                )

        # All subsystems summary
        lines.append(f"\n  TODOS LOS SUBSISTEMAS ({len(self.records)}):")
        all_sorted = sorted(self.records.values(), key=lambda r: r.name)
        for record in all_sorted:
            stats = record.get_stats()
            err_str = f" ERR:{stats['errors']}" if stats['errors'] > 0 else ""
            lines.append(
                f"    {stats['name']:30s} "
                f"avg:{stats['avg_ms']:8.1f}ms  "
                f"calls:{stats['total_calls']:4d}{err_str}"
            )

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen breve para /status."""
        n = len(self.records)
        total_calls = sum(r.total_calls for r in self.records.values())
        degrading = len(self.get_degrading())
        state = "ON" if self.enabled else "OFF"
        deg_str = f", {degrading} degradando" if degrading > 0 else ""
        return (
            f"  Estado: {state} | Subsistemas: {n} | "
            f"Calls: {total_calls}{deg_str}"
        )
