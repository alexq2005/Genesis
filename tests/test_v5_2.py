"""
Tests para Genesis v5.2.0 -- ActionTracker, ResponseQualityGuard, AutoPipInstall, DynamicCtx
Verifica las 4 mejoras de evolucion implementadas.
"""
import sys, os, tempfile, shutil, re, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

passed = 0
failed = 0
errors = []
def test(name, condition):
    global passed, failed, errors
    try:
        if condition: passed += 1
        else: failed += 1; errors.append(f"FAIL: {name}"); print(f"  FAIL: {name}")
    except Exception as e:
        failed += 1; errors.append(f"ERROR: {name}: {e}"); print(f"  ERROR: {name}: {e}")

print("=" * 60)
print("GENESIS v5.2.0 -- Evolution Phase Tests")
print("=" * 60)


# =============================================================
# SECTION 1: ActionTracker
# =============================================================
print("\n--- ActionTracker ---")

from core.action_tracker import ActionTracker

# Use temp dir for isolation
_tmpdir = tempfile.mkdtemp()
at = ActionTracker(base_dir=_tmpdir)

test("ActionTracker init empty", at.get_stats()["total_actions"] == 0)

# Log various actions
at.log_tool("python", "print(1+1)", "2", success=True)
at.log_tool("escribir", "test.py ||| code", "OK", success=True)
at.log_tool("shell", "dir", "Error: not found", success=False)
test("ActionTracker 3 actions logged", at.get_stats()["total_actions"] == 3)

# Pip install tracking
at.log_pip_install("requests", success=True)
at.log_pip_install("flask", success=True)
at.log_pip_install("broken-pkg", success=False)
test("ActionTracker pip: 2 installed", len(at._installed_packages) == 2)
test("ActionTracker is_package_installed", at.is_package_installed("requests"))
test("ActionTracker not installed", not at.is_package_installed("broken-pkg"))

# Project tracking
at.log_project_created("/tmp/demo", ["main.py", "config.py", "README.md"])
test("ActionTracker project logged", at.get_stats()["total_actions"] == 7)

# Auto-fix tracking
at.log_auto_fix("ModuleNotFoundError", "pip install requests")
test("ActionTracker auto-fix logged", at.get_stats()["total_actions"] == 8)

# Persistence
at.save()
at2 = ActionTracker(base_dir=_tmpdir)
test("ActionTracker persists actions", at2.get_stats()["total_actions"] == 8)
test("ActionTracker persists packages", at2.is_package_installed("flask"))

# Context generation
context = at.get_recent_context(max_actions=5)
test("ActionTracker context not empty", len(context) > 50)
test("ActionTracker context has tool info", "python" in context or "pip" in context)

# Session summary
summary = at.get_session_summary()
test("ActionTracker session summary", "Herramientas" in summary)

# Report
report = at.generate_report()
test("ActionTracker report", "requests" in report and "flask" in report)

# Status
status = at.status()
test("ActionTracker status string", "acciones" in status)

# Clear
at.clear()
test("ActionTracker clear", at.get_stats()["total_actions"] == 0)
# Packages preserved after clear
test("ActionTracker packages preserved after clear", at.is_package_installed("requests"))

# Cleanup
shutil.rmtree(_tmpdir, ignore_errors=True)


# =============================================================
# SECTION 2: Brain Dynamic num_ctx
# =============================================================
print("\n--- Brain Dynamic num_ctx ---")

from core.brain import Brain

brain = Brain(provider="ollama", model="test")

# Test the dynamic ctx calculation indirectly by checking payload construction
# We can't call _think_ollama without Ollama running, but we can verify the class
test("Brain has think method", hasattr(brain, 'think'))
test("Brain has quick_think", hasattr(brain, 'quick_think'))
test("Brain has is_available", hasattr(brain, 'is_available'))
test("Brain has get_stats", hasattr(brain, 'get_stats'))

# Verify that the method signature supports all params
import inspect
sig = inspect.signature(brain.think)
params = list(sig.parameters.keys())
test("Brain.think has stream param", "stream" in params)
test("Brain.think has stream_callback", "stream_callback" in params)


# =============================================================
# SECTION 3: Genesis class — New features exist
# =============================================================
print("\n--- Genesis Class Features ---")

from genesis import Genesis
g = Genesis()

