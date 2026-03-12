"""
GENESIS — Concept Synthesizer (v2.6)

Síntesis de conceptos: combina ideas de dominios diferentes
para generar insights novedosos mediante transferencia analógica.

Componentes:
- Concept: un concepto con propiedades, relaciones y dominio
- AnalogyFinder: encuentra analogías entre conceptos de dominios distintos
- SynthesisEngine: genera síntesis creativas combinando conceptos
- ConceptSynthesizer: coordinador con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class Concept:
    """Un concepto con propiedades y relaciones."""

    def __init__(self, name: str, domain: str = "general",
                 properties: list = None, relations: list = None):
        self.concept_id = hashlib.md5(
            f"concept_{name}_{domain}".encode()
        ).hexdigest()[:10]
        self.name = name.lower().strip()
        self.domain = domain.lower().strip()
        self.properties = properties or []    # ["rápido", "distribuido", ...]
        self.relations = relations or []      # [("es_tipo", "algoritmo"), ...]
        self.created_at = time.time()
        self.usage_count = 0
        self.synthesis_count = 0              # Veces usado en síntesis

    def similarity(self, other: "Concept") -> float:
        """Similitud basada en propiedades compartidas."""
        if not self.properties or not other.properties:
            return 0.0
        set_a = set(p.lower() for p in self.properties)
        set_b = set(p.lower() for p in other.properties)
        intersection = set_a & set_b
        min_size = min(len(set_a), len(set_b))
        return len(intersection) / min_size if min_size else 0.0

    def is_cross_domain(self, other: "Concept") -> bool:
        """¿Son de dominios diferentes?"""
        return self.domain != other.domain

    def to_dict(self) -> dict:
        return {
            "id": self.concept_id,
            "name": self.name,
            "domain": self.domain,
            "properties": self.properties[:20],
            "relations": self.relations[:20],
            "created_at": self.created_at,
            "usage_count": self.usage_count,
            "synthesis_count": self.synthesis_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Concept":
        c = cls(
            name=data.get("name", ""),
            domain=data.get("domain", "general"),
            properties=data.get("properties", []),
            relations=data.get("relations", []),
        )
        c.concept_id = data.get("id", c.concept_id)
        c.created_at = data.get("created_at", time.time())
        c.usage_count = data.get("usage_count", 0)
        c.synthesis_count = data.get("synthesis_count", 0)
        return c


class Synthesis:
    """Resultado de una síntesis creativa."""

    def __init__(self, synthesis_id: str = None):
        self.synthesis_id = synthesis_id or hashlib.md5(
            f"syn_{time.time()}".encode()
        ).hexdigest()[:10]
        self.source_concepts = []     # Conceptos fuente (nombres)
        self.source_domains = []      # Dominios fuente
        self.insight = ""             # El insight generado
        self.analogy = ""             # La analogía encontrada
        self.novelty_score = 0.0      # Qué tan novedoso (0-1)
        self.created_at = time.time()
        self.useful = None            # None=sin evaluar, True/False

    def to_text(self) -> str:
        """Representación textual."""
        parts = [f"[Síntesis: {' × '.join(self.source_concepts[:3])}]"]
        if self.analogy:
            parts.append(f"  Analogía: {self.analogy[:150]}")
        if self.insight:
            parts.append(f"  Insight: {self.insight[:150]}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "id": self.synthesis_id,
            "source_concepts": self.source_concepts,
            "source_domains": self.source_domains,
            "insight": self.insight[:500],
            "analogy": self.analogy[:500],
            "novelty_score": round(self.novelty_score, 3),
            "created_at": self.created_at,
            "useful": self.useful,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Synthesis":
        s = cls(synthesis_id=data.get("id"))
        s.source_concepts = data.get("source_concepts", [])
        s.source_domains = data.get("source_domains", [])
        s.insight = data.get("insight", "")
        s.analogy = data.get("analogy", "")
        s.novelty_score = data.get("novelty_score", 0.0)
        s.created_at = data.get("created_at", time.time())
        s.useful = data.get("useful")
        return s


class AnalogyFinder:
    """Encuentra analogías entre conceptos de dominios distintos."""

    # Templates de analogía por relación
    ANALOGY_TEMPLATES = {
        "structural": "{a} es a {domain_a} como {b} es a {domain_b}",
        "functional": "{a} cumple en {domain_a} la misma función que {b} en {domain_b}",
        "property": "{a} y {b} comparten {shared}: pueden combinarse",
        "transfer": "La técnica de {a} ({domain_a}) podría aplicarse a {b} ({domain_b})",
    }

    def find_analogies(self, concepts: list, min_similarity: float = 0.2) -> list:
        """Encuentra pares analógicos entre conceptos cross-domain."""
        analogies = []

        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                # Solo cross-domain
                if not c1.is_cross_domain(c2):
                    continue

                sim = c1.similarity(c2)
                if sim >= min_similarity:
                    shared = set(p.lower() for p in c1.properties) & \
                             set(p.lower() for p in c2.properties)

                    analogy_type = "property" if shared else "structural"

                    analogy_text = self.ANALOGY_TEMPLATES[analogy_type].format(
                        a=c1.name, b=c2.name,
                        domain_a=c1.domain, domain_b=c2.domain,
                        shared=", ".join(list(shared)[:3]) if shared else "características",
                    )

                    analogies.append({
                        "concept_a": c1,
                        "concept_b": c2,
                        "similarity": sim,
                        "shared_properties": list(shared),
                        "analogy_type": analogy_type,
                        "analogy_text": analogy_text,
                    })

        # Ordenar por similitud (las más interesantes son medias, no las más altas)
        analogies.sort(key=lambda a: abs(a["similarity"] - 0.5))
        return analogies[:10]

    def find_transfer_opportunities(self, source: Concept, targets: list) -> list:
        """Encuentra oportunidades de transferencia desde un concepto fuente."""
        opportunities = []

        for target in targets:
            if not source.is_cross_domain(target):
                continue

            # Propiedades que source tiene y target no
            source_props = set(p.lower() for p in source.properties)
            target_props = set(p.lower() for p in target.properties)
            transferable = source_props - target_props

            if transferable and source_props & target_props:
                text = self.ANALOGY_TEMPLATES["transfer"].format(
                    a=source.name, b=target.name,
                    domain_a=source.domain, domain_b=target.domain,
                )
                opportunities.append({
                    "target": target,
                    "transferable": list(transferable)[:5],
                    "common_ground": list(source_props & target_props)[:3],
                    "text": text,
                })

        return opportunities[:5]


class SynthesisEngine:
    """Motor de síntesis creativa."""

    # Templates para generar insights
    INSIGHT_TEMPLATES = [
        "Combinar {prop} de {a} ({domain_a}) con {b} ({domain_b}) podría crear un enfoque híbrido",
        "Si {a} usa {prop} exitosamente en {domain_a}, {b} podría beneficiarse de lo mismo en {domain_b}",
        "La intersección entre {a} y {b} sugiere un nuevo patrón: {prop} aplicado cross-domain",
        "{a} y {b} comparten {prop} — esto indica un principio fundamental transferible entre {domain_a} y {domain_b}",
    ]

    def synthesize(self, concept_a: Concept, concept_b: Concept,
                   shared_properties: list = None) -> Synthesis:
        """Genera una síntesis creativa entre dos conceptos."""
        syn = Synthesis()
        syn.source_concepts = [concept_a.name, concept_b.name]
        syn.source_domains = [concept_a.domain, concept_b.domain]

        # Determinar propiedades compartidas
        if shared_properties is None:
            set_a = set(p.lower() for p in concept_a.properties)
            set_b = set(p.lower() for p in concept_b.properties)
            shared_properties = list(set_a & set_b)

        prop_str = ", ".join(shared_properties[:3]) if shared_properties else "patrones similares"

        # Generar analogía
        if shared_properties:
            syn.analogy = (f"{concept_a.name} es análogo a {concept_b.name}: "
                           f"ambos usan {prop_str}")
        else:
            syn.analogy = (f"{concept_a.name} ({concept_a.domain}) y "
                           f"{concept_b.name} ({concept_b.domain}) tienen "
                           f"estructuras comparables")

        # Generar insight
        template = self.INSIGHT_TEMPLATES[
            hash(concept_a.name + concept_b.name) % len(self.INSIGHT_TEMPLATES)
        ]
        syn.insight = template.format(
            a=concept_a.name, b=concept_b.name,
            domain_a=concept_a.domain, domain_b=concept_b.domain,
            prop=prop_str,
        )

        # Calcular novelty score
        syn.novelty_score = self._calculate_novelty(concept_a, concept_b, shared_properties)

        # Incrementar contadores
        concept_a.synthesis_count += 1
        concept_b.synthesis_count += 1

        return syn

    def _calculate_novelty(self, a: Concept, b: Concept,
                           shared: list) -> float:
        """
        Calcula qué tan novedosa es la síntesis.
        Más novedosa si: dominios muy distintos, similaridad media,
        pocos usos previos en síntesis.
        """
        # Factor de distancia de dominio (dominios distintos = más novedoso)
        domain_factor = 1.0 if a.domain != b.domain else 0.3

        # Factor de similitud (media = más interesante)
        sim = a.similarity(b)
        sim_factor = 1.0 - abs(sim - 0.4)  # Óptimo alrededor de 0.4

        # Factor de frescura (menos usos = más novedoso)
        usage = (a.synthesis_count + b.synthesis_count) / 2
        freshness = max(0.2, 1.0 - usage * 0.1)

        novelty = (domain_factor * 0.4 + sim_factor * 0.4 + freshness * 0.2)
        return min(1.0, max(0.0, novelty))


class ConceptSynthesizer:
    """
    Coordinador de síntesis de conceptos.
    Extrae conceptos, encuentra analogías y genera síntesis creativas.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/concept_synth")
        self.data_file = self.base_dir / "synth_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.concepts = {}       # concept_id -> Concept
        self.syntheses = []      # Lista de Synthesis
        self.analogy_finder = AnalogyFinder()
        self.synth_engine = SynthesisEngine()
        self.max_concepts = 200
        self.max_syntheses = 100
        self.total_concepts = 0
        self.total_syntheses = 0
        self.enabled = True

        self._load()

    # Domain keywords para detección automática
    DOMAIN_KEYWORDS = {
        "programacion": ["codigo", "funcion", "variable", "algoritmo", "compilar",
                         "python", "javascript", "clase", "metodo", "loop"],
        "redes": ["servidor", "protocolo", "red", "paquete", "tcp", "http",
                  "dns", "firewall", "router", "proxy"],
        "ia_ml": ["modelo", "neural", "training", "embeddings", "transformer",
                  "inferencia", "loss", "epoch", "dataset", "features"],
        "matematicas": ["ecuacion", "funcion", "derivada", "integral", "probabilidad",
                        "estadistica", "variable", "matriz", "vector", "grafo"],
        "biologia": ["celula", "gen", "proteina", "evolucion", "mutacion",
                      "organismo", "ecosistema", "metabolismo", "adn", "enzima"],
        "fisica": ["energia", "fuerza", "masa", "velocidad", "onda",
                   "particula", "campo", "cuantico", "termodinamica", "entropia"],
    }

    PROPERTY_KEYWORDS = {
        "rapido": ["rapido", "veloz", "eficiente", "optimizado", "performante"],
        "distribuido": ["distribuido", "paralelo", "concurrente", "cluster", "nodos"],
        "jerarquico": ["jerarquico", "arbol", "niveles", "capas", "herencia"],
        "adaptativo": ["adaptativo", "aprendizaje", "evolucion", "auto", "dinamico"],
        "recursivo": ["recursivo", "recursion", "fractal", "auto-referencia", "iterativo"],
        "robusto": ["robusto", "tolerante", "resiliente", "redundante", "backup"],
        "escalable": ["escalable", "escalar", "crecimiento", "expandible"],
        "modular": ["modular", "componente", "plugin", "extensible", "desacoplado"],
    }

    def extract_concept(self, text: str, name: str = "") -> Concept:
        """Extrae un concepto del texto."""
        if not self.enabled or not text:
            return None

        text_lower = text.lower()

        # Detectar dominio
        domain = self._detect_domain(text_lower)

        # Detectar propiedades
        properties = self._detect_properties(text_lower)

        if not name:
            # Intentar extraer nombre del texto (primer sustantivo significativo)
            words = [w for w in re.findall(r'\b\w+\b', text_lower)
                     if len(w) > 4 and w not in ("sobre", "tiene", "puede", "cuando")]
            name = words[0] if words else "concepto"

        # Verificar si ya existe
        for existing in self.concepts.values():
            if existing.name == name.lower() and existing.domain == domain:
                existing.usage_count += 1
                # Agregar nuevas propiedades
                for prop in properties:
                    if prop not in existing.properties:
                        existing.properties.append(prop)
                return existing

        concept = Concept(name=name, domain=domain, properties=properties)
        self.concepts[concept.concept_id] = concept
        self.total_concepts += 1

        # Evicción
        if len(self.concepts) > self.max_concepts:
            self._evict_concepts()

        return concept

    def synthesize_pair(self, name_a: str, name_b: str) -> Synthesis:
        """Sintetiza dos conceptos por nombre."""
        a = self._find_concept(name_a)
        b = self._find_concept(name_b)

        if not a or not b:
            return None

        syn = self.synth_engine.synthesize(a, b)
        self.syntheses.append(syn)
        self.total_syntheses += 1

        if len(self.syntheses) > self.max_syntheses:
            self.syntheses = self.syntheses[-self.max_syntheses:]

        return syn

    def find_analogies(self, min_similarity: float = 0.2) -> list:
        """Encuentra analogías cross-domain en los conceptos almacenados."""
        concepts = list(self.concepts.values())
        return self.analogy_finder.find_analogies(concepts, min_similarity)

    def auto_synthesize(self) -> list:
        """Genera síntesis automáticas desde las mejores analogías."""
        analogies = self.find_analogies()
        results = []

        for analogy in analogies[:3]:
            syn = self.synth_engine.synthesize(
                analogy["concept_a"],
                analogy["concept_b"],
                analogy["shared_properties"],
            )
            self.syntheses.append(syn)
            self.total_syntheses += 1
            results.append(syn)

        return results

    def get_context_for_prompt(self, user_input: str, max_chars: int = 400) -> str:
        """Genera contexto de síntesis para inyectar en prompt."""
        if not self.enabled or not self.syntheses:
            return ""

        # Buscar síntesis relevantes por keywords del input
        input_words = set(w.lower() for w in user_input.split() if len(w) > 3)
        relevant = []

        for syn in reversed(self.syntheses[-20:]):
            syn_words = set(
                w.lower() for w in
                " ".join(syn.source_concepts + [syn.insight]).split()
                if len(w) > 3
            )
            overlap = len(input_words & syn_words)
            if overlap >= 2:
                relevant.append((overlap, syn))

        if not relevant:
            return ""

        relevant.sort(key=lambda x: x[0], reverse=True)

        lines = ["[SÍNTESIS DE CONCEPTOS RELEVANTES]"]
        total = 0
        for _, syn in relevant[:2]:
            text = syn.to_text()
            if total + len(text) > max_chars:
                break
            lines.append(text)
            total += len(text)

        return "\n".join(lines) if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        domains = defaultdict(int)
        for c in self.concepts.values():
            domains[c.domain] += 1

        return {
            "total_concepts": self.total_concepts,
            "stored_concepts": len(self.concepts),
            "total_syntheses": self.total_syntheses,
            "stored_syntheses": len(self.syntheses),
            "domains": dict(domains),
            "latest_synthesis": self.syntheses[-1].to_text()[:100] if self.syntheses else "",
        }

    def status(self) -> str:
        domains = len(set(c.domain for c in self.concepts.values()))
        return (f"Conceptos: {len(self.concepts)} ({domains} dominios) | "
                f"Síntesis: {len(self.syntheses)} | "
                f"Total: {self.total_syntheses}")

    def generate_report(self) -> str:
        lines = ["=== CONCEPT SYNTHESIZER REPORT ==="]
        lines.append(f"Conceptos almacenados: {len(self.concepts)}")
        lines.append(f"Total conceptos extraidos: {self.total_concepts}")
        lines.append(f"Síntesis generadas: {self.total_syntheses}")
        lines.append(f"Síntesis almacenadas: {len(self.syntheses)}")

        # Por dominio
        domains = defaultdict(list)
        for c in self.concepts.values():
            domains[c.domain].append(c.name)
        if domains:
            lines.append(f"\nConceptos por dominio:")
            for dom, names in sorted(domains.items()):
                sample = ", ".join(names[:5])
                lines.append(f"  {dom} ({len(names)}): {sample}")

        # Últimas síntesis
        if self.syntheses:
            lines.append(f"\nÚltimas síntesis:")
            for syn in self.syntheses[-5:]:
                lines.append(f"  [{' × '.join(syn.source_concepts[:2])}]")
                lines.append(f"    {syn.insight[:120]}")

        # Analogías posibles
        analogies = self.find_analogies()
        if analogies:
            lines.append(f"\nAnalogías detectadas ({len(analogies)}):")
            for a in analogies[:3]:
                lines.append(f"  {a['analogy_text']}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_concepts": self.total_concepts,
            "total_syntheses": self.total_syntheses,
            "concepts": [c.to_dict() for c in self.concepts.values()],
            "syntheses": [s.to_dict() for s in self.syntheses[-self.max_syntheses:]],
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
            self.total_concepts = data.get("total_concepts", 0)
            self.total_syntheses = data.get("total_syntheses", 0)
            for cd in data.get("concepts", []):
                c = Concept.from_dict(cd)
                self.concepts[c.concept_id] = c
            self.syntheses = [Synthesis.from_dict(sd) for sd in data.get("syntheses", [])]
        except Exception:
            pass

    def clear(self):
        self.concepts = {}
        self.syntheses = []
        self.total_concepts = 0
        self.total_syntheses = 0

    def _find_concept(self, name: str) -> Concept:
        name_lower = name.lower().strip()
        for c in self.concepts.values():
            if c.name == name_lower:
                return c
        # Búsqueda parcial
        for c in self.concepts.values():
            if name_lower in c.name or c.name in name_lower:
                return c
        return None

    def _detect_domain(self, text: str) -> str:
        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text)
            if count >= 2:
                scores[domain] = count
        return max(scores, key=scores.get) if scores else "general"

    def _detect_properties(self, text: str) -> list:
        props = []
        for prop, keywords in self.PROPERTY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                props.append(prop)
        return props

    def _evict_concepts(self):
        if len(self.concepts) <= self.max_concepts:
            return
        sorted_concepts = sorted(
            self.concepts.values(),
            key=lambda c: c.usage_count + c.synthesis_count * 2,
        )
        to_remove = len(self.concepts) - self.max_concepts
        for c in sorted_concepts[:to_remove]:
            del self.concepts[c.concept_id]
