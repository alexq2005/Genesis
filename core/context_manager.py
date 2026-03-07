"""
GENESIS Context Budget Manager — Control inteligente de tokens.

Con 8192 tokens de contexto, cada token cuenta.
Este modulo administra un "presupuesto" de tokens:
1. Estima cuantos tokens ocupa cada seccion del prompt
2. Prioriza secciones criticas (personalidad, reglas) sobre opcionales (curiosidad)
3. Recorta secciones de baja prioridad cuando hay overflow
4. Garantiza que siempre haya espacio para la conversacion

Sin esto, el system prompt puede crecer hasta consumir todo el contexto
y el modelo recibe conversacion truncada o corrupta.
"""
from typing import Optional


class ContextBudgetManager:
    """
    Administrador de presupuesto de tokens para el contexto del LLM.

    Distribuye el contexto disponible entre:
    - System prompt (personalidad, reglas, inyecciones)
    - Conversacion (mensajes del usuario y asistente)
    - Respuesta (espacio reservado para que el modelo genere)
    """

    # Prioridades de secciones del system prompt (mayor = mas importante)
    # Las secciones con prioridad alta NUNCA se recortan
    SECTION_PRIORITIES = {
        "personality":      100,   # Personalidad base — nunca recortar
        "core_rules":       95,    # Reglas inmutables — nunca recortar
        "tools":            90,    # Descripcion de herramientas — critico para funcionar
        "self_awareness":   70,    # Auto-conocimiento — importante pero recortable
        "workspace":        65,    # Contexto del proyecto — importante si esta activo
        "active_plan":      60,    # Plan activo — importante durante ejecucion
        "error_context":    55,    # Errores para el prompt actual
        "feedback":         50,    # Preferencias aprendidas
        "memory":           45,    # Memoria de largo plazo
        "code_context":     40,    # Codigo relevante del workspace
        "curiosity":        30,    # Curiosidad — dispensable bajo presion
        "emotional":        25,    # Memoria emocional — dispensable
        "metadata":         20,    # Version/generacion — minimo
        "debate_insights":  35,    # Insights de debate — dispensable
    }

    # Limites de tokens para recorte por seccion
    # Cuando hay overflow, las secciones se recortan a estos maximos
    SECTION_MAX_TOKENS = {
        "personality":      400,
        "core_rules":       200,
        "tools":            600,
        "self_awareness":   300,
        "workspace":        400,
        "active_plan":      300,
        "error_context":    200,
        "feedback":         150,
        "memory":           300,
        "code_context":     400,
        "curiosity":        100,
        "emotional":        100,
        "metadata":         50,
        "debate_insights":  200,
    }

    def __init__(self, max_context_tokens: int = 8192,
                 response_reserve: int = 1024,
                 system_ratio: float = 0.45):
        """
        Args:
            max_context_tokens: Tokens totales del modelo
            response_reserve: Tokens reservados para la respuesta del modelo
            system_ratio: Proporcion maxima del contexto para system prompt (0.0-0.7)
        """
        self.max_context = max_context_tokens
        self.response_reserve = response_reserve
        self.system_ratio = min(0.7, max(0.2, system_ratio))

        # Presupuestos calculados
        self.usable_tokens = self.max_context - self.response_reserve
        self.system_budget = int(self.usable_tokens * self.system_ratio)
        self.conversation_budget = self.usable_tokens - self.system_budget

        # Estadisticas
        self.last_system_tokens = 0
        self.last_conversation_tokens = 0
        self.last_overflow = False
        self.total_overflows = 0
        self.sections_trimmed: list[str] = []

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estima tokens de un texto.

        Para modelos GGUF con tokenizer de Mistral/Llama:
        - Espanol: ~1 token cada 3.5 caracteres
        - Ingles: ~1 token cada 4 caracteres
        - Codigo: ~1 token cada 3 caracteres
        - Promedio general: ~1 token cada 3.5 caracteres

        Es una estimacion conservadora (sobreestima ligeramente = mas seguro).
        """
        if not text:
            return 0
        # Usar 3.5 como factor promedio para espanol
        return max(1, int(len(text) / 3.5))

    def fit_system_prompt(self, sections: dict[str, str]) -> str:
        """
        Ajusta las secciones del system prompt al presupuesto.

        Args:
            sections: dict de {nombre_seccion: contenido}
                      Los nombres deben coincidir con SECTION_PRIORITIES

        Returns:
            System prompt completo que cabe en el presupuesto
        """
        self.sections_trimmed = []

        # Calcular tokens de cada seccion
        section_tokens = {}
        for name, content in sections.items():
            if content:
                section_tokens[name] = self.estimate_tokens(content)

        total_tokens = sum(section_tokens.values())

        # Si cabe todo, unir y retornar
        if total_tokens <= self.system_budget:
            self.last_system_tokens = total_tokens
            self.last_overflow = False
            return self._join_sections(sections)

        # Overflow — recortar secciones de menor prioridad
        self.last_overflow = True
        self.total_overflows += 1

        # Ordenar secciones por prioridad (menor primero = recortar primero)
        sorted_sections = sorted(
            section_tokens.keys(),
            key=lambda s: self.SECTION_PRIORITIES.get(s, 50)
        )

        # Recortar hasta que quepa
        trimmed_sections = dict(sections)
        current_total = total_tokens

        for section_name in sorted_sections:
            if current_total <= self.system_budget:
                break

            priority = self.SECTION_PRIORITIES.get(section_name, 50)
            current_tokens = section_tokens.get(section_name, 0)

            # Secciones de prioridad >= 90 no se recortan
            if priority >= 90:
                continue

            # Calcular cuanto recortar
            max_allowed = self.SECTION_MAX_TOKENS.get(section_name, 200)
            excess = current_total - self.system_budget

            if current_tokens > max_allowed:
                # Recortar a max_allowed
                new_content = self._truncate_section(
                    trimmed_sections.get(section_name, ""),
                    max_allowed
                )
                saved = current_tokens - self.estimate_tokens(new_content)
                trimmed_sections[section_name] = new_content
                current_total -= saved
                self.sections_trimmed.append(section_name)
            elif excess > current_tokens and priority < 40:
                # Eliminar completamente secciones de baja prioridad
                current_total -= current_tokens
                trimmed_sections[section_name] = ""
                self.sections_trimmed.append(f"{section_name} (eliminado)")

        self.last_system_tokens = current_total
        return self._join_sections(trimmed_sections)

    def fit_messages(self, messages: list[dict],
                     summary: str = "") -> list[dict]:
        """
        Ajusta los mensajes de conversacion al presupuesto.

        Estrategia:
        1. Si hay un resumen de conversacion, incluirlo primero
        2. Mantener los mensajes mas recientes
        3. Descartar los mas antiguos si no caben

        Args:
            messages: Lista de mensajes {"role": ..., "content": ...}
            summary: Resumen de mensajes anteriores (opcional)

        Returns:
            Lista de mensajes que caben en el presupuesto
        """
        if not messages:
            return []

        # Recalcular presupuesto de conversacion basado en system real
        actual_conv_budget = self.usable_tokens - self.last_system_tokens

        # Si hay resumen, reservar espacio para el
        summary_tokens = 0
        if summary:
            summary_tokens = self.estimate_tokens(summary)
            actual_conv_budget -= summary_tokens

        # Incluir mensajes desde el mas reciente
        fitted = []
        used_tokens = 0

        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens(msg.get("content", ""))
            if used_tokens + msg_tokens <= actual_conv_budget:
                fitted.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        # Prepend resumen si hay uno y se descartaron mensajes
        if summary and len(fitted) < len(messages):
            fitted.insert(0, {
                "role": "user",
                "content": f"[RESUMEN DE CONVERSACION ANTERIOR]\n{summary}"
            })

        self.last_conversation_tokens = used_tokens + summary_tokens
        return fitted

    def get_budget_status(self) -> dict:
        """Retorna el estado actual del presupuesto."""
        used = self.last_system_tokens + self.last_conversation_tokens
        return {
            "max_context": self.max_context,
            "response_reserve": self.response_reserve,
            "usable_tokens": self.usable_tokens,
            "system_budget": self.system_budget,
            "system_used": self.last_system_tokens,
            "conversation_budget": self.conversation_budget,
            "conversation_used": self.last_conversation_tokens,
            "total_used": used,
            "free_tokens": self.usable_tokens - used,
            "overflow": self.last_overflow,
            "total_overflows": self.total_overflows,
            "sections_trimmed": self.sections_trimmed,
        }

    def _join_sections(self, sections: dict[str, str]) -> str:
        """Une secciones no vacias con separadores."""
        # Ordenar por prioridad descendente para que lo importante vaya primero
        sorted_names = sorted(
            sections.keys(),
            key=lambda s: self.SECTION_PRIORITIES.get(s, 50),
            reverse=True
        )
        parts = []
        for name in sorted_names:
            content = sections.get(name, "")
            if content and content.strip():
                parts.append(content.strip())
        return "\n\n".join(parts)

    def _truncate_section(self, text: str, max_tokens: int) -> str:
        """Trunca una seccion a max_tokens estimados."""
        if not text:
            return ""
        max_chars = int(max_tokens * 3.5)
        if len(text) <= max_chars:
            return text
        # Truncar con indicador
        truncated = text[:max_chars - 30]
        # Cortar en el ultimo salto de linea
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.5:
            truncated = truncated[:last_newline]
        return truncated + "\n[...truncado por limite de contexto]"

    def status(self) -> str:
        """Resumen para /status."""
        budget = self.get_budget_status()
        pct_used = (budget["total_used"] / budget["usable_tokens"] * 100
                    if budget["usable_tokens"] > 0 else 0)
        overflow_info = ""
        if budget["total_overflows"] > 0:
            overflow_info = f" | Overflows: {budget['total_overflows']}"
        return (
            f"  Contexto: {budget['total_used']}/{budget['usable_tokens']} tokens "
            f"({pct_used:.0f}%){overflow_info}\n"
            f"  System: {budget['system_used']}/{budget['system_budget']} | "
            f"Conv: {budget['conversation_used']}/{budget['conversation_budget']}"
        )
