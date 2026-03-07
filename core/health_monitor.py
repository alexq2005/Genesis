"""
GENESIS Health Monitor — Monitoreo de salud del sistema en produccion.

Problema:
Con 30+ subsistemas, Genesis necesita detectar automaticamente cuando
algo esta degradado (LLM no responde, disco lleno, memoria corrupta, etc.)
antes de que el usuario experimente un error.

Solucion:
Un HealthMonitor que ejecuta checks periodicos sobre cada componente,
genera reportes de salud, y emite alertas cuando algo esta fuera de rango.

Uso:
    monitor = HealthMonitor()
    monitor.register_check("brain", check_brain_fn)
    report = monitor.run_all_checks()
    alerts = monitor.get_active_alerts()
"""
import os
import time
import psutil
import shutil
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime


class HealthStatus:
    """Enum-like para estados de salud."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Resultado de un check de salud individual."""

    def __init__(self, name: str, status: str = HealthStatus.UNKNOWN,
                 message: str = "", value: float = 0.0,
                 threshold_warn: float = 0.0, threshold_crit: float = 0.0):
        self.name = name
        self.status = status
        self.message = message
        self.value = value
        self.threshold_warn = threshold_warn
        self.threshold_crit = threshold_crit
        self.timestamp = time.time()
        self.duration_ms = 0.0  # Tiempo que tardo el check

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "value": self.value,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 2),
        }

    def icon(self) -> str:
        icons = {
            HealthStatus.HEALTHY: "[OK]",
            HealthStatus.DEGRADED: "[WARN]",
            HealthStatus.UNHEALTHY: "[CRIT]",
            HealthStatus.UNKNOWN: "[??]",
        }
        return icons.get(self.status, "[??]")


class Alert:
    """Alerta activa del sistema."""

    def __init__(self, source: str, level: str, message: str):
        self.source = source
        self.level = level  # "warning" o "critical"
        self.message = message
        self.timestamp = time.time()
        self.acknowledged = False

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


class ResourceMetrics:
    """Metricas de recursos del sistema (RAM, disco, CPU)."""

    def __init__(self):
        self.snapshots: list[dict] = []
        self.max_snapshots = 60  # Mantener 60 muestras

    def take_snapshot(self) -> dict:
        """Captura metricas actuales del sistema."""
        snapshot = {
            "timestamp": time.time(),
            "cpu_percent": 0.0,
            "ram_used_mb": 0.0,
            "ram_total_mb": 0.0,
            "ram_percent": 0.0,
            "disk_free_gb": 0.0,
            "disk_total_gb": 0.0,
            "disk_percent": 0.0,
        }
        try:
            # CPU
            snapshot["cpu_percent"] = psutil.cpu_percent(interval=0.1)

            # RAM
            mem = psutil.virtual_memory()
            snapshot["ram_used_mb"] = round(mem.used / (1024 * 1024), 1)
            snapshot["ram_total_mb"] = round(mem.total / (1024 * 1024), 1)
            snapshot["ram_percent"] = mem.percent

            # Disco (particion donde esta Genesis)
            disk = shutil.disk_usage(Path(__file__).parent.parent)
            snapshot["disk_free_gb"] = round(disk.free / (1024**3), 2)
            snapshot["disk_total_gb"] = round(disk.total / (1024**3), 2)
            snapshot["disk_percent"] = round(
                (disk.used / disk.total) * 100, 1
            ) if disk.total > 0 else 0.0
        except Exception:
            pass

        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        return snapshot

    def get_averages(self) -> dict:
        """Promedio de las ultimas muestras."""
        if not self.snapshots:
            return {"cpu_avg": 0, "ram_avg": 0, "disk_percent": 0}
        n = len(self.snapshots)
        cpu_avg = sum(s["cpu_percent"] for s in self.snapshots) / n
        ram_avg = sum(s["ram_percent"] for s in self.snapshots) / n
        disk_pct = self.snapshots[-1]["disk_percent"] if self.snapshots else 0
        return {
            "cpu_avg": round(cpu_avg, 1),
            "ram_avg": round(ram_avg, 1),
            "disk_percent": disk_pct,
            "samples": n,
        }

    def get_latest(self) -> dict:
        """Ultima muestra."""
        if self.snapshots:
            return self.snapshots[-1]
        return self.take_snapshot()


