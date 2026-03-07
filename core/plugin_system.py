"""
GENESIS Plugin System — Extensiones dinamicas sin modificar el core.

Problema:
Cada nueva feature requiere modificar genesis.py, lo cual es fragil
y hace el archivo mas largo. Las features deberian ser modulares.

Solucion:
Un sistema de plugins que permite:
1. Cargar extensiones automaticamente desde una carpeta
2. Cada plugin registra comandos, tools, o hooks
3. Los plugins pueden interactuar con los subsistemas de Genesis
4. Se pueden activar/desactivar sin reiniciar

Estructura de un plugin:
    plugins/
        mi_plugin.py          # Un archivo = un plugin

    # mi_plugin.py
    PLUGIN_NAME = "Mi Plugin"
    PLUGIN_VERSION = "1.0"
    PLUGIN_DESCRIPTION = "Descripcion corta"

    def on_load(genesis):
        '''Se llama cuando el plugin se carga.'''
        pass

    def on_unload(genesis):
        '''Se llama cuando el plugin se descarga.'''
        pass

    def register_commands():
        '''Retorna dict de comandos que el plugin agrega.'''
        return {
            "/mi_comando": {
                "handler": mi_funcion,
                "help": "Descripcion del comando"
            }
        }

    def on_message(genesis, user_input, response):
        '''Hook que se llama en cada interaccion (opcional).'''
        pass
"""
import os
import sys
import importlib
import importlib.util
from pathlib import Path
from typing import Optional, Callable


class PluginInfo:
    """Metadatos de un plugin cargado."""

    def __init__(self, name: str, version: str, description: str,
                 module, filepath: Path):
        self.name = name
        self.version = version
        self.description = description
        self.module = module
        self.filepath = filepath
        self.enabled = True
        self.commands: dict[str, dict] = {}
        self.has_on_message = False
        self.has_on_tool_result = False
        self.load_error: str = ""

    def __repr__(self):
        state = "activo" if self.enabled else "inactivo"
        return f"Plugin({self.name} v{self.version}, {state})"


