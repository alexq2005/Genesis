"""
GENESIS Curiosity — Motor de curiosidad autonoma.

Genesis genera preguntas propias sobre los temas que trabaja.
Identifica "lagunas de conocimiento" y las registra para
explorar despues. Simula curiosidad intrinseca.
"""
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .brain import Brain


class CuriosityEngine:
    """Motor que genera curiosidad autonoma en Genesis."""

    def __init__(self, curiosity_file: Path):
        self.curiosity_file = curiosity_file
        self.questions: list[dict] = self._load()
        self.questions_generated = 0

    def _load(self) -> list[dict]:
        """Carga preguntas pendientes desde disco."""
        if self.curiosity_file.exists():
            try:
                with open(self.curiosity_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save(self):
        """Persiste preguntas a disco."""
        with open(self.curiosity_file, "w", encoding="utf-8") as f:
            json.dump(self.questions, f, ensure_ascii=False, indent=2)

    def generate_questions(self, brain: "Brain", conversation_context: str) -> list[str]:
        """
        Analiza la conversacion y genera preguntas que Genesis
        "quiere" explorar.

        Returns:
            Lista de preguntas generadas
        """
        prompt = (
            f"Analiza esta conversacion reciente:\n\n"
            f"{conversation_context[:2000]}\n\n"
            f"Genera 1-3 preguntas que surjan naturalmente de esta conversacion. "
            f"Deben ser preguntas que una mente curiosa querria investigar. "
            f"Enfocate en lagunas de conocimiento o temas interesantes que "
            f"quedaron sin explorar.\n\n"
            f"Responde SOLO con las preguntas, una por linea, sin numeros ni guiones."
        )

        result = brain.quick_think(
            prompt,
            system="Eres un motor de curiosidad. Generas preguntas profundas e interesantes.",
            temperature=0.8,
        )

        if "[ERROR]" in result:
            return []

        new_questions = [q.strip() for q in result.strip().split("\n") if q.strip()]

        for q in new_questions:
            if len(q) > 10:  # Filtrar lineas muy cortas
                self.questions.append({
                    "question": q,
                    "created": time.time(),
                    "explored": False,
                    "priority": 0.5,
                })
                self.questions_generated += 1

        self._save()
        return new_questions

    def get_pending_questions(self, limit: int = 5) -> list[dict]:
        """Retorna preguntas pendientes de explorar."""
        pending = [q for q in self.questions if not q["explored"]]
        pending.sort(key=lambda x: x["priority"], reverse=True)
        return pending[:limit]

    def mark_explored(self, question: str):
        """Marca una pregunta como explorada."""
        for q in self.questions:
            if q["question"] == question:
                q["explored"] = True
                break
        self._save()

    def boost_priority(self, question: str, amount: float = 0.2):
        """Aumenta la prioridad de una pregunta (refuerza la curiosidad)."""
        for q in self.questions:
            if q["question"] == question:
                q["priority"] = min(1.0, q["priority"] + amount)
                break
        self._save()

    def get_curiosity_prompt(self) -> str:
        """Genera texto sobre la curiosidad actual para inyectar en el prompt."""
        pending = self.get_pending_questions(3)
        if not pending:
            return ""

        lines = ["[CURIOSIDAD ACTIVA — Preguntas que quiero explorar:]"]
        for q in pending:
            lines.append(f"  - {q['question']}")
        return "\n".join(lines)

    def status(self) -> str:
        """Retorna estado del motor de curiosidad."""
        pending = len([q for q in self.questions if not q["explored"]])
        explored = len([q for q in self.questions if q["explored"]])
        return (
            f"  Preguntas generadas: {self.questions_generated}\n"
            f"  Pendientes: {pending}\n"
            f"  Exploradas: {explored}"
        )
