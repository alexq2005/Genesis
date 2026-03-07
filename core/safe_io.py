"""
GENESIS Safe I/O — Lectura/escritura segura de archivos JSON.

Problemas resueltos:
1. Thread Safety: El heartbeat corre en un thread separado y puede escribir
   JSON al mismo tiempo que el thread principal. Sin locks, el archivo se
   corrompe (escrituras parciales, JSON roto).

2. Backups automaticos: Antes de cada escritura, se crea un backup del
   archivo anterior. Si el nuevo write falla a mitad, el backup esta intacto.

3. Escritura atomica: Se escribe a un archivo temporal y luego se renombra.
   El rename es atomico en la mayoria de OS, evitando archivos corruptos.

Uso:
    from core.safe_io import safe_read_json, safe_write_json

    data = safe_read_json(Path("data.json"), default=[])
    safe_write_json(Path("data.json"), data)
"""
import json
import time
import shutil
import threading
from pathlib import Path
from typing import Any, Optional


# Lock global por archivo — evita que dos threads escriban al mismo archivo
_file_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()  # Lock para proteger el dict de locks


def _get_lock(filepath: Path) -> threading.Lock:
    """Obtiene o crea un lock para un archivo especifico."""
    key = str(filepath.resolve())
    with _locks_lock:
        if key not in _file_locks:
            _file_locks[key] = threading.Lock()
        return _file_locks[key]


def safe_read_json(filepath: Path, default: Any = None) -> Any:
    """
    Lee un archivo JSON de forma thread-safe.

    Args:
        filepath: Ruta al archivo JSON
        default: Valor por defecto si el archivo no existe o esta corrupto

    Returns:
        Datos deserializados del JSON, o el default
    """
    lock = _get_lock(filepath)
    with lock:
        if not filepath.exists():
            return default if default is not None else []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, OSError):
            # Intentar leer del backup
            backup = filepath.with_suffix(filepath.suffix + ".bak")
            if backup.exists():
                try:
                    with open(backup, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError, OSError):
                    pass

            return default if default is not None else []


def safe_write_json(filepath: Path, data: Any,
                    create_backup: bool = True) -> bool:
    """
    Escribe datos a JSON de forma thread-safe y atomica.

    Proceso:
    1. Adquiere lock del archivo
    2. Crea backup del archivo actual (si existe)
    3. Escribe a archivo temporal (.tmp)
    4. Renombra temporal al archivo final (atomico)

    Args:
        filepath: Ruta al archivo JSON
        data: Datos a serializar
        create_backup: Si crear backup del archivo anterior

    Returns:
        True si la escritura fue exitosa
    """
    lock = _get_lock(filepath)
    with lock:
        try:
            # Asegurar que el directorio existe
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Backup del archivo actual
            if create_backup and filepath.exists():
                backup = filepath.with_suffix(filepath.suffix + ".bak")
                try:
                    shutil.copy2(filepath, backup)
                except Exception:
                    pass  # No fallar si el backup falla

            # Escribir a temporal
            tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Renombrar (atomico en la mayoria de OS)
            tmp_path.replace(filepath)

            return True

        except Exception:
            # Limpiar temporal si quedo
            tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            return False


class BackupManager:
    """
    Gestor de backups automaticos para los datos de Genesis.

    Crea snapshots periodicos de todos los archivos JSON de datos.
    Permite restaurar a un punto anterior si algo sale mal.
    """

    def __init__(self, data_dirs: list[Path],
                 backup_dir: Path = None,
                 max_backups: int = 5):
        """
        Args:
            data_dirs: Directorios que contienen los JSON a respaldar
            backup_dir: Donde guardar los backups
            max_backups: Cantidad maxima de backups a mantener
        """
        self.data_dirs = data_dirs
        self.backup_dir = backup_dir or Path(__file__).parent.parent / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        self.max_backups = max_backups

    def create_backup(self, label: str = "") -> Optional[Path]:
        """
        Crea un backup completo de todos los datos.

        Args:
            label: Etiqueta opcional para el backup (ej: "pre_evolution")

        Returns:
            Path al directorio del backup, o None si fallo
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"backup_{timestamp}"
        if label:
            name += f"_{label}"

        backup_path = self.backup_dir / name

        try:
            backup_path.mkdir(exist_ok=True)
            files_backed = 0

            for data_dir in self.data_dirs:
                if not data_dir.exists():
                    continue

                for json_file in data_dir.glob("*.json"):
                    try:
                        # Usar safe_read para no interferir con threads
                        dest = backup_path / f"{data_dir.name}_{json_file.name}"
                        shutil.copy2(json_file, dest)
                        files_backed += 1
                    except Exception:
                        continue

            if files_backed == 0:
                # No habia nada que respaldar
                backup_path.rmdir()
                return None

            # Limpiar backups viejos
            self._cleanup()

            return backup_path

        except Exception:
            return None

    def restore_backup(self, backup_name: str) -> bool:
        """
        Restaura un backup especifico.

        Args:
            backup_name: Nombre del directorio de backup

        Returns:
            True si la restauracion fue exitosa
        """
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return False

        try:
            for backup_file in backup_path.glob("*.json"):
                # Parsear nombre: directorio_archivo.json
                parts = backup_file.name.split("_", 1)
                if len(parts) != 2:
                    continue

                dir_name, file_name = parts
                # Buscar el directorio de datos correcto
                for data_dir in self.data_dirs:
                    if data_dir.name == dir_name:
                        dest = data_dir / file_name
                        safe_write_json(dest, safe_read_json(backup_file))
                        break

            return True

        except Exception:
            return False

    def list_backups(self) -> list[dict]:
        """Lista los backups disponibles."""
        backups = []
        for item in sorted(self.backup_dir.iterdir(), reverse=True):
            if item.is_dir() and item.name.startswith("backup_"):
                files = list(item.glob("*.json"))
                size = sum(f.stat().st_size for f in files)
                backups.append({
                    "name": item.name,
                    "files": len(files),
                    "size_kb": size / 1024,
                    "created": item.stat().st_mtime,
                })
        return backups

    def _cleanup(self):
        """Elimina backups viejos si hay mas del maximo."""
        backups = sorted(
            [d for d in self.backup_dir.iterdir()
             if d.is_dir() and d.name.startswith("backup_")],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[self.max_backups:]:
            try:
                shutil.rmtree(old_backup)
            except Exception:
                pass

    def status(self) -> str:
        """Resumen para /status."""
        backups = self.list_backups()
        if not backups:
            return "  Sin backups"
        last = backups[0]
        t = time.strftime("%d/%m %H:%M", time.localtime(last["created"]))
        return (
            f"  Backups: {len(backups)}\n"
            f"  Ultimo: {t} ({last['files']} archivos, {last['size_kb']:.1f} KB)"
        )
