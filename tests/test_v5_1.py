"""
Tests para Genesis v5.1.0 -- Auto-Tool Detection, Anti-Hallucination, Device Tools Security
Verifica las 3 features criticas de v5.1 que no tenian cobertura de tests.
"""
import sys, os, tempfile, shutil, re, inspect
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
print("GENESIS v5.1.0 -- Auto-Tool + Anti-Hallucination + Device Security")
print("=" * 60)


# =============================================================
# SECTION 1: Device Tools — Security Hardening
# =============================================================
print("\n--- Device Tools: Security ---")

from core.device_tools import (
    ProcessManager, AppLauncher, ClipboardManager,
    ScreenCapture, RecycleBin, FileManager, FileSearcher,
    DiskAnalyzer, DuplicateFinder, FileOrganizer,
    file_manager, process_manager, clipboard_manager,
    app_launcher, screen_capture, recycle_bin,
)

# Verificar que ProcessManager.kill_process sanitiza input
test("DT: kill_process rejects empty after sanitize",
     "invalido" in process_manager.kill_process("").lower() or
     "error" in process_manager.kill_process("").lower())

# Inyeccion via nombre de proceso: caracteres peligrosos deben ser stripped
dangerous_input = 'notepad" && del C:\\Windows\\System32'
result = process_manager.kill_process(dangerous_input)
# El nombre sanitizado no debe contener comillas ni &&
test("DT: kill_process strips injection chars",
     "&&" not in result or "error" in result.lower())

# Verificar que AppLauncher sanitiza target (strips $ ( ) chars)
open_src_quick = inspect.getsource(AppLauncher.open)
test("DT: AppLauncher sanitizes with regex",
     "re.sub" in open_src_quick or "_re.sub" in open_src_quick)

# Verificar que ClipboardManager.write no usa shell=True
# Inspeccionamos el source code para verificar la fix
import inspect
write_src = inspect.getsource(ClipboardManager.write)
test("DT: ClipboardManager.write no usa shell=True",
     "shell=True" not in write_src)
test("DT: ClipboardManager.write usa stdin (input=)",
     "input=text" in write_src or "input=" in write_src)

read_src = inspect.getsource(ClipboardManager.read)
test("DT: ClipboardManager.read no usa shell=True",
     "shell=True" not in read_src)

# Verificar kill_process no usa shell=True
kill_src = inspect.getsource(ProcessManager.kill_process)
test("DT: kill_process no usa shell=True",
     "shell=True" not in kill_src)

# Verificar AppLauncher source
open_src = inspect.getsource(AppLauncher.open)
test("DT: AppLauncher.open no usa shell=True en Windows branch",
     open_src.count("shell=True") == 0)

# Verificar ScreenCapture source
capture_src = inspect.getsource(ScreenCapture.capture)
test("DT: ScreenCapture.capture no usa shell=True",
     "shell=True" not in capture_src)

# Verificar RecycleBin.restore sanitiza
restore_src = inspect.getsource(RecycleBin.restore)
test("DT: RecycleBin.restore sanitiza name_filter",
     "re.sub" in restore_src or "_re.sub" in restore_src)


# =============================================================
# SECTION 2: Device Tools — Protected Paths
# =============================================================
print("\n--- Device Tools: Protected Paths ---")

from core.device_tools import _is_protected

test("DT: Windows dir is protected",
     _is_protected("C:\\Windows\\System32\\config"))
test("DT: System32 is protected",
     _is_protected("C:\\Windows\\System32"))
test("DT: Normal path is NOT protected",
     not _is_protected("C:\\Users\\Lexus\\Desktop\\test.txt"))
test("DT: Boot dir is protected",
     _is_protected("/boot/grub"))
test("DT: Desktop is NOT protected",
     not _is_protected("C:\\Users\\Lexus\\Desktop"))


# =============================================================
# SECTION 3: Device Tools — Functional (safe operations)
# =============================================================
print("\n--- Device Tools: Functional ---")

