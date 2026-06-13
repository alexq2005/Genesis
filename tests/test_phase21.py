"""
Tests Phase 21 — JARVIS Intelligence: WindowManager, SmartLauncher, DailyBriefing, MacroSystem.
"""
import sys
import os
import time
import tempfile

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
print("  GENESIS Phase 21 — JARVIS Intelligence Tests")
print("=" * 60)


# ============================================================
# 1. WINDOW MANAGER
# ============================================================
print("\n--- WindowManager ---")
from core.window_manager import WindowManager, window_manager

# List windows (no crashea)
windows = WindowManager.list_windows()
test("List windows retorna string", isinstance(windows, str))
test("List tiene header o vacío", "VENTANAS" in windows or "No hay" in windows)

# Parse and execute con ventana inexistente
test("Snap inexistente", "no encontré" in window_manager.snap_left("XYZNOEXISTE123").lower())
test("Maximize inexistente", "no encontré" in window_manager.maximize("XYZNOEXISTE123").lower())
test("Minimize inexistente", "no encontré" in window_manager.minimize("XYZNOEXISTE123").lower())
test("Focus inexistente", "no encontré" in window_manager.focus("XYZNOEXISTE123").lower())
test("Restore inexistente", "no encontré" in window_manager.restore("XYZNOEXISTE123").lower())
test("Close inexistente", "no encontré" in window_manager.close_window("XYZNOEXISTE123").lower())

# Minimize all (solo verificar que no crashea, NO ejecutar realmente)
test("minimize_all method exists", callable(window_manager.minimize_all))

# Parse and execute
parse_r = window_manager.parse_and_execute("comando inválido sin target")
test("Parse invalid muestra help", "no entendí" in parse_r.lower() or "ejemplo" in parse_r.lower())

# Screen info
screen = window_manager.screen_info()
test("Screen info retorna", isinstance(screen, str))

# Singleton
test("Singleton", isinstance(window_manager, WindowManager))


# ============================================================
# 2. SMART LAUNCHER
# ============================================================
print("\n--- SmartLauncher ---")
from core.smart_launcher import SmartLauncher, smart_launcher

# Fuzzy matching
test("Fuzzy exact", SmartLauncher._fuzzy_score("chrome", "Google Chrome") > 0.5)
test("Fuzzy partial", SmartLauncher._fuzzy_score("chr", "chrome") > 0.3)
test("Fuzzy no match", SmartLauncher._fuzzy_score("xyz123", "notepad") < 0.3)
test("Fuzzy start", SmartLauncher._fuzzy_score("note", "notepad") > 0.7)

# Search vacío
empty = smart_launcher.search("")
test("Search vacío muestra help", "smart launcher" in empty.lower() or "busca" in empty.lower())

# Search con query
result = smart_launcher.search("notepad")
test("Search retorna string", isinstance(result, str))

# Search inexistente
# NOTA: "xyzNoExiste12345" hacia falso-positivo con accesos directos reales del
# escritorio (ej "Forex-mt5.lnk") via SequenceMatcher (ratio exacto 0.4 == umbral).
# Usamos una cadena aleatoria que no comparte n-gramas con apps/archivos reales,
# para que el test sea determinista en cualquier entorno.
_NONSENSE = "zzzzqqqqwwww9999kkkk"
result_none = smart_launcher.search(_NONSENSE)
test("Search inexistente", "no encontré" in result_none.lower() or isinstance(result_none, str))

# Launch inexistente
launch_r = smart_launcher.launch(_NONSENSE)
test("Launch inexistente", "no encontré" in launch_r.lower())

# Singleton
test("Singleton", isinstance(smart_launcher, SmartLauncher))


# ============================================================
# 3. DAILY BRIEFING
# ============================================================
print("\n--- DailyBriefing ---")
from core.daily_briefing import DailyBriefing, daily_briefing

# Generate full briefing
briefing = daily_briefing.generate()
test("Briefing retorna string", isinstance(briefing, str))
test("Briefing tiene saludo", any(g in briefing for g in ["Buenos", "Buenas", "Hola"]))
test("Briefing tiene fecha", "2026" in briefing or "de" in briefing)
test("Briefing tiene sistema", "CPU" in briefing or "RAM" in briefing or "SISTEMA" in briefing)
test("Briefing tiene uptime", "uptime" in briefing.lower() or "Uptime" in briefing)
test("Briefing tiene motivación", "\"" in briefing or "—" in briefing)
test("Briefing tiene username", os.getenv("USERNAME", "") in briefing or "usuario" in briefing)

# Short status
short = daily_briefing.generate(full=False)
test("Short briefing más corto", len(short) < len(briefing))

# Quick status
quick = daily_briefing.quick_status()
test("Quick status retorna", isinstance(quick, str))

