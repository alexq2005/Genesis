"""
GENESIS Logger — Sistema de logging centralizado.

Problema: Sin logging, debuggear Genesis es un infierno. Los print() se
pierden en la consola y no hay registro de que paso, cuando ni por que.

Solucion: Logger estructurado que escribe a archivo con rotacion automatica.
Cada modulo obtiene su propio logger hijo con prefijo identificador.

Niveles:
- DEBUG: Detalle interno (solo en archivo)
- INFO: Eventos normales
- WARN: Problemas no criticos
- ERROR: Fallos que necesitan atencion
"""
import time
import os
import threading
from pathlib import Path
from typing import Optional


class GenesisLogger:
    """
    Logger ligero con escritura a archivo + consola opcional.

    No usa el modulo `logging` de Python para evitar conflictos con
    otros modulos y mantener control total del formato.
    """

    LEVELS = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}

    def __init__(self, log_dir: Path = None,
                 file_level: str = "DEBUG",
                 console_level: str = "WARN",
                 max_file_size_mb: float = 5.0,
                 max_files: int = 3):
        """
        Args:
            log_dir: Directorio para archivos de log
            file_level: Nivel minimo para escribir a archivo
            console_level: Nivel minimo para imprimir en consola
            max_file_size_mb: Tamano maximo del log antes de rotar
            max_files: Cantidad de archivos de log a mantener
        """
        self.log_dir = log_dir or Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

        self.file_level = self.LEVELS.get(file_level, 0)
        self.console_level = self.LEVELS.get(console_level, 2)
        self.max_file_size = int(max_file_size_mb * 1024 * 1024)
        self.max_files = max_files
        self.console_enabled = False  # Se activa con /debug

        self._lock = threading.Lock()
        self._log_file = self.log_dir / "genesis.log"
        self._session_start = time.time()
        self._message_count = 0

        # Escribir header de sesion
        self._write_header()

    def _write_header(self):
        """Escribe encabezado de nueva sesion en el log."""
        header = (
            f"\n{'='*60}\n"
            f"GENESIS SESSION START — {self._format_time(time.time())}\n"
            f"PID: {os.getpid()}\n"
            f"{'='*60}\n"
        )
        self._write_to_file(header)

    def get_child(self, module_name: str) -> "ModuleLogger":
        """
        Crea un logger hijo para un modulo especifico.

        Args:
            module_name: Nombre del modulo (ej: "heartbeat", "memory")

        Returns:
            ModuleLogger con prefijo del modulo
        """
        return ModuleLogger(parent=self, module=module_name)

    def log(self, level: str, module: str, message: str):
        """
        Registra un mensaje de log.

        Args:
            level: DEBUG, INFO, WARN, ERROR
            module: Nombre del modulo origen
            message: Mensaje a registrar
        """
        level_num = self.LEVELS.get(level, 0)
        timestamp = self._format_time(time.time())
        line = f"[{timestamp}] [{level:5s}] [{module:12s}] {message}"

        # Escribir a archivo si supera el nivel
        if level_num >= self.file_level:
            self._write_to_file(line + "\n")

        # Imprimir en consola si esta habilitado y supera el nivel
        if self.console_enabled and level_num >= self.console_level:
            print(f"  [LOG] {line}")

        self._message_count += 1

    def _write_to_file(self, text: str):
        """Escribe texto al archivo de log con thread safety."""
        with self._lock:
            try:
                # Verificar rotacion
                if self._log_file.exists():
                    if self._log_file.stat().st_size > self.max_file_size:
                        self._rotate()

                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass  # El logger nunca debe crashear la app

    def _rotate(self):
        """Rota los archivos de log (genesis.log -> genesis.1.log -> ...)."""
        try:
            # Eliminar el mas viejo
            oldest = self.log_dir / f"genesis.{self.max_files}.log"
            if oldest.exists():
                oldest.unlink()

            # Renombrar en cascada
            for i in range(self.max_files - 1, 0, -1):
                src = self.log_dir / f"genesis.{i}.log"
                dst = self.log_dir / f"genesis.{i+1}.log"
                if src.exists():
                    src.rename(dst)

            # El actual pasa a ser .1
            if self._log_file.exists():
                self._log_file.rename(self.log_dir / "genesis.1.log")

        except Exception:
            pass

    @staticmethod
    def _format_time(timestamp: float) -> str:
        """Formatea timestamp a string legible."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    def get_recent_logs(self, n: int = 50, level: str = "INFO") -> str:
        """Lee las ultimas N lineas del log con nivel minimo."""
        min_level = self.LEVELS.get(level, 0)
        try:
            if not self._log_file.exists():
                return "Sin logs disponibles."

            with open(self._log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Filtrar por nivel
            filtered = []
            for line in lines:
                for lvl, num in self.LEVELS.items():
                    if f"[{lvl}" in line and num >= min_level:
                        filtered.append(line.rstrip())
                        break

            recent = filtered[-n:]
            return "\n".join(recent) if recent else "Sin logs para este nivel."

        except Exception as e:
            return f"Error leyendo logs: {e}"

    def cleanup_old_logs(self, max_age_days: int = 30):
        """
        Elimina logs mas viejos que max_age_days.
        Politica de retencion: 30 dias por defecto.
        """
        now = time.time()
        max_age_secs = max_age_days * 86400
        deleted = 0
        try:
            for f in self.log_dir.iterdir():
                if f.suffix == '.log' and f.is_file():
                    age = now - f.stat().st_mtime
                    if age > max_age_secs:
                        f.unlink()
                        deleted += 1
            if deleted > 0:
                self.log("INFO", "logger", f"Retencion: {deleted} logs eliminados (>{max_age_days} dias)")
        except Exception:
            pass
        return deleted

    def status(self) -> str:
        """Resumen para /status."""
        uptime = time.time() - self._session_start
        uptime_min = uptime / 60

        size_kb = 0
        if self._log_file.exists():
            size_kb = self._log_file.stat().st_size / 1024

        return (
            f"  Mensajes loggeados: {self._message_count}\n"
            f"  Uptime sesion: {uptime_min:.0f} min\n"
            f"  Archivo: {size_kb:.1f} KB"
        )


class ModuleLogger:
    """Logger hijo con prefijo de modulo. Interfaz simplificada."""

    def __init__(self, parent: GenesisLogger, module: str):
        self._parent = parent
        self._module = module

    def debug(self, message: str):
        self._parent.log("DEBUG", self._module, message)

    def info(self, message: str):
        self._parent.log("INFO", self._module, message)

    def error(self, message: str):
        self._parent.log("ERROR", self._module, message)