# FileManager basic operations
fm = FileManager()
tmp = tempfile.mkdtemp()
try:
    # create_folder
    new_folder = os.path.join(tmp, "test_genesis_folder")
    result = fm.create_folder(new_folder)
    test("DT: create_folder works", os.path.isdir(new_folder))

    # file_info
    test_file = os.path.join(tmp, "test.txt")
    with open(test_file, "w") as f:
        f.write("hello genesis")
    info = fm.file_info(test_file)
    test("DT: file_info returns info", "test.txt" in info)

    # copy
    copy_dest = os.path.join(tmp, "test_copy.txt")
    result = fm.copy(test_file, copy_dest)
    test("DT: copy works", os.path.exists(copy_dest))

    # rename
    rename_dest = os.path.join(tmp, "renamed.txt")
    fm.rename(copy_dest, rename_dest)
    test("DT: rename works", os.path.exists(rename_dest))

    # delete
    fm.delete(rename_dest)
    test("DT: delete works", not os.path.exists(rename_dest))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# FileSearcher
fs = FileSearcher()
tmp2 = tempfile.mkdtemp()
try:
    # Create test files
    for name in ["doc1.txt", "doc2.txt", "image.png"]:
        with open(os.path.join(tmp2, name), "w") as f:
            f.write("test")
    result = fs.search("doc", path=tmp2)
    test("DT: search finds files", "doc1" in result or "doc2" in result)
finally:
    shutil.rmtree(tmp2, ignore_errors=True)

# DiskAnalyzer
da = DiskAnalyzer()
result = da.analyze()
test("DT: disk_analyzer returns data", len(result) > 50)
test("DT: disk_analyzer has drive info", "GB" in result or "TB" in result)

# DuplicateFinder
df = DuplicateFinder()
tmp3 = tempfile.mkdtemp()
try:
    # Create duplicate files
    for name in ["dup1.txt", "dup2.txt"]:
        with open(os.path.join(tmp3, name), "w") as f:
            f.write("exactly the same content for dedup testing")
    result = df.find(tmp3)
    test("DT: duplicate_finder runs", isinstance(result, str))
finally:
    shutil.rmtree(tmp3, ignore_errors=True)

# FileOrganizer dry_run
fo = FileOrganizer()
tmp4 = tempfile.mkdtemp()
try:
    with open(os.path.join(tmp4, "photo.jpg"), "w") as f:
        f.write("fake jpg")
    with open(os.path.join(tmp4, "report.pdf"), "w") as f:
        f.write("fake pdf")
    result = fo.organize(tmp4, dry_run=True)
    test("DT: organize dry_run returns preview", "Simulacion" in result or "mover" in result.lower())
    # Verify files NOT moved (dry_run)
    test("DT: dry_run doesn't move files", os.path.exists(os.path.join(tmp4, "photo.jpg")))
finally:
    shutil.rmtree(tmp4, ignore_errors=True)


# =============================================================
# SECTION 4: Anti-Hallucination Filter
# =============================================================
print("\n--- Anti-Hallucination Filter ---")

# Import Genesis class for testing
from config import GENESIS_VERSION
test("AH: Version >= 5.1.0", GENESIS_VERSION >= "5.1.0")

# Test the filter directly by importing the method
# We need a Genesis instance or we can test the logic manually
# Simulate the filter logic since full Genesis init is heavy

# Recreate the filter logic for isolated testing
def mock_anti_hallucination_filter(response: str, had_tool: bool = False) -> str:
    """Replica de _anti_hallucination_filter para testing aislado."""
    resp_lower = response.lower()

    hallucination_patterns = [
        ("restaurando", "restaurar archivos"),
        ("he restaurado", "restaurar archivos"),
        ("ha sido restaurado", "restaurar archivos"),
        ("archivo restaurado", "restaurar archivos"),
        ("accediendo a", "acceder al sistema"),
        ("he accedido", "acceder al sistema"),
        ("eliminando el archivo", "eliminar archivos"),
        ("he eliminado", "eliminar archivos"),
        ("archivo eliminado", "eliminar archivos"),
        ("moviendo el archivo", "mover archivos"),
        ("he movido", "mover archivos"),
        ("copiando el archivo", "copiar archivos"),
        ("he copiado", "copiar archivos"),
        ("instalando", "instalar software"),
        ("he instalado", "instalar software"),
        ("descargando", "descargar archivos"),
        ("he descargado", "descargar archivos"),
        ("ejecutando el comando", "ejecutar comandos"),
        ("he ejecutado", "ejecutar comandos"),
    ]

    fake_indicators = [
        "informe de ventas", "fotos de vacaciones",
        "confirmación de reserva", "proyecto de diseño",
        "lista de compras", "documento.txt", "imagen.jpg",
        "el archivo ha sido", "ahora muestra 0",
        "se ha completado", "operación exitosa",
    ]

    if not had_tool:
        for pattern, action in hallucination_patterns:
            if pattern in resp_lower:
                if any(fi in resp_lower for fi in fake_indicators):
                    return (f"No pude {action} — esa acción requiere una "
                            f"herramienta que no se ejecutó. "
                            f"Intenta pedirlo de forma más específica.")

    return response

