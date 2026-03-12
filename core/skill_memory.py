"""
GENESIS — Skill Memory (v2.3)

Memoria de procedimientos: Genesis aprende HOW-TO paso a paso
y los reutiliza cuando detecta preguntas similares.

Componentes:
- SkillEntry: Un procedimiento almacenado con pasos, tags, versión
- SkillExtractor: Detecta cuando una respuesta contiene un procedimiento
- SkillRecall: Busca skills relevantes para inyectar en el contexto
- SkillMemory: Coordinador principal con persistencia
"""
import time
import json
import re
import hashlib
from pathlib import Path


class SkillEntry:
    """Un procedimiento almacenado (skill)."""

    def __init__(self, title: str, steps: list, tags: list = None,
                 source_query: str = "", skill_id: str = None,
                 version: int = 1):
        self.skill_id = skill_id or hashlib.md5(
            f"{title}{time.time()}".encode()
        ).hexdigest()[:10]
        self.title = title
        self.steps = steps  # Lista de strings
        self.tags = tags or []
        self.source_query = source_query
        self.version = version
        self.created_at = time.time()
        self.last_used = time.time()
        self.times_used = 0
        self.quality = 0.5  # Se ajusta con feedback

    def to_text(self) -> str:
        """Genera representación textual del skill."""
        lines = [f"SKILL: {self.title}"]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"  {i}. {step}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.skill_id,
            "title": self.title,
            "steps": self.steps,
            "tags": self.tags,
            "source_query": self.source_query[:200],
            "version": self.version,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "times_used": self.times_used,
            "quality": self.quality,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillEntry":
        entry = cls(
            title=data["title"],
            steps=data["steps"],
            tags=data.get("tags", []),
            source_query=data.get("source_query", ""),
            skill_id=data.get("id"),
            version=data.get("version", 1),
        )
        entry.created_at = data.get("created_at", time.time())
        entry.last_used = data.get("last_used", time.time())
        entry.times_used = data.get("times_used", 0)
        entry.quality = data.get("quality", 0.5)
        return entry


