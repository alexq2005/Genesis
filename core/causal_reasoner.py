"""
GENESIS — Causal Reasoner (v2.6)

Razonamiento causal: Genesis construye grafos de causa-efecto,
infiere cadenas causales y responde preguntas "por qué" y "qué pasaría si".

Componentes:
- CausalLink: una relación causa → efecto con confianza
- CausalGraph: grafo dirigido de relaciones causales con propagación
- CausalInference: motor de inferencia causal (cadenas, contrafactuales)
- CausalReasoner: coordinador con extracción automática y persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict, deque


class CausalLink:
    """Una relación causa → efecto."""

    def __init__(self, cause: str, effect: str, confidence: float = 0.5,
                 evidence: str = "", domain: str = "general"):
        self.link_id = hashlib.md5(
            f"{cause}→{effect}".encode()
        ).hexdigest()[:10]
        self.cause = cause.lower().strip()
        self.effect = effect.lower().strip()
        self.confidence = max(0.0, min(1.0, confidence))
        self.evidence = evidence[:300]   # Evidencia textual
        self.domain = domain             # Dominio temático
        self.created_at = time.time()
        self.reinforcements = 1          # Veces confirmado
        self.contradictions = 0          # Veces contradicho

    @property
    def strength(self) -> float:
        """Fuerza neta del link (confianza ajustada por refuerzos/contradicciones)."""
        total = self.reinforcements + self.contradictions
        if total == 0:
            return self.confidence
        ratio = self.reinforcements / total
        return self.confidence * ratio

    def reinforce(self, evidence: str = ""):
        """Refuerza este link causal."""
        self.reinforcements += 1
        self.confidence = min(1.0, self.confidence + 0.05)
        if evidence:
            self.evidence = evidence[:300]

    def contradict(self):
        """Registra una contradicción."""
        self.contradictions += 1
        self.confidence = max(0.1, self.confidence - 0.1)

    def to_dict(self) -> dict:
        return {
            "id": self.link_id,
            "cause": self.cause,
            "effect": self.effect,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "domain": self.domain,
            "created_at": self.created_at,
            "reinforcements": self.reinforcements,
            "contradictions": self.contradictions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CausalLink":
        link = cls(
            cause=data.get("cause", ""),
            effect=data.get("effect", ""),
            confidence=data.get("confidence", 0.5),
            evidence=data.get("evidence", ""),
            domain=data.get("domain", "general"),
        )
        link.link_id = data.get("id", link.link_id)
        link.created_at = data.get("created_at", time.time())
        link.reinforcements = data.get("reinforcements", 1)
        link.contradictions = data.get("contradictions", 0)
        return link


class CausalGraph:
    """Grafo dirigido de relaciones causales."""

    def __init__(self):
        self.links = {}         # link_id -> CausalLink
        self.forward = defaultdict(list)   # cause -> [link_ids]
        self.backward = defaultdict(list)  # effect -> [link_ids]

    def add_link(self, link: CausalLink) -> str:
        """Agrega o refuerza un link causal."""
        # Verificar si ya existe
        existing = self._find_existing(link.cause, link.effect)
        if existing:
            existing.reinforce(link.evidence)
            return existing.link_id

        self.links[link.link_id] = link
        self.forward[link.cause].append(link.link_id)
        self.backward[link.effect].append(link.link_id)
        return link.link_id

    def get_causes_of(self, effect: str) -> list:
        """¿Qué causa este efecto?"""
        effect_lower = effect.lower().strip()
        results = []
        for link_id in self.backward.get(effect_lower, []):
            link = self.links.get(link_id)
            if link:
                results.append(link)
        # También buscar por matching parcial
        for eff_key, link_ids in self.backward.items():
            if effect_lower in eff_key or eff_key in effect_lower:
                for lid in link_ids:
                    link = self.links.get(lid)
                    if link and link not in results:
                        results.append(link)
        return sorted(results, key=lambda l: l.strength, reverse=True)

    def get_effects_of(self, cause: str) -> list:
        """¿Qué efectos tiene esta causa?"""
        cause_lower = cause.lower().strip()
        results = []
        for link_id in self.forward.get(cause_lower, []):
            link = self.links.get(link_id)
            if link:
                results.append(link)
        for cause_key, link_ids in self.forward.items():
            if cause_lower in cause_key or cause_key in cause_lower:
                for lid in link_ids:
                    link = self.links.get(lid)
                    if link and link not in results:
                        results.append(link)
        return sorted(results, key=lambda l: l.strength, reverse=True)

    def trace_chain(self, start: str, max_depth: int = 5) -> list:
        """
        Traza una cadena causal desde un concepto.
        Retorna lista de listas: [[link1], [link2, link3], ...]
        por nivel de profundidad (BFS).
        """
        visited = set()
        queue = deque([(start.lower().strip(), 0)])
        chains = []

        while queue:
            concept, depth = queue.popleft()
            if depth >= max_depth or concept in visited:
                continue
            visited.add(concept)

            effects = self.get_effects_of(concept)
            if effects:
                level_links = []
                for link in effects[:3]:  # Max 3 por nivel
                    if link.effect not in visited:
                        level_links.append(link)
                        queue.append((link.effect, depth + 1))
                if level_links:
                    chains.append(level_links)

        return chains

    def trace_reverse(self, end: str, max_depth: int = 5) -> list:
        """Traza cadena causal hacia atrás (¿por qué?)."""
        visited = set()
        queue = deque([(end.lower().strip(), 0)])
        chains = []

        while queue:
            concept, depth = queue.popleft()
            if depth >= max_depth or concept in visited:
                continue
            visited.add(concept)

            causes = self.get_causes_of(concept)
            if causes:
                level_links = []
                for link in causes[:3]:
                    if link.cause not in visited:
                        level_links.append(link)
                        queue.append((link.cause, depth + 1))
                if level_links:
                    chains.append(level_links)

        return chains

    @property
    def node_count(self) -> int:
        """Número de conceptos únicos."""
        nodes = set()
        for link in self.links.values():
            nodes.add(link.cause)
            nodes.add(link.effect)
        return len(nodes)

    @property
    def link_count(self) -> int:
        return len(self.links)

    def strongest_links(self, n: int = 10) -> list:
        """Links más fuertes."""
        return sorted(self.links.values(),
                      key=lambda l: l.strength, reverse=True)[:n]

    def _find_existing(self, cause: str, effect: str) -> CausalLink:
        cause_l = cause.lower().strip()
        effect_l = effect.lower().strip()
        for lid in self.forward.get(cause_l, []):
            link = self.links.get(lid)
            if link and link.effect == effect_l:
                return link
        return None

    def to_dict(self) -> dict:
        return {
            "links": [l.to_dict() for l in self.links.values()],
        }

    def load_dict(self, data: dict):
        self.links = {}
        self.forward = defaultdict(list)
        self.backward = defaultdict(list)
        for ld in data.get("links", []):
            link = CausalLink.from_dict(ld)
            self.links[link.link_id] = link
            self.forward[link.cause].append(link.link_id)
            self.backward[link.effect].append(link.link_id)


class CausalInference:
    """Motor de inferencia causal."""

    # Patrones para extraer relaciones causa-efecto del texto
    CAUSAL_PATTERNS = [
        r"(.+?)\s+(?:causa|provoca|genera|produce|origina)\s+(.+?)(?:\.|$)",
        r"(.+?)\s+(?:porque|ya que|debido a que|dado que)\s+(.+?)(?:\.|$)",
        r"si\s+(.+?)\s*(?:,\s*|\s+)entonces\s+(.+?)(?:\.|$)",
        r"(.+?)\s+(?:lleva a|resulta en|conduce a|implica)\s+(.+?)(?:\.|$)",
        r"(.+?)\s+(?:permite|habilita|facilita)\s+(.+?)(?:\.|$)",
        r"(?:cuando|al)\s+(.+?)\s*(?:,\s*|\s+)(?:se produce|ocurre|pasa|sucede)\s+(.+?)(?:\.|$)",
    ]

    # Keywords que indican preguntas causales
    CAUSAL_QUESTION_PATTERNS = [
        r"(?:por\s*qu[eé]|cual\s+es\s+la\s+causa|qu[eé]\s+causa|qu[eé]\s+provoca)",
        r"(?:qu[eé]\s+pasa(?:r[ií]a)?\s+si|qu[eé]\s+efecto|qu[eé]\s+consecuencia)",
        r"(?:c[oó]mo\s+afecta|c[oó]mo\s+influye|qu[eé]\s+impacto)",
    ]

    def extract_causal_pairs(self, text: str) -> list:
        """Extrae pares causa-efecto del texto."""
        pairs = []
        text_clean = text.lower().strip()

        for pattern in self.CAUSAL_PATTERNS:
            matches = re.finditer(pattern, text_clean, re.IGNORECASE)
            for match in matches:
                cause = match.group(1).strip()[:100]
                effect = match.group(2).strip()[:100]

                if len(cause) > 3 and len(effect) > 3:
                    # Para patrones "porque", invertir: efecto porque causa
                    if "porque" in pattern or "debido" in pattern or "dado que" in pattern:
                        cause, effect = effect, cause

                    pairs.append((cause, effect))

        return pairs[:5]  # Max 5 por texto

    def is_causal_question(self, text: str) -> bool:
        """Detecta si el texto es una pregunta causal."""
        text_lower = text.lower()
        for pattern in self.CAUSAL_QUESTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    def build_explanation(self, chains: list, question: str = "") -> str:
        """Construye una explicación textual desde cadenas causales."""
        if not chains:
            return ""

        lines = []
        if question:
            lines.append(f"[RAZONAMIENTO CAUSAL sobre: {question[:60]}]")

        for depth, level_links in enumerate(chains):
            prefix = "  " * depth + "→ " if depth > 0 else "• "
            for link in level_links:
                conf_str = f"({link.strength:.0%})"
                lines.append(f"{prefix}{link.cause} → {link.effect} {conf_str}")

        return "\n".join(lines)


class CausalReasoner:
    """
    Coordinador de razonamiento causal.
    Construye y consulta el grafo causal, extrae relaciones
    de conversaciones, y genera explicaciones causales.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/causal")
        self.data_file = self.base_dir / "causal_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.graph = CausalGraph()
        self.inference = CausalInference()
        self.max_links = 500
        self.total_extracted = 0
        self.total_queries = 0
        self.enabled = True

        self._load()

    def extract_and_store(self, text: str, domain: str = "general") -> int:
        """Extrae relaciones causales del texto y las almacena."""
        if not self.enabled or not text:
            return 0

        pairs = self.inference.extract_causal_pairs(text)
        stored = 0
        for cause, effect in pairs:
            link = CausalLink(
                cause=cause, effect=effect,
                confidence=0.5, evidence=text[:200],
                domain=domain,
            )
            self.graph.add_link(link)
            stored += 1

        self.total_extracted += stored

        # Trim si excede máximo
        if self.graph.link_count > self.max_links:
            self._evict()

        return stored

    def why(self, effect: str, max_depth: int = 4) -> str:
        """Responde '¿por qué X?' trazando causas hacia atrás."""
        self.total_queries += 1
        chains = self.graph.trace_reverse(effect, max_depth=max_depth)
        return self.inference.build_explanation(chains, question=f"¿Por qué {effect}?")

    def what_if(self, cause: str, max_depth: int = 4) -> str:
        """Responde '¿qué pasa si X?' trazando efectos hacia adelante."""
        self.total_queries += 1
        chains = self.graph.trace_chain(cause, max_depth=max_depth)
        return self.inference.build_explanation(chains, question=f"¿Qué pasa si {cause}?")

    def get_context_for_prompt(self, user_input: str, max_chars: int = 500) -> str:
        """Genera contexto causal relevante para el prompt."""
        if not self.enabled or self.graph.link_count == 0:
            return ""

        if not self.inference.is_causal_question(user_input):
            return ""

        # Intentar responder con el grafo causal
        input_lower = user_input.lower()
        explanation = ""

        if "por qu" in input_lower or "causa" in input_lower:
            # Extraer el objeto de la pregunta
            subject = self._extract_subject(user_input)
            if subject:
                explanation = self.why(subject)
        elif "qu" in input_lower and ("pasa" in input_lower or "efecto" in input_lower):
            subject = self._extract_subject(user_input)
            if subject:
                explanation = self.what_if(subject)

        if explanation:
            return explanation[:max_chars]
        return ""

    def add_manual_link(self, cause: str, effect: str,
                        confidence: float = 0.7, domain: str = "general") -> str:
        """Agrega un link causal manualmente."""
        link = CausalLink(cause=cause, effect=effect,
                          confidence=confidence, domain=domain)
        return self.graph.add_link(link)

    def get_stats(self) -> dict:
        return {
            "total_links": self.graph.link_count,
            "total_nodes": self.graph.node_count,
            "total_extracted": self.total_extracted,
            "total_queries": self.total_queries,
            "strongest": [
                {"cause": l.cause, "effect": l.effect, "strength": round(l.strength, 2)}
                for l in self.graph.strongest_links(3)
            ],
        }

    def status(self) -> str:
        return (f"Links: {self.graph.link_count} | "
                f"Nodos: {self.graph.node_count} | "
                f"Extraidos: {self.total_extracted} | "
                f"Queries: {self.total_queries}")

    def generate_report(self) -> str:
        lines = ["=== CAUSAL REASONER REPORT ==="]
        lines.append(f"Links causales: {self.graph.link_count}")
        lines.append(f"Nodos (conceptos): {self.graph.node_count}")
        lines.append(f"Total extraidos: {self.total_extracted}")
        lines.append(f"Total queries: {self.total_queries}")

        strongest = self.graph.strongest_links(10)
        if strongest:
            lines.append(f"\nLinks más fuertes:")
            for link in strongest:
                lines.append(
                    f"  {link.cause} → {link.effect} "
                    f"(fuerza={link.strength:.0%}, refuerzos={link.reinforcements})"
                )

        # Dominios
        domains = defaultdict(int)
        for link in self.graph.links.values():
            domains[link.domain] += 1
        if domains:
            lines.append(f"\nPor dominio:")
            for dom, count in sorted(domains.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {dom}: {count} links")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_extracted": self.total_extracted,
            "total_queries": self.total_queries,
            "graph": self.graph.to_dict(),
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
            self.total_extracted = data.get("total_extracted", 0)
            self.total_queries = data.get("total_queries", 0)
            self.graph.load_dict(data.get("graph", {}))
        except Exception:
            pass

    def clear(self):
        self.graph = CausalGraph()
        self.total_extracted = 0
        self.total_queries = 0

    def _extract_subject(self, text: str) -> str:
        """Extrae el sujeto de una pregunta causal."""
        text_clean = re.sub(r'[¿?¡!]', '', text.lower()).strip()
        # Remover prefijos de pregunta
        for prefix in ["por que ", "por qué ", "que causa ", "que provoca ",
                        "que pasa si ", "que pasaria si ", "que efecto tiene ",
                        "como afecta "]:
            if text_clean.startswith(prefix):
                return text_clean[len(prefix):].strip()
        # Fallback: últimas palabras significativas
        words = [w for w in text_clean.split() if len(w) > 3]
        return " ".join(words[-4:]) if words else ""

    def _evict(self):
        """Elimina links más débiles."""
        if self.graph.link_count <= self.max_links:
            return
        sorted_links = sorted(self.graph.links.values(),
                              key=lambda l: l.strength)
        to_remove = self.graph.link_count - self.max_links
        for link in sorted_links[:to_remove]:
            del self.graph.links[link.link_id]
            if link.link_id in self.graph.forward.get(link.cause, []):
                self.graph.forward[link.cause].remove(link.link_id)
            if link.link_id in self.graph.backward.get(link.effect, []):
                self.graph.backward[link.effect].remove(link.link_id)
