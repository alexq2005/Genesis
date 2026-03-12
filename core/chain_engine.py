"""
GENESIS — Conversation Chain Engine (v2.3)

Razonamiento multi-paso: descompone preguntas complejas en sub-preguntas,
ejecuta cada paso secuencialmente, y recuerda cadenas exitosas.

Componentes:
- ChainPlanner: Decide si una pregunta necesita chain y la descompone
- StepExecutor: Ejecuta cada paso alimentando contexto al siguiente
- ChainMemory: Recuerda cadenas exitosas para reutilización
- ChainEngine: Coordinador principal
"""
import time
import json
import re
import hashlib
from pathlib import Path


class ChainStep:
    """Un paso dentro de una cadena de razonamiento."""

    def __init__(self, question: str, step_number: int, depends_on: list = None):
        self.question = question
        self.step_number = step_number
        self.depends_on = depends_on or []
        self.answer = ""
        self.status = "pending"  # pending, running, completed, failed
        self.elapsed_ms = 0

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "step_number": self.step_number,
            "depends_on": self.depends_on,
            "answer": self.answer[:500],
            "status": self.status,
            "elapsed_ms": self.elapsed_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChainStep":
        step = cls(
            question=data["question"],
            step_number=data["step_number"],
            depends_on=data.get("depends_on", []),
        )
        step.answer = data.get("answer", "")
        step.status = data.get("status", "pending")
        step.elapsed_ms = data.get("elapsed_ms", 0)
        return step


class Chain:
    """Una cadena completa de razonamiento."""

    def __init__(self, original_query: str, steps: list = None, chain_id: str = None):
        self.chain_id = chain_id or hashlib.md5(
            f"{original_query}{time.time()}".encode()
        ).hexdigest()[:10]
        self.original_query = original_query
        self.steps = steps or []
        self.created_at = time.time()
        self.completed_at = 0
        self.status = "pending"  # pending, running, completed, failed
        self.final_answer = ""

    @property
    def is_complete(self) -> bool:
        return all(s.status == "completed" for s in self.steps)

    @property
    def current_step(self) -> int:
        for s in self.steps:
            if s.status in ("pending", "running"):
                return s.step_number
        return len(self.steps)

    def get_context_so_far(self) -> str:
        """Genera contexto acumulado de los pasos completados."""
        lines = []
        for s in self.steps:
            if s.status == "completed" and s.answer:
                lines.append(f"[Paso {s.step_number}] {s.question}")
                lines.append(f"Resultado: {s.answer[:300]}")
                lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.chain_id,
            "original_query": self.original_query,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "final_answer": self.final_answer[:1000],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chain":
        chain = cls(
            original_query=data["original_query"],
            chain_id=data.get("id"),
        )
        chain.steps = [ChainStep.from_dict(s) for s in data.get("steps", [])]
        chain.created_at = data.get("created_at", time.time())
        chain.completed_at = data.get("completed_at", 0)
        chain.status = data.get("status", "pending")
        chain.final_answer = data.get("final_answer", "")
        return chain


