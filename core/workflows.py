"""
GENESIS — Workflow Engine
Define y ejecuta cadenas de tareas automatizadas.

Un workflow es una secuencia de pasos que pueden incluir:
- Delegacion a agentes especificos
- Condiciones (if/else basado en output anterior)
- Loops (repetir hasta condicion)
- Transformaciones de datos entre pasos

Workflows predefinidos:
- code_review: analizar → revisar seguridad → sugerir mejoras
- research_deep: investigar → analizar → sintetizar
- debug_fix: diagnosticar → planificar fix → implementar
- project_scaffold: planificar → crear estructura → documentar

Uso:
    engine = WorkflowEngine(agent_system)
    result = engine.run("code_review", input_data="def foo(): pass")
    result = engine.run("research_deep", input_data="quantum computing")
"""
import time
import json
from typing import Optional, List, Callable


# ============================================================
# Workflow Step — paso individual
# ============================================================
class WorkflowStep:
    """Un paso dentro de un workflow."""

    def __init__(self, name: str, agent: str = "", action: str = "delegate",
                 prompt_template: str = "", transform: str = "",
                 condition: str = ""):
        """
        Args:
            name: nombre descriptivo del paso
            agent: nombre del agente a usar (vacio = auto-detect)
            action: tipo de accion (delegate, transform, condition)
            prompt_template: template del prompt (usa {input} y {context})
            transform: transformacion a aplicar al output (extract_code, summarize, etc.)
            condition: condicion para ejecutar (skip si es False)
        """
        self.name = name
        self.agent = agent
        self.action = action
        self.prompt_template = prompt_template
        self.transform = transform
        self.condition = condition


# ============================================================
# Workflow — secuencia de pasos
# ============================================================
class Workflow:
    """Define un workflow completo con pasos y metadata."""

    def __init__(self, name: str, description: str = "", steps: list = None,
                 tags: list = None):
        self.name = name
        self.description = description
        self.steps = steps or []
        self.tags = tags or []
        self.times_run = 0
        self.total_time = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": len(self.steps),
            "tags": self.tags,
            "times_run": self.times_run,
            "avg_time": round(self.total_time / max(1, self.times_run), 2),
        }


