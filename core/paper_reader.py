"""
GENESIS — Paper Reader (v3.5)

Lectura y análisis de papers/documentos. Parsea textos en secciones,
extrae claims clave usando patrones de lenguaje asertivo, y permite
buscar entre papers previamente leídos.

Componentes:
- PaperSection: sección de un paper con nombre, contenido y claims
- PaperSummary: resumen completo de un paper analizado
- ClaimExtractor: extrae claims del texto usando regex de lenguaje asertivo
- PaperReader: coordinador con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict


class PaperSection:
    """Una sección de un paper con nombre, contenido y claims extraídos."""

    VALID_NAMES = {"abstract", "introduction", "methods", "results",
                   "conclusion", "discussion", "references", "other"}

    def __init__(self, name: str, content: str = "", key_claims: list = None):
        self.name = name.lower().strip() if name else "other"
        if self.name not in self.VALID_NAMES:
            self.name = "other"
        self.content = content.strip()
        self.key_claims = key_claims or []

    def word_count(self) -> int:
        return len(self.content.split()) if self.content else 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "content": self.content[:5000],
            "key_claims": self.key_claims[:50],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperSection":
        return cls(
            name=data.get("name", "other"),
            content=data.get("content", ""),
            key_claims=data.get("key_claims", []),
        )


class PaperSummary:
    """Resumen completo de un paper analizado."""

    def __init__(self, title: str = "", authors: list = None):
        self.paper_id = hashlib.md5(
            f"paper_{title}_{time.time()}".encode()
        ).hexdigest()[:10]
        self.title = title.strip()
        self.authors = authors or []
        self.sections = {}          # name -> PaperSection
        self.key_findings = []      # Top findings extraídos
        self.methodology = ""       # Resumen de metodología
        self.created_at = time.time()
        self.total_words = 0
        self.total_claims = 0

    def add_section(self, section: PaperSection):
        """Agrega una sección al paper."""
        self.sections[section.name] = section
        self.total_words += section.word_count()
        self.total_claims += len(section.key_claims)

    def get_all_claims(self) -> list:
        """Retorna todos los claims de todas las secciones."""
        claims = []
        for section in self.sections.values():
            claims.extend(section.key_claims)
        return claims

    def brief_summary(self) -> str:
        """Resumen de 1 oración."""
        if "abstract" in self.sections and self.sections["abstract"].content:
            text = self.sections["abstract"].content
            # Primera oración del abstract
            sentences = re.split(r'[.!?]+', text)
            first = sentences[0].strip() if sentences else text[:150]
            return f"{self.title}: {first}." if self.title else f"{first}."
        if self.key_findings:
            return f"{self.title}: {self.key_findings[0]}"
        return f"{self.title}: paper de {self.total_words} palabras"

    def standard_summary(self) -> str:
        """Resumen de 1 párrafo."""
        parts = []
        if self.title:
            parts.append(f"'{self.title}'")
        if self.authors:
            parts.append(f"por {', '.join(self.authors[:3])}")
        if "abstract" in self.sections:
            abstract = self.sections["abstract"].content[:300]
            parts.append(f"— {abstract}")
        if self.key_findings:
            findings = "; ".join(self.key_findings[:3])
            parts.append(f"Hallazgos clave: {findings}.")
        if self.methodology:
            parts.append(f"Metodología: {self.methodology[:150]}.")
        return " ".join(parts)

    def detailed_summary(self) -> str:
        """Resumen detallado con todas las secciones."""
        lines = []
        if self.title:
            lines.append(f"=== {self.title.upper()} ===")
        if self.authors:
            lines.append(f"Autores: {', '.join(self.authors)}")
        lines.append(f"Palabras: {self.total_words} | Claims: {self.total_claims}")
        lines.append("")

        section_order = ["abstract", "introduction", "methods", "results",
                         "discussion", "conclusion", "other"]
        for sec_name in section_order:
            if sec_name in self.sections:
                sec = self.sections[sec_name]
                lines.append(f"--- {sec_name.upper()} ({sec.word_count()} palabras) ---")
                lines.append(sec.content[:500])
                if sec.key_claims:
                    lines.append(f"  Claims ({len(sec.key_claims)}):")
                    for claim in sec.key_claims[:5]:
                        lines.append(f"    - {claim}")
                lines.append("")

        if self.key_findings:
            lines.append("--- HALLAZGOS CLAVE ---")
            for f in self.key_findings:
                lines.append(f"  * {f}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors[:20],
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "key_findings": self.key_findings[:30],
            "methodology": self.methodology[:1000],
            "created_at": self.created_at,
            "total_words": self.total_words,
            "total_claims": self.total_claims,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperSummary":
        p = cls(
            title=data.get("title", ""),
            authors=data.get("authors", []),
        )
        p.paper_id = data.get("paper_id", p.paper_id)
        p.key_findings = data.get("key_findings", [])
        p.methodology = data.get("methodology", "")
        p.created_at = data.get("created_at", time.time())
        p.total_words = data.get("total_words", 0)
        p.total_claims = data.get("total_claims", 0)
        for name, sd in data.get("sections", {}).items():
            p.sections[name] = PaperSection.from_dict(sd)
        return p


class ClaimExtractor:
    """Extrae claims del texto usando regex para lenguaje asertivo."""

    # Patrones en inglés y español para lenguaje asertivo
    CLAIM_PATTERNS = [
        # Inglés
        (r"we (?:show|demonstrate|prove|find|observe|report|confirm|establish)\s+(?:that\s+)?(.{15,200}?)[\.;]", "assertion_en"),
        (r"(?:results?|data|findings?|evidence|analysis)\s+(?:indicate|suggest|show|reveal|confirm|demonstrate)s?\s+(?:that\s+)?(.{15,200}?)[\.;]", "evidence_en"),
        (r"this (?:demonstrates?|shows?|proves?|confirms?|establishes?|suggests?)\s+(?:that\s+)?(.{15,200}?)[\.;]", "demonstration_en"),
        (r"(?:our|these|the)\s+(?:results?|findings?|experiments?|analysis)\s+(?:clearly\s+)?(?:show|demonstrate|indicate|prove|reveal)\s+(.{15,200}?)[\.;]", "result_en"),
        (r"it (?:is|was|has been)\s+(?:shown|demonstrated|proven|established|confirmed)\s+(?:that\s+)?(.{15,200}?)[\.;]", "passive_en"),
        # Español
        (r"(?:se demuestra|demostramos|se muestra|mostramos)\s+(?:que\s+)?(.{15,200}?)[\.;]", "assertion_es"),
        (r"los resultados (?:indican|sugieren|muestran|revelan|confirman)\s+(?:que\s+)?(.{15,200}?)[\.;]", "evidence_es"),
        (r"(?:esto|ello|lo anterior)\s+(?:demuestra|muestra|prueba|confirma|establece)\s+(?:que\s+)?(.{15,200}?)[\.;]", "demonstration_es"),
        (r"(?:nuestros|estos|los)\s+(?:resultados|hallazgos|experimentos|análisis)\s+(?:demuestran|muestran|indican|prueban|revelan)\s+(.{15,200}?)[\.;]", "result_es"),
        (r"se (?:ha demostrado|ha comprobado|ha establecido|ha confirmado)\s+(?:que\s+)?(.{15,200}?)[\.;]", "passive_es"),
    ]

    def extract_claims(self, text: str) -> list:
        """Extrae claims del texto usando patrones de lenguaje asertivo."""
        if not text or len(text) < 30:
            return []

        claims = []
        seen = set()
        text_lower = text.lower()

        for pattern, claim_type in self.CLAIM_PATTERNS:
            try:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    claim_text = match.group(1).strip()
                    # Normalizar para dedup
                    normalized = re.sub(r'\s+', ' ', claim_text.lower())
                    if normalized not in seen and len(claim_text) > 15:
                        seen.add(normalized)
                        claims.append({
                            "text": claim_text,
                            "type": claim_type,
                            "position": match.start(),
                        })
            except re.error:
                continue

        # Ordenar por posición en el texto
        claims.sort(key=lambda c: c["position"])
        return claims

    def extract_claim_texts(self, text: str) -> list:
        """Versión simplificada que retorna solo los textos de claims."""
        return [c["text"] for c in self.extract_claims(text)]


class PaperReader:
    """
    Coordinador de lectura y análisis de papers.
    Parsea documentos en secciones, extrae claims y permite búsqueda.
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path("data/paper_reader")
        self.data_file = self.base_dir / "paper_reader_state.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.papers = {}            # paper_id -> PaperSummary
        self.claim_extractor = ClaimExtractor()
        self.max_papers = 100
        self.total_papers_read = 0
        self.total_claims_extracted = 0
        self.enabled = True

        self._load()

    # Patrones para detectar secciones por headers
    SECTION_PATTERNS = [
        (r"(?:^|\n)\s*#+\s*(abstract|resumen)\s*\n", "abstract"),
        (r"(?:^|\n)\s*#+\s*(introduction|introducción)\s*\n", "introduction"),
        (r"(?:^|\n)\s*#+\s*(methods?|methodology|metodología|métodos)\s*\n", "methods"),
        (r"(?:^|\n)\s*#+\s*(results?|resultados)\s*\n", "results"),
        (r"(?:^|\n)\s*#+\s*(discussion|discusión)\s*\n", "discussion"),
        (r"(?:^|\n)\s*#+\s*(conclusions?|conclusiones?)\s*\n", "conclusion"),
        (r"(?:^|\n)\s*#+\s*(references?|referencias|bibliografía)\s*\n", "references"),
        # También detectar en mayúsculas sin markdown
        (r"(?:^|\n)\s*(ABSTRACT|RESUMEN)\s*\n", "abstract"),
        (r"(?:^|\n)\s*(INTRODUCTION|INTRODUCCIÓN)\s*\n", "introduction"),
        (r"(?:^|\n)\s*(METHODS?|METHODOLOGY|METODOLOGÍA)\s*\n", "methods"),
        (r"(?:^|\n)\s*(RESULTS?|RESULTADOS)\s*\n", "results"),
        (r"(?:^|\n)\s*(DISCUSSION|DISCUSIÓN)\s*\n", "discussion"),
        (r"(?:^|\n)\s*(CONCLUSIONS?|CONCLUSIONES?)\s*\n", "conclusion"),
    ]

    # Patrones para detectar autores
    AUTHOR_PATTERNS = [
        r"(?:by|por|authors?|autores?)[:\s]+([A-Z][a-záéíóú]+ (?:[A-Z]\.\s*)?[A-Z][a-záéíóú]+(?:\s*,\s*[A-Z][a-záéíóú]+ (?:[A-Z]\.\s*)?[A-Z][a-záéíóú]+)*)",
        r"([A-Z][a-záéíóú]+(?:\s[A-Z]\.?)?\s[A-Z][a-záéíóú]+)\s+(?:et al\.?)",
    ]

    def read_paper(self, text: str, title: str = "") -> PaperSummary:
        """Parsea un texto en secciones, extrae claims y crea un PaperSummary."""
        if not self.enabled or not text:
            return None

        # Extraer título si no se proporcionó
        if not title:
            title = self._extract_title(text)

        # Extraer autores
        authors = self._extract_authors(text)

        paper = PaperSummary(title=title, authors=authors)

        # Parsear secciones
        sections = self._parse_sections(text)
        for section in sections:
            # Extraer claims por sección
            claims = self.claim_extractor.extract_claim_texts(section.content)
            section.key_claims = claims
            paper.add_section(section)
            self.total_claims_extracted += len(claims)

        # Generar key findings (claims de results y conclusion)
        paper.key_findings = self._extract_key_findings(paper)

        # Extraer metodología
        if "methods" in paper.sections:
            paper.methodology = paper.sections["methods"].content[:500]

        # Almacenar
        self.papers[paper.paper_id] = paper
        self.total_papers_read += 1

        # Evicción
        if len(self.papers) > self.max_papers:
            self._evict()

        return paper

    def summarize(self, paper_id: str = None, level: str = "brief") -> str:
        """Genera resumen del paper. Niveles: brief, standard, detailed."""
        paper = self._get_paper(paper_id)
        if not paper:
            return "No hay paper para resumir."

        if level == "brief":
            return paper.brief_summary()
        elif level == "standard":
            return paper.standard_summary()
        elif level == "detailed":
            return paper.detailed_summary()
        return paper.brief_summary()

    def get_key_findings(self, paper_id: str = None) -> list:
        """Retorna top findings del paper actual o especificado."""
        paper = self._get_paper(paper_id)
        if not paper:
            return []
        return paper.key_findings[:10]

    def search_papers(self, query: str) -> list:
        """Busca papers previamente leídos por keyword."""
        if not query or not self.papers:
            return []

        query_words = set(w.lower() for w in query.split() if len(w) > 2)
        results = []

        for paper in self.papers.values():
            score = 0
            # Buscar en título
            title_words = set(paper.title.lower().split())
            score += len(query_words & title_words) * 3

            # Buscar en findings
            findings_text = " ".join(paper.key_findings).lower()
            for qw in query_words:
                if qw in findings_text:
                    score += 2

            # Buscar en claims de todas las secciones
            all_claims = paper.get_all_claims()
            claims_text = " ".join(all_claims).lower()
            for qw in query_words:
                if qw in claims_text:
                    score += 1

            if score > 0:
                results.append({"paper": paper, "score": score})

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:10]

    def get_context_for_prompt(self, user_input: str, max_chars: int = 400) -> str:
        """Si el input es research-related, inyecta findings relevantes."""
        if not self.enabled or not self.papers:
            return ""

        # Verificar si el input es research-related
        research_words = {"paper", "estudio", "investigación", "research", "findings",
                          "hallazgos", "evidencia", "evidence", "claim", "resultado",
                          "hypothesis", "hipótesis", "método", "method", "análisis"}
        input_words = set(w.lower() for w in user_input.split())
        if not (input_words & research_words):
            return ""

        # Buscar papers relevantes
        results = self.search_papers(user_input)
        if not results:
            return ""

        lines = ["[PAPERS RELEVANTES]"]
        total = 0
        for r in results[:3]:
            paper = r["paper"]
            summary = paper.brief_summary()[:150]
            line = f"  {summary}"
            if total + len(line) > max_chars - 50:
                break
            lines.append(line)
            total += len(line)
            # Agregar top claim si hay espacio
            if paper.key_findings and total + 60 < max_chars:
                finding = paper.key_findings[0][:100]
                lines.append(f"    -> {finding}")
                total += len(finding) + 7

        return "\n".join(lines)[:max_chars] if len(lines) > 1 else ""

    def get_stats(self) -> dict:
        total_findings = sum(len(p.key_findings) for p in self.papers.values())
        total_sections = sum(len(p.sections) for p in self.papers.values())
        return {
            "total_papers_read": self.total_papers_read,
            "stored_papers": len(self.papers),
            "total_claims_extracted": self.total_claims_extracted,
            "total_findings": total_findings,
            "total_sections": total_sections,
        }

    def status(self) -> str:
        stats = self.get_stats()
        return (f"Papers: {stats['stored_papers']} leídos | "
                f"Claims: {stats['total_claims_extracted']} | "
                f"Findings: {stats['total_findings']}")

    def generate_report(self) -> str:
        lines = ["=== PAPER READER REPORT ==="]
        stats = self.get_stats()
        lines.append(f"Total papers leídos: {stats['total_papers_read']}")
        lines.append(f"Papers almacenados: {stats['stored_papers']}")
        lines.append(f"Total claims extraídos: {stats['total_claims_extracted']}")
        lines.append(f"Total findings: {stats['total_findings']}")

        if self.papers:
            lines.append(f"\nPapers recientes:")
            sorted_papers = sorted(
                self.papers.values(),
                key=lambda p: p.created_at,
                reverse=True,
            )
            for paper in sorted_papers[:10]:
                n_claims = paper.total_claims
                n_sections = len(paper.sections)
                lines.append(f"  [{paper.paper_id}] {paper.title or '(sin título)'}")
                lines.append(f"    {paper.total_words} palabras, "
                             f"{n_sections} secciones, {n_claims} claims")
                if paper.key_findings:
                    lines.append(f"    Hallazgo principal: {paper.key_findings[0][:120]}")

        return "\n".join(lines)

    def save(self):
        data = {
            "total_papers_read": self.total_papers_read,
            "total_claims_extracted": self.total_claims_extracted,
            "papers": {pid: p.to_dict() for pid, p in self.papers.items()},
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
            self.total_papers_read = data.get("total_papers_read", 0)
            self.total_claims_extracted = data.get("total_claims_extracted", 0)
            for pid, pd in data.get("papers", {}).items():
                self.papers[pid] = PaperSummary.from_dict(pd)
        except Exception:
            pass

    def clear(self):
        self.papers = {}
        self.total_papers_read = 0
        self.total_claims_extracted = 0

    def _extract_title(self, text: str) -> str:
        """Extrae el título del texto (primera línea no vacía significativa)."""
        for line in text.split("\n"):
            stripped = line.strip().strip("#").strip()
            if stripped and len(stripped) > 5 and len(stripped) < 200:
                return stripped
        return "Sin título"

    def _extract_authors(self, text: str) -> list:
        """Extrae autores del texto usando patrones."""
        authors = []
        for pattern in self.AUTHOR_PATTERNS:
            matches = re.finditer(pattern, text[:2000])
            for match in matches:
                raw = match.group(1).strip()
                # Separar por coma si hay múltiples
                for author in raw.split(","):
                    name = author.strip()
                    if name and len(name) > 3 and len(name) < 60:
                        authors.append(name)
        return list(dict.fromkeys(authors))[:20]  # Dedup preservando orden

    def _parse_sections(self, text: str) -> list:
        """Parsea texto en secciones por headers o estructura de párrafos."""
        # Intentar detectar secciones por headers
        section_positions = []
        for pattern, section_name in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                section_positions.append((match.start(), section_name, match.end()))

        if section_positions:
            # Ordenar por posición
            section_positions.sort(key=lambda x: x[0])
            sections = []
            for i, (start, name, content_start) in enumerate(section_positions):
                end = section_positions[i + 1][0] if i + 1 < len(section_positions) else len(text)
                content = text[content_start:end].strip()
                if content:
                    sections.append(PaperSection(name=name, content=content))
            return sections if sections else [PaperSection(name="other", content=text)]

        # Fallback: dividir por párrafos largos
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return [PaperSection(name="other", content=text)]

        sections = []
        if len(paragraphs) >= 4:
            # Heurística: primer párrafo = abstract, último = conclusion
            sections.append(PaperSection(name="abstract", content=paragraphs[0]))
            mid = "\n\n".join(paragraphs[1:-1])
            sections.append(PaperSection(name="other", content=mid))
            sections.append(PaperSection(name="conclusion", content=paragraphs[-1]))
        else:
            sections.append(PaperSection(name="other", content="\n\n".join(paragraphs)))

        return sections

    def _extract_key_findings(self, paper: PaperSummary) -> list:
        """Extrae key findings priorizando results y conclusion."""
        findings = []
        priority_sections = ["results", "conclusion", "abstract", "discussion"]

        for sec_name in priority_sections:
            if sec_name in paper.sections:
                claims = paper.sections[sec_name].key_claims
                findings.extend(claims[:5])

        # Si no hay claims, usar primeras oraciones de results/conclusion
        if not findings:
            for sec_name in ["results", "conclusion", "abstract"]:
                if sec_name in paper.sections:
                    content = paper.sections[sec_name].content
                    sentences = re.split(r'[.!?]+', content)
                    for s in sentences[:3]:
                        s = s.strip()
                        if len(s) > 20:
                            findings.append(s)

        return list(dict.fromkeys(findings))[:15]  # Dedup

    def _evict(self):
        """Elimina papers más antiguos cuando se supera el límite."""
        if len(self.papers) <= self.max_papers:
            return
        sorted_papers = sorted(
            self.papers.items(),
            key=lambda item: item[1].created_at,
        )
        to_remove = len(self.papers) - self.max_papers
        for pid, _ in sorted_papers[:to_remove]:
            del self.papers[pid]

    def _get_paper(self, paper_id: str = None) -> PaperSummary:
        """Obtiene un paper por ID o el último leído."""
        if paper_id and paper_id in self.papers:
            return self.papers[paper_id]
        if self.papers:
            return max(self.papers.values(), key=lambda p: p.created_at)
        return None
