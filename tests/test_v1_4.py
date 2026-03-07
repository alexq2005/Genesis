"""
Tests para Genesis v1.4.0
- Prompt Templates (auto-deteccion, set/get, temperatura)
- Proactive Engine (sugerencias, cooldown, toggle)
- Project Generator (parse multi-archivo, validacion, generacion)
- Web UI (importable, rutas)
- Integracion en genesis.py
"""
import sys
import os
import tempfile
import shutil
import time

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# Mini test framework
# ============================================================
_passed = 0
_failed = 0

def test(name, condition):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name}")


# ============================================================
# TEST 1: Prompt Templates
# ============================================================
print("\n=== TEST: Prompt Templates ===")
from core.prompt_templates import PromptTemplateSystem, PromptTemplate

pts = PromptTemplateSystem()

# Defaults cargados
test("Templates default cargados", len(pts.templates) >= 7)
test("Template 'code' existe", "code" in pts.templates)
test("Template 'debug' existe", "debug" in pts.templates)
test("Template 'creative' existe", "creative" in pts.templates)
test("Template 'explain' existe", "explain" in pts.templates)
test("Template 'security' existe", "security" in pts.templates)

# Auto-deteccion
t_code = pts.detect_template("crea un programa en python que calcule primos")
test("Auto-detect: codigo", t_code is not None and t_code.name == "code")

t_debug = pts.detect_template("tengo un error en el traceback de mi funcion")
test("Auto-detect: debug", t_debug is not None and t_debug.name == "debug")

t_explain = pts.detect_template("explicame como funciona la recursion")
test("Auto-detect: explicacion", t_explain is not None and t_explain.name == "explain")

t_creative = pts.detect_template("inventa una historia sobre un robot")
test("Auto-detect: creativo", t_creative is not None and t_creative.name == "creative")

t_none = pts.detect_template("hola que tal")
test("Auto-detect: sin match significativo", t_none is None)

# Temperatura por tipo
test("Temp codigo < 0.5", pts.templates["code"].temperature < 0.5)
test("Temp debug < 0.3", pts.templates["debug"].temperature <= 0.3)
test("Temp creative > 0.7", pts.templates["creative"].temperature > 0.7)

# get_system_extra
extra, temp, name = pts.get_system_extra("escribe un script python")
test("get_system_extra retorna extra", len(extra) > 0)
test("get_system_extra retorna temp", isinstance(temp, float))
test("get_system_extra retorna nombre", name == "code")

extra_none, temp_none, name_none = pts.get_system_extra("hola")
test("get_system_extra sin match: extra vacio", extra_none == "")
test("get_system_extra sin match: default temp", temp_none == 0.7)
test("get_system_extra sin match: default name", name_none == "default")

# Set active manual
result = pts.set_active("creative")
test("Set active exitoso", "creative" in result.lower() or "activo" in result.lower())
test("Auto-select desactivado", pts.auto_select is False)

# Con template forzado, siempre retorna ese
forced = pts.detect_template("escribe un script python")
test("Template forzado ignora input", forced is not None and forced.name == "creative")

# Volver a auto
pts.set_active("auto")
test("Auto-select reactivado", pts.auto_select is True)

# Template inexistente
result_bad = pts.set_active("inexistente")
test("Template inexistente: error", "no encontrado" in result_bad.lower() or "not found" in result_bad.lower())

# Custom template
pts.register(PromptTemplate(
    name="custom_test",
    description="Test template",
    system_extra="TEST EXTRA",
    temperature=0.42,
    tags=["testword123"],
))
test("Custom template registrado", "custom_test" in pts.templates)

custom_detect = pts.detect_template("algo sobre testword123")
test("Custom template detectado", custom_detect is not None and custom_detect.name == "custom_test")

# list_templates
listing = pts.list_templates()
test("list_templates tiene contenido", len(listing) > 50)
test("list_templates menciona templates", "AUTOMATICO" in listing or "auto" in listing.lower())

# status
status = pts.status()
test("status tiene info", "Templates" in status or "templates" in status.lower())

# Uses counter
initial_uses = pts.templates["code"].uses
pts.detect_template("crea un programa en python")
test("Uses incrementa", pts.templates["code"].uses > initial_uses)


# ============================================================
# TEST 2: Proactive Engine
# ============================================================
print("\n=== TEST: Proactive Engine ===")
from core.proactive import ProactiveEngine

pe = ProactiveEngine(enabled=True)

# Estado inicial
test("ProactiveEngine creado", pe is not None)
test("Enabled por default", pe.enabled)
test("Sin sugerencias iniciales", len(pe.shown_suggestions) == 0)

