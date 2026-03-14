"""
GENESIS — Story Generator (v3.2) "Creative Genesis"

Narrativa creativa con estructura. Genera esqueletos de historias con
arcos de 5 actos, perfiles de personajes y plantillas por genero.
Permite avanzar por actos y mantener contexto narrativo activo.

Componentes:
- StoryArc: arco de 5 actos con progreso
- CharacterProfile: perfil de personaje con tipo de arco
- StoryTemplate: plantillas por genero con setting/conflicto/tono
- StoryGenerator: coordinador con persistencia
"""
import time
import json
import re
from pathlib import Path
from collections import defaultdict


# ── StoryArc ─────────────────────────────────────────────────────────

class StoryArc:
    """Arco narrativo de 5 actos con seguimiento de progreso."""

    ACTS = ["setup", "rising_action", "climax", "falling_action", "resolution"]
    ACT_DESCRIPTIONS = {
        "setup":          "Presentacion del mundo, personajes y conflicto inicial",
        "rising_action":  "Escalada de tension, obstaculos y desarrollo de personajes",
        "climax":         "Punto de maxima tension, confrontacion decisiva",
        "falling_action": "Consecuencias del climax, resolucion de subtramas",
        "resolution":     "Desenlace final, cierre de arcos de personaje",
    }

    def __init__(self):
        self.current_act_index = 0
        self.act_notes = {act: "" for act in self.ACTS}
        self.completed = False

    @property
    def current_act(self) -> str:
        if self.current_act_index >= len(self.ACTS):
            return "resolution"
        return self.ACTS[self.current_act_index]

    @property
    def progress(self) -> float:
        """Progreso del arco (0.0 a 1.0)."""
        if self.completed:
            return 1.0
        return self.current_act_index / len(self.ACTS)

    def advance(self) -> str:
        """Avanza al siguiente acto. Retorna el nombre del acto actual."""
        if self.current_act_index < len(self.ACTS) - 1:
            self.current_act_index += 1
        else:
            self.completed = True
        return self.current_act

    def set_note(self, act: str, note: str):
        """Agrega nota a un acto especifico."""
        if act in self.act_notes:
            self.act_notes[act] = note

    def to_dict(self) -> dict:
        return {
            "current_act_index": self.current_act_index,
            "act_notes": self.act_notes,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StoryArc":
        arc = cls()
        arc.current_act_index = d.get("current_act_index", 0)
        arc.act_notes = d.get("act_notes", {act: "" for act in cls.ACTS})
        arc.completed = d.get("completed", False)
        return arc


# ── CharacterProfile ─────────────────────────────────────────────────

class CharacterProfile:
    """Perfil de personaje con rasgos y tipo de arco."""

    VALID_ARC_TYPES = ["hero", "mentor", "trickster", "shadow"]

    def __init__(self, name: str, traits: list = None,
                 motivation: str = "", arc_type: str = "hero"):
        self.name = name
        self.traits = traits or []
        self.motivation = motivation
        self.arc_type = arc_type if arc_type in self.VALID_ARC_TYPES else "hero"
        self.created_at = time.time()

    def summary(self) -> str:
        """Resumen del personaje en una linea."""
        traits_str = ", ".join(self.traits[:3]) if self.traits else "sin rasgos"
        return f"{self.name} ({self.arc_type}): {traits_str} — {self.motivation}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "traits": self.traits,
            "motivation": self.motivation,
            "arc_type": self.arc_type,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterProfile":
        cp = cls(
            name=d["name"],
            traits=d.get("traits", []),
            motivation=d.get("motivation", ""),
            arc_type=d.get("arc_type", "hero"),
        )
        cp.created_at = d.get("created_at", time.time())
        return cp


# ── StoryTemplate ────────────────────────────────────────────────────

class StoryTemplate:
    """Plantillas predefinidas por genero literario."""

    GENRES = {
        "sci_fi": {
            "setting": "Futuro lejano, colonias espaciales o Tierra transformada por tecnologia",
            "conflict": "La humanidad enfrenta una amenaza tecnologica, alienigena o existencial",
            "tone": "Reflexivo, tenso, con asombro ante lo desconocido",
            "keywords": [
                "espacio", "robot", "ia", "futuro", "nave", "planeta",
                "tecnologia", "android", "ciborg", "galaxia", "space",
                "alien", "ai", "robot", "cyber", "quantum",
            ],
        },
        "fantasy": {
            "setting": "Mundo con magia, criaturas miticas y reinos en conflicto",
            "conflict": "Una fuerza oscura amenaza el equilibrio, un elegido debe actuar",
            "tone": "Epico, misterioso, con sentido de maravilla",
            "keywords": [
                "magia", "dragon", "reino", "espada", "hechizo", "elfo",
                "mago", "profecia", "bosque", "castillo", "magic",
                "wizard", "sword", "quest", "kingdom", "mythical",
            ],
        },
        "thriller": {
            "setting": "Ciudad moderna, ambientes urbanos o corporativos",
            "conflict": "Conspiracion, peligro oculto o carrera contra el tiempo",
            "tone": "Tenso, rapido, con giros inesperados",
            "keywords": [
                "asesino", "secreto", "conspiracion", "detective", "crimen",
                "peligro", "trampa", "sospechoso", "misterio", "policia",
                "murder", "crime", "secret", "danger", "chase", "spy",
            ],
        },
        "slice_of_life": {
            "setting": "Entorno cotidiano, pueblo o ciudad familiar",
            "conflict": "Dilemas personales, relaciones, crecimiento interior",
            "tone": "Intimo, calido, con momentos de reflexion",
            "keywords": [
                "familia", "amor", "amigos", "escuela", "trabajo", "vida",
                "recuerdos", "crecer", "hogar", "relacion", "family",
                "love", "friends", "home", "memories", "daily",
            ],
        },
    }

    @classmethod
    def detect_genre(cls, text: str) -> str:
        """Detecta genero por keywords en el texto."""
        text_lower = text.lower()
        scores = {}
        for genre, config in cls.GENRES.items():
            hits = sum(1 for kw in config["keywords"] if kw in text_lower)
            scores[genre] = hits

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "sci_fi"  # Default si no hay match
        return best

    @classmethod
    def get_template(cls, genre: str) -> dict:
        """Retorna la plantilla para el genero dado."""
        return cls.GENRES.get(genre, cls.GENRES["sci_fi"])


# ── StoryGenerator (Coordinador) ────────────────────────────────────

class StoryGenerator:
    """Coordinador de generacion narrativa con persistencia."""

    def __init__(self, base_dir: str = "data/story_generator"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.stories = []           # Lista de story dicts
        self.current_story = -1     # Indice de la historia activa (-1 = ninguna)
        self.total_stories = 0
        self.total_characters = 0

        self._load()

    def create_story(self, prompt: str, genre: str = "auto") -> dict:
        """Crea un esqueleto de historia a partir de un prompt.

        Si genre="auto", detecta el genero por keywords en el prompt.
        Retorna dict con el outline de la historia.
        """
        if genre == "auto":
            genre = StoryTemplate.detect_genre(prompt)

        template = StoryTemplate.get_template(genre)
        arc = StoryArc()

        # Generar nota para el primer acto basada en el prompt
        first_words = prompt.strip()[:80]
        arc.set_note("setup", f"Basado en: {first_words}")

        story = {
            "id": self.total_stories,
            "title": self._generate_title(prompt),
            "prompt": prompt,
            "genre": genre,
            "setting": template["setting"],
            "conflict": template["conflict"],
            "tone": template["tone"],
            "arc": arc.to_dict(),
            "characters": [],
            "created_at": time.time(),
            "last_updated": time.time(),
        }

        self.stories.append(story)
        self.current_story = len(self.stories) - 1
        self.total_stories += 1

        return {
            "story_id": story["id"],
            "title": story["title"],
            "genre": genre,
            "setting": story["setting"],
            "conflict": story["conflict"],
            "tone": story["tone"],
            "current_act": arc.current_act,
            "act_description": StoryArc.ACT_DESCRIPTIONS[arc.current_act],
        }

    def _generate_title(self, prompt: str) -> str:
        """Genera un titulo a partir de las primeras palabras significativas."""
        # Filtrar palabras cortas y tomar las primeras significativas
        words = re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}\b', prompt)
        significant = [w.capitalize() for w in words[:4]]
        if significant:
            return " ".join(significant)
        return f"Historia #{self.total_stories}"

    def add_character(self, name: str, traits: list = None,
                      motivation: str = "") -> dict:
        """Agrega un personaje a la historia activa."""
        if self.current_story < 0 or self.current_story >= len(self.stories):
            return {"error": "No hay historia activa"}

        # Determinar arc_type segun rasgos
        arc_type = self._infer_arc_type(traits or [], motivation)
        char = CharacterProfile(name, traits, motivation, arc_type)

        story = self.stories[self.current_story]
        story["characters"].append(char.to_dict())
        story["last_updated"] = time.time()
        self.total_characters += 1

        return {
            "name": char.name,
            "arc_type": char.arc_type,
            "summary": char.summary(),
            "character_count": len(story["characters"]),
        }

    def _infer_arc_type(self, traits: list, motivation: str) -> str:
        """Infiere el tipo de arco del personaje por rasgos y motivacion."""
        text = " ".join(traits).lower() + " " + motivation.lower()

        hero_signals = ["valiente", "noble", "justo", "brave", "hero", "salvar", "proteger"]
        mentor_signals = ["sabio", "viejo", "guia", "maestro", "wise", "teacher", "mentor"]
        trickster_signals = ["astuto", "bromista", "caos", "clever", "cunning", "tricky"]
        shadow_signals = ["oscuro", "venganza", "poder", "dark", "villain", "evil", "cruel"]

        scores = {
            "hero": sum(1 for s in hero_signals if s in text),
            "mentor": sum(1 for s in mentor_signals if s in text),
            "trickster": sum(1 for s in trickster_signals if s in text),
            "shadow": sum(1 for s in shadow_signals if s in text),
        }

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "hero"
        return best

    def advance_act(self) -> dict:
        """Avanza la historia activa al siguiente acto."""
        if self.current_story < 0 or self.current_story >= len(self.stories):
            return {"error": "No hay historia activa"}

        story = self.stories[self.current_story]
        arc = StoryArc.from_dict(story["arc"])

        if arc.completed:
            return {
                "status": "completed",
                "message": "La historia ya esta completada",
                "progress": 1.0,
            }

        new_act = arc.advance()
        story["arc"] = arc.to_dict()
        story["last_updated"] = time.time()

        return {
            "current_act": new_act,
            "act_description": StoryArc.ACT_DESCRIPTIONS.get(new_act, ""),
            "progress": arc.progress,
            "completed": arc.completed,
        }

    def get_context_for_prompt(self, user_input: str = "",
                                max_chars: int = 400) -> str:
        """Si hay historia activa, inyecta contexto narrativo en el prompt."""
        if self.current_story < 0 or self.current_story >= len(self.stories):
            return ""

        # Detectar si el input del usuario es relevante a la historia
        story_keywords = ["historia", "story", "personaje", "character", "acto",
                          "act", "trama", "plot", "narr", "escena", "scene",
                          "continua", "siguiente", "capitulo"]
        if user_input:
            input_lower = user_input.lower()
            relevant = any(kw in input_lower for kw in story_keywords)
            if not relevant:
                return ""

        story = self.stories[self.current_story]
        arc = StoryArc.from_dict(story["arc"])

        parts = [
            f"[CONTEXTO NARRATIVO] Historia: '{story['title']}' ({story['genre']})",
            f"Acto actual: {arc.current_act} — {StoryArc.ACT_DESCRIPTIONS.get(arc.current_act, '')}",
            f"Tono: {story['tone']}",
        ]

        # Agregar personajes si hay
        chars = story.get("characters", [])
        if chars:
            char_names = [c["name"] for c in chars[:4]]
            parts.append(f"Personajes: {', '.join(char_names)}")

        context = ". ".join(parts)
        return context[:max_chars]

    def get_stats(self) -> dict:
        active_title = ""
        active_genre = ""
        active_progress = 0.0
        if 0 <= self.current_story < len(self.stories):
            s = self.stories[self.current_story]
            active_title = s["title"]
            active_genre = s["genre"]
            arc = StoryArc.from_dict(s["arc"])
            active_progress = arc.progress

        return {
            "total_stories": self.total_stories,
            "total_characters": self.total_characters,
            "active_stories": len(self.stories),
            "current_story_title": active_title,
            "current_story_genre": active_genre,
            "current_story_progress": round(active_progress, 2),
        }

    def status(self) -> str:
        stats = self.get_stats()
        if stats["current_story_title"]:
            return (f"  Historias: {stats['total_stories']} | "
                    f"Personajes: {stats['total_characters']} | "
                    f"Activa: '{stats['current_story_title']}' "
                    f"({stats['current_story_genre']}, "
                    f"{stats['current_story_progress']:.0%})")
        return (f"  Historias: {stats['total_stories']} | "
                f"Personajes: {stats['total_characters']} | "
                f"Sin historia activa")

    def generate_report(self) -> str:
        lines = [
            "=== STORY GENERATOR ===",
            f"Total historias: {self.total_stories}",
            f"Total personajes: {self.total_characters}",
            "",
        ]

        if not self.stories:
            lines.append("No hay historias registradas.")
            return "\n".join(lines)

        for i, story in enumerate(self.stories):
            arc = StoryArc.from_dict(story["arc"])
            marker = " << ACTIVA" if i == self.current_story else ""
            lines.append(f"  [{i}] '{story['title']}' ({story['genre']}){marker}")
            lines.append(f"      Acto: {arc.current_act} | "
                         f"Progreso: {arc.progress:.0%} | "
                         f"Personajes: {len(story.get('characters', []))}")

            # Listar personajes
            for char in story.get("characters", [])[:5]:
                cp = CharacterProfile.from_dict(char)
                lines.append(f"        - {cp.summary()}")

        return "\n".join(lines)

    def save(self):
        data = {
            "stories": self.stories,
            "current_story": self.current_story,
            "total_stories": self.total_stories,
            "total_characters": self.total_characters,
        }
        path = self.base_dir / "story_generator.json"
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "story_generator.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.stories = data.get("stories", [])
            self.current_story = data.get("current_story", -1)
            self.total_stories = data.get("total_stories", 0)
            self.total_characters = data.get("total_characters", 0)
        except Exception:
            pass

    def clear(self):
        self.stories = []
        self.current_story = -1
        self.total_stories = 0
        self.total_characters = 0
        self.save()
