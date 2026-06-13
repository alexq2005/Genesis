"""
GENESIS Tool Creator — Genesis puede crear herramientas nuevas para si mismo.

Problema:
Las herramientas de Genesis son fijas (buscar, python, leer, escribir, shell).
Si el usuario necesita algo que no esta, Genesis no puede hacer nada.

Solucion:
ToolCreator permite que Genesis:
1. Defina nuevas herramientas como funciones Python
2. Las valide (syntax, seguridad, imports)
3. Las registre dinámicamente en el sistema de tools
4. Las persista para que sobrevivan reinicios
5. Las pueda listar, editar y eliminar

Cada herramienta creada es un archivo .py en tools_custom/ con estructura:
    TOOL_NAME = "mi_tool"
    TOOL_DESCRIPTION = "Descripcion para el LLM"
    TOOL_USAGE = "[TOOL:mi_tool] argumento"

    def execute(arg: str) -> str:
        '''Funcion principal — recibe un argumento string, retorna resultado string.'''
        return "resultado"
"""
import ast
import importlib
import importlib.util
import time
from pathlib import Path
from typing import Optional

try:
    from core.safe_io import safe_read_json, safe_write_json
except ImportError:
    import json
    def safe_read_json(path, default=None):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    def safe_write_json(path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True


class CustomTool:
    """Representa una herramienta custom creada por Genesis."""

    def __init__(self, name: str, description: str, usage: str,
                 module, filepath: Path):
        self.name = name
        self.description = description
        self.usage = usage
        self.module = module
        self.filepath = filepath
        self.enabled = True
        self.calls = 0
        self.errors = 0
        self.created_at = time.time()

    def execute(self, arg: str) -> str:
        """Ejecuta la herramienta."""
        self.calls += 1
        try:
            result = self.module.execute(arg)
            return str(result) if result is not None else "(sin resultado)"
        except Exception as e:
            self.errors += 1
            return f"[ERROR en {self.name}] {type(e).__name__}: {e}"


class ToolCreator:
    """
    Sistema para crear, validar y registrar herramientas custom.

    Las herramientas se guardan como archivos .py en tools_custom/.
    Se cargan automaticamente al iniciar Genesis.
    """

    # Imports prohibidos en herramientas custom (seguridad)
    BLOCKED_IMPORTS = {
        "ctypes", "winreg", "_winreg", "msvcrt", "nt",
        "socket",  # Sin acceso a red directa
    }

    # Patrones prohibidos
    BLOCKED_PATTERNS = [
        "os.system", "subprocess.Popen", "subprocess.call",
        "shutil.rmtree", "__import__", "exec(", "eval(",
        "open('/etc", "open('C:\\\\Windows",
    ]

    def __init__(self, tools_dir: Optional[Path] = None,
                 registry_file: Optional[Path] = None):
        if tools_dir is None:
            tools_dir = Path(__file__).parent.parent / "tools_custom"
        self.tools_dir = tools_dir
        self.tools_dir.mkdir(exist_ok=True)

        if registry_file is None:
            mem_dir = Path(__file__).parent.parent / "memory_data"
            mem_dir.mkdir(exist_ok=True)
            registry_file = mem_dir / "custom_tools.json"
        self.registry_file = registry_file

        # Tools cargadas: {nombre: CustomTool}
        self.tools: dict[str, CustomTool] = {}

        # Cargar tools existentes
        self._load_all()

    def _load_all(self):
        """Carga todas las tools custom del directorio."""
        if not self.tools_dir.exists():
            return

        for filepath in sorted(self.tools_dir.glob("*.py")):
            if filepath.name.startswith("_"):
                continue
            self._load_tool(filepath)

    def _load_tool(self, filepath: Path) -> bool:
        """Carga una tool desde un archivo .py.

        SEGURIDAD: valida el código con _check_security ANTES de ejecutarlo
        (exec_module corre el código a nivel de módulo). Un .py planteado en
        tools_custom/ por cualquier vía no se ejecuta si tiene imports/patrones
        prohibidos. Esto cierra el bypass de auto-carga sin validación.
        """
        try:
            # Validación previa al exec (no ejecutar código no confiable)
            try:
                code = filepath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return False
            warnings = self._check_security(code)
            if any(w.startswith("[BLOCKED]") for w in warnings):
                blocked = "; ".join(w for w in warnings if w.startswith("[BLOCKED]"))
                try:
                    print(f"  [ToolCreator] Tool NO cargada (seguridad) {filepath.name}: {blocked}")
                except Exception:
                    pass
                return False
            # Además: debe parsear como Python válido
            try:
                ast.parse(code)
            except SyntaxError:
                return False

            spec = importlib.util.spec_from_file_location(
                f"genesis_tool_{filepath.stem}", str(filepath)
            )
            if not spec or not spec.loader:
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Validar estructura requerida
            if not hasattr(module, "execute"):
                return False

            name = getattr(module, "TOOL_NAME", filepath.stem)
            description = getattr(module, "TOOL_DESCRIPTION", "Herramienta custom")
            usage = getattr(module, "TOOL_USAGE", f"[TOOL:{name}] argumento")

            tool = CustomTool(
                name=name,
                description=description,
                usage=usage,
                module=module,
                filepath=filepath,
            )
            self.tools[name] = tool
            return True

        except Exception:
            return False

    def create_tool(self, name: str, description: str,
                    code: str, usage: str = "") -> dict:
        """
        Crea una nueva herramienta custom.

        Args:
            name: Nombre de la herramienta (sin espacios, minusculas)
            description: Descripcion para el LLM
            code: Codigo Python de la funcion execute(arg) -> str
            usage: Ejemplo de uso para el LLM

        Returns:
            Dict con status y mensaje
        """
        # Normalizar nombre
        name = name.strip().lower().replace(" ", "_").replace("-", "_")

        # Validar nombre
        if not name.isidentifier():
            return {"status": "error", "message": f"Nombre invalido: '{name}'"}

        if name in ("python", "buscar", "leer", "escribir", "investigar",
                     "analizar", "web", "shell", "sysinfo", "self_read",
                     "self_edit", "project_scan"):
            return {"status": "error", "message": f"Nombre reservado: '{name}'"}

        # Construir codigo completo del archivo
        if not usage:
            usage = f"[TOOL:{name}] argumento"

        full_code = f'''"""
Herramienta custom: {name}
{description}
Creada automaticamente por Genesis.
"""

TOOL_NAME = "{name}"
TOOL_DESCRIPTION = """{description}"""
TOOL_USAGE = """{usage}"""

{code}
'''

        # Validar syntax
        try:
            ast.parse(full_code)
        except SyntaxError as e:
            return {
                "status": "error",
                "message": f"Error de sintaxis en linea {e.lineno}: {e.msg}",
            }

        # Validar seguridad
        warnings = self._check_security(full_code)
        if any(w.startswith("[BLOCKED]") for w in warnings):
            blocked = [w for w in warnings if w.startswith("[BLOCKED]")]
            return {
                "status": "error",
                "message": f"Codigo bloqueado por seguridad: {'; '.join(blocked)}",
            }

        # Validar que tiene funcion execute
        tree = ast.parse(full_code)
        has_execute = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "execute":
                has_execute = True
                break

        if not has_execute:
            return {
                "status": "error",
                "message": "El codigo debe contener una funcion 'execute(arg: str) -> str'",
            }

        # Escribir archivo
        filepath = self.tools_dir / f"{name}.py"
        try:
            filepath.write_text(full_code, encoding="utf-8")
        except Exception as e:
            return {"status": "error", "message": f"No se pudo escribir: {e}"}

        # Cargar la tool
        if self._load_tool(filepath):
            # Registrar en historial
            self._save_registry()
            return {
                "status": "created",
                "message": (
                    f"Herramienta '{name}' creada exitosamente!\n"
                    f"  Uso: {usage}\n"
                    f"  Archivo: {filepath.name}\n"
                    f"  {'Warnings: ' + '; '.join(warnings) if warnings else ''}"
                ),
            }
        else:
            filepath.unlink(missing_ok=True)
            return {
                "status": "error",
                "message": "La herramienta se creo pero no se pudo cargar. Revisa el codigo.",
            }

    def _check_security(self, code: str) -> list[str]:
        """Verifica seguridad del codigo."""
        warnings = []

        # Imports bloqueados
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        if mod in self.BLOCKED_IMPORTS:
                            warnings.append(f"[BLOCKED] Import prohibido: {mod}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split(".")[0]
                        if mod in self.BLOCKED_IMPORTS:
                            warnings.append(f"[BLOCKED] Import prohibido: {mod}")
        except SyntaxError:
            pass

        # Patrones peligrosos
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in code:
                warnings.append(f"[BLOCKED] Patron peligroso: {pattern}")

        return warnings

    def execute_tool(self, name: str, arg: str) -> Optional[str]:
        """
        Ejecuta una herramienta custom por nombre.

        Returns:
            Resultado string, o None si la tool no existe
        """
        if name not in self.tools:
            return None

        tool = self.tools[name]
        if not tool.enabled:
            return f"[Herramienta '{name}' desactivada]"

        return tool.execute(arg)

    def delete_tool(self, name: str) -> str:
        """Elimina una herramienta custom."""
        if name not in self.tools:
            return f"Herramienta '{name}' no encontrada."

        tool = self.tools[name]
        try:
            tool.filepath.unlink(missing_ok=True)
        except Exception:
            pass

        del self.tools[name]
        self._save_registry()
        return f"Herramienta '{name}' eliminada."

    def toggle_tool(self, name: str) -> str:
        """Activa/desactiva una herramienta."""
        if name not in self.tools:
            return f"Herramienta '{name}' no encontrada."
        tool = self.tools[name]
        tool.enabled = not tool.enabled
        state = "activada" if tool.enabled else "desactivada"
        return f"Herramienta '{name}': {state}"

    def get_tools_description(self) -> str:
        """
        Genera la descripcion de todas las tools custom para inyectar
        en el system prompt (para que el LLM las conozca).
        """
        if not self.tools:
            return ""

        lines = ["\n[HERRAMIENTAS CUSTOM (creadas por ti)]"]
        for name, tool in self.tools.items():
            if tool.enabled:
                lines.append(f"  {tool.usage}")
                lines.append(f"    {tool.description}")
        return "\n".join(lines)

    def list_tools(self) -> str:
        """Lista todas las tools custom."""
        if not self.tools:
            return "  No hay herramientas custom.\n  Genesis puede crear nuevas con /tool_create."

        lines = []
        for name, tool in self.tools.items():
            icon = "●" if tool.enabled else "○"
            lines.append(f"  {icon} {name} — {tool.description[:60]}")
            lines.append(f"    Uso: {tool.usage}")
            lines.append(f"    Llamadas: {tool.calls} ({tool.errors} errores)")
        return "\n".join(lines)

    def _save_registry(self):
        """Guarda el registro de tools."""
        data = {
            "tools": {
                name: {
                    "name": tool.name,
                    "description": tool.description,
                    "calls": tool.calls,
                    "errors": tool.errors,
                    "enabled": tool.enabled,
                    "created_at": tool.created_at,
                }
                for name, tool in self.tools.items()
            }
        }
        safe_write_json(self.registry_file, data)

    def status(self) -> str:
        """Resumen para /status."""
        total = len(self.tools)
        active = sum(1 for t in self.tools.values() if t.enabled)
        total_calls = sum(t.calls for t in self.tools.values())
        return f"  Tools custom: {active}/{total} activas, {total_calls} llamadas totales"
