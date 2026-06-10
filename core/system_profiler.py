"""
GENESIS System Profiler — Análisis profundo del sistema.
Software instalado, programas de inicio, variables de entorno,
uso de disco por carpeta, conexiones de red, servicios.
"""
import os
import subprocess
import json
import threading
from datetime import datetime
from typing import Optional


class SystemProfiler:
    """Análisis profundo del sistema operativo."""

    def __init__(self):
        self._lock = threading.RLock()
        self._cache: dict = {}
        self._cache_time: float = 0
        self._cache_ttl: float = 300  # 5 min

    # ── Helpers ──────────────────────────────────────
    @staticmethod
    def _run_ps(command: str, timeout: int = 15) -> str:
        """Ejecuta PowerShell y retorna stdout."""
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace"
            )
            return r.stdout.strip()
        except Exception as e:
            return f"Error: {e}"

    # ── Software instalado ───────────────────────────
    def installed_software(self, limit: int = 30) -> str:
        """Lista software instalado (registry-based)."""
        cmd = (
            "Get-ItemProperty "
            "'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*', "
            "'HKLM:\\Software\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*' "
            "-ErrorAction SilentlyContinue | "
            "Where-Object { $_.DisplayName } | "
            "Sort-Object DisplayName | "
            "Select-Object DisplayName, DisplayVersion, Publisher, InstallDate -First " + str(limit) + " | "
            "ConvertTo-Json"
        )
        raw = self._run_ps(cmd, timeout=20)

        try:
            apps = json.loads(raw) if raw and not raw.startswith("Error") else []
            if isinstance(apps, dict):
                apps = [apps]
        except Exception:
            return "🔍 No pude obtener la lista de software instalado."

        if not apps:
            return "🔍 No se encontró software instalado (o sin acceso al registro)."

        lines = [f"🔍 **SOFTWARE INSTALADO** — {len(apps)} programas\n"]
        for app in apps:
            name = app.get("DisplayName", "?")
            version = app.get("DisplayVersion", "-")
            publisher = app.get("Publisher", "-")
            lines.append(f"  📦 **{name}** v{version}")
            if publisher and publisher != "-":
                lines.append(f"     {publisher}")

        return "\n".join(lines)

    # ── Programas de inicio ──────────────────────────
    def startup_programs(self) -> str:
        """Lista programas que se inician con Windows."""
        cmd = (
            "$startup = @(); "
            "Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue | "
            "ForEach-Object { $startup += @{Name=$_.Name; Command=$_.Command; Location=$_.Location} }; "
            "$startup | ConvertTo-Json"
        )
        raw = self._run_ps(cmd, timeout=15)

        try:
            programs = json.loads(raw) if raw and not raw.startswith("Error") else []
            if isinstance(programs, dict):
                programs = [programs]
        except Exception:
            programs = []

        # También revisar carpeta de startup
        startup_folder = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        folder_items = []
        try:
            if os.path.isdir(startup_folder):
                folder_items = os.listdir(startup_folder)
        except Exception:
            pass

        if not programs and not folder_items:
            return "🔍 No se encontraron programas de inicio."

        lines = ["🚀 **PROGRAMAS DE INICIO**\n"]

        if programs:
            lines.append("  **Registro/WMI:**")
            for p in programs[:20]:
                name = p.get("Name", "?")
                cmd_str = p.get("Command", "?")[:60]
                loc = p.get("Location", "?")
                lines.append(f"    • **{name}** — `{cmd_str}`")

        if folder_items:
            lines.append("\n  **Carpeta Startup:**")
            for item in folder_items:
                lines.append(f"    • {item}")

        return "\n".join(lines)

    # ── Variables de entorno ─────────────────────────
    def environment_vars(self, filter_query: str = "") -> str:
        """Lista variables de entorno (filtradas opcionalmente)."""
        env_vars = dict(os.environ)

        if filter_query:
            filter_q = filter_query.lower()
            env_vars = {k: v for k, v in env_vars.items() if filter_q in k.lower()}

        if not env_vars:
            return f"🔍 No se encontraron variables con '{filter_query}'."

        lines = [f"🔍 **VARIABLES DE ENTORNO** — {len(env_vars)}\n"]

        # Separar las importantes
        important_keys = {"PATH", "USERPROFILE", "APPDATA", "TEMP", "PYTHON",
                         "JAVA_HOME", "NODE_PATH", "GOPATH", "GOOGLE_API_KEY"}

        for key in sorted(env_vars.keys()):
            value = env_vars[key]
            # Truncar valores largos
            display = value[:80] + ("..." if len(value) > 80 else "")
            marker = "⭐" if key.upper() in important_keys else "  "
            lines.append(f"  {marker} **{key}** = `{display}`")

        return "\n".join(lines)

    # ── Uso de disco por carpeta ─────────────────────
    def disk_usage(self, path: str = "", top: int = 10) -> str:
        """Analiza uso de disco por carpetas de primer nivel."""
        if not path:
            path = os.path.expanduser("~")

        path = os.path.expandvars(os.path.expanduser(path))

        if not os.path.isdir(path):
            return f"🔍 El directorio '{path}' no existe."

        sizes: list[tuple[str, int]] = []

        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                try:
                    if os.path.isfile(item_path):
                        sizes.append((item, os.path.getsize(item_path)))
                    elif os.path.isdir(item_path):
                        # Solo contar archivos de primer nivel dentro del subdirectorio
                        total = 0
                        try:
                            for f in os.listdir(item_path):
                                fp = os.path.join(item_path, f)
                                if os.path.isfile(fp):
                                    try:
                                        total += os.path.getsize(fp)
                                    except OSError:
                                        pass
                        except (PermissionError, OSError):
                            pass
                        sizes.append((item + "/", total))
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError) as e:
            return f"🔍 Error accediendo a '{path}': {e}"

        sizes.sort(key=lambda x: x[1], reverse=True)
        top_items = sizes[:top]

        if not top_items:
            return f"🔍 No se encontraron archivos en '{path}'."

        total_size = sum(s for _, s in sizes)
        max_size = top_items[0][1] if top_items else 1

        lines = [f"💾 **USO DE DISCO: {path}**",
                 f"  Total estimado: {self._format_size(total_size)}\n"]

        for name, size in top_items:
            bar_len = int(size / max_size * 15) if max_size > 0 else 0
            bar = "█" * bar_len + "░" * (15 - bar_len)
            pct = (size / total_size * 100) if total_size > 0 else 0
            lines.append(f"  {bar} {self._format_size(size):>10s} ({pct:4.1f}%) {name}")

        return "\n".join(lines)

    # ── Conexiones de red ────────────────────────────
    def network_connections(self, limit: int = 20) -> str:
        """Lista conexiones de red activas."""
        cmd = (
            "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
            "Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, "
            "OwningProcess, @{N='Process';E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName}} "
            f"-First {limit} | ConvertTo-Json"
        )
        raw = self._run_ps(cmd, timeout=15)

        try:
            conns = json.loads(raw) if raw and not raw.startswith("Error") else []
            if isinstance(conns, dict):
                conns = [conns]
        except Exception:
            return "🔍 No pude obtener las conexiones de red."

        if not conns:
            return "🔍 No hay conexiones establecidas (o sin acceso)."

        lines = [f"🌐 **CONEXIONES DE RED** — {len(conns)} activas\n"]
        for c in conns:
            process = c.get("Process", "?")
            local = f"{c.get('LocalAddress', '?')}:{c.get('LocalPort', '?')}"
            remote = f"{c.get('RemoteAddress', '?')}:{c.get('RemotePort', '?')}"
            lines.append(f"  🔗 **{process}** {local} → {remote}")

        return "\n".join(lines)

    # ── Servicios ────────────────────────────────────
    def services(self, filter_running: bool = True) -> str:
        """Lista servicios del sistema."""
        state = "Running" if filter_running else "*"
        cmd = (
            f"Get-Service | Where-Object {{$_.Status -eq '{state}'}} | "
            "Sort-Object DisplayName | "
            "Select-Object DisplayName, Status, StartType -First 30 | "
            "ConvertTo-Json"
        )
        raw = self._run_ps(cmd, timeout=15)

        try:
            svcs = json.loads(raw) if raw and not raw.startswith("Error") else []
            if isinstance(svcs, dict):
                svcs = [svcs]
        except Exception:
            return "🔍 No pude obtener la lista de servicios."

        if not svcs:
            return "🔍 No se encontraron servicios."

        state_label = "en ejecución" if filter_running else "todos"
        lines = [f"⚙️ **SERVICIOS ({state_label})** — {len(svcs)}\n"]
        for s in svcs:
            name = s.get("DisplayName", "?")
            status = s.get("Status", 0)
            start_type = s.get("StartType", 0)
            status_map = {4: "Running", 1: "Stopped"}
            start_map = {2: "Auto", 3: "Manual", 4: "Disabled"}
            status_str = status_map.get(status, str(status))
            start_str = start_map.get(start_type, str(start_type))
            icon = "🟢" if status in (4, "Running") else "🔴"
            lines.append(f"  {icon} **{name}** — {start_str}")

        return "\n".join(lines)

    # ── Reporte completo ─────────────────────────────
    def full_report(self) -> str:
        """Genera reporte completo del sistema."""
        lines = ["🔍 **REPORTE COMPLETO DEL SISTEMA**\n"]

        # Software (top 10)
        lines.append(self.installed_software(limit=10))
        lines.append("")

        # Startup
        lines.append(self.startup_programs())
        lines.append("")

        # Disco usuario
        lines.append(self.disk_usage(top=5))

        return "\n".join(lines)

    # ── Helpers ──────────────────────────────────────
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formatea bytes a unidad legible."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def status(self) -> dict:
        """Estado del profiler."""
        return {
            "available_reports": [
                "installed_software", "startup_programs", "environment_vars",
                "disk_usage", "network_connections", "services", "full_report"
            ]
        }


# Singleton
system_profiler = SystemProfiler()
