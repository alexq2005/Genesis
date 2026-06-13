"""
GENESIS Heartbeat — Despertar periodico autonomo.

Genesis se despierta cada N minutos y:
1. Toma una pregunta de su cola de curiosidad
2. La investiga autonomamente (busqueda web + lectura de paginas)
3. Almacena los hallazgos en memoria de largo plazo
4. Si es momento de evolucionar, pone la propuesta en cola
   y espera confirmacion del usuario (NUNCA evoluciona solo)

Restricciones de seguridad:
- Solo modo lectura: busca y lee, NO ejecuta codigo ni edita archivos
- Evolucion requiere confirmacion humana
- Kill switch: archivo PAUSE detiene el heartbeat
- Log obligatorio de toda actividad
- Cooldown minimo entre ciclos
"""
import threading
import time
import json
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .brain import Brain
    from .memory import MemorySystem
    from .curiosity import CuriosityEngine
    from .evolution import EvolutionEngine


class HeartbeatLog:
    """Log de actividad del heartbeat — thread-safe."""

    def __init__(self, log_file: Path):
        self.log_file = log_file
        self._lock = threading.Lock()
        self.entries: list[dict] = self._load()

    def _load(self) -> list[dict]:
        try:
            from .safe_io import safe_read_json
            return safe_read_json(self.log_file, default=[])
        except ImportError:
            if self.log_file.exists():
                try:
                    with open(self.log_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    return []
            return []

    def _save(self):
        try:
            from .safe_io import safe_write_json
            safe_write_json(self.log_file, self.entries[-100:])
        except ImportError:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.entries[-100:], f, ensure_ascii=False, indent=2)

    def save(self):
        """Persiste estado a disco."""
        self._save()

    def add(self, action: str, details: str):
        with self._lock:
            self.entries.append({
                "action": action,
                "details": details[:500],
                "timestamp": time.time(),
            })
            self._save()

    def get_recent(self, n: int = 10) -> list[dict]:
        return self.entries[-n:]

    def format_recent(self, n: int = 10) -> str:
        recent = self.get_recent(n)
        if not recent:
            return "No hay actividad registrada."
        lines = ["=== ACTIVIDAD DEL HEARTBEAT ===\n"]
        for entry in recent:
            t = time.strftime("%H:%M:%S", time.localtime(entry["timestamp"]))
            lines.append(f"  [{t}] {entry['action']}: {entry['details']}")
        return "\n".join(lines)