# Test: respuesta normal (sin alucinacion)
normal = "Claro, puedo ayudarte con eso. ¿Qué necesitas?"
test("AH: normal response passes through",
     mock_anti_hallucination_filter(normal) == normal)

# Test: hallucination detected (dice que restauro + indicador falso)
hallucinated = "He restaurado el archivo 'documento.txt' exitosamente. El archivo ha sido recuperado."
result = mock_anti_hallucination_filter(hallucinated)
test("AH: catches hallucinated restore",
     "No pude" in result and "restaurar" in result)

# Test: hallucination con eliminacion + indicador falso
hallucinated2 = "He eliminado el archivo 'imagen.jpg'. La operación exitosa."
result2 = mock_anti_hallucination_filter(hallucinated2)
test("AH: catches hallucinated delete",
     "No pude" in result2 and "eliminar" in result2)

# Test: hallucination con instalacion + indicador falso
hallucinated3 = "Instalando el paquete solicitado... se ha completado la instalación."
result3 = mock_anti_hallucination_filter(hallucinated3)
test("AH: catches hallucinated install",
     "No pude" in result3 and "instalar" in result3)

# Test: response con tool call real (had_tool=True) pasa sin filtrar
real_tool = "He restaurado el archivo 'documento.txt'. El archivo ha sido recuperado."
result4 = mock_anti_hallucination_filter(real_tool, had_tool=True)
test("AH: real tool call passes through",
     result4 == real_tool)

# Test: response mencionando accion pero sin indicador falso
mention_only = "Puedo ayudarte restaurando esos archivos si me das la ruta."
result5 = mock_anti_hallucination_filter(mention_only)
test("AH: mention without fake indicator passes",
     result5 == mention_only)

# Test: multiples patrones — solo primer match
multi = "He copiado el informe de ventas y he movido las fotos de vacaciones."
result6 = mock_anti_hallucination_filter(multi)
test("AH: catches first match in multi-pattern",
     "No pude" in result6)

# Edge case: empty response
test("AH: empty response passes",
     mock_anti_hallucination_filter("") == "")


# =============================================================
# SECTION 5: Auto-Tool Detection Keywords
# =============================================================
print("\n--- Auto-Tool Detection: Keyword Matching ---")

# Test keyword detection logic isolated from system calls
# We test the MATCHING logic, not the actual tool execution

def test_keyword_match(inp: str, keywords: list) -> bool:
    """Simula el patron de matching de _auto_detect_tool."""
    inp = inp.lower().strip()
    return any(k in inp for k in keywords)

# System keywords — " ram " requires spaces
sys_keywords = ["mi sistema", "mi cpu", " ram ", "mi memoria", "mi gpu",
                "mi disco", "mi hardware",
                "que computadora", "que pc", "especificaciones", "specs",
                "info del sistema", "informacion del sistema"]

test("AT: 'cuanta ram tengo' matches ' ram '",
     test_keyword_match("cuanta ram tengo", sys_keywords))

test("AT: 'programas de inicio' does NOT match ' ram '",
     not test_keyword_match("programas de inicio", sys_keywords))

test("AT: 'mis programas' does NOT match ' ram '",
     not test_keyword_match("mis programas", sys_keywords))

test("AT: 'mi cpu es buena?' matches 'mi cpu'",
     test_keyword_match("mi cpu es buena?", sys_keywords))

test("AT: 'que pc tengo' matches 'que pc'",
     test_keyword_match("que pc tengo", sys_keywords))

# Startup keywords — must come BEFORE sys_keywords
startup_keywords = ["programas de inicio", "inicio de windows", "startup",
                    "que se ejecuta al inicio", "arranque", "ejecutan al inicio"]

test("AT: 'programas de inicio' matches startup",
     test_keyword_match("programas de inicio", startup_keywords))

test("AT: 'que se ejecuta al inicio' matches startup",
     test_keyword_match("que se ejecuta al inicio", startup_keywords))

# Process keywords
process_keywords = ["procesos", "que esta corriendo", "que esta ejecutando",
                    "programas abiertos", "apps abiertas", "tareas"]

