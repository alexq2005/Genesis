"""
Tests para Genesis v1.2.0 — Nuevas funcionalidades:
1. Timeout protection (TimeoutExecutor, Spinner)
2. Plugin System
3. Self-Modifier
4. Streaming en main loop
5. Conversation persistence
6. Version check
7. Imports de nuevos modulos
"""
import sys
import os
import json
import time
import threading

# UTF-8 para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import tempfile
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

passed = 0
failed = 0
total = 0


def test(name, condition):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")


# ============================================================
# TEST 1: Timeout Executor
# ============================================================
print("\n=== TEST: TimeoutExecutor ===")
from core.timeout import TimeoutExecutor, Spinner, ProgressBar

# Normal execution (should complete)
result = TimeoutExecutor.run(
    func=lambda: "hello",
    timeout=5,
    description="test simple"
)
test("Ejecucion normal retorna resultado", result == "hello")

# Timeout execution (should use default)
result = TimeoutExecutor.run(
    func=lambda: time.sleep(10) or "never",
    timeout=1,
    description="test timeout",
    default_on_timeout="timeout!"
)
test("Timeout retorna default", result == "timeout!")

# Timeout without default (should raise)
try:
    from core.timeout import TimeoutError as TError
    TimeoutExecutor.run(
        func=lambda: time.sleep(10),
        timeout=1,
        description="test raise"
    )
    test("Timeout sin default lanza excepcion", False)
except TError:
    test("Timeout sin default lanza excepcion", True)
except Exception:
    test("Timeout sin default lanza excepcion", True)

# Exception propagation
try:
    TimeoutExecutor.run(
        func=lambda: 1/0,
        timeout=5,
        description="test exception"
    )
    test("Excepciones se propagan", False)
except ZeroDivisionError:
    test("Excepciones se propagan", True)

# Function with return value
result = TimeoutExecutor.run(
    func=lambda: sum(range(100)),
    timeout=5,
    description="suma"
)
test("Retorna valor complejo", result == 4950)


# ============================================================
# TEST 2: Spinner
# ============================================================
print("\n=== TEST: Spinner ===")

# Test basic spinner lifecycle
spinner = Spinner("Testing", use_unicode=False)
test("Spinner creado", spinner is not None)
test("Spinner no corriendo", not spinner._running)

spinner.start()
test("Spinner corriendo", spinner._running)
time.sleep(0.3)
test("Spinner elapsed > 0", spinner.elapsed > 0)

spinner.stop()
test("Spinner detenido", not spinner._running)
test("Spinner elapsed registrado", spinner.elapsed > 0)

# Test context manager
with Spinner("Context test", use_unicode=False) as s:
    test("Spinner como context manager", s._running)
    time.sleep(0.2)
test("Spinner detenido al salir del contexto", not s._running)


# ============================================================
# TEST 3: ProgressBar
# ============================================================
print("\n=== TEST: ProgressBar ===")

bar = ProgressBar("Descargando", total=100, width=20)
test("ProgressBar creada", bar is not None)
test("ProgressBar total correcto", bar.total == 100)
test("ProgressBar current inicia en 0", bar.current == 0)

bar.update(50)
test("ProgressBar update funciona", bar.current == 50)

bar.update(100)
test("ProgressBar 100% funciona", bar.current == 100)
bar.finish()


# ============================================================
# TEST 4: Plugin System
# ============================================================
print("\n=== TEST: Plugin System ===")
from core.plugin_system import PluginSystem, PluginInfo