# Verify new methods exist
test("Genesis has _response_quality_guard", hasattr(g, '_response_quality_guard'))
test("Genesis has _auto_builder", hasattr(g, '_auto_builder'))
test("Genesis has _anti_hallucination_filter", hasattr(g, '_anti_hallucination_filter'))
test("Genesis has _auto_detect_tool", hasattr(g, '_auto_detect_tool'))

# ActionTracker accessible via lazy loading
at = g.action_tracker
test("Genesis.action_tracker loads lazily", at is not None)
test("Genesis.action_tracker is ActionTracker", type(at).__name__ == "ActionTracker")

# Test _response_quality_guard — should return response unchanged for good responses
good_response = "Python es un lenguaje de programacion interpretado, de alto nivel y proposito general. Fue creado por Guido van Rossum en 1991."
result = g._response_quality_guard("que es python", good_response, "system prompt")
test("QualityGuard passes good response", result == good_response)

# Test with very short response for complex query
short_response = "Si."
result2 = g._response_quality_guard(
    "como funciona el garbage collector de Python en detalle",
    short_response,
    "system prompt"
)
# Note: Without LLM running, the regeneration will fail/return something
# We just verify it doesn't crash
test("QualityGuard handles short response", result2 is not None)

# Test anti-hallucination filter with safe response
safe = g._anti_hallucination_filter("hola", "Hola, soy Genesis.")
test("Anti-hallucination passes safe response", safe == "Hola, soy Genesis.")


# =============================================================
# SECTION 4: Auto-detect tool — Research patterns
# =============================================================
print("\n--- Auto-Detect Tool Patterns ---")

# Test that research patterns exist in _auto_detect_tool
import inspect
source = inspect.getsource(g._auto_detect_tool)
test("Auto-detect has research patterns", "research_patterns" in source)
test("Auto-detect has que es pattern", "que|qu" in source)
test("Auto-detect has como funciona pattern", "como funciona" in source or "cómo funciona" in source)
test("Auto-detect has investiga pattern", "investiga" in source)

# Test that pip auto-install code exists in genesis.py process flow.
# Tras el refactor a mixins, la logica de procesamiento/herramientas vive en
# core/genesis_processing.py, core/genesis_commands.py y core/genesis_tools.py.
# Concatenamos las fuentes para localizar los simbolos donde realmente estan.
_root = os.path.join(os.path.dirname(__file__), "..")
genesis_source = open(os.path.join(_root, "genesis.py"), encoding="utf-8").read()
for _mf in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    _p = os.path.join(_root, "core", _mf)
    if os.path.exists(_p):
        genesis_source += "\n" + open(_p, encoding="utf-8").read()
test("Pip auto-install in genesis", "ModuleNotFoundError" in genesis_source and "pip install" in genesis_source)
test("Auto-Pip module map exists", "pip_name_map" in genesis_source)
test("Auto-Pip has cv2 mapping", "opencv-python" in genesis_source)
test("Auto-Pip has PIL mapping", "Pillow" in genesis_source)
test("Auto-Pip has sklearn mapping", "scikit-learn" in genesis_source)

# Test action_tracker in save_all list
test("ActionTracker in save_all", "action_tracker" in genesis_source)

# Test response quality guard call
test("QualityGuard in process_input", "_response_quality_guard" in genesis_source)

# Test dynamic ctx in brain
brain_source = open(os.path.join(os.path.dirname(__file__), "..", "core", "brain.py"), encoding="utf-8").read()
test("Dynamic num_ctx in brain", "dynamic_ctx" in brain_source)
test("Ctx alignment to 2048", "2048" in brain_source or "2047" in brain_source)


# =============================================================
# SECTION 5: File Editing Tools
# =============================================================
print("\n--- File Editing Tools ---")

from core.tools import FileTools

# Create test file
_edit_dir = tempfile.mkdtemp()
_edit_file = os.path.join(_edit_dir, "test_edit.py")
with open(_edit_file, "w", encoding="utf-8") as f:
    f.write("import sys\nimport os\n\ndef main():\n    print('hello')\n\nmain()\n")

# Test exact edit
result = FileTools.edit_file(_edit_file, "print('hello')", "print('world')")
test("Edit exact match", "editado" in result.lower() or "Archivo editado" in result)
with open(_edit_file, encoding="utf-8") as f:
    content = f.read()
test("Edit content correct", "print('world')" in content)

# Test edit with non-existent text
result = FileTools.edit_file(_edit_file, "THIS_DOES_NOT_EXIST", "replacement")
test("Edit not found returns error", "ERROR" in result or "No encontr" in result)

