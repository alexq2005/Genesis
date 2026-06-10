"""
GENESIS — Device Tools
Herramientas avanzadas para control total del dispositivo local.
Incluye gestion de archivos, analisis de disco, procesos, clipboard, etc.
"""
import os
import shutil
import hashlib
import subprocess
import platform
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


# ==============================================================
# CONSTANTES DE SEGURIDAD
# ==============================================================
PROTECTED_DIRS = {
    "windows", "system32", "syswow64", "winsxs",
    "boot", "recovery", "programdata",
}

PROTECTED_PATHS = {
    "C:\\Windows", "C:\\$Recycle.Bin",
    "/boot", "/usr", "/bin", "/sbin", "/lib",
}

ORGANIZE_CATEGORIES = {
    "Imagenes": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".raw", ".heic"},
    "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus"},
    "Documentos": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf"},
    "Texto": {".txt", ".md", ".csv", ".log", ".json", ".xml", ".yaml", ".yml", ".ini", ".cfg", ".conf"},
    "Codigo": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".java", ".cpp", ".c", ".h", ".cs",
               ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".sql", ".sh", ".bat", ".ps1"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tar.gz", ".tgz"},
    "Ejecutables": {".exe", ".msi", ".dmg", ".app", ".deb", ".rpm", ".apk"},
    "Fuentes": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "3D_Diseno": {".psd", ".ai", ".sketch", ".fig", ".xd", ".blend", ".obj", ".stl", ".fbx"},
    "Datos": {".db", ".sqlite", ".sqlite3", ".mdb", ".accdb", ".bak"},
    "Torrents": {".torrent", ".magnet"},
}


def _is_protected(path: str) -> bool:
    """Verifica si una ruta esta protegida contra modificacion."""
    p = Path(path).resolve()
    p_str = str(p).lower()
    for protected in PROTECTED_DIRS:
        if f"\\{protected}\\" in p_str or f"/{protected}/" in p_str:
            return True
    for protected in PROTECTED_PATHS:
        if p_str.startswith(protected.lower()):
            return True
    return False


