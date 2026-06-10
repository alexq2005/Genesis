"""
GENESIS File Watcher — Monitoreo de directorios con acciones automáticas.
Vigila carpetas, detecta archivos nuevos/modificados, ejecuta reglas configuradas.
Acciones: mover, copiar, notificar, ejecutar comando.
"""
import os
import time
import shutil
import fnmatch
import threading
import json
from datetime import datetime
from typing import Optional


class FileWatcher:
    """Monitor de directorios con reglas automáticas."""

    def __init__(self, data_dir: str = "memory_data"):
        self._rules: list[dict] = []
        self._events: list[dict] = []
        self._watching: bool = False
        self._watch_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._next_id: int = 1
        self._known_files: dict[str, dict[str, float]] = {}  # dir -> {filename: mtime}
        self._max_events: int = 200
        self._scan_interval: float = 3.0  # segundos entre scans
        self._data_file = os.path.join(data_dir, "file_watcher.json")
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    # ── Persistencia ─────────────────────────────────
    def _load(self):
        """Carga reglas y eventos desde disco."""
        try:
            if os.path.exists(self._data_file):
                with open(self._data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._rules = data.get("rules", [])
                self._events = data.get("events", [])[-self._max_events:]
                self._next_id = data.get("next_id", 1)
        except Exception:
            pass

    def save(self):
        """Guarda reglas y eventos a disco."""
        with self._lock:
            try:
                data = {
                    "rules": self._rules,
                    "events": self._events[-self._max_events:],
                    "next_id": self._next_id
                }
                with open(self._data_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    # ── Gestión de reglas ────────────────────────────
    def add_rule(self, directory: str, pattern: str, action: str,
                 action_args: str = "", name: str = "") -> str:
        """Agrega una regla de vigilancia.
        action: 'move', 'copy', 'notify', 'execute'
        pattern: glob (*.pdf, *.jpg, screenshot*)
        """
        if not directory or not pattern or not action:
            return "👁️ Necesita: directorio, patrón y acción."

        # Normalizar directorio
        directory = os.path.expanduser(directory)
        directory = os.path.expandvars(directory)

        if not os.path.isdir(directory):
            return f"👁️ El directorio '{directory}' no existe."

        valid_actions = {"move", "copy", "notify", "execute"}
        if action.lower() not in valid_actions:
            return f"👁️ Acción inválida. Opciones: {', '.join(valid_actions)}"

        if action.lower() in ("move", "copy") and not action_args:
            return f"👁️ La acción '{action}' necesita un destino (action_args)."

        with self._lock:
            rule_name = name or f"regla_{self._next_id}"
            rule = {
                "id": self._next_id,
                "name": rule_name,
                "directory": directory,
                "pattern": pattern,
                "action": action.lower(),
                "action_args": action_args,
                "enabled": True,
                "created": datetime.now().isoformat()
            }
            self._rules.append(rule)
            self._next_id += 1
            self.save()

        return (f"👁️ **Regla #{rule['id']} creada:**\n"
                f"  📁 Vigilar: `{directory}`\n"
                f"  🔍 Patrón: `{pattern}`\n"
                f"  ⚡ Acción: {action} {action_args}")

    def remove_rule(self, rule_id: int) -> str:
        """Elimina una regla por ID."""
        with self._lock:
            for i, rule in enumerate(self._rules):
                if rule["id"] == rule_id:
                    removed = self._rules.pop(i)
                    self.save()
                    return f"👁️ Regla #{rule_id} '{removed['name']}' eliminada."
            return f"👁️ No encontré la regla #{rule_id}."

    def list_rules(self) -> str:
        """Lista todas las reglas configuradas."""
        with self._lock:
            if not self._rules:
                return "👁️ No hay reglas configuradas. Usá 'vigila [carpeta] para [acción] cuando [patrón]'."

            lines = [f"👁️ **REGLAS DE VIGILANCIA** — {len(self._rules)} regla(s)\n"]
            for r in self._rules:
                status = "✅" if r["enabled"] else "⏸️"
                lines.append(f"  {status} #{r['id']} **{r['name']}**")
                lines.append(f"     📁 {r['directory']}")
                lines.append(f"     🔍 {r['pattern']} → {r['action']} {r.get('action_args', '')}")
            return "\n".join(lines)

    def enable_rule(self, rule_id: int) -> str:
        """Habilita una regla."""
        with self._lock:
            for r in self._rules:
                if r["id"] == rule_id:
                    r["enabled"] = True
                    self.save()
                    return f"👁️ Regla #{rule_id} habilitada."
            return f"👁️ No encontré la regla #{rule_id}."

    def disable_rule(self, rule_id: int) -> str:
        """Deshabilita una regla."""
        with self._lock:
            for r in self._rules:
                if r["id"] == rule_id:
                    r["enabled"] = False
                    self.save()
                    return f"👁️ Regla #{rule_id} deshabilitada."
            return f"👁️ No encontré la regla #{rule_id}."

    # ── Monitoreo ────────────────────────────────────
    def start(self) -> str:
        """Inicia el monitoreo en background."""
        if self._watching:
            return "👁️ El monitoreo ya está activo."

        with self._lock:
            if not self._rules:
                return "👁️ No hay reglas configuradas. Primero agregá una regla."

            # Snapshot inicial: registrar archivos existentes sin disparar acciones
            self._snapshot_all()
            self._watching = True

        self._watch_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="FileWatcher"
        )
        self._watch_thread.start()

        active = sum(1 for r in self._rules if r["enabled"])
        return f"👁️ **Monitoreo iniciado** — {active} regla(s) activa(s), escaneando cada {self._scan_interval}s."

    def stop(self) -> str:
        """Detiene el monitoreo."""
        if not self._watching:
            return "👁️ El monitoreo no está activo."

        self._watching = False
        self.save()
        return "👁️ Monitoreo detenido."

    def _snapshot_all(self):
        """Toma snapshot de archivos actuales en todos los directorios vigilados."""
        dirs = set(r["directory"] for r in self._rules if r["enabled"])
        for d in dirs:
            try:
                files = {}
                for f in os.listdir(d):
                    fp = os.path.join(d, f)
                    if os.path.isfile(fp):
                        try:
                            files[f] = os.path.getmtime(fp)
                        except OSError:
                            pass
                self._known_files[d] = files
            except (PermissionError, OSError):
                self._known_files[d] = {}

    def _monitor_loop(self):
        """Loop principal de monitoreo (background thread)."""
        while self._watching:
            try:
                self._scan_once()
            except Exception:
                pass
            time.sleep(self._scan_interval)

    def _scan_once(self):
        """Escanea todos los directorios vigilados una vez."""
        with self._lock:
            active_rules = [r for r in self._rules if r["enabled"]]

        if not active_rules:
            return

        # Agrupar reglas por directorio
        dirs_rules: dict[str, list[dict]] = {}
        for r in active_rules:
            dirs_rules.setdefault(r["directory"], []).append(r)

        for directory, rules in dirs_rules.items():
            try:
                current_files: dict[str, float] = {}
                for f in os.listdir(directory):
                    fp = os.path.join(directory, f)
                    if os.path.isfile(fp):
                        try:
                            current_files[f] = os.path.getmtime(fp)
                        except OSError:
                            pass

                known = self._known_files.get(directory, {})

                # Detectar nuevos y modificados
                for filename, mtime in current_files.items():
                    is_new = filename not in known
                    is_modified = not is_new and mtime > known.get(filename, 0)

                    if is_new or is_modified:
                        event_type = "nuevo" if is_new else "modificado"
                        filepath = os.path.join(directory, filename)

                        for rule in rules:
                            if fnmatch.fnmatch(filename.lower(), rule["pattern"].lower()):
                                self._fire_action(rule, filepath, event_type)

                # Actualizar known_files
                with self._lock:
                    self._known_files[directory] = current_files

            except (PermissionError, OSError):
                continue

    def _fire_action(self, rule: dict, filepath: str, event_type: str):
        """Ejecuta la acción configurada en la regla."""
        filename = os.path.basename(filepath)
        action = rule["action"]
        args = rule.get("action_args", "")
        result = ""

        try:
            if action == "notify":
                result = f"Notificación: {event_type} '{filename}'"

            elif action == "move":
                dest_dir = os.path.expandvars(os.path.expanduser(args))
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, filename)
                shutil.move(filepath, dest)
                result = f"Movido a {dest}"

            elif action == "copy":
                dest_dir = os.path.expandvars(os.path.expanduser(args))
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, filename)
                shutil.copy2(filepath, dest)
                result = f"Copiado a {dest}"

            elif action == "execute":
                import subprocess
                cmd = args.replace("{file}", filepath).replace("{name}", filename)
                r = subprocess.run(cmd, shell=True, capture_output=True,
                                   text=True, timeout=30, encoding="utf-8",
                                   errors="replace")
                result = f"Ejecutado: {r.returncode}"

        except Exception as e:
            result = f"Error: {e}"

        # Registrar evento
        event = {
            "timestamp": datetime.now().isoformat(),
            "file": filename,
            "directory": rule["directory"],
            "event_type": event_type,
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "action": action,
            "result": result
        }

        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    # ── Consultas ────────────────────────────────────
    def events(self, limit: int = 20) -> str:
        """Muestra eventos recientes."""
        with self._lock:
            if not self._events:
                return "👁️ No hay eventos registrados aún."

            recent = self._events[-limit:]
            lines = [f"👁️ **EVENTOS RECIENTES** — últimos {len(recent)}\n"]
            for e in reversed(recent):
                ts = e["timestamp"][:19].replace("T", " ")
                emoji = "🆕" if e["event_type"] == "nuevo" else "📝"
                lines.append(f"  {emoji} [{ts}] **{e['file']}** ({e['event_type']})")
                lines.append(f"     → {e['action']}: {e['result']}")

            return "\n".join(lines)

    def status(self) -> dict:
        """Estado del watcher."""
        with self._lock:
            return {
                "rules_count": len(self._rules),
                "active_rules": sum(1 for r in self._rules if r["enabled"]),
                "events_count": len(self._events),
                "watching": self._watching
            }


# Singleton
file_watcher = FileWatcher()