class HealthMonitor:
    """
    Monitor de salud de Genesis.

    Registra checks de salud para cada subsistema y ejecuta
    verificaciones periodicas. Genera reportes y alertas.
    """

    def __init__(self, base_dir: str = ""):
        if not base_dir:
            base_dir = str(Path(__file__).parent.parent)
        self.base_dir = Path(base_dir)

        # Checks registrados: {nombre: callable}
        self._checks: dict[str, Callable] = {}

        # Resultados del ultimo check
        self.last_results: dict[str, HealthCheck] = {}

        # Alertas activas
        self.alerts: list[Alert] = []
        self.max_alerts = 50

        # Metricas de recursos
        self.resources = ResourceMetrics()

        # Historial de checks
        self.check_count = 0
        self.last_check_time = 0.0

        # Thresholds
        self.thresholds = {
            "ram_warn": 85.0,      # % RAM para warning
            "ram_crit": 95.0,      # % RAM para critical
            "disk_warn": 90.0,     # % disco para warning
            "disk_crit": 95.0,     # % disco para critical
            "cpu_warn": 90.0,      # % CPU para warning
            "check_timeout": 5.0,  # Segundos max por check
        }

        # Registrar checks built-in
        self._register_builtin_checks()

    def _register_builtin_checks(self):
        """Registra los checks de salud incorporados."""
        self.register_check("resources", self._check_resources)
        self.register_check("data_dirs", self._check_data_dirs)
        self.register_check("disk_space", self._check_disk_space)

    def register_check(self, name: str, check_fn: Callable) -> None:
        """
        Registra un check de salud.

        Args:
            name: Nombre unico del check
            check_fn: Funcion que retorna un HealthCheck
        """
        self._checks[name] = check_fn

    def unregister_check(self, name: str) -> bool:
        """Elimina un check registrado."""
        if name in self._checks:
            del self._checks[name]
            return True
        return False

    def run_check(self, name: str) -> Optional[HealthCheck]:
        """Ejecuta un check individual por nombre."""
        if name not in self._checks:
            return None

        start = time.time()
        try:
            result = self._checks[name]()
            if not isinstance(result, HealthCheck):
                result = HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=str(result),
                )
            result.duration_ms = (time.time() - start) * 1000
        except Exception as e:
            result = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check fallo: {e}",
            )
            result.duration_ms = (time.time() - start) * 1000

        self.last_results[name] = result

        # Generar alertas si necesario
        if result.status == HealthStatus.DEGRADED:
            self._add_alert(name, "warning", result.message)
        elif result.status == HealthStatus.UNHEALTHY:
            self._add_alert(name, "critical", result.message)

        return result

    def run_all_checks(self) -> dict[str, HealthCheck]:
        """Ejecuta todos los checks registrados."""
        results = {}
        for name in self._checks:
            results[name] = self.run_check(name)
        self.check_count += 1
        self.last_check_time = time.time()
        return results

    def _add_alert(self, source: str, level: str, message: str):
        """Agrega una alerta si no existe una similar activa."""
        # Evitar alertas duplicadas del mismo source
        for alert in self.alerts:
            if alert.source == source and not alert.acknowledged:
                alert.message = message
                alert.timestamp = time.time()
                return

        alert = Alert(source=source, level=level, message=message)
        self.alerts.append(alert)
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

    def get_active_alerts(self) -> list[Alert]:
        """Retorna alertas no reconocidas."""
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_alert(self, index: int) -> bool:
        """Reconoce una alerta por indice."""
        active = self.get_active_alerts()
        if 0 <= index < len(active):
            active[index].acknowledged = True
            return True
        return False

    def acknowledge_all(self) -> int:
        """Reconoce todas las alertas activas."""
        count = 0
        for alert in self.alerts:
            if not alert.acknowledged:
                alert.acknowledged = True
                count += 1
        return count

    def get_overall_status(self) -> str:
        """Estado general del sistema basado en todos los checks."""
        if not self.last_results:
            return HealthStatus.UNKNOWN

        statuses = [r.status for r in self.last_results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    # ─── Built-in checks ─────────────────────────────

    def _check_resources(self) -> HealthCheck:
        """Check de recursos del sistema (CPU, RAM)."""
        snapshot = self.resources.take_snapshot()

        ram_pct = snapshot["ram_percent"]
        cpu_pct = snapshot["cpu_percent"]

        if ram_pct >= self.thresholds["ram_crit"]:
            return HealthCheck(
                name="resources",
                status=HealthStatus.UNHEALTHY,
                message=f"RAM critica: {ram_pct}% usada ({snapshot['ram_used_mb']:.0f}MB / {snapshot['ram_total_mb']:.0f}MB)",
                value=ram_pct,
            )
        elif ram_pct >= self.thresholds["ram_warn"]:
            return HealthCheck(
                name="resources",
                status=HealthStatus.DEGRADED,
                message=f"RAM alta: {ram_pct}% usada",
                value=ram_pct,
            )

        return HealthCheck(
            name="resources",
            status=HealthStatus.HEALTHY,
            message=f"CPU: {cpu_pct}% | RAM: {ram_pct}% ({snapshot['ram_used_mb']:.0f}MB)",
            value=ram_pct,
        )

    def _check_data_dirs(self) -> HealthCheck:
        """Check de directorios de datos."""
        dirs_to_check = [
            self.base_dir / "memory_data",
            self.base_dir / "evolution_data",
        ]

        missing = []
        for d in dirs_to_check:
            if not d.exists():
                missing.append(d.name)

        if missing:
            return HealthCheck(
                name="data_dirs",
                status=HealthStatus.DEGRADED,
                message=f"Directorios faltantes: {', '.join(missing)}",
            )

        return HealthCheck(
            name="data_dirs",
            status=HealthStatus.HEALTHY,
            message=f"{len(dirs_to_check)} directorios OK",
        )

    def _check_disk_space(self) -> HealthCheck:
        """Check de espacio en disco."""
        try:
            disk = shutil.disk_usage(self.base_dir)
            free_gb = disk.free / (1024**3)
            pct_used = (disk.used / disk.total) * 100 if disk.total > 0 else 0

            if pct_used >= self.thresholds["disk_crit"]:
                return HealthCheck(
                    name="disk_space",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Disco critico: {pct_used:.1f}% usado, {free_gb:.1f}GB libre",
                    value=pct_used,
                )
            elif pct_used >= self.thresholds["disk_warn"]:
                return HealthCheck(
                    name="disk_space",
                    status=HealthStatus.DEGRADED,
                    message=f"Disco alto: {pct_used:.1f}% usado, {free_gb:.1f}GB libre",
                    value=pct_used,
                )

            return HealthCheck(
                name="disk_space",
                status=HealthStatus.HEALTHY,
                message=f"Disco: {pct_used:.1f}% usado, {free_gb:.1f}GB libre",
                value=pct_used,
            )
        except Exception as e:
            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"No se pudo verificar disco: {e}",
            )

    # ─── Checks que requieren subsistemas (se registran desde genesis.py) ───

    def create_brain_check(self, brain) -> Callable:
        """Crea un check para el Brain/LLM."""
        def check_brain() -> HealthCheck:
            try:
                available = brain.is_available()
                stats = brain.get_stats()
                if available:
                    return HealthCheck(
                        name="brain",
                        status=HealthStatus.HEALTHY,
                        message=f"LLM disponible: {stats.get('model', 'unknown')} | Tokens: {stats.get('total_tokens', 0)}",
                    )
                else:
                    return HealthCheck(
                        name="brain",
                        status=HealthStatus.UNHEALTHY,
                        message="LLM no disponible",
                    )
            except Exception as e:
                return HealthCheck(
                    name="brain",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Error verificando LLM: {e}",
                )
        return check_brain

    def create_memory_check(self, memory) -> Callable:
        """Crea un check para el sistema de memoria."""
        def check_memory() -> HealthCheck:
            try:
                st_count = len(memory.short_term)
                lt_count = memory.long_term.count() if hasattr(memory.long_term, 'count') else 0
                return HealthCheck(
                    name="memory",
                    status=HealthStatus.HEALTHY,
                    message=f"Corto plazo: {st_count} msgs | Largo plazo: {lt_count} entries",
                )
            except Exception as e:
                return HealthCheck(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    message=f"Error en memoria: {e}",
                )
        return check_memory

    # ─── Reportes ─────────────────────────────────────

    def generate_report(self) -> str:
        """Genera un reporte completo de salud."""
        if not self.last_results:
            self.run_all_checks()

        overall = self.get_overall_status()
        icon_map = {
            HealthStatus.HEALTHY: "[OK]",
            HealthStatus.DEGRADED: "[WARN]",
            HealthStatus.UNHEALTHY: "[CRIT]",
            HealthStatus.UNKNOWN: "[??]",
        }

        lines = [
            f"=== HEALTH REPORT ===",
            f"Estado general: {icon_map.get(overall, '??')} {overall.upper()}",
            f"Checks: {self.check_count} ejecuciones totales",
            f"",
        ]

        # Resultados individuales
        for name, result in sorted(self.last_results.items()):
            lines.append(f"  {result.icon()} {name}: {result.message} ({result.duration_ms:.0f}ms)")

        # Alertas activas
        active_alerts = self.get_active_alerts()
        if active_alerts:
            lines.append(f"\n  ALERTAS ACTIVAS ({len(active_alerts)}):")
            for i, alert in enumerate(active_alerts):
                ts = datetime.fromtimestamp(alert.timestamp).strftime("%H:%M:%S")
                lines.append(f"    [{i}] [{alert.level.upper()}] {alert.source}: {alert.message} ({ts})")

        # Metricas de recursos
        latest = self.resources.get_latest()
        lines.append(f"\n  RECURSOS:")
        lines.append(f"    CPU: {latest['cpu_percent']}%")
        lines.append(f"    RAM: {latest['ram_used_mb']:.0f}MB / {latest['ram_total_mb']:.0f}MB ({latest['ram_percent']}%)")
        lines.append(f"    Disco: {latest['disk_free_gb']:.1f}GB libre ({latest['disk_percent']}% usado)")

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen breve para /status."""
        overall = self.get_overall_status()
        alerts = len(self.get_active_alerts())
        checks = len(self._checks)
        latest = self.resources.get_latest()
        alert_str = f", {alerts} alertas" if alerts > 0 else ""
        return (
            f"  Estado: {overall.upper()} | Checks: {checks}{alert_str}\n"
            f"  RAM: {latest['ram_percent']}% | Disco: {latest['disk_percent']}% usado"
        )
