"""
GENESIS — Anomaly Detector (v2.7)

Detección de anomalías en métricas, patrones de conversación
y salud del sistema. Usa Z-score, medias móviles y detección
de trend breaks para alertar sobre comportamientos inusuales.

Componentes:
- MetricStream: serie temporal con estadísticas incrementales
- ZScoreDetector: detección por Z-score (desviaciones estándar)
- TrendBreakDetector: detecta cambios abruptos de tendencia
- AnomalyDetector: coordinador con múltiples streams
"""
import time
import json
import math
from pathlib import Path
from collections import defaultdict, deque


class MetricStream:
    """Serie temporal de una métrica con estadísticas incrementales."""

    def __init__(self, name: str, window_size: int = 50):
        self.name = name
        self.window_size = window_size
        self.values = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        self.total_count = 0
        self._sum = 0.0
        self._sum_sq = 0.0

    def add(self, value: float, timestamp: float = None):
        """Agrega un valor a la serie."""
        self.values.append(value)
        self.timestamps.append(timestamp or time.time())
        self.total_count += 1
        self._sum += value
        self._sum_sq += value * value

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    @property
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        mean = self.mean
        variance = sum((v - mean) ** 2 for v in self.values) / len(self.values)
        return math.sqrt(variance)

    @property
    def last(self) -> float:
        return self.values[-1] if self.values else 0.0

    def moving_average(self, window: int = 5) -> float:
        """Media móvil de los últimos N valores."""
        if not self.values:
            return 0.0
        recent = list(self.values)[-window:]
        return sum(recent) / len(recent)

    def trend(self) -> str:
        """Tendencia: 'rising', 'falling', 'stable'."""
        if len(self.values) < 4:
            return "stable"
        mid = len(self.values) // 2
        first_half = sum(list(self.values)[:mid]) / mid
        second_half = sum(list(self.values)[mid:]) / (len(self.values) - mid)
        diff = second_half - first_half
        threshold = self.std * 0.5 if self.std > 0 else abs(first_half) * 0.1
        if diff > threshold:
            return "rising"
        elif diff < -threshold:
            return "falling"
        return "stable"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "values": list(self.values),
            "timestamps": list(self.timestamps),
            "total_count": self.total_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MetricStream":
        ms = cls(name=data.get("name", ""), window_size=50)
        for v, t in zip(data.get("values", []), data.get("timestamps", [])):
            ms.values.append(v)
            ms.timestamps.append(t)
        ms.total_count = data.get("total_count", len(ms.values))
        ms._sum = sum(ms.values)
        ms._sum_sq = sum(v * v for v in ms.values)
        return ms


class Anomaly:
    """Una anomalía detectada."""

    def __init__(self, metric_name: str, value: float, expected: float,
                 severity: str = "warning", detector: str = ""):
        self.metric_name = metric_name
        self.value = value
        self.expected = expected
        self.deviation = abs(value - expected)
        self.severity = severity      # "info", "warning", "critical"
        self.detector = detector      # Qué detector la encontró
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "metric": self.metric_name,
            "value": round(self.value, 4),
            "expected": round(self.expected, 4),
            "deviation": round(self.deviation, 4),
            "severity": self.severity,
            "detector": self.detector,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return (f"Anomaly({self.metric_name}: {self.value:.2f} "
                f"vs expected {self.expected:.2f}, {self.severity})")