class Heartbeat:
    """
    Motor de despertar periodico.
    Genesis investiga autonomamente sus preguntas de curiosidad.
    La evolucion SIEMPRE requiere confirmacion del usuario.
    """

    def __init__(self, interval_minutes: int = 30,
                 genesis_dir: Path = None,
                 log_file: Path = None):
        """
        Args:
            interval_minutes: Minutos entre despertares (minimo 5)
            genesis_dir: Directorio raiz de Genesis (para kill switch)
            log_file: Archivo de log de actividad
        """
        self.interval = max(5, interval_minutes) * 60  # En segundos, minimo 5 min
        self.genesis_dir = genesis_dir or Path(__file__).parent.parent
        self.log = HeartbeatLog(log_file or self.genesis_dir / "evolution_data" / "heartbeat_log.json")

        # Estado
        self.running = False
        self.paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Cola de evoluciones pendientes de confirmacion
        self.pending_evolution: Optional[dict] = None

        # Referencias a subsistemas (se setean desde Genesis)
        self.brain = None
        self.memory = None
        self.curiosity = None
        self.evolution = None

        # Stats
        self.cycles_completed = 0
        self.questions_researched = 0
        self.last_cycle_time: Optional[float] = None
        self.last_findings: list[dict] = []  # Últimos hallazgos para mostrar al usuario
        self._notify_enabled = False  # Notificaciones Windows desactivadas por defecto (usar /heartbeat notify on)

        # === Tareas de fondo autónomas (FASE 3) ===
        # Genesis registra aquí tareas periódicas (consolidación de aprendizaje,
        # self-eval, schedulers) que corren en cada ciclo aunque el usuario no
        # interactúe. Cada tarea: {name, fn, cooldown, last_run, runs, fails}.
        self.background_tasks: list[dict] = []
        self._bg_consecutive_fails = 0
        self._cpu_skip_threshold = 85.0  # % CPU por encima del cual se posponen tareas pesadas

    def configure(self, brain: "Brain", memory: "MemorySystem",
                  curiosity: "CuriosityEngine", evolution: "EvolutionEngine"):
        """Conecta el heartbeat con los subsistemas de Genesis."""
        self.brain = brain
        self.memory = memory
        self.curiosity = curiosity
        self.evolution = evolution

    def start(self):
        """Inicia el heartbeat en un thread daemon."""
        if self.running:
            return

        if not all([self.brain, self.memory, self.curiosity, self.evolution]):
            self.log.add("ERROR", "No se pudo iniciar: subsistemas no configurados")
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="genesis-heartbeat")
        self._thread.start()
        self.log.add("INICIO", f"Heartbeat iniciado (intervalo: {self.interval // 60} min)")

    def stop(self):
        """Detiene el heartbeat."""
        self.running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self.log.add("DETENIDO", "Heartbeat detenido")

    def _is_paused(self) -> bool:
        """Verifica el kill switch (archivo PAUSE)."""
        pause_file = self.genesis_dir / "PAUSE"
        return pause_file.exists()

    def register_task(self, name: str, fn, cooldown_minutes: int = 60,
                      heavy: bool = True):
        """Registra una tarea de fondo autónoma (FASE 3).

        Args:
            name: nombre legible (para logs)
            fn: callable sin argumentos; debe ser idempotente y barato de fallar
            cooldown_minutes: mínimo entre ejecuciones de esta tarea
            heavy: si True, se pospone cuando la CPU está saturada
        """
        self.background_tasks.append({
            "name": name, "fn": fn,
            "cooldown": max(1, cooldown_minutes) * 60,
            "last_run": 0.0, "runs": 0, "fails": 0, "heavy": heavy,
        })

    def _resources_ok(self) -> bool:
        """True si hay recursos para correr tareas pesadas (CPU no saturada).
        Si psutil no está, asume que sí."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.3) < self._cpu_skip_threshold
        except Exception:
            return True

    def _run_background_tasks(self):
        """Ejecuta las tareas de fondo que están due, con guardas de seguridad."""
        if not self.background_tasks:
            return
        now = time.time()
        resources_ok = None  # lazy: solo medir CPU si hay alguna tarea heavy due
        for task in self.background_tasks:
            if now - task["last_run"] < task["cooldown"]:
                continue
            if task["heavy"]:
                if resources_ok is None:
                    resources_ok = self._resources_ok()
                if not resources_ok:
                    self.log.add("BG_SKIP", f"{task['name']}: CPU saturada, pospuesto")
                    continue
            try:
                task["fn"]()
                task["last_run"] = time.time()
                task["runs"] += 1
                self._bg_consecutive_fails = 0
                self.log.add("BG_TASK", f"{task['name']} ejecutada (#{task['runs']})")
            except Exception as e:
                task["fails"] += 1
                task["last_run"] = time.time()  # no reintentar en loop apretado
                self._bg_consecutive_fails += 1
                self.log.add("BG_ERROR", f"{task['name']}: {str(e)[:200]}")
                # Backoff de seguridad: demasiados fallos seguidos → frenar este ciclo
                if self._bg_consecutive_fails >= 5:
                    self.log.add("BG_BACKOFF",
                                 "5 fallos consecutivos en tareas de fondo, frenando ciclo")
                    break

    def _loop(self):
        """Loop principal del heartbeat."""
        while self.running and not self._stop_event.is_set():
            # Esperar el intervalo (verificando stop cada 10 segundos)
            waited = 0
            while waited < self.interval and not self._stop_event.is_set():
                self._stop_event.wait(timeout=10)
                waited += 10

            if self._stop_event.is_set():
                break

            # Verificar kill switch
            if self._is_paused():
                self.log.add("PAUSA", "Heartbeat pausado (archivo PAUSE detectado)")
                continue

            # Verificar que el brain esta disponible
            if not self.brain.is_available():
                self.log.add("SKIP", "Brain no disponible, saltando ciclo")
                continue

            # Ejecutar ciclo
            try:
                self._execute_cycle()
            except Exception as e:
                self.log.add("ERROR", f"Error en ciclo: {str(e)[:200]}")

    def _execute_cycle(self):
        """Ejecuta un ciclo completo del heartbeat."""
        self.log.add("DESPERTAR", f"Ciclo #{self.cycles_completed + 1} iniciado")

        # Paso 1: Tomar una pregunta de curiosidad pendiente
        pending = self.curiosity.get_pending_questions(3)

        if not pending:
            # Si no hay preguntas, generar nuevas basadas en memorias
            self.log.add("CURIOSIDAD", "Sin preguntas pendientes, generando nuevas...")
            memories_text = self.memory.long_term.get_all_formatted()
            if memories_text and memories_text != "No hay memorias de largo plazo.":
                self.curiosity.generate_questions(self.brain, memories_text[:1000])
                pending = self.curiosity.get_pending_questions(3)

        if not pending:
            self.log.add("SKIP", "Sin preguntas para investigar")
            self.cycles_completed += 1
            self.last_cycle_time = time.time()
            return

        # Paso 2: Investigar la pregunta de mayor prioridad
        question = pending[0]
        question_text = question["question"]
        self.log.add("INVESTIGANDO", question_text)

        research_result = self._research_question(question_text)

        if research_result:
            # Paso 3: Almacenar hallazgos en memoria de largo plazo
            summary = research_result[:300]
            self.memory.long_term.remember(
                fact=f"[Investigacion autonoma] {question_text}: {summary}",
                category="investigacion_autonoma",
                source="heartbeat",
            )
            self.log.add("HALLAZGO", f"Almacenado: {summary[:150]}...")

            # Marcar como explorada
            self.curiosity.mark_explored(question_text)
            self.questions_researched += 1

            # Guardar hallazgo reciente para el usuario
            self.last_findings.append({
                "question": question_text,
                "finding": summary,
                "timestamp": time.time(),
            })
            # Mantener solo últimos 10
            if len(self.last_findings) > 10:
                self.last_findings = self.last_findings[-10:]

            # Notificación Windows
            if self._notify_enabled:
                self._send_notification(question_text, summary)

        # Paso 4: Verificar si toca evolucionar (poner en cola, NO ejecutar)
        if self.evolution.should_evolve() and not self.pending_evolution:
            self.log.add("EVOLUCION_PENDIENTE",
                         "Es momento de evolucionar. Esperando confirmacion del usuario.")
            self.pending_evolution = {
                "requested_at": time.time(),
                "generation": self.evolution.get_generation(),
                "interactions": self.evolution.interaction_count,
            }

        # Paso 5: Tareas de fondo autónomas (consolidación de aprendizaje,
        # self-eval, schedulers). Gated por killswitch (ya verificado arriba),
        # cooldowns y límite de recursos. FASE 3.
        self._run_background_tasks()

        self.cycles_completed += 1
        self.last_cycle_time = time.time()
        self.log.add("CICLO_COMPLETO",
                     f"Ciclo #{self.cycles_completed} completado. "
                     f"Preguntas investigadas total: {self.questions_researched}")

    def _research_question(self, question: str) -> Optional[str]:
        """
        Investiga una pregunta usando busqueda web.
        MODO READ-ONLY: solo busca y lee, no ejecuta nada.
        """
        try:
            from .tools import WebSearchTool

            # Buscar en la web
            search_results = WebSearchTool.search(question, max_results=5)

            if "[ERROR]" in search_results or "No se encontraron" in search_results:
                self.log.add("BUSQUEDA_FALLIDA", f"Sin resultados para: {question}")
                return None

            # Extraer la primera URL para leer en detalle
            import re
            urls = re.findall(r'URL: (https?://[^\s]+)', search_results)

            page_content = ""
            if urls:
                # Leer solo la primera pagina (conservar recursos)
                page_content = WebSearchTool.fetch_page(urls[0], max_chars=3000)
                if "[ERROR]" in page_content:
                    page_content = ""

            # Pedir al LLM que resuma los hallazgos
            summary_prompt = (
                f"Pregunta investigada: {question}\n\n"
                f"Resultados de busqueda:\n{search_results[:2000]}\n\n"
            )

            if page_content:
                summary_prompt += f"Contenido de pagina:\n{page_content[:2000]}\n\n"

            summary_prompt += (
                "Resume los hallazgos principales en 2-3 oraciones. "
                "Responde en espanol. Solo los datos clave."
            )

            summary = self.brain.quick_think(
                summary_prompt,
                system="Resume informacion de forma concisa y precisa. Responde en espanol.",
                temperature=0.3,
            )

            if "[ERROR]" not in summary:
                return summary

            return None

        except Exception as e:
            self.log.add("ERROR_INVESTIGACION", str(e)[:200])
            return None

    def _send_notification(self, question: str, finding: str):
        """Envía notificación Windows sobre hallazgo de investigación."""
        try:
            import subprocess as _sp
            safe_q = question[:60].replace("'", "").replace('"', '').replace('\n', ' ')
            safe_f = finding[:120].replace("'", "").replace('"', '').replace('\n', ' ')
            ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipTitle = 'GENESIS — Investigacion Autonoma'
$balloon.BalloonTipText = '{safe_q}: {safe_f}'
$balloon.Visible = $true
$balloon.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$balloon.Dispose()
"""
            _sp.Popen(
                ['powershell', '-NoProfile', '-Command', ps_script],
                stdout=_sp.DEVNULL, stderr=_sp.DEVNULL,
            )
        except Exception:
            pass  # No bloquear el heartbeat por fallos de notificación

    def get_recent_findings(self, n: int = 5) -> str:
        """Retorna los hallazgos recientes para mostrar al usuario."""
        if not self.last_findings:
            return "No hay hallazgos recientes de investigación autónoma."
        lines = ["🔬 HALLAZGOS DE INVESTIGACIÓN AUTÓNOMA:\n"]
        for f in self.last_findings[-n:]:
            t = time.strftime("%H:%M", time.localtime(f["timestamp"]))
            lines.append(f"  [{t}] 🔍 {f['question'][:60]}")
            lines.append(f"        → {f['finding'][:200]}\n")
        return "\n".join(lines)

    def confirm_evolution(self, brain: "Brain",
                          real_fitness: int = None,
                          feedback_context: str = None) -> dict:
        """
        El usuario confirmo la evolucion. Ejecutarla ahora.
        Llamado desde genesis.py cuando el usuario dice 'si'.

        Args:
            brain: Motor de inferencia
            real_fitness: Fitness calculado de datos reales (feedback + metricas)
            feedback_context: Preferencias del usuario aprendidas
        """
        if not self.pending_evolution:
            return {"evolved": False, "reason": "No hay evolucion pendiente"}

        self.log.add("EVOLUCION_CONFIRMADA",
                     f"Usuario confirmo. Fitness real: {real_fitness}. Ejecutando evolucion...")
        result = self.evolution.evolve(
            brain,
            real_fitness=real_fitness,
            feedback_context=feedback_context,
        )
        self.pending_evolution = None

        if result.get("evolved"):
            self.log.add("EVOLUCION_EXITOSA",
                         f"Gen {result.get('generation')} - Fitness: {result.get('fitness')}")
        else:
            self.log.add("EVOLUCION_RECHAZADA", result.get("reason", "Sin razon"))

        return result

    def reject_evolution(self):
        """El usuario rechazo la evolucion pendiente."""
        self.pending_evolution = None
        self.log.add("EVOLUCION_RECHAZADA", "Usuario rechazo la evolucion")

    def has_pending_evolution(self) -> bool:
        """Verifica si hay una evolucion esperando confirmacion."""
        return self.pending_evolution is not None

    def status(self) -> str:
        """Retorna estado del heartbeat."""
        state = "activo" if self.running else "inactivo"
        paused = " (PAUSADO)" if self._is_paused() else ""
        last = "nunca"
        if self.last_cycle_time:
            mins_ago = (time.time() - self.last_cycle_time) / 60
            last = f"hace {mins_ago:.0f} min"

        lines = [
            f"  Estado: {state}{paused}",
            f"  Intervalo: {self.interval // 60} minutos",
            f"  Ciclos completados: {self.cycles_completed}",
            f"  Preguntas investigadas: {self.questions_researched}",
            f"  Ultimo ciclo: {last}",
        ]

        if self.pending_evolution:
            lines.append(f"  ⚠ EVOLUCION PENDIENTE de confirmacion")

        return "\n".join(lines)
