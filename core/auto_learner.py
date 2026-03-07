"""
GENESIS — Auto Learner
Aprende de las interacciones para mejorar automaticamente.

Analiza patrones de exito/fracaso y ajusta:
- Prioridades de agentes segun tasa de exito
- Preferencias de templates por tipo de tarea
- Patrones de respuesta que obtienen mejor feedback
- Asociaciones usuario↔preferencia

Usa el feedback (+/-) como señal de aprendizaje.
Persiste los patrones aprendidos en disco.

Uso:
    learner = AutoLearner(base_dir)
    learner.record_interaction(agent="coder", template="code", feedback=1, tags=["python"])
    learner.record_interaction(agent="researcher", template="research", feedback=-1, tags=["web"])
    insights = learner.get_insights()
    adjustments = learner.get_agent_adjustments()
"""
import json
import time
import os
from pathlib import Path
from typing import Optional, List
from collections import defaultdict


class PatternTracker:
    """Rastrea patrones de exito/fracaso para una dimension."""

    def __init__(self):
        self.counts = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})

    def record(self, key: str, positive: bool):
        """Registra un evento positivo o negativo para una clave."""
        self.counts[key]["total"] += 1
        if positive:
            self.counts[key]["positive"] += 1
        else:
            self.counts[key]["negative"] += 1

    def success_rate(self, key: str) -> float:
        """Tasa de exito de una clave (0.0 a 1.0)."""
        data = self.counts.get(key)
        if not data or data["total"] == 0:
            return 0.5  # Sin datos = neutral
        return data["positive"] / data["total"]

    def get_ranking(self) -> list:
        """Ranking de claves por tasa de exito (mejor primero)."""
        items = []
        for key, data in self.counts.items():
            if data["total"] >= 2:  # Minimo 2 muestras
                rate = data["positive"] / data["total"]
                items.append({
                    "key": key,
                    "rate": round(rate, 3),
                    "positive": data["positive"],
                    "negative": data["negative"],
                    "total": data["total"],
                })
        return sorted(items, key=lambda x: -x["rate"])

    def to_dict(self) -> dict:
        return dict(self.counts)

    def from_dict(self, data: dict):
        self.counts = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})
        for key, vals in data.items():
            self.counts[key] = vals