class SkillExtractor:
    """
    Detecta cuando una respuesta contiene un procedimiento
    y lo extrae como skill.
    """

    # Patrones que indican que hay un procedimiento
    PROCEDURE_PATTERNS = [
        r'(?:paso|step)\s*\d+[.:)]',
        r'^\s*\d+[.)]\s+.{10,}',
        r'(?:primero|segundo|tercero|cuarto|quinto)',
        r'(?:first|second|third|then|next|finally)',
        r'(?:para hacer|para lograr|para configurar|para instalar)',
        r'(?:como hacer|como configurar|como instalar|como crear)',
    ]

    # Patrones de pregunta tipo "cómo"
    HOW_TO_PATTERNS = [
        r'como\s+(?:hago|hacer|puedo|configuro|instalo|creo|uso|instalar|configurar|crear|usar|desplegar|deploy)',
        r'como\s+se\s+(?:hace|configura|instala|crea|usa)',
        r'how\s+(?:to|do|can|should)',
        r'pasos\s+para',
        r'tutorial',
        r'guia\s+para',
        r'instrucciones\s+para',
    ]

    def is_how_to_question(self, text: str) -> bool:
        """Detecta si el input es una pregunta tipo 'cómo hacer X'."""
        text_lower = text.lower()
        return any(
            re.search(p, text_lower) for p in self.HOW_TO_PATTERNS
        )

    def has_procedure(self, response: str) -> bool:
        """Detecta si una respuesta contiene un procedimiento."""
        response_lower = response.lower()

        # Buscar patrones de procedimiento
        pattern_matches = sum(
            1 for p in self.PROCEDURE_PATTERNS
            if re.search(p, response_lower, re.MULTILINE)
        )

        # También buscar listas numeradas
        numbered_steps = len(re.findall(
            r'^\s*\d+[.)]\s+.{10,}', response, re.MULTILINE
        ))

        # Necesita al menos 2 indicadores o 3+ pasos numerados
        return pattern_matches >= 2 or numbered_steps >= 3

    def extract_skill(self, user_input: str, response: str) -> SkillEntry:
        """
        Extrae un skill de una respuesta.
        Retorna None si no se puede extraer o no es pregunta how-to.
        """
        if not self.is_how_to_question(user_input):
            return None

        if not self.has_procedure(response):
            return None

        # Extraer título del skill
        title = self._extract_title(user_input)
        if not title:
            return None

        # Extraer pasos
        steps = self._extract_steps(response)
        if len(steps) < 2:
            return None

        # Extraer tags
        tags = self._extract_tags(user_input, response)

        return SkillEntry(
            title=title,
            steps=steps,
            tags=tags,
            source_query=user_input,
        )

    def _extract_title(self, user_input: str) -> str:
        """Genera un título corto para el skill."""
        # Remover palabras interrogativas
        clean = re.sub(
            r'^(como|how|que pasos|cuales son los pasos|pasos para)\s+',
            '', user_input.lower().strip(), flags=re.IGNORECASE
        )
        # Capitalizar y truncar
        clean = clean.strip("?¿!¡ ").strip()
        if len(clean) < 5:
            return ""
        return clean[:80].capitalize()

    def _extract_steps(self, response: str) -> list:
        """Extrae pasos numerados de una respuesta."""
        steps = []

        # Intentar extraer pasos numerados (1. xxx, 2. xxx)
        numbered = re.findall(
            r'^\s*\d+[.)]\s+(.{10,}?)(?=\n\s*\d+[.)]|\n\n|\Z)',
            response, re.MULTILINE | re.DOTALL
        )
        if numbered:
            for step in numbered:
                clean = step.strip().split('\n')[0].strip()
                if len(clean) >= 10:
                    steps.append(clean[:300])

        # Si no hay numerados, buscar bullets
        if not steps:
            bullets = re.findall(
                r'^\s*[-*]\s+(.{10,}?)(?=\n\s*[-*]|\n\n|\Z)',
                response, re.MULTILINE | re.DOTALL
            )
            for bullet in bullets:
                clean = bullet.strip().split('\n')[0].strip()
                if len(clean) >= 10:
                    steps.append(clean[:300])

        return steps[:15]  # Max 15 pasos

    def _extract_tags(self, user_input: str, response: str) -> list:
        """Extrae tags relevantes del contenido."""
        text = f"{user_input} {response}".lower()
        tags = set()

        # Keywords técnicos comunes
        tech_keywords = [
            "python", "javascript", "docker", "git", "linux", "windows",
            "react", "flask", "django", "api", "database", "sql",
            "html", "css", "node", "npm", "pip", "conda",
            "deploy", "install", "config", "setup", "debug",
            "seguridad", "red", "servidor", "testing", "backup",
        ]
        for kw in tech_keywords:
            if kw in text:
                tags.add(kw)

        return list(tags)[:10]