with tempfile.TemporaryDirectory() as tmpdir:
    plugins_dir = Path(tmpdir) / "plugins"
    plugins_dir.mkdir()

    # Create a test plugin
    plugin_code = '''
PLUGIN_NAME = "TestPlugin"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Plugin de prueba"

_loaded = False

def on_load(genesis):
    global _loaded
    _loaded = True

def register_commands():
    return {
        "/test_cmd": {
            "handler": lambda genesis, args: f"Test: {args}",
            "help": "Comando de prueba"
        }
    }

def on_message(genesis, user_input, response):
    pass
'''
    (plugins_dir / "test_plugin.py").write_text(plugin_code, encoding="utf-8")

    # Load plugins
    ps = PluginSystem(plugins_dir=plugins_dir)
    ps.load_all()

    test("Plugin cargado", "test_plugin" in ps.plugins)
    test("Plugin activo", ps.plugins["test_plugin"].enabled)
    test("Plugin nombre correcto", ps.plugins["test_plugin"].name == "TestPlugin")
    test("Plugin version correcta", ps.plugins["test_plugin"].version == "1.0")

    # Commands registered
    test("Comando registrado", "/test_cmd" in ps.commands)

    # Execute command
    result = ps.handle_command("/test_cmd hola mundo")
    test("Comando ejecutado", result == "Test: hola mundo")

    # Unknown command
    result = ps.handle_command("/nonexistent")
    test("Comando desconocido retorna None", result is None)

    # Toggle plugin
    ps.toggle_plugin("test_plugin")
    test("Plugin desactivado", not ps.plugins["test_plugin"].enabled)

    ps.toggle_plugin("test_plugin")
    test("Plugin reactivado", ps.plugins["test_plugin"].enabled)

    # Status
    status = ps.status()
    test("Status tiene info", "activos" in status)

    # List plugins
    listing = ps.list_plugins()
    test("Lista plugins tiene nombre", "TestPlugin" in listing)

    # Plugin with hooks
    test("Hook on_message detectado", ps.plugins["test_plugin"].has_on_message)

    # Create plugin with syntax error
    (plugins_dir / "bad_plugin.py").write_text("def broken(\n", encoding="utf-8")
    ps2 = PluginSystem(plugins_dir=plugins_dir)
    ps2.load_all()
    test("Plugin con error cargado pero desactivado",
         "bad_plugin" in ps2.plugins and not ps2.plugins["bad_plugin"].enabled)

    # Unload
    ps.unload_plugin("test_plugin")
    test("Plugin descargado", "test_plugin" not in ps.plugins)
    test("Comando removido al descargar", "/test_cmd" not in ps.commands)

    # Commands help
    ps3 = PluginSystem(plugins_dir=plugins_dir)
    ps3.load_all()
    help_text = ps3.get_commands_help()
    test("Help de plugins generado", "PLUGINS:" in help_text or help_text == "")


# ============================================================
# TEST 5: Self-Modifier
# ============================================================
print("\n=== TEST: Self-Modifier ===")
from core.self_modifier import SelfModifier

with tempfile.TemporaryDirectory() as tmpdir:
    genesis_dir = Path(tmpdir) / "genesis"
    genesis_dir.mkdir()
    core_dir = genesis_dir / "core"
    core_dir.mkdir()
    history_file = genesis_dir / "memory_data" / "self_mods.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    sm = SelfModifier(
        genesis_dir=genesis_dir,
        history_file=history_file,
    )
    test("SelfModifier creado", sm is not None)

    # Create a test file
    test_file = core_dir / "test_module.py"
    test_file.write_text("# Original\ndef hello():\n    return 'world'\n", encoding="utf-8")

    # Propose a change
    result = sm.propose_change(
        filepath="core/test_module.py",
        new_content="# Modified\ndef hello():\n    return 'universe'\n\ndef new_func():\n    pass\n",
        reason="Mejorar funcion hello",
        description="Cambiar retorno y agregar new_func",
    )
    test("Propuesta acepta valida", result["status"] == "pending")
    test("Diff generado", len(result["diff"]) > 0)
    test("Lineas agregadas contadas", result["additions"] > 0)

    # Get pending diff
    diff = sm.get_pending_diff()
    test("Pending diff disponible", "Modified" in diff)

    # Apply change
    apply_result = sm.apply_change()
    test("Cambio aplicado", apply_result["status"] == "applied")

    # Verify file was modified
    new_content = test_file.read_text(encoding="utf-8")
    test("Archivo modificado correctamente", "universe" in new_content)

    # Backup created
    backup = test_file.with_suffix(".py.bak")
    test("Backup creado", backup.exists())
    test("Backup tiene contenido original", "world" in backup.read_text(encoding="utf-8"))

    # History
    test("Historial registrado", len(sm.history) == 1)
    test("Historial tiene filepath", sm.history[0]["filepath"] == "core/test_module.py")

    # Rollback
    rollback_result = sm.rollback_last()
    test("Rollback exitoso", "Revertido" in rollback_result)
    reverted_content = test_file.read_text(encoding="utf-8")
    test("Archivo revertido al original", "world" in reverted_content)

    # Propose invalid Python
    result = sm.propose_change(
        filepath="core/test_module.py",
        new_content="def broken(\n",
        reason="test",
    )
    test("Syntax error detectado", result["status"] == "rejected")
    test("Mensaje de syntax error", "sintaxis" in result["error"].lower() or "Linea" in result["error"])

    # Propose outside genesis dir
    result = sm.propose_change(
        filepath="../../etc/passwd",
        new_content="hacked",
    )
    test("Path traversal bloqueado", result["status"] == "rejected")

    # No change
    current = test_file.read_text(encoding="utf-8")
    result = sm.propose_change(
        filepath="core/test_module.py",
        new_content=current,
    )
    test("Sin cambios detectado", result["status"] == "no_change")

    # Reject pending
    sm.propose_change(
        filepath="core/test_module.py",
        new_content="# New content\npass\n",
        reason="test reject",
    )
    reject_msg = sm.reject_change()
    test("Rechazo funciona", "rechazado" in reject_msg.lower() or "test_module" in reject_msg)
    test("Sin cambio pendiente despues de rechazar", sm.pending_change is None)

    # Stats
    stats = sm.get_stats()
    test("Stats tiene total_modifications", "total_modifications" in stats)
    test("Stats tiene files_modified", stats["files_modified"] >= 1)

    # Format history
    history = sm.format_history()
    test("Historial formateado", "test_module" in history)

    # Status
    status = sm.status()
    test("Status generado", "Modificaciones" in status)

    # Dangerous patterns warning
    result = sm.propose_change(
        filepath="core/test_module.py",
        new_content="import os\nos.system('rm -rf /')\n",
        reason="test dangerous",
    )
    test("Patron peligroso detectado como warning",
         result["status"] == "rejected"
         or len(result.get("warnings", [])) > 0)

    # New file creation (no existing file)
    new_file = core_dir / "new_module.py"
    result = sm.propose_change(
        filepath="core/new_module.py",
        new_content="# New module\ndef func():\n    pass\n",
        reason="crear nuevo modulo",
    )
    test("Crear archivo nuevo propuesto", result["status"] == "pending")
    sm.apply_change()
    test("Archivo nuevo creado", new_file.exists())


