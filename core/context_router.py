"""
GENESIS — Context Router (v2.5)

Ensamblaje inteligente de contexto: en lugar de concatenar
todos los contextos linealmente, el router asigna un presupuesto
de tokens/chars proporcional a la relevancia de cada fuente
para cada query específica.

Componentes:
- ContextSource: una fuente de contexto registrada con scorer
- ContextBudget: asignación de presupuesto por fuente
- ContextRouter: coordinador que ensambla contexto óptimo
"""
import time
import re
import json
from pathlib import Path
from collections import defaultdict


class ContextSource:
    """Una fuente de contexto registrada."""

    def __init__(self, name: str, getter=None, max_chars: int = 800,
                 base_priority: float = 0.5, keywords: list = None):
        self.name = name
        self.getter = getter              # Callable(user_input, max_chars) -> str
        self.max_chars = max_chars
        self.base_priority = base_priority  # 0.0-1.0
        self.keywords = keywords or []    # Keywords que disparan esta fuente
        self.enabled = True
        self.total_used = 0
        self.total_chars_provided = 0
        self.avg_usefulness = 0.5         # Promedio de utilidad reportada

    def score_relevance(self, user_input: str) -> float:
        """Calcula relevancia de esta fuente para el input dado."""
        if not self.enabled or not self.getter:
            return 0.0

        score = self.base_priority

        # Bonus por keywords
        if self.keywords:
            input_lower = user_input.lower()
            matches = sum(1 for kw in self.keywords if kw in input_lower)
            if matches > 0:
                score += min(0.3, matches * 0.1)

        # Factor de historial (si esta fuente suele ser útil)
        score *= (0.5 + self.avg_usefulness * 0.5)

        return min(1.0, score)

    def get_context(self, user_input: str, max_chars: int) -> str:
        """Obtiene contexto de esta fuente."""
        if not self.enabled or not self.getter:
            return ""

        try:
            result = self.getter(user_input, max_chars)
            if result:
                self.total_used += 1
                self.total_chars_provided += len(result)
            return result or ""
        except Exception:
            return ""

    def record_usefulness(self, useful: bool):
        """Registra si el contexto fue útil (para ajustar avg_usefulness)."""
        new_val = 1.0 if useful else 0.0
        # Moving average
        alpha = 0.1
        self.avg_usefulness = (1 - alpha) * self.avg_usefulness + alpha * new_val

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "max_chars": self.max_chars,
            "base_priority": self.base_priority,
            "keywords": self.keywords[:20],
            "enabled": self.enabled,
            "total_used": self.total_used,
            "total_chars_provided": self.total_chars_provided,
            "avg_usefulness": round(self.avg_usefulness, 3),
        }


class ContextBudget:
    """Asigna presupuesto de chars a cada fuente proporcionalmente."""

    def __init__(self, total_budget: int = 3000):
        self.total_budget = total_budget

    def allocate(self, sources_with_scores: list) -> dict:
        """
        Asigna presupuesto a cada fuente.
        sources_with_scores: lista de (ContextSource, relevance_score)
        Retorna dict {source_name: allocated_chars}
        """
        if not sources_with_scores:
            return {}

        # Filtrar fuentes con score > umbral mínimo
        eligible = [(s, score) for s, score in sources_with_scores if score > 0.1]

        if not eligible:
            return {}

        # Normalizar scores
        total_score = sum(score for _, score in eligible)
        if total_score <= 0:
            return {}

        allocations = {}
        for source, score in eligible:
            proportion = score / total_score
            allocated = int(self.total_budget * proportion)
            # Respetar max_chars de la fuente
            allocated = min(allocated, source.max_chars)
            # Mínimo razonable
            allocated = max(allocated, 100)
            allocations[source.name] = allocated

        # Si el total excede el presupuesto, recortar proporcionalmente
        total_allocated = sum(allocations.values())
        if total_allocated > self.total_budget:
            factor = self.total_budget / total_allocated
            allocations = {k: max(100, int(v * factor))
                           for k, v in allocations.items()}

        return allocations


