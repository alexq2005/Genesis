"""
GENESIS — Temporal Reasoner (v4.1)

Razonamiento temporal explícito: Genesis construye timelines,
detecta relaciones temporales entre eventos, y predice duraciones
basándose en promedios históricos de eventos similares.

Componentes:
- TemporalEvent: evento con timestamp, duración, dominio y relaciones
- Timeline: lista ordenada de eventos con consultas por rango
- TemporalRelation: detección de relaciones temporales entre eventos
- TemporalReasoner: coordinador con persistencia y contexto temporal
"""
import time
import json
import re
from pathlib import Path
from collections import defaultdict


class TemporalEvent:
    """Un evento temporal con metadatos y relaciones."""

    def __init__(self, name: str, timestamp: float = None,
                 duration_seconds: float = 0.0, domain: str = "general",
                 tags: list = None, relations: dict = None):
        self.name = name.strip()
        self.timestamp = timestamp or time.time()
        self.duration_seconds = max(0.0, duration_seconds)
        self.domain = domain
        self.tags = list(tags) if tags else []
        self.relations = relations if relations else {
            "before": [],
            "after": [],
            "during": [],
        }

    @property
    def end_time(self) -> float:
        """Timestamp de finalización del evento."""
        return self.timestamp + self.duration_seconds

    @property
    def is_instantaneous(self) -> bool:
        return self.duration_seconds == 0.0

    def overlaps_with(self, other: "TemporalEvent") -> bool:
        """Verifica si dos eventos se solapan en el tiempo."""
        return (self.timestamp < other.end_time and
                self.end_time > other.timestamp)

    def add_relation(self, relation_type: str, event_name: str):
        """Agrega una relación temporal con otro evento."""
        if relation_type not in self.relations:
            self.relations[relation_type] = []
        if event_name not in self.relations[relation_type]:
            self.relations[relation_type].append(event_name)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "domain": self.domain,
            "tags": self.tags,
            "relations": self.relations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TemporalEvent":
        return cls(
            name=data.get("name", ""),
            timestamp=data.get("timestamp", time.time()),
            duration_seconds=data.get("duration_seconds", 0.0),
            domain=data.get("domain", "general"),
            tags=data.get("tags", []),
            relations=data.get("relations", {"before": [], "after": [], "during": []}),
        )


class Timeline:
    """Lista ordenada de eventos temporales con consultas por rango."""

    def __init__(self, max_events: int = 500):
        self.events = []       # Ordenados por timestamp
        self.index = {}        # name -> TemporalEvent
        self.max_events = max_events

    def add_event(self, event: TemporalEvent):
        """Agrega un evento manteniendo orden cronológico."""
        # Si ya existe un evento con el mismo nombre, actualizar
        if event.name in self.index:
            self.events = [e for e in self.events if e.name != event.name]
        self.index[event.name] = event
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

        # Evict si excede máximo
        if len(self.events) > self.max_events:
            removed = self.events.pop(0)
            self.index.pop(removed.name, None)

    def get_event(self, name: str) -> TemporalEvent:
        """Busca un evento por nombre (búsqueda exacta y parcial)."""
        if name in self.index:
            return self.index[name]
        # Búsqueda parcial case-insensitive
        name_lower = name.lower()
        for key, event in self.index.items():
            if name_lower in key.lower() or key.lower() in name_lower:
                return event
        return None

    def get_events_between(self, start: float, end: float) -> list:
        """Retorna eventos cuyo timestamp está en el rango [start, end]."""
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_by_domain(self, domain: str) -> list:
        """Retorna eventos filtrados por dominio."""
        return [e for e in self.events if e.domain == domain]

    def get_events_by_tag(self, tag: str) -> list:
        """Retorna eventos que contengan un tag específico."""
        return [e for e in self.events if tag in e.tags]

    def get_sequence(self) -> list:
        """Retorna todos los eventos en orden cronológico."""
        return list(self.events)

    def get_recent(self, n: int = 10) -> list:
        """Retorna los N eventos más recientes."""
        return self.events[-n:]

    @property
    def count(self) -> int:
        return len(self.events)

    @property
    def domains(self) -> list:
        """Lista de dominios únicos."""
        return list(set(e.domain for e in self.events))

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
        }

    def load_dict(self, data: dict):
        self.events = []
        self.index = {}
        for ed in data.get("events", []):
            event = TemporalEvent.from_dict(ed)
            self.events.append(event)
            self.index[event.name] = event
        self.events.sort(key=lambda e: e.timestamp)