# ============================================================
# WorkflowEngine — motor de ejecucion
# ============================================================
class WorkflowEngine:
    """
    Motor que define, gestiona y ejecuta workflows.
    """

    def __init__(self, agent_system=None):
        """
        Args:
            agent_system: instancia de AgentSystem para delegacion
        """
        self.agent_system = agent_system
        self.workflows = {}
        self.history = []
        self.max_history = 30

        # Cargar workflows predefinidos
        self._load_defaults()

    def _load_defaults(self):
        """Carga workflows predefinidos."""

        # Code Review Pipeline
        self.workflows["code_review"] = Workflow(
            name="code_review",
            description="Revisa codigo: analiza → seguridad → mejoras",
            tags=["code", "review", "security"],
            steps=[
                WorkflowStep(
                    name="Analisis de codigo",
                    agent="coder",
                    prompt_template=(
                        "Analiza el siguiente codigo. Identifica: estructura, "
                        "patrones usados, posibles bugs, y complejidad.\n\n"
                        "CODIGO:\n{input}"
                    ),
                ),
                WorkflowStep(
                    name="Revision de seguridad",
                    agent="security",
                    prompt_template=(
                        "Revisa el siguiente codigo en busca de vulnerabilidades "
                        "de seguridad. Busca: inyecciones, leaks, validacion "
                        "insuficiente, hardcoded secrets.\n\n"
                        "CODIGO:\n{input}\n\n"
                        "ANALISIS PREVIO:\n{context}"
                    ),
                ),
                WorkflowStep(
                    name="Sugerencias de mejora",
                    agent="coder",
                    prompt_template=(
                        "Basado en el analisis y la revision de seguridad, "
                        "sugiere mejoras concretas al codigo. Incluye codigo "
                        "de ejemplo para cada mejora.\n\n"
                        "CODIGO ORIGINAL:\n{input}\n\n"
                        "HALLAZGOS:\n{context}"
                    ),
                ),
            ],
        )

        # Deep Research Pipeline
        self.workflows["research_deep"] = Workflow(
            name="research_deep",
            description="Investigacion profunda: buscar → analizar → sintetizar",
            tags=["research", "analysis", "summarize"],
            steps=[
                WorkflowStep(
                    name="Investigacion inicial",
                    agent="researcher",
                    prompt_template=(
                        "Investiga a fondo sobre: {input}\n"
                        "Cubre: definicion, historia, estado actual, "
                        "aplicaciones practicas y tendencias futuras."
                    ),
                ),
                WorkflowStep(
                    name="Analisis critico",
                    agent="analyst",
                    prompt_template=(
                        "Analiza criticamente la siguiente investigacion. "
                        "Identifica fortalezas, debilidades, sesgos y gaps "
                        "en la informacion.\n\n"
                        "TEMA: {input}\n"
                        "INVESTIGACION:\n{context}"
                    ),
                ),
                WorkflowStep(
                    name="Sintesis final",
                    agent="researcher",
                    prompt_template=(
                        "Sintetiza todo en un resumen ejecutivo claro y "
                        "accionable. Incluye: puntos clave, conclusiones "
                        "y recomendaciones.\n\n"
                        "TEMA: {input}\n"
                        "MATERIAL:\n{context}"
                    ),
                ),
            ],
        )

        # Debug & Fix Pipeline
        self.workflows["debug_fix"] = Workflow(
            name="debug_fix",
            description="Debug: diagnosticar → planificar → implementar fix",
            tags=["debug", "fix", "code"],
            steps=[
                WorkflowStep(
                    name="Diagnostico",
                    agent="coder",
                    prompt_template=(
                        "Diagnostica el siguiente problema. Identifica la "
                        "causa raiz, reproduce mentalmente el flujo y "
                        "determina exactamente donde falla.\n\n"
                        "PROBLEMA:\n{input}"
                    ),
                ),
                WorkflowStep(
                    name="Plan de correccion",
                    agent="planner",
                    prompt_template=(
                        "Planifica la correccion del siguiente bug. Lista "
                        "los pasos exactos, archivos a modificar, y tests "
                        "necesarios para verificar el fix.\n\n"
                        "PROBLEMA: {input}\n"
                        "DIAGNOSTICO:\n{context}"
                    ),
                ),
                WorkflowStep(
                    name="Implementacion",
                    agent="coder",
                    prompt_template=(
                        "Implementa el fix siguiendo el plan. Escribe el "
                        "codigo corregido completo, no solo fragmentos.\n\n"
                        "PROBLEMA: {input}\n"
                        "PLAN:\n{context}"
                    ),
                ),
            ],
        )

        # Project Scaffold Pipeline
        self.workflows["project_scaffold"] = Workflow(
            name="project_scaffold",
            description="Nuevo proyecto: planificar → estructura → documentar",
            tags=["planning", "architecture", "code"],
            steps=[
                WorkflowStep(
                    name="Planificacion",
                    agent="planner",
                    prompt_template=(
                        "Planifica la arquitectura para: {input}\n"
                        "Define: stack tecnologico, estructura de archivos, "
                        "componentes principales, y dependencias."
                    ),
                ),
                WorkflowStep(
                    name="Generacion de estructura",
                    agent="coder",
                    prompt_template=(
                        "Genera la estructura completa del proyecto con "
                        "archivos iniciales. Usa el formato:\n"
                        "[FILE: nombre_archivo]\ncontenido\n\n"
                        "ESPECIFICACION: {input}\n"
                        "ARQUITECTURA:\n{context}"
                    ),
                ),
                WorkflowStep(
                    name="Documentacion",
                    agent="researcher",
                    prompt_template=(
                        "Genera un README.md completo para el proyecto. "
                        "Incluye: descripcion, instalacion, uso, "
                        "arquitectura y contribucion.\n\n"
                        "PROYECTO: {input}\n"
                        "DETALLES:\n{context}"
                    ),
                ),
            ],
        )

    def run(self, workflow_name: str, input_data: str, context: str = "") -> dict:
        """
        Ejecuta un workflow completo.

        Args:
            workflow_name: nombre del workflow a ejecutar
            input_data: datos de entrada
            context: contexto adicional

        Returns:
            dict: {workflow, steps, final_output, total_time, success}
        """
        if workflow_name not in self.workflows:
            return {
                "workflow": workflow_name,
                "steps": [],
                "final_output": f"Workflow '{workflow_name}' no encontrado.",
                "total_time": 0,
                "success": False,
            }

        workflow = self.workflows[workflow_name]
        start = time.time()
        steps_result = []
        accumulated_context = context
        current_output = ""

        for step in workflow.steps:
            step_start = time.time()

            # Construir prompt
            prompt = step.prompt_template.format(
                input=input_data,
                context=accumulated_context,
            ) if step.prompt_template else input_data

            # Delegar al agente
            if self.agent_system:
                result = self.agent_system.delegate(
                    prompt,
                    context=accumulated_context,
                    agent_name=step.agent,
                )
                current_output = result.get("response", "")
            else:
                current_output = f"[Paso simulado: {step.name}]"

            step_time = time.time() - step_start

            steps_result.append({
                "name": step.name,
                "agent": step.agent,
                "time": round(step_time, 2),
                "output_preview": current_output[:200] if current_output else "",
                "success": bool(current_output and "[Error" not in current_output),
            })

            # Acumular contexto
            if current_output:
                accumulated_context += f"\n\n[{step.name}]:\n{current_output}"

        total_time = time.time() - start

        # Actualizar stats
        workflow.times_run += 1
        workflow.total_time += total_time

        # Registrar en historial
        self.history.append({
            "workflow": workflow_name,
            "steps_count": len(steps_result),
            "time": round(total_time, 2),
            "success": all(s["success"] for s in steps_result),
            "timestamp": time.time(),
        })
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return {
            "workflow": workflow_name,
            "steps": steps_result,
            "final_output": current_output,
            "total_time": round(total_time, 2),
            "success": all(s["success"] for s in steps_result),
        }

    def create_workflow(self, name: str, description: str,
                        steps_config: list) -> str:
        """
        Crea un workflow custom.

        Args:
            name: nombre unico
            description: descripcion
            steps_config: lista de dicts con {name, agent, prompt_template}

        Returns:
            Mensaje de confirmacion
        """
        if name in self.workflows:
            return f"Workflow '{name}' ya existe."

        steps = []
        for cfg in steps_config:
            steps.append(WorkflowStep(
                name=cfg.get("name", f"Paso {len(steps)+1}"),
                agent=cfg.get("agent", ""),
                prompt_template=cfg.get("prompt_template", "{input}\n{context}"),
            ))

        self.workflows[name] = Workflow(
            name=name,
            description=description,
            steps=steps,
            tags=["custom"],
        )
        return f"Workflow '{name}' creado con {len(steps)} pasos."

    def list_workflows(self) -> str:
        """Lista todos los workflows disponibles."""
        lines = ["=== Workflows Disponibles ==="]
        for name, wf in sorted(self.workflows.items()):
            lines.append(f"\n  {wf.name} — {wf.description}")
            lines.append(f"    Pasos: {len(wf.steps)} | Tags: {', '.join(wf.tags)}")
            lines.append(f"    Ejecutado: {wf.times_run} veces")
            if wf.steps:
                agents = " → ".join(s.agent or "auto" for s in wf.steps)
                lines.append(f"    Pipeline: {agents}")
        return "\n".join(lines)

    def get_history(self, limit: int = 10) -> str:
        """Muestra historial de ejecuciones."""
        if not self.history:
            return "Sin historial de workflows."

        lines = ["=== Historial de Workflows ==="]
        for entry in self.history[-limit:]:
            status = "OK" if entry["success"] else "FAIL"
            lines.append(
                f"  [{status}] {entry['workflow']} — "
                f"{entry['steps_count']} pasos ({entry['time']}s)"
            )
        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido del engine."""
        total = len(self.workflows)
        runs = sum(w.times_run for w in self.workflows.values())
        return f"WorkflowEngine: {total} workflows | Ejecuciones: {runs}"
