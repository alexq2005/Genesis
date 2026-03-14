"""
GENESIS — Idea Brainstormer (v3.2) "Creative Genesis"

Ideacion divergente estructurada. Facilita sesiones de brainstorming
con multiples metodos (SCAMPER, Six Hats, Mind Map, What-If),
auto-scoring de ideas por viabilidad/novedad/impacto, y combinacion
de ideas para generar conceptos hibridos.

Componentes:
- BrainstormMethod: metodos de brainstorming con pasos y prompts
- IdeaEntry: entrada de idea con scoring multidimensional
- IdeaScorer: scoring automatico por senales lexicas
- IdeaBrainstormer: coordinador con persistencia
"""
import time
import json
import re
import math
from pathlib import Path
from collections import defaultdict


# ── BrainstormMethod ─────────────────────────────────────────────────

class BrainstormMethod:
    """Metodo de brainstorming con descripcion, prompts y pasos."""

    METHODS = {
        "scamper": {
            "name": "SCAMPER",
            "description": "Tecnica de creatividad sistematica: Sustituir, Combinar, Adaptar, Modificar, Poner otros usos, Eliminar, Reorganizar",
            "prompts": [
                "Que podrias SUSTITUIR en esta idea?",
                "Que podrias COMBINAR con algo existente?",
                "Que podrias ADAPTAR de otro contexto?",
                "Que podrias MODIFICAR o magnificar?",
                "Para que OTROS USOS serviria?",
                "Que podrias ELIMINAR para simplificar?",
                "Como podrias REORGANIZAR el orden?",
            ],
            "steps": [
                "Definir el problema u objeto base",
                "Aplicar cada letra de SCAMPER como filtro",
                "Generar al menos una idea por filtro",
                "Evaluar y seleccionar las mejores variantes",
            ],
            "keywords": [
                "mejorar", "existente", "modificar", "cambiar", "adaptar",
                "sustituir", "simplificar", "improve", "modify", "change",
            ],
        },
        "six_hats": {
            "name": "Seis Sombreros de Pensar",
            "description": "Metodo de De Bono: analizar desde 6 perspectivas (hechos, emociones, critica, optimismo, creatividad, proceso)",
            "prompts": [
                "BLANCO: Que datos y hechos tenemos?",
                "ROJO: Que sientes intuitivamente sobre esto?",
                "NEGRO: Que riesgos o problemas ves?",
                "AMARILLO: Que beneficios y oportunidades hay?",
                "VERDE: Que alternativas creativas se te ocurren?",
                "AZUL: Como organizamos el proceso de decision?",
            ],
            "steps": [
                "Presentar el tema o decision a analizar",
                "Recorrer cada sombrero secuencialmente",
                "Registrar insights de cada perspectiva",
                "Sintetizar en una decision informada",
            ],
            "keywords": [
                "decision", "analizar", "perspectiva", "evaluar", "pros",
                "contras", "riesgo", "oportunidad", "decidir", "analyze",
            ],
        },
        "mind_map": {
            "name": "Mapa Mental",
            "description": "Expansion radial desde un concepto central, ramificando en subtemas y conexiones",
            "prompts": [
                "Cual es el concepto central?",
                "Que subtemas principales se derivan?",
                "Que conexiones inesperadas ves entre ramas?",
                "Que detalles puedes agregar a cada rama?",
                "Que patron emerge del mapa completo?",
            ],
            "steps": [
                "Colocar el tema central",
                "Dibujar ramas principales (3-7 subtemas)",
                "Expandir cada rama con sub-ramas",
                "Buscar conexiones cruzadas entre ramas",
                "Identificar clusters y patrones emergentes",
            ],
            "keywords": [
                "explorar", "expandir", "conectar", "tema", "concepto",
                "ramificar", "mapa", "idea", "explore", "brainstorm",
                "lluvia", "generar",
            ],
        },
        "what_if": {
            "name": "What-If (Escenarios Hipoteticos)",
            "description": "Generar ideas extremas preguntando 'que pasaria si...' con restricciones o cambios radicales",
            "prompts": [
                "Que pasaria si no tuvieras limitaciones de presupuesto?",
                "Que pasaria si tuvieras que hacerlo en 24 horas?",
                "Que pasaria si el usuario fuera un nino de 5 anos?",
                "Que pasaria si la tecnologia actual no existiera?",
                "Que pasaria si lo hicieras al reves?",
            ],
            "steps": [
                "Definir el desafio base",
                "Formular 5+ preguntas 'que pasaria si'",
                "Explorar cada escenario sin censura",
                "Extraer ideas aplicables de escenarios extremos",
            ],
            "keywords": [
                "imaginar", "hipotetico", "escenario", "radical", "extremo",
                "disruptivo", "imposible", "loco", "imagine", "what if",
                "inventar", "revolucionar",
            ],
        },
    }

    def __init__(self, method_name: str):
        config = self.METHODS.get(method_name, self.METHODS["mind_map"])
        self.method_name = method_name
        self.name = config["name"]
        self.description = config["description"]
        self.prompts = config["prompts"]
        self.steps = config["steps"]
        self.keywords = config["keywords"]

    @classmethod
    def detect_method(cls, text: str) -> str:
        """Detecta el metodo mas adecuado por keywords en el texto."""
        text_lower = text.lower()
        scores = {}
        for mname, config in cls.METHODS.items():
            hits = sum(1 for kw in config["keywords"] if kw in text_lower)
            scores[mname] = hits

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "mind_map"  # Default versatil
        return best

    @classmethod
    def get_all_methods(cls) -> list:
        return list(cls.METHODS.keys())