class ChainPlanner:
    """
    Decide si una pregunta necesita razonamiento multi-paso
    y la descompone en sub-preguntas.
    """

    # Indicadores de pregunta compleja que necesita chain
    COMPLEXITY_INDICATORS = [
        r'compara\s+.+\s+(?:con|vs|versus|y)\s+',
        r'(?:ventajas|desventajas|pros|contras)\s+(?:de|y)',
        r'(?:analiza|analizar|analisis)\s+(?:de|del|la|el)',
        r'(?:diseña|diseñar|arquitectura)\s+(?:de|para|un)',
        r'(?:optimiza|optimizar|mejorar)\s+',
        r'(?:explica|explicar)\s+(?:como|por que|por qué)\s+',
        r'(?:que diferencia|cual es la diferencia|diferencias entre)',
        r'(?:paso a paso|step by step)',
        r'(?:completo|detallado|exhaustivo|profundo)',
        r'(?:multiple|varios|diferentes)\s+(?:aspectos|factores|componentes)',
    ]

    # Patrones para descomponer (templates de sub-preguntas)
    DECOMPOSITION_TEMPLATES = {
        "compare": [
            "Describe brevemente {A}",
            "Describe brevemente {B}",
            "Compara las características principales de {A} vs {B}",
            "Conclusión: ¿cuál es mejor y para qué casos?",
        ],
        "analyze": [
            "¿Qué es {topic} y cuál es su contexto?",
            "¿Cuáles son los componentes principales de {topic}?",
            "¿Cuáles son las fortalezas y debilidades de {topic}?",
            "Conclusión y recomendaciones sobre {topic}",
        ],
        "optimize": [
            "¿Cuál es el estado actual de {target}?",
            "¿Cuáles son los cuellos de botella o problemas de {target}?",
            "¿Qué técnicas de optimización aplican a {target}?",
            "Plan de acción concreto para optimizar {target}",
        ],
        "explain_why": [
            "¿Qué es {topic}?",
            "¿Cuáles son las causas o mecanismos de {topic}?",
            "¿Qué consecuencias o implicaciones tiene?",
        ],
        "design": [
            "¿Cuáles son los requisitos de {target}?",
            "¿Qué patrones o arquitecturas aplican a {target}?",
            "Diseño propuesto para {target}",
            "Consideraciones de implementación y posibles problemas",
        ],
        "generic": [
            "Contexto: ¿qué sabemos sobre {topic}?",
            "Análisis: aspectos clave de {topic}",
            "Síntesis: conclusión sobre {topic}",
        ],
    }

    def needs_chain(self, user_input: str) -> bool:
        """Decide si una pregunta necesita razonamiento multi-paso."""
        if len(user_input) < 20:
            return False

        input_lower = user_input.lower()

        # Contar indicadores de complejidad
        complexity_score = sum(
            1 for p in self.COMPLEXITY_INDICATORS
            if re.search(p, input_lower)
        )

        # Longitud también indica complejidad
        if len(user_input) > 100:
            complexity_score += 1

        return complexity_score >= 2

    def plan(self, user_input: str) -> Chain:
        """
        Descompone una pregunta en una cadena de sub-preguntas.
        Usa heurísticas para elegir el template correcto.
        """
        input_lower = user_input.lower()

        # Detectar tipo de pregunta
        chain_type = self._detect_type(input_lower)

        # Extraer topic/entities
        topic = self._extract_topic(user_input)

        # Generar steps desde template
        template = self.DECOMPOSITION_TEMPLATES.get(
            chain_type, self.DECOMPOSITION_TEMPLATES["generic"]
        )

        steps = []
        for i, tmpl in enumerate(template, 1):
            question = tmpl.format(
                topic=topic, target=topic,
                A=self._extract_entity_a(user_input),
                B=self._extract_entity_b(user_input),
            )
            step = ChainStep(
                question=question,
                step_number=i,
                depends_on=list(range(1, i)),
            )
            steps.append(step)

        chain = Chain(original_query=user_input, steps=steps)
        return chain

    def _detect_type(self, input_lower: str) -> str:
        """Detecta el tipo de pregunta para elegir template."""
        if re.search(r'compara|vs|versus|diferencia', input_lower):
            return "compare"
        elif re.search(r'analiza|analisis|evalua', input_lower):
            return "analyze"
        elif re.search(r'optimiza|mejorar|rendimiento', input_lower):
            return "optimize"
        elif re.search(r'por que|por qué|why|causa', input_lower):
            return "explain_why"
        elif re.search(r'diseña|arquitectura|diseño|estructura', input_lower):
            return "design"
        return "generic"

    def _extract_topic(self, user_input: str) -> str:
        """Extrae el tema principal de la pregunta."""
        # Remover palabras de pregunta comunes
        clean = re.sub(
            r'^(compara|analiza|explica|diseña|optimiza|como|que es|por que)\s+',
            '', user_input.lower().strip()
        )
        clean = re.sub(r'[?¿!¡]', '', clean).strip()
        return clean[:100] if clean else user_input[:100]

    def _extract_entity_a(self, user_input: str) -> str:
        """Extrae primera entidad en una comparación."""
        match = re.search(
            r'(?:compara|entre)\s+(.+?)\s+(?:con|vs|versus|y)\s+',
            user_input, re.IGNORECASE,
        )
        return match.group(1).strip() if match else "A"

    def _extract_entity_b(self, user_input: str) -> str:
        """Extrae segunda entidad en una comparación."""
        match = re.search(
            r'(?:con|vs|versus|y)\s+(.+?)(?:\?|$)',
            user_input, re.IGNORECASE,
        )
        return match.group(1).strip() if match else "B"


