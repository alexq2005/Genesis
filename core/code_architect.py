"""
GENESIS — Code Architect (v3.2) "Creative Genesis"

Diseno de sistemas de software. Analiza requerimientos, sugiere patrones
arquitectonicos y gestiona componentes y decisiones de diseno.
Mantiene historial de decisiones arquitectonicas con razonamiento.

Componentes:
- ArchitecturePattern: patrones arquitectonicos con pros/contras
- ComponentSpec: especificacion de componente de software
- DesignDecision: decision arquitectonica con razonamiento
- CodeArchitect: coordinador con persistencia
"""
import time
import json
import re
from pathlib import Path
from collections import defaultdict


# ── ArchitecturePattern ──────────────────────────────────────────────

class ArchitecturePattern:
    """Patron arquitectonico con descripcion, pros/contras y casos de uso."""

    PATTERNS = {
        "mvc": {
            "name": "Model-View-Controller",
            "description": "Separacion en modelo de datos, vista de presentacion y controlador de logica",
            "pros": [
                "Separacion clara de responsabilidades",
                "Facilita testing unitario del modelo",
                "Multiples vistas para el mismo modelo",
                "Familiar para la mayoria de desarrolladores",
            ],
            "cons": [
                "Puede generar controladores masivos (fat controllers)",
                "Acoplamiento indirecto entre vista y modelo",
                "No escala bien para dominios muy complejos",
            ],
            "best_for": "Aplicaciones web, APIs REST, CRUD con UI",
            "keywords": [
                "web", "api", "rest", "crud", "frontend", "backend",
                "pagina", "vista", "formulario", "interfaz", "ui",
            ],
        },
        "microservices": {
            "name": "Microservicios",
            "description": "Sistema distribuido de servicios independientes comunicados por mensajes o APIs",
            "pros": [
                "Escalado independiente por servicio",
                "Despliegue independiente",
                "Equipos autonomos por servicio",
                "Tolerancia a fallos por aislamiento",
            ],
            "cons": [
                "Complejidad operacional alta (orquestacion, monitoreo)",
                "Latencia de red entre servicios",
                "Consistencia eventual vs. transaccional",
                "Requiere infraestructura madura (Docker, K8s)",
            ],
            "best_for": "Sistemas grandes, equipos multiples, alta escalabilidad",
            "keywords": [
                "microservicio", "distribuido", "escalar", "docker", "kubernetes",
                "servicio", "api gateway", "independiente", "equipo",
                "deploy", "scale", "distributed", "service",
            ],
        },
        "event_driven": {
            "name": "Arquitectura Dirigida por Eventos",
            "description": "Componentes se comunican mediante eventos asincrónicos a traves de un bus de mensajes",
            "pros": [
                "Desacoplamiento total entre productores y consumidores",
                "Alta escalabilidad horizontal",
                "Procesamiento asincrono natural",
                "Facilita integracion de sistemas heterogeneos",
            ],
            "cons": [
                "Dificil de debuggear (flujo no lineal)",
                "Consistencia eventual obligatoria",
                "Complejidad en el ordenamiento de eventos",
            ],
            "best_for": "Sistemas reactivos, IoT, procesamiento de streams, notificaciones",
            "keywords": [
                "evento", "event", "mensaje", "queue", "kafka", "rabbit",
                "asincrono", "async", "stream", "notificacion", "real-time",
                "reactivo", "bus", "publish", "subscribe",
            ],
        },
        "layered": {
            "name": "Arquitectura en Capas",
            "description": "Organizacion en capas horizontales (presentacion, logica, datos) con dependencia unidireccional",
            "pros": [
                "Simple y facil de entender",
                "Separacion clara por responsabilidad",
                "Patron mas comun, facil de contratar equipo",
                "Bueno para proyectos pequenos y medianos",
            ],
            "cons": [
                "Puede generar capas innecesarias (over-engineering)",
                "Cambios pueden requerir modificar multiples capas",
                "No optimiza para rendimiento (pasar por todas las capas)",
            ],
            "best_for": "Aplicaciones empresariales clasicas, proyectos simples",
            "keywords": [
                "capas", "layer", "simple", "clasico", "tradicional",
                "monolito", "empresarial", "enterprise", "basico",
                "principiante", "pequeno", "rapido",
            ],
        },
        "hexagonal": {
            "name": "Arquitectura Hexagonal (Ports & Adapters)",
            "description": "Nucleo de dominio aislado con puertos de entrada/salida y adaptadores intercambiables",
            "pros": [
                "Dominio totalmente aislado de infraestructura",
                "Altamente testeable (mocks en puertos)",
                "Adaptadores intercambiables (DB, API, UI)",
                "Excelente para DDD (Domain-Driven Design)",
            ],
            "cons": [
                "Curva de aprendizaje alta",
                "Mas codigo boilerplate (interfaces, adaptadores)",
                "Over-engineering para proyectos simples",
            ],
            "best_for": "Dominios complejos, DDD, sistemas que cambian de infraestructura",
            "keywords": [
                "hexagonal", "ports", "adapters", "ddd", "domain",
                "dominio", "clean", "limpia", "aislado", "testeable",
                "solid", "puertos", "adaptadores",
            ],
        },
    }

    def __init__(self, pattern_name: str):
        config = self.PATTERNS.get(pattern_name, self.PATTERNS["layered"])
        self.pattern_name = pattern_name
        self.name = config["name"]
        self.description = config["description"]
        self.pros = config["pros"]
        self.cons = config["cons"]
        self.best_for = config["best_for"]
        self.keywords = config["keywords"]

    def summary(self) -> str:
        return f"{self.name}: {self.description} (ideal para: {self.best_for})"

    @classmethod
    def detect_pattern(cls, text: str) -> str:
        """Detecta el patron mas adecuado segun keywords en el texto."""
        text_lower = text.lower()
        scores = {}
        for pname, config in cls.PATTERNS.items():
            hits = sum(1 for kw in config["keywords"] if kw in text_lower)
            scores[pname] = hits

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "layered"  # Default seguro
        return best


