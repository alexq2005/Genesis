"""
GENESIS — Trend Forecaster (v4.1)

Predicción de tendencias: Genesis registra series de datos,
calcula medias móviles y suavizado exponencial, detecta tendencias
y estacionalidad, y genera alertas sobre cambios significativos.

Componentes:
- DataSeries: serie temporal con valores y timestamps
- MovingAverage: media móvil simple con ventana configurable
- ExponentialSmoothing: suavizado exponencial con parámetro alpha
- TrendForecaster: coordinador con predicción y detección de patrones
"""
import time
import json
import math
from pathlib import Path
from collections import deque


class DataSeries:
    """Serie temporal de datos con nombre y unidad."""

    def __init__(self, name: str, unit: str = "", maxlen: int = 100):
        self.name = name
        self.unit = unit
        self.maxlen = maxlen
        self.values = deque(maxlen=maxlen)
        self.timestamps = deque(maxlen=maxlen)
        self.total_recorded = 0

    def add(self, value: float, timestamp: float = None):
        """Agrega un valor a la serie."""
        self.values.append(value)
        self.timestamps.append(timestamp or time.time())
        self.total_recorded += 1

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def last(self) -> float:
        return self.values[-1] if self.values else 0.0

    @property
    def mean(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)

    @property
    def std(self) -> float:
        if len(self.values) < 2:
            return 0.0
        m = self.mean
        variance = sum((v - m) ** 2 for v in self.values) / len(self.values)
        return math.sqrt(variance)

    @property
    def min_val(self) -> float:
        return min(self.values) if self.values else 0.0

    @property
    def max_val(self) -> float:
        return max(self.values) if self.values else 0.0

    def values_list(self) -> list:
        return list(self.values)

    def timestamps_list(self) -> list:
        return list(self.timestamps)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "unit": self.unit,
            "maxlen": self.maxlen,
            "values": list(self.values),
            "timestamps": list(self.timestamps),
            "total_recorded": self.total_recorded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DataSeries":
        ds = cls(
            name=data.get("name", ""),
            unit=data.get("unit", ""),
            maxlen=data.get("maxlen", 100),
        )
        for v, t in zip(data.get("values", []), data.get("timestamps", [])):
            ds.values.append(v)
            ds.timestamps.append(t)
        ds.total_recorded = data.get("total_recorded", len(ds.values))
        return ds


class MovingAverage:
    """Calcula media móvil simple con ventana configurable."""

    def __init__(self, window: int = 5):
        self.window = max(1, window)

    def compute(self, values: list) -> list:
        """Calcula la media móvil para toda la serie."""
        if not values:
            return []
        result = []
        for i in range(len(values)):
            start = max(0, i - self.window + 1)
            window_vals = values[start:i + 1]
            result.append(sum(window_vals) / len(window_vals))
        return result

    def current(self, values: list) -> float:
        """Calcula la media móvil del último punto."""
        if not values:
            return 0.0
        recent = values[-self.window:]
        return sum(recent) / len(recent)

    def slope(self, values: list) -> float:
        """Calcula la pendiente de la media móvil (últimos 2 puntos MA)."""
        ma = self.compute(values)
        if len(ma) < 2:
            return 0.0
        return ma[-1] - ma[-2]


class ExponentialSmoothing:
    """Suavizado exponencial con parámetro alpha."""

    def __init__(self, alpha: float = 0.3):
        self.alpha = max(0.01, min(1.0, alpha))

    def compute(self, values: list) -> list:
        """Aplica suavizado exponencial a toda la serie."""
        if not values:
            return []
        result = [values[0]]
        for i in range(1, len(values)):
            smoothed = self.alpha * values[i] + (1.0 - self.alpha) * result[-1]
            result.append(smoothed)
        return result

    def forecast(self, values: list, steps: int = 5) -> list:
        """
        Predice los próximos N valores usando doble suavizado exponencial.
        Usa nivel + tendencia para proyectar hacia adelante.
        """
        if not values or len(values) < 2:
            return [values[-1] if values else 0.0] * steps

        # Inicializar nivel y tendencia
        level = values[0]
        trend = values[1] - values[0]

        # Aplicar doble suavizado exponencial (Holt)
        beta = self.alpha * 0.8  # Beta derivado de alpha
        for val in values:
            prev_level = level
            level = self.alpha * val + (1.0 - self.alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1.0 - beta) * trend

        # Proyectar
        forecasts = []
        for step in range(1, steps + 1):
            forecasts.append(round(level + trend * step, 6))

        return forecasts

    def current(self, values: list) -> float:
        """Valor suavizado actual."""
        smoothed = self.compute(values)
        return smoothed[-1] if smoothed else 0.0