class PluginSystem:
    """
    Sistema de plugins de Genesis.

    Carga automaticamente plugins desde la carpeta plugins/.
    Los plugins pueden registrar comandos, hooks y herramientas.
    """

    def __init__(self, plugins_dir: Optional[Path] = None):
        """
        Args:
            plugins_dir: Directorio donde buscar plugins.
                         Default: GENESIS/plugins/
        """
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent.parent / "plugins"
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(exist_ok=True)

        # Plugins cargados: {nombre: PluginInfo}
        self.plugins: dict[str, PluginInfo] = {}

        # Comandos registrados por plugins: {"/cmd": PluginInfo}
        self.commands: dict[str, dict] = {}

        # Referencia a Genesis (se setea en load_all)
        self._genesis = None

    def load_all(self, genesis=None):
        """
        Descubre y carga todos los plugins del directorio.

        Args:
            genesis: Instancia de Genesis para inyectar en plugins
        """
        self._genesis = genesis

        if not self.plugins_dir.exists():
            return

        # Buscar archivos .py en el directorio de plugins
        for filepath in sorted(self.plugins_dir.glob("*.py")):
            if filepath.name.startswith("_"):
                continue  # Ignorar __init__.py, __pycache__, etc
            self._load_plugin(filepath)

    def _load_plugin(self, filepath: Path) -> bool:
        """
        Carga un plugin desde un archivo .py.

        Args:
            filepath: Path al archivo del plugin

        Returns:
            True si se cargo exitosamente
        """
        plugin_id = filepath.stem  # nombre sin .py

        try:
            # Cargar modulo dinamicamente
            spec = importlib.util.spec_from_file_location(
                f"genesis_plugin_{plugin_id}", str(filepath)
            )
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Extraer metadatos
            name = getattr(module, "PLUGIN_NAME", plugin_id)
            version = getattr(module, "PLUGIN_VERSION", "0.1")
            description = getattr(module, "PLUGIN_DESCRIPTION", "Sin descripcion")

            # Crear info del plugin
            info = PluginInfo(
                name=name,
                version=version,
                description=description,
                module=module,
                filepath=filepath,
            )

            # Registrar comandos
            if hasattr(module, "register_commands"):
                commands = module.register_commands()
                if isinstance(commands, dict):
                    for cmd_name, cmd_config in commands.items():
                        # Asegurar que el comando empieza con /
                        if not cmd_name.startswith("/"):
                            cmd_name = f"/{cmd_name}"
                        info.commands[cmd_name] = cmd_config
                        self.commands[cmd_name] = {
                            "plugin": info,
                            "handler": cmd_config.get("handler"),
                            "help": cmd_config.get("help", ""),
                        }

            # Detectar hooks
            info.has_on_message = hasattr(module, "on_message")
            info.has_on_tool_result = hasattr(module, "on_tool_result")

            # Llamar on_load si existe
            if hasattr(module, "on_load") and self._genesis:
                try:
                    module.on_load(self._genesis)
                except Exception as e:
                    info.load_error = f"on_load fallo: {e}"

            # Registrar
            self.plugins[plugin_id] = info
            return True

        except Exception as e:
            # Plugin con error — registrar pero desactivar
            info = PluginInfo(
                name=plugin_id,
                version="?",
                description="Error al cargar",
                module=None,
                filepath=filepath,
            )
            info.enabled = False
            info.load_error = str(e)
            self.plugins[plugin_id] = info
            return False

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Descarga un plugin.

        Args:
            plugin_id: ID del plugin (nombre del archivo sin .py)
        """
        if plugin_id not in self.plugins:
            return False

        info = self.plugins[plugin_id]

        # Llamar on_unload si existe
        if info.module and hasattr(info.module, "on_unload"):
            try:
                info.module.on_unload(self._genesis)
            except Exception:
                pass

        # Remover comandos
        for cmd_name in list(info.commands.keys()):
            self.commands.pop(cmd_name, None)

        # Remover plugin
        del self.plugins[plugin_id]
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """Recarga un plugin (descarga + carga)."""
        if plugin_id in self.plugins:
            filepath = self.plugins[plugin_id].filepath
            self.unload_plugin(plugin_id)
            return self._load_plugin(filepath)
        return False

    def handle_command(self, command: str) -> Optional[str]:
        """
        Intenta ejecutar un comando registrado por un plugin.

        Args:
            command: Comando completo (ej: "/mi_comando arg1 arg2")

        Returns:
            Resultado del comando, o None si no es un comando de plugin
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd not in self.commands:
            return None

        cmd_info = self.commands[cmd]
        plugin_info = cmd_info["plugin"]

        if not plugin_info.enabled:
            return f"[Plugin '{plugin_info.name}' esta desactivado]"

        handler = cmd_info.get("handler")
        if not handler:
            return f"[Plugin '{plugin_info.name}': comando sin handler]"

        try:
            # Intentar pasar genesis + args; si falla, solo args
            import inspect
            sig = inspect.signature(handler)
            params = list(sig.parameters)

            if len(params) >= 2 and self._genesis:
                return handler(self._genesis, args)
            elif len(params) >= 1:
                # Handler que solo acepta args (o genesis)
                try:
                    return handler(self._genesis, args)
                except TypeError:
                    return handler(args)
            else:
                return handler()
        except Exception as e:
            return f"[Plugin '{plugin_info.name}' error: {e}]"

    def run_on_message_hooks(self, user_input: str, response: str):
        """Ejecuta los hooks on_message de todos los plugins activos."""
        for plugin_id, info in self.plugins.items():
            if info.enabled and info.has_on_message and info.module:
                try:
                    info.module.on_message(self._genesis, user_input, response)
                except Exception:
                    pass  # No romper el flujo por un plugin

    def run_on_tool_result_hooks(self, tool_name: str, result: str):
        """Ejecuta los hooks on_tool_result de todos los plugins activos."""
        for plugin_id, info in self.plugins.items():
            if info.enabled and info.has_on_tool_result and info.module:
                try:
                    info.module.on_tool_result(self._genesis, tool_name, result)
                except Exception:
                    pass

    def toggle_plugin(self, plugin_id: str) -> str:
        """Activa/desactiva un plugin."""
        if plugin_id not in self.plugins:
            return f"Plugin '{plugin_id}' no encontrado."
        info = self.plugins[plugin_id]
        info.enabled = not info.enabled
        state = "activado" if info.enabled else "desactivado"
        return f"Plugin '{info.name}': {state}"

    def list_plugins(self) -> str:
        """Lista todos los plugins con su estado."""
        if not self.plugins:
            return "  No hay plugins instalados.\n  Crea archivos .py en: plugins/"
        lines = []
        for pid, info in self.plugins.items():
            icon = "●" if info.enabled else "○"
            cmds = ", ".join(info.commands.keys()) if info.commands else "sin comandos"
            lines.append(f"  {icon} {info.name} v{info.version} ({pid})")
            lines.append(f"    {info.description}")
            lines.append(f"    Comandos: {cmds}")
            if info.load_error:
                lines.append(f"    [ERROR: {info.load_error}]")
        return "\n".join(lines)

    def status(self) -> str:
        """Resumen para /status."""
        total = len(self.plugins)
        active = sum(1 for p in self.plugins.values() if p.enabled)
        cmds = len(self.commands)
        return f"  Plugins: {active}/{total} activos, {cmds} comandos registrados"

    def get_commands_help(self) -> str:
        """Genera texto de ayuda con los comandos de plugins."""
        if not self.commands:
            return ""
        lines = ["  PLUGINS:"]
        for cmd, info in sorted(self.commands.items()):
            help_text = info.get("help", "")
            lines.append(f"  {cmd:15s} — {help_text}")
        return "\n".join(lines)