# ── ComponentSpec ────────────────────────────────────────────────────

class ComponentSpec:
    """Especificacion de un componente de software."""

    VALID_TYPES = ["service", "controller", "model", "view", "util"]

    def __init__(self, name: str, comp_type: str = "service",
                 dependencies: list = None, description: str = ""):
        self.name = name
        self.comp_type = comp_type if comp_type in self.VALID_TYPES else "service"
        self.dependencies = dependencies or []
        self.description = description
        self.created_at = time.time()

    def summary(self) -> str:
        deps = ", ".join(self.dependencies[:3]) if self.dependencies else "ninguna"
        return f"{self.name} [{self.comp_type}] -> deps: {deps}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "comp_type": self.comp_type,
            "dependencies": self.dependencies,
            "description": self.description,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ComponentSpec":
        cs = cls(
            name=d["name"],
            comp_type=d.get("comp_type", "service"),
            dependencies=d.get("dependencies", []),
            description=d.get("description", ""),
        )
        cs.created_at = d.get("created_at", time.time())
        return cs


# ── DesignDecision ───────────────────────────────────────────────────

class DesignDecision:
    """Decision arquitectonica con razonamiento y alternativas."""

    def __init__(self, decision: str, rationale: str = "",
                 alternatives: list = None):
        self.decision = decision
        self.rationale = rationale
        self.alternatives = alternatives or []
        self.chosen_at = time.time()

    def summary(self) -> str:
        alts = f" (alternativas: {', '.join(self.alternatives[:2])})" if self.alternatives else ""
        return f"{self.decision}{alts} — {self.rationale[:60]}"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "chosen_at": self.chosen_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DesignDecision":
        dd = cls(
            decision=d["decision"],
            rationale=d.get("rationale", ""),
            alternatives=d.get("alternatives", []),
        )
        dd.chosen_at = d.get("chosen_at", time.time())
        return dd


