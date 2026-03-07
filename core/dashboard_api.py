"""
GENESIS Dashboard API — Metricas en tiempo real de todos los subsistemas.

Problema:
Genesis tiene 40+ subsistemas, cada uno con su propio .status().
No hay forma centralizada de obtener todas las metricas en un formato
uniforme para un dashboard en tiempo real.

Solucion:
Un DashboardAPI que:
1. Recopila metricas de todos los subsistemas registrados
2. Expone datos en formato JSON uniforme (listo para Web UI)
3. Mantiene historial de snapshots para graficos temporales
4. Genera resumen ejecutivo del estado del sistema

Uso:
    api = DashboardAPI()
    api.register("brain", lambda: brain.get_stats())
    snapshot = api.get_snapshot()
    timeline = api.get_timeline("brain", "total_tokens")
"""
import time
import json
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime


class MetricCollector:
    """Un collector de metricas registrado para un subsistema."""

    def __init__(self, name: str, collector: Callable,
                 category: str = "general"):
        self.name = name
        self.collector = collector
        self.category = category
        self.last_value: dict = {}
        self.last_collect_time: float = 0.0
        self.collect_count: int = 0
        self.errors: int = 0

    def collect(self) -> dict:
        """Ejecuta el collector y retorna las metricas."""
        try:
            data = self.collector()
            if not isinstance(data, dict):
                data = {"value": str(data)}
            self.last_value = data
            self.last_collect_time = time.time()
            self.collect_count += 1
            return data
        except Exception as e:
            self.errors += 1
            return {"_error": str(e)}


class TimeSeriesPoint:
    """Un punto en una serie temporal."""

    def __init__(self, timestamp: float, values: dict):
        self.timestamp = timestamp
        self.values = values


class MetricTimeline:
    """Serie temporal de metricas para un subsistema."""

    def __init__(self, name: str, max_points: int = 120):
        self.name = name
        self.max_points = max_points
        self.points: list[TimeSeriesPoint] = []

    def add_point(self, values: dict):
        """Agrega un punto a la serie."""
        self.points.append(TimeSeriesPoint(time.time(), values))
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points:]

    def get_series(self, key: str) -> list[dict]:
        """Extrae una serie para una metrica especifica."""
        series = []
        for point in self.points:
            if key in point.values:
                series.append({
                    "timestamp": point.timestamp,
                    "value": point.values[key],
                })
        return series

    def get_latest(self) -> Optional[dict]:
        """Ultimo punto de la serie."""
        if self.points:
            p = self.points[-1]
            return {"timestamp": p.timestamp, "values": p.values}
        return None

    def get_range(self, start_time: float, end_time: float = 0) -> list[dict]:
        """Puntos en un rango de tiempo."""
        if end_time <= 0:
            end_time = time.time()
        return [
            {"timestamp": p.timestamp, "values": p.values}
            for p in self.points
            if start_time <= p.timestamp <= end_time
        ]


