"""
GENESIS — Experiment Runner (v3.5)

Experimentación autónoma: diseña, ejecuta y analiza experimentos.
Soporta diseño experimental con hipótesis, variables y métricas,
ejecución simulada con datos provistos o sintéticos, y análisis
estadístico básico de resultados.

Componentes:
- ExperimentDesign: diseño de un experimento con hipótesis y variables
- ExperimentResult: resultado de un experimento ejecutado
- StatAnalyzer: análisis estadístico básico (mean, std, comparación)
- ExperimentRunner: coordinador con persistencia
"""
import time
import json
import math
import re
import hashlib
import random
from pathlib import Path
from collections import defaultdict


class ExperimentDesign:
    """Diseño de un experimento con hipótesis, variables y protocolo."""

    def __init__(self, hypothesis: str, variables: dict = None,
                 metrics: list = None, protocol_steps: list = None,
                 seed: int = None):
        self.experiment_id = hashlib.md5(
            f"exp_{hypothesis}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.hypothesis = hypothesis.strip()
        self.variables = variables or {
            "independent": [],
            "dependent": [],
            "controlled": [],
        }
        self.metrics = metrics or []
        self.protocol_steps = protocol_steps or []
        self.seed = seed if seed is not None else int(time.time()) % 100000
        self.status = "designed"       # designed, running, completed, failed
        self.created_at = time.time()

    def is_valid(self) -> bool:
        """Verifica que el diseño tenga los componentes mínimos."""
        return (
            bool(self.hypothesis) and
            len(self.hypothesis) > 10 and
            bool(self.metrics)
        )

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "variables": self.variables,
            "metrics": self.metrics[:20],
            "protocol_steps": self.protocol_steps[:30],
            "seed": self.seed,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentDesign":
        d = cls(
            hypothesis=data.get("hypothesis", ""),
            variables=data.get("variables", {}),
            metrics=data.get("metrics", []),
            protocol_steps=data.get("protocol_steps", []),
            seed=data.get("seed", 0),
        )
        d.experiment_id = data.get("experiment_id", d.experiment_id)
        d.status = data.get("status", "designed")
        d.created_at = data.get("created_at", time.time())
        return d


class ExperimentResult:
    """Resultado de un experimento ejecutado."""

    def __init__(self, experiment_id: str):
        self.result_id = hashlib.md5(
            f"result_{experiment_id}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.experiment_id = experiment_id
        self.measurements = {}       # metric_name -> list of values
        self.success = False
        self.notes = ""
        self.duration_seconds = 0.0
        self.completed_at = time.time()

    def add_measurement(self, metric: str, value: float):
        """Agrega una medición para una métrica."""
        if metric not in self.measurements:
            self.measurements[metric] = []
        self.measurements[metric].append(value)

    def add_measurements(self, metric: str, values: list):
        """Agrega múltiples mediciones para una métrica."""
        if metric not in self.measurements:
            self.measurements[metric] = []
        self.measurements[metric].extend(values)

    def get_metric_values(self, metric: str) -> list:
        """Obtiene los valores de una métrica."""
        return self.measurements.get(metric, [])

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "experiment_id": self.experiment_id,
            "measurements": self.measurements,
            "success": self.success,
            "notes": self.notes[:2000],
            "duration_seconds": round(self.duration_seconds, 3),
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentResult":
        r = cls(experiment_id=data.get("experiment_id", ""))
        r.result_id = data.get("result_id", r.result_id)
        r.measurements = data.get("measurements", {})
        r.success = data.get("success", False)
        r.notes = data.get("notes", "")
        r.duration_seconds = data.get("duration_seconds", 0.0)
        r.completed_at = data.get("completed_at", time.time())
        return r


class StatAnalyzer:
    """Análisis estadístico básico para mediciones experimentales."""

    def basic_stats(self, values: list) -> dict:
        """Calcula estadísticas básicas para una lista de valores."""
        if not values:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0,
                    "count": 0, "median": 0.0}

        n = len(values)
        mean = sum(values) / n

        if n >= 2:
            variance = sum((v - mean) ** 2 for v in values) / (n - 1)
            std = math.sqrt(variance)
        else:
            std = 0.0

        sorted_vals = sorted(values)
        if n % 2 == 0:
            median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            median = sorted_vals[n // 2]

        return {
            "mean": round(mean, 6),
            "std": round(std, 6),
            "min": round(min(values), 6),
            "max": round(max(values), 6),
            "count": n,
            "median": round(median, 6),
        }

    def compare_groups(self, group_a: list, group_b: list) -> dict:
        """
        Compara dos grupos de mediciones.
        Retorna diferencia y si es significativa (diff > 1 std pooled).
        """
        if not group_a or not group_b:
            return {
                "diff": 0.0,
                "significant": False,
                "effect_size": 0.0,
                "group_a_stats": self.basic_stats(group_a),
                "group_b_stats": self.basic_stats(group_b),
            }

        stats_a = self.basic_stats(group_a)
        stats_b = self.basic_stats(group_b)

        diff = stats_b["mean"] - stats_a["mean"]

        # Pooled standard deviation
        n_a = len(group_a)
        n_b = len(group_b)
        if n_a >= 2 and n_b >= 2:
            var_a = stats_a["std"] ** 2
            var_b = stats_b["std"] ** 2
            pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
            pooled_std = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
        else:
            pooled_std = max(stats_a["std"], stats_b["std"])

        # Effect size (Cohen's d approximation)
        effect_size = abs(diff) / pooled_std if pooled_std > 0 else 0.0

        # Significativo si la diferencia supera 1 desviación estándar pooled
        significant = abs(diff) > pooled_std if pooled_std > 0 else False

        return {
            "diff": round(diff, 6),
            "abs_diff": round(abs(diff), 6),
            "significant": significant,
            "effect_size": round(effect_size, 4),
            "pooled_std": round(pooled_std, 6),
            "group_a_stats": stats_a,
            "group_b_stats": stats_b,
        }

    def trend_analysis(self, values: list) -> dict:
        """Análisis de tendencia simple por regresión lineal."""
        if len(values) < 3:
            return {"slope": 0.0, "direction": "stable", "r_squared": 0.0}

        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        # R-squared
        ss_res = sum((values[i] - (y_mean + slope * (x[i] - x_mean))) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        direction = "rising" if slope > 0.01 else ("falling" if slope < -0.01 else "stable")

        return {
            "slope": round(slope, 6),
            "direction": direction,
            "r_squared": round(max(0.0, r_squared), 4),
        }


class ExperimentRunner:
    """
    Coordinador de experimentación autónoma.
    Diseña, ejecuta y analiza experimentos con persistencia.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/experiments")
        self.data_file = self.base_dir / "experiment_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.experiments = {}       # experiment_id -> ExperimentDesign
        self.results = {}           # experiment_id -> ExperimentResult
        self.analyzer = StatAnalyzer()
        self.max_experiments = 200
        self.total_experiments = 0
        self.total_completed = 0
        self.enabled = True

        self._load()

    # Templates para auto-generar protocolo
    PROTOCOL_TEMPLATES = {
        "default": [
            "1. Definir condiciones iniciales y variables controladas",
            "2. Configurar métricas de medición",
            "3. Ejecutar condición de control (baseline)",
            "4. Ejecutar condición experimental",
            "5. Recopilar mediciones para cada métrica",
            "6. Analizar resultados con StatAnalyzer",
            "7. Comparar contra hipótesis original",
            "8. Documentar conclusiones",
        ],
        "comparison": [
            "1. Establecer grupo de control (A)",
            "2. Establecer grupo experimental (B)",
            "3. Asegurar variables controladas idénticas",
            "4. Ejecutar ambos grupos en paralelo",
            "5. Recopilar métricas de ambos grupos",
            "6. Comparar grupos con compare_groups()",
            "7. Evaluar significancia estadística",
            "8. Reportar effect size y conclusión",
        ],
    }

    def design_experiment(self, hypothesis: str,
                          variables: dict = None) -> ExperimentDesign:
        """Crea un ExperimentDesign con protocolo auto-generado."""
        if not self.enabled or not hypothesis:
            return None

        # Auto-generar variables si no se proporcionan
        if not variables:
            variables = self._auto_detect_variables(hypothesis)

        # Auto-generar métricas desde la hipótesis
        metrics = self._auto_generate_metrics(hypothesis, variables)

        # Seleccionar template de protocolo
        has_comparison = any(
            w in hypothesis.lower()
            for w in ["comparar", "compare", "vs", "versus", "mejor", "better",
                       "diferencia", "difference"]
        )
        protocol_key = "comparison" if has_comparison else "default"
        protocol = list(self.PROTOCOL_TEMPLATES[protocol_key])

        design = ExperimentDesign(
            hypothesis=hypothesis,
            variables=variables,
            metrics=metrics,
            protocol_steps=protocol,
        )

        self.experiments[design.experiment_id] = design
        self.total_experiments += 1

        # Evicción
        if len(self.experiments) > self.max_experiments:
            self._evict()

        return design

    def run_experiment(self, experiment_id: str,
                       data: dict = None) -> ExperimentResult:
        """
        Ejecuta un experimento. Si data es proporcionado, lo usa como
        mediciones. Si no, genera datos sintéticos basados en el seed.
        """
        if not self.enabled:
            return None

        design = self.experiments.get(experiment_id)
        if not design:
            return None

        start_time = time.time()
        design.status = "running"

        result = ExperimentResult(experiment_id=experiment_id)

        if data:
            # Usar datos proporcionados
            for metric, values in data.items():
                if isinstance(values, list):
                    result.add_measurements(metric, values)
                else:
                    result.add_measurement(metric, float(values))
        else:
            # Generar datos sintéticos reproducibles
            rng = random.Random(design.seed)
            for metric in design.metrics:
                n_samples = 30
                base_mean = rng.uniform(0.3, 0.8)
                base_std = rng.uniform(0.05, 0.2)
                values = [rng.gauss(base_mean, base_std) for _ in range(n_samples)]
                result.add_measurements(metric, values)

        result.duration_seconds = time.time() - start_time
        result.success = bool(result.measurements)

        if result.success:
            design.status = "completed"
            self.total_completed += 1
            # Auto-generar notas
            notes_parts = [f"Experimento {experiment_id} completado."]
            for metric, vals in result.measurements.items():
                stats = self.analyzer.basic_stats(vals)
                notes_parts.append(
                    f"{metric}: mean={stats['mean']:.4f}, std={stats['std']:.4f}, n={stats['count']}"
                )
            result.notes = " | ".join(notes_parts)
        else:
            design.status = "failed"
            result.notes = "No se obtuvieron mediciones."

        self.results[experiment_id] = result
        return result

    def analyze_results(self, experiment_id: str) -> dict:
        """Ejecuta StatAnalyzer sobre los resultados de un experimento."""
        result = self.results.get(experiment_id)
        design = self.experiments.get(experiment_id)

        if not result:
            return {"error": "No hay resultados para este experimento."}

        analysis = {
            "experiment_id": experiment_id,
            "hypothesis": design.hypothesis if design else "",
            "success": result.success,
            "duration": result.duration_seconds,
            "metrics": {},
        }

        metric_names = list(result.measurements.keys())
        for metric in metric_names:
            values = result.get_metric_values(metric)
            stats = self.analyzer.basic_stats(values)
            trend = self.analyzer.trend_analysis(values)
            analysis["metrics"][metric] = {
                "stats": stats,
                "trend": trend,
            }

        # Si hay 2+ métricas, comparar las dos primeras
        if len(metric_names) >= 2:
            group_a = result.get_metric_values(metric_names[0])
            group_b = result.get_metric_values(metric_names[1])
            comparison = self.analyzer.compare_groups(group_a, group_b)
            analysis["comparison"] = {
                "metric_a": metric_names[0],
                "metric_b": metric_names[1],
                **comparison,
            }

        # Evaluación contra hipótesis
        if design:
            analysis["hypothesis_evaluation"] = self._evaluate_hypothesis(design, analysis)

        return analysis

    def get_context_for_prompt(self, max_chars: int = 400) -> str:
        """Inyecta contexto de experimentos activos en el prompt."""
        if not self.enabled:
            return ""

        # Experimentos recientes (últimos 5 completados)
        completed = [
            (eid, self.experiments[eid], self.results[eid])
            for eid in self.results
            if eid in self.experiments and self.experiments[eid].status == "completed"
        ]
        if not completed:
            # Mostrar diseñados pero no ejecutados
            designed = [
                d for d in self.experiments.values()
                if d.status == "designed"
            ]
            if not designed:
                return ""
            lines = ["[EXPERIMENTOS PENDIENTES]"]
            for d in designed[-3:]:
                lines.append(f"  H: {d.hypothesis[:80]} ({d.experiment_id})")
            return "\n".join(lines)[:max_chars]

        completed.sort(key=lambda x: x[2].completed_at, reverse=True)

        lines = ["[EXPERIMENTOS RECIENTES]"]
        total = 0
        for eid, design, result in completed[:3]:
            line = f"  {eid}: {design.hypothesis[:60]}"
            if result.success:
                # Agregar resultado principal
                if result.measurements:
                    first_metric = list(result.measurements.keys())[0]
                    vals = result.measurements[first_metric]
                    stats = self.analyzer.basic_stats(vals)
                    line += f" -> {first_metric}={stats['mean']:.3f}"
            else:
                line += " [FAILED]"
            if total + len(line) > max_chars - 30:
                break
            lines.append(line)
            total += len(line)

        return "\n".join(lines)[:max_chars] if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        active = len([d for d in self.experiments.values() if d.status == "designed"])
        running = len([d for d in self.experiments.values() if d.status == "running"])
        completed = len([d for d in self.experiments.values() if d.status == "completed"])
        failed = len([d for d in self.experiments.values() if d.status == "failed"])
        return {
            "total_experiments": self.total_experiments,
            "stored_experiments": len(self.experiments),
            "total_completed": self.total_completed,
            "active": active,
            "running": running,
            "completed": completed,
            "failed": failed,
            "total_results": len(self.results),
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Experimentos: {stats['stored_experiments']} "
                f"(diseñados={stats['active']}, completados={stats['completed']}, "
                f"fallidos={stats['failed']}) | "
                f"Total: {stats['total_experiments']}")

    def generate_report(self) -> str:
        lines = ["=== EXPERIMENT RUNNER REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total experimentos: {stats['total_experiments']}")
        lines.append(f"Completados: {stats['total_completed']}")
        lines.append(f"Almacenados: {stats['stored_experiments']}")
        lines.append(f"Resultados: {stats['total_results']}")

        # Experimentos por estado
        lines.append(f"\nPor estado:")
        lines.append(f"  Diseñados: {stats['active']}")
        lines.append(f"  En ejecución: {stats['running']}")
        lines.append(f"  Completados: {stats['completed']}")
        lines.append(f"  Fallidos: {stats['failed']}")

        # Últimos completados con análisis
        completed_ids = [
            eid for eid, d in self.experiments.items()
            if d.status == "completed" and eid in self.results
        ]
        if completed_ids:
            lines.append(f"\nÚltimos completados:")
            for eid in completed_ids[-5:]:
                design = self.experiments[eid]
                result = self.results[eid]
                lines.append(f"  [{eid}] {design.hypothesis[:80]}")
                lines.append(f"    Duración: {result.duration_seconds:.2f}s | "
                             f"Métricas: {len(result.measurements)}")
                for metric, vals in list(result.measurements.items())[:3]:
                    s = self.analyzer.basic_stats(vals)
                    bar = "█" * int(s["mean"] * 20) + "░" * (20 - int(s["mean"] * 20))
                    lines.append(f"    [{bar}] {metric}: "
                                 f"mean={s['mean']:.4f} std={s['std']:.4f}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_experiments": self.total_experiments,
            "total_completed": self.total_completed,
            "experiments": {eid: d.to_dict() for eid, d in self.experiments.items()},
            "results": {eid: r.to_dict() for eid, r in self.results.items()},
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
            self.total_experiments = data.get("total_experiments", 0)
            self.total_completed = data.get("total_completed", 0)
            for eid, ed in data.get("experiments", {}).items():
                self.experiments[eid] = ExperimentDesign.from_dict(ed)
            for eid, rd in data.get("results", {}).items():
                self.results[eid] = ExperimentResult.from_dict(rd)
        except Exception:
            pass

    def clear(self):
        self.experiments = {}
        self.results = {}
        self.total_experiments = 0
        self.total_completed = 0

    def _auto_detect_variables(self, hypothesis: str) -> dict:
        """Auto-detecta variables desde el texto de la hipótesis."""
        variables = {"independent": [], "dependent": [], "controlled": []}
        h_lower = hypothesis.lower()

        # Patrones para variables independientes
        ind_patterns = [
            r"(?:si|when|if|al)\s+(?:se\s+)?(?:aumenta|cambia|modifica|incrementa|reduce|aplica|usa)\s+(.+?)(?:,|\s+entonces)",
            r"(?:cambiar|modificar|variar|ajustar)\s+(.+?)(?:\s+(?:para|produce|genera|causa))",
        ]
        for pattern in ind_patterns:
            match = re.search(pattern, h_lower)
            if match:
                variables["independent"].append(match.group(1).strip()[:50])

        # Patrones para variables dependientes
        dep_patterns = [
            r"(?:entonces|produce|genera|mejora|empeora|afecta|causa)\s+(?:un\s+|una\s+)?(.+?)(?:\.|$)",
            r"(?:el|la|los|las)\s+(.+?)\s+(?:mejora|empeora|cambia|aumenta|disminuye)",
        ]
        for pattern in dep_patterns:
            match = re.search(pattern, h_lower)
            if match:
                variables["dependent"].append(match.group(1).strip()[:50])

        # Defaults si no se detectó nada
        if not variables["independent"]:
            variables["independent"] = ["variable_independiente"]
        if not variables["dependent"]:
            variables["dependent"] = ["resultado_observado"]
        variables["controlled"] = ["entorno", "configuración base"]

        return variables

    def _auto_generate_metrics(self, hypothesis: str,
                                variables: dict) -> list:
        """Auto-genera métricas relevantes desde la hipótesis y variables."""
        metrics = []

        # Métricas basadas en variables dependientes
        for dep in variables.get("dependent", []):
            metrics.append(f"medicion_{dep.replace(' ', '_')[:20]}")

        # Métricas por keywords en la hipótesis
        h_lower = hypothesis.lower()
        metric_keywords = {
            "rendimiento": "performance_score",
            "performance": "performance_score",
            "velocidad": "speed_metric",
            "speed": "speed_metric",
            "precisión": "accuracy",
            "accuracy": "accuracy",
            "error": "error_rate",
            "calidad": "quality_score",
            "quality": "quality_score",
            "eficiencia": "efficiency",
            "efficiency": "efficiency",
        }
        for keyword, metric_name in metric_keywords.items():
            if keyword in h_lower and metric_name not in metrics:
                metrics.append(metric_name)

        # Siempre incluir al menos una métrica
        if not metrics:
            metrics = ["primary_metric", "secondary_metric"]

        return metrics[:10]

    def _evaluate_hypothesis(self, design: ExperimentDesign,
                              analysis: dict) -> str:
        """Evalúa si los resultados soportan la hipótesis."""
        if not analysis.get("metrics"):
            return "Sin datos suficientes para evaluar."

        # Verificar si hay comparación significativa
        comparison = analysis.get("comparison", {})
        if comparison:
            if comparison.get("significant"):
                effect = comparison.get("effect_size", 0)
                if effect > 0.8:
                    return f"FUERTEMENTE SOPORTADA: efecto grande (d={effect:.2f})"
                elif effect > 0.5:
                    return f"SOPORTADA: efecto mediano (d={effect:.2f})"
                else:
                    return f"DÉBILMENTE SOPORTADA: efecto pequeño (d={effect:.2f})"
            else:
                return "NO SOPORTADA: diferencia no significativa"

        # Sin comparación, evaluar por tendencia
        for metric, data in analysis["metrics"].items():
            trend = data.get("trend", {})
            if trend.get("direction") != "stable" and trend.get("r_squared", 0) > 0.5:
                return f"INDICIOS: tendencia {trend['direction']} en {metric} (R²={trend['r_squared']:.2f})"

        return "INCONCLUSA: se necesitan más datos o un diseño comparativo"

    def _evict(self):
        """Elimina experimentos antiguos cuando se supera el límite."""
        if len(self.experiments) <= self.max_experiments:
            return
        # Priorizar: completados con resultados > diseñados > fallidos
        priority = {"completed": 3, "running": 2, "designed": 1, "failed": 0}
        sorted_exps = sorted(
            self.experiments.items(),
            key=lambda item: (
                priority.get(item[1].status, 0),
                item[1].created_at,
            ),
            reverse=True,
        )
        keep_ids = set(eid for eid, _ in sorted_exps[:self.max_experiments])
        self.experiments = {eid: d for eid, d in self.experiments.items() if eid in keep_ids}
        # También limpiar resultados huérfanos
        self.results = {eid: r for eid, r in self.results.items() if eid in keep_ids}