# ── CodeArchitect (Coordinador) ─────────────────────────────────────

class CodeArchitect:
    """Coordinador de diseno de sistemas con persistencia."""

    def __init__(self, base_dir: str = "data/code_architect"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.designs = []           # Lista de design dicts
        self.current_design = -1    # Indice del diseno activo (-1 = ninguno)
        self.total_designs = 0
        self.total_components = 0
        self.total_decisions = 0

        self._load()

    def design_system(self, requirements: str) -> dict:
        """Analiza requerimientos y sugiere patron arquitectonico.

        Crea un nuevo diseno con el patron detectado.
        Retorna dict con el outline del diseno.
        """
        pattern_name = ArchitecturePattern.detect_pattern(requirements)
        pattern = ArchitecturePattern(pattern_name)

        design = {
            "id": self.total_designs,
            "name": self._generate_name(requirements),
            "requirements": requirements,
            "pattern": pattern_name,
            "pattern_description": pattern.description,
            "components": [],
            "decisions": [],
            "created_at": time.time(),
            "last_updated": time.time(),
        }

        self.designs.append(design)
        self.current_design = len(self.designs) - 1
        self.total_designs += 1

        return {
            "design_id": design["id"],
            "name": design["name"],
            "suggested_pattern": pattern.name,
            "pattern_key": pattern_name,
            "description": pattern.description,
            "pros": pattern.pros,
            "cons": pattern.cons,
            "best_for": pattern.best_for,
        }

    def _generate_name(self, requirements: str) -> str:
        """Genera nombre para el diseno desde los requerimientos."""
        words = re.findall(r'\b[a-zA-ZáéíóúñÁÉÍÓÚÑ]{3,}\b', requirements)
        significant = [w.capitalize() for w in words[:3]]
        if significant:
            return " ".join(significant) + " System"
        return f"System #{self.total_designs}"

    def add_component(self, name: str, comp_type: str = "service",
                      dependencies: list = None,
                      description: str = "") -> dict:
        """Agrega un componente al diseno activo."""
        if self.current_design < 0 or self.current_design >= len(self.designs):
            return {"error": "No hay diseno activo"}

        comp = ComponentSpec(name, comp_type, dependencies, description)
        design = self.designs[self.current_design]
        design["components"].append(comp.to_dict())
        design["last_updated"] = time.time()
        self.total_components += 1

        return {
            "name": comp.name,
            "type": comp.comp_type,
            "summary": comp.summary(),
            "component_count": len(design["components"]),
        }

    def record_decision(self, decision: str, rationale: str = "",
                        alternatives: list = None) -> dict:
        """Registra una decision arquitectonica en el diseno activo."""
        if self.current_design < 0 or self.current_design >= len(self.designs):
            return {"error": "No hay diseno activo"}

        dd = DesignDecision(decision, rationale, alternatives)
        design = self.designs[self.current_design]
        design["decisions"].append(dd.to_dict())
        design["last_updated"] = time.time()
        self.total_decisions += 1

        return {
            "decision": dd.decision,
            "summary": dd.summary(),
            "decision_count": len(design["decisions"]),
        }

    def get_context_for_prompt(self, user_input: str = "",
                                max_chars: int = 400) -> str:
        """Si se detecta pregunta de diseno, inyecta contexto del diseno activo."""
        if self.current_design < 0 or self.current_design >= len(self.designs):
            return ""

        # Detectar si el input es relevante a arquitectura/diseno
        design_keywords = [
            "arquitectura", "architecture", "diseno", "design", "patron",
            "pattern", "componente", "component", "servicio", "service",
            "modulo", "module", "capa", "layer", "api", "estructura",
            "dependencia", "dependency", "decision",
        ]
        if user_input:
            input_lower = user_input.lower()
            relevant = any(kw in input_lower for kw in design_keywords)
            if not relevant:
                return ""

        design = self.designs[self.current_design]
        pattern = ArchitecturePattern(design["pattern"])

        parts = [
            f"[CONTEXTO ARQUITECTONICO] Diseno: '{design['name']}' ({pattern.name})",
            f"Patron: {pattern.description}",
        ]

        # Componentes
        comps = design.get("components", [])
        if comps:
            comp_names = [c["name"] for c in comps[:5]]
            parts.append(f"Componentes: {', '.join(comp_names)}")

        # Ultima decision
        decisions = design.get("decisions", [])
        if decisions:
            last = DesignDecision.from_dict(decisions[-1])
            parts.append(f"Ultima decision: {last.decision}")

        context = ". ".join(parts)
        return context[:max_chars]

    def get_stats(self) -> dict:
        active_name = ""
        active_pattern = ""
        if 0 <= self.current_design < len(self.designs):
            d = self.designs[self.current_design]
            active_name = d["name"]
            active_pattern = d["pattern"]

        return {
            "total_designs": self.total_designs,
            "total_components": self.total_components,
            "total_decisions": self.total_decisions,
            "active_designs": len(self.designs),
            "current_design_name": active_name,
            "current_design_pattern": active_pattern,
        }

    def status(self) -> str:
        stats = self.get_stats()
        if stats["current_design_name"]:
            d = self.designs[self.current_design]
            n_comp = len(d.get("components", []))
            n_dec = len(d.get("decisions", []))
            return (f"  Disenos: {stats['total_designs']} | "
                    f"Activo: '{stats['current_design_name']}' "
                    f"({stats['current_design_pattern']}) | "
                    f"Componentes: {n_comp} | Decisiones: {n_dec}")
        return (f"  Disenos: {stats['total_designs']} | "
                f"Componentes: {stats['total_components']} | "
                f"Sin diseno activo")

    def generate_report(self) -> str:
        lines = [
            "=== CODE ARCHITECT ===",
            f"Total disenos: {self.total_designs}",
            f"Total componentes: {self.total_components}",
            f"Total decisiones: {self.total_decisions}",
            "",
        ]

        if not self.designs:
            lines.append("No hay disenos registrados.")
            return "\n".join(lines)

        for i, design in enumerate(self.designs):
            pattern = ArchitecturePattern(design["pattern"])
            marker = " << ACTIVO" if i == self.current_design else ""
            lines.append(f"  [{i}] '{design['name']}' ({pattern.name}){marker}")

            comps = design.get("components", [])
            lines.append(f"      Componentes ({len(comps)}):")
            for c in comps[:8]:
                cs = ComponentSpec.from_dict(c)
                lines.append(f"        - {cs.summary()}")

            decs = design.get("decisions", [])
            if decs:
                lines.append(f"      Decisiones ({len(decs)}):")
                for d in decs[:5]:
                    dd = DesignDecision.from_dict(d)
                    lines.append(f"        * {dd.summary()}")

            lines.append("")

        return "\n".join(lines)

    def save(self):
        data = {
            "designs": self.designs,
            "current_design": self.current_design,
            "total_designs": self.total_designs,
            "total_components": self.total_components,
            "total_decisions": self.total_decisions,
        }
        path = self.base_dir / "code_architect.json"
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        except Exception:
            pass

    def _load(self):
        path = self.base_dir / "code_architect.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.designs = data.get("designs", [])
            self.current_design = data.get("current_design", -1)
            self.total_designs = data.get("total_designs", 0)
            self.total_components = data.get("total_components", 0)
            self.total_decisions = data.get("total_decisions", 0)
        except Exception:
            pass

    def clear(self):
        self.designs = []
        self.current_design = -1
        self.total_designs = 0
        self.total_components = 0
        self.total_decisions = 0
        self.save()