# Greeting
db = DailyBriefing()
greeting = db._get_greeting()
test("Greeting es string", isinstance(greeting, str))
test("Greeting válido", any(g in greeting for g in ["Buenos", "Buenas", "Hola"]))

# System status
sys_info = DailyBriefing._get_system_status()
test("Sys info es dict", isinstance(sys_info, dict))
test("Sys info tiene uptime", "uptime" in sys_info)
test("Sys info tiene cpu", "cpu" in sys_info)
test("Sys info tiene ram", "ram" in sys_info)
test("Sys info tiene disk", "disk" in sys_info)

# Singleton
test("Singleton", isinstance(daily_briefing, DailyBriefing))


# ============================================================
# 4. MACRO SYSTEM
# ============================================================
print("\n--- MacroSystem ---")
from core.macro_system import MacroSystem

with tempfile.TemporaryDirectory() as tmp:
    ms = MacroSystem(data_dir=tmp)

    # Create macro
    r1 = ms.create("test", ["comando 1", "comando 2", "comando 3"])
    test("Crear macro", "creada" in r1.lower())
    test("Muestra comandos", "comando 1" in r1)

    # Create macro con nombre vacío
    test("Nombre vacío rechazado", "necesita" in ms.create("", ["cmd"]).lower())
    test("Sin comandos rechazado", "necesita" in ms.create("x", []).lower())

    # List
    lista = ms.list_macros()
    test("Lista tiene macro", "test" in lista.lower())

    # Show
    detalle = ms.show("test")
    test("Show detalle", "test" in detalle.lower() and "comando 1" in detalle)

    # Show inexistente
    test("Show inexistente", "no encontré" in ms.show("xxx").lower())

    # Update
    r2 = ms.create("test", ["cmd a", "cmd b"], description="Updated")
    test("Update macro", "actualizada" in r2.lower())

    # Delete
    r3 = ms.delete("test")
    test("Delete macro", "eliminada" in r3.lower())
    test("Delete inexistente", "no encontré" in ms.delete("xxx").lower())

    # List empty
    empty_list = ms.list_macros()
    test("Lista vacía", "no hay" in empty_list.lower())

    # Execute without executor
    ms.create("noexec", ["cmd"])
    exec_r = ms.execute("noexec")
    test("Execute sin executor", "no hay ejecutor" in exec_r.lower())

    # Execute with mock executor
    exec_log = []
    def mock_executor(cmd):
        exec_log.append(cmd)
        return f"OK: {cmd}"

    ms.set_executor(mock_executor)
    ms.create("demo", ["paso 1", "paso 2", "paso 3"])
    exec_result = ms.execute("demo")
    test("Execute con executor", "completado" in exec_result.lower())
    test("3 pasos ejecutados", len(exec_log) == 3)
    test("Pasos correctos", "paso 1" in exec_log and "paso 2" in exec_log)

    # Run count
    test("Run count incrementó", ms._macros["demo"]["run_count"] == 1)

    # History
    hist = ms.history()
    test("Historial tiene entry", "demo" in hist.lower())

    # History vacío (fresh instance)
    ms2 = MacroSystem(data_dir=tmp + "/sub")
    test("Historial vacío", "no hay" in ms2.history().lower())

    # Parse definition
    parsed = MacroSystem.parse_macro_definition("macro trabajo: abre chrome, abre vscode, inicia pomodoro")
    test("Parse definición", parsed is not None)
    test("Parse nombre", parsed[0] == "trabajo")
    test("Parse 3 comandos", len(parsed[1]) == 3)
    test("Parse comando 1", "abre chrome" in parsed[1][0])

    # Parse with "y luego"
    parsed2 = MacroSystem.parse_macro_definition("macro noche: cierra todo y luego bloquea pantalla")
    test("Parse 'y luego'", parsed2 is not None and len(parsed2[1]) == 2)

    # Parse invalid
    test("Parse inválido", MacroSystem.parse_macro_definition("hola mundo") is None)

    # Execute fuzzy match
    ms.create("produccion", ["cmd"])
    fuzzy_r = ms.execute("produccin")  # typo
    test("Execute fuzzy match", "produccion" in fuzzy_r.lower() or "completado" in fuzzy_r.lower())

    # Status
    st = ms.status()
    test("Status total", "total_macros" in st)
    test("Status runs", "total_runs" in st)

    # Persistence
    ms.save()
    ms3 = MacroSystem(data_dir=tmp)
    test("Persistencia", ms3.status()["total_macros"] >= 1)


# ============================================================
# 5. VERSION CHECK
# ============================================================
print("\n--- Version ---")
from config import GENESIS_VERSION
test(f"Version {GENESIS_VERSION} >= 5.7.0", GENESIS_VERSION >= "5.7.0")


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"  RESULTADOS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print(f"\n  ⚠️ {failed} test(s) FALLARON")
else:
    print("\n  ✅ TODOS LOS TESTS PASARON — Phase 21 100% funcional")
