"""
GENESIS Conversation Summarizer — Comprime la conversacion sin perder contexto.

Problema: ShortTermMemory tiene un limite de mensajes. Cuando se llena,
simplemente descarta los mas antiguos. Esto pierde informacion valiosa.

Solucion: Antes de descartar, comprimir los mensajes viejos en un resumen.
El resumen se inyecta como contexto, preservando la esencia de la conversacion
anterior sin consumir muchos tokens.

Inspirado en: "Recursive summarization" de GPT-4 Long Context papers.
"""
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .brain import Brain


class ConversationSummarizer:
    """
    Comprime mensajes de conversacion viejos en resumenes.

    Flujo:
    1. Monitorea la cantidad de mensajes en memoria de corto plazo
    2. Cuando se acerca al limite, comprime los mas viejos en un resumen
    3. El resumen se acumula (resumen previo + nuevos mensajes → nuevo resumen)
    4. Los mensajes comprimidos se eliminan de la memoria
    """

    def __init__(self, trigger_ratio: float = 0.7,
                 keep_recent: int = 8,
                 max_summary_tokens: int = 400):
        """
        Args:
            trigger_ratio: Comprimir cuando la memoria llega a este % de capacidad
            keep_recent: Mensajes recientes a mantener (no comprimir)
            max_summary_tokens: Tokens maximos para el resumen
        """
        self.trigger_ratio = trigger_ratio
        self.keep_recent = keep_recent
        self.max_summary_tokens = max_summary_tokens

        # Estado
        self.current_summary: str = ""
        self.summaries_count: int = 0
        self.messages_compressed: int = 0
        self.last_summary_time: Optional[float] = None

    def should_summarize(self, message_count: int, max_messages: int) -> bool:
        """
        Determina si es momento de comprimir mensajes.

        Args:
            message_count: Cantidad actual de mensajes
            max_messages: Capacidad maxima de la memoria

        Returns:
            True si deberia comprimir
        """
        threshold = int(max_messages * self.trigger_ratio)
        return message_count >= threshold

    def summarize(self, brain: "Brain", messages: list[dict]) -> str:
        """
        Comprime mensajes en un resumen usando el LLM.

        Estrategia:
        - Mantiene los ultimos `keep_recent` mensajes intactos
        - Comprime los anteriores en un resumen conciso
        - Si ya hay un resumen previo, lo incorpora

        Args:
            brain: Motor de inferencia
            messages: Lista completa de mensajes

        Returns:
            El resumen generado (tambien guardado en self.current_summary)
        """
        if len(messages) <= self.keep_recent:
            return self.current_summary

        # Separar mensajes a comprimir vs mantener
        to_compress = messages[:-self.keep_recent]
        n_compressed = len(to_compress)

        if not to_compress:
            return self.current_summary

        # Formatear mensajes para el LLM
        conversation_text = ""
        for msg in to_compress:
            role = "Usuario" if msg.get("role") == "user" else "Genesis"
            content = msg.get("content", "")[:300]
            conversation_text += f"{role}: {content}\n"

        # Construir prompt de resumen
        prompt = ""
        if self.current_summary:
            prompt += (
                f"RESUMEN PREVIO DE LA CONVERSACION:\n"
                f"{self.current_summary}\n\n"
            )

        prompt += (
            f"NUEVOS MENSAJES A RESUMIR ({n_compressed} mensajes):\n"
            f"{conversation_text}\n\n"
            f"INSTRUCCIONES:\n"
            f"- Resume toda la conversacion (resumen previo + nuevos mensajes) en maximo 4 oraciones\n"
            f"- Captura: temas discutidos, decisiones tomadas, tareas completadas, datos importantes del usuario\n"
            f"- Incluye nombres, rutas de archivos, y datos especificos que el usuario menciono\n"
            f"- NO incluyas saludos ni frases de relleno\n"
            f"- Responde SOLO con el resumen, nada mas\n"
        )

        summary = brain.quick_think(
            prompt,
            system="Eres un resumidor experto. Comprime conversaciones preservando informacion clave. Responde en espanol. Solo el resumen, sin preambulos.",
            temperature=0.2,
        )

        if summary and "[ERROR]" not in summary:
            self.current_summary = summary[:int(self.max_summary_tokens * 3.5)]
            self.summaries_count += 1
            self.messages_compressed += n_compressed
            self.last_summary_time = time.time()
            return self.current_summary

        # Si fallo, hacer resumen basico sin LLM
        return self._fallback_summary(to_compress)

    def _fallback_summary(self, messages: list[dict]) -> str:
        """
        Resumen de emergencia sin usar el LLM.
        Extrae las primeras palabras de cada mensaje del usuario.
        """
        topics = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "").strip()
                # Solo la primera oracion o primeros 60 chars
                first_sentence = content.split(".")[0][:60]
                if first_sentence and not first_sentence.startswith("["):
                    topics.append(first_sentence)

        if not topics:
            return self.current_summary

        # Tomar los ultimos 5 temas
        recent_topics = topics[-5:]
        summary = "Temas discutidos: " + "; ".join(recent_topics)

        if self.current_summary:
            summary = f"{self.current_summary} | {summary}"

        # Limitar tamaño
        max_chars = int(self.max_summary_tokens * 3.5)
        if len(summary) > max_chars:
            summary = summary[-max_chars:]

        self.current_summary = summary
        self.summaries_count += 1
        self.messages_compressed += len(messages)
        self.last_summary_time = time.time()
        return self.current_summary

    def get_summary(self) -> str:
        """Retorna el resumen actual de la conversacion."""
        return self.current_summary

    def has_summary(self) -> bool:
        """Verifica si hay un resumen disponible."""
        return bool(self.current_summary)

    def clear(self):
        """Limpia el resumen (nueva conversacion)."""
        self.current_summary = ""

    def status(self) -> str:
        """Resumen para /status."""
        if not self.current_summary:
            return "  Sin resumen (conversacion corta)"

        tokens_est = len(self.current_summary) // 4
        return (
            f"  Resumenes generados: {self.summaries_count}\n"
            f"  Mensajes comprimidos: {self.messages_compressed}\n"
            f"  Resumen actual: ~{tokens_est} tokens"
        )