class DashboardAPI:
    """
    API de dashboard para Genesis.

    Recopila metricas de todos los subsistemas y las expone
    en formato uniforme para consumo por Web UI o CLI.
    """

    def __init__(self):
        # Collectors registrados
        self.collectors: dict[str, MetricCollector] = {}

        # Series temporales por subsistema
        self.timelines: dict[str, MetricTimeline] = {}

        # Snapshots globales
        self.snapshots: list[dict] = []
        self.max_snapshots = 60

        # Estado
        self.started_at = time.time()
        self.total_snapshots = 0

        # Categorias predefinidas
        self.categories = {
            "core": "Subsistemas principales",
            "memory": "Sistemas de memoria",
            "learning": "Aprendizaje y adaptacion",
            "tools": "Herramientas y plugins",
            "monitoring": "Monitoreo y performance",
            "general": "General",
        }

    def register(self, name: str, collector: Callable,
                 category: str = "general") -> str:
        """
        Registra un collector de metricas.

        Args:
            name: Nombre del subsistema
            collector: Funcion que retorna dict de metricas
            category: Categoria del subsistema
        """
        self.collectors[name] = MetricCollector(name, collector, category)
        self.timelines[name] = MetricTimeline(name)
        return f"Collector '{name}' registrado en categoria '{category}'"

    def unregister(self, name: str) -> bool:
        """Elimina un collector."""
        if name in self.collectors:
            del self.collectors[name]
            self.timelines.pop(name, None)
            return True
        return False

    def collect_all(self) -> dict:
        """
        Recopila metricas de todos los collectors.

        Returns:
            Dict con metricas agrupadas por categoria
        """
        snapshot = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "categories": {},
            "subsystems": {},
        }

        for name, collector in self.collectors.items():
            data = collector.collect()
            snapshot["subsystems"][name] = {
                "category": collector.category,
                "data": data,
                "collect_time": collector.last_collect_time,
            }

            # Agregar a timeline
            if name in self.timelines:
                self.timelines[name].add_point(data)

            # Agrupar por categoria
            cat = collector.category
            if cat not in snapshot["categories"]:
                snapshot["categories"][cat] = {}
            snapshot["categories"][cat][name] = data

        # Guardar snapshot
        self.snapshots.append(snapshot)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]
        self.total_snapshots += 1

        return snapshot

    def get_snapshot(self) -> dict:
        """Obtiene el snapshot mas reciente (o genera uno nuevo)."""
        if not self.snapshots:
            return self.collect_all()
        return self.snapshots[-1]

    def get_subsystem(self, name: str) -> dict:
        """Obtiene metricas de un subsistema especifico."""
        if name not in self.collectors:
            return {"error": f"Subsistema '{name}' no registrado"}
        return self.collectors[name].collect()

    def get_timeline(self, subsystem: str, metric_key: str) -> list[dict]:
        """
        Obtiene serie temporal de una metrica especifica.

        Args:
            subsystem: Nombre del subsistema
            metric_key: Clave de la metrica dentro del dict

        Returns:
            Lista de {timestamp, value}
        """
        if subsystem not in self.timelines:
            return []
        return self.timelines[subsystem].get_series(metric_key)

    def get_categories(self) -> dict:
        """Lista categorias con sus subsistemas."""
        result = {}
        for name, collector in self.collectors.items():
            cat = collector.category
            if cat not in result:
                result[cat] = {
                    "description": self.categories.get(cat, ""),
                    "subsystems": [],
                }
            result[cat]["subsystems"].append(name)
        return result

    def get_summary(self) -> dict:
        """
        Resumen ejecutivo del sistema.

        Agrega datos de alto nivel de todos los subsistemas.
        """
        snapshot = self.get_snapshot()
        uptime = time.time() - self.started_at

        summary = {
            "uptime_seconds": round(uptime, 1),
            "uptime_human": f"{uptime/3600:.1f}h" if uptime >= 3600 else f"{uptime/60:.0f}m",
            "total_snapshots": self.total_snapshots,
            "registered_collectors": len(self.collectors),
            "categories": len(set(c.category for c in self.collectors.values())),
            "collectors_with_errors": sum(
                1 for c in self.collectors.values() if c.errors > 0
            ),
        }

        return summary

    def generate_dashboard(self) -> str:
        """Genera dashboard en formato texto para CLI."""
        snapshot = self.collect_all()
        summary = self.get_summary()

        lines = [
            "=== GENESIS DASHBOARD ===",
            f"  Uptime: {summary['uptime_human']} | "
            f"Collectors: {summary['registered_collectors']} | "
            f"Snapshots: {summary['total_snapshots']}",
            "",
        ]

        # Por categoria
        for cat_name, subsystems in snapshot["categories"].items():
            cat_desc = self.categories.get(cat_name, "")
            lines.append(f"  [{cat_name.upper()}] {cat_desc}")

            for sub_name, data in subsystems.items():
                # Resumir data (primeros 3 campos)
                preview_items = list(data.items())[:4]
                preview = ", ".join(
                    f"{k}: {self._format_value(v)}"
                    for k, v in preview_items
                    if not k.startswith("_")
                )
                lines.append(f"    {sub_name:25s} {preview}")

            lines.append("")

        # Errores de collectors
        errors = [
            (name, c.errors)
            for name, c in self.collectors.items()
            if c.errors > 0
        ]
        if errors:
            lines.append("  [!] COLLECTORS CON ERRORES:")
            for name, count in errors:
                lines.append(f"    {name}: {count} errores")

        return "\n".join(lines)

    def _format_value(self, value) -> str:
        """Formatea un valor para display."""
        if isinstance(value, float):
            return f"{value:.1f}"
        if isinstance(value, (list, dict)):
            return f"({type(value).__name__})"
        s = str(value)
        return s[:30] + "..." if len(s) > 30 else s

    def export_json(self) -> str:
        """Exporta el snapshot actual como JSON string."""
        snapshot = self.get_snapshot()
        return json.dumps(snapshot, indent=2, ensure_ascii=False, default=str)

    def get_collector_stats(self) -> list[dict]:
        """Stats de todos los collectors."""
        stats = []
        for name, collector in sorted(self.collectors.items()):
            stats.append({
                "name": name,
                "category": collector.category,
                "collect_count": collector.collect_count,
                "errors": collector.errors,
                "timeline_points": len(self.timelines.get(name, MetricTimeline("")).points),
            })
        return stats

    def status(self) -> str:
        """Resumen para /status."""
        n = len(self.collectors)
        cats = len(set(c.category for c in self.collectors.values()))
        return (
            f"  Collectors: {n} | Categorias: {cats} | "
            f"Snapshots: {self.total_snapshots}"
        )