# Test edit with duplicate text
with open(_edit_file, "w", encoding="utf-8") as f:
    f.write("x = 1\nx = 1\n")
result = FileTools.edit_file(_edit_file, "x = 1", "x = 2")
test("Edit duplicate returns error", "aparece" in result.lower() or "veces" in result.lower())

# Test insert_at_line
with open(_edit_file, "w", encoding="utf-8") as f:
    f.write("line1\nline2\nline3\n")
result = FileTools.insert_at_line(_edit_file, 2, "inserted")
test("Insert returns success", "nsertad" in result)
with open(_edit_file, encoding="utf-8") as f:
    lines = f.readlines()
test("Insert at correct position", lines[1].strip() == "inserted")
test("Insert preserves other lines", lines[0].strip() == "line1" and lines[2].strip() == "line2")

# Test security: can't edit blocked files
result = FileTools.edit_file("C:\\Windows\\System32\\test.txt", "a", "b")
test("Edit blocked path", "bloqueado" in result.lower() or "ERROR" in result)

# Cleanup
shutil.rmtree(_edit_dir, ignore_errors=True)


# =============================================================
# SECTION 6: Multi-Tool Parser
# =============================================================
print("\n--- Multi-Tool Parser ---")

from core.tools import parse_all_tool_calls, parse_tool_call

# Single tool
single = "Voy a listar.\n[TOOL:listar] C:/Users/Lexus/Desktop"
r = parse_tool_call(single)
test("Single tool parse", r is not None and r[0] == "listar")

all_single = parse_all_tool_calls(single)
test("Single tool multi-parse", len(all_single) == 1)

# Multiple tools in one response
multi = ("Creando archivos...\n"
         "[TOOL:escribir] C:/test/a.py ||| print('a')\n\n"
         "Y ahora el segundo:\n"
         "[TOOL:escribir] C:/test/b.py ||| print('b')")
all_multi = parse_all_tool_calls(multi)
test("Multi-tool count", len(all_multi) == 2)
test("Multi-tool first", all_multi[0][0] == "escribir" and "a.py" in all_multi[0][1])
test("Multi-tool second", all_multi[1][0] == "escribir" and "b.py" in all_multi[1][1])

# Three tools
triple = ("[TOOL:crear_carpeta] C:/test\n"
          "[TOOL:escribir] C:/test/main.py ||| import os\n"
          "[TOOL:shell] pip install flask")
all_triple = parse_all_tool_calls(triple)
test("Triple-tool count", len(all_triple) == 3)
test("Triple-tool types", [t[0] for t in all_triple] == ["crear_carpeta", "escribir", "shell"])

# No tools
empty = "No necesito herramientas para esto."
all_empty = parse_all_tool_calls(empty)
test("No tools returns empty list", len(all_empty) == 0)

# parse_tool_call should truncate arg at next tool
truncated = parse_tool_call("[TOOL:escribir] a.py ||| code\n[TOOL:shell] dir")
test("parse_tool_call truncates at next tool", truncated is not None and "shell" not in truncated[1])


# =============================================================
# SECTION 7: Auto-Install Detection
# =============================================================
print("\n--- Auto-Install in Source ---")

# Verify install keywords exist in _auto_detect_tool
test("Install keywords in auto_detect", "install_keywords" in genesis_source)
test("Instala keyword", '"instala "' in genesis_source)
test("Pip install detection", "pip install" in genesis_source.lower())
test("npm detection", "npm" in genesis_source)

# Verify multi-tool in genesis
test("Multi-tool in genesis", "parse_all_tool_calls" in genesis_source)
test("Multi-Tool batch in genesis", "Multi-Tool" in genesis_source)

# Verify health check in startup briefing
test("Health check in briefing", "Health Check" in genesis_source or "warnings" in genesis_source)

# Verify edit tool in tools.py
tools_source = open(os.path.join(os.path.dirname(__file__), "..", "core", "tools.py"), encoding="utf-8").read()
test("Edit tool registered", "TOOL:editar" in tools_source)
test("Insert tool registered", "TOOL:insertar" in tools_source)
test("edit_file method exists", "def edit_file" in tools_source)
test("insert_at_line method exists", "def insert_at_line" in tools_source)
test("Edit handler in execute_tool", 'tool_name == "editar"' in tools_source)
test("Insert handler in execute_tool", 'tool_name == "insertar"' in tools_source)


# =============================================================
# RESULTS
# =============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed ({failed} failed)")
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")
print("=" * 60)

# Exit code
sys.exit(0 if failed == 0 else 1)
