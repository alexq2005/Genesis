"""
GENESIS — Dream Engine (v3.0)

Procesamiento offline de experiencias. Consolida memorias, refuerza
patrones fuertes, debilita irrelevantes. Inspirado en consolidación
durante sueño REM: comprime experiencias, genera conexiones latentes.

Componentes:
- DreamFragment: fragmento procesado de una experiencia
- ConsolidationStrategy: estrategias de consolidación
- DreamProcessor: procesa experiencias acumuladas
- DreamEngine: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class DreamFragment:
    """Un fragmento procesado de experiencia."""

    def __init__(self, content: str, domain: str = "general",
                 emotional_weight: float = 0.5):
        self.fragment_id = hashlib.md5(
            f"{content[:50]}{time.time()}".encode()).hexdigest()[:10]
        self.content = content[:300]
        self.domain = domain
        self.emotional_weight = max(0.0, min(1.0, emotional_weight))
        self.consolidation_count = 0
        self.strength = emotional_weight     # Fuerza del recuerdo
        self.connections = []                # IDs de fragmentos relacionados
        self.max_connections = 10
        self.created_at = time.time()
        self.last_consolidated = None

    def consolidate(self, boost: float = 0.1):
        """Consolida este fragmento (lo refuerza)."""
        self.consolidation_count += 1
        self.strength = min(1.0, self.strength + boost)
        self.last_consolidated = time.time()

    def decay(self, factor: float = 0.95):
        """Aplica decaimiento (olvido gradual)."""
        self.strength *= factor
        self.strength = max(0.01, self.strength)

    def add_connection(self, fragment_id: str):
        """Conecta con otro fragmento."""
        if fragment_id not in self.connections:
            self.connections.append(fragment_id)
            if len(self.connections) > self.max_connections:
                self.connections = self.connections[-self.max_connections:]

    def to_dict(self) -> dict:
        return {
            "fragment_id": self.fragment_id,
            "content": self.content,
            "domain": self.domain,
            "emotional_weight": round(self.emotional_weight, 3),
            "consolidation_count": self.consolidation_count,
            "strength": round(self.strength, 4),
            "connections": self.connections,
            "created_at": self.created_at,
            "last_consolidated": self.last_consolidated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DreamFragment":
        f = cls(
            content=data.get("content", ""),
            domain=data.get("domain", "general"),
            emotional_weight=data.get("emotional_weight", 0.5),
        )
        f.fragment_id = data.get("fragment_id", f.fragment_id)
        f.consolidation_count = data.get("consolidation_count", 0)
        f.strength = data.get("strength", 0.5)
        f.connections = data.get("connections", [])
        f.created_at = data.get("created_at", time.time())
        f.last_consolidated = data.get("last_consolidated", None)
        return f


class ConsolidationStrategy:
    """Estrategias de consolidación de memorias."""

    STRATEGIES = {
        "emotional_priority": {
            "name": "Prioridad Emocional",
            "description": "Refuerza experiencias con alta carga emocional.",
            "boost": 0.15,
            "decay": 0.9,
        },
        "frequency_based": {
            "name": "Basado en Frecuencia",
            "description": "Refuerza patrones que se repiten frecuentemente.",
            "boost": 0.1,
            "decay": 0.95,
        },
        "connection_based": {
            "name": "Basado en Conexiones",
            "description": "Refuerza fragmentos con muchas conexiones.",
            "boost": 0.12,
            "decay": 0.93,
        },
        "recency_based": {
            "name": "Basado en Recencia",
            "description": "Refuerza experiencias recientes, olvida antiguas.",
            "boost": 0.08,
            "decay": 0.85,
        },
    }

    @classmethod
    def get(cls, key: str) -> dict:
        return cls.STRATEGIES.get(key, cls.STRATEGIES["frequency_based"])


class DreamProcessor:
    """Procesa experiencias acumuladas (ciclo de sueño)."""

    def __init__(self, strategy: str = "frequency_based"):
        self.strategy_key = strategy
        self.strategy = ConsolidationStrategy.get(strategy)
        self.total_cycles = 0

    def run_cycle(self, fragments: dict) -> dict:
        """Ejecuta un ciclo de consolidación."""
        if not fragments:
            return {"consolidated": 0, "decayed": 0, "connections": 0}

        consolidated = 0
        decayed = 0
        connections = 0
        boost = self.strategy["boost"]
        decay = self.strategy["decay"]

        fragments_list = list(fragments.values())

        for frag in fragments_list:
            # Consolidar fragmentos fuertes
            if frag.emotional_weight > 0.5 or frag.consolidation_count > 0:
                frag.consolidate(boost)
                consolidated += 1
            else:
                # Decay para fragmentos débiles
                frag.decay(decay)
                decayed += 1

            # Buscar conexiones por dominio
            for other in fragments_list:
                if other.fragment_id != frag.fragment_id:
                    if other.domain == frag.domain and frag.strength > 0.3:
                        frag.add_connection(other.fragment_id)
                        connections += 1

        self.total_cycles += 1
        return {
            "consolidated": consolidated,
            "decayed": decayed,
            "connections": connections,
        }


class DreamEngine:
    """
    Coordinador de procesamiento de experiencias.
    Consolida memorias y genera conexiones latentes.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/dream")
        self.data_file = self.base_dir / "dream_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.fragments = {}          # fragment_id -> DreamFragment
        self.max_fragments = 200
        self.processor = DreamProcessor()
        self.pending_experiences = []   # Experiencias pendientes de procesar
        self.max_pending = 50
        self.total_dreams = 0        # Ciclos de "sueño" ejecutados
        self.total_fragments_created = 0
        self.last_dream_time = None
        self.enabled = True

        self._load()

    def record_experience(self, content: str, domain: str = "general",
                          emotional_weight: float = 0.5):
        """Registra una experiencia para procesar luego."""
        if not self.enabled or not content:
            return

        self.pending_experiences.append({
            "content": content[:300],
            "domain": domain,
            "emotional_weight": max(0.0, min(1.0, emotional_weight)),
            "time": time.time(),
        })
        if len(self.pending_experiences) > self.max_pending:
            self.pending_experiences = self.pending_experiences[-self.max_pending:]

    def dream(self, strategy: str = None) -> dict:
        """Ejecuta un ciclo de 'sueño' — procesa experiencias pendientes."""
        if not self.enabled:
            return {"status": "disabled"}

        # Convertir pending a fragmentos
        for exp in self.pending_experiences:
            frag = DreamFragment(
                content=exp["content"],
                domain=exp["domain"],
                emotional_weight=exp["emotional_weight"],
            )
            self.fragments[frag.fragment_id] = frag
            self.total_fragments_created += 1

        self.pending_experiences = []

        # Consolidación
        if strategy:
            self.processor = DreamProcessor(strategy)

        cycle_result = self.processor.run_cycle(self.fragments)
        self.total_dreams += 1
        self.last_dream_time = time.time()

        # Evicción de fragmentos muy débiles
        self._evict()

        return {
            "status": "completed",
            "cycle": self.total_dreams,
            **cycle_result,
        }

    def get_strongest_memories(self, n: int = 5) -> list:
        """Retorna los N fragmentos más fuertes."""
        sorted_frags = sorted(
            self.fragments.values(),
            key=lambda f: f.strength,
            reverse=True,
        )
        return [f.to_dict() for f in sorted_frags[:n]]

    def get_domain_memories(self, domain: str) -> list:
        """Retorna fragmentos de un dominio específico."""
        return [f.to_dict() for f in self.fragments.values()
                if f.domain == domain]

    def _evict(self):
        """Elimina fragmentos muy débiles."""
        if len(self.fragments) <= self.max_fragments:
            return
        sorted_frags = sorted(
            self.fragments.values(),
            key=lambda f: f.strength,
            reverse=True,
        )
        keep = sorted_frags[:self.max_fragments]
        self.fragments = {f.fragment_id: f for f in keep}

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de experiencias consolidadas para prompt."""
        if not self.enabled:
            return ""

        strong = self.get_strongest_memories(2)
        if not strong:
            return ""

        # Solo inyectar si hay fragmentos significativos
        if strong[0].get("strength", 0) < 0.5:
            return ""

        lines = ["[MEMORIAS CONSOLIDADAS]"]
        for s in strong:
            lines.append(f"  {s['domain']}: {s['content'][:80]}...")
        return "\n".join(lines)[:max_chars]

    def get_stats(self) -> dict:
        total_frags = len(self.fragments)
        strong = len([f for f in self.fragments.values() if f.strength > 0.5])
        return {
            "total_fragments": total_frags,
            "strong_fragments": strong,
            "pending_experiences": len(self.pending_experiences),
            "total_dreams": self.total_dreams,
            "total_created": self.total_fragments_created,
            "last_dream": self.last_dream_time,
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Fragmentos: {stats['total_fragments']} "
                f"(fuertes={stats['strong_fragments']}) | "
                f"Sueños: {stats['total_dreams']} | "
                f"Pendientes: {stats['pending_experiences']}")

    def generate_report(self) -> str:
        lines = ["=== DREAM ENGINE REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total fragmentos: {stats['total_fragments']}")
        lines.append(f"Fragmentos fuertes: {stats['strong_fragments']}")
        lines.append(f"Pendientes: {stats['pending_experiences']}")
        lines.append(f"Total sueños: {stats['total_dreams']}")
        lines.append(f"Total creados: {stats['total_created']}")

        strong = self.get_strongest_memories(5)
        if strong:
            lines.append(f"\nMemorias mas fuertes:")
            for s in strong:
                bar = "█" * int(s["strength"] * 20) + "░" * (20 - int(s["strength"] * 20))
                lines.append(f"  [{bar}] {s['domain']}: "
                             f"{s['content'][:60]} (x{s['consolidation_count']})")

        # Dominios
        domains = defaultdict(int)
        for f in self.fragments.values():
            domains[f.domain] += 1
        if domains:
            lines.append(f"\nDominios en memoria:")
            for d, c in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]:
                lines.append(f"  {d}: {c} fragmentos")

        return "\n".join(lines)

    def save(self):
        data = {
            "fragments": {k: v.to_dict() for k, v in self.fragments.items()},
            "pending_experiences": self.pending_experiences,
            "total_dreams": self.total_dreams,
            "total_fragments_created": self.total_fragments_created,
            "last_dream_time": self.last_dream_time,
        }
        try:
            self.data_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        if not self.data_file.exists():
            return
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            for fid, fd in data.get("fragments", {}).items():
                self.fragments[fid] = DreamFragment.from_dict(fd)
            self.pending_experiences = data.get("pending_experiences", [])
            self.total_dreams = data.get("total_dreams", 0)
            self.total_fragments_created = data.get("total_fragments_created", 0)
            self.last_dream_time = data.get("last_dream_time", None)
        except Exception:
            pass

    def clear(self):
        self.fragments = {}
        self.pending_experiences = []
        self.total_dreams = 0
        self.total_fragments_created = 0
        self.last_dream_time = None