class TemporalRelation:
    """Detección de relaciones temporales entre eventos."""

    RELATION_TYPES = ["before", "after", "overlapping", "concurrent", "during"]

    def detect(self, event_a: TemporalEvent, event_b: TemporalEvent) -> str:
        """
        Detecta la relación temporal de event_a respecto a event_b.
        Retorna: before, after, overlapping, concurrent, during.
        """
        # Concurrent: ambos empiezan en el mismo segundo (tolerance 1s)
        if abs(event_a.timestamp - event_b.timestamp) < 1.0:
            return "concurrent"

        # During: event_a ocurre completamente dentro de event_b
        if (event_a.timestamp >= event_b.timestamp and
                event_a.end_time <= event_b.end_time and
                event_b.duration_seconds > 0):
            return "during"

        # Overlapping: se solapan parcialmente
        if event_a.overlaps_with(event_b):
            return "overlapping"

        # Before/After: sin solapamiento
        if event_a.end_time <= event_b.timestamp:
            return "before"
        if event_a.timestamp >= event_b.end_time:
            return "after"

        return "before" if event_a.timestamp < event_b.timestamp else "after"

    def detect_all(self, event: TemporalEvent, timeline: Timeline) -> dict:
        """Detecta todas las relaciones de un evento con el timeline."""
        relations = defaultdict(list)
        for other in timeline.get_sequence():
            if other.name == event.name:
                continue
            rel = self.detect(event, other)
            relations[rel].append(other.name)
        return dict(relations)

    def build_temporal_graph(self, timeline: Timeline) -> dict:
        """Construye grafo completo de relaciones temporales."""
        graph = {}
        events = timeline.get_sequence()
        for i, event_a in enumerate(events):
            rels = defaultdict(list)
            for j, event_b in enumerate(events):
                if i == j:
                    continue
                rel = self.detect(event_a, event_b)
                rels[rel].append(event_b.name)
            graph[event_a.name] = dict(rels)
        return graph