class LearningRule:
    """Una regla aprendida del analisis de patrones."""

    def __init__(self, rule_type: str, description: str, confidence: float,
                 action: str = "", data: dict = None):
        """
        Args:
            rule_type: tipo de regla (agent_preference, template_match, avoid_pattern)
            description: descripcion legible
            confidence: confianza en la regla (0.0 a 1.0)
            action: accion sugerida
            data: datos asociados
        """
        self.rule_type = rule_type
        self.description = description
        self.confidence = confidence
        self.action = action
        self.data = data or {}
        self.created_at = time.time()
        self.times_applied = 0

    def to_dict(self) -> dict:
        return {
            "rule_type": self.rule_type,
            "description": self.description,
            "confidence": round(self.confidence, 3),
            "action": self.action,
            "data": self.data,
            "created_at": self.created_at,
            "times_applied": self.times_applied,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LearningRule":
        rule = cls(
            rule_type=d.get("rule_type", ""),
            description=d.get("description", ""),
            confidence=d.get("confidence", 0.0),
            action=d.get("action", ""),
            data=d.get("data", {}),
        )
        rule.created_at = d.get("created_at", time.time())
        rule.times_applied = d.get("times_applied", 0)
        return rule


class AutoLearner:
    """
    Motor de aprendizaje automatico basado en patrones.
    Analiza feedback para mejorar seleccion de agentes, templates y respuestas.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "memory_data" / "learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Trackers por dimension
        self.agent_tracker = PatternTracker()
        self.template_tracker = PatternTracker()
        self.tag_tracker = PatternTracker()
        self.combo_tracker = PatternTracker()  # agent+template combos

        # Reglas aprendidas
        self.rules = []  # type: List[LearningRule]

        # Historial de interacciones recientes
        self.interactions = []
        self.max_interactions = 500

        # Estadisticas globales
        self.total_positive = 0
        self.total_negative = 0
        self.total_neutral = 0

        # Cargar datos persistidos
        self._load()

    def record_interaction(self, agent: str = "", template: str = "",
                           feedback: int = 0, tags: list = None,
                           response_time: float = 0.0,
                           query_preview: str = ""):
        """
        Registra una interaccion con su feedback.

        Args:
            agent: nombre del agente usado
            template: nombre del template usado
            feedback: +1 (bueno), -1 (malo), 0 (neutral)
            tags: etiquetas del tipo de tarea
            response_time: tiempo de respuesta en segundos
            query_preview: preview del query (primeros 100 chars)
        """
        tags = tags or []
        positive = feedback > 0

        # Actualizar contadores globales
        if feedback > 0:
            self.total_positive += 1
        elif feedback < 0:
            self.total_negative += 1
        else:
            self.total_neutral += 1

        # Solo aprender de feedback no-neutral
        if feedback != 0:
            # Registrar por dimension
            if agent:
                self.agent_tracker.record(agent, positive)
            if template:
                self.template_tracker.record(template, positive)
            for tag in tags:
                self.tag_tracker.record(tag, positive)
            if agent and template:
                combo_key = f"{agent}+{template}"
                self.combo_tracker.record(combo_key, positive)

        # Guardar en historial
        interaction = {
            "agent": agent,
            "template": template,
            "feedback": feedback,
            "tags": tags,
            "response_time": response_time,
            "query_preview": query_preview[:100],
            "timestamp": time.time(),
        }
        self.interactions.append(interaction)
        if len(self.interactions) > self.max_interactions:
            self.interactions = self.interactions[-self.max_interactions:]

        # Auto-analizar cada 10 interacciones con feedback
        if (self.total_positive + self.total_negative) % 10 == 0:
            self._analyze_patterns()

        # Auto-save cada 20 interacciones
        if len(self.interactions) % 20 == 0:
            self._save()

    def _analyze_patterns(self):
        """Analiza patrones y genera reglas de aprendizaje."""
        new_rules = []

        # Regla 1: Agentes con alta tasa de exito
        agent_ranking = self.agent_tracker.get_ranking()
        for item in agent_ranking:
            if item["total"] >= 5 and item["rate"] >= 0.8:
                new_rules.append(LearningRule(
                    rule_type="agent_preference",
                    description=f"Agente '{item['key']}' tiene alta tasa de exito ({item['rate']*100:.0f}%)",
                    confidence=min(item["rate"], item["total"] / 20),
                    action=f"boost_priority:{item['key']}",
                    data={"agent": item["key"], "rate": item["rate"], "samples": item["total"]},
                ))

        # Regla 2: Agentes con baja tasa de exito
        for item in agent_ranking:
            if item["total"] >= 5 and item["rate"] <= 0.3:
                new_rules.append(LearningRule(
                    rule_type="agent_warning",
                    description=f"Agente '{item['key']}' tiene baja tasa de exito ({item['rate']*100:.0f}%)",
                    confidence=min(0.9, item["total"] / 20),
                    action=f"lower_priority:{item['key']}",
                    data={"agent": item["key"], "rate": item["rate"], "samples": item["total"]},
                ))

        # Regla 3: Mejores combinaciones agent+template
        combo_ranking = self.combo_tracker.get_ranking()
        for item in combo_ranking[:5]:
            if item["total"] >= 3 and item["rate"] >= 0.7:
                parts = item["key"].split("+")
                if len(parts) == 2:
                    new_rules.append(LearningRule(
                        rule_type="combo_preference",
                        description=f"Combinacion '{parts[0]}' + template '{parts[1]}' funciona bien ({item['rate']*100:.0f}%)",
                        confidence=min(item["rate"], item["total"] / 10),
                        action=f"prefer_combo:{item['key']}",
                        data={"agent": parts[0], "template": parts[1], "rate": item["rate"]},
                    ))

        # Regla 4: Tags problematicos (baja tasa de exito)
        tag_ranking = self.tag_tracker.get_ranking()
        for item in tag_ranking:
            if item["total"] >= 3 and item["rate"] <= 0.4:
                new_rules.append(LearningRule(
                    rule_type="tag_warning",
                    description=f"Tareas con tag '{item['key']}' tienen baja satisfaccion ({item['rate']*100:.0f}%)",
                    confidence=min(0.8, item["total"] / 10),
                    action=f"review_tag:{item['key']}",
                    data={"tag": item["key"], "rate": item["rate"]},
                ))

        # Actualizar reglas (reemplazar las del mismo tipo)
        existing_types = {(r.rule_type, r.action) for r in self.rules}
        for rule in new_rules:
            key = (rule.rule_type, rule.action)
            if key not in existing_types:
                self.rules.append(rule)
                existing_types.add(key)
            else:
                # Actualizar regla existente
                for i, existing in enumerate(self.rules):
                    if (existing.rule_type, existing.action) == key:
                        self.rules[i] = rule
                        break

        # Limitar reglas
        if len(self.rules) > 50:
            # Mantener las de mayor confianza
            self.rules.sort(key=lambda r: -r.confidence)
            self.rules = self.rules[:50]

    def get_agent_adjustments(self) -> dict:
        """
        Retorna ajustes recomendados para prioridades de agentes.

        Returns:
            dict: {agent_name: priority_delta} donde delta > 0 = subir, < 0 = bajar
        """
        adjustments = {}
        for rule in self.rules:
            if rule.rule_type == "agent_preference" and rule.confidence >= 0.5:
                agent = rule.data.get("agent", "")
                if agent:
                    adjustments[agent] = min(2, int(rule.confidence * 3))
            elif rule.rule_type == "agent_warning" and rule.confidence >= 0.5:
                agent = rule.data.get("agent", "")
                if agent:
                    adjustments[agent] = max(-2, -int(rule.confidence * 3))
        return adjustments

    def get_best_agent_for_template(self, template: str) -> Optional[str]:
        """Sugiere el mejor agente para un template dado."""
        best = None
        best_rate = 0.0
        for item in self.combo_tracker.get_ranking():
            parts = item["key"].split("+")
            if len(parts) == 2 and parts[1] == template:
                if item["rate"] > best_rate and item["total"] >= 3:
                    best = parts[0]
                    best_rate = item["rate"]
        return best

    def get_insights(self) -> str:
        """Retorna insights de aprendizaje en formato legible."""
        lines = ["=== Insights de Aprendizaje ==="]

        # Estadisticas globales
        total = self.total_positive + self.total_negative + self.total_neutral
        lines.append(f"\nInteracciones: {total} ({self.total_positive}+ {self.total_negative}- {self.total_neutral}~)")

        if total == 0:
            lines.append("Sin datos suficientes para generar insights.")
            return "\n".join(lines)

        # Tasa de satisfaccion global
        if self.total_positive + self.total_negative > 0:
            rate = self.total_positive / (self.total_positive + self.total_negative)
            lines.append(f"Satisfaccion global: {rate*100:.1f}%")

        # Top agentes
        agent_ranking = self.agent_tracker.get_ranking()
        if agent_ranking:
            lines.append("\nAgentes por efectividad:")
            for item in agent_ranking[:6]:
                bar = "+" * item["positive"] + "-" * item["negative"]
                lines.append(f"  {item['key']}: {item['rate']*100:.0f}% ({bar})")

        # Top templates
        template_ranking = self.template_tracker.get_ranking()
        if template_ranking:
            lines.append("\nTemplates por efectividad:")
            for item in template_ranking[:6]:
                lines.append(f"  {item['key']}: {item['rate']*100:.0f}% ({item['total']} usos)")

        # Mejores combos
        combo_ranking = self.combo_tracker.get_ranking()
        if combo_ranking:
            lines.append("\nMejores combinaciones agente+template:")
            for item in combo_ranking[:5]:
                lines.append(f"  {item['key']}: {item['rate']*100:.0f}% ({item['total']} usos)")

        # Reglas aprendidas
        if self.rules:
            lines.append(f"\nReglas aprendidas: {len(self.rules)}")
            for rule in sorted(self.rules, key=lambda r: -r.confidence)[:5]:
                lines.append(f"  [{rule.confidence:.0%}] {rule.description}")

        return "\n".join(lines)

    def get_rules_summary(self) -> str:
        """Resumen de reglas aprendidas."""
        if not self.rules:
            return "Sin reglas aprendidas aun. Se necesitan mas interacciones con feedback."

        lines = ["=== Reglas Aprendidas ==="]
        for rule in sorted(self.rules, key=lambda r: -r.confidence):
            lines.append(f"  [{rule.confidence:.0%}] {rule.description}")
            lines.append(f"    Accion: {rule.action}")
        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido del learner."""
        total_fb = self.total_positive + self.total_negative
        rate = (self.total_positive / max(1, total_fb)) * 100
        return (
            f"AutoLearner: {total_fb} feedback registrados | "
            f"Satisfaccion: {rate:.0f}% | "
            f"Reglas: {len(self.rules)}"
        )

    # --- Persistencia ---

    def _save(self):
        """Guarda el estado a disco."""
        try:
            data = {
                "agent_tracker": self.agent_tracker.to_dict(),
                "template_tracker": self.template_tracker.to_dict(),
                "tag_tracker": self.tag_tracker.to_dict(),
                "combo_tracker": self.combo_tracker.to_dict(),
                "rules": [r.to_dict() for r in self.rules],
                "interactions": self.interactions[-100:],  # Solo ultimas 100
                "total_positive": self.total_positive,
                "total_negative": self.total_negative,
                "total_neutral": self.total_neutral,
                "saved_at": time.time(),
            }
            filepath = self.data_dir / "auto_learner.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """Carga el estado desde disco."""
        try:
            filepath = self.data_dir / "auto_learner.json"
            if not filepath.exists():
                return
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.agent_tracker.from_dict(data.get("agent_tracker", {}))
            self.template_tracker.from_dict(data.get("template_tracker", {}))
            self.tag_tracker.from_dict(data.get("tag_tracker", {}))
            self.combo_tracker.from_dict(data.get("combo_tracker", {}))
            self.rules = [LearningRule.from_dict(d) for d in data.get("rules", [])]
            self.interactions = data.get("interactions", [])
            self.total_positive = data.get("total_positive", 0)
            self.total_negative = data.get("total_negative", 0)
            self.total_neutral = data.get("total_neutral", 0)
        except Exception:
            pass

    def save(self):
        """Guarda forzado (para llamar al cerrar Genesis)."""
        self._save()
