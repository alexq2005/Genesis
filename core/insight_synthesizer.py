"""
GENESIS — Insight Synthesizer (v3.5)

Generación de descubrimientos: sintetiza insights a partir de
observaciones, detecta novedad contra insights existentes, y
encuentra conexiones cross-domain entre descubrimientos.

Componentes:
- Insight: un descubrimiento con contenido, dominio, evidencia y scores
- NoveltyDetector: verifica novedad comparando overlap con insights existentes
- EvidenceChain: cadena de evidencia con cálculo de fortaleza asintótica
- InsightSynthesizer: coordinador con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class Insight:
    """Un descubrimiento con contenido, dominio, evidencia y scores."""

    VALID_SOURCE_TYPES = {"observation", "pattern", "connection"}

    def __init__(self, content: str, domain: str = "general",
                 evidence: list = None, confidence: float = 0.5,
                 novelty: float = 0.5, source_type: str = "observation"):
        self.insight_id = hashlib.md5(
            f"insight_{content[:50]}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.content = content.strip()
        self.domain = domain.lower().strip()
        self.evidence = evidence or []           # List of evidence strings
        self.confidence = max(0.0, min(1.0, confidence))
        self.novelty = max(0.0, min(1.0, novelty))
        self.source_type = source_type if source_type in self.VALID_SOURCE_TYPES else "observation"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.usage_count = 0
        self.connections = []         # IDs de insights conectados

    @property
    def strength(self) -> float:
        """Score compuesto: confidence * novelty."""
        return self.confidence * self.novelty

    @property
    def evidence_strength(self) -> float:
        """Fortaleza asintótica basada en cantidad de evidencia."""
        n = len(self.evidence)
        return n / (n + 2) if n > 0 else 0.0

    def add_evidence(self, evidence_text: str):
        """Agrega evidencia y recalcula confianza."""
        if evidence_text and evidence_text not in self.evidence:
            self.evidence.append(evidence_text)
            # Ajustar confianza basado en evidencia acumulada
            self.confidence = min(1.0, self.confidence + 0.05 * self.evidence_strength)
            self.updated_at = time.time()

    def content_words(self) -> set:
        """Retorna set de palabras significativas del contenido."""
        words = re.findall(r'\b\w+\b', self.content.lower())
        stopwords = {"el", "la", "los", "las", "de", "en", "un", "una",
                      "que", "es", "se", "con", "por", "para", "del",
                      "the", "a", "an", "in", "of", "to", "and", "is",
                      "it", "on", "for", "with", "as", "at", "by"}
        return {w for w in words if len(w) > 2 and w not in stopwords}

    def to_dict(self) -> dict:
        return {
            "insight_id": self.insight_id,
            "content": self.content[:2000],
            "domain": self.domain,
            "evidence": self.evidence[:50],
            "confidence": round(self.confidence, 4),
            "novelty": round(self.novelty, 4),
            "source_type": self.source_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
            "connections": self.connections[:20],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Insight":
        i = cls(
            content=data.get("content", ""),
            domain=data.get("domain", "general"),
            evidence=data.get("evidence", []),
            confidence=data.get("confidence", 0.5),
            novelty=data.get("novelty", 0.5),
            source_type=data.get("source_type", "observation"),
        )
        i.insight_id = data.get("insight_id", i.insight_id)
        i.created_at = data.get("created_at", time.time())
        i.updated_at = data.get("updated_at", time.time())
        i.usage_count = data.get("usage_count", 0)
        i.connections = data.get("connections", [])
        return i


class NoveltyDetector:
    """Verifica novedad comparando overlap con insights existentes."""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold     # Containment similarity threshold

    def is_novel(self, new_content: str, existing_insights: list) -> tuple:
        """
        Verifica si el contenido es novel comparando con insights existentes.
        Retorna (is_novel: bool, novelty_score: float, most_similar_id: str).
        """
        if not existing_insights:
            return True, 1.0, ""

        new_words = self._get_words(new_content)
        if not new_words:
            return True, 1.0, ""

        max_similarity = 0.0
        most_similar_id = ""

        for insight in existing_insights:
            existing_words = insight.content_words()
            if not existing_words:
                continue

            # Containment similarity: qué fracción de new_words está en existing
            overlap = len(new_words & existing_words)
            containment = overlap / len(new_words)

            if containment > max_similarity:
                max_similarity = containment
                most_similar_id = insight.insight_id

        novelty_score = 1.0 - max_similarity
        is_novel = max_similarity < self.threshold
        return is_novel, round(novelty_score, 4), most_similar_id

    def compute_pairwise_novelty(self, insights: list) -> dict:
        """Calcula novelty entre pares de insights."""
        results = {}
        for i, a in enumerate(insights):
            for b in insights[i + 1:]:
                a_words = a.content_words()
                b_words = b.content_words()
                if not a_words or not b_words:
                    continue
                overlap = len(a_words & b_words)
                union = len(a_words | b_words)
                jaccard = overlap / union if union > 0 else 0.0
                key = f"{a.insight_id}:{b.insight_id}"
                results[key] = round(1.0 - jaccard, 4)
        return results

    def _get_words(self, text: str) -> set:
        """Extrae palabras significativas del texto."""
        words = re.findall(r'\b\w+\b', text.lower())
        stopwords = {"el", "la", "los", "las", "de", "en", "un", "una",
                      "que", "es", "se", "con", "por", "para", "del",
                      "the", "a", "an", "in", "of", "to", "and", "is",
                      "it", "on", "for", "with", "as", "at", "by"}
        return {w for w in words if len(w) > 2 and w not in stopwords}


class EvidenceChain:
    """Cadena de evidencia con cálculo de fortaleza asintótica."""

    def __init__(self, evidence: list = None):
        self.evidence = evidence or []     # List of evidence strings

    def add(self, evidence_text: str):
        """Agrega evidencia a la cadena."""
        if evidence_text and evidence_text not in self.evidence:
            self.evidence.append(evidence_text)

    @property
    def overall_strength(self) -> float:
        """
        Fortaleza asintótica: n / (n + 2).
        0 evidencias = 0.0, 2 = 0.5, 4 = 0.67, 10 = 0.83, etc.
        """
        n = len(self.evidence)
        return n / (n + 2) if n > 0 else 0.0

    @property
    def length(self) -> int:
        return len(self.evidence)

    def strongest_evidence(self, n: int = 3) -> list:
        """Retorna las N piezas de evidencia más largas (más detalladas)."""
        sorted_ev = sorted(self.evidence, key=len, reverse=True)
        return sorted_ev[:n]

    def to_dict(self) -> dict:
        return {
            "evidence": self.evidence[:50],
            "strength": round(self.overall_strength, 4),
            "count": self.length,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvidenceChain":
        return cls(evidence=data.get("evidence", []))


class InsightSynthesizer:
    """
    Coordinador de generación de descubrimientos.
    Sintetiza insights desde observaciones, verifica novedad,
    y encuentra conexiones cross-domain.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/insights")
        self.data_file = self.base_dir / "insight_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.insights = {}           # insight_id -> Insight
        self.novelty_detector = NoveltyDetector(threshold=0.5)
        self.max_insights = 200
        self.total_insights = 0
        self.total_novel = 0
        self.enabled = True

        self._load()

    # Patrones para detectar observaciones relevantes
    OBSERVATION_PATTERNS = [
        (r"(?:noté|observé|vi|encontré|descubrí)\s+(?:que\s+)?(.{15,200})", "observation_es"),
        (r"(?:noticed|observed|found|discovered|saw)\s+(?:that\s+)?(.{15,200})", "observation_en"),
        (r"(?:parece que|it seems|apparently|al parecer)\s+(.{15,200})", "apparent"),
        (r"(?:interesante|interesting|curioso|curious)[\s:]+(.{15,200})", "notable"),
    ]

    # Keywords por dominio
    DOMAIN_KEYWORDS = {
        "tecnología": ["software", "hardware", "código", "programa", "sistema", "api",
                        "servidor", "database", "algoritmo", "framework"],
        "ciencia": ["hipótesis", "experimento", "resultado", "muestra", "variable",
                     "datos", "análisis", "método", "evidencia", "conclusión"],
        "negocio": ["mercado", "cliente", "producto", "venta", "estrategia",
                     "competencia", "precio", "demanda", "negocio", "inversión"],
        "creatividad": ["idea", "diseño", "concepto", "innovación", "creativo",
                         "original", "arte", "inspiración", "imaginación", "patrón"],
        "social": ["persona", "grupo", "comunidad", "relación", "comunicación",
                    "cultura", "sociedad", "comportamiento", "interacción", "opinión"],
    }

    def synthesize(self, observations: list, domain: str = "") -> list:
        """
        Toma una lista de observaciones, encuentra patrones y genera insights.
        """
        if not self.enabled or not observations:
            return []

        created = []

        # Detectar dominio si no se proporciona
        if not domain:
            combined_text = " ".join(observations)
            domain = self._detect_domain(combined_text)

        # 1. Insights por observaciones individuales relevantes
        for obs in observations:
            if len(obs) > 20:
                insight = self.add_insight(
                    content=obs,
                    domain=domain,
                    evidence=[obs],
                    source_type="observation",
                )
                if insight:
                    created.append(insight)

        # 2. Buscar patrones entre observaciones
        if len(observations) >= 2:
            patterns = self._find_patterns(observations)
            for pattern in patterns:
                insight = self.add_insight(
                    content=pattern["description"],
                    domain=domain,
                    evidence=pattern["evidence"],
                    source_type="pattern",
                )
                if insight:
                    created.append(insight)

        # 3. Buscar conexiones con insights existentes
        connections = self._find_connections_with_existing(observations, domain)
        for conn in connections:
            insight = self.add_insight(
                content=conn["content"],
                domain=domain,
                evidence=conn["evidence"],
                source_type="connection",
            )
            if insight:
                created.append(insight)

        return created

    def add_insight(self, content: str, domain: str = "general",
                    evidence: list = None, source_type: str = "observation") -> Insight:
        """Agrega un insight con verificación de novedad."""
        if not self.enabled or not content or len(content) < 10:
            return None

        existing_list = list(self.insights.values())

        # Verificar novedad
        is_novel, novelty_score, similar_id = self.novelty_detector.is_novel(
            content, existing_list
        )

        if not is_novel and similar_id:
            # Actualizar insight existente con nueva evidencia
            existing = self.insights.get(similar_id)
            if existing and evidence:
                for ev in evidence:
                    existing.add_evidence(ev)
            return None

        # Crear nuevo insight
        chain = EvidenceChain(evidence=evidence or [])
        confidence = max(0.3, chain.overall_strength)

        insight = Insight(
            content=content,
            domain=domain,
            evidence=evidence or [],
            confidence=confidence,
            novelty=novelty_score,
            source_type=source_type,
        )

        self.insights[insight.insight_id] = insight
        self.total_insights += 1
        self.total_novel += 1

        # Evicción
        if len(self.insights) > self.max_insights:
            self._evict()

        return insight

    def get_strongest(self, n: int = 5) -> list:
        """Retorna los top N insights por confidence * novelty."""
        sorted_insights = sorted(
            self.insights.values(),
            key=lambda i: i.strength,
            reverse=True,
        )
        return sorted_insights[:n]

    def cross_domain_insights(self) -> list:
        """Encuentra conexiones entre insights de dominios diferentes."""
        insights_list = list(self.insights.values())
        cross_domain = []

        domains = defaultdict(list)
        for ins in insights_list:
            domains[ins.domain].append(ins)

        domain_names = list(domains.keys())
        if len(domain_names) < 2:
            return []

        for i, domain_a in enumerate(domain_names):
            for domain_b in domain_names[i + 1:]:
                for ins_a in domains[domain_a]:
                    for ins_b in domains[domain_b]:
                        # Buscar overlap de palabras clave
                        words_a = ins_a.content_words()
                        words_b = ins_b.content_words()
                        shared = words_a & words_b

                        if len(shared) >= 2:
                            connection = {
                                "insight_a": ins_a,
                                "insight_b": ins_b,
                                "domain_a": domain_a,
                                "domain_b": domain_b,
                                "shared_concepts": list(shared)[:10],
                                "connection_strength": len(shared) / max(len(words_a | words_b), 1),
                                "description": (
                                    f"Conexión entre '{domain_a}' y '{domain_b}': "
                                    f"comparten {', '.join(list(shared)[:3])}"
                                ),
                            }
                            cross_domain.append(connection)

                            # Registrar conexión en los insights
                            if ins_b.insight_id not in ins_a.connections:
                                ins_a.connections.append(ins_b.insight_id)
                            if ins_a.insight_id not in ins_b.connections:
                                ins_b.connections.append(ins_a.insight_id)

        cross_domain.sort(key=lambda c: c["connection_strength"], reverse=True)
        return cross_domain[:20]

    def get_context_for_prompt(self, user_input: str, max_chars: int = 400) -> str:
        """Inyecta los insights más fuertes y relevantes en el prompt."""
        if not self.enabled or not self.insights:
            return ""

        # Buscar insights relevantes al input
        input_words = set(w.lower() for w in user_input.split() if len(w) > 3)
        scored = []

        for insight in self.insights.values():
            # Relevancia por overlap de palabras
            insight_words = insight.content_words()
            overlap = len(input_words & insight_words)
            if overlap > 0:
                # Score = relevancia * strength
                score = overlap * insight.strength
                scored.append((score, insight))

        if not scored:
            # Fallback: mostrar los más fuertes
            strongest = self.get_strongest(2)
            if not strongest:
                return ""
            scored = [(i.strength, i) for i in strongest]

        scored.sort(key=lambda x: x[0], reverse=True)

        lines = ["[INSIGHTS RELEVANTES]"]
        total = 0
        for score, insight in scored[:3]:
            line = (f"  [{insight.source_type}] {insight.content[:100]} "
                    f"(conf={insight.confidence:.0%})")
            if total + len(line) > max_chars - 30:
                break
            lines.append(line)
            total += len(line)
            insight.usage_count += 1

        return "\n".join(lines)[:max_chars] if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        by_type = defaultdict(int)
        by_domain = defaultdict(int)
        for ins in self.insights.values():
            by_type[ins.source_type] += 1
            by_domain[ins.domain] += 1

        avg_confidence = 0.0
        avg_novelty = 0.0
        if self.insights:
            avg_confidence = sum(i.confidence for i in self.insights.values()) / len(self.insights)
            avg_novelty = sum(i.novelty for i in self.insights.values()) / len(self.insights)

        return {
            "total_insights": self.total_insights,
            "stored_insights": len(self.insights),
            "total_novel": self.total_novel,
            "by_source_type": dict(by_type),
            "by_domain": dict(by_domain),
            "avg_confidence": round(avg_confidence, 4),
            "avg_novelty": round(avg_novelty, 4),
        }

    def status(self) -> str:
        stats = self.get_stats()
        domains = len(stats["by_domain"])
        return (f"Insights: {stats['stored_insights']} "
                f"({domains} dominios) | "
                f"Novel: {stats['total_novel']} | "
                f"Conf: {stats['avg_confidence']:.0%}")

    def generate_report(self) -> str:
        lines = ["=== INSIGHT SYNTHESIZER REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total insights generados: {stats['total_insights']}")
        lines.append(f"Almacenados: {stats['stored_insights']}")
        lines.append(f"Novel: {stats['total_novel']}")
        lines.append(f"Confianza promedio: {stats['avg_confidence']:.2%}")
        lines.append(f"Novedad promedio: {stats['avg_novelty']:.2%}")

        # Por tipo
        if stats["by_source_type"]:
            lines.append(f"\nPor tipo:")
            for stype, count in sorted(stats["by_source_type"].items()):
                lines.append(f"  {stype}: {count}")

        # Por dominio
        if stats["by_domain"]:
            lines.append(f"\nPor dominio:")
            for domain, count in sorted(stats["by_domain"].items()):
                lines.append(f"  {domain}: {count}")

        # Top insights
        strongest = self.get_strongest(10)
        if strongest:
            lines.append(f"\nTop insights:")
            for ins in strongest:
                bar = "█" * int(ins.strength * 20) + "░" * (20 - int(ins.strength * 20))
                lines.append(f"  [{bar}] {ins.strength:.2f}")
                lines.append(f"    {ins.content[:120]}")
                lines.append(f"    [{ins.source_type}] conf={ins.confidence:.0%} "
                             f"nov={ins.novelty:.0%} ev={len(ins.evidence)}")

        # Cross-domain connections
        connections = self.cross_domain_insights()
        if connections:
            lines.append(f"\nConexiones cross-domain ({len(connections)}):")
            for conn in connections[:5]:
                lines.append(f"  {conn['description']}")
                lines.append(f"    Fuerza: {conn['connection_strength']:.2f}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_insights": self.total_insights,
            "total_novel": self.total_novel,
            "insights": {iid: i.to_dict() for iid, i in self.insights.items()},
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
            self.total_insights = data.get("total_insights", 0)
            self.total_novel = data.get("total_novel", 0)
            for iid, id_data in data.get("insights", {}).items():
                self.insights[iid] = Insight.from_dict(id_data)
        except Exception:
            pass

    def clear(self):
        self.insights = {}
        self.total_insights = 0
        self.total_novel = 0

    def _detect_domain(self, text: str) -> str:
        """Detecta dominio desde keywords en el texto."""
        text_lower = text.lower()
        scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count >= 2:
                scores[domain] = count
        return max(scores, key=scores.get) if scores else "general"

    def _find_patterns(self, observations: list) -> list:
        """Encuentra patrones entre múltiples observaciones."""
        patterns = []

        # Buscar palabras frecuentes entre observaciones
        word_freq = defaultdict(int)
        for obs in observations:
            words = set(re.findall(r'\b\w+\b', obs.lower()))
            stopwords = {"el", "la", "los", "las", "de", "en", "un", "una",
                          "que", "es", "se", "con", "por", "para", "del",
                          "the", "a", "an", "in", "of", "to", "and", "is"}
            for word in words:
                if len(word) > 3 and word not in stopwords:
                    word_freq[word] += 1

        # Temas recurrentes (aparecen en 2+ observaciones)
        recurring = {w: c for w, c in word_freq.items() if c >= 2}
        if recurring:
            top_words = sorted(recurring, key=recurring.get, reverse=True)[:5]
            theme = ", ".join(top_words[:3])
            evidence = [obs[:150] for obs in observations if
                        any(w in obs.lower() for w in top_words[:3])]

            patterns.append({
                "description": f"Patrón recurrente detectado: temas '{theme}' "
                               f"aparecen en {len(evidence)} de {len(observations)} observaciones",
                "evidence": evidence[:5],
                "type": "frequency",
            })

        # Buscar pares de observaciones con alta similitud de contenido
        for i, obs_a in enumerate(observations):
            words_a = set(re.findall(r'\b\w+\b', obs_a.lower()))
            for obs_b in observations[i + 1:]:
                words_b = set(re.findall(r'\b\w+\b', obs_b.lower()))
                shared = words_a & words_b
                shared_significant = {w for w in shared if len(w) > 4}
                if len(shared_significant) >= 3:
                    patterns.append({
                        "description": (
                            f"Convergencia entre observaciones: comparten "
                            f"'{', '.join(list(shared_significant)[:4])}'"
                        ),
                        "evidence": [obs_a[:150], obs_b[:150]],
                        "type": "convergence",
                    })

        return patterns[:5]

    def _find_connections_with_existing(self, observations: list,
                                         domain: str) -> list:
        """Busca conexiones entre nuevas observaciones e insights existentes."""
        if not self.insights:
            return []

        connections = []
        obs_text = " ".join(observations).lower()
        obs_words = set(re.findall(r'\b\w+\b', obs_text))
        obs_words = {w for w in obs_words if len(w) > 3}

        for insight in self.insights.values():
            insight_words = insight.content_words()
            shared = obs_words & insight_words

            # Conexión cross-domain interesante
            if len(shared) >= 2 and insight.domain != domain:
                connections.append({
                    "content": (
                        f"Conexión cross-domain: nuevas observaciones en '{domain}' "
                        f"conectan con insight de '{insight.domain}' a través de "
                        f"'{', '.join(list(shared)[:3])}'"
                    ),
                    "evidence": [
                        f"Insight existente: {insight.content[:100]}",
                        f"Nuevas observaciones mencionan: {', '.join(list(shared)[:5])}",
                    ],
                })

        return connections[:3]

    def _evict(self):
        """Elimina insights más débiles cuando se supera el límite."""
        if len(self.insights) <= self.max_insights:
            return
        sorted_insights = sorted(
            self.insights.items(),
            key=lambda item: item[1].strength + item[1].usage_count * 0.01,
        )
        to_remove = len(self.insights) - self.max_insights
        for iid, _ in sorted_insights[:to_remove]:
            del self.insights[iid]
