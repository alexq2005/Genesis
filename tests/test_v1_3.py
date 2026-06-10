"""
Tests para Genesis v1.3.0:
1. Brain streaming support (fix critico)
2. Tool Creator
3. Knowledge Graph
4. Self-Modifier auto-test
5. Version check
6. All imports
"""
import sys
import os
import time
import tempfile
from pathlib import Path

# UTF-8 para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
# TEST 1: Brain streaming support
# ============================================================
print("\n=== TEST: Brain Streaming ===")
from core.brain import Brain
import inspect

brain = Brain(provider="ollama", model="test")
sig = inspect.signature(brain.think)

test("Brain.think acepta stream", "stream" in sig.parameters)
test("Brain.think acepta stream_callback", "stream_callback" in sig.parameters)
test("Brain.think stream default False", sig.parameters["stream"].default is False)
test("Brain.think callback default None", sig.parameters["stream_callback"].default is None)

# Verify internal methods also accept streaming
sig_ollama = inspect.signature(brain._think_ollama)
test("_think_ollama acepta stream", "stream" in sig_ollama.parameters)
test("_think_ollama acepta callback", "callback" in sig_ollama.parameters)

sig_openai = inspect.signature(brain._think_openai)
test("_think_openai acepta stream", "stream" in sig_openai.parameters)

sig_anthropic = inspect.signature(brain._think_anthropic)
test("_think_anthropic acepta stream", "stream" in sig_anthropic.parameters)


# ============================================================
# TEST 2: Tool Creator
# ============================================================
print("\n=== TEST: Tool Creator ===")
from core.tool_creator import ToolCreator

with tempfile.TemporaryDirectory() as tmpdir:
    tools_dir = Path(tmpdir) / "tools_custom"
    tools_dir.mkdir()
    registry = Path(tmpdir) / "registry.json"

    tc = ToolCreator(tools_dir=tools_dir, registry_file=registry)
    test("ToolCreator creado", tc is not None)
    test("Sin tools iniciales", len(tc.tools) == 0)

    # Create a valid tool (safe — no eval/exec)
    calc_code = '''def execute(arg: str) -> str:
    """Repite el argumento en mayusculas."""
    return arg.upper()
'''
    result = tc.create_tool(
        name="uppercase",
        description="Convierte texto a mayusculas",
        code=calc_code,
        usage="[TOOL:uppercase] texto",
    )
    test("Tool creada exitosamente", result["status"] == "created")
    test("Tool registrada", "uppercase" in tc.tools)

    # Execute custom tool
    result = tc.execute_tool("uppercase", "hola mundo")
    test("Tool ejecutada correctamente", result == "HOLA MUNDO")

    result = tc.execute_tool("uppercase", "genesis")
    test("Segunda ejecucion correcta", result == "GENESIS")

    # Non-existent tool
    result = tc.execute_tool("nonexistent", "arg")
    test("Tool inexistente retorna None", result is None)

    # Tool with syntax error
    result = tc.create_tool(
        name="broken",
        description="Tool rota",
        code="def execute(arg):\n    return unclosed_string",
    )
    # This might parse OK but fail at runtime - let's test a real syntax error
    result2 = tc.create_tool(
        name="broken2",
        description="Tool rota",
        code="def execute(arg\n    return 'hi'",
    )
    test("Tool con syntax error rechazada", result2["status"] == "error")

    # Tool with blocked import
    result = tc.create_tool(
        name="dangerous",
        description="Tool peligrosa",
        code="import ctypes\ndef execute(arg):\n    return 'hacked'",
    )
    test("Tool con import peligroso bloqueada", result["status"] == "error")

    # Tool with reserved name
    result = tc.create_tool(
        name="python",
        description="Override python",
        code="def execute(arg): return arg",
    )
    test("Nombre reservado rechazado", result["status"] == "error")

    # Tool description for LLM
    desc = tc.get_tools_description()
    test("Descripcion para LLM generada", "uppercase" in desc)

    # Toggle
    tc.toggle_tool("uppercase")
    test("Tool desactivada", not tc.tools["uppercase"].enabled)
    tc.toggle_tool("uppercase")
    test("Tool reactivada", tc.tools["uppercase"].enabled)

    # Stats
    test("Calls tracked", tc.tools["uppercase"].calls == 2)

    # Delete
    tc.delete_tool("uppercase")
    test("Tool eliminada", "uppercase" not in tc.tools)

    # Also delete "broken" (valid syntax, runtime error — it was created successfully)
    if "broken" in tc.tools:
        tc.delete_tool("broken")

    # Status
    status = tc.status()
    test("Status generado", "custom" in status.lower() or "Tools" in status)

    # List (empty after delete)
    listing = tc.list_tools()
    test("Lista vacia despues de delete", "No hay" in listing or len(tc.tools) == 0)


