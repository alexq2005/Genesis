"""
Tests Phase 23 — System Mastery: ProjectScaffolder, CodeSnippets, TemplateEngine, SystemProfiler.
"""
import sys
import os
import tempfile
import shutil

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


print("=" * 60)
print("  GENESIS Phase 23 — System Mastery Tests")
print("=" * 60)


# ============================================================
# 1. PROJECT SCAFFOLDER
# ============================================================
print("\n--- ProjectScaffolder ---")
from core.project_scaffolder import ProjectScaffolder, project_scaffolder

with tempfile.TemporaryDirectory() as tmp:
    ps = ProjectScaffolder()

    # Templates disponibles
    test("Templates incluyen python", "python" in ps.TEMPLATES)
    test("Templates incluyen flask", "flask" in ps.TEMPLATES)
    test("Templates incluyen fastapi", "fastapi" in ps.TEMPLATES)
    test("Templates incluyen node", "node" in ps.TEMPLATES)
    test("Templates incluyen html", "html" in ps.TEMPLATES)
    test("Templates incluyen react", "react" in ps.TEMPLATES)

    # List templates
    tlist = ps.list_templates()
    test("List templates retorna", isinstance(tlist, str))
    test("List tiene python", "python" in tlist.lower())

    # Create proyecto python
    r1 = ps.create("test_project", "python", path=tmp)
    test("Crear proyecto", "creado" in r1.lower())
    test("Proyecto tiene main.py", os.path.isfile(os.path.join(tmp, "test_project", "main.py")))
    test("Proyecto tiene requirements", os.path.isfile(os.path.join(tmp, "test_project", "requirements.txt")))
    test("Proyecto tiene .gitignore", os.path.isfile(os.path.join(tmp, "test_project", ".gitignore")))
    test("Proyecto tiene tests/", os.path.isdir(os.path.join(tmp, "test_project", "tests")))
    test("Proyecto tiene src/", os.path.isdir(os.path.join(tmp, "test_project", "src")))

    # Verificar contenido tiene el nombre del proyecto
    with open(os.path.join(tmp, "test_project", "main.py"), "r") as f:
        content = f.read()
    test("Main tiene nombre", "test_project" in content)

    # Create duplicado
    r2 = ps.create("test_project", "python", path=tmp)
    test("Duplicado rechazado", "ya existe" in r2.lower())

    # Create con template inexistente
    r3 = ps.create("bad", "xyztemplate", path=tmp)
    test("Template inexistente", "no existe" in r3.lower() or "disponibles" in r3.lower())

    # Create sin nombre
    r4 = ps.create("", "python", path=tmp)
    test("Sin nombre rechazado", "necesita" in r4.lower())

    # Create flask
    r5 = ps.create("flask_app", "flask", path=tmp)
    test("Crear flask", "creado" in r5.lower())
    test("Flask tiene app.py", os.path.isfile(os.path.join(tmp, "flask_app", "app.py")))
    test("Flask tiene templates/", os.path.isdir(os.path.join(tmp, "flask_app", "templates")))

    # Create node
    r6 = ps.create("node_app", "node", path=tmp)
    test("Crear node", "creado" in r6.lower())
    test("Node tiene package.json", os.path.isfile(os.path.join(tmp, "node_app", "package.json")))

    # Create HTML
    r7 = ps.create("web_page", "html", path=tmp)
    test("Crear html", "creado" in r7.lower())
    test("HTML tiene index.html", os.path.isfile(os.path.join(tmp, "web_page", "index.html")))
    test("HTML tiene css/", os.path.isdir(os.path.join(tmp, "web_page", "css")))

    # History
    hist = ps.history()
    test("History tiene proyectos", "test_project" in hist.lower() or "flask_app" in hist.lower())

    # Status
    st = ps.status()
    test("Status templates_count", "templates_count" in st)
    test("Status projects_generated", st["projects_generated"] >= 4)

    # Singleton
    test("Singleton", isinstance(project_scaffolder, ProjectScaffolder))


# ============================================================
# 2. CODE SNIPPETS
# ============================================================
print("\n--- CodeSnippets ---")
from core.code_snippets import CodeSnippets, code_snippets

