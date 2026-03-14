"""
GENESIS — Domain Expert (v4.3)

Conocimiento de dominio: Genesis detecta el nivel de expertise del usuario
en cada dominio temático y ajusta la profundidad de sus respuestas.

Componentes:
- DomainProfile: perfil de un dominio con terminología, reglas y nivel
- ExpertiseDetector: detecta nivel del usuario por sofisticación del vocabulario
- DomainExpert: coordinador con registro de dominios y persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class DomainProfile:
    """Perfil de un dominio de conocimiento."""

    VALID_LEVELS = ("novato", "intermedio", "experto")

    def __init__(self, name: str, terminology: dict = None,
                 rules: list = None, depth_level: str = "intermedio"):
        self.profile_id = hashlib.md5(
            name.lower().strip().encode()
        ).hexdigest()[:10]
        self.name = name.lower().strip()
        self.terminology = terminology or {}   # term -> definition
        self.rules = rules or []               # domain-specific rules
        self.depth_level = depth_level if depth_level in self.VALID_LEVELS else "intermedio"
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.detected_levels = []              # history of detected levels

    def add_term(self, term: str, definition: str):
        """Agrega un término al glosario del dominio."""
        self.terminology[term.lower().strip()] = definition.strip()[:300]

    def add_rule(self, rule: str):
        """Agrega una regla al dominio."""
        if rule not in self.rules:
            self.rules.append(rule.strip()[:200])

    def record_detection(self, level: str):
        """Registra una detección de nivel."""
        if level in self.VALID_LEVELS:
            self.detected_levels.append({
                "level": level,
                "timestamp": time.time(),
            })
            # Mantener solo las últimas 20 detecciones
            if len(self.detected_levels) > 20:
                self.detected_levels = self.detected_levels[-20:]
            # Actualizar nivel si hay consenso en las últimas 5
            recent = [d["level"] for d in self.detected_levels[-5:]]
            if len(recent) >= 3:
                counts = defaultdict(int)
                for lvl in recent:
                    counts[lvl] += 1
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= 3:
                    self.depth_level = dominant

    @property
    def term_count(self) -> int:
        return len(self.terminology)

    def get_depth_instructions(self) -> str:
        """Genera instrucciones de profundidad para el prompt."""
        if self.depth_level == "novato":
            return (f"[DOMINIO: {self.name}] El usuario es principiante. "
                    "Usa lenguaje simple, evita jerga técnica, "
                    "da ejemplos concretos y explica cada concepto.")
        elif self.depth_level == "experto":
            return (f"[DOMINIO: {self.name}] El usuario es experto. "
                    "Usa terminología precisa, asume conocimientos previos, "
                    "ve directo al punto sin explicar lo básico.")
        return (f"[DOMINIO: {self.name}] Nivel intermedio. "
                "Equilibra claridad con precisión técnica.")

    def to_dict(self) -> dict:
        return {
            "id": self.profile_id,
            "name": self.name,
            "terminology": self.terminology,
            "rules": self.rules,
            "depth_level": self.depth_level,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "detected_levels": self.detected_levels,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DomainProfile":
        profile = cls(
            name=data.get("name", ""),
            terminology=data.get("terminology", {}),
            rules=data.get("rules", []),
            depth_level=data.get("depth_level", "intermedio"),
        )
        profile.profile_id = data.get("id", profile.profile_id)
        profile.created_at = data.get("created_at", time.time())
        profile.last_accessed = data.get("last_accessed", time.time())
        profile.access_count = data.get("access_count", 0)
        profile.detected_levels = data.get("detected_levels", [])
        return profile


class ExpertiseDetector:
    """Detecta el nivel de expertise del usuario por vocabulario."""

    # Indicadores de nivel por categoría
    NOVICE_INDICATORS = [
        r"\bqu[eé]\s+es\b", r"\bc[oó]mo\s+funciona\b", r"\bno\s+entiendo\b",
        r"\bqu[eé]\s+significa\b", r"\bexpl[ií]came\b", r"\bprincipiante\b",
        r"\bbásico\b", r"\bsimple\b", r"\bfácil\b", r"\bno\s+s[eé]\b",
        r"\bwhat\s+is\b", r"\bhow\s+does\b", r"\bbeginner\b",
    ]

    EXPERT_INDICATORS = [
        r"\boptimizar\b", r"\brefactorizar\b", r"\blatencia\b",
        r"\bcomplejidad\s+computacional\b", r"\btrade-?off\b",
        r"\bescalabilidad\b", r"\bidempotente\b", r"\bpolimorfismo\b",
        r"\bmutex\b", r"\bdeadlock\b", r"\bsharding\b", r"\bCAP\s+theorem\b",
        r"\bconcurrency\b", r"\bthroughput\b", r"\bbig\s*O\b",
        r"\basintótic[oa]\b", r"\bheurístic[oa]\b", r"\bentropía\b",
    ]

    def detect_level(self, text: str, domain: DomainProfile = None) -> str:
        """
        Detecta nivel de expertise basado en vocabulario.
        Retorna 'novato', 'intermedio', o 'experto'.
        """
        if not text or len(text) < 5:
            return "intermedio"

        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        # Contar indicadores de cada nivel
        novice_score = sum(
            1 for p in self.NOVICE_INDICATORS
            if re.search(p, text_lower)
        )
        expert_score = sum(
            1 for p in self.EXPERT_INDICATORS
            if re.search(p, text_lower)
        )

        # Verificar terminología del dominio si está disponible
        domain_term_hits = 0
        if domain and domain.terminology:
            for term in domain.terminology:
                if term in text_lower:
                    domain_term_hits += 1
            # Muchos términos técnicos del dominio = experto
            if domain_term_hits >= 3:
                expert_score += 2
            elif domain_term_hits >= 1:
                expert_score += 1

        # Longitud de palabras promedio (vocabulario sofisticado = más largo)
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
        if avg_word_len > 7:
            expert_score += 1
        elif avg_word_len < 4.5:
            novice_score += 1

        # Decidir nivel
        if expert_score >= 3 and expert_score > novice_score * 2:
            return "experto"
        elif novice_score >= 2 and novice_score > expert_score:
            return "novato"
        return "intermedio"

    def analyze_vocabulary(self, text: str) -> dict:
        """Analiza la sofisticación del vocabulario."""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return {"word_count": 0, "avg_length": 0, "unique_ratio": 0}

        unique = set(words)
        return {
            "word_count": len(words),
            "avg_length": round(sum(len(w) for w in words) / len(words), 2),
            "unique_ratio": round(len(unique) / len(words), 3),
            "long_words": len([w for w in words if len(w) > 8]),
            "technical_density": round(
                len([w for w in unique if len(w) > 6]) / max(len(unique), 1), 3
            ),
        }


class DomainExpert:
    """
    Coordinador de expertise de dominio.
    Registra dominios, detecta niveles de usuario,
    y ajusta profundidad de respuestas.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/domain_expert")
        self.data_file = self.base_dir / "domain_expert_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.domains = {}           # name -> DomainProfile
        self.detector = ExpertiseDetector()
        self.max_domains = 100
        self.total_detections = 0
        self.total_domains = 0
        self.enabled = True

        self._load()

    def register_domain(self, name: str, terminology: dict = None,
                        rules: list = None) -> str:
        """Registra un nuevo dominio o actualiza uno existente."""
        name_lower = name.lower().strip()
        if name_lower in self.domains:
            profile = self.domains[name_lower]
            if terminology:
                for term, defn in terminology.items():
                    profile.add_term(term, defn)
            if rules:
                for rule in rules:
                    profile.add_rule(rule)
            return profile.profile_id

        profile = DomainProfile(
            name=name_lower,
            terminology=terminology or {},
            rules=rules or [],
        )
        self.domains[name_lower] = profile
        self.total_domains += 1

        # Evictar si excede máximo
        if len(self.domains) > self.max_domains:
            self._evict()

        return profile.profile_id

    def detect_level(self, text: str, domain_name: str = None) -> dict:
        """
        Detecta el nivel de expertise del usuario.
        Retorna dict con level, domain, vocabulary_analysis.
        """
        if not self.enabled or not text:
            return {"level": "intermedio", "domain": None}

        self.total_detections += 1

        domain = None
        if domain_name:
            domain = self.domains.get(domain_name.lower().strip())
        else:
            # Auto-detectar dominio por terminología
            domain = self._detect_domain(text)

        level = self.detector.detect_level(text, domain)
        vocab = self.detector.analyze_vocabulary(text)

        if domain:
            domain.record_detection(level)
            domain.last_accessed = time.time()
            domain.access_count += 1

        return {
            "level": level,
            "domain": domain.name if domain else None,
            "vocabulary": vocab,
        }

    def adjust_depth(self, domain_name: str, level: str) -> bool:
        """Ajusta manualmente la profundidad de un dominio."""
        if level not in DomainProfile.VALID_LEVELS:
            return False
        domain = self.domains.get(domain_name.lower().strip())
        if not domain:
            return False
        domain.depth_level = level
        return True

    def get_domain(self, name: str) -> DomainProfile:
        """Obtiene un perfil de dominio."""
        return self.domains.get(name.lower().strip())

    def get_context_for_prompt(self, user_input: str = "",
                               max_chars: int = 500) -> str:
        """Genera contexto de dominio para inyectar en el prompt."""
        if not self.enabled or not self.domains:
            return ""

        # Detectar dominio y nivel del input actual
        domain = self._detect_domain(user_input) if user_input else None
        if not domain:
            return ""

        level = self.detector.detect_level(user_input, domain)
        domain.record_detection(level)

        lines = [domain.get_depth_instructions()]

        # Inyectar reglas del dominio si existen
        if domain.rules:
            lines.append(f"Reglas del dominio ({len(domain.rules)}):")
            for rule in domain.rules[:3]:
                lines.append(f"  - {rule}")

        result = "\n".join(lines)
        return result[:max_chars]

    def _detect_domain(self, text: str) -> DomainProfile:
        """Auto-detecta el dominio basado en terminología del texto."""
        if not text:
            return None
        text_lower = text.lower()
        best_domain = None
        best_score = 0

        for domain in self.domains.values():
            score = 0
            for term in domain.terminology:
                if term in text_lower:
                    score += 1
            # También buscar el nombre del dominio
            if domain.name in text_lower:
                score += 2
            if score > best_score:
                best_score = score
                best_domain = domain

        return best_domain if best_score > 0 else None

    def get_stats(self) -> dict:
        return {
            "total_domains": len(self.domains),
            "total_detections": self.total_detections,
            "domains": [
                {
                    "name": d.name,
                    "level": d.depth_level,
                    "terms": d.term_count,
                    "accesses": d.access_count,
                }
                for d in sorted(self.domains.values(),
                                key=lambda x: x.access_count, reverse=True)[:10]
            ],
        }

    def status(self) -> str:
        return (f"Dominios: {len(self.domains)} | "
                f"Detecciones: {self.total_detections}")

    def generate_report(self) -> str:
        lines = ["=== DOMAIN EXPERT REPORT ==="]
        lines.append(f"Dominios registrados: {len(self.domains)}")
        lines.append(f"Total detecciones: {self.total_detections}")

        if self.domains:
            lines.append(f"\nDominios:")
            for domain in sorted(self.domains.values(),
                                 key=lambda x: x.access_count, reverse=True):
                lines.append(
                    f"  {domain.name}: nivel={domain.depth_level}, "
                    f"términos={domain.term_count}, "
                    f"reglas={len(domain.rules)}, "
                    f"accesos={domain.access_count}"
                )

        # Distribución de niveles
        level_counts = defaultdict(int)
        for domain in self.domains.values():
            level_counts[domain.depth_level] += 1
        if level_counts:
            lines.append(f"\nDistribución de niveles:")
            for level, count in sorted(level_counts.items()):
                lines.append(f"  {level}: {count} dominios")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_detections": self.total_detections,
            "total_domains": self.total_domains,
            "domains": {n: d.to_dict() for n, d in self.domains.items()},
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
            self.total_detections = data.get("total_detections", 0)
            self.total_domains = data.get("total_domains", 0)
            for name, ddata in data.get("domains", {}).items():
                self.domains[name] = DomainProfile.from_dict(ddata)
        except Exception:
            pass

    def clear(self):
        self.domains = {}
        self.total_detections = 0
        self.total_domains = 0

    def _evict(self):
        """Elimina dominios menos usados."""
        if len(self.domains) <= self.max_domains:
            return
        sorted_domains = sorted(
            self.domains.items(),
            key=lambda x: x[1].access_count
        )
        to_remove = len(self.domains) - self.max_domains
        for name, _ in sorted_domains[:to_remove]:
            del self.domains[name]
