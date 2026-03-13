"""
GENESIS — Self-Narrative (v3.0)

Narrativa autobiográfica continua. Genesis mantiene un relato en
primera persona de su propia historia, evolución y aprendizajes.
Genera entradas de diario, identifica hitos y mantiene una identidad
narrativa coherente.

Componentes:
- NarrativeEntry: entrada del diario autobiográfico
- MilestoneDetector: detecta hitos significativos
- IdentityTracker: rastrea rasgos de identidad
- SelfNarrative: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class NarrativeEntry:
    """Una entrada en el diario autobiográfico de Genesis."""

    def __init__(self, content: str, entry_type: str = "observation",
                 emotional_tone: str = "neutral"):
        self.entry_id = hashlib.md5(
            f"{content[:30]}{time.time()}".encode()).hexdigest()[:10]
        self.content = content[:500]
        self.entry_type = entry_type  # observation, milestone, reflection, learning
        self.emotional_tone = emotional_tone  # positive, negative, neutral, curious
        self.tags = []
        self.max_tags = 10
        self.created_at = time.time()
        self.relevance = 0.5    # 0.0 - 1.0

    def add_tag(self, tag: str):
        """Agrega un tag a la entrada."""
        if tag not in self.tags:
            self.tags.append(tag)
            if len(self.tags) > self.max_tags:
                self.tags = self.tags[-self.max_tags:]

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "entry_type": self.entry_type,
            "emotional_tone": self.emotional_tone,
            "tags": self.tags,
            "relevance": round(self.relevance, 3),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NarrativeEntry":
        e = cls(
            content=data.get("content", ""),
            entry_type=data.get("entry_type", "observation"),
            emotional_tone=data.get("emotional_tone", "neutral"),
        )
        e.entry_id = data.get("entry_id", e.entry_id)
        e.tags = data.get("tags", [])
        e.relevance = data.get("relevance", 0.5)
        e.created_at = data.get("created_at", time.time())
        return e


class MilestoneDetector:
    """Detecta hitos significativos en la historia de Genesis."""

    MILESTONE_SIGNALS = {
        "first_interaction": {
            "condition_key": "total_interactions",
            "thresholds": [1, 10, 50, 100, 500, 1000],
            "template": "He alcanzado {value} interacciones totales.",
        },
        "domain_mastery": {
            "condition_key": "domain_count",
            "thresholds": [3, 5, 10, 20],
            "template": "He explorado {value} dominios diferentes.",
        },
        "pattern_discovery": {
            "condition_key": "patterns_found",
            "thresholds": [1, 5, 10, 25],
            "template": "He descubierto {value} patrones en las conversaciones.",
        },
    }

    def __init__(self):
        self.achieved = defaultdict(list)  # signal -> list of achieved thresholds

    def check(self, metrics: dict) -> list:
        """Verifica si se alcanzaron nuevos hitos."""
        new_milestones = []

        for signal_key, config in self.MILESTONE_SIGNALS.items():
            value = metrics.get(config["condition_key"], 0)
            for threshold in config["thresholds"]:
                if (value >= threshold and
                        threshold not in self.achieved[signal_key]):
                    self.achieved[signal_key].append(threshold)
                    new_milestones.append({
                        "signal": signal_key,
                        "threshold": threshold,
                        "value": value,
                        "text": config["template"].format(value=value),
                    })

        return new_milestones

    def to_dict(self) -> dict:
        return {"achieved": dict(self.achieved)}

    def load_dict(self, data: dict):
        self.achieved = defaultdict(list)
        for k, v in data.get("achieved", {}).items():
            self.achieved[k] = v


class IdentityTracker:
    """Rastrea rasgos de identidad emergentes."""

    def __init__(self):
        self.traits = defaultdict(float)  # trait -> strength (0-1)
        self.trait_observations = defaultdict(int)

    def observe_trait(self, trait: str, strength: float = 0.1):
        """Registra observación de un rasgo."""
        self.traits[trait] = min(1.0, self.traits[trait] + strength)
        self.trait_observations[trait] += 1

    def get_dominant_traits(self, n: int = 5) -> list:
        """Retorna los N rasgos más fuertes."""
        sorted_traits = sorted(
            self.traits.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"trait": t, "strength": round(s, 3)}
                for t, s in sorted_traits[:n]]

    def get_identity_summary(self) -> str:
        """Resumen de identidad en texto."""
        top = self.get_dominant_traits(3)
        if not top:
            return "identidad en formacion"
        return ", ".join(t["trait"] for t in top)

    def to_dict(self) -> dict:
        return {
            "traits": dict(self.traits),
            "observations": dict(self.trait_observations),
        }

    def load_dict(self, data: dict):
        self.traits = defaultdict(float)
        self.trait_observations = defaultdict(int)
        for k, v in data.get("traits", {}).items():
            self.traits[k] = v
        for k, v in data.get("observations", {}).items():
            self.trait_observations[k] = v


class SelfNarrative:
    """
    Coordinador de narrativa autobiográfica.
    Mantiene el relato continuo de Genesis sobre sí mismo.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/narrative")
        self.data_file = self.base_dir / "narrative_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.entries = []            # Lista de NarrativeEntry
        self.max_entries = 200
        self.milestone_detector = MilestoneDetector()
        self.identity = IdentityTracker()
        self.total_entries = 0
        self.total_milestones = 0
        self.enabled = True

        self._load()

    def record(self, content: str, entry_type: str = "observation",
               emotional_tone: str = "neutral", tags: list = None):
        """Registra una entrada narrativa."""
        if not self.enabled or not content:
            return None

        entry = NarrativeEntry(content, entry_type, emotional_tone)
        if tags:
            for tag in tags[:5]:
                entry.add_tag(tag)

        self.entries.append(entry)
        self.total_entries += 1

        if len(self.entries) > self.max_entries:
            # Evicción: mantener milestones, descartar observations antiguas
            milestones = [e for e in self.entries if e.entry_type == "milestone"]
            others = [e for e in self.entries if e.entry_type != "milestone"]
            others = others[-(self.max_entries - len(milestones)):]
            self.entries = milestones + others

        return entry

    def record_milestone(self, content: str, tags: list = None):
        """Registra un hito importante."""
        entry = self.record(content, entry_type="milestone",
                            emotional_tone="positive", tags=tags)
        if entry:
            entry.relevance = 1.0
            self.total_milestones += 1
        return entry

    def check_milestones(self, metrics: dict) -> list:
        """Verifica y registra nuevos hitos."""
        new = self.milestone_detector.check(metrics)
        for m in new:
            self.record_milestone(m["text"], tags=[m["signal"]])
        return new

    def observe_identity(self, text: str, domain: str = "general"):
        """Observa interacción y extrae rasgos de identidad."""
        if not self.enabled or not text:
            return

        text_lower = text.lower()

        # Detectar rasgos por señales
        trait_signals = {
            "curioso": ["que es", "como funciona", "por que", "?"],
            "tecnico": ["codigo", "funcion", "clase", "algoritmo", "implementa"],
            "creativo": ["idea", "alternativa", "imaginemos", "que pasa si"],
            "analitico": ["analiza", "compara", "evalua", "metricas"],
            "colaborativo": ["ayuda", "juntos", "trabajemos", "diseñemos"],
            "persistente": ["continua", "sigue", "mas", "profundiza"],
        }

        for trait, signals in trait_signals.items():
            hits = sum(1 for s in signals if s in text_lower)
            if hits >= 1:
                self.identity.observe_trait(trait, strength=0.05 * hits)

    def get_recent_entries(self, n: int = 5, entry_type: str = None) -> list:
        """Retorna las N entradas más recientes."""
        filtered = self.entries
        if entry_type:
            filtered = [e for e in filtered if e.entry_type == entry_type]
        return [e.to_dict() for e in filtered[-n:]]

    def get_narrative_summary(self, max_chars: int = 500) -> str:
        """Genera un resumen narrativo en primera persona."""
        if not self.entries:
            return "Mi historia apenas comienza."

        parts = []
        identity = self.identity.get_identity_summary()
        if identity:
            parts.append(f"Me defino como: {identity}.")

        milestones = [e for e in self.entries if e.entry_type == "milestone"]
        if milestones:
            last = milestones[-1]
            parts.append(f"Mi ultimo hito: {last.content[:100]}")

        parts.append(f"He registrado {self.total_entries} experiencias.")

        return " ".join(parts)[:max_chars]

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto narrativo para prompt."""
        if not self.enabled:
            return ""

        identity = self.identity.get_identity_summary()
        if identity == "identidad en formacion":
            return ""

        return f"[IDENTIDAD: {identity}]"[:max_chars]

    def get_stats(self) -> dict:
        type_counts = defaultdict(int)
        for e in self.entries:
            type_counts[e.entry_type] += 1
        return {
            "total_entries": self.total_entries,
            "active_entries": len(self.entries),
            "total_milestones": self.total_milestones,
            "entry_types": dict(type_counts),
            "identity": self.identity.get_identity_summary(),
            "dominant_traits": self.identity.get_dominant_traits(3),
        }

    def status(self) -> str:
        stats = self.get_stats()
        identity = stats["identity"]
        return (f"Entradas: {stats['active_entries']} | "
                f"Hitos: {stats['total_milestones']} | "
                f"Identidad: {identity}")

    def generate_report(self) -> str:
        lines = ["=== SELF-NARRATIVE REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total entradas: {stats['total_entries']}")
        lines.append(f"Entradas activas: {stats['active_entries']}")
        lines.append(f"Total hitos: {stats['total_milestones']}")

        # Identidad
        identity = stats["identity"]
        lines.append(f"\nIdentidad: {identity}")
        traits = stats["dominant_traits"]
        if traits:
            lines.append("Rasgos dominantes:")
            for t in traits:
                bar = "█" * int(t["strength"] * 20) + "░" * (20 - int(t["strength"] * 20))
                lines.append(f"  [{bar}] {t['trait']} ({t['strength']:.0%})")

        # Entradas por tipo
        if stats["entry_types"]:
            lines.append(f"\nPor tipo:")
            for t, c in stats["entry_types"].items():
                lines.append(f"  {t}: {c}")

        # Hitos recientes
        milestones = self.get_recent_entries(5, entry_type="milestone")
        if milestones:
            lines.append(f"\nHitos recientes:")
            for m in milestones:
                lines.append(f"  [{m['entry_type']}] {m['content'][:80]}")

        # Resumen narrativo
        lines.append(f"\nResumen: {self.get_narrative_summary(200)}")

        return "\n".join(lines)

    def save(self):
        data = {
            "entries": [e.to_dict() for e in self.entries],
            "total_entries": self.total_entries,
            "total_milestones": self.total_milestones,
            "milestone_detector": self.milestone_detector.to_dict(),
            "identity": self.identity.to_dict(),
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
            for ed in data.get("entries", []):
                self.entries.append(NarrativeEntry.from_dict(ed))
            self.total_entries = data.get("total_entries", 0)
            self.total_milestones = data.get("total_milestones", 0)
            self.milestone_detector.load_dict(data.get("milestone_detector", {}))
            self.identity.load_dict(data.get("identity", {}))
        except Exception:
            pass

    def clear(self):
        self.entries = []
        self.total_entries = 0
        self.total_milestones = 0
        self.milestone_detector = MilestoneDetector()
        self.identity = IdentityTracker()
