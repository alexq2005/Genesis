"""
GENESIS — Abstraction Engine (v2.9)

Motor de abstracción: extrae patrones generales de interacciones
específicas. Cuando ve que el usuario repite patrones similares,
los generaliza en reglas abstractas reutilizables.

Componentes:
- AbstractPattern: patrón abstracto con instancias y confianza
- PatternMatcher: detecta similitudes entre interacciones
- AbstractionEngine: coordinador con persistencia
"""
import time
import json
import hashlib
from pathlib import Path
from collections import defaultdict


class AbstractPattern:
    """Un patrón abstracto extraído de múltiples instancias."""

    def __init__(self, name: str, template: str, domain: str = "general"):
        self.pattern_id = hashlib.md5(
            f"{name}{time.time()}".encode()).hexdigest()[:10]
        self.name = name
        self.template = template     # Plantilla generalizada
        self.domain = domain
        self.instances = []          # Instancias concretas
        self.max_instances = 20
        self.confidence = 0.0        # 0.0 - 1.0
        self.applications = 0        # Veces que se aplicó
        self.created_at = time.time()
        self.updated_at = time.time()

    def add_instance(self, text: str):
        """Agrega una instancia concreta del patrón."""
        self.instances.append({
            "text": text[:300],
            "time": time.time(),
        })
        if len(self.instances) > self.max_instances:
            self.instances = self.instances[-self.max_instances:]
        self._update_confidence()
        self.updated_at = time.time()

    def _update_confidence(self):
        """Actualiza confianza basada en número de instancias."""
        n = len(self.instances)
        # Confianza crece con más instancias (asintótica)
        self.confidence = min(1.0, n / (n + 3.0))

    @property
    def strength(self) -> float:
        """Fuerza del patrón = confianza × frecuencia de aplicación."""
        app_factor = min(1.0, self.applications / 10.0)
        return self.confidence * 0.7 + app_factor * 0.3

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "template": self.template,
            "domain": self.domain,
            "instances": self.instances,
            "confidence": round(self.confidence, 4),
            "applications": self.applications,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AbstractPattern":
        p = cls(
            name=data.get("name", ""),
            template=data.get("template", ""),
            domain=data.get("domain", "general"),
        )
        p.pattern_id = data.get("pattern_id", p.pattern_id)
        p.instances = data.get("instances", [])
        p.confidence = data.get("confidence", 0.0)
        p.applications = data.get("applications", 0)
        p.created_at = data.get("created_at", time.time())
        p.updated_at = data.get("updated_at", time.time())
        return p


class PatternMatcher:
    """Detecta similitudes entre interacciones para abstracción."""

    # Patrones de interacción recurrente
    INTERACTION_PATTERNS = {
        "debug_cycle": {
            "keywords": ["error", "fix", "debug", "falla", "no funciona", "bug"],
            "template": "El usuario tiene un ciclo de debugging: describe error → pide fix → verifica",
        },
        "learning_sequence": {
            "keywords": ["que es", "como funciona", "explica", "ejemplo", "tutorial"],
            "template": "El usuario sigue una secuencia de aprendizaje: concepto → mecanismo → ejemplo",
        },
        "implementation_flow": {
            "keywords": ["implementa", "codigo", "funcion", "clase", "crea"],
            "template": "El usuario sigue un flujo de implementación: requisito → diseño → código",
        },
        "refactor_pattern": {
            "keywords": ["refactoriza", "mejora", "optimiza", "simplifica", "limpia"],
            "template": "El usuario busca optimización iterativa: identifica problema → refactoriza",
        },
        "exploration_spiral": {
            "keywords": ["que pasa si", "alternativa", "otra forma", "posibilidad"],
            "template": "El usuario explora alternativas en espiral: pregunta → alternativa → pregunta",
        },
    }

    def detect_patterns(self, text: str) -> list:
        """Detecta qué patrones de interacción aplican al texto."""
        text_lower = text.lower()
        detected = []

        for pattern_key, config in self.INTERACTION_PATTERNS.items():
            hits = sum(1 for kw in config["keywords"] if kw in text_lower)
            if hits >= 2:
                detected.append({
                    "key": pattern_key,
                    "template": config["template"],
                    "hits": hits,
                    "confidence": min(1.0, hits / len(config["keywords"])),
                })

        detected.sort(key=lambda x: x["confidence"], reverse=True)
        return detected

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud entre dos textos (containment)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        return len(intersection) / min(len(words1), len(words2))