class ChainMemory:
    """
    Recuerda cadenas de razonamiento exitosas para reutilización.
    """

    def __init__(self, max_chains: int = 50):
        self.max_chains = max_chains
        self.chains = {}  # chain_id -> Chain

    def store(self, chain: Chain):
        """Almacena una cadena completada."""
        if chain.status != "completed":
            return
        self.chains[chain.chain_id] = chain
        if len(self.chains) > self.max_chains:
            self._evict()

    def find_similar(self, query: str) -> Chain:
        """Busca una cadena similar a la query."""
        query_words = set(
            w.lower() for w in re.findall(r'\b\w+\b', query) if len(w) > 3
        )
        if not query_words:
            return None

        best_score = 0
        best_chain = None

        for chain in self.chains.values():
            chain_words = set(
                w.lower() for w in re.findall(r'\b\w+\b', chain.original_query)
                if len(w) > 3
            )
            if not chain_words:
                continue
            overlap = len(query_words & chain_words)
            score = overlap / max(len(query_words), 1)
            if score > best_score and score >= 0.5:
                best_score = score
                best_chain = chain

        return best_chain

    def _evict(self):
        """Elimina cadenas más antiguas."""
        if len(self.chains) <= self.max_chains:
            return
        sorted_chains = sorted(
            self.chains.items(),
            key=lambda x: x[1].completed_at,
        )
        to_remove = len(self.chains) - self.max_chains + 5
        for cid, _ in sorted_chains[:to_remove]:
            del self.chains[cid]

    def to_dict(self) -> dict:
        return {
            cid: c.to_dict() for cid, c in self.chains.items()
        }

    def load_dict(self, data: dict):
        for cid, cdata in data.items():
            self.chains[cid] = Chain.from_dict(cdata)