# ============================================================
# TEST 3: Knowledge Graph
# ============================================================
print("\n=== TEST: Knowledge Graph ===")
from core.knowledge_graph import KnowledgeGraph

with tempfile.TemporaryDirectory() as tmpdir:
    graph_file = Path(tmpdir) / "kg.json"
    kg = KnowledgeGraph(graph_file=graph_file)
    test("KnowledgeGraph creado", kg is not None)
    test("Grafo vacio inicialmente", len(kg.nodes) == 0)

    # Learn from text
    kg.learn("Python es un lenguaje de programacion muy popular")
    test("Nodos creados despues de learn", len(kg.nodes) > 0)
    test("Python es un nodo", "python" in kg.nodes)
    test("Programacion es un nodo", "programacion" in kg.nodes)

    # Learn more to build connections
    kg.learn("Me gusta programar en Python con pandas y numpy")
    kg.learn("Python tiene muchas bibliotecas para data science")
    kg.learn("Uso pandas para analisis de datos en Python")

    # Check edges exist
    test("Aristas creadas", len(kg.edges) > 0)

    # Get related
    related = kg.get_related("python", depth=1)
    test("Python tiene conceptos relacionados", len(related) > 0)
    related_names = [r["concept"] for r in related]
    test("Pandas relacionado con Python", "pandas" in related_names)

    # Search
    results = kg.search("python")
    test("Busqueda funciona", len(results) > 0)
    test("Busqueda encuentra python", results[0]["concept"] == "python")

    # Context for query
    context = kg.get_context_for_query("Como uso pandas en Python?")
    test("Contexto para query generado", len(context) > 0)
    test("Contexto menciona python", "python" in context.lower())

    # Extract concepts
    concepts = KnowledgeGraph.extract_concepts("Node.js es rapido para APIs REST")
    test("Extract concepts funciona", len(concepts) > 0)
    test("node.js extraido", "node.js" in concepts)

    # Stopwords filtered
    concepts = KnowledgeGraph.extract_concepts("el la los de en con por para")
    test("Stopwords filtradas", len(concepts) == 0)

    # Format graph
    formatted = kg.format_graph(top_n=5)
    test("Grafo formateado", "python" in formatted)

    # Status
    status = kg.status()
    test("Status tiene info", "Nodos" in status)

    # Stats
    stats = kg.get_stats()
    test("Stats tiene nodes", stats["nodes"] > 0)
    test("Stats tiene edges", stats["edges"] > 0)

    # Persistence
    kg2 = KnowledgeGraph(graph_file=graph_file)
    test("Persistencia: nodos cargados", len(kg2.nodes) == len(kg.nodes))
    test("Persistencia: aristas cargadas", len(kg2.edges) == len(kg.edges))

    # Depth 2 search
    kg.learn("pandas usa numpy internamente para calculos")
    related_depth2 = kg.get_related("python", depth=2)
    test("Busqueda depth=2 retorna mas resultados", len(related_depth2) >= len(related))


# ============================================================
# TEST 4: Self-Modifier auto-test feature
# ============================================================
print("\n=== TEST: Self-Modifier Auto-Test ===")
from core.self_modifier import SelfModifier