def _format_size(size_bytes: int) -> str:
    """Formatea bytes a unidad legible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def _get_file_info(path: str) -> dict:
    """Obtiene informacion detallada de un archivo."""
    p = Path(path)
    stat = p.stat()
    return {
        "nombre": p.name,
        "ruta": str(p),
        "tamano": _format_size(stat.st_size),
        "tamano_bytes": stat.st_size,
        "extension": p.suffix.lower(),
        "modificado": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "creado": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M"),
        "es_directorio": p.is_dir(),
    }


# ==============================================================
# FILE MANAGEMENT — Mover, Copiar, Renombrar, Eliminar
# ==============================================================

class FileManager:
    """Gestión avanzada de archivos y carpetas."""

    @staticmethod
    def move(source: str, destination: str) -> str:
        """Mueve archivo o carpeta."""
        src = Path(source).resolve()
        if not src.exists():
            return f"[ERROR] No existe: {source}"
        if _is_protected(str(src)):
            return f"[ERROR] Ruta protegida: {source}"

        dst = Path(destination).resolve()
        if dst.is_dir():
            dst = dst / src.name

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"Movido: {src.name} → {dst}"
        except Exception as e:
            return f"[ERROR] No se pudo mover: {e}"

    @staticmethod
    def copy(source: str, destination: str) -> str:
        """Copia archivo o carpeta."""
        src = Path(source).resolve()
        if not src.exists():
            return f"[ERROR] No existe: {source}"

        dst = Path(destination).resolve()
        if dst.is_dir():
            dst = dst / src.name

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            return f"Copiado: {src.name} → {dst} ({_format_size(src.stat().st_size if src.is_file() else 0)})"
        except Exception as e:
            return f"[ERROR] No se pudo copiar: {e}"

    @staticmethod
    def rename(path: str, new_name: str) -> str:
        """Renombra archivo o carpeta."""
        p = Path(path).resolve()
        if not p.exists():
            return f"[ERROR] No existe: {path}"
        if _is_protected(str(p)):
            return f"[ERROR] Ruta protegida: {path}"

        new_path = p.parent / new_name
        if new_path.exists():
            return f"[ERROR] Ya existe: {new_name}"

        try:
            p.rename(new_path)
            return f"Renombrado: {p.name} → {new_name}"
        except Exception as e:
            return f"[ERROR] No se pudo renombrar: {e}"

    @staticmethod
    def delete(path: str) -> str:
        """Elimina archivo o carpeta (a la papelera si es posible)."""
        p = Path(path).resolve()
        if not p.exists():
            return f"[ERROR] No existe: {path}"
        if _is_protected(str(p)):
            return f"[ERROR] Ruta protegida, no se puede eliminar: {path}"

        try:
            # Intentar enviar a papelera primero (requiere send2trash)
            try:
                from send2trash import send2trash
                send2trash(str(p))
                return f"Enviado a papelera: {p.name}"
            except ImportError:
                pass

            # Fallback: eliminar directamente
            if p.is_dir():
                shutil.rmtree(str(p))
                return f"Carpeta eliminada: {p.name}"
            else:
                size = _format_size(p.stat().st_size)
                p.unlink()
                return f"Archivo eliminado: {p.name} ({size})"
        except Exception as e:
            return f"[ERROR] No se pudo eliminar: {e}"

    @staticmethod
    def create_folder(path: str) -> str:
        """Crea una carpeta (y subcarpetas si es necesario)."""
        try:
            p = Path(path).resolve()
            p.mkdir(parents=True, exist_ok=True)
            return f"Carpeta creada: {p}"
        except Exception as e:
            return f"[ERROR] No se pudo crear carpeta: {e}"

    @staticmethod
    def file_info(path: str) -> str:
        """Obtiene informacion detallada de un archivo o carpeta."""
        p = Path(path).resolve()
        if not p.exists():
            return f"[ERROR] No existe: {path}"

        try:
            info = _get_file_info(str(p))
            lines = [
                f"Nombre: {info['nombre']}",
                f"Ruta: {info['ruta']}",
                f"Tipo: {'Carpeta' if info['es_directorio'] else info['extension']}",
                f"Tamaño: {info['tamano']}",
                f"Modificado: {info['modificado']}",
                f"Creado: {info['creado']}",
            ]

            if p.is_dir():
                items = list(p.iterdir())
                files = [i for i in items if i.is_file()]
                dirs = [i for i in items if i.is_dir()]
                total_size = sum(f.stat().st_size for f in files)
                lines.append(f"Contenido: {len(files)} archivos, {len(dirs)} carpetas")
                lines.append(f"Tamaño total (nivel 1): {_format_size(total_size)}")

            return "\n".join(lines)
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# FILE SEARCH — Buscar archivos por nombre, tipo, tamaño
# ==============================================================

class FileSearcher:
    """Busqueda avanzada de archivos en el sistema."""

    @staticmethod
    def search(query: str, path: str = None, max_results: int = 50) -> str:
        """
        Busca archivos por nombre/patron.
        Soporta: nombre parcial, extension (*.py), tamaño (>100MB).
        """
        search_path = Path(path) if path else Path.home()
        if not search_path.exists():
            return f"[ERROR] Ruta no existe: {path}"

        results = []
        query_lower = query.lower().strip()

        # Detectar busqueda por extension
        by_extension = query_lower.startswith("*.") or query_lower.startswith(".")
        ext_filter = query_lower.lstrip("*") if by_extension else None

        # Detectar busqueda por tamaño
        size_filter = None
        if query_lower.startswith(">"):
            size_str = query_lower[1:].strip().upper()
            multiplier = 1
            if size_str.endswith("GB"):
                multiplier = 1024**3
                size_str = size_str[:-2]
            elif size_str.endswith("MB"):
                multiplier = 1024**2
                size_str = size_str[:-2]
            elif size_str.endswith("KB"):
                multiplier = 1024
                size_str = size_str[:-2]
            try:
                size_filter = float(size_str) * multiplier
            except ValueError:
                pass

        try:
            count = 0
            for root, dirs, files in os.walk(str(search_path)):
                # Skip protected/system dirs
                dirs[:] = [d for d in dirs if d.lower() not in
                          {'__pycache__', '.git', 'node_modules', '.venv',
                           'windows', 'system32', '$recycle.bin', 'appdata'}]

                for fname in files:
                    count += 1
                    if count > 500000:  # Safety limit
                        break

                    fpath = os.path.join(root, fname)

                    try:
                        if size_filter:
                            if os.path.getsize(fpath) >= size_filter:
                                info = _get_file_info(fpath)
                                results.append(info)
                        elif ext_filter:
                            if fname.lower().endswith(ext_filter):
                                info = _get_file_info(fpath)
                                results.append(info)
                        else:
                            if query_lower in fname.lower():
                                info = _get_file_info(fpath)
                                results.append(info)
                    except (PermissionError, OSError):
                        continue

                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break

        except Exception as e:
            return f"[ERROR] Error buscando: {e}"

        if not results:
            return f"No se encontraron archivos para: {query}"

        # Ordenar por tamaño descendente
        results.sort(key=lambda x: x['tamano_bytes'], reverse=True)

        lines = [f"Encontrados: {len(results)} archivos (busqueda: '{query}' en {search_path})\n"]
        for r in results:
            lines.append(f"  {r['tamano']:>10s}  {r['modificado']}  {r['ruta']}")

        return "\n".join(lines)


# ==============================================================
# FILE ORGANIZER — Organizar archivos por tipo
# ==============================================================

class FileOrganizer:
    """Organiza archivos automaticamente por categoria."""

    @staticmethod
    def organize(path: str, dry_run: bool = False) -> str:
        """
        Organiza archivos de una carpeta por tipo.
        dry_run=True solo muestra que haria sin mover nada.
        """
        p = Path(path).resolve()
        if not p.exists() or not p.is_dir():
            return f"[ERROR] No es una carpeta valida: {path}"
        if _is_protected(str(p)):
            return f"[ERROR] Carpeta protegida: {path}"

        # Clasificar archivos
        classified = {}
        unclassified = []

        for item in p.iterdir():
            if item.is_dir():
                continue
            ext = item.suffix.lower()
            category = None
            for cat, extensions in ORGANIZE_CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break

            if category:
                classified.setdefault(category, []).append(item)
            else:
                unclassified.append(item)

        if not classified and not unclassified:
            return "La carpeta no tiene archivos para organizar."

        lines = [f"{'[SIMULACION] ' if dry_run else ''}Organizando: {p}\n"]
        moved_count = 0

        for category, files in sorted(classified.items()):
            cat_dir = p / category
            lines.append(f"\n📁 {category}/ ({len(files)} archivos)")

            if not dry_run:
                cat_dir.mkdir(exist_ok=True)

            for f in files:
                dest = cat_dir / f.name
                if dest.exists():
                    # Evitar sobreescritura
                    stem = f.stem
                    suffix = f.suffix
                    counter = 1
                    while dest.exists():
                        dest = cat_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                lines.append(f"  → {f.name}")
                if not dry_run:
                    try:
                        shutil.move(str(f), str(dest))
                        moved_count += 1
                    except Exception as e:
                        lines.append(f"    [ERROR] {e}")

        if unclassified:
            lines.append(f"\nSin clasificar ({len(unclassified)} archivos):")
            for f in unclassified[:20]:
                lines.append(f"  ? {f.name} ({f.suffix})")

        if not dry_run:
            lines.append(f"\nTotal movidos: {moved_count} archivos en {len(classified)} categorias")
        else:
            total = sum(len(files) for files in classified.values())
            lines.append(f"\n[SIMULACION] Se moverian {total} archivos en {len(classified)} categorias")
            lines.append("Ejecuta sin 'simular' para aplicar los cambios.")

        return "\n".join(lines)


# ==============================================================
# DISK ANALYZER — Analisis de uso de disco
# ==============================================================

class DiskAnalyzer:
    """Analiza uso de disco, archivos grandes, limpieza."""

    @staticmethod
    def analyze(path: str = None, top_n: int = 20) -> str:
        """Analiza una carpeta: tamano total, archivos mas grandes, distribucion."""
        search_path = Path(path) if path else Path.home()
        if not search_path.exists():
            return f"[ERROR] No existe: {path}"

        total_size = 0
        file_count = 0
        dir_count = 0
        ext_stats = {}
        large_files = []
        old_files = []
        now = time.time()

        try:
            for root, dirs, files in os.walk(str(search_path)):
                dirs[:] = [d for d in dirs if d.lower() not in
                          {'__pycache__', '.git', 'node_modules', '.venv', '$recycle.bin'}]
                dir_count += len(dirs)

                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        stat = os.stat(fpath)
                        size = stat.st_size
                        total_size += size
                        file_count += 1

                        ext = Path(fname).suffix.lower() or "(sin ext)"
                        ext_stats.setdefault(ext, {"count": 0, "size": 0})
                        ext_stats[ext]["count"] += 1
                        ext_stats[ext]["size"] += size

                        # Track archivos grandes (>10 MB)
                        if size > 10 * 1024 * 1024:
                            large_files.append((fpath, size, stat.st_mtime))

                        # Archivos sin acceder en >1 año
                        if (now - stat.st_atime) > 365 * 24 * 3600:
                            if size > 1024 * 1024:  # Solo >1MB
                                old_files.append((fpath, size, stat.st_atime))

                    except (PermissionError, OSError):
                        continue

        except Exception as e:
            return f"[ERROR] {e}"

        # Disk usage global
        try:
            usage = shutil.disk_usage(str(search_path))
            disk_total = _format_size(usage.total)
            disk_used = _format_size(usage.used)
            disk_free = _format_size(usage.free)
            disk_pct = (usage.used / usage.total * 100) if usage.total > 0 else 0
        except Exception:
            disk_total = disk_used = disk_free = "N/A"
            disk_pct = 0

        lines = [
            f"Analisis de disco: {search_path}",
            f"{'=' * 50}",
            f"Disco: {disk_used} usados / {disk_total} total ({disk_pct:.1f}%) — {disk_free} libre",
            f"Carpeta analizada: {_format_size(total_size)}",
            f"Archivos: {file_count:,} | Carpetas: {dir_count:,}",
            "",
        ]

        # Top extensiones por tamano
        sorted_exts = sorted(ext_stats.items(), key=lambda x: x[1]["size"], reverse=True)[:15]
        lines.append("Distribucion por tipo:")
        for ext, data in sorted_exts:
            pct = (data["size"] / total_size * 100) if total_size > 0 else 0
            lines.append(f"  {ext:>10s}  {_format_size(data['size']):>10s}  {data['count']:>5,} archivos  ({pct:.1f}%)")

        # Archivos mas grandes
        if large_files:
            large_files.sort(key=lambda x: x[1], reverse=True)
            lines.append(f"\nArchivos mas grandes (top {min(top_n, len(large_files))}):")
            for fpath, size, mtime in large_files[:top_n]:
                date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                lines.append(f"  {_format_size(size):>10s}  {date}  {fpath}")

        # Archivos viejos
        if old_files:
            old_files.sort(key=lambda x: x[1], reverse=True)
            old_total = sum(s for _, s, _ in old_files)
            lines.append(f"\nArchivos sin acceder >1 ano ({len(old_files)}, {_format_size(old_total)} total):")
            for fpath, size, atime in old_files[:10]:
                date = datetime.fromtimestamp(atime).strftime("%Y-%m-%d")
                lines.append(f"  {_format_size(size):>10s}  ultimo acceso: {date}  {fpath}")

        return "\n".join(lines)


# ==============================================================
# DUPLICATE FINDER — Encontrar archivos duplicados
# ==============================================================

class DuplicateFinder:
    """Encuentra archivos duplicados por hash."""

    @staticmethod
    def find(path: str, min_size: int = 1024) -> str:
        """Encuentra archivos duplicados en una carpeta."""
        search_path = Path(path).resolve()
        if not search_path.exists():
            return f"[ERROR] No existe: {path}"

        # Paso 1: Agrupar por tamano
        size_groups = {}
        file_count = 0
        for root, dirs, files in os.walk(str(search_path)):
            dirs[:] = [d for d in dirs if d.lower() not in
                      {'__pycache__', '.git', 'node_modules', '.venv', '$recycle.bin'}]
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                    if size >= min_size:
                        size_groups.setdefault(size, []).append(fpath)
                        file_count += 1
                except (PermissionError, OSError):
                    continue

        # Paso 2: Hash parcial de archivos con mismo tamano
        hash_groups = {}
        candidates = {s: files for s, files in size_groups.items() if len(files) > 1}

        for size, files in candidates.items():
            for fpath in files:
                try:
                    h = hashlib.md5()
                    with open(fpath, 'rb') as f:
                        # Hash primeros 8KB + ultimos 8KB para velocidad
                        chunk = f.read(8192)
                        h.update(chunk)
                        if size > 8192:
                            f.seek(-8192, 2)
                            h.update(f.read(8192))
                    key = f"{size}_{h.hexdigest()}"
                    hash_groups.setdefault(key, []).append(fpath)
                except (PermissionError, OSError):
                    continue

        # Filtrar solo grupos con duplicados
        duplicates = {k: v for k, v in hash_groups.items() if len(v) > 1}

        if not duplicates:
            return f"No se encontraron duplicados en {search_path} ({file_count:,} archivos analizados)"

        total_waste = 0
        lines = [f"Duplicados encontrados en: {search_path}\n"]

        for key, files in sorted(duplicates.items(), key=lambda x: int(x[0].split('_')[0]), reverse=True):
            size = int(key.split('_')[0])
            waste = size * (len(files) - 1)
            total_waste += waste

            lines.append(f"[{_format_size(size)}] x{len(files)} copias (desperdicio: {_format_size(waste)})")
            for f in files:
                lines.append(f"  - {f}")
            lines.append("")

        lines.append(f"Total: {len(duplicates)} grupos de duplicados")
        lines.append(f"Espacio desperdiciado: {_format_size(total_waste)}")

        return "\n".join(lines)


# ==============================================================
# PROCESS MANAGER — Gestión de procesos
# ==============================================================

class ProcessManager:
    """Gestión de procesos del sistema."""

    @staticmethod
    def list_processes(filter_name: str = None) -> str:
        """Lista procesos activos, opcionalmente filtrados por nombre."""
        try:
            if platform.system() == "Windows":
                cmd = 'tasklist /FO CSV /NH'
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=15
                )
                lines = ["PID       Memoria     Nombre"]
                lines.append("-" * 50)

                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.strip('"').split('","')
                    if len(parts) >= 5:
                        name = parts[0]
                        pid = parts[1]
                        mem = parts[4]

                        if filter_name and filter_name.lower() not in name.lower():
                            continue

                        lines.append(f"{pid:>8s}  {mem:>12s}  {name}")

                return "\n".join(lines[:100])  # Limit output
            else:
                cmd = "ps aux --sort=-%mem | head -50"
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=15
                )
                return result.stdout

        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def kill_process(pid_or_name: str) -> str:
        """Termina un proceso por PID o nombre."""
        if _is_protected(pid_or_name):
            return "[ERROR] No se puede terminar procesos del sistema."

        import re as _re
        try:
            if platform.system() == "Windows":
                if pid_or_name.isdigit():
                    result = subprocess.run(
                        ['taskkill', '/F', '/PID', pid_or_name],
                        capture_output=True, text=True, timeout=10
                    )
                else:
                    # Sanitizar: solo letras, numeros, puntos, guiones, espacios
                    safe_name = _re.sub(r'[^a-zA-Z0-9_.\- ]', '', pid_or_name).strip()
                    if not safe_name:
                        return "[ERROR] Nombre de proceso invalido."
                    result = subprocess.run(
                        ['taskkill', '/F', '/IM', safe_name],
                        capture_output=True, text=True, timeout=10
                    )
                return result.stdout.strip() or result.stderr.strip()
            else:
                if pid_or_name.isdigit():
                    os.kill(int(pid_or_name), 15)
                    return f"Proceso {pid_or_name} terminado"
                else:
                    safe_name = _re.sub(r'[^a-zA-Z0-9_.\- ]', '', pid_or_name).strip()
                    if not safe_name:
                        return "[ERROR] Nombre de proceso invalido."
                    result = subprocess.run(
                        ['pkill', '-f', safe_name],
                        capture_output=True, text=True, timeout=10
                    )
                    return result.stdout.strip() or f"Proceso '{safe_name}' terminado"
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# APP LAUNCHER — Abrir archivos y aplicaciones
# ==============================================================

class AppLauncher:
    """Abre archivos y aplicaciones."""

    # Comandos del sistema Windows que SIEMPRE funcionan con cmd /c start
    # (están en PATH o son URI schemes reconocidos)
    _WINDOWS_SYSTEM_APPS = {
        "calc", "notepad", "mspaint", "cmd", "powershell", "pwsh",
        "explorer", "taskmgr", "resmon", "perfmon", "regedit", "msconfig",
        "control", "dxdiag", "winver", "snippingtool", "write", "wordpad",
        "magnify", "osk", "charmap", "cleanmgr", "eventvwr",
    }

    # URI schemes que Windows puede lanzar directamente
    _URI_SCHEMES = ("ms-settings:", "shell:", "ms-clock:", "ms-calculator:",
                    "mailto:", "tel:", "skype:", "steam://", "https://",
                    "http://", "file://")

    @staticmethod
    def _is_windows_system_app(target: str) -> bool:
        """Determina si el target es una app/comando del sistema Windows."""
        t = target.strip().lower()
        # URI schemes
        if any(t.startswith(scheme) for scheme in AppLauncher._URI_SCHEMES):
            return True
        # Quitar extensión .exe si la tiene para matchear con whitelist
        base = t.replace(".exe", "").strip()
        return base in AppLauncher._WINDOWS_SYSTEM_APPS

    @staticmethod
    def _find_in_path(target: str) -> str:
        """Busca el target en PATH. Retorna ruta completa o None."""
        import shutil
        # shutil.which respeta PATH y PATHEXT (encuentra .exe, .bat, .cmd, etc.)
        found = shutil.which(target)
        return found if found else None

    @staticmethod
    def resolve_lnk_target(lnk_path: str) -> str:
        """
        Resuelve un .lnk (shortcut) a su ejecutable target usando COM.
        Retorna la ruta al .exe real, o None si no se puede resolver.
        Útil para verificar que un shortcut apunta a algo que existe antes de lanzar.
        """
        if not lnk_path or not lnk_path.lower().endswith('.lnk'):
            return None
        try:
            # Usar pywin32/winshell si disponible, sino parsing binario básico
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            try:
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(lnk_path)
                target = shortcut.Targetpath
                return target if target and os.path.exists(target) else None
            finally:
                pythoncom.CoUninitialize()
        except ImportError:
            # Fallback: pywin32 no instalado, retornar None (el caller hará os.startfile que funciona)
            return None
        except Exception:
            return None

    @staticmethod
    def open(target: str) -> str:
        """
        Abre un archivo con su programa predeterminado o lanza una app.

        Orden de intentos:
        1. Ruta de archivo/carpeta existente → os.startfile (siempre funciona)
        2. URI scheme (ms-settings:, steam://) → cmd /c start (nativo Windows)
        3. App del sistema en whitelist (calc, notepad) → cmd /c start
        4. Ejecutable en PATH → subprocess.Popen directo
        5. Fallo explícito (NO intentar cmd /c start con apps de usuario — es silencioso)
        """
        try:
            p = Path(target).resolve()

            # CASO 1: Archivo o carpeta que existe
            if p.exists():
                if platform.system() == "Windows":
                    os.startfile(str(p))
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", str(p)])
                else:
                    subprocess.Popen(["xdg-open", str(p)])
                return f"Abriendo: {p.name}"

            # Solo Windows para el resto — otras plataformas usan subprocess directo
            if platform.system() != "Windows":
                import re as _re
                safe_target = _re.sub(r'[^a-zA-Z0-9_.\-\\ /:]', '', target).strip()
                if not safe_target:
                    return "[ERROR] Nombre de aplicacion invalido."
                subprocess.Popen([safe_target])
                return f"Abriendo: {safe_target}"

            # CASO 2 + 3: URI scheme o app del sistema (whitelist)
            if AppLauncher._is_windows_system_app(target):
                import re as _re
                # Para URI schemes permitimos / : . etc.
                safe_target = _re.sub(r'[^\w\s.\-:/@+?&=]', '', target).strip()
                if safe_target:
                    subprocess.Popen(['cmd', '/c', 'start', '', safe_target], shell=False)
                    return f"Abriendo: {safe_target}"

            # CASO 4: Ejecutable en PATH
            found_in_path = AppLauncher._find_in_path(target)
            if found_in_path:
                subprocess.Popen([found_in_path])
                return f"Abriendo: {os.path.basename(found_in_path)}"

            # CASO 5: Fallo explícito — el caller debe usar _discover_installed_app
            # NUNCA hacer cmd /c start con nombre arbitrario: falla silenciosamente
            return f"[ERROR] '{target}' no está en PATH ni es comando del sistema. Probá con el nombre exacto del .exe o usá el Menú Inicio."

        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# CLIPBOARD — Leer/escribir portapapeles
# ==============================================================

class ClipboardManager:
    """Acceso al portapapeles del sistema."""

    @staticmethod
    def read() -> str:
        """Lee el contenido del portapapeles."""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', 'Get-Clipboard'],
                    capture_output=True, text=True, timeout=5
                )
                content = result.stdout.strip()
                if content:
                    return f"Contenido del portapapeles ({len(content)} chars):\n{content[:5000]}"
                return "Portapapeles vacio."
            else:
                result = subprocess.run(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip() or "Portapapeles vacio."
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def write(text: str) -> str:
        """Escribe texto al portapapeles."""
        try:
            if platform.system() == "Windows":
                # Pasar texto via stdin — seguro contra inyeccion
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command',
                     '[Console]::In.ReadToEnd() | Set-Clipboard'],
                    input=text, capture_output=True, text=True, timeout=5
                )
                return f"Copiado al portapapeles ({len(text)} chars)"
            else:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE
                )
                process.communicate(text.encode())
                return f"Copiado al portapapeles ({len(text)} chars)"
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# SCREENSHOT — Captura de pantalla
# ==============================================================

class ScreenCapture:
    """Captura de pantalla."""

    @staticmethod
    def capture(output_path: str = None) -> str:
        """Toma una captura de pantalla."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path.home() / "Desktop" / f"captura_{timestamp}.png")

        try:
            # Intentar con Pillow
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(output_path)
                size = _format_size(Path(output_path).stat().st_size)
                return f"Captura guardada: {output_path} ({img.size[0]}x{img.size[1]}, {size})"
            except ImportError:
                pass

            # Fallback: PowerShell en Windows
            if platform.system() == "Windows":
                # Usar Path().resolve() para sanitizar la ruta
                safe_path = str(Path(output_path).resolve())
                ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save('{safe_path.replace(chr(39), "")}')
"""
                result = subprocess.run(
                    ['powershell', '-NoProfile', '-Command', ps_script],
                    capture_output=True, text=True, timeout=10
                )
                if Path(output_path).exists():
                    size = _format_size(Path(output_path).stat().st_size)
                    return f"Captura guardada: {output_path} ({size})"
                return f"[ERROR] No se pudo capturar: {result.stderr}"

            return "[ERROR] Instala Pillow (pip install Pillow) para capturas."
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# STARTUP APPS — Programas de inicio
# ==============================================================

class StartupManager:
    """Gestión de programas de inicio."""

    @staticmethod
    def list_startup() -> str:
        """Lista programas que se ejecutan al inicio."""
        if platform.system() != "Windows":
            return "Solo disponible en Windows."

        try:
            lines = ["Programas de inicio:\n"]

            # Registry Run keys
            cmd = 'reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" 2>nul'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                lines.append("== Registro (Usuario) ==")
                lines.append(result.stdout.strip())

            cmd = 'reg query "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" 2>nul'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                lines.append("\n== Registro (Sistema) ==")
                lines.append(result.stdout.strip())

            # Startup folder
            startup_dir = Path(os.environ.get('APPDATA', '')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup_dir.exists():
                items = list(startup_dir.iterdir())
                if items:
                    lines.append(f"\n== Carpeta Startup ({startup_dir}) ==")
                    for item in items:
                        lines.append(f"  {item.name}")

            return "\n".join(lines)
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# RECYCLE BIN — Papelera de reciclaje
# ==============================================================

class RecycleBin:
    """Acceso a la papelera de reciclaje."""

    @staticmethod
    def list_items() -> str:
        """Lista los elementos en la papelera de reciclaje."""
        if platform.system() != "Windows":
            return "Solo disponible en Windows."

        try:
            ps_script = """
$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.Namespace(0x0A)
$items = $recycleBin.Items()
$count = ($items | Measure-Object).Count
Write-Output "Papelera de reciclaje: $count elementos"
Write-Output "=================================================="
$items | ForEach-Object {
    $name = $_.Name
    $size = $_.ExtendedProperty('System.Size')
    $date = $_.ExtendedProperty('System.Recycle.DateDeleted')
    $path = $_.ExtendedProperty('System.Recycle.DeletedFrom')
    if ($size) {
        if ($size -gt 1GB) { $sizeStr = "{0:N1} GB" -f ($size/1GB) }
        elseif ($size -gt 1MB) { $sizeStr = "{0:N1} MB" -f ($size/1MB) }
        elseif ($size -gt 1KB) { $sizeStr = "{0:N1} KB" -f ($size/1KB) }
        else { $sizeStr = "$size B" }
    } else { $sizeStr = "---" }
    Write-Output "  $sizeStr | $date | $name | De: $path"
} | Select-Object -First 50
"""
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=15,
                encoding='utf-8', errors='replace'
            )
            output = result.stdout.strip()
            if output:
                return output
            if result.stderr:
                return f"[ERROR] {result.stderr.strip()}"
            return "Papelera de reciclaje vacia."
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def restore(name_filter: str = "") -> str:
        """Restaura elementos de la papelera a su ubicación original."""
        if platform.system() != "Windows":
            return "Solo disponible en Windows."

        try:
            if name_filter:
                # Sanitizar: eliminar caracteres peligrosos para PowerShell
                import re as _re
                name_filter = _re.sub(r"['\"`$(){}\[\];|&<>!]", "", name_filter).strip()
                if not name_filter:
                    return "[ERROR] Nombre de filtro invalido."
                # Restaurar elemento específico por nombre
                ps_script = f"""
$shell = New-Object -ComObject Shell.Application
$recycleBin = $shell.Namespace(0x0A)
$found = $false
$recycleBin.Items() | ForEach-Object {{
    if ($_.Name -like '*{name_filter}*') {{
        $origPath = $_.ExtendedProperty('System.Recycle.DeletedFrom')
        $name = $_.Name
        # MoveHere restaura el archivo a la ubicación original
        $destFolder = $shell.Namespace($origPath)
        if ($destFolder) {{
            $destFolder.MoveHere($_)
            Write-Output "Restaurado: $name -> $origPath"
            $found = $true
        }} else {{
            # Si la carpeta original no existe, crear y restaurar
            New-Item -ItemType Directory -Path $origPath -Force | Out-Null
            $destFolder = $shell.Namespace($origPath)
            $destFolder.MoveHere($_)
            Write-Output "Restaurado: $name -> $origPath (carpeta recreada)"
            $found = $true
        }}
    }}
}}
if (-not $found) {{ Write-Output "No se encontro '$name_filter' en la papelera." }}
"""
            else:
                return "[ERROR] Especifica el nombre del archivo a restaurar."

            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=15,
                encoding='utf-8', errors='replace'
            )
            output = result.stdout.strip()
            if output:
                return output
            if result.stderr:
                return f"[ERROR] {result.stderr.strip()}"
            return "No se pudo restaurar el elemento."
        except Exception as e:
            return f"[ERROR] {e}"

    @staticmethod
    def empty() -> str:
        """Vacia la papelera de reciclaje."""
        if platform.system() != "Windows":
            return "Solo disponible en Windows."
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'],
                capture_output=True, text=True, timeout=30
            )
            return "Papelera de reciclaje vaciada."
        except Exception as e:
            return f"[ERROR] {e}"


# ==============================================================
# DISPATCHER — Registrar todas las herramientas
# ==============================================================

# Instancias globales
file_manager = FileManager()
file_searcher = FileSearcher()
file_organizer = FileOrganizer()
disk_analyzer = DiskAnalyzer()
duplicate_finder = DuplicateFinder()
process_manager = ProcessManager()
app_launcher = AppLauncher()
clipboard_manager = ClipboardManager()
screen_capture = ScreenCapture()
startup_manager = StartupManager()
recycle_bin = RecycleBin()


def execute_device_tool(tool_name: str, tool_arg: str) -> Optional[str]:
    """
    Dispatcher para herramientas de dispositivo.
    Retorna None si el tool_name no es de dispositivo.
    """
    tool_name = tool_name.lower().strip()
    arg = tool_arg.strip()

    if tool_name == "mover":
        parts = arg.split("|||")
        if len(parts) < 2:
            return "[ERROR] Uso: [TOOL:mover] origen ||| destino"
        return file_manager.move(parts[0].strip(), parts[1].strip())

    elif tool_name == "copiar":
        parts = arg.split("|||")
        if len(parts) < 2:
            return "[ERROR] Uso: [TOOL:copiar] origen ||| destino"
        return file_manager.copy(parts[0].strip(), parts[1].strip())

    elif tool_name == "renombrar":
        parts = arg.split("|||")
        if len(parts) < 2:
            return "[ERROR] Uso: [TOOL:renombrar] ruta ||| nuevo_nombre"
        return file_manager.rename(parts[0].strip(), parts[1].strip())

    elif tool_name == "eliminar":
        return file_manager.delete(arg)

    elif tool_name == "crear_carpeta":
        return file_manager.create_folder(arg)

    elif tool_name == "info":
        return file_manager.file_info(arg)

    elif tool_name == "buscar_archivos":
        parts = arg.split("|||")
        if len(parts) >= 2:
            return file_searcher.search(parts[0].strip(), parts[1].strip())
        return file_searcher.search(arg)

    elif tool_name == "organizar":
        dry_run = "simular" in arg.lower()
        path = arg.replace("simular", "").strip()
        return file_organizer.organize(path, dry_run=dry_run)

    elif tool_name == "disco":
        return disk_analyzer.analyze(arg if arg else None)

    elif tool_name == "duplicados":
        return duplicate_finder.find(arg)

    elif tool_name == "procesos":
        return process_manager.list_processes(arg if arg else None)

    elif tool_name == "cerrar_proceso":
        return process_manager.kill_process(arg)

    elif tool_name == "abrir":
        return app_launcher.open(arg)

    elif tool_name == "portapapeles":
        if arg:
            return clipboard_manager.write(arg)
        return clipboard_manager.read()

    elif tool_name == "captura":
        return screen_capture.capture(arg if arg else None)

    elif tool_name == "inicio":
        return startup_manager.list_startup()

    elif tool_name == "papelera":
        if arg.lower() in ("vaciar", "limpiar", "empty"):
            return recycle_bin.empty()
        return recycle_bin.list_items()

    return None  # No es una herramienta de dispositivo


# Descripcion para el system prompt del LLM
DEVICE_TOOLS_DESCRIPTION = """
=== HERRAMIENTAS DE DISPOSITIVO ===
Tienes acceso completo al dispositivo del usuario. Usa estas herramientas:

[TOOL:mover] ruta_origen ||| ruta_destino — Mover archivo/carpeta
[TOOL:copiar] ruta_origen ||| ruta_destino — Copiar archivo/carpeta
[TOOL:renombrar] ruta ||| nuevo_nombre — Renombrar archivo/carpeta
[TOOL:eliminar] ruta — Eliminar archivo/carpeta (papelera si es posible)
[TOOL:crear_carpeta] ruta — Crear carpeta
[TOOL:info] ruta — Info detallada de archivo/carpeta
[TOOL:buscar_archivos] patron — Buscar archivos (nombre, *.ext, o >100MB)
[TOOL:buscar_archivos] patron ||| ruta — Buscar en ruta especifica
[TOOL:organizar] ruta — Organizar carpeta por tipo (Imagenes, Videos, Documentos, etc)
[TOOL:organizar] ruta simular — Ver que haria sin mover nada
[TOOL:disco] ruta — Analisis de disco: uso, archivos grandes, viejos, distribucion
[TOOL:duplicados] ruta — Encontrar archivos duplicados
[TOOL:procesos] — Listar procesos activos
[TOOL:procesos] nombre — Filtrar procesos por nombre
[TOOL:cerrar_proceso] PID_o_nombre — Terminar un proceso
[TOOL:abrir] ruta — Abrir archivo/carpeta con programa predeterminado
[TOOL:portapapeles] — Leer portapapeles
[TOOL:portapapeles] texto — Copiar texto al portapapeles
[TOOL:captura] — Tomar captura de pantalla (guardar en Escritorio)
[TOOL:captura] ruta — Guardar captura en ruta especifica
[TOOL:inicio] — Ver programas de inicio de Windows
"""