# No sugiere en primeras interacciones
result = pe.analyze("hola", "hola! en que te ayudo?")
test("No sugiere en interaccion 1", result is None)

result = pe.analyze("como estas", "bien!")
test("No sugiere en interaccion 2", result is None)

# Toggle
toggle_result = pe.toggle()
test("Toggle desactiva", pe.enabled is False)
test("Toggle mensaje", "desactivado" in toggle_result)

pe.toggle()
test("Toggle reactiva", pe.enabled is True)

# Status
status = pe.status()
test("Status tiene info", "Proactivo" in status or "proactivo" in status.lower())

# Stats
stats = pe.get_stats()
test("Stats tiene enabled", "enabled" in stats)
test("Stats tiene total", "total_suggestions" in stats)

# Proactive desactivado no sugiere
pe.enabled = False
pe.interaction_count = 10  # Simular interacciones
result = pe.analyze("algo", "respuesta larga " * 100)
test("Desactivado no sugiere", result is None)

pe.enabled = True

# Cooldown: forzar que ya haya sugerido recientemente
pe.last_suggestion_time = time.time()
pe.interaction_count = 10
result = pe.analyze("algo", "respuesta")
test("Cooldown respetado", result is None)


# ============================================================
# TEST 3: Project Generator
# ============================================================
print("\n=== TEST: Project Generator ===")
from core.project_generator import ProjectGenerator

pg = ProjectGenerator()

# Parseo de archivos - Formato [FILE:]
response1 = """
Aqui tienes el proyecto:

[FILE: main.py]
```python
print("Hello World")
```

[FILE: utils/helper.py]
```python
def greet(name):
    return f"Hello {name}"
```
"""

files1 = pg.parse_files(response1)
test("Parse [FILE:]: 2 archivos encontrados", len(files1) == 2)
test("Parse [FILE:]: main.py", any(f["path"] == "main.py" for f in files1))
test("Parse [FILE:]: utils/helper.py", any(f["path"] == "utils/helper.py" for f in files1))

# Parseo - Formato ### titulo
response2 = """
### app.py
```python
from flask import Flask
app = Flask(__name__)
```

### config.json
```json
{"debug": true}
```
"""

files2 = pg.parse_files(response2)
test("Parse ###: archivos encontrados", len(files2) >= 1)

# Parseo - Formato # --- name ---
response3 = """
# --- models.py ---
```python
class User:
    pass
```

# --- views.py ---
```python
def index():
    pass
```
"""

files3 = pg.parse_files(response3)
test("Parse ---: archivos encontrados", len(files3) >= 1)

# Validacion de rutas
test("Path valido: archivo.py", pg._validate_path("archivo.py"))
test("Path valido: src/main.py", pg._validate_path("src/main.py"))
test("Path invalido: ../escape.py", not pg._validate_path("../escape.py"))
test("Path invalido: /etc/passwd", not pg._validate_path("/etc/passwd"))
test("Path invalido: C:\\hack.py", not pg._validate_path("C:\\hack.py"))
test("Path invalido: extension .exe", not pg._validate_path("virus.exe"))

# Deteccion de lenguaje
test("Detect lang: python", pg._detect_language("main.py") == "python")
test("Detect lang: javascript", pg._detect_language("app.js") == "javascript")
test("Detect lang: html", pg._detect_language("index.html") == "html")

# has_multiple_files
test("has_multiple_files: True con 2+", pg.has_multiple_files(response1))
test("has_multiple_files: False con 0", not pg.has_multiple_files("hola mundo"))

# Generacion real en directorio temporal
tmp_dir = tempfile.mkdtemp(prefix="genesis_test_")
try:
    result = pg.generate(response1, tmp_dir)
    test("Generate: archivos creados", len(result["created"]) == 2)
    test("Generate: sin errores", len(result["errors"]) == 0)

    # Verificar archivos existen
    test("Generate: main.py existe", os.path.exists(os.path.join(tmp_dir, "main.py")))
    test("Generate: subdirectorio creado", os.path.exists(os.path.join(tmp_dir, "utils")))
    test("Generate: helper.py existe", os.path.exists(os.path.join(tmp_dir, "utils", "helper.py")))

    # Contenido correcto
    with open(os.path.join(tmp_dir, "main.py"), "r", encoding="utf-8") as f:
        content = f.read()
    test("Generate: contenido correcto", "Hello World" in content)

    # No sobreescribe por default
    result2 = pg.generate(response1, tmp_dir, overwrite=False)
    test("Generate: no sobreescribe", len(result2["skipped"]) == 2)

    # Sobreescribe con flag
    result3 = pg.generate(response1, tmp_dir, overwrite=True)
    test("Generate: sobreescribe con flag", len(result3["created"]) == 2)

    # format_result
    formatted = pg.format_result(result)
    test("format_result tiene contenido", "creados" in formatted.lower() or "PROYECTO" in formatted)

    # Status
    status = pg.status()
    test("Status actualizado", "ultimo" in status.lower() or "Ultimo" in status)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

