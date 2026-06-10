"""
GENESIS Action Tracker — Registra todas las acciones ejecutadas.

Mantiene un log persistente de:
- Herramientas usadas (archivos creados, comandos ejecutados)
- Paquetes instalados
- Proyectos generados
- Errores corregidos automaticamente

Esto permite:
1. Saber exactamente qué hizo Genesis en cada sesión
2. No repetir trabajo ya hecho
3. Ofrecer contexto al LLM sobre acciones previas
"""
import json
import time
from pathlib import Path
from typing import Optional


class ActionTracker:
    """Rastrea todas las acciones de Genesis para persistencia y contexto."""

    def __init__(self, base_dir: str = "memory_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.log_file = self.base_dir / "action_log.json"
        self.actions: list[dict] = []
        self.session_start = time.time()
        self.session_id = f"session_{int(self.session_start)}"
        self._installed_packages: set[str] = set()
        self._created_files: list[str] = []
        self._created_dirs: list[str] = []
        self._load()

    def _load(self):
        """Carga historial de acciones previas."""
        try:
            if self.log_file.exists():
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
                self.actions = data.get("actions", [])[-500:]  # Mantener últimas 500
                self._installed_packages = set(data.get("installed_packages", []))
            else:
                self.actions = []
                self._installed_packages = set()
        except Exception:
            self.actions = []
            self._installed_packages = set()

    def save(self):
        """Persiste el log de acciones a disco."""
        try:
            data = {
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_actions": len(self.actions),
                "installed_packages": sorted(self._installed_packages),
                "actions": self.actions[-500:],
            }
            self.log_file.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def log_tool(self, tool_name: str, argument: str, result: str,
                 success: bool = True):
        """Registra el uso de una herramienta."""
        action = {
            "type": "tool",
            "tool": tool_name,
            "argument": argument[:200],
            "result_preview": result[:200],
            "success": success,
            "timestamp": time.time(),
            "session": self.session_id,
        }
        self.actions.append(action)

        # Rastrear archivos creados
        if tool_name == "escribir" and success:
            path = argument.split("|||")[0].strip() if "|||" in argument else argument
            self._created_files.append(path.strip())
        elif tool_name == "crear_carpeta" and success:
            self._created_dirs.append(argument.strip())

    def log_pip_install(self, package: str, success: bool = True):
        """Registra instalación de paquete pip."""
        action = {
            "type": "pip_install",
            "package": package,
            "success": success,
            "timestamp": time.time(),
            "session": self.session_id,
        }
        self.actions.append(action)
        if success:
            self._installed_packages.add(package)

    def log_project_created(self, path: str, files: list[str]):
        """Registra creación de un proyecto multi-archivo."""
        action = {
            "type": "project_created",
            "path": path,
            "files": files,
            "file_count": len(files),
            "timestamp": time.time(),
            "session": self.session_id,
        }
        self.actions.append(action)
        self._created_dirs.append(path)
        for f in files:
            self._created_files.append(f"{path}/{f}")

    def log_auto_fix(self, error_type: str, fix_description: str):
        """Registra corrección automática (pip install, directorio creado, etc)."""
        action = {
            "type": "auto_fix",
            "error_type": error_type,
            "fix": fix_description,
            "timestamp": time.time(),
            "session": self.session_id,
        }
        self.actions.append(action)

    def is_package_installed(self, package: str) -> bool:
        """Verifica si un paquete fue instalado por Genesis."""
        return package.lower() in {p.lower() for p in self._installed_packages}

    def get_session_summary(self) -> str:
        """Resumen de acciones de la sesión actual."""
        session_actions = [a for a in self.actions if a.get("session") == self.session_id]
        if not session_actions:
            return ""

        tools_used = {}
        files_created = 0
        packages_installed = []
        projects = []

        for a in session_actions:
            if a["type"] == "tool":
                tools_used[a["tool"]] = tools_used.get(a["tool"], 0) + 1
                if a["tool"] == "escribir":
                    files_created += 1
            elif a["type"] == "pip_install" and a["success"]:
                packages_installed.append(a["package"])
            elif a["type"] == "project_created":
                projects.append(a["path"])

        lines = ["[ACCIONES DE ESTA SESION]:"]
        if tools_used:
            tools_str = ", ".join(f"{k}:{v}" for k, v in sorted(tools_used.items()))
            lines.append(f"- Herramientas: {tools_str}")
        if files_created:
            lines.append(f"- Archivos creados: {files_created}")
        if packages_installed:
            lines.append(f"- Paquetes instalados: {', '.join(packages_installed)}")
        if projects:
            lines.append(f"- Proyectos: {', '.join(projects)}")
        return "\n".join(lines)

    def get_recent_context(self, max_actions: int = 10) -> str:
        """Genera contexto de acciones recientes para el system prompt."""
        recent = self.actions[-max_actions:]
        if not recent:
            return ""

        lines = ["[ACCIONES RECIENTES DE GENESIS]:"]
        for a in recent:
            ts = time.strftime("%H:%M", time.localtime(a["timestamp"]))
            if a["type"] == "tool":
                status = "OK" if a["success"] else "FAIL"
                lines.append(f"  [{ts}] {a['tool']}: {a['argument'][:60]} → {status}")
            elif a["type"] == "pip_install":
                status = "instalado" if a["success"] else "falló"
                lines.append(f"  [{ts}] pip install {a['package']} → {status}")
            elif a["type"] == "project_created":
                lines.append(f"  [{ts}] Proyecto: {a['path']} ({a['file_count']} archivos)")
            elif a["type"] == "auto_fix":
                lines.append(f"  [{ts}] Auto-fix: {a['fix'][:80]}")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Estadísticas del tracker."""
        return {
            "total_actions": len(self.actions),
            "installed_packages": len(self._installed_packages),
            "created_files": len(self._created_files),
            "created_dirs": len(self._created_dirs),
        }

    def status(self) -> str:
        """Estado actual del tracker."""
        stats = self.get_stats()
        return (
            f"ActionTracker: {stats['total_actions']} acciones, "
            f"{stats['installed_packages']} paquetes, "
            f"{stats['created_files']} archivos creados"
        )

    def clear(self):
        """Limpia historial (preserva paquetes instalados)."""
        self.actions = []
        self._created_files = []
        self._created_dirs = []
        self.save()

    def generate_report(self) -> str:
        """Genera reporte completo."""
        stats = self.get_stats()
        recent = self.get_recent_context(20)
        return (
            f"=== ActionTracker Report ===\n"
            f"Total acciones: {stats['total_actions']}\n"
            f"Paquetes instalados: {', '.join(sorted(self._installed_packages)) or 'ninguno'}\n"
            f"Archivos creados: {stats['created_files']}\n"
            f"\n{recent}"
        )