class ChainEngine:
    """
    Motor de cadenas de razonamiento.
    Coordina planificación, ejecución, y memoria.
    """

    def __init__(self, base_dir: str = None):
        self.planner = ChainPlanner()
        self.memory = ChainMemory()

        self.base_dir = Path(base_dir) if base_dir else Path("data/chain_engine")
        self.data_file = self.base_dir / "chains.json"
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.active_chain = None  # Chain actualmente en ejecución
        self.total_chains = 0
        self.total_steps_executed = 0
        self.enabled = True

        self._load()

    def should_chain(self, user_input: str) -> bool:
        """Decide si activar razonamiento en cadena."""
        if not self.enabled:
            return False
        if self.active_chain and self.active_chain.status == "running":
            return False  # Ya hay una cadena activa
        return self.planner.needs_chain(user_input)

    def start_chain(self, user_input: str) -> Chain:
        """
        Inicia una cadena de razonamiento.
        Retorna la Chain con los pasos planificados.
        """
        # Buscar cadena similar existente
        similar = self.memory.find_similar(user_input)
        if similar:
            # Reutilizar estructura pero con nueva query
            chain = Chain(original_query=user_input)
            for s in similar.steps:
                # Adaptar preguntas al nuevo contexto
                adapted_q = s.question  # Podría adaptarse más
                chain.steps.append(ChainStep(
                    question=adapted_q,
                    step_number=s.step_number,
                    depends_on=s.depends_on,
                ))
        else:
            chain = self.planner.plan(user_input)

        chain.status = "running"
        self.active_chain = chain
        self.total_chains += 1
        return chain

    def get_next_step(self) -> ChainStep:
        """Retorna el siguiente paso pendiente de la cadena activa."""
        if not self.active_chain:
            return None
        for step in self.active_chain.steps:
            if step.status == "pending":
                return step
        return None

    def complete_step(self, step_number: int, answer: str, elapsed_ms: float = 0):
        """Marca un paso como completado con su respuesta."""
        if not self.active_chain:
            return
        for step in self.active_chain.steps:
            if step.step_number == step_number:
                step.answer = answer
                step.status = "completed"
                step.elapsed_ms = elapsed_ms
                self.total_steps_executed += 1
                break

        # Verificar si toda la cadena está completa
        if self.active_chain.is_complete:
            self.active_chain.status = "completed"
            self.active_chain.completed_at = time.time()
            # Generar respuesta final combinando pasos
            self.active_chain.final_answer = self._synthesize(self.active_chain)
            # Almacenar en memoria
            self.memory.store(self.active_chain)
            self.save()

    def get_chain_prompt(self, step: ChainStep) -> str:
        """
        Genera el prompt para un paso de la cadena,
        incluyendo contexto de pasos anteriores.
        """
        if not self.active_chain:
            return step.question

        lines = [
            "Estoy analizando una pregunta compleja paso a paso.",
            f"Pregunta original: {self.active_chain.original_query}",
            "",
        ]

        # Agregar contexto de pasos anteriores
        context = self.active_chain.get_context_so_far()
        if context:
            lines.append("Pasos anteriores:")
            lines.append(context)

        lines.append(f"Ahora responde el paso {step.step_number}: {step.question}")
        lines.append("Se conciso y directo (max 200 palabras).")

        return "\n".join(lines)

    def _synthesize(self, chain: Chain) -> str:
        """Sintetiza las respuestas de todos los pasos en una respuesta final."""
        lines = [f"Análisis de: {chain.original_query}", ""]
        for step in chain.steps:
            if step.answer:
                lines.append(f"**{step.question}**")
                lines.append(step.answer[:500])
                lines.append("")
        return "\n".join(lines)

    def cancel_chain(self):
        """Cancela la cadena activa."""
        if self.active_chain:
            self.active_chain.status = "failed"
            self.active_chain = None

    def get_stats(self) -> dict:
        return {
            "total_chains": self.total_chains,
            "total_steps_executed": self.total_steps_executed,
            "chains_memorized": len(self.memory.chains),
            "active": self.active_chain is not None and self.active_chain.status == "running",
            "enabled": self.enabled,
        }

    def status(self) -> str:
        """Status string para /status."""
        active_info = "ninguna"
        if self.active_chain and self.active_chain.status == "running":
            active_info = (f"paso {self.active_chain.current_step}/"
                          f"{len(self.active_chain.steps)}")
        lines = [
            f"  Cadenas ejecutadas: {self.total_chains}",
            f"  Pasos totales: {self.total_steps_executed}",
            f"  Memorizadas: {len(self.memory.chains)}",
            f"  Cadena activa: {active_info}",
            f"  Habilitado: {'si' if self.enabled else 'no'}",
        ]
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Reporte completo para /chain."""
        lines = ["=== CHAIN ENGINE ===", ""]
        lines.append(f"Cadenas ejecutadas: {self.total_chains}")
        lines.append(f"Pasos ejecutados: {self.total_steps_executed}")
        lines.append(f"Cadenas memorizadas: {len(self.memory.chains)}")
        lines.append(f"Estado: {'habilitado' if self.enabled else 'deshabilitado'}")
        lines.append("")

        # Cadena activa
        if self.active_chain and self.active_chain.status == "running":
            lines.append("CADENA ACTIVA:")
            lines.append(f"  Query: {self.active_chain.original_query[:100]}")
            for s in self.active_chain.steps:
                status_icon = {"pending": "[ ]", "running": "[>]",
                               "completed": "[x]", "failed": "[!]"}
                lines.append(f"  {status_icon.get(s.status, '[ ]')} "
                             f"Paso {s.step_number}: {s.question[:80]}")
            lines.append("")

        # Cadenas memorizadas
        if self.memory.chains:
            lines.append("CADENAS MEMORIZADAS:")
            for chain in sorted(
                self.memory.chains.values(),
                key=lambda c: c.completed_at, reverse=True
            )[:5]:
                n_steps = len(chain.steps)
                lines.append(f"  [{chain.chain_id}] {chain.original_query[:60]} "
                             f"({n_steps} pasos)")
            lines.append("")

        return "\n".join(lines)

    def save(self):
        """Persiste estado."""
        data = {
            "total_chains": self.total_chains,
            "total_steps_executed": self.total_steps_executed,
            "memory": self.memory.to_dict(),
            "enabled": self.enabled,
        }
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
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
            self.total_chains = data.get("total_chains", 0)
            self.total_steps_executed = data.get("total_steps_executed", 0)
            self.enabled = data.get("enabled", True)
            if "memory" in data:
                self.memory.load_dict(data["memory"])
        except Exception:
            pass

    def clear(self):
        """Resetea todo."""
        self.memory = ChainMemory()
        self.active_chain = None
        self.total_chains = 0
        self.total_steps_executed = 0
        if self.data_file.exists():
            self.data_file.unlink()