class TrendForecaster:
    """
    Coordinador de predicción de tendencias.
    Gestiona múltiples series de datos, detecta tendencias,
    genera forecasts y alerta sobre cambios significativos.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/forecast")
        self.data_file = self.base_dir / "forecast_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.series = {}              # name -> DataSeries
        self.moving_avg = MovingAverage(window=5)
        self.smoother = ExponentialSmoothing(alpha=0.3)
        self.total_forecasts = 0
        self.alerts = []              # Alertas de cambios significativos
        self.max_alerts = 50
        self.enabled = True

        self._load()

    def record(self, series_name: str, value: float, unit: str = "") -> DataSeries:
        """Agrega un valor a una serie (creándola si no existe)."""
        if not self.enabled or not series_name:
            return None

        if series_name not in self.series:
            self.series[series_name] = DataSeries(name=series_name, unit=unit)

        series = self.series[series_name]
        series.add(value)

        # Verificar si hay cambio significativo para generar alerta
        self._check_alert(series)

        return series

    def forecast(self, series_name: str, steps: int = 5) -> list:
        """Predice los próximos N valores usando suavizado exponencial."""
        self.total_forecasts += 1

        series = self.series.get(series_name)
        if not series or series.count < 2:
            return []

        values = series.values_list()
        return self.smoother.forecast(values, steps=steps)

    def detect_trend(self, series_name: str) -> str:
        """
        Detecta la tendencia de una serie: 'rising', 'falling', 'stable'.
        Basado en la pendiente de la media móvil reciente.
        """
        series = self.series.get(series_name)
        if not series or series.count < 4:
            return "stable"

        values = series.values_list()
        mid = len(values) // 2
        first_half = sum(values[:mid]) / mid
        second_half = sum(values[mid:]) / (len(values) - mid)

        diff = second_half - first_half
        std = series.std
        threshold = std * 0.5 if std > 0 else abs(first_half) * 0.1

        if threshold == 0:
            return "stable"
        if diff > threshold:
            return "rising"
        elif diff < -threshold:
            return "falling"
        return "stable"

    def detect_seasonality(self, series_name: str, period: int = 7) -> dict:
        """
        Detecta si un patrón se repite cada N puntos.
        Calcula autocorrelación en el lag=period y retorna score.
        """
        series = self.series.get(series_name)
        if not series or series.count < period * 2:
            return {"seasonal": False, "period": period, "score": 0.0}

        values = series.values_list()
        n = len(values)
        mean = sum(values) / n

        # Autocorrelación en lag = period
        numerator = 0.0
        denominator = 0.0
        for i in range(n):
            denominator += (values[i] - mean) ** 2
            if i >= period:
                numerator += (values[i] - mean) * (values[i - period] - mean)

        if denominator == 0:
            return {"seasonal": False, "period": period, "score": 0.0}

        autocorr = numerator / denominator
        is_seasonal = autocorr > 0.5

        return {
            "seasonal": is_seasonal,
            "period": period,
            "score": round(autocorr, 4),
        }

    def get_series_summary(self, series_name: str) -> dict:
        """Resumen completo de una serie."""
        series = self.series.get(series_name)
        if not series:
            return {}

        values = series.values_list()
        trend = self.detect_trend(series_name)
        ma_current = self.moving_avg.current(values) if values else 0.0
        es_current = self.smoother.current(values) if values else 0.0

        return {
            "name": series.name,
            "unit": series.unit,
            "count": series.count,
            "total_recorded": series.total_recorded,
            "last": round(series.last, 4),
            "mean": round(series.mean, 4),
            "std": round(series.std, 4),
            "min": round(series.min_val, 4),
            "max": round(series.max_val, 4),
            "trend": trend,
            "moving_average": round(ma_current, 4),
            "exponential_smooth": round(es_current, 4),
        }

    def _check_alert(self, series: DataSeries):
        """Genera alerta si hay cambio significativo en la serie."""
        if series.count < 5:
            return

        values = series.values_list()
        ma_prev = self.moving_avg.current(values[:-1])
        ma_curr = self.moving_avg.current(values)

        if ma_prev == 0:
            return

        pct_change = abs(ma_curr - ma_prev) / abs(ma_prev)
        if pct_change > 0.2:  # Cambio > 20%
            direction = "sube" if ma_curr > ma_prev else "baja"
            alert = {
                "series": series.name,
                "type": f"cambio_significativo_{direction}",
                "pct_change": round(pct_change * 100, 1),
                "from_value": round(ma_prev, 4),
                "to_value": round(ma_curr, 4),
                "timestamp": time.time(),
            }
            self.alerts.append(alert)
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]

    def get_recent_alerts(self, max_age_hours: float = 24) -> list:
        """Retorna alertas recientes."""
        cutoff = time.time() - max_age_hours * 3600
        return [a for a in self.alerts if a.get("timestamp", 0) > cutoff]

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Genera contexto de tendencias para inyectar en prompt."""
        if not self.enabled or not self.series:
            return ""

        # Buscar series con cambios significativos
        trending = []
        for name, series in self.series.items():
            if series.count < 4:
                continue
            trend = self.detect_trend(name)
            if trend != "stable":
                trending.append((name, trend, series))

        recent_alerts = self.get_recent_alerts(max_age_hours=1)

        if not trending and not recent_alerts:
            return ""

        lines = ["[TENDENCIAS DETECTADAS]"]

        # Alertas recientes
        if recent_alerts:
            for alert in recent_alerts[:3]:
                lines.append(
                    f"  ! {alert['series']}: {alert['type']} "
                    f"({alert['pct_change']}%)"
                )

        # Series con tendencia
        for name, trend, series in trending[:3]:
            trend_str = "en alza" if trend == "rising" else "en baja"
            lines.append(
                f"  {name}: {trend_str} "
                f"(actual={series.last:.2f}, media={series.mean:.2f})"
            )

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_series": len(self.series),
            "total_forecasts": self.total_forecasts,
            "total_alerts": len(self.alerts),
            "recent_alerts": len(self.get_recent_alerts()),
            "series_summary": {
                name: {
                    "count": s.count,
                    "trend": self.detect_trend(name),
                    "last": round(s.last, 4),
                }
                for name, s in self.series.items()
            },
        }

    def status(self) -> str:
        trends = sum(1 for n in self.series if self.detect_trend(n) != "stable")
        return (f"Series: {len(self.series)} | "
                f"Forecasts: {self.total_forecasts} | "
                f"Tendencias activas: {trends} | "
                f"Alertas: {len(self.alerts)}")

    def generate_report(self) -> str:
        lines = ["=== TREND FORECASTER REPORT ==="]
        lines.append(f"Series monitoreadas: {len(self.series)}")
        lines.append(f"Total forecasts: {self.total_forecasts}")
        lines.append(f"Alertas totales: {len(self.alerts)}")

        # Detalle por serie
        if self.series:
            lines.append(f"\nSeries:")
            for name, series in sorted(self.series.items()):
                trend = self.detect_trend(name)
                unit_str = f" {series.unit}" if series.unit else ""
                lines.append(
                    f"  {name}: last={series.last:.2f}{unit_str} "
                    f"mean={series.mean:.2f} std={series.std:.2f} "
                    f"trend={trend} n={series.count}"
                )

                # Forecast si hay datos suficientes
                if series.count >= 3:
                    fc = self.forecast(name, steps=3)
                    self.total_forecasts -= 1  # No contar forecasts del report
                    if fc:
                        fc_str = ", ".join(f"{v:.2f}" for v in fc)
                        lines.append(f"    forecast(3): [{fc_str}]")

                # Estacionalidad
                if series.count >= 14:
                    seas = self.detect_seasonality(name, period=7)
                    if seas["seasonal"]:
                        lines.append(
                            f"    estacionalidad detectada "
                            f"(periodo={seas['period']}, score={seas['score']:.2f})"
                        )

        # Alertas recientes
        recent = self.get_recent_alerts(max_age_hours=24)
        if recent:
            lines.append(f"\nAlertas últimas 24h ({len(recent)}):")
            for alert in recent[-10:]:
                lines.append(
                    f"  [{alert['type']}] {alert['series']}: "
                    f"{alert['pct_change']}% ({alert['from_value']:.2f} -> {alert['to_value']:.2f})"
                )

        return "\n".join(lines)

    def save(self):
        data = {
            "total_forecasts": self.total_forecasts,
            "series": {n: s.to_dict() for n, s in self.series.items()},
            "alerts": self.alerts[-self.max_alerts:],
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_forecasts = data.get("total_forecasts", 0)
            for name, sd in data.get("series", {}).items():
                self.series[name] = DataSeries.from_dict(sd)
            self.alerts = data.get("alerts", [])
        except Exception:
            pass

    def clear(self):
        self.series = {}
        self.total_forecasts = 0
        self.alerts = []
