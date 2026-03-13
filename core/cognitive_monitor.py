"""
GENESIS — Cognitive Monitor (v2.9)

Monitoreo de carga cognitiva del sistema. Rastrea tokens usados,
latencia, utilización de contexto, y detecta sobrecarga. Sugiere
optimizaciones cuando el sistema está bajo presión.

Componentes:
- CognitiveMetric: métrica cognitiva con umbral
- CognitiveLoad: snapshot de carga cognitiva
- OverloadDetector: detecta estados de sobrecarga
- CognitiveMonitor: coordinador con persistencia
"""
import time
import json
from pathlib import Path
from collections import defaultdict, deque


class CognitiveMetric:
    """Una métrica cognitiva con umbral de alarma."""

    def __init__(self, name: str, unit: str = "", warning_threshold: float = 0.8,
                 critical_threshold: float = 0.95):
        self.name = name
        self.unit = unit
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.values = deque(maxlen=100)
        self.total_samples = 0

    def record(self, value: float):
        """Registra un valor normalizado (0.0 - 1.0)."""
        self.values.append({"value": value, "time": time.time()})
        self.total_samples += 1

    @property
    def current(self) -> float:
        if not self.values:
            return 0.0
        return self.values[-1]["value"]

    @property
    def average(self) -> float:
        if not self.values:
            return 0.0
        return sum(v["value"] for v in self.values) / len(self.values)

    @property
    def peak(self) -> float:
        if not self.values:
            return 0.0
        return max(v["value"] for v in self.values)

    @property
    def status(self) -> str:
        val = self.current
        if val >= self.critical_threshold:
            return "critical"
        elif val >= self.warning_threshold:
            return "warning"
        return "normal"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "unit": self.unit,
            "current": round(self.current, 4),
            "average": round(self.average, 4),
            "peak": round(self.peak, 4),
            "total_samples": self.total_samples,
            "status": self.status,
        }


class CognitiveLoad:
    """Snapshot de carga cognitiva del sistema."""

    def __init__(self):
        self.context_utilization = 0.0  # % del contexto usado
        self.response_latency = 0.0     # Latencia normalizada
        self.memory_pressure = 0.0      # Presión de memoria
        self.module_load = 0.0          # Carga de módulos activos
        self.timestamp = time.time()

    @property
    def overall_load(self) -> float:
        """Carga total ponderada (0.0 - 1.0)."""
        return min(1.0, (
            self.context_utilization * 0.35 +
            self.response_latency * 0.25 +
            self.memory_pressure * 0.2 +
            self.module_load * 0.2
        ))

    @property
    def load_level(self) -> str:
        load = self.overall_load
        if load >= 0.9:
            return "critical"
        elif load >= 0.7:
            return "high"
        elif load >= 0.4:
            return "moderate"
        return "low"

    def to_dict(self) -> dict:
        return {
            "context_utilization": round(self.context_utilization, 4),
            "response_latency": round(self.response_latency, 4),
            "memory_pressure": round(self.memory_pressure, 4),
            "module_load": round(self.module_load, 4),
            "overall_load": round(self.overall_load, 4),
            "load_level": self.load_level,
            "timestamp": self.timestamp,
        }


class OverloadDetector:
    """Detecta estados de sobrecarga y sugiere optimizaciones."""

    SUGGESTIONS = {
        "context_utilization": [
            "Reducir contexto inyectado por módulos",
            "Comprimir historial de conversación",
            "Desactivar módulos de bajo impacto",
        ],
        "response_latency": [
            "Reducir max_tokens en generación",
            "Simplificar system prompt",
            "Usar cache de respuestas similares",
        ],
        "memory_pressure": [
            "Ejecutar evicción de memorias antiguas",
            "Limpiar caches de módulos",
            "Reducir window_size de streams",
        ],
        "module_load": [
            "Desactivar módulos no esenciales",
            "Reducir frecuencia de checks",
            "Posponer operaciones no urgentes",
        ],
    }

    def detect(self, load: CognitiveLoad) -> list:
        """Detecta problemas y sugiere optimizaciones."""
        issues = []

        if load.context_utilization > 0.8:
            issues.append({
                "area": "context_utilization",
                "severity": "critical" if load.context_utilization > 0.95 else "warning",
                "value": load.context_utilization,
                "suggestions": self.SUGGESTIONS["context_utilization"],
            })

        if load.response_latency > 0.7:
            issues.append({
                "area": "response_latency",
                "severity": "critical" if load.response_latency > 0.9 else "warning",
                "value": load.response_latency,
                "suggestions": self.SUGGESTIONS["response_latency"],
            })

        if load.memory_pressure > 0.8:
            issues.append({
                "area": "memory_pressure",
                "severity": "critical" if load.memory_pressure > 0.95 else "warning",
                "value": load.memory_pressure,
                "suggestions": self.SUGGESTIONS["memory_pressure"],
            })

        if load.module_load > 0.8:
            issues.append({
                "area": "module_load",
                "severity": "warning",
                "value": load.module_load,
                "suggestions": self.SUGGESTIONS["module_load"],
            })

        return issues