with tempfile.TemporaryDirectory() as tmp:
    cs = CodeSnippets(data_dir=tmp)

    # Add snippet
    r1 = cs.add("hello", 'print("Hola Mundo")', "python", ["util", "basic"])
    test("Add snippet", "guardado" in r1.lower())

    # Add duplicado (actualiza)
    r2 = cs.add("hello", 'print("Hola!")', "python")
    test("Update snippet", "actualizado" in r2.lower())

    # Add sin nombre
    test("Sin nombre", "necesita" in cs.add("", "code").lower())
    test("Sin código", "necesita" in cs.add("x", "").lower())

    # Get
    r3 = cs.get("hello")
    test("Get snippet", "hello" in r3.lower())
    test("Get tiene código", "hola" in r3.lower())

    # Get inexistente
    r4 = cs.get("xyzNoExiste")
    test("Get inexistente", "no encontré" in r4.lower())

    # Add más snippets
    cs.add("fetch_api", 'const r = await fetch(url);', "javascript", ["api", "fetch"])
    cs.add("sql_select", 'SELECT * FROM users WHERE id = ?;', "sql", ["database"])
    cs.add("css_center", 'display: flex; justify-content: center; align-items: center;', "css", ["layout"])

    # Search por nombre
    r5 = cs.search("hello")
    test("Search nombre", "hello" in r5.lower())

    # Search por tag
    r6 = cs.search("api")
    test("Search tag", "fetch" in r6.lower())

    # Search por contenido
    r7 = cs.search("SELECT")
    test("Search contenido", "sql" in r7.lower())

    # Search por lenguaje
    r8 = cs.search("css")
    test("Search lenguaje", "css" in r8.lower())

    # Search vacío
    r9 = cs.search("xyzNoExiste123")
    test("Search sin resultados", "no encontré" in r9.lower())

    # List
    lista = cs.list_snippets()
    test("List tiene snippets", "hello" in lista.lower())
    test("List agrupado por lenguaje", "python" in lista.lower() or "PYTHON" in lista)

    # List by tag
    r10 = cs.list_by_tag("api")
    test("List by tag", "fetch" in r10.lower())

    r11 = cs.list_by_tag("inexistente")
    test("List by tag vacío", "no hay" in r11.lower())

    # Remove
    r12 = cs.remove("css_center")
    test("Remove snippet", "eliminado" in r12.lower())

    r13 = cs.remove("xyzNoExiste")
    test("Remove inexistente", "no encontré" in r13.lower())

    # Uses counter
    cs.get("hello")  # segundo uso
    test("Uses incrementa", cs._snippets["hello"]["uses"] >= 2)

    # Status
    st = cs.status()
    test("Status total_snippets", "total_snippets" in st)
    test("Status languages", "languages" in st)
    test("Status total_uses", "total_uses" in st)

    # Persistencia
    cs.save()
    cs2 = CodeSnippets(data_dir=tmp)
    test("Persistencia", cs2.status()["total_snippets"] >= 3)

    # List vacío
    cs3 = CodeSnippets(data_dir=tmp + "/sub")
    test("List vacío", "no hay" in cs3.list_snippets().lower())

    # Singleton
    test("Singleton", isinstance(code_snippets, CodeSnippets))


# ============================================================
# 3. TEMPLATE ENGINE
# ============================================================
print("\n--- TemplateEngine ---")
from core.template_engine import TemplateEngine, template_engine

with tempfile.TemporaryDirectory() as tmp:
    te = TemplateEngine(data_dir=tmp)

    # Builtin templates
    test("Builtin email_formal", "email_formal" in te.BUILTIN)
    test("Builtin bug_report", "bug_report" in te.BUILTIN)
    test("Builtin acta_reunion", "acta_reunion" in te.BUILTIN)
    test("Builtin changelog", "changelog" in te.BUILTIN)

    # List templates
    tlist = te.list_templates()
    test("List tiene predefinidos", "predefinidos" in tlist.lower())
    test("List tiene email", "email" in tlist.lower())

    # Preview builtin
    r1 = te.preview("email_formal")
    test("Preview builtin", "template" in r1.lower())
    test("Preview tiene variables", "destinatario" in r1.lower())

    # Apply builtin sin valores
    r2 = te.apply("email_formal")
    test("Apply sin valores", "aplicado" in r2.lower())
    test("Apply tiene placeholder", "{destinatario}" in r2 or "destinatario" in r2)

    # Apply con valores
    r3 = te.apply("email_formal", {"destinatario": "Juan", "cuerpo": "Test", "remitente": "Ana"})
    test("Apply con valores", "juan" in r3.lower())
    test("Apply reemplaza", "ana" in r3.lower())

    # Apply auto-fill fecha
    r4 = te.apply("changelog", {"version": "1.0", "agregado": "test", "cambiado": "-", "corregido": "-"})
    test("Apply auto-fill fecha", "2026" in r4 or "202" in r4)

    # Create custom template
    r5 = te.create("saludo", "Hola {nombre}, bienvenido a {proyecto}.", "Saludo personalizado")
    test("Create custom", "creado" in r5.lower())
    test("Create detecta variables", "nombre" in r5 and "proyecto" in r5)

    # Apply custom
    r6 = te.apply("saludo", {"nombre": "Carlos", "proyecto": "Genesis"})
    test("Apply custom", "carlos" in r6.lower())

    # Update custom
    r7 = te.create("saludo", "Hey {nombre}!", "Saludo corto")
    test("Update custom", "actualizado" in r7.lower())

    # Remove custom
    r8 = te.remove("saludo")
    test("Remove custom", "eliminado" in r8.lower())

    # Remove builtin
    r9 = te.remove("email_formal")
    test("Remove builtin bloqueado", "predefinido" in r9.lower())

    # Remove inexistente
    r10 = te.remove("xyzNoExiste")
    test("Remove inexistente", "no encontré" in r10.lower())

    # Preview inexistente
    r11 = te.preview("xyzNoExiste")
    test("Preview inexistente", "no encontré" in r11.lower())

    # Apply inexistente
    r12 = te.apply("xyzNoExiste")
    test("Apply inexistente", "no encontré" in r12.lower())

    # Create sin nombre
    test("Create sin nombre", "necesita" in te.create("", "content").lower())
    test("Create sin contenido", "necesita" in te.create("x", "").lower())

    # Status
    st = te.status()
    test("Status builtin_templates", "builtin_templates" in st)
    test("Status custom_templates", "custom_templates" in st)
    test("Status total_templates", st["total_templates"] >= len(te.BUILTIN))

    # Persistencia
    te.create("persistente", "Contenido {var}")
    te.save()
    te2 = TemplateEngine(data_dir=tmp)
    test("Persistencia", te2.status()["custom_templates"] >= 1)

    # Singleton
    test("Singleton", isinstance(template_engine, TemplateEngine))