class AbstractionEngine:
    """
    Coordinador de abstracción.
    Extrae patrones generales de interacciones específicas.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/abstraction")
        self.data_file = self.base_dir / "abstraction_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.patterns = {}           # pattern_id -> AbstractPattern
        self.matcher = PatternMatcher()
        self.recent_inputs = []      # Últimos N inputs para detectar repeticiones
        self.max_recent = 50
        self.max_patterns = 100
        self.total_abstractions = 0
        self.enabled = True

        self._load()

    def observe(self, text: str, domain: str = "general"):
        """Observa texto y busca patrones abstractos."""
        if not self.enabled or not text:
            return

        # Guardar input reciente
        self.recent_inputs.append({
            "text": text[:300],
            "domain": domain,
            "time": time.time(),
        })
        if len(self.recent_inputs) > self.max_recent:
            self.recent_inputs = self.recent_inputs[-self.max_recent:]

        # Detectar patrones en el texto actual
        detected = self.matcher.detect_patterns(text)
        for det in detected:
            self._register_pattern(
                name=det["key"],
                template=det["template"],
                instance=text[:300],
                domain=domain,
            )

        # Buscar repeticiones con inputs anteriores
        self._detect_repetitions(text, domain)

    def _register_pattern(self, name: str, template: str,
                          instance: str, domain: str):
        """Registra o actualiza un patrón abstracto."""
        # Buscar patrón existente por nombre
        existing = None
        for p in self.patterns.values():
            if p.name == name:
                existing = p
                break

        if existing:
            existing.add_instance(instance)
        else:
            pattern = AbstractPattern(name, template, domain)
            pattern.add_instance(instance)
            self.patterns[pattern.pattern_id] = pattern
            self.total_abstractions += 1

        self._evict()

    def _detect_repetitions(self, text: str, domain: str):
        """Detecta repeticiones de patrones en inputs recientes."""
        if len(self.recent_inputs) < 3:
            return

        # Buscar similitudes con inputs anteriores (excluyendo el último)
        similar_count = 0
        for entry in self.recent_inputs[:-1]:
            sim = self.matcher.compute_similarity(text, entry["text"])
            if sim > 0.5:
                similar_count += 1

        if similar_count >= 2:
            # Patrón detectado por repetición
            words = text.lower().split()
            if len(words) > 3:
                theme = " ".join(words[:5])
                self._register_pattern(
                    name=f"repetition_{theme[:20]}",
                    template=f"El usuario repite un patron similar sobre '{theme}'",
                    instance=text[:300],
                    domain=domain,
                )

    def get_active_patterns(self, min_confidence: float = 0.3) -> list:
        """Retorna patrones con suficiente confianza."""
        active = [p for p in self.patterns.values()
                  if p.confidence >= min_confidence]
        active.sort(key=lambda p: p.strength, reverse=True)
        return active

    def apply_pattern(self, pattern_id: str):
        """Marca un patrón como aplicado."""
        p = self.patterns.get(pattern_id)
        if p:
            p.applications += 1
            p.updated_at = time.time()

    def get_context_for_prompt(self, max_chars: int = 300) -> str:
        """Genera contexto de patrones para prompt."""
        if not self.enabled:
            return ""
        active = self.get_active_patterns(min_confidence=0.5)[:2]
        if not active:
            return ""

        lines = ["[PATRONES DETECTADOS]"]
        for p in active:
            lines.append(f"  {p.name}: {p.template} (conf={p.confidence:.0%})")
        return "\n".join(lines)[:max_chars]

    def _evict(self):
        if len(self.patterns) <= self.max_patterns:
            return
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.strength,
            reverse=True,
        )
        keep = sorted_patterns[:self.max_patterns]
        self.patterns = {p.pattern_id: p for p in keep}

    def get_stats(self) -> dict:
        active = len(self.get_active_patterns())
        return {
            "total_patterns": len(self.patterns),
            "active_patterns": active,
            "total_abstractions": self.total_abstractions,
            "recent_inputs": len(self.recent_inputs),
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Patrones: {stats['total_patterns']} "
                f"(activos={stats['active_patterns']}) | "
                f"Abstracciones: {stats['total_abstractions']}")

    def generate_report(self) -> str:
        lines = ["=== ABSTRACTION ENGINE REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total patrones: {stats['total_patterns']}")
        lines.append(f"Patrones activos: {stats['active_patterns']}")
        lines.append(f"Total abstracciones: {stats['total_abstractions']}")
        lines.append(f"Inputs recientes: {stats['recent_inputs']}")

        active = self.get_active_patterns()[:10]
        if active:
            lines.append(f"\nPatrones activos:")
            for p in active:
                bar = "█" * int(p.strength * 20) + "░" * (20 - int(p.strength * 20))
                lines.append(f"  [{bar}] {p.name}")
                lines.append(f"    {p.template}")
                lines.append(f"    conf={p.confidence:.0%} apps={p.applications} "
                             f"instances={len(p.instances)}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_abstractions": self.total_abstractions,
            "patterns": {k: v.to_dict() for k, v in self.patterns.items()},
            "recent_inputs": self.recent_inputs[-self.max_recent:],
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
            self.total_abstractions = data.get("total_abstractions", 0)
            self.recent_inputs = data.get("recent_inputs", [])
            for pid, pd in data.get("patterns", {}).items():
                self.patterns[pid] = AbstractPattern.from_dict(pd)
        except Exception:
            pass

    def clear(self):
        self.patterns = {}
        self.recent_inputs = []
        self.total_abstractions = 0