class ContextRouter:
    """
    Coordinador de ensamblaje inteligente de contexto.
    Registra fuentes, calcula relevancia, asigna presupuesto
    y ensambla el contexto final.
    """

    def __init__(self, base_dir: str = None, total_budget: int = 3000):
        self.base_dir = Path(base_dir) if base_dir else Path("data/context_router")
        self.data_file = self.base_dir / "router_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.sources = {}  # name -> ContextSource
        self.budget = ContextBudget(total_budget=total_budget)
        self.total_routes = 0
        self.total_chars_assembled = 0
        self.enabled = True

        # Historial de allocations para análisis
        self.allocation_history = []
        self.max_history = 100

        self._load()

    def register_source(self, name: str, getter=None, max_chars: int = 800,
                        base_priority: float = 0.5, keywords: list = None):
        """Registra una fuente de contexto."""
        source = ContextSource(
            name=name,
            getter=getter,
            max_chars=max_chars,
            base_priority=base_priority,
            keywords=keywords or [],
        )
        # Restaurar stats si existía previamente
        if name in self.sources:
            old = self.sources[name]
            source.total_used = old.total_used
            source.total_chars_provided = old.total_chars_provided
            source.avg_usefulness = old.avg_usefulness
        self.sources[name] = source

    def route(self, user_input: str) -> str:
        """
        Ensambla contexto óptimo para el input dado.
        Retorna string con contexto combinado.
        """
        if not self.enabled or not self.sources:
            return ""

        # 1. Calcular relevancia de cada fuente
        scored_sources = []
        for source in self.sources.values():
            if source.enabled:
                relevance = source.score_relevance(user_input)
                scored_sources.append((source, relevance))

        # 2. Asignar presupuesto
        allocations = self.budget.allocate(scored_sources)

        if not allocations:
            return ""

        # 3. Obtener contexto de cada fuente con su presupuesto
        context_parts = []
        allocation_record = {"timestamp": time.time(), "sources": {}}

        for source_name, chars in sorted(allocations.items(),
                                          key=lambda x: x[1], reverse=True):
            source = self.sources.get(source_name)
            if not source:
                continue

            context = source.get_context(user_input, chars)
            if context:
                # Truncar al presupuesto asignado
                if len(context) > chars:
                    context = context[:chars].rsplit(" ", 1)[0]
                context_parts.append(context)
                allocation_record["sources"][source_name] = len(context)

        # 4. Ensamblar resultado
        result = "\n\n".join(context_parts) if context_parts else ""

        # Registrar
        self.total_routes += 1
        self.total_chars_assembled += len(result)

        self.allocation_history.append(allocation_record)
        if len(self.allocation_history) > self.max_history:
            self.allocation_history = self.allocation_history[-self.max_history:]

        return result

    def record_feedback(self, positive: bool, active_sources: list = None):
        """
        Registra feedback para ajustar usefulness de fuentes activas.
        active_sources: lista de nombres de fuentes que participaron.
        """
        if not active_sources and self.allocation_history:
            # Usar la última allocation
            last = self.allocation_history[-1]
            active_sources = list(last.get("sources", {}).keys())

        if active_sources:
            for name in active_sources:
                if name in self.sources:
                    self.sources[name].record_usefulness(positive)

    def get_source_stats(self) -> dict:
        """Estadísticas por fuente."""
        stats = {}
        for name, source in self.sources.items():
            stats[name] = {
                "enabled": source.enabled,
                "total_used": source.total_used,
                "total_chars": source.total_chars_provided,
                "avg_usefulness": round(source.avg_usefulness, 3),
                "base_priority": source.base_priority,
            }
        return stats

    def get_stats(self) -> dict:
        """Estadísticas generales."""
        return {
            "total_routes": self.total_routes,
            "total_chars_assembled": self.total_chars_assembled,
            "registered_sources": len(self.sources),
            "enabled_sources": len([s for s in self.sources.values() if s.enabled]),
            "budget": self.budget.total_budget,
            "source_stats": self.get_source_stats(),
        }

    def status(self) -> str:
        """Status de una línea."""
        enabled = len([s for s in self.sources.values() if s.enabled])
        return (f"Fuentes: {enabled}/{len(self.sources)} | "
                f"Routes: {self.total_routes} | "
                f"Budget: {self.budget.total_budget} chars")

    def generate_report(self) -> str:
        """Reporte detallado."""
        lines = ["=== CONTEXT ROUTER REPORT ==="]
        lines.append(f"Total routes: {self.total_routes}")
        lines.append(f"Total chars ensamblados: {self.total_chars_assembled}")
        lines.append(f"Presupuesto total: {self.budget.total_budget} chars")
        lines.append(f"Fuentes registradas: {len(self.sources)}")

        if self.sources:
            lines.append("\nFuentes:")
            # Ordenar por uso
            sorted_sources = sorted(
                self.sources.values(),
                key=lambda s: s.total_used,
                reverse=True,
            )
            for source in sorted_sources:
                status = "✓" if source.enabled else "✗"
                avg_chars = (source.total_chars_provided / source.total_used
                             if source.total_used > 0 else 0)
                lines.append(
                    f"  {status} {source.name:20s} | "
                    f"usado={source.total_used:4d} | "
                    f"avg_chars={avg_chars:5.0f} | "
                    f"útil={source.avg_usefulness:.0%} | "
                    f"prioridad={source.base_priority:.1f}"
                )

        # Última allocation
        if self.allocation_history:
            last = self.allocation_history[-1]
            lines.append("\nÚltima allocation:")
            for name, chars in sorted(last.get("sources", {}).items(),
                                       key=lambda x: x[1], reverse=True):
                lines.append(f"  {name}: {chars} chars")

        return "\n".join(lines)

    def save(self):
        """Persiste estado a disco."""
        source_data = {}
        for name, source in self.sources.items():
            source_data[name] = source.to_dict()

        data = {
            "total_routes": self.total_routes,
            "total_chars_assembled": self.total_chars_assembled,
            "sources": source_data,
            "allocation_history": self.allocation_history[-self.max_history:],
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
            self.total_routes = data.get("total_routes", 0)
            self.total_chars_assembled = data.get("total_chars_assembled", 0)
            self.allocation_history = data.get("allocation_history", [])

            # Restaurar stats de fuentes (getters se conectan después)
            for name, sdata in data.get("sources", {}).items():
                source = ContextSource(
                    name=name,
                    max_chars=sdata.get("max_chars", 800),
                    base_priority=sdata.get("base_priority", 0.5),
                    keywords=sdata.get("keywords", []),
                )
                source.enabled = sdata.get("enabled", True)
                source.total_used = sdata.get("total_used", 0)
                source.total_chars_provided = sdata.get("total_chars_provided", 0)
                source.avg_usefulness = sdata.get("avg_usefulness", 0.5)
                self.sources[name] = source
        except Exception:
            pass

    def clear(self):
        """Limpia estado (mantiene sources registradas)."""
        self.total_routes = 0
        self.total_chars_assembled = 0
        self.allocation_history = []
        for source in self.sources.values():
            source.total_used = 0
            source.total_chars_provided = 0
            source.avg_usefulness = 0.5