class ZScoreDetector:
    """Detección de anomalías por Z-score."""

    def __init__(self, warning_threshold: float = 2.0, critical_threshold: float = 3.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def check(self, stream: MetricStream) -> Anomaly:
        """Verifica si el último valor es anómalo."""
        if stream.count < 5:
            return None

        mean = stream.mean
        std = stream.std
        if std == 0:
            return None

        z_score = abs(stream.last - mean) / std

        if z_score >= self.critical_threshold:
            return Anomaly(stream.name, stream.last, mean,
                           severity="critical", detector="zscore")
        elif z_score >= self.warning_threshold:
            return Anomaly(stream.name, stream.last, mean,
                           severity="warning", detector="zscore")
        return None


class TrendBreakDetector:
    """Detecta cambios abruptos de tendencia."""

    def __init__(self, sensitivity: float = 0.3):
        self.sensitivity = sensitivity
        self._last_trends = {}

    def check(self, stream: MetricStream) -> Anomaly:
        """Verifica si hubo un cambio de tendencia."""
        if stream.count < 8:
            return None

        current_trend = stream.trend()
        last_trend = self._last_trends.get(stream.name, "stable")
        self._last_trends[stream.name] = current_trend

        # Detectar cambio de tendencia
        if last_trend != current_trend and last_trend != "stable" and current_trend != "stable":
            return Anomaly(stream.name, stream.last, stream.mean,
                           severity="warning",
                           detector=f"trend_break:{last_trend}->{current_trend}")
        return None


class AnomalyDetector:
    """
    Coordinador de detección de anomalías.
    Gestiona múltiples streams de métricas y aplica detectores.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/anomaly")
        self.data_file = self.base_dir / "anomaly_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.streams = {}          # name -> MetricStream
        self.anomalies = []        # Últimas anomalías
        self.zscore = ZScoreDetector()
        self.trend_break = TrendBreakDetector()
        self.max_anomalies = 100
        self.total_checks = 0
        self.total_anomalies = 0
        self.enabled = True

        self._load()

    def record(self, metric_name: str, value: float):
        """Registra un valor en un stream."""
        if not self.enabled:
            return

        if metric_name not in self.streams:
            self.streams[metric_name] = MetricStream(metric_name)
        self.streams[metric_name].add(value)

    def check_all(self) -> list:
        """Ejecuta todos los detectores en todos los streams."""
        if not self.enabled:
            return []

        new_anomalies = []
        self.total_checks += 1

        for stream in self.streams.values():
            # Z-score
            anomaly = self.zscore.check(stream)
            if anomaly:
                new_anomalies.append(anomaly)

            # Trend break
            anomaly = self.trend_break.check(stream)
            if anomaly:
                new_anomalies.append(anomaly)

        self.total_anomalies += len(new_anomalies)
        self.anomalies.extend(new_anomalies)
        if len(self.anomalies) > self.max_anomalies:
            self.anomalies = self.anomalies[-self.max_anomalies:]

        return new_anomalies

    def check_stream(self, metric_name: str) -> list:
        """Ejecuta detectores en un stream específico."""
        stream = self.streams.get(metric_name)
        if not stream:
            return []

        results = []
        for detector in [self.zscore, self.trend_break]:
            anomaly = detector.check(stream)
            if anomaly:
                results.append(anomaly)
                self.anomalies.append(anomaly)
                self.total_anomalies += 1

        return results

    def get_active_anomalies(self, max_age_hours: float = 24) -> list:
        """Anomalías recientes."""
        cutoff = time.time() - max_age_hours * 3600
        return [a for a in self.anomalies if a.timestamp > cutoff]

    def get_stream_summary(self, metric_name: str) -> dict:
        """Resumen de un stream."""
        stream = self.streams.get(metric_name)
        if not stream:
            return {}
        return {
            "name": stream.name,
            "count": stream.count,
            "mean": round(stream.mean, 4),
            "std": round(stream.std, 4),
            "last": round(stream.last, 4),
            "trend": stream.trend(),
            "ma5": round(stream.moving_average(5), 4),
        }

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de anomalías para prompt."""
        if not self.enabled:
            return ""

        recent = self.get_active_anomalies(max_age_hours=1)
        critical = [a for a in recent if a.severity == "critical"]

        if not critical:
            return ""

        lines = ["[ANOMALÍAS DETECTADAS]"]
        for a in critical[:3]:
            lines.append(f"  ⚠ {a.metric_name}: {a.value:.2f} (esperado ~{a.expected:.2f})")
        return "\n".join(lines)[:max_chars]

    def get_stats(self) -> dict:
        return {
            "streams": len(self.streams),
            "total_checks": self.total_checks,
            "total_anomalies": self.total_anomalies,
            "active_anomalies": len(self.get_active_anomalies()),
            "critical": len([a for a in self.get_active_anomalies() if a.severity == "critical"]),
        }

    def status(self) -> str:
        active = self.get_active_anomalies()
        critical = len([a for a in active if a.severity == "critical"])
        return (f"Streams: {len(self.streams)} | "
                f"Checks: {self.total_checks} | "
                f"Anomalías: {len(active)} activas ({critical} críticas)")

    def generate_report(self) -> str:
        lines = ["=== ANOMALY DETECTOR REPORT ==="]
        lines.append(f"Streams monitoreados: {len(self.streams)}")
        lines.append(f"Total checks: {self.total_checks}")
        lines.append(f"Total anomalías: {self.total_anomalies}")

        # Streams
        if self.streams:
            lines.append(f"\nStreams:")
            for name, stream in sorted(self.streams.items()):
                trend = stream.trend()
                lines.append(f"  {name}: mean={stream.mean:.2f} std={stream.std:.2f} "
                             f"last={stream.last:.2f} trend={trend} n={stream.count}")

        # Anomalías recientes
        recent = self.get_active_anomalies(max_age_hours=24)
        if recent:
            lines.append(f"\nAnomalías últimas 24h ({len(recent)}):")
            for a in recent[-10:]:
                lines.append(f"  [{a.severity}] {a.metric_name}: "
                             f"{a.value:.2f} vs {a.expected:.2f} ({a.detector})")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_checks": self.total_checks,
            "total_anomalies": self.total_anomalies,
            "streams": {n: s.to_dict() for n, s in self.streams.items()},
            "anomalies": [a.to_dict() for a in self.anomalies[-self.max_anomalies:]],
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
            self.total_checks = data.get("total_checks", 0)
            self.total_anomalies = data.get("total_anomalies", 0)
            for name, sd in data.get("streams", {}).items():
                self.streams[name] = MetricStream.from_dict(sd)
        except Exception:
            pass

    def clear(self):
        self.streams = {}
        self.anomalies = []
        self.total_checks = 0
        self.total_anomalies = 0
