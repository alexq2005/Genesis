"""
GENESIS — Modo Proactivo
Genesis sugiere mejoras, investigaciones y optimizaciones sin que le pregunten.

Funciona analizando:
- Patrones del Knowledge Graph (conceptos frecuentes poco explorados)
- Historial de errores (errores recurrentes sin solucion)
- Memoria emocional (frustraciones del usuario)
- Workspace (archivos que podrian mejorarse)
- Feedback negativo reciente (areas a mejorar)

Las sugerencias se acumulan y se muestran en momentos naturales
(despues de una respuesta, cuando hay pausa, etc.)
"""
import time
from typing import Optional


class ProactiveEngine:
    """
    Motor de sugerencias proactivas.

    Analiza el contexto y genera sugerencias relevantes sin que
    el usuario las pida. Las sugerencias tienen prioridad y cooldown
    para no ser repetitivas.
    """

    # Cooldown minimo entre sugerencias del mismo tipo (en segundos)
    COOLDOWN = 300  # 5 minutos

    # Maximo de sugerencias pendientes
    MAX_PENDING = 5

    # Interacciones minimas antes de empezar a sugerir
    MIN_INTERACTIONS = 3

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.pending_suggestions: list[dict] = []
        self.shown_suggestions: list[dict] = []
        self.last_suggestion_time: float = 0
        self.interaction_count = 0
        self._cooldowns: dict[str, float] = {}  # tipo -> timestamp

    def analyze(self, user_input: str, response: str,
                knowledge_graph=None, error_memory=None,
                feedback=None, workspace=None,
                curiosity=None) -> Optional[str]:
        """
        Analiza el contexto actual y genera sugerencia si es apropiado.

        Args:
            user_input: Lo que dijo el usuario
            response: Lo que respondio Genesis
            knowledge_graph: KnowledgeGraph instance
            error_memory: ErrorMemory instance
            feedback: FeedbackSystem instance
            workspace: Workspace instance
            curiosity: CuriosityEngine instance

        Returns:
            Sugerencia formateada o None
        """
        if not self.enabled:
            return None

        self.interaction_count += 1

        # No sugerir en las primeras interacciones
        if self.interaction_count < self.MIN_INTERACTIONS:
            return None

        # No sugerir muy seguido
        now = time.time()
        if now - self.last_suggestion_time < 60:  # Minimo 1 minuto entre sugerencias
            return None

        # Generar sugerencias segun contexto
        suggestions = []

        # 1. Errores recurrentes no resueltos
        if error_memory:
            suggestion = self._check_error_patterns(error_memory)
            if suggestion:
                suggestions.append(suggestion)

        # 2. Conceptos poco explorados en Knowledge Graph
        if knowledge_graph:
            suggestion = self._check_unexplored_concepts(knowledge_graph, user_input)
            if suggestion:
                suggestions.append(suggestion)

        # 3. Feedback negativo reciente
        if feedback:
            suggestion = self._check_negative_feedback(feedback)
            if suggestion:
                suggestions.append(suggestion)

        # 4. Curiosidad pendiente relevante
        if curiosity:
            suggestion = self._check_pending_curiosity(curiosity, user_input)
            if suggestion:
                suggestions.append(suggestion)

        # 5. Mejoras de workspace
        if workspace and workspace.is_set():
            suggestion = self._check_workspace_improvements(workspace)
            if suggestion:
                suggestions.append(suggestion)

        # 6. Patrones de uso
        suggestion = self._check_usage_patterns(user_input, response)
        if suggestion:
            suggestions.append(suggestion)

        # Seleccionar la mejor sugerencia (mayor prioridad)
        if not suggestions:
            return None

        suggestions.sort(key=lambda s: s.get("priority", 0), reverse=True)
        best = suggestions[0]

        # Verificar cooldown para este tipo
        stype = best.get("type", "general")
        if stype in self._cooldowns and now - self._cooldowns[stype] < self.COOLDOWN:
            return None

        # Registrar sugerencia
        self._cooldowns[stype] = now
        self.last_suggestion_time = now
        self.shown_suggestions.append({
            **best,
            "timestamp": now,
        })

        # Formatear como hint sutil
        return self._format_suggestion(best)

    def _check_error_patterns(self, error_memory) -> Optional[dict]:
        """Detecta errores recurrentes sin solucion."""
        if not hasattr(error_memory, "errors") or not error_memory.errors:
            return None

        # Contar errores no resueltos
        unresolved = [e for e in error_memory.errors if not e.get("resolved")]
        if len(unresolved) >= 3:
            # Buscar patron comun
            error_types = {}
            for e in unresolved[-10:]:
                error_text = e.get("error", "")[:50]
                # Extraer tipo de error (ej: "TypeError", "ImportError")
                import re
                match = re.search(r'(\w+Error)', error_text)
                if match:
                    etype = match.group(1)
                    error_types[etype] = error_types.get(etype, 0) + 1

            if error_types:
                most_common = max(error_types, key=error_types.get)
                count = error_types[most_common]
                if count >= 2:
                    return {
                        "type": "error_pattern",
                        "priority": 8,
                        "message": f"He detectado que '{most_common}' aparece {count} veces en errores recientes sin resolver. "
                                   f"Puedo investigar la causa raiz si quieres.",
                        "action": f"Investigar patron de {most_common}",
                    }
        return None

    def _check_unexplored_concepts(self, knowledge_graph, user_input: str) -> Optional[dict]:
        """Sugiere explorar conceptos relacionados poco profundizados."""
        if not user_input or len(user_input) < 5:
            return None

        try:
            # Buscar conceptos relacionados al input
            concepts = knowledge_graph._extract_concepts(user_input)
            if not concepts:
                return None

            for concept in concepts[:3]:
                related = knowledge_graph.get_related(concept, depth=2, max_results=5)
                for r in related:
                    # Nodo con pocas conexiones = poco explorado
                    node = knowledge_graph.nodes.get(r.get("concept", ""))
                    if node and node.get("mentions", 0) == 1 and r.get("weight", 0) > 0:
                        return {
                            "type": "unexplored_concept",
                            "priority": 4,
                            "message": f"'{r['concept']}' aparecio en relacion a '{concept}' pero no lo hemos explorado mucho. "
                                       f"Podria ser interesante profundizar.",
                            "action": f"Explorar {r['concept']}",
                        }
        except Exception:
            pass
        return None

    def _check_negative_feedback(self, feedback) -> Optional[dict]:
        """Detecta feedback negativo reciente y sugiere mejoras."""
        try:
            streak = feedback.data.get("streak", 0)
            if streak <= -2:
                recent_fails = feedback.get_recent_failures(2)
                if recent_fails:
                    categories = [f.get("category", "general") for f in recent_fails]
                    common_cat = max(set(categories), key=categories.count) if categories else "general"
                    return {
                        "type": "negative_feedback",
                        "priority": 7,
                        "message": f"He recibido feedback negativo reciente en respuestas de tipo '{common_cat}'. "
                                   f"Puedo ajustar mi estilo o pedir mas detalles sobre lo que prefieres.",
                        "action": "Ajustar estilo de respuestas",
                    }
        except Exception:
            pass
        return None

    def _check_pending_curiosity(self, curiosity, user_input: str) -> Optional[dict]:
        """Sugiere investigar preguntas de curiosidad relevantes."""
        try:
            pending = curiosity.get_pending_questions(5)
            if not pending:
                return None

            input_lower = user_input.lower()
            for q in pending:
                question = q.get("question", "").lower()
                # Buscar solapamiento de palabras con el input actual
                q_words = set(question.split())
                i_words = set(input_lower.split())
                overlap = q_words & i_words - {"que", "como", "por", "de", "el", "la", "en", "es", "un", "una"}
                if len(overlap) >= 2:
                    return {
                        "type": "curiosity_match",
                        "priority": 5,
                        "message": f"Tengo una pregunta pendiente relacionada: '{q['question']}'. "
                                   f"Puedo investigarla ahora si te interesa.",
                        "action": f"Investigar: {q['question'][:50]}",
                    }
        except Exception:
            pass
        return None

    def _check_workspace_improvements(self, workspace) -> Optional[dict]:
        """Sugiere mejoras en el workspace activo."""
        try:
            if not workspace.is_set():
                return None

            stats = workspace.data
            files = stats.get("files", [])
            if not files:
                return None

            # Detectar archivos Python sin docstring (simplificado)
            py_files = [f for f in files if f.get("name", "").endswith(".py")]
            if len(py_files) > 3:
                return {
                    "type": "workspace_improvement",
                    "priority": 3,
                    "message": f"Tu workspace tiene {len(py_files)} archivos Python. "
                               f"Puedo analizar la estructura del proyecto y sugerir mejoras.",
                    "action": "Analizar estructura del proyecto",
                }
        except Exception:
            pass
        return None

    def _check_usage_patterns(self, user_input: str, response: str) -> Optional[dict]:
        """Detecta patrones de uso y sugiere funcionalidades."""
        input_lower = user_input.lower()

        # Si el usuario pregunta mucho sobre el mismo tema
        # (detectar repeticion de palabras clave)

        # Sugerir streaming si las respuestas son largas y no esta activado
        if len(response) > 1000:
            return {
                "type": "feature_suggestion",
                "priority": 2,
                "message": "Las respuestas largas se ven mejor con streaming activado (/stream). "
                           "Veras los tokens aparecer en tiempo real.",
                "action": "Activar streaming",
            }

        return None

    def _format_suggestion(self, suggestion: dict) -> str:
        """Formatea la sugerencia para mostrar al usuario."""
        msg = suggestion.get("message", "")
        return f"\n  [Genesis sugiere] {msg}"

    def toggle(self) -> str:
        """Activa/desactiva el modo proactivo."""
        self.enabled = not self.enabled
        state = "activado" if self.enabled else "desactivado"
        return f"Modo proactivo: {state}"

    def status(self) -> str:
        """Estado del motor proactivo."""
        state = "activo" if self.enabled else "inactivo"
        total = len(self.shown_suggestions)
        pending = len(self.pending_suggestions)
        return (
            f"  Proactivo: {state} | "
            f"Sugerencias mostradas: {total} | "
            f"Pendientes: {pending}"
        )

    def get_stats(self) -> dict:
        """Estadisticas del motor proactivo."""
        type_counts = {}
        for s in self.shown_suggestions:
            stype = s.get("type", "general")
            type_counts[stype] = type_counts.get(stype, 0) + 1

        return {
            "enabled": self.enabled,
            "total_suggestions": len(self.shown_suggestions),
            "by_type": type_counts,
            "interaction_count": self.interaction_count,
        }
