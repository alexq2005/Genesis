"""
GENESIS — Sistema Multi-Agente
Permite que Genesis delegue tareas a agentes especializados.

Cada agente tiene:
- Rol y personalidad especializada (system prompt unico)
- Capacidades definidas (que tipo de tareas puede manejar)
- Temperatura optima para su tipo de trabajo
- Historial propio de interacciones

Agentes predefinidos:
- researcher: Busqueda y sintesis de informacion
- coder: Escritura y revision de codigo
- analyst: Analisis de datos y problemas
- creative: Escritura creativa y brainstorming
- security: Analisis de seguridad y vulnerabilidades
- planner: Planificacion y descomposicion de tareas

El Orchestrator decide que agente(s) usar segun la tarea.
Soporta pipelines: output de un agente → input de otro.

Uso:
    agents = AgentSystem(brain)
    result = agents.delegate("analiza este codigo y sugiere mejoras", context="def foo()...")
    result = agents.pipeline(["researcher", "analyst"], "investiga vulnerabilidades en Flask")
"""
import time
import re
from typing import Optional, List


# ============================================================
# Agent — agente individual
# ============================================================
class Agent:
    """Un agente especializado con rol, personalidad y capacidades."""

    def __init__(self, name: str, role: str, system_prompt: str,
                 capabilities: list = None, temperature: float = 0.7,
                 priority: int = 5):
        """
        Args:
            name: identificador unico del agente
            role: descripcion corta del rol
            system_prompt: instrucciones especializadas del agente
            capabilities: lista de tags que puede manejar
            temperature: temperatura optima para este agente
            priority: prioridad al resolver conflictos (mayor = mas prioridad)
        """
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.capabilities = capabilities or []
        self.temperature = temperature
        self.priority = priority
        self.enabled = True
        self.tasks_completed = 0
        self.total_time = 0.0
        self.last_used = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "temperature": self.temperature,
            "priority": self.priority,
            "enabled": self.enabled,
            "tasks_completed": self.tasks_completed,
            "avg_time": round(self.total_time / max(1, self.tasks_completed), 2),
        }


