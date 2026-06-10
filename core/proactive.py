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
import os
import time
from pathlib import Path
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
        self.executed_actions: list[dict] = []
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
            "actions_executed": len(self.executed_actions),
        }

    # ============================================================
    # ACCIONES PROACTIVAS REALES (Ultron mode: ejecutar, no sugerir)
    # ============================================================

    SAFE_ACTIONS = {
        "clean_temp": {
            "name": "Limpiar archivos temporales",
            "description": "Elimina archivos temporales de Windows y Python cache",
            "category": "optimization",
        },
        "optimize_memory": {
            "name": "Optimizar memoria Genesis",
            "description": "Compacta memorias, elimina duplicados, libera recursos",
            "category": "optimization",
        },
        "backup_state": {
            "name": "Backup de estado",
            "description": "Crea backup completo de Genesis (memorias, config, estado)",
            "category": "safety",
        },
        "check_updates": {
            "name": "Verificar dependencias",
            "description": "Lista paquetes Python desactualizados",
            "category": "maintenance",
        },
        "system_health": {
            "name": "Diagnostico de salud",
            "description": "CPU, RAM, disco, GPU — detecta problemas",
            "category": "monitoring",
        },
        "kill_idle": {
            "name": "Cerrar procesos idle pesados",
            "description": "Identifica procesos que consumen >500MB sin actividad",
            "category": "optimization",
        },
    }

    def execute_action(self, action_id: str, genesis=None) -> dict:
        """
        Ejecuta una accion proactiva REAL.
        Ultron mode: no solo sugerir, sino hacer.

        Returns:
            dict con 'result', 'notification', 'error'
        """
        if action_id not in self.SAFE_ACTIONS:
            return {
                "error": f"Accion desconocida: {action_id}",
                "available": list(self.SAFE_ACTIONS.keys()),
            }

        action = self.SAFE_ACTIONS[action_id]
        result = ""
        notification = ""

        try:
            if action_id == "clean_temp":
                result, notification = self._action_clean_temp()

            elif action_id == "optimize_memory":
                result, notification = self._action_optimize_memory(genesis)

            elif action_id == "backup_state":
                result, notification = self._action_backup_state(genesis)

            elif action_id == "check_updates":
                result, notification = self._action_check_updates()

            elif action_id == "system_health":
                result, notification = self._action_system_health()

            elif action_id == "kill_idle":
                result, notification = self._action_kill_idle()

            self.executed_actions.append({
                "action_id": action_id,
                "name": action["name"],
                "timestamp": time.time(),
                "success": True,
            })

            return {
                "result": result,
                "notification": notification,
                "action": action["name"],
            }

        except Exception as e:
            self.executed_actions.append({
                "action_id": action_id,
                "name": action["name"],
                "timestamp": time.time(),
                "success": False,
                "error": str(e),
            })
            return {"error": str(e)}

    def _action_clean_temp(self) -> tuple:
        """Limpia archivos temporales de forma segura."""
        import shutil
        import glob

        cleaned = 0
        freed_bytes = 0
        errors = 0

        # Python __pycache__
        for cache_dir in glob.glob("**/__pycache__", recursive=True):
            try:
                size = sum(f.stat().st_size for f in Path(cache_dir).rglob("*") if f.is_file())
                shutil.rmtree(cache_dir)
                freed_bytes += size
                cleaned += 1
            except Exception:
                errors += 1

        # .pyc files sueltos
        for pyc in glob.glob("**/*.pyc", recursive=True):
            try:
                freed_bytes += os.path.getsize(pyc)
                os.remove(pyc)
                cleaned += 1
            except Exception:
                errors += 1

        freed_mb = freed_bytes / (1024 * 1024)
        result = (
            f"  ━━━ LIMPIEZA COMPLETADA ━━━\n"
            f"  Archivos eliminados: {cleaned}\n"
            f"  Espacio liberado: {freed_mb:.1f} MB\n"
            f"  Errores: {errors}\n"
        )
        notification = f"Limpieza: {cleaned} archivos, {freed_mb:.1f}MB liberados"
        return result, notification

    def _action_optimize_memory(self, genesis) -> tuple:
        """Optimiza memorias de Genesis."""
        if not genesis:
            return "Genesis no disponible", ""

        optimized = []

        # Compactar short-term memory
        if hasattr(genesis, 'memory'):
            st_before = len(genesis.memory.short_term)
            if st_before > 20:
                genesis.memory.short_term = genesis.memory.short_term[-15:]
                optimized.append(f"Short-term: {st_before} -> {len(genesis.memory.short_term)}")

        # Limpiar sugerencias viejas
        old_suggestions = len(self.shown_suggestions)
        if old_suggestions > 50:
            self.shown_suggestions = self.shown_suggestions[-20:]
            optimized.append(f"Sugerencias: {old_suggestions} -> {len(self.shown_suggestions)}")

        # Garbage collect
        import gc
        gc.collect()
        optimized.append("Garbage collector ejecutado")

        result = "  ━━━ MEMORIA OPTIMIZADA ━━━\n" + "\n".join(f"  {o}" for o in optimized)
        notification = f"Memoria optimizada: {len(optimized)} operaciones"
        return result, notification

    def _action_backup_state(self, genesis) -> tuple:
        """Crea backup del estado de Genesis."""
        if not genesis:
            return "Genesis no disponible", ""

        try:
            if hasattr(genesis, 'save_all'):
                genesis.save_all()
                result = "  ━━━ BACKUP COMPLETADO ━━━\n  Estado persistido via save_all()"
                notification = "Backup de estado completado"
            else:
                result = "  save_all() no disponible"
                notification = ""
            return result, notification
        except Exception as e:
            return f"  Error en backup: {str(e)}", ""

    def _action_check_updates(self) -> tuple:
        """Verifica paquetes desactualizados."""
        import subprocess

        try:
            proc = subprocess.run(
                ['pip', 'list', '--outdated', '--format=columns'],
                capture_output=True, text=True, timeout=30
            )
            output = proc.stdout.strip()
            if not output or "Package" not in output:
                result = "  ━━━ DEPENDENCIAS ━━━\n  Todos los paquetes estan actualizados"
                notification = "Dependencias al dia"
            else:
                lines = output.strip().split('\n')
                count = max(0, len(lines) - 2)  # Minus header lines
                result = f"  ━━━ DEPENDENCIAS ({count} desactualizadas) ━━━\n{output}"
                notification = f"{count} paquetes desactualizados"
            return result, notification
        except Exception as e:
            return f"  Error: {str(e)}", ""

    def _action_system_health(self) -> tuple:
        """Diagnostico completo del sistema."""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")

            issues = []
            if cpu > 80:
                issues.append(f"CPU al {cpu}% — alto")
            if ram.percent > 85:
                issues.append(f"RAM al {ram.percent}% — critico")
            if disk.percent > 90:
                issues.append(f"Disco al {disk.percent}% — critico")

            # GPU
            gpu_info = ""
            try:
                import subprocess
                gpu_out = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5,
                )
                if gpu_out.returncode == 0:
                    parts = gpu_out.stdout.strip().split(", ")
                    if len(parts) >= 4:
                        gpu_info = f"\n  GPU: {parts[0]}% | {parts[2]}/{parts[3]}MB VRAM | {parts[1]}C"
                        if int(parts[1]) > 85:
                            issues.append(f"GPU temperatura: {parts[1]}C — peligroso")
            except Exception:
                pass

            status = "SALUDABLE" if not issues else f"{len(issues)} ALERTAS"
            result = (
                f"  ━━━ DIAGNOSTICO: {status} ━━━\n"
                f"  CPU: {cpu}%\n"
                f"  RAM: {ram.percent}% ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)\n"
                f"  Disco: {disk.percent}% ({disk.free // (1024**3)} GB libres)"
                f"{gpu_info}"
            )
            if issues:
                result += "\n\n  ⚠ Problemas:\n" + "\n".join(f"    - {i}" for i in issues)

            notification = f"Sistema: {status}"
            return result, notification

        except ImportError:
            return "  psutil no instalado", ""

    def _action_kill_idle(self) -> tuple:
        """Identifica procesos pesados idle (solo reporta, no mata)."""
        try:
            import psutil

            heavy = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    mem_mb = proc.info['memory_info'].rss / (1024 * 1024)
                    if mem_mb > 500:
                        heavy.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'mem_mb': round(mem_mb, 1),
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            heavy.sort(key=lambda x: x['mem_mb'], reverse=True)

            if not heavy:
                result = "  ━━━ PROCESOS ━━━\n  No hay procesos usando >500MB"
                notification = "Sin procesos pesados"
            else:
                lines = [f"  {p['name']} (PID {p['pid']}): {p['mem_mb']} MB" for p in heavy[:10]]
                result = f"  ━━━ PROCESOS PESADOS ({len(heavy)}) ━━━\n" + "\n".join(lines)
                notification = f"{len(heavy)} procesos usando >500MB"

            return result, notification

        except ImportError:
            return "  psutil no instalado", ""
