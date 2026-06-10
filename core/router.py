"""
GENESIS Smart Router — Clasificacion de intenciones y optimizacion de prompt.

En vez de enviar TODO el system prompt (personalidad + reglas + herramientas +
workspace + memorias + errores + plan + feedback + curiosidad) para cada
interaccion, el Router detecta que tipo de tarea es y construye un prompt
OPTIMIZADO que solo incluye las secciones relevantes.

Tipos de tarea:
- CHAT:       Conversacion casual → personalidad + reglas + memorias
- CODE:       Programacion → + herramientas + workspace + errores + plan
- RESEARCH:   Investigacion → + herramientas (buscar/web) + curiosidad
- SYSTEM:     Info del sistema → + herramientas (sistema/gpu)
- SELF:       Preguntas sobre Genesis → + self_awareness + evolucion
- FILE:       Operaciones de archivos → + herramientas (leer/escribir)

Beneficio: Reduce tokens del system prompt en 30-50% para tareas simples,
dejando mas espacio para la conversacion.
"""


class IntentRouter:
    """Clasifica la intencion del usuario y optimiza el contexto."""

    # Patrones de deteccion por tipo de tarea
    INTENT_PATTERNS = {
        "code": {
            "keywords": [
                "programa", "codigo", "script", "funcion", "clase", "variable",
                "python", "javascript", "html", "css", "java", "rust", "go",
                "crea un", "escribe un", "haz un", "genera un", "implementa",
                "algoritmo", "calculadora", "bot", "scraper", "app", "aplicacion",
                "api", "servidor", "web", "automatiza", "ejecuta", "debuggea",
                "compila", "arregla el error", "fix", "refactoriza",
                "code", "program", "function", "class", "create", "build",
            ],
            "sections": [
                "personality", "core_rules", "tools", "self_awareness",
                "workspace", "active_plan", "error_context", "feedback",
                "code_context", "metadata",
            ],
        },
        "research": {
            "keywords": [
                "busca", "investiga", "informacion sobre", "que es", "como funciona",
                "explicame", "dime sobre", "averigua", "encuentra",
                "search", "research", "find", "what is", "how does",
                "noticias", "ultimo", "reciente", "pagina web",
                "lee la pagina", "lee esta url", "traduce esta pagina",
                "aprende sobre", "aprende de", "especialízate", "especializate",
                "estudia sobre", "capacítate", "capacitate", "entrénate", "entrenate",
                "quiero que aprendas", "vuelvete experto", "learn about",
            ],
            "sections": [
                "personality", "core_rules", "tools", "self_awareness",
                "curiosity", "memory", "feedback", "metadata",
            ],
        },
        "system": {
            "keywords": [
                "sistema", "cpu", "ram", "gpu", "vram", "disco", "red",
                "hardware", "procesos", "memoria ram", "nvidia", "temperatura",
                "system", "hardware", "processes", "network",
                "que hardware", "cuanta ram", "cuanta vram",
            ],
            "sections": [
                "personality", "core_rules", "tools", "self_awareness",
                "metadata",
            ],
        },
        "self": {
            "keywords": [
                "tu estado", "tu evolucion", "tu generacion", "tu personalidad",
                "tu memoria", "tu codigo", "tu prompt", "tu fitness",
                "sobre ti", "tu version", "que eres", "quien eres",
                "tu curiosidad", "tu heartbeat", "tu feedback",
                "mostrar tu", "leer tu codigo", "editar tu codigo",
                "modifica tu", "mejora tu", "tu propio",
                "your state", "your evolution", "what are you",
            ],
            "sections": [
                "personality", "core_rules", "tools", "self_awareness",
                "memory", "feedback", "metadata",
            ],
        },
        "file": {
            "keywords": [
                "lee el archivo", "crea el archivo", "escribe en",
                "abre el archivo", "modifica el archivo", "lista el directorio",
                "listar carpeta", "listar directorio", "contenido de",
                "read file", "write file", "open file", "list directory",
                "escanea el proyecto", "escanea la carpeta",
            ],
            "sections": [
                "personality", "core_rules", "tools", "self_awareness",
                "workspace", "metadata",
            ],
        },
    }

    # Secciones base que siempre se incluyen para CHAT
    CHAT_SECTIONS = [
        "personality", "core_rules", "tools", "self_awareness",
        "memory", "emotional", "feedback", "curiosity", "metadata",
        "custom_tools",
    ]

    def __init__(self):
        self.last_intent: str = "chat"
        self.intent_history: list[str] = []
        self.intent_counts: dict[str, int] = {}

    def classify(self, user_input: str) -> str:
        """
        Clasifica la intencion del usuario.

        Args:
            user_input: Texto del usuario

        Returns:
            Tipo de intent: "code", "research", "system", "self", "file", "chat"
        """
        text = user_input.lower()
        scores: dict[str, int] = {}

        for intent, config in self.INTENT_PATTERNS.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in text:
                    score += 1
            if score > 0:
                scores[intent] = score

        if scores:
            best_intent = max(scores, key=scores.get)
            # Requiere al menos 1 match para clasificar
            if scores[best_intent] >= 1:
                self._record_intent(best_intent)
                return best_intent

        # Default: chat
        self._record_intent("chat")
        return "chat"

    def get_relevant_sections(self, intent: str) -> list[str]:
        """
        Retorna las secciones del system prompt relevantes para este intent.

        Args:
            intent: Tipo de intent detectado

        Returns:
            Lista de nombres de secciones a incluir
        """
        if intent in self.INTENT_PATTERNS:
            return self.INTENT_PATTERNS[intent]["sections"]
        return self.CHAT_SECTIONS

    def filter_sections(self, sections: dict[str, str],
                        intent: str) -> dict[str, str]:
        """
        Filtra las secciones del system prompt, manteniendo solo las relevantes.

        Args:
            sections: Todas las secciones disponibles
            intent: Tipo de intent

        Returns:
            Solo las secciones relevantes para este intent
        """
        relevant = self.get_relevant_sections(intent)
        filtered = {}
        for name, content in sections.items():
            if name in relevant:
                filtered[name] = content
        return filtered

    def _record_intent(self, intent: str):
        """Registra la intencion para estadisticas."""
        self.last_intent = intent
        self.intent_history.append(intent)
        # Mantener ultimos 50
        if len(self.intent_history) > 50:
            self.intent_history = self.intent_history[-50:]
        self.intent_counts[intent] = self.intent_counts.get(intent, 0) + 1

    def get_dominant_intent(self) -> str:
        """Retorna la intencion mas frecuente del usuario."""
        if not self.intent_counts:
            return "chat"
        return max(self.intent_counts, key=self.intent_counts.get)

    def status(self) -> str:
        """Resumen para /status."""
        total = sum(self.intent_counts.values())
        if total == 0:
            return "  Sin clasificaciones aun"
        lines = [f"  Ultimo intent: {self.last_intent}"]
        for intent, count in sorted(self.intent_counts.items(),
                                     key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            lines.append(f"    {intent}: {count} ({pct:.0f}%)")
        return "\n".join(lines)