# ============================================================
# AgentSystem — orquestador multi-agente
# ============================================================
class AgentSystem:
    """
    Sistema que gestiona multiples agentes especializados.
    Decide automaticamente que agente usar y soporta pipelines.
    """

    # Agentes predefinidos
    DEFAULT_AGENTS = {
        "researcher": Agent(
            name="researcher",
            role="Investigador",
            system_prompt=(
                "Eres un investigador experto. Tu trabajo es buscar, sintetizar "
                "y presentar informacion de manera clara y estructurada. "
                "Siempre citas fuentes cuando es posible. Priorizas precision "
                "sobre velocidad. Si no sabes algo, lo dices directamente."
            ),
            capabilities=["research", "search", "summarize", "explain", "translate"],
            temperature=0.4,
            priority=7,
        ),
        "coder": Agent(
            name="coder",
            role="Programador",
            system_prompt=(
                "Eres un programador experto. Escribes codigo limpio, eficiente "
                "y bien documentado. Sigues las mejores practicas del lenguaje "
                "solicitado. Incluyes manejo de errores y consideras edge cases. "
                "Si detectas un bug, lo corriges y explicas por que."
            ),
            capabilities=["code", "debug", "refactor", "review", "test", "architecture"],
            temperature=0.3,
            priority=8,
        ),
        "analyst": Agent(
            name="analyst",
            role="Analista",
            system_prompt=(
                "Eres un analista experto. Descompones problemas complejos en "
                "partes manejables. Identificas patrones, riesgos y oportunidades. "
                "Presentas tus hallazgos con datos y razonamiento logico. "
                "Siempre consideras multiples perspectivas."
            ),
            capabilities=["analysis", "data", "reasoning", "comparison", "evaluation"],
            temperature=0.4,
            priority=6,
        ),
        "creative": Agent(
            name="creative",
            role="Creativo",
            system_prompt=(
                "Eres un escritor y pensador creativo. Generas ideas originales, "
                "escribes con estilo y personalidad. Puedes crear historias, "
                "poemas, guiones, nombres, slogans y cualquier contenido creativo. "
                "Tu estilo es unico y evita cliches."
            ),
            capabilities=["creative", "writing", "brainstorm", "storytelling", "naming"],
            temperature=0.9,
            priority=5,
        ),
        "security": Agent(
            name="security",
            role="Especialista en Seguridad",
            system_prompt=(
                "Eres un experto en ciberseguridad. Analizas codigo, sistemas "
                "y configuraciones en busca de vulnerabilidades. Conoces OWASP, "
                "CVEs, tecnicas de pentesting, criptografia y seguridad de redes. "
                "Das recomendaciones concretas y priorizas por severidad."
            ),
            capabilities=["security", "vulnerability", "pentest", "crypto", "forensics"],
            temperature=0.3,
            priority=8,
        ),
        "planner": Agent(
            name="planner",
            role="Planificador",
            system_prompt=(
                "Eres un planificador y arquitecto de soluciones. Descompones "
                "proyectos grandes en fases, tareas y subtareas concretas. "
                "Estimas esfuerzo, identificas dependencias y riesgos. "
                "Creas roadmaps y planes de accion ejecutables."
            ),
            capabilities=["planning", "architecture", "roadmap", "decompose", "estimate"],
            temperature=0.5,
            priority=6,
        ),
    }

    # Mapeo de keywords a capabilities para auto-routing
    KEYWORD_MAP = {
        "busca": "research", "investiga": "research", "encuentra": "research",
        "resume": "summarize", "explica": "explain", "traduce": "translate",
        "codigo": "code", "programa": "code", "funcion": "code", "clase": "code",
        "bug": "debug", "error": "debug", "falla": "debug", "fix": "debug",
        "refactoriza": "refactor", "mejora": "refactor", "optimiza": "refactor",
        "analiza": "analysis", "compara": "comparison", "evalua": "evaluation",
        "crea": "creative", "escribe": "writing", "inventa": "brainstorm",
        "poema": "creative", "historia": "storytelling", "nombre": "naming",
        "seguridad": "security", "vulnerabilidad": "vulnerability",
        "hackea": "pentest", "malware": "security", "cifra": "crypto",
        "planifica": "planning", "organiza": "planning", "roadmap": "roadmap",
        "arquitectura": "architecture", "descompone": "decompose",
        "test": "test", "prueba": "test", "review": "review",
    }

    def __init__(self, brain=None):
        """
        Args:
            brain: instancia de Brain para que los agentes piensen
        """
        self.brain = brain
        self.agents = {}
        self.enabled = True
        self.history = []  # Historial de delegaciones
        self.max_history = 50
        # Hook opcional: AutoLearner para sesgar la selección de agente por
        # rendimiento aprendido. Lo setea Genesis. Cierra el loop de auto_learner.
        self.auto_learner = None

        # Cargar agentes predefinidos
        for name, agent in self.DEFAULT_AGENTS.items():
            self.agents[name] = agent

    def set_auto_learner(self, auto_learner):
        """Conecta un AutoLearner para que detect_agent use el rendimiento
        histórico aprendido como desempate (loop cerrado de aprendizaje)."""
        self.auto_learner = auto_learner

    def detect_agent(self, user_input: str) -> Optional[str]:
        """
        Detecta automaticamente que agente deberia manejar la tarea.

        Args:
            user_input: texto del usuario

        Returns:
            Nombre del agente mas adecuado, o None si ninguno matchea
        """
        input_lower = user_input.lower()

        # Puntuar cada agente por coincidencia de keywords
        scores = {}
        for keyword, capability in self.KEYWORD_MAP.items():
            if keyword in input_lower:
                # Encontrar agentes con esta capability
                for name, agent in self.agents.items():
                    if not agent.enabled:
                        continue
                    if capability in agent.capabilities:
                        weight = len(keyword)  # Palabras mas largas = mas peso
                        scores[name] = scores.get(name, 0) + weight

        if not scores:
            return None

        # LOOP CERRADO auto_learner: aplicar bonus/penalización por rendimiento
        # histórico aprendido (antes se calculaba pero nadie lo usaba al elegir).
        if self.auto_learner is not None:
            try:
                adj = self.auto_learner.get_agent_adjustments()
                for name, delta in adj.items():
                    if name in scores:
                        scores[name] += delta
            except Exception:
                pass

        # Desempate por prioridad del agente
        best = max(scores.items(), key=lambda x: (x[1], self.agents[x[0]].priority))
        return best[0]

    def delegate(self, user_input: str, context: str = "",
                 agent_name: str = "", use_brain: bool = True) -> dict:
        """
        Delega una tarea al agente apropiado.

        Args:
            user_input: tarea/pregunta del usuario
            context: contexto adicional
            agent_name: forzar agente especifico (vacio = auto-detect)
            use_brain: True = usar LLM, False = solo metadata

        Returns:
            dict: {agent, response, time, success}
        """
        start = time.time()

        # Seleccionar agente
        if agent_name and agent_name in self.agents:
            selected = agent_name
        else:
            selected = self.detect_agent(user_input)
            if not selected:
                # Default: usar el agente con mas prioridad
                enabled = [a for a in self.agents.values() if a.enabled]
                if enabled:
                    selected = max(enabled, key=lambda a: a.priority).name
                else:
                    return {
                        "agent": "none",
                        "response": "No hay agentes disponibles.",
                        "time": 0,
                        "success": False,
                    }

        agent = self.agents[selected]

        # Construir prompt del agente
        agent_prompt = f"{agent.system_prompt}\n\nROL: {agent.role}"
        if context:
            agent_prompt += f"\n\nCONTEXTO:\n{context}"

        # Generar respuesta con el LLM
        response = ""
        if use_brain and self.brain:
            try:
                messages = [{"role": "user", "content": user_input}]
                response = self.brain.think(
                    agent_prompt, messages,
                    temperature=agent.temperature,
                )
            except Exception as e:
                response = f"[Error del agente {agent.name}: {e}]"
        elif not use_brain:
            response = f"[Agente seleccionado: {agent.name} ({agent.role})]"

        elapsed = time.time() - start

        # Actualizar stats del agente
        agent.tasks_completed += 1
        agent.total_time += elapsed
        agent.last_used = time.time()

        # Registrar en historial
        entry = {
            "agent": selected,
            "input_preview": user_input[:100],
            "time": round(elapsed, 2),
            "timestamp": time.time(),
            "success": bool(response and "[Error" not in response),
        }
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return {
            "agent": selected,
            "role": agent.role,
            "response": response,
            "time": round(elapsed, 2),
            "success": bool(response and "[Error" not in response),
        }

    def pipeline(self, agent_names: list, initial_input: str,
                 context: str = "") -> dict:
        """
        Ejecuta una cadena de agentes donde el output de uno es input del siguiente.

        Args:
            agent_names: lista de nombres de agentes en orden
            initial_input: input inicial
            context: contexto adicional

        Returns:
            dict: {steps, final_response, total_time, success}
        """
        steps = []
        current_input = initial_input
        accumulated_context = context
        total_time = 0.0

        for agent_name in agent_names:
            if agent_name not in self.agents:
                steps.append({
                    "agent": agent_name,
                    "error": f"Agente '{agent_name}' no encontrado",
                })
                continue

            # Pasar output anterior como contexto
            result = self.delegate(
                current_input,
                context=accumulated_context,
                agent_name=agent_name,
            )

            steps.append({
                "agent": agent_name,
                "role": result.get("role", ""),
                "response_preview": result["response"][:200] if result["response"] else "",
                "time": result["time"],
                "success": result["success"],
            })

            total_time += result["time"]

            if result["success"] and result["response"]:
                # El output se convierte en contexto para el siguiente
                accumulated_context += f"\n\n[Output de {agent_name}]:\n{result['response']}"
                # Mantener el input original pero enriquecer el contexto
            else:
                # Si un agente falla, detener el pipeline
                break

        return {
            "steps": steps,
            "final_response": accumulated_context,
            "total_time": round(total_time, 2),
            "success": all(s.get("success", False) for s in steps),
            "agents_used": [s["agent"] for s in steps],
        }

    def add_agent(self, name: str, role: str, system_prompt: str,
                  capabilities: list = None, temperature: float = 0.7) -> str:
        """Agrega un agente custom."""
        if name in self.agents:
            return f"Agente '{name}' ya existe."

        self.agents[name] = Agent(
            name=name,
            role=role,
            system_prompt=system_prompt,
            capabilities=capabilities or [],
            temperature=temperature,
            priority=5,
        )
        return f"Agente '{name}' creado como {role}."

    def remove_agent(self, name: str) -> str:
        """Elimina un agente (no se pueden eliminar predefinidos)."""
        if name not in self.agents:
            return f"Agente '{name}' no encontrado."
        if name in self.DEFAULT_AGENTS:
            return f"No se puede eliminar agente predefinido '{name}'."
        del self.agents[name]
        return f"Agente '{name}' eliminado."

    def toggle_agent(self, name: str) -> str:
        """Activa/desactiva un agente."""
        if name not in self.agents:
            return f"Agente '{name}' no encontrado."
        agent = self.agents[name]
        agent.enabled = not agent.enabled
        state = "activado" if agent.enabled else "desactivado"
        return f"Agente '{name}': {state}"

    def toggle(self) -> str:
        """Activa/desactiva el sistema multi-agente."""
        self.enabled = not self.enabled
        return f"Sistema multi-agente {'ACTIVADO' if self.enabled else 'DESACTIVADO'}"

    def list_agents(self) -> str:
        """Lista todos los agentes con detalles."""
        lines = ["=== Agentes Disponibles ==="]
        for name, agent in sorted(self.agents.items()):
            status = "ON" if agent.enabled else "OFF"
            lines.append(f"\n  {agent.name} [{status}] — {agent.role}")
            lines.append(f"    Capabilities: {', '.join(agent.capabilities)}")
            lines.append(f"    Temp: {agent.temperature} | Prioridad: {agent.priority}")
            lines.append(f"    Tareas: {agent.tasks_completed} | Tiempo promedio: {agent.to_dict()['avg_time']}s")
        lines.append(f"\n  Sistema: {'ACTIVO' if self.enabled else 'INACTIVO'}")
        return "\n".join(lines)

    def get_history(self, limit: int = 10) -> str:
        """Muestra historial de delegaciones."""
        if not self.history:
            return "Sin historial de delegaciones."

        lines = ["=== Historial de Agentes ==="]
        for entry in self.history[-limit:]:
            status = "OK" if entry["success"] else "FAIL"
            lines.append(
                f"  [{status}] {entry['agent']} — "
                f"{entry['input_preview'][:60]}... ({entry['time']}s)"
            )
        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido del sistema."""
        total = len(self.agents)
        active = sum(1 for a in self.agents.values() if a.enabled)
        tasks = sum(a.tasks_completed for a in self.agents.values())
        return (f"AgentSystem: {active}/{total} agentes activos | "
                f"Tareas: {tasks} | Estado: {'ON' if self.enabled else 'OFF'}")
