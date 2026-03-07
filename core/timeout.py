"""
GENESIS Timeout & Progress — Proteccion contra cuelgues y feedback visual.

Problemas que resuelve:
- Si el LLM se cuelga, Genesis se congela para siempre
- No hay feedback visual durante operaciones largas
- No hay forma de cancelar una generacion en progreso

Solucion:
- TimeoutExecutor: ejecuta funciones con timeout configurable
- Spinner: indicador visual de progreso para operaciones largas
- ProgressBar: barra de progreso para operaciones con progreso conocido
"""
import threading
import sys
import time
import itertools
from typing import Callable, Any, Optional


class TimeoutError(Exception):
    """Error cuando una operacion excede el timeout."""
    pass


class TimeoutExecutor:
    """
    Ejecuta funciones con timeout usando threads.

    Uso:
        result = TimeoutExecutor.run(
            func=lambda: brain.think(prompt, messages),
            timeout=120,
            description="Generando respuesta"
        )

    El thread se marca como daemon, asi que si Genesis se cierra,
    el thread muere automaticamente. Si la operacion excede el timeout,
    retorna un mensaje de error en vez de colgar para siempre.
    """

    @staticmethod
    def run(func: Callable, timeout: int = 120,
            description: str = "operacion",
            default_on_timeout: str = "") -> Any:
        """
        Ejecuta func() con un timeout.

        Args:
            func: Funcion a ejecutar (sin argumentos)
            timeout: Segundos maximos antes de abortar
            description: Descripcion de la operacion (para logs)
            default_on_timeout: Valor a retornar si hay timeout

        Returns:
            El resultado de func(), o default_on_timeout si excede el timeout
        """
        result_container = [None]
        error_container = [None]
        completed = threading.Event()

        def _worker():
            try:
                result_container[0] = func()
            except Exception as e:
                error_container[0] = e
            finally:
                completed.set()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        # Esperar con timeout
        if completed.wait(timeout=timeout):
            # Completo a tiempo
            if error_container[0]:
                raise error_container[0]
            return result_container[0]
        else:
            # Timeout excedido
            if default_on_timeout:
                return default_on_timeout
            raise TimeoutError(
                f"[TIMEOUT] {description} excedio {timeout}s. "
                f"El modelo puede estar sobrecargado. "
                f"Intenta de nuevo o usa un prompt mas corto."
            )


class Spinner:
    """
    Spinner visual para operaciones largas.

    Muestra un indicador animado en la terminal mientras una
    operacion esta en progreso. Thread-safe.

    Uso:
        with Spinner("Pensando"):
            response = brain.think(prompt, messages)
        # El spinner se detiene automaticamente al salir del bloque
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Fallback para terminales sin Unicode
    FRAMES_ASCII = ["|", "/", "-", "\\"]

    def __init__(self, message: str = "Procesando", use_unicode: bool = None):
        self.message = message
        if use_unicode is None:
            # Auto-detectar soporte Unicode
            try:
                encoding = sys.stdout.encoding or ""
                use_unicode = encoding.lower() in ("utf-8", "utf8", "utf-16", "utf-32")
            except Exception:
                use_unicode = False
        self.frames = self.FRAMES if use_unicode else self.FRAMES_ASCII
        self._cycle = itertools.cycle(self.frames)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._elapsed = 0.0
        self._start_time = 0.0

    def start(self):
        """Inicia el spinner en un thread separado."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message: str = ""):
        """Detiene el spinner."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        self._elapsed = time.time() - self._start_time
        # Limpiar la linea
        sys.stdout.write(f"\r  {' ' * 60}\r")
        sys.stdout.flush()
        if final_message:
            sys.stdout.write(f"  {final_message}\n")
            sys.stdout.flush()

    def _spin(self):
        """Loop del spinner (corre en thread daemon)."""
        while self._running:
            elapsed = time.time() - self._start_time
            frame = next(self._cycle)
            try:
                sys.stdout.write(
                    f"\r  {frame} {self.message}... ({elapsed:.0f}s)"
                )
                sys.stdout.flush()
            except (UnicodeEncodeError, OSError):
                pass  # Terminal no soporta los caracteres
            time.sleep(0.1)

    @property
    def elapsed(self) -> float:
        """Tiempo transcurrido desde que se inicio."""
        if self._running:
            return time.time() - self._start_time
        return self._elapsed

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class ProgressBar:
    """
    Barra de progreso para operaciones con progreso conocido.

    Uso:
        bar = ProgressBar("Descargando", total=100)
        for i in range(100):
            do_work()
            bar.update(i + 1)
        bar.finish()
    """

    def __init__(self, message: str, total: int, width: int = 30):
        self.message = message
        self.total = max(total, 1)
        self.width = width
        self.current = 0
        self._start_time = time.time()
        # Detectar si la terminal soporta Unicode
        self._use_unicode = self._check_unicode()
        self._fill_char = "#" if not self._use_unicode else "="
        self._empty_char = "-" if not self._use_unicode else " "

    @staticmethod
    def _check_unicode() -> bool:
        """Verifica si stdout soporta Unicode."""
        try:
            encoding = sys.stdout.encoding or ""
            return encoding.lower() in ("utf-8", "utf8", "utf-16", "utf-32")
        except Exception:
            return False

    def update(self, current: int):
        """Actualiza el progreso."""
        self.current = min(current, self.total)
        self._render()

    def _render(self):
        """Renderiza la barra de progreso."""
        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = self._fill_char * filled + self._empty_char * (self.width - filled)
        elapsed = time.time() - self._start_time

        # Estimar tiempo restante
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f" ETA: {eta:.0f}s"
        else:
            eta_str = ""

        try:
            sys.stdout.write(
                f"\r  {self.message}: [{bar}] {pct*100:.0f}% "
                f"({self.current}/{self.total}){eta_str}"
            )
            sys.stdout.flush()
        except (UnicodeEncodeError, OSError):
            pass  # Terminal no soporta los caracteres, silenciar

    def finish(self, message: str = ""):
        """Completa la barra de progreso."""
        self.current = self.total
        elapsed = time.time() - self._start_time
        try:
            sys.stdout.write(f"\r  {' ' * 70}\r")
            if message:
                sys.stdout.write(f"  {message} ({elapsed:.1f}s)\n")
            sys.stdout.flush()
        except (UnicodeEncodeError, OSError):
            pass