class SkillMemory:
    """
    Memoria de skills con indexación, búsqueda, y persistencia.
    """

    def __init__(self, embeddings_engine=None, base_dir: str = None):
        self.embeddings = embeddings_engine
        self.base_dir = Path(base_dir) if base_dir else Path("data/skill_memory")
        self.data_file = self.base_dir / "skills.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.skills = {}  # skill_id -> SkillEntry
        self.extractor = SkillExtractor()
        self.max_skills = 200
        self.total_extracted = 0
        self.total_recalls = 0
        self.total_hits = 0

        # Cargar estado previo
        self._load()

    def extract_and_store(self, user_input: str, response: str) -> str:
        """
        Intenta extraer un skill de la respuesta y almacenarlo.
        Retorna skill_id si se extrajo, None si no.
        """
        # Solo procesar si parece una pregunta how-to
        if not self.extractor.is_how_to_question(user_input):
            return None

        skill = self.extractor.extract_skill(user_input, response)
        if not skill:
            return None

        # Verificar duplicados por título similar
        for existing in self.skills.values():
            if self._title_similarity(skill.title, existing.title) > 0.8:
                # Actualizar versión existente si la nueva tiene más pasos
                if len(skill.steps) > len(existing.steps):
                    existing.steps = skill.steps
                    existing.version += 1
                    existing.tags = list(set(existing.tags + skill.tags))
                    self.total_extracted += 1
                    return existing.skill_id
                return None  # Duplicado, no actualizar

        # Almacenar nuevo skill
        self.skills[skill.skill_id] = skill
        self.total_extracted += 1

        # Indexar en embeddings si disponible
        if self.embeddings:
            try:
                self.embeddings.add_text(
                    f"skill_{skill.skill_id}",
                    f"{skill.title} {' '.join(skill.tags)} {skill.source_query}",
                    metadata={"type": "skill", "skill_id": skill.skill_id},
                )
            except Exception:
                pass

        # Evictar si hay demasiados
        if len(self.skills) > self.max_skills:
            self._evict()

        # Persistir periódicamente
        if self.total_extracted % 5 == 0:
            self.save()

        return skill.skill_id

    def recall(self, query: str, top_k: int = 3) -> list:
        """
        Busca skills relevantes para una query.
        Retorna lista de SkillEntry matches.
        """
        self.total_recalls += 1

        if not self.skills:
            return []

        # Si hay embeddings, buscar semánticamente
        if self.embeddings:
            try:
                results = self.embeddings.search(query, top_k=top_k)
                matched = []
                for r in results:
                    key = r.get("key", "")
                    if key.startswith("skill_"):
                        sid = key.replace("skill_", "")
                        if sid in self.skills:
                            skill = self.skills[sid]
                            skill.last_used = time.time()
                            skill.times_used += 1
                            matched.append(skill)
                            self.total_hits += 1
                if matched:
                    return matched[:top_k]
            except Exception:
                pass

        # Fallback: búsqueda por keywords
        query_lower = query.lower()
        query_words = set(
            w for w in re.findall(r'\b\w+\b', query_lower) if len(w) > 3
        )

        scored = []
        for skill in self.skills.values():
            # Score basado en overlap de palabras
            skill_text = f"{skill.title} {' '.join(skill.tags)} {skill.source_query}".lower()
            skill_words = set(
                w for w in re.findall(r'\b\w+\b', skill_text) if len(w) > 3
            )
            if not query_words:
                continue
            overlap = len(query_words & skill_words)
            if overlap > 0:
                score = overlap / len(query_words)
                scored.append((score, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, skill in scored[:top_k]:
            if score >= 0.2:  # Mínimo 20% overlap
                skill.last_used = time.time()
                skill.times_used += 1
                results.append(skill)
                self.total_hits += 1

        return results

    def get_context_for_prompt(self, user_input: str, max_chars: int = 1000) -> str:
        """
        Genera contexto de skills para inyectar en el prompt.
        Solo si detecta una pregunta how-to.
        """
        if not self.extractor.is_how_to_question(user_input):
            return ""

        matches = self.recall(user_input, top_k=2)
        if not matches:
            return ""

        lines = ["[SKILLS APRENDIDOS RELEVANTES]"]
        total_chars = 0
        for skill in matches:
            text = skill.to_text()
            if total_chars + len(text) > max_chars:
                break
            lines.append(text)
            total_chars += len(text)
            lines.append("")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _title_similarity(self, a: str, b: str) -> float:
        """Similitud entre títulos basada en containment (el menor está contenido en el mayor)."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        min_size = min(len(words_a), len(words_b))
        return len(intersection) / min_size if min_size else 0.0

    def _evict(self):
        """Elimina skills antiguos y poco usados."""
        if len(self.skills) <= self.max_skills:
            return
        # Score: quality * times_used - age_penalty
        now = time.time()
        scored = []
        for sid, skill in self.skills.items():
            age_days = (now - skill.created_at) / 86400
            score = skill.quality * (skill.times_used + 1) - (age_days * 0.01)
            scored.append((score, sid))
        scored.sort(key=lambda x: x[0])

        # Eliminar los peores hasta volver al límite
        to_remove = len(self.skills) - self.max_skills + 10
        for _, sid in scored[:to_remove]:
            del self.skills[sid]
            if self.embeddings:
                try:
                    self.embeddings.remove(f"skill_{sid}")
                except Exception:
                    pass

    def get_stats(self) -> dict:
        return {
            "total_skills": len(self.skills),
            "total_extracted": self.total_extracted,
            "total_recalls": self.total_recalls,
            "total_hits": self.total_hits,
            "top_skills": [
                {"title": s.title, "used": s.times_used, "version": s.version}
                for s in sorted(
                    self.skills.values(),
                    key=lambda x: x.times_used, reverse=True
                )[:5]
            ],
        }

    def status(self) -> str:
        """Status string para /status."""
        lines = [
            f"  Skills: {len(self.skills)}",
            f"  Extraidos: {self.total_extracted}",
            f"  Recalls: {self.total_recalls}",
            f"  Hits: {self.total_hits}",
        ]
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Reporte completo para /skills."""
        lines = ["=== SKILL MEMORY ===", ""]
        lines.append(f"Skills almacenados: {len(self.skills)}")
        lines.append(f"Total extraidos: {self.total_extracted}")
        lines.append(f"Recalls: {self.total_recalls}")
        lines.append(f"Hits: {self.total_hits}")
        lines.append("")

        if self.skills:
            # Top skills por uso
            top = sorted(self.skills.values(),
                         key=lambda x: x.times_used, reverse=True)[:10]
            lines.append("TOP SKILLS:")
            for s in top:
                lines.append(f"  [{s.skill_id}] {s.title} "
                             f"(v{s.version}, usado {s.times_used}x, "
                             f"q={s.quality:.1f})")
            lines.append("")

            # Skills recientes
            recent = sorted(self.skills.values(),
                            key=lambda x: x.created_at, reverse=True)[:5]
            lines.append("RECIENTES:")
            for s in recent:
                lines.append(f"  {s.title} ({len(s.steps)} pasos)")
            lines.append("")

            # Distribución de tags
            all_tags = {}
            for s in self.skills.values():
                for tag in s.tags:
                    all_tags[tag] = all_tags.get(tag, 0) + 1
            if all_tags:
                lines.append("TAGS:")
                for tag, count in sorted(all_tags.items(),
                                          key=lambda x: x[1], reverse=True)[:10]:
                    lines.append(f"  {tag}: {count}")

        return "\n".join(lines)

    def get_skill(self, skill_id: str) -> SkillEntry:
        """Retorna un skill por ID."""
        return self.skills.get(skill_id)

    def delete_skill(self, skill_id: str) -> bool:
        """Elimina un skill por ID."""
        if skill_id in self.skills:
            del self.skills[skill_id]
            if self.embeddings:
                try:
                    self.embeddings.remove(f"skill_{skill_id}")
                except Exception:
                    pass
            return True
        return False

    def save(self):
        """Persiste a disco."""
        data = {
            "skills": {sid: s.to_dict() for sid, s in self.skills.items()},
            "stats": {
                "total_extracted": self.total_extracted,
                "total_recalls": self.total_recalls,
                "total_hits": self.total_hits,
            },
        }
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load(self):
        """Carga estado previo."""
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for sid, sdata in data.get("skills", {}).items():
                self.skills[sid] = SkillEntry.from_dict(sdata)
            stats = data.get("stats", {})
            self.total_extracted = stats.get("total_extracted", 0)
            self.total_recalls = stats.get("total_recalls", 0)
            self.total_hits = stats.get("total_hits", 0)
        except Exception:
            pass

    def clear(self):
        """Resetea todo."""
        self.skills.clear()
        self.total_extracted = 0
        self.total_recalls = 0
        self.total_hits = 0
        if self.data_file.exists():
            self.data_file.unlink()