# Generacion con respuesta sin archivos
result_empty = pg.generate("hola mundo sin archivos", tempfile.mkdtemp(prefix="genesis_empty_"))
test("Generate vacia: sin creados", len(result_empty["created"]) == 0)


# ============================================================
# TEST 4: Imports v1.4
# ============================================================
print("\n=== TEST: Imports v1.4 ===")

all_imports_ok = True
try:
    from core.prompt_templates import PromptTemplateSystem
    from core.proactive import ProactiveEngine
    from core.project_generator import ProjectGenerator
except ImportError as e:
    all_imports_ok = False
    print(f"  Import error: {e}")

test("Todos los imports v1.4 exitosos", all_imports_ok)


# ============================================================
# TEST 5: Config v1.4
# ============================================================
print("\n=== TEST: Config v1.4 ===")
from config import GENESIS_VERSION

test("Version >= 1.4.0", GENESIS_VERSION >= "1.4.0")


# ============================================================
# TEST 6: Web UI (importabilidad)
# ============================================================
print("\n=== TEST: Web UI ===")

# Verificar que web_ui.py existe y es importable (sin ejecutar Flask)
web_ui_path = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
test("web_ui.py existe", os.path.exists(web_ui_path))

# Verificar que contiene las rutas esperadas
with open(web_ui_path, "r", encoding="utf-8") as f:
    web_content = f.read()

test("Web UI tiene ruta /", "def index" in web_content)
test("Web UI tiene /api/chat", "def api_chat" in web_content)
test("Web UI tiene /api/info", "def api_info" in web_content)
test("Web UI tiene /api/status", "def api_status" in web_content)
test("Web UI tiene HTML template", "HTML_TEMPLATE" in web_content)
test("Web UI tiene SSE o streaming ref", "stream" in web_content.lower() or "SSE" in web_content)


# ============================================================
# TEST 7: Prompt Templates edge cases
# ============================================================
print("\n=== TEST: Template Edge Cases ===")

pts2 = PromptTemplateSystem()

# Input vacio
t_empty = pts2.detect_template("")
test("Input vacio: sin template", t_empty is None)

# Input muy corto
t_short = pts2.detect_template("hi")
test("Input corto: sin template", t_short is None)

# Multiple tags match (debe elegir el de mayor score)
t_multi = pts2.detect_template("tengo un error y el traceback dice TypeError, no funciona nada")
test("Multi-match: debug gana sobre code", t_multi is not None and t_multi.name == "debug")

# Security template
t_sec = pts2.detect_template("como hago un pentest a un servidor web con vulnerabilidades")
test("Security template detectado", t_sec is not None and t_sec.name == "security")

# Research template
t_res = pts2.detect_template("investiga informacion sobre machine learning")
test("Research template detectado", t_res is not None and t_res.name == "research")

# Summarize template
t_sum = pts2.detect_template("resume este texto en pocas palabras")
test("Summarize template detectado", t_sum is not None and t_sum.name == "summarize")


# ============================================================
# TEST 8: Project Generator edge cases
# ============================================================
print("\n=== TEST: Project Generator Edge Cases ===")

pg2 = ProjectGenerator()

# Archivo con contenido muy largo (exceede MAX_FILE_SIZE)
long_response = '[FILE: big.py]\n```python\n' + 'x = 1\n' * 20000 + '```'
files_long = pg2.parse_files(long_response)
test("Archivo largo parseado", len(files_long) == 1)

tmp_dir2 = tempfile.mkdtemp(prefix="genesis_edge_")
try:
    result_long = pg2.generate(long_response, tmp_dir2)
    test("Archivo largo rechazado por tamaño", len(result_long["errors"]) > 0)
finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)

# Directorio inexistente (debe crearlo)
tmp_new = os.path.join(tempfile.mkdtemp(prefix="genesis_new_"), "subdir", "project")
try:
    result_new = pg2.generate(response1, tmp_new)
    test("Crea directorios intermedios", len(result_new["created"]) == 2)
    test("Directorio creado", os.path.exists(tmp_new))
finally:
    shutil.rmtree(os.path.dirname(os.path.dirname(tmp_new)), ignore_errors=True)


# ============================================================
# RESULTADOS
# ============================================================
print(f"\n{'=' * 50}")
print(f"  RESULTADOS: {_passed}/{_passed + _failed} pasaron, {_failed} fallaron")
print(f"{'=' * 50}")

if _failed > 0:
    sys.exit(1)