class CognitiveMonitor:
    """
    Coordinador de monitoreo cognitivo.
    Rastrea carga del sistema y sugiere optimizaciones.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/cognitive")
        self.data_file = self.base_dir / "cognitive_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.metrics = {
            "context_utilization": CognitiveMetric("context_utilization", "%"),
            "response_latency": CognitiveMetric("response_latency", "s"),
            "memory_pressure": CognitiveMetric("memory_pressure", "%"),
            "module_load": CognitiveMetric("module_load", "%"),
        }
        self.load_history = deque(maxlen=50)
        self.detector = OverloadDetector()
        self.total_snapshots = 0
        self.overload_count = 0
        self.enabled = True

        self._load()

    def record_snapshot(self, context_util: float = 0.0, latency: float = 0.0,
                        memory_pressure: float = 0.0, module_load: float = 0.0):
        """Registra un snapshot de carga cognitiva."""
        if not self.enabled:
            return None

        load = CognitiveLoad()
        load.context_utilization = max(0.0, min(1.0, context_util))
        load.response_latency = max(0.0, min(1.0, latency))
        load.memory_pressure = max(0.0, min(1.0, memory_pressure))
        load.module_load = max(0.0, min(1.0, module_load))

        self.metrics["context_utilization"].record(load.context_utilization)
        self.metrics["response_latency"].record(load.response_latency)
        self.metrics["memory_pressure"].record(load.memory_pressure)
        self.metrics["module_load"].record(load.module_load)

        self.load_history.append(load.to_dict())
        self.total_snapshots += 1

        if load.overall_load > 0.8:
            self.overload_count += 1

        return load

    def get_current_load(self) -> CognitiveLoad:
        """Obtiene la carga cognitiva actual."""
        load = CognitiveLoad()
        load.context_utilization = self.metrics["context_utilization"].current
        load.response_latency = self.metrics["response_latency"].current
        load.memory_pressure = self.metrics["memory_pressure"].current
        load.module_load = self.metrics["module_load"].current
        return load

    def detect_overload(self) -> list:
        """Detecta sobrecarga y retorna sugerencias."""
        load = self.get_current_load()
        return self.detector.detect(load)

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de carga para prompt."""
        if not self.enabled:
            return ""

        load = self.get_current_load()
        if load.load_level in ("low", "moderate"):
            return ""

        issues = self.detect_overload()
        if not issues:
            return ""

        lines = [f"[CARGA COGNITIVA: {load.load_level.upper()}]"]
        for issue in issues[:2]:
            lines.append(f"  {issue['area']}: {issue['value']:.0%} ({issue['severity']})")
        return "\n".join(lines)[:max_chars]

    def get_stats(self) -> dict:
        load = self.get_current_load()
        return {
            "overall_load": round(load.overall_load, 3),
            "load_level": load.load_level,
            "total_snapshots": self.total_snapshots,
            "overload_count": self.overload_count,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }

    def status(self) -> str:
        load = self.get_current_load()
        return (f"Carga: {load.overall_load:.0%} ({load.load_level}) | "
                f"Snapshots: {self.total_snapshots} | "
                f"Sobrecargas: {self.overload_count}")

    def generate_report(self) -> str:
        lines = ["=== COGNITIVE MONITOR REPORT ==="]
        load = self.get_current_load()
        lines.append(f"Carga total: {load.overall_load:.1%} ({load.load_level})")
        lines.append(f"Total snapshots: {self.total_snapshots}")
        lines.append(f"Sobrecargas detectadas: {self.overload_count}")

        lines.append(f"\nMetricas:")
        for name, metric in self.metrics.items():
            bar = "█" * int(metric.current * 20) + "░" * (20 - int(metric.current * 20))
            lines.append(f"  {name:25s} [{bar}] {metric.current:.0%} "
                         f"(avg={metric.average:.0%}, peak={metric.peak:.0%}) "
                         f"[{metric.status}]")

        issues = self.detect_overload()
        if issues:
            lines.append(f"\nProblemas detectados:")
            for issue in issues:
                lines.append(f"  [{issue['severity']}] {issue['area']}: {issue['value']:.0%}")
                for s in issue["suggestions"][:2]:
                    lines.append(f"    → {s}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_snapshots": self.total_snapshots,
            "overload_count": self.overload_count,
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_snapshots = data.get("total_snapshots", 0)
            self.overload_count = data.get("overload_count", 0)
        except Exception:
            pass

    def clear(self):
        for m in self.metrics.values():
            m.values.clear()
            m.total_samples = 0
        self.load_history.clear()
        self.total_snapshots = 0
        self.overload_count = 0