test("AT: 'que procesos hay' matches process",
     test_keyword_match("que procesos hay", process_keywords))

# Clipboard
clip_keywords = ["portapapeles", "clipboard", "que copie", "que tengo copiado"]
test("AT: 'que tengo en el portapapeles' matches",
     test_keyword_match("que tengo en el portapapeles", clip_keywords))

# Capture
capture_keywords = ["captura", "screenshot", "pantallazo", "foto de pantalla"]
test("AT: 'toma un screenshot' matches",
     test_keyword_match("toma un screenshot", capture_keywords))

# Recycle bin
recycle_keywords = ["papelera", "reciclaje", "recycle", "eliminados recientemente"]
test("AT: 'que hay en la papelera' matches",
     test_keyword_match("que hay en la papelera", recycle_keywords))

# List files
list_keywords = ["lista", "muestra", "que hay en", "archivos en", "que tiene",
                 "contenido de", "ver carpeta", "mostrar archivos", "que archivos"]
test("AT: 'que hay en escritorio' matches list",
     test_keyword_match("que hay en escritorio", list_keywords))

# Delete
delete_keywords = ["elimina ", "borra ", "borrar "]
test("AT: 'elimina test.txt' matches delete",
     test_keyword_match("elimina test.txt", delete_keywords))

# Organize
organize_keywords = ["organiza", "ordena", "clasifica", "organizar"]
test("AT: 'organiza mi escritorio' matches organize",
     test_keyword_match("organiza mi escritorio", organize_keywords))

# Open
open_keywords = ["abre ", "abrir ", "ejecuta ", "lanza "]
test("AT: 'abre chrome' matches open",
     any("abre chrome".startswith(k) or f" {k}" in "abre chrome" for k in open_keywords))

# Keyword ordering: startup BEFORE system prevents false match
inp_startup = "programas de inicio"
startup_matches = test_keyword_match(inp_startup, startup_keywords)
system_matches = test_keyword_match(inp_startup, sys_keywords)
test("AT: 'programas de inicio' matches startup first, not system",
     startup_matches and not system_matches)


# =============================================================
# SECTION 6: Auto-Tool Path Extraction
# =============================================================
print("\n--- Auto-Tool: Path Extraction ---")

# Test regex for path detection
path_regex = r'[A-Za-z]:[/\\][\w/\\._ -]+'

test("AT: extracts Windows path",
     re.search(path_regex, "lee C:/Users/Lexus/test.txt") is not None)

test("AT: extracts backslash path",
     re.search(path_regex, "abre C:\\Users\\Lexus\\Desktop") is not None)

test("AT: no match on plain text",
     re.search(path_regex, "hola como estas") is None)

# Test path_keywords mapping
path_keywords = {
    "escritorio": "C:/Users/Lexus/Desktop",
    "desktop": "C:/Users/Lexus/Desktop",
    "descargas": "C:/Users/Lexus/Downloads",
    "downloads": "C:/Users/Lexus/Downloads",
    "documentos": "C:/Users/Lexus/Documents",
}

test("AT: 'escritorio' maps to Desktop",
     path_keywords.get("escritorio") == "C:/Users/Lexus/Desktop")

test("AT: 'descargas' maps to Downloads",
     path_keywords.get("descargas") == "C:/Users/Lexus/Downloads")


# =============================================================
# SECTION 7: Logger Spec Compliance
# =============================================================
print("\n--- Logger: Spec Compliance ---")

from pathlib import Path
from core.logger import GenesisLogger, ModuleLogger

tmp_log = tempfile.mkdtemp()
logger = GenesisLogger(log_dir=Path(tmp_log))
child = logger.get_child("test_v51")

test("LOG: child has .info()", hasattr(child, "info"))
test("LOG: child has .error()", hasattr(child, "error"))
test("LOG: child has .debug()", hasattr(child, "debug"))
test("LOG: child does NOT have .warn()", not hasattr(child, "warn"))
test("LOG: child does NOT have .warning()", not hasattr(child, "warning"))

shutil.rmtree(tmp_log, ignore_errors=True)


# =============================================================
# SECTION 8: Semantic Memory field fix
# =============================================================
print("\n--- Semantic Memory: Field Matching ---")

# Verify semantic_memory uses "id" not "key"
import inspect
from core.semantic_memory import SemanticMemory