# ── IdeaEntry ────────────────────────────────────────────────────────

class IdeaEntry:
    """Entrada de idea con scoring multidimensional."""

    def __init__(self, content: str, method: str = "",
                 tags: list = None):
        self.idea_id = int(time.time() * 1000) % 1000000  # ID unico simple
        self.content = content
        self.method = method
        self.tags = tags or []
        self.score = {"viability": 0.5, "novelty": 0.5, "impact": 0.5}
        self.overall = 0.5
        self.timestamp = time.time()

    def set_score(self, viability: float, novelty: float, impact: float):
        """Establece scores y calcula overall."""
        self.score["viability"] = max(0.0, min(1.0, viability))
        self.score["novelty"] = max(0.0, min(1.0, novelty))
        self.score["impact"] = max(0.0, min(1.0, impact))
        # Weighted average: viability 0.4, novelty 0.3, impact 0.3
        self.overall = (
            self.score["viability"] * 0.4 +
            self.score["novelty"] * 0.3 +
            self.score["impact"] * 0.3
        )

    def summary(self) -> str:
        tags_str = ", ".join(self.tags[:3]) if self.tags else "sin tags"
        return (f"[{self.overall:.0%}] {self.content[:60]}... "
                f"({tags_str})")

    def to_dict(self) -> dict:
        return {
            "idea_id": self.idea_id,
            "content": self.content,
            "method": self.method,
            "tags": self.tags,
            "score": self.score,
            "overall": round(self.overall, 3),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "IdeaEntry":
        ie = cls(
            content=d["content"],
            method=d.get("method", ""),
            tags=d.get("tags", []),
        )
        ie.idea_id = d.get("idea_id", ie.idea_id)
        ie.score = d.get("score", {"viability": 0.5, "novelty": 0.5, "impact": 0.5})
        ie.overall = d.get("overall", 0.5)
        ie.timestamp = d.get("timestamp", time.time())
        return ie


# ── IdeaScorer ───────────────────────────────────────────────────────

class IdeaScorer:
    """Scoring automatico de ideas por senales lexicas."""

    # Senales que indican alta viabilidad (tecnicas, concretas)
    VIABILITY_SIGNALS = [
        "implementar", "codigo", "herramienta", "framework", "api",
        "base de datos", "servidor", "automatizar", "script", "funcion",
        "metodo", "algoritmo", "proceso", "sistema", "integrate",
        "build", "deploy", "test", "tool", "platform", "paso a paso",
    ]

    # Senales que indican alta novedad (creativas, inusuales)
    NOVELTY_SIGNALS = [
        "nuevo", "nunca", "innovador", "diferente", "unico", "original",
        "revolucionario", "disruptivo", "inedito", "creativo", "novel",
        "unprecedented", "creative", "unconventional", "fresh", "hybrid",
        "combinar", "fusionar", "reimaginar", "inverso",
    ]

    # Senales que indican alto impacto (escala, afecta muchos)
    IMPACT_SIGNALS = [
        "todos", "global", "industria", "millones", "escala", "masivo",
        "transformar", "cambiar", "revolucionar", "mercado", "mundo",
        "comunidad", "sociedad", "everyone", "worldwide", "scale",
        "impacto", "afectar", "mejorar vidas", "accesible",
    ]

    def score(self, content: str, tags: list = None) -> dict:
        """Calcula scores para una idea.

        Retorna dict con viability, novelty, impact y overall.
        """
        text = content.lower()
        if tags:
            text += " " + " ".join(tags).lower()

        # Calcular cada dimension
        viability = self._dimension_score(text, self.VIABILITY_SIGNALS)
        novelty = self._dimension_score(text, self.NOVELTY_SIGNALS)
        impact = self._dimension_score(text, self.IMPACT_SIGNALS)

        # Overall: weighted average
        overall = viability * 0.4 + novelty * 0.3 + impact * 0.3

        return {
            "viability": round(viability, 3),
            "novelty": round(novelty, 3),
            "impact": round(impact, 3),
            "overall": round(overall, 3),
        }

    def _dimension_score(self, text: str, signals: list) -> float:
        """Calcula score de una dimension (0-1) por cantidad de senales."""
        hits = sum(1 for s in signals if s in text)
        if hits == 0:
            return 0.3  # Base minima
        # Saturacion logaritmica: 1 hit=0.5, 2=0.65, 3=0.75, 5+=0.85+
        raw = 0.3 + 0.15 * math.log2(1 + hits)
        return min(1.0, raw)


# ── IdeaBrainstormer (Coordinador) ──────────────────────────────────

class IdeaBrainstormer:
    """Coordinador de ideacion divergente con persistencia."""

    def __init__(self, base_dir: str = "data/idea_brainstormer"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.ideas = []             # Lista de idea dicts
        self.sessions = []          # Lista de session dicts
        self.total_ideas = 0
        self.total_sessions = 0
        self.scorer = IdeaScorer()

        self._load()

    def brainstorm(self, topic: str, method: str = "auto") -> dict:
        """Inicia una sesion de brainstorming sobre un tema.

        Si method="auto", detecta el metodo mas adecuado por keywords.
        Retorna dict con el outline de la sesion.
        """
        if method == "auto":
            method = BrainstormMethod.detect_method(topic)

        bm = BrainstormMethod(method)

        session = {
            "id": self.total_sessions,
            "topic": topic,
            "method": method,
            "method_name": bm.name,
            "idea_ids": [],
            "created_at": time.time(),
            "last_updated": time.time(),
        }

        self.sessions.append(session)
        self.total_sessions += 1

        return {
            "session_id": session["id"],
            "topic": topic,
            "method": bm.name,
            "description": bm.description,
            "prompts": bm.prompts,
            "steps": bm.steps,
        }

    def add_idea(self, content: str, method: str = "",
                 tags: list = None) -> dict:
        """Agrega una idea con auto-scoring.

        Si hay sesion activa, la vincula automaticamente.
        """
        # Auto-score
        scores = self.scorer.score(content, tags)

        idea = IdeaEntry(content, method, tags)
        idea.set_score(scores["viability"], scores["novelty"], scores["impact"])

        idea_dict = idea.to_dict()
        self.ideas.append(idea_dict)
        self.total_ideas += 1

        # Vincular a la sesion activa (la ultima)
        if self.sessions:
            self.sessions[-1]["idea_ids"].append(idea.idea_id)
            self.sessions[-1]["last_updated"] = time.time()

        return {
            "idea_id": idea.idea_id,
            "content": content[:80],
            "scores": scores,
            "overall": scores["overall"],
            "tags": tags or [],
            "total_ideas": self.total_ideas,
        }

    def get_best_ideas(self, n: int = 5) -> list:
        """Retorna las top N ideas por overall score."""
        if not self.ideas:
            return []

        sorted_ideas = sorted(self.ideas,
                               key=lambda x: x.get("overall", 0),
                               reverse=True)

        results = []
        for idea_dict in sorted_ideas[:n]:
            ie = IdeaEntry.from_dict(idea_dict)
            results.append({
                "idea_id": ie.idea_id,
                "content": ie.content,
                "overall": ie.overall,
                "scores": ie.score,
                "tags": ie.tags,
                "method": ie.method,
            })
        return results

    def combine_ideas(self, id1: int, id2: int) -> dict:
        """Combina dos ideas existentes en una nueva idea hibrida."""
        idea1 = None
        idea2 = None

        for idea_dict in self.ideas:
            if idea_dict.get("idea_id") == id1:
                idea1 = IdeaEntry.from_dict(idea_dict)
            if idea_dict.get("idea_id") == id2:
                idea2 = IdeaEntry.from_dict(idea_dict)

        if not idea1 or not idea2:
            return {"error": "Una o ambas ideas no encontradas"}

        # Combinar contenido
        combined_content = (
            f"Combinacion de: [{idea1.content[:50]}] + [{idea2.content[:50]}]. "
            f"Idea hibrida que fusiona ambos conceptos."
        )

        # Tags combinados (sin duplicados)
        combined_tags = list(set(idea1.tags + idea2.tags + ["combinada"]))

        # Score combinado: promedio ponderado favoreciendo la mejor
        best_v = max(idea1.score["viability"], idea2.score["viability"])
        best_n = max(idea1.score["novelty"], idea2.score["novelty"])
        best_i = max(idea1.score["impact"], idea2.score["impact"])
        # Bonus de novedad por ser combinacion
        boost_n = min(1.0, best_n + 0.1)

        new_idea = IdeaEntry(combined_content, "combination", combined_tags)
        new_idea.set_score(best_v, boost_n, best_i)

        idea_dict = new_idea.to_dict()
        self.ideas.append(idea_dict)
        self.total_ideas += 1

        # Vincular a sesion activa
        if self.sessions:
            self.sessions[-1]["idea_ids"].append(new_idea.idea_id)
            self.sessions[-1]["last_updated"] = time.time()

        return {
            "idea_id": new_idea.idea_id,
            "content": combined_content,
            "scores": new_idea.score,
            "overall": new_idea.overall,
            "source_ids": [id1, id2],
            "tags": combined_tags,
        }

    def get_context_for_prompt(self, user_input: str = "",
                                max_chars: int = 400) -> str:
        """Si se detecta brainstorming, inyecta las mejores ideas como contexto."""
        if not self.ideas:
            return ""

        # Detectar si el input es relevante a brainstorming
        brainstorm_keywords = [
            "idea", "brainstorm", "lluvia", "pensar", "crear", "creativ",
            "innovar", "propuesta", "concepto", "generar", "inventar",
            "sugerencia", "alternativa", "opcion", "posibilidad",
        ]
        if user_input:
            input_lower = user_input.lower()
            relevant = any(kw in input_lower for kw in brainstorm_keywords)
            if not relevant:
                return ""

        best = self.get_best_ideas(3)
        if not best:
            return ""

        parts = [f"[CONTEXTO BRAINSTORM] {self.total_ideas} ideas registradas"]

        # Sesion activa
        if self.sessions:
            last_session = self.sessions[-1]
            parts.append(f"Sesion: '{last_session['topic']}' ({last_session['method_name']})")

        # Top ideas
        parts.append("Top ideas:")
        for idea in best:
            parts.append(f"  - [{idea['overall']:.0%}] {idea['content'][:50]}")

        context = ". ".join(parts[:2]) + "\n" + "\n".join(parts[2:])
        return context[:max_chars]

    def get_stats(self) -> dict:
        avg_score = 0.0
        if self.ideas:
            avg_score = sum(i.get("overall", 0) for i in self.ideas) / len(self.ideas)

        active_topic = ""
        active_method = ""
        if self.sessions:
            active_topic = self.sessions[-1]["topic"]
            active_method = self.sessions[-1].get("method_name", "")

        return {
            "total_ideas": self.total_ideas,
            "total_sessions": self.total_sessions,
            "average_score": round(avg_score, 3),
            "active_session_topic": active_topic,
            "active_session_method": active_method,
        }

    def status(self) -> str:
        stats = self.get_stats()
        if stats["active_session_topic"]:
            return (f"  Ideas: {stats['total_ideas']} | "
                    f"Sesiones: {stats['total_sessions']} | "
                    f"Score promedio: {stats['average_score']:.0%} | "
                    f"Activa: '{stats['active_session_topic']}' "
                    f"({stats['active_session_method']})")
        return (f"  Ideas: {stats['total_ideas']} | "
                f"Sesiones: {stats['total_sessions']} | "
                f"Sin sesion activa")

    def generate_report(self) -> str:
        lines = [
            "=== IDEA BRAINSTORMER ===",
            f"Total ideas: {self.total_ideas}",
            f"Total sesiones: {self.total_sessions}",
            "",
        ]

        if not self.ideas:
            lines.append("No hay ideas registradas.")
            return "\n".join(lines)

        # Sesiones
        if self.sessions:
            lines.append("Sesiones:")
            for s in self.sessions:
                n_ideas = len(s.get("idea_ids", []))
                lines.append(f"  [{s['id']}] '{s['topic']}' ({s['method_name']}) "
                             f"— {n_ideas} ideas")
            lines.append("")

        # Top ideas
        best = self.get_best_ideas(10)
        if best:
            lines.append("Top ideas por score:")
            for rank, idea in enumerate(best, 1):
                v = idea["scores"].get("viability", 0)
                n = idea["scores"].get("novelty", 0)
                imp = idea["scores"].get("impact", 0)
                lines.append(
                    f"  {rank}. [{idea['overall']:.0%}] {idea['content'][:70]}"
                )
                lines.append(
                    f"     Viabilidad: {v:.0%} | Novedad: {n:.0%} | Impacto: {imp:.0%}"
                )

        # Distribucion de scores
        if self.ideas:
            high = sum(1 for i in self.ideas if i.get("overall", 0) >= 0.7)
            mid = sum(1 for i in self.ideas if 0.4 <= i.get("overall", 0) < 0.7)
            low = sum(1 for i in self.ideas if i.get("overall", 0) < 0.4)
            lines.append(f"\nDistribucion de scores:")
            lines.append(f"  Alta (70%+): {high} ideas")
            lines.append(f"  Media (40-69%): {mid} ideas")
            lines.append(f"  Baja (<40%): {low} ideas")

        return "\n".join(lines)

    def save(self):
        data = {
            "ideas": self.ideas,
            "sessions": self.sessions,
            "total_ideas": self.total_ideas,
            "total_sessions": self.total_sessions,
        }
        path = self.base_dir / "idea_brainstormer.json"
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "idea_brainstormer.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.ideas = data.get("ideas", [])
            self.sessions = data.get("sessions", [])
            self.total_ideas = data.get("total_ideas", 0)
            self.total_sessions = data.get("total_sessions", 0)
        except Exception:
            pass

    def clear(self):
        self.ideas = []
        self.sessions = []
        self.total_ideas = 0
        self.total_sessions = 0
        self.save()