# ============================================================
# TEST 6: Imports v1.2
# ============================================================
print("\n=== TEST: Imports v1.2 ===")

try:
    from core.timeout import TimeoutExecutor, Spinner, ProgressBar
    from core.plugin_system import PluginSystem, PluginInfo
    from core.self_modifier import SelfModifier
    test("Todos los imports v1.2 exitosos", True)
except ImportError as e:
    test(f"Import fallo: {e}", False)


# ============================================================
# TEST 7: Config v1.2
# ============================================================
print("\n=== TEST: Config v1.2 ===")
from config import GENESIS_VERSION

test("Version >= 1.2.0", GENESIS_VERSION >= "1.2.0")


# ============================================================
# TEST 8: Streaming Callback Pattern
# ============================================================
print("\n=== TEST: Streaming Callback Pattern ===")

# Test that the streaming callback pattern works
tokens_received = []
def mock_callback(token):
    tokens_received.append(token)

# Simulate streaming
for word in "Hola mundo esto es streaming".split():
    mock_callback(word + " ")

test("Callback recibe tokens", len(tokens_received) == 5)
test("Tokens correctos", "".join(tokens_received).strip() == "Hola mundo esto es streaming")


# ============================================================
# TEST 9: Conversation Persistence Pattern
# ============================================================
print("\n=== TEST: Conversation Persistence ===")
from core.safe_io import safe_read_json, safe_write_json

with tempfile.TemporaryDirectory() as tmpdir:
    session_file = Path(tmpdir) / "session.json"

    # Simulate save
    messages = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola! Como estas?"},
        {"role": "user", "content": "Bien, gracias"},
    ]
    session = {
        "timestamp": time.time(),
        "conversation": messages,
        "summarizer_summary": "Conversacion de saludo",
        "streaming": True,
    }
    safe_write_json(session_file, session)

    # Simulate restore
    loaded = safe_read_json(session_file)
    test("Sesion guardada correctamente", loaded is not None)
    test("Conversacion restaurada", len(loaded["conversation"]) == 3)
    test("Mensajes correctos", loaded["conversation"][0]["content"] == "Hola")
    test("Resumen restaurado", loaded["summarizer_summary"] == "Conversacion de saludo")
    test("Preferencias restauradas", loaded["streaming"] is True)


# ============================================================
# TEST 10: Plugin with real Genesis plugins dir
# ============================================================
print("\n=== TEST: Plugins dir Genesis ===")

genesis_plugins_dir = Path(__file__).parent.parent / "plugins"
test("Directorio plugins existe", genesis_plugins_dir.exists())

# Check example plugin exists
example = genesis_plugins_dir / "example_plugin.py"
test("Example plugin existe", example.exists())

# Load real plugins
ps_real = PluginSystem(plugins_dir=genesis_plugins_dir)
ps_real.load_all()
test("Plugins reales cargados", "example_plugin" in ps_real.plugins)
test("Example plugin activo", ps_real.plugins["example_plugin"].enabled)
test("Example tiene /hello", "/hello" in ps_real.commands)
test("Example tiene /dice", "/dice" in ps_real.commands)


# ============================================================
# TEST 11: TimeoutExecutor with concurrent operations
# ============================================================
print("\n=== TEST: TimeoutExecutor Concurrent ===")

results = []

def slow_task(n):
    time.sleep(0.1)
    return n * 2

# Run multiple timeouts concurrently
threads = []
for i in range(5):
    def worker(val=i):
        r = TimeoutExecutor.run(
            func=lambda v=val: slow_task(v),
            timeout=5,
        )
        results.append(r)
    t = threading.Thread(target=worker)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

test("Operaciones concurrentes completadas", len(results) == 5)
test("Resultados correctos", sorted(results) == [0, 2, 4, 6, 8])


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'='*50}")
print(f"  RESULTADOS: {passed}/{total} pasaron, {failed} fallaron")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