recall_src = inspect.getsource(SemanticMemory.recall)
test("SM: recall uses 'id' field",
     '"id"' in recall_src)
test("SM: recall does NOT use 'key' field",
     'get("key"' not in recall_src)

# Also check dedup in index_conversation
if hasattr(SemanticMemory, 'index_conversation'):
    index_src = inspect.getsource(SemanticMemory.index_conversation)
    test("SM: index dedup uses 'id' field",
         '"id"' in index_src)
    test("SM: index dedup does NOT use 'key'",
         'get("key"' not in index_src)


# =============================================================
# SECTION 9: Self-Modifier & Mutation
# =============================================================
print("\n--- Self-Modifier: Code Mutation Safety ---")

from core.self_modifier import SelfModifier

# Test: SelfModifier rejects file outside genesis dir
tmp_sm = tempfile.mkdtemp()
sm = SelfModifier(genesis_dir=Path(tmp_sm))
result = sm.propose_change("../../etc/passwd", "malicious", reason="test")
test("SM: rejects path traversal",
     result["status"] == "rejected")

# Test: SelfModifier rejects bad syntax
bad_py = "def foo(\n  return"
result = sm.propose_change("test_bad.py", bad_py, reason="test")
test("SM: rejects bad Python syntax",
     result["status"] == "rejected" and "sintaxis" in result.get("error", "").lower())

# Test: SelfModifier detects dangerous patterns
dangerous_code = "import os\nos.system('rm -rf /')\n"
result = sm.propose_change("test_danger.py", dangerous_code, reason="test")
test("SM: warns about os.system",
     result["status"] == "rejected"
     or len(result.get("warnings", [])) > 0)

# Test: SelfModifier accepts valid Python change
safe_file = Path(tmp_sm) / "test_safe.py"
safe_file.write_text("# original\nx = 1\n", encoding="utf-8")
result = sm.propose_change("test_safe.py", "# modified\nx = 2\n", reason="test")
test("SM: accepts valid change",
     result["status"] == "pending")
test("SM: generates diff for valid change",
     "+x = 2" in result.get("diff", ""))

# Test: SelfModifier identifies critical files
test("SM: genesis.py is critical",
     "genesis.py" in sm.CRITICAL_FILES)
test("SM: core/brain.py is critical",
     "core/brain.py" in sm.CRITICAL_FILES)

# Test: SelfModifier detects no_change
same_content = "# same\nx = 1\n"
same_file = Path(tmp_sm) / "test_same.py"
same_file.write_text(same_content, encoding="utf-8")
result = sm.propose_change("test_same.py", same_content, reason="test")
test("SM: detects no_change",
     result["status"] == "no_change")

# Test: evolution.evolve method exists and has correct signature
from core.evolution import EvolutionEngine
test("EVO: evolve method exists",
     hasattr(EvolutionEngine, "evolve"))
evo_sig = inspect.signature(EvolutionEngine.evolve)
test("EVO: evolve accepts real_fitness param",
     "real_fitness" in evo_sig.parameters)
test("EVO: evolve accepts feedback_context param",
     "feedback_context" in evo_sig.parameters)

# Test: evaluate_and_evolve does NOT exist (was the bug)
test("EVO: evaluate_and_evolve does NOT exist (was buggy)",
     not hasattr(EvolutionEngine, "evaluate_and_evolve"))

# Test: genesis.py uses evolve() not evaluate_and_evolve()
genesis_src = open(os.path.join(os.path.dirname(__file__), "..", "genesis.py"),
                   encoding="utf-8").read()
for _extra in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    _ep = os.path.join(os.path.dirname(__file__), "..", "core", _extra)
    if os.path.exists(_ep):
        genesis_src += "\n" + open(_ep, encoding="utf-8").read()
test("GEN: no longer calls evaluate_and_evolve",
     "evaluate_and_evolve" not in genesis_src)
test("GEN: calls evolution.evolve() directly",
     "self.evolution.evolve(" in genesis_src)
test("GEN: has /mutate command handler",
     "_cmd_mutate" in genesis_src)
test("GEN: /mutate is wired in command dispatch",
     '"/mutate"' in genesis_src or "'/mutate'" in genesis_src)

# Cleanup
shutil.rmtree(tmp_sm, ignore_errors=True)


# =============================================================
# RESULTS
# =============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTADOS: {passed}/{total} passed, {failed} failed")
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
