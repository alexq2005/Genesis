"""
GENESIS Task Planner — Descompone tareas complejas en pasos.

Cuando el usuario pide algo complejo ("crea una app web con login"),
Genesis lo descompone en subtareas ejecutables:
1. Crear estructura del proyecto
2. Implementar backend
3. Implementar login
4. etc.

Ejecuta cada paso secuencialmente, reportando progreso.
Puede adaptarse si un paso falla.
"""
import json
import time
import re
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .brain import Brain


class TaskPlanner:
    """Planificador de tareas complejas."""

    # Indicadores de que una tarea es compleja y necesita planificacion
    COMPLEXITY_INDICATORS = [
        # Multi-paso explicito
        "y luego", "y despues", "ademas", "tambien",
        "primero", "segundo", "por ultimo",
        "paso 1", "paso 2",
        # Proyectos complejos
        "app ", "aplicacion", "proyecto", "sistema",
        "pagina web", "sitio web", "api rest", "api",
        "bot de", "scraper de", "crawler",
        "juego", "game",
        # Componentes multiples
        "login", "registro", "autenticacion", "base de datos",
        "database", "frontend", "backend", "servidor",
        "interfaz", "dashboard",
        # Multiples archivos
        "multiples archivos", "varios archivos",
        "frontend y backend", "full stack",
        # Refactoring
        "refactoriza", "reestructura", "reorganiza",
        "migra", "convierte",
    ]

    def __init__(self):
        self.current_plan: Optional[dict] = None
        self.history: list[dict] = []

    def needs_planning(self, user_input: str) -> bool:
        """Determina si la tarea necesita planificacion."""
        text = user_input.lower()

        # Verificar indicadores de complejidad
        complexity_score = 0
        for indicator in self.COMPLEXITY_INDICATORS:
            if indicator in text:
                complexity_score += 1

        # Longitud del input tambien indica complejidad
        if len(text) > 150:
            complexity_score += 1

        # Si tiene multiples verbos de accion, es complejo
        action_verbs = [
            "crea", "haz", "programa", "implementa", "agrega",
            "modifica", "cambia", "mejora", "arregla", "configura",
            "create", "make", "build", "implement", "add",
        ]
        verb_count = sum(1 for v in action_verbs if v in text)
        if verb_count >= 2:
            complexity_score += 2

        # Conectores "con" + "y" indican multiples requerimientos
        if " con " in text and " y " in text:
            complexity_score += 1

        return complexity_score >= 2

    def create_plan(self, brain: "Brain", user_input: str,
                    workspace_context: str = "") -> dict:
        """
        Usa el LLM para descomponer la tarea en pasos.

        Args:
            brain: Motor de inferencia
            user_input: La tarea del usuario
            workspace_context: Contexto del proyecto actual

        Returns:
            dict con el plan estructurado
        """
        plan_prompt = (
            f"TAREA DEL USUARIO:\n{user_input}\n\n"
        )

        if workspace_context:
            plan_prompt += f"CONTEXTO DEL PROYECTO:\n{workspace_context}\n\n"

        plan_prompt += (
            "Descompone esta tarea en pasos concretos y ejecutables.\n"
            "Cada paso debe ser una accion especifica que puedas hacer con tus herramientas.\n\n"
            "Responde SOLO con JSON valido (sin markdown):\n"
            '{"steps": [\n'
            '  {"id": 1, "action": "descripcion corta", "tool": "python|escribir|leer|buscar|escanear", "details": "que hacer exactamente"},\n'
            '  ...\n'
            '], "estimated_steps": N}\n\n'
            "REGLAS:\n"
            "- Maximo 8 pasos\n"
            "- Cada paso debe usar UNA herramienta\n"
            "- Se especifico en los detalles\n"
            "- Ordena logicamente (dependencias primero)\n"
        )

        response = brain.quick_think(
            plan_prompt,
            system="Eres un planificador de tareas. Descompones tareas complejas en pasos ejecutables. Responde SOLO con JSON valido.",
            temperature=0.3,
        )

        plan_data = self._parse_plan(response)

        if plan_data and plan_data.get("steps"):
            self.current_plan = {
                "task": user_input,
                "steps": plan_data["steps"],
                "current_step": 0,
                "completed_steps": [],
                "failed_steps": [],
                "status": "activo",
                "created": time.time(),
            }
            return self.current_plan

        return {}

    def get_current_step(self) -> Optional[dict]:
        """Retorna el paso actual a ejecutar."""
        if not self.current_plan:
            return None

        idx = self.current_plan["current_step"]
        steps = self.current_plan["steps"]

        if idx >= len(steps):
            self.current_plan["status"] = "completado"
            return None

        return steps[idx]

    def complete_step(self, success: bool = True, result: str = ""):
        """Marca el paso actual como completado y avanza."""
        if not self.current_plan:
            return

        idx = self.current_plan["current_step"]
        steps = self.current_plan["steps"]

        if idx < len(steps):
            step = steps[idx]
            step["completed"] = True
            step["success"] = success
            step["result"] = result[:300]

            if success:
                self.current_plan["completed_steps"].append(idx)
            else:
                self.current_plan["failed_steps"].append(idx)

        self.current_plan["current_step"] += 1

        # Verificar si termino
        if self.current_plan["current_step"] >= len(steps):
            self.current_plan["status"] = "completado"
            self.current_plan["finished"] = time.time()
            self.history.append(self.current_plan)

    def get_plan_prompt_context(self) -> str:
        """
        Genera contexto del plan actual para inyectar en el prompt.
        Le dice al LLM en que paso esta y que viene despues.
        """
        if not self.current_plan or self.current_plan["status"] != "activo":
            return ""

        plan = self.current_plan
        steps = plan["steps"]
        current_idx = plan["current_step"]

        lines = [
            f"[PLAN DE TRABAJO ACTIVO — Tarea: {plan['task'][:100]}]",
            f"Progreso: {current_idx}/{len(steps)} pasos completados",
            "",
        ]

        for i, step in enumerate(steps):
            status = ""
            if i < current_idx:
                if step.get("success", True):
                    status = "✅"
                else:
                    status = "❌"
            elif i == current_idx:
                status = "➡️ ACTUAL"
            else:
                status = "⬜"

            lines.append(f"  {status} Paso {step.get('id', i+1)}: {step.get('action', '?')}")

        if current_idx < len(steps):
            current = steps[current_idx]
            lines.append(f"\nEJECUTA AHORA: {current.get('details', current.get('action', ''))}")
            if current.get("tool"):
                lines.append(f"Herramienta sugerida: [TOOL:{current['tool']}]")

        return "\n".join(lines)

    def cancel(self):
        """Cancela el plan actual."""
        if self.current_plan:
            self.current_plan["status"] = "cancelado"
            self.current_plan["finished"] = time.time()
            self.history.append(self.current_plan)
            self.current_plan = None

    def is_active(self) -> bool:
        """Verifica si hay un plan activo."""
        return self.current_plan is not None and self.current_plan["status"] == "activo"

    def _parse_plan(self, text: str) -> Optional[dict]:
        """Intenta parsear el plan del LLM."""
        text = text.strip()

        # Limpiar markdown
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Intentar extraer JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return None

    def format_plan(self) -> str:
        """Formatea el plan actual para mostrar al usuario."""
        if not self.current_plan:
            return "No hay plan activo."

        plan = self.current_plan
        steps = plan["steps"]
        current_idx = plan["current_step"]

        lines = [
            f"=== PLAN DE TRABAJO ===",
            f"Tarea: {plan['task'][:150]}",
            f"Estado: {plan['status']}",
            f"Progreso: {current_idx}/{len(steps)}\n",
        ]

        for i, step in enumerate(steps):
            if i < current_idx:
                icon = "✅" if step.get("success", True) else "❌"
            elif i == current_idx:
                icon = "▶️"
            else:
                icon = "⬜"

            lines.append(f"  {icon} [{step.get('id', i+1)}] {step.get('action', '?')}")
            if step.get("details"):
                lines.append(f"      {step['details'][:100]}")

        return "\n".join(lines)

    def status(self) -> str:
        """Resumen corto para /status."""
        if not self.current_plan:
            return "  Sin plan activo"

        plan = self.current_plan
        current = plan["current_step"]
        total = len(plan["steps"])
        return f"  Plan activo: {plan['task'][:60]}... ({current}/{total} pasos)"
