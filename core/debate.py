"""
GENESIS Debate — Sistema de debate multi-agente interno.

Antes de responder, multiples "voces" internas debaten:
- Critico: Busca fallas, riesgos y problemas en la respuesta
- Creativo: Propone soluciones originales y conexiones inesperadas
- Logico: Verifica consistencia, hechos y estructura

Un sintetizador combina lo mejor de cada voz en la respuesta final.
Inspirado en "Society of Mind" (Marvin Minsky) y tecnicas de
multi-agent debate (Du et al., 2023).
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .brain import Brain


# Personalidades de cada agente interno
AGENT_PERSONAS = {
    "critico": {
        "name": "Critico",
        "symbol": "🔍",
        "system": (
            "Eres la voz CRITICA interna de una IA llamada Genesis. "
            "Tu rol es encontrar fallas, riesgos, errores logicos y problemas "
            "en cualquier respuesta propuesta. Sé duro pero justo. "
            "Señala: errores factuales, suposiciones no verificadas, "
            "riesgos de seguridad, posibles malentendidos. "
            "Responde en 2-3 oraciones maximo, directo al punto."
        ),
    },
    "creativo": {
        "name": "Creativo",
        "symbol": "💡",
        "system": (
            "Eres la voz CREATIVA interna de una IA llamada Genesis. "
            "Tu rol es proponer ideas originales, conexiones inesperadas, "
            "analogias utiles y enfoques no convencionales. "
            "Piensa fuera de la caja. Sugiere lo que nadie mas sugeriria. "
            "Responde en 2-3 oraciones maximo, directo al punto."
        ),
    },
    "logico": {
        "name": "Logico",
        "symbol": "🧮",
        "system": (
            "Eres la voz LOGICA interna de una IA llamada Genesis. "
            "Tu rol es verificar la consistencia, la estructura del razonamiento, "
            "y la precision de los hechos. Asegurate de que la respuesta sea "
            "coherente, bien estructurada y basada en evidencia. "
            "Responde en 2-3 oraciones maximo, directo al punto."
        ),
    },
}

SYNTHESIZER_SYSTEM = (
    "Eres el SINTETIZADOR interno de una IA llamada Genesis. "
    "Recibes las opiniones de 3 voces internas (critico, creativo, logico) "
    "sobre una pregunta del usuario. Tu trabajo es combinar lo mejor de "
    "cada voz en UNA sola respuesta coherente, precisa y util. "
    "No menciones a las voces internas — el usuario no debe saber "
    "que hubo un debate. Genera la respuesta final directamente. "
    "Responde en el idioma del usuario."
)


class DebateSystem:
    """Sistema de debate multi-agente interno."""

    def __init__(self, enabled: bool = True, agents: list[str] = None):
        self.enabled = enabled
        self.active_agents = agents or ["critico", "creativo", "logico"]
        self.last_debate: dict = {}
        self.debate_count = 0

    def debate(self, brain: "Brain", user_input: str,
               context: str = "") -> str:
        """
        Ejecuta un debate interno y retorna la respuesta sintetizada.

        Args:
            brain: Motor LLM
            user_input: Pregunta/input del usuario
            context: Contexto adicional (memoria, conversacion previa)

        Returns:
            Respuesta sintetizada final
        """
        if not self.enabled:
            return ""

        self.debate_count += 1

        # Cada agente genera su perspectiva
        perspectives = {}
        debate_prompt = f"El usuario dice: \"{user_input}\"\n"
        if context:
            debate_prompt += f"\nContexto previo: {context}\n"
        debate_prompt += "\n¿Cual es tu analisis/perspectiva?"

        for agent_id in self.active_agents:
            if agent_id not in AGENT_PERSONAS:
                continue

            agent = AGENT_PERSONAS[agent_id]
            perspective = brain.quick_think(
                debate_prompt,
                system=agent["system"],
                temperature=0.6,
            )
            perspectives[agent_id] = {
                "name": agent["name"],
                "symbol": agent["symbol"],
                "response": perspective,
            }

        # Sintetizar las perspectivas
        synthesis_prompt = (
            f"Pregunta del usuario: \"{user_input}\"\n\n"
            f"Voces internas:\n"
        )
        for agent_id, data in perspectives.items():
            synthesis_prompt += f"\n{data['name']}: {data['response']}\n"

        synthesis_prompt += (
            f"\nGenera la respuesta final para el usuario. "
            f"Integra las mejores ideas de cada voz. "
            f"No menciones el debate interno."
        )

        final_response = brain.quick_think(
            synthesis_prompt,
            system=SYNTHESIZER_SYSTEM,
            temperature=0.5,
        )

        # Guardar registro del debate
        self.last_debate = {
            "input": user_input,
            "perspectives": perspectives,
            "synthesis": final_response,
            "debate_number": self.debate_count,
        }

        return final_response

    def get_last_debate_log(self) -> str:
        """Retorna un log legible del ultimo debate (para debug/transparencia)."""
        if not self.last_debate:
            return "No hay debates registrados."

        lines = [f"=== Debate Interno #{self.last_debate['debate_number']} ==="]
        lines.append(f"Input: {self.last_debate['input'][:100]}")
        lines.append("")

        for agent_id, data in self.last_debate.get("perspectives", {}).items():
            lines.append(f"{data['symbol']} {data['name']}:")
            lines.append(f"  {data['response'][:200]}")
            lines.append("")

        lines.append("Sintesis final:")
        lines.append(f"  {self.last_debate.get('synthesis', 'N/A')[:200]}")

        return "\n".join(lines)

    def status(self) -> str:
        """Retorna estado del sistema de debate."""
        agents_str = ", ".join(self.active_agents)
        return (
            f"  Debate: {'activo' if self.enabled else 'inactivo'}\n"
            f"  Agentes: {agents_str}\n"
            f"  Debates realizados: {self.debate_count}"
        )