class TemporalReasoner:
    """
    Coordinador de razonamiento temporal.
    Construye timelines, detecta relaciones entre eventos,
    predice duraciones y genera contexto temporal para prompts.
    """

    TEMPORAL_KEYWORDS = [
        r"cu[aá]ndo", r"antes\s+de", r"despu[eé]s\s+de", r"durante",
        r"cu[aá]nto\s+(?:dur[oó]|tarda|tiempo)", r"secuencia",
        r"orden\s+(?:cronol[oó]gico|temporal)", r"historial",
        r"(?:primera?|[uú]ltima?)\s+vez", r"frecuencia",
        r"cada\s+cu[aá]nto", r"timeline", r"simultáneo",
    ]

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/temporal")
        self.data_file = self.base_dir / "temporal_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.timeline = Timeline(max_events=500)
        self.relation_detector = TemporalRelation()
        self.duration_history = defaultdict(list)  # domain -> [durations]
        self.total_events = 0
        self.total_queries = 0
        self.enabled = True

        self._load()

    def record_event(self, name: str, domain: str = "general",
                     duration: float = 0.0, tags: list = None) -> TemporalEvent:
        """Registra un evento en el timeline con timestamp actual."""
        if not self.enabled or not name:
            return None

        event = TemporalEvent(
            name=name,
            timestamp=time.time(),
            duration_seconds=duration,
            domain=domain,
            tags=tags,
        )

        # Detectar relaciones con eventos existentes
        if self.timeline.count > 0:
            rels = self.relation_detector.detect_all(event, self.timeline)
            event.relations = rels

        self.timeline.add_event(event)
        self.total_events += 1

        # Registrar duración en historial por dominio
        if duration > 0:
            self.duration_history[domain].append(duration)
            # Limitar historial a 100 por dominio
            if len(self.duration_history[domain]) > 100:
                self.duration_history[domain] = self.duration_history[domain][-100:]

        return event

    def query_before(self, event_name: str) -> list:
        """Retorna eventos que ocurrieron antes del evento dado."""
        self.total_queries += 1
        event = self.timeline.get_event(event_name)
        if not event:
            return []
        return [e for e in self.timeline.get_sequence()
                if e.end_time <= event.timestamp and e.name != event.name]

    def query_after(self, event_name: str) -> list:
        """Retorna eventos que ocurrieron después del evento dado."""
        self.total_queries += 1
        event = self.timeline.get_event(event_name)
        if not event:
            return []
        return [e for e in self.timeline.get_sequence()
                if e.timestamp >= event.end_time and e.name != event.name]

    def query_concurrent(self, event_name: str) -> list:
        """Retorna eventos concurrentes o solapados con el evento dado."""
        self.total_queries += 1
        event = self.timeline.get_event(event_name)
        if not event:
            return []
        return [e for e in self.timeline.get_sequence()
                if e.name != event.name and e.overlaps_with(event)]

    def predict_duration(self, event_type: str) -> float:
        """Predice la duración de un tipo de evento basándose en promedios históricos."""
        self.total_queries += 1

        # Buscar por dominio exacto
        if event_type in self.duration_history and self.duration_history[event_type]:
            durations = self.duration_history[event_type]
            return sum(durations) / len(durations)

        # Buscar por coincidencia parcial en dominios
        for domain, durations in self.duration_history.items():
            if (event_type.lower() in domain.lower() or
                    domain.lower() in event_type.lower()):
                if durations:
                    return sum(durations) / len(durations)

        # Buscar por duración promedio de eventos con tags similares
        matching_durations = []
        for event in self.timeline.get_sequence():
            if (event.duration_seconds > 0 and
                    (event_type.lower() in event.name.lower() or
                     event_type.lower() in event.domain.lower() or
                     event_type.lower() in " ".join(event.tags).lower())):
                matching_durations.append(event.duration_seconds)

        if matching_durations:
            return sum(matching_durations) / len(matching_durations)

        return 0.0  # Sin datos suficientes

    def get_timeline_summary(self, last_n: int = 10) -> str:
        """Genera resumen textual del timeline reciente."""
        recent = self.timeline.get_recent(last_n)
        if not recent:
            return "No hay eventos registrados."

        lines = []
        for event in recent:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(event.timestamp))
            dur_str = f" ({event.duration_seconds:.0f}s)" if event.duration_seconds > 0 else ""
            tag_str = f" [{', '.join(event.tags)}]" if event.tags else ""
            lines.append(f"  {ts} | {event.name}{dur_str}{tag_str} ({event.domain})")

        return "\n".join(lines)

    def _is_temporal_query(self, text: str) -> bool:
        """Detecta si el texto contiene una consulta temporal."""
        text_lower = text.lower()
        for pattern in self.TEMPORAL_KEYWORDS:
            if re.search(pattern, text_lower):
                return True
        return False

    def get_context_for_prompt(self, user_input: str = "", max_chars: int = 500) -> str:
        """Genera contexto temporal relevante para inyectar en prompt."""
        if not self.enabled or self.timeline.count == 0:
            return ""

        if user_input and not self._is_temporal_query(user_input):
            return ""

        lines = ["[CONTEXTO TEMPORAL]"]
        lines.append(f"Eventos registrados: {self.timeline.count}")

        # Timeline reciente
        recent = self.timeline.get_recent(5)
        if recent:
            lines.append("Eventos recientes:")
            for event in recent:
                elapsed = time.time() - event.timestamp
                if elapsed < 60:
                    ago = f"hace {elapsed:.0f}s"
                elif elapsed < 3600:
                    ago = f"hace {elapsed / 60:.0f}min"
                else:
                    ago = f"hace {elapsed / 3600:.1f}h"
                dur_str = f", duración {event.duration_seconds:.0f}s" if event.duration_seconds > 0 else ""
                lines.append(f"  {event.name} ({ago}{dur_str})")

        # Dominios activos
        domains = self.timeline.domains
        if domains:
            lines.append(f"Dominios: {', '.join(domains[:5])}")

        result = "\n".join(lines)
        return result[:max_chars]

    def get_stats(self) -> dict:
        return {
            "total_events": self.total_events,
            "timeline_size": self.timeline.count,
            "domains": self.timeline.domains,
            "total_queries": self.total_queries,
            "duration_domains": len(self.duration_history),
            "avg_durations": {
                domain: round(sum(durs) / len(durs), 2)
                for domain, durs in self.duration_history.items()
                if durs
            },
        }

    def status(self) -> str:
        return (f"Eventos: {self.timeline.count} | "
                f"Dominios: {len(self.timeline.domains)} | "
                f"Total registrados: {self.total_events} | "
                f"Queries: {self.total_queries}")

    def generate_report(self) -> str:
        lines = ["=== TEMPORAL REASONER REPORT ==="]
        lines.append(f"Eventos en timeline: {self.timeline.count}")
        lines.append(f"Total eventos registrados: {self.total_events}")
        lines.append(f"Total queries: {self.total_queries}")
        lines.append(f"Dominios: {', '.join(self.timeline.domains) if self.timeline.domains else 'ninguno'}")

        # Duraciones promedio por dominio
        if self.duration_history:
            lines.append(f"\nDuraciones promedio por dominio:")
            for domain, durs in sorted(self.duration_history.items()):
                avg = sum(durs) / len(durs) if durs else 0
                lines.append(f"  {domain}: {avg:.1f}s (n={len(durs)})")

        # Timeline reciente
        summary = self.get_timeline_summary(10)
        if summary and summary != "No hay eventos registrados.":
            lines.append(f"\nTimeline reciente:")
            lines.append(summary)

        return "\n".join(lines)

    def save(self):
        data = {
            "total_events": self.total_events,
            "total_queries": self.total_queries,
            "timeline": self.timeline.to_dict(),
            "duration_history": dict(self.duration_history),
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
            self.total_events = data.get("total_events", 0)
            self.total_queries = data.get("total_queries", 0)
            self.timeline.load_dict(data.get("timeline", {}))
            for domain, durs in data.get("duration_history", {}).items():
                self.duration_history[domain] = durs
        except Exception:
            pass

    def clear(self):
        self.timeline = Timeline(max_events=500)
        self.duration_history = defaultdict(list)
        self.total_events = 0
        self.total_queries = 0