# ============================================================
# 4. SYSTEM PROFILER
# ============================================================
print("\n--- SystemProfiler ---")
from core.system_profiler import SystemProfiler, system_profiler

sp = SystemProfiler()

# Installed software
r1 = sp.installed_software(limit=5)
test("Software retorna string", isinstance(r1, str))
test("Software tiene contenido", len(r1) > 10)

# Startup programs
r2 = sp.startup_programs()
test("Startup retorna string", isinstance(r2, str))

# Environment vars
r3 = sp.environment_vars()
test("Env vars retorna", isinstance(r3, str))
test("Env vars tiene PATH", "PATH" in r3 or "path" in r3.lower())

# Env vars filtrado
r4 = sp.environment_vars("PYTHON")
test("Env vars filtrado", isinstance(r4, str))

# Env vars inexistente
r5 = sp.environment_vars("XYZNOEXISTE123")
test("Env vars sin match", "no se encontraron" in r5.lower())

# Disk usage
with tempfile.TemporaryDirectory() as tmp:
    # Crear archivos de prueba
    with open(os.path.join(tmp, "big.txt"), "w") as f:
        f.write("x" * 10000)
    with open(os.path.join(tmp, "small.txt"), "w") as f:
        f.write("y" * 100)
    os.makedirs(os.path.join(tmp, "subdir"))
    with open(os.path.join(tmp, "subdir", "inner.txt"), "w") as f:
        f.write("z" * 5000)

    r6 = sp.disk_usage(path=tmp)
    test("Disk usage retorna", isinstance(r6, str))
    test("Disk usage tiene big", "big" in r6.lower())
    test("Disk usage tiene barra", "█" in r6)

# Disk usage dir inexistente
r7 = sp.disk_usage("C:\\NoExisteDir12345")
test("Disk usage dir inexistente", "no existe" in r7.lower())

# Network connections
r8 = sp.network_connections(limit=5)
test("Network retorna", isinstance(r8, str))

# Services
r9 = sp.services()
test("Services retorna", isinstance(r9, str))

# Format size
test("Format bytes", "B" in sp._format_size(500))
test("Format KB", "KB" in sp._format_size(5000))
test("Format MB", "MB" in sp._format_size(5000000))
test("Format GB", "GB" in sp._format_size(5000000000))

# Status
st = sp.status()
test("Status available_reports", "available_reports" in st)
test("Status tiene 7 reportes", len(st["available_reports"]) == 7)

# Singleton
test("Singleton", isinstance(system_profiler, SystemProfiler))


# ============================================================
# 5. VERSION CHECK
# ============================================================
print("\n--- Version ---")
from config import GENESIS_VERSION
test(f"Version {GENESIS_VERSION} >= 5.9.0", GENESIS_VERSION >= "5.9.0")


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"  RESULTADOS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print(f"\n  ⚠️ {failed} test(s) FALLARON")
else:
    print("\n  ✅ TODOS LOS TESTS PASARON — Phase 23 100% funcional")