with tempfile.TemporaryDirectory() as tmpdir:
    genesis_dir = Path(tmpdir) / "genesis"
    genesis_dir.mkdir()
    core_dir = genesis_dir / "core"
    core_dir.mkdir()
    tests_dir = genesis_dir / "tests"
    tests_dir.mkdir()
    history_file = genesis_dir / "memory_data" / "sm.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    # Create a test file that always passes
    (tests_dir / "test_simple.py").write_text(
        "import sys\nprint('  [PASS] test simple')\nprint('RESULTADOS: 1/1')\n",
        encoding="utf-8"
    )

    # Create a source file
    src_file = core_dir / "example.py"
    src_file.write_text("# Original\ndef hello():\n    return 'world'\n", encoding="utf-8")

    sm = SelfModifier(genesis_dir=genesis_dir, history_file=history_file)

    # Apply a valid change (tests should pass)
    sm.propose_change(
        filepath="core/example.py",
        new_content="# Modified\ndef hello():\n    return 'universe'\n",
        reason="test auto-test",
    )
    result = sm.apply_change()
    test("Cambio con tests pasando: applied", result["status"] == "applied")
    test("Mensaje menciona tests", "Tests" in result["message"] or "PASARON" in result["message"])

    # Now create a test that FAILS
    (tests_dir / "test_fail.py").write_text(
        "import sys\nprint('  [FAIL] something')\nprint('RESULTADOS: 0/1')\nsys.exit(1)\n",
        encoding="utf-8"
    )

    # Apply another change (tests should fail → auto-revert)
    sm.propose_change(
        filepath="core/example.py",
        new_content="# This should be reverted\ndef hello():\n    return 'reverted'\n",
        reason="test auto-revert",
    )
    result = sm.apply_change()
    test("Cambio con tests fallando: reverted", result["status"] == "reverted")
    test("Mensaje explica reversion", "REVERTIDO" in result["message"] or "revert" in result["message"].lower())

    # Verify file was actually reverted
    content = src_file.read_text(encoding="utf-8")
    test("Archivo realmente revertido", "universe" in content)  # Should be the previous version
    test("Archivo NO tiene contenido nuevo", "reverted" not in content.lower() or "This should" not in content)


# ============================================================
# TEST 5: Imports v1.3
# ============================================================
print("\n=== TEST: Imports v1.3 ===")

try:
    from core.tool_creator import ToolCreator, CustomTool
    from core.knowledge_graph import KnowledgeGraph
    from core.brain import Brain
    from core.self_modifier import SelfModifier
    test("Todos los imports v1.3 exitosos", True)
except ImportError as e:
    test(f"Import fallo: {e}", False)


# ============================================================
# TEST 6: Config v1.3
# ============================================================
print("\n=== TEST: Config v1.3 ===")
from config import GENESIS_VERSION

test("Version >= 1.3.0", GENESIS_VERSION >= "1.3.0")


# ============================================================
# TEST 7: Knowledge Graph edge cases
# ============================================================
print("\n=== TEST: KG Edge Cases ===")

with tempfile.TemporaryDirectory() as tmpdir:
    kg = KnowledgeGraph(graph_file=Path(tmpdir) / "kg.json")

    # Empty query
    context = kg.get_context_for_query("")
    test("Query vacio retorna vacio", context == "")

    # Single word
    kg.learn("test")
    test("Single word aprendida", "test" in kg.nodes)

    # Very short words filtered
    kg2 = KnowledgeGraph(graph_file=Path(tmpdir) / "kg2.json")
    kg2.learn("a b c de el")
    test("Palabras cortas/stopwords filtradas", len(kg2.nodes) == 0)

    # Non-existent concept search
    related = kg.get_related("nonexistent")
    test("Concepto inexistente: lista vacia", related == [])


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'='*50}")
print(f"  RESULTADOS: {passed}/{total} pasaron, {failed} fallaron")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
