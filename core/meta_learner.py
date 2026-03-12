"""
GENESIS — Meta-Learner (v2.4)

Meta-aprendizaje: Genesis aprende QUÉ ESTRATEGIAS funcionan mejor.
Correlaciona templates, intents, configuraciones y scores de calidad
para descubrir patrones de auto-mejora.

Componentes:
- StrategyRecord: registro de una estrategia usada y su resultado
- PatternDetector: detecta correlaciones entre estrategias y calidad
- LearningInsight: un insight descubierto (patrón + recomendación)
- MetaLearner: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class StrategyRecord:
    """Registro de una estrategia usada y su resultado."""

    def __init__(self, intent: str, template: str = "", temperature: float = 0.7,
                 chain_used: bool = False, skill_injected: bool = False,
                 score: float = 0.0, user_feedback: str = ""):
        self.timestamp = time.time()
        self.intent = intent
        self.template = template
        self.temperature = temperature
        self.chain_used = chain_used
        self.skill_injected = skill_injected
        self.score = score
        self.user_feedback = user_feedback  # "+", "-", ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "intent": self.intent,
            "template": self.template,
            "temperature": self.temperature,
            "chain_used": self.chain_used,
            "skill_injected": self.skill_injected,
            "score": self.score,
            "user_feedback": self.user_feedback,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyRecord":
        rec = cls(
            intent=data.get("intent", ""),
            template=data.get("template", ""),
            temperature=data.get("temperature", 0.7),
            chain_used=data.get("chain_used", False),
            skill_injected=data.get("skill_injected", False),
            score=data.get("score", 0.0),
            user_feedback=data.get("user_feedback", ""),
        )
        rec.timestamp = data.get("timestamp", time.time())
        return rec


class LearningInsight:
    """Un insight descubierto por el meta-learner."""

    def __init__(self, insight_id: str = None, category: str = "",
                 description: str = "", confidence: float = 0.0,
                 recommendation: str = ""):
        self.insight_id = insight_id or hashlib.md5(
            f"ins_{time.time()}".encode()
        ).hexdigest()[:10]
        self.category = category        # "template", "temperature", "chain", "skill"
        self.description = description  # Qué se descubrió
        self.confidence = confidence    # 0.0-1.0
        self.recommendation = recommendation  # Qué hacer al respecto
        self.created_at = time.time()
        self.applied = False
        self.sample_size = 0

    def to_dict(self) -> dict:
        return {
            "id": self.insight_id,
            "category": self.category,
            "description": self.description,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "applied": self.applied,
            "sample_size": self.sample_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningInsight":
        ins = cls(
            insight_id=data.get("id"),
            category=data.get("category", ""),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.0),
            recommendation=data.get("recommendation", ""),
        )
        ins.created_at = data.get("created_at", time.time())
        ins.applied = data.get("applied", False)
        ins.sample_size = data.get("sample_size", 0)
        return ins


class PatternDetector:
    """Detecta patrones entre estrategias y calidad de respuestas."""

    def __init__(self, min_samples: int = 5):
        self.min_samples = min_samples

    def analyze_by_intent(self, records: list) -> dict:
        """Analiza rendimiento por intent."""
        by_intent = defaultdict(list)
        for rec in records:
            by_intent[rec.intent].append(rec.score)

        results = {}
        for intent, scores in by_intent.items():
            if len(scores) >= self.min_samples:
                avg = sum(scores) / len(scores)
                results[intent] = {
                    "avg_score": round(avg, 3),
                    "count": len(scores),
                    "min": round(min(scores), 3),
                    "max": round(max(scores), 3),
                }
        return results

    def analyze_by_template(self, records: list) -> dict:
        """Analiza rendimiento por template."""
        by_template = defaultdict(list)
        for rec in records:
            if rec.template:
                by_template[rec.template].append(rec.score)

        results = {}
        for tmpl, scores in by_template.items():
            if len(scores) >= self.min_samples:
                avg = sum(scores) / len(scores)
                results[tmpl] = {
                    "avg_score": round(avg, 3),
                    "count": len(scores),
                }
        return results

    def analyze_chain_impact(self, records: list) -> dict:
        """Analiza si usar chain mejora los scores."""
        with_chain = [r.score for r in records if r.chain_used]
        without_chain = [r.score for r in records if not r.chain_used]

        result = {"sufficient_data": False}

        if len(with_chain) >= self.min_samples and len(without_chain) >= self.min_samples:
            avg_with = sum(with_chain) / len(with_chain)
            avg_without = sum(without_chain) / len(without_chain)
            result = {
                "sufficient_data": True,
                "avg_with_chain": round(avg_with, 3),
                "avg_without_chain": round(avg_without, 3),
                "improvement": round(avg_with - avg_without, 3),
                "chain_helps": avg_with > avg_without + 0.05,
            }

        return result

    def analyze_skill_impact(self, records: list) -> dict:
        """Analiza si inyectar skills mejora los scores."""
        with_skill = [r.score for r in records if r.skill_injected]
        without_skill = [r.score for r in records if not r.skill_injected]

        result = {"sufficient_data": False}

        if len(with_skill) >= self.min_samples and len(without_skill) >= self.min_samples:
            avg_with = sum(with_skill) / len(with_skill)
            avg_without = sum(without_skill) / len(without_skill)
            result = {
                "sufficient_data": True,
                "avg_with_skill": round(avg_with, 3),
                "avg_without_skill": round(avg_without, 3),
                "improvement": round(avg_with - avg_without, 3),
                "skill_helps": avg_with > avg_without + 0.05,
            }

        return result

    def analyze_temperature_correlation(self, records: list) -> dict:
        """Analiza correlación entre temperatura y calidad por intent."""
        by_intent_temp = defaultdict(list)
        for rec in records:
            by_intent_temp[rec.intent].append((rec.temperature, rec.score))

        results = {}
        for intent, pairs in by_intent_temp.items():
            if len(pairs) < self.min_samples:
                continue

            # Dividir en "low temp" y "high temp"
            sorted_pairs = sorted(pairs, key=lambda x: x[0])
            mid = len(sorted_pairs) // 2
            low_temps = sorted_pairs[:mid]
            high_temps = sorted_pairs[mid:]

            if low_temps and high_temps:
                avg_low = sum(s for _, s in low_temps) / len(low_temps)
                avg_high = sum(s for _, s in high_temps) / len(high_temps)
                results[intent] = {
                    "avg_low_temp_score": round(avg_low, 3),
                    "avg_high_temp_score": round(avg_high, 3),
                    "prefers_low": avg_low > avg_high + 0.05,
                    "prefers_high": avg_high > avg_low + 0.05,
                }

        return results

    def detect_insights(self, records: list) -> list:
        """Detecta insights a partir de los registros."""
        insights = []

        # 1. Mejores y peores intents
        intent_analysis = self.analyze_by_intent(records)
        for intent, data in intent_analysis.items():
            if data["avg_score"] >= 0.85 and data["count"] >= self.min_samples:
                ins = LearningInsight(
                    category="intent",
                    description=f"Excelente rendimiento en '{intent}' (avg: {data['avg_score']})",
                    confidence=min(0.9, data["count"] / 20),
                    recommendation=f"Mantener estrategia actual para '{intent}'",
                )
                ins.sample_size = data["count"]
                insights.append(ins)

            elif data["avg_score"] < 0.5 and data["count"] >= self.min_samples:
                ins = LearningInsight(
                    category="intent",
                    description=f"Bajo rendimiento en '{intent}' (avg: {data['avg_score']})",
                    confidence=min(0.9, data["count"] / 20),
                    recommendation=f"Ajustar estrategia para '{intent}': revisar temperature y templates",
                )
                ins.sample_size = data["count"]
                insights.append(ins)

        # 2. Impacto de chains
        chain = self.analyze_chain_impact(records)
        if chain.get("sufficient_data"):
            if chain["chain_helps"]:
                ins = LearningInsight(
                    category="chain",
                    description=f"Chain mejora scores en +{chain['improvement']}",
                    confidence=0.7,
                    recommendation="Considerar activar chain para más queries complejas",
                )
                insights.append(ins)

        # 3. Impacto de skills
        skill = self.analyze_skill_impact(records)
        if skill.get("sufficient_data"):
            if skill["skill_helps"]:
                ins = LearningInsight(
                    category="skill",
                    description=f"Skills inyectados mejoran scores en +{skill['improvement']}",
                    confidence=0.7,
                    recommendation="Ampliar extracción y reutilización de skills",
                )
                insights.append(ins)

        # 4. Correlación de temperatura
        temp = self.analyze_temperature_correlation(records)
        for intent, data in temp.items():
            if data.get("prefers_low"):
                ins = LearningInsight(
                    category="temperature",
                    description=f"'{intent}' funciona mejor con temperatura baja",
                    confidence=0.6,
                    recommendation=f"Reducir temperatura para '{intent}'",
                )
                insights.append(ins)
            elif data.get("prefers_high"):
                ins = LearningInsight(
                    category="temperature",
                    description=f"'{intent}' funciona mejor con temperatura alta",
                    confidence=0.6,
                    recommendation=f"Aumentar temperatura para '{intent}'",
                )
                insights.append(ins)

        return insights


class MetaLearner:
    """
    Coordinador de meta-aprendizaje.
    Registra estrategias, detecta patrones, genera insights.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/meta_learner")
        self.data_file = self.base_dir / "meta_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.records = []  # Lista de StrategyRecord
        self.insights = []  # Lista de LearningInsight
        self.detector = PatternDetector(min_samples=5)
        self.max_records = 1000
        self.total_recorded = 0
        self.total_insights = 0
        self.enabled = True

        # Cada cuántos records re-analizar
        self.analysis_interval = 10

        self._load()

    def record_strategy(self, intent: str, template: str = "",
                        temperature: float = 0.7, chain_used: bool = False,
                        skill_injected: bool = False, score: float = 0.0,
                        user_feedback: str = ""):
        """Registra una estrategia y su resultado."""
        if not self.enabled:
            return

        rec = StrategyRecord(
            intent=intent,
            template=template,
            temperature=temperature,
            chain_used=chain_used,
            skill_injected=skill_injected,
            score=score,
            user_feedback=user_feedback,
        )
        self.records.append(rec)
        self.total_recorded += 1

        # Trim si excede máximo
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]

        # Re-analizar periódicamente
        if self.total_recorded % self.analysis_interval == 0:
            self._run_analysis()

    def get_recommendation(self, intent: str) -> dict:
        """Obtiene recomendaciones para un intent basado en datos."""
        if not self.enabled or len(self.records) < 5:
            return {}

        # Filtrar records de este intent
        intent_records = [r for r in self.records if r.intent == intent]
        if len(intent_records) < 3:
            return {}

        # Calcular mejores configuraciones
        best_temp = self._best_temperature(intent_records)
        chain_recommended = self._chain_recommended(intent_records)

        result = {}
        if best_temp is not None:
            result["temperature"] = best_temp
        if chain_recommended is not None:
            result["use_chain"] = chain_recommended

        return result

    def get_insights(self, min_confidence: float = 0.5) -> list:
        """Retorna insights con confianza mínima."""
        return [i for i in self.insights if i.confidence >= min_confidence]

    def get_stats(self) -> dict:
        """Estadísticas del meta-learner."""
        return {
            "total_recorded": self.total_recorded,
            "records_stored": len(self.records),
            "total_insights": self.total_insights,
            "active_insights": len(self.insights),
        }

    def status(self) -> str:
        """Status de una línea."""
        return (f"Records: {len(self.records)} | "
                f"Insights: {len(self.insights)} | "
                f"Total: {self.total_recorded}")

    def generate_report(self) -> str:
        """Reporte detallado del meta-learner."""
        lines = ["=== META-LEARNER REPORT ==="]
        lines.append(f"Total registros: {self.total_recorded}")
        lines.append(f"Registros almacenados: {len(self.records)}")
        lines.append(f"Insights generados: {self.total_insights}")

        # Análisis por intent
        intent_data = self.detector.analyze_by_intent(self.records)
        if intent_data:
            lines.append("\nRendimiento por intent:")
            for intent, data in sorted(intent_data.items(),
                                        key=lambda x: x[1]["avg_score"],
                                        reverse=True):
                lines.append(f"  {intent}: avg={data['avg_score']} "
                             f"(n={data['count']})")

        # Insights activos
        if self.insights:
            lines.append(f"\nInsights activos ({len(self.insights)}):")
            for ins in self.insights[:5]:
                lines.append(f"  [{ins.category}] {ins.description}")
                lines.append(f"    -> {ins.recommendation}")

        return "\n".join(lines)

    def save(self):
        """Persiste el estado a disco."""
        data = {
            "total_recorded": self.total_recorded,
            "total_insights": self.total_insights,
            "records": [r.to_dict() for r in self.records[-self.max_records:]],
            "insights": [i.to_dict() for i in self.insights],
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _load(self):
        """Carga estado desde disco."""
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.total_recorded = data.get("total_recorded", 0)
            self.total_insights = data.get("total_insights", 0)
            self.records = [StrategyRecord.from_dict(r) for r in data.get("records", [])]
            self.insights = [LearningInsight.from_dict(i) for i in data.get("insights", [])]
        except Exception:
            pass

    def clear(self):
        """Limpia todos los datos."""
        self.records = []
        self.insights = []
        self.total_recorded = 0
        self.total_insights = 0

    def _run_analysis(self):
        """Ejecuta análisis y genera insights."""
        new_insights = self.detector.detect_insights(self.records)

        # Filtrar duplicados por descripción
        existing_descs = {i.description for i in self.insights}
        for ins in new_insights:
            if ins.description not in existing_descs:
                self.insights.append(ins)
                self.total_insights += 1

        # Limitar insights almacenados
        if len(self.insights) > 50:
            # Mantener los de mayor confianza
            self.insights.sort(key=lambda x: x.confidence, reverse=True)
            self.insights = self.insights[:50]

    def _best_temperature(self, records: list) -> float:
        """Determina la mejor temperatura para un conjunto de records."""
        if len(records) < 3:
            return None

        # Agrupar por rangos de temperatura
        low = [r.score for r in records if r.temperature < 0.5]
        mid = [r.score for r in records if 0.5 <= r.temperature < 0.8]
        high = [r.score for r in records if r.temperature >= 0.8]

        buckets = {}
        if low:
            buckets[0.3] = sum(low) / len(low)
        if mid:
            buckets[0.6] = sum(mid) / len(mid)
        if high:
            buckets[0.9] = sum(high) / len(high)

        if not buckets:
            return None

        return max(buckets, key=buckets.get)

    def _chain_recommended(self, records: list) -> bool:
        """Determina si chain debería usarse para estos records."""
        with_chain = [r.score for r in records if r.chain_used]
        without_chain = [r.score for r in records if not r.chain_used]

        if len(with_chain) < 3 or len(without_chain) < 3:
            return None

        avg_with = sum(with_chain) / len(with_chain)
        avg_without = sum(without_chain) / len(without_chain)

        return avg_with > avg_without + 0.05
