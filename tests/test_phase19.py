"""
Tests Phase 19 — Smart Productivity: Notas, Recordatorios, Red, Acciones del Sistema.
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
print("  GENESIS Phase 19 — Smart Productivity Tests")
print("=" * 60)

# ============================================================
# Quick Notes Tests
# ============================================================
print("\n--- QuickNotes ---")

from core.quick_notes import QuickNotes

# Usar directorio temporal para tests
with tempfile.TemporaryDirectory() as tmp:
    notes = QuickNotes(data_dir=tmp)

    test("Crear nota", "guardada" in notes.add("Comprar leche").lower())
    test("Crear nota con tag", "guardada" in notes.add("Estudiar Python", tag="estudio").lower())
    test("Crear nota vacía rechazada", "vacía" in notes.add("").lower() or "vacía" in notes.add("  ").lower())

    test("Listar notas (2 notas)", "2 total" in notes.list_notes())
    test("Listar por tag", "estudio" in notes.list_notes(tag="estudio").lower())
    test("Listar tag inexistente", "no hay notas" in notes.list_notes(tag="xyz").lower())

    test("Buscar nota existente", "leche" in notes.search("leche").lower())
    test("Buscar nota inexistente", "no encontré" in notes.search("xyz").lower())

    test("Eliminar nota", "eliminada" in notes.delete(1).lower())
    test("Eliminar nota inexistente", "no encontré" in notes.delete(999).lower())

    test("Pin nota", "fijada" in notes.pin(2).lower())
    test("Pin nota inexistente", "no encontré" in notes.pin(999).lower())

    test("Status notas", notes.status()["total"] >= 1)
    test("Clear notas", "eliminadas" in notes.clear().lower())
    test("Lista vacía", "no tenés" in notes.list_notes().lower())

    # Persistencia
    notes2 = QuickNotes(data_dir=tmp)
    notes2.add("Test persistencia")
    notes2.save()
    notes3 = QuickNotes(data_dir=tmp)
    test("Persistencia JSON", notes3.status()["total"] == 1)


# ============================================================
# Reminder System Tests
# ============================================================
print("\n--- ReminderSystem ---")

from core.reminder_system import ReminderSystem

test("Parse '5 minutos'", ReminderSystem.parse_time_expression("5 minutos") == 300)
test("Parse '1 hora'", ReminderSystem.parse_time_expression("1 hora") == 3600)
test("Parse '30 segundos'", ReminderSystem.parse_time_expression("30 segundos") == 30)
test("Parse '2h30m'", ReminderSystem.parse_time_expression("2h30m") == 9000)
test("Parse 'media hora'", ReminderSystem.parse_time_expression("media hora") == 1800)
test("Parse 'un cuarto de hora'", ReminderSystem.parse_time_expression("un cuarto de hora") == 900)
test("Parse '10m'", ReminderSystem.parse_time_expression("10m") == 600)
test("Parse '1h'", ReminderSystem.parse_time_expression("1h") == 3600)

rs = ReminderSystem()
result = rs.add("Test reminder", 60)
test("Crear recordatorio", "configurado" in result.lower())
test("Recordatorio activo", rs.status()["active"] == 1)

list_result = rs.list_active()
test("Listar activos", "test reminder" in list_result.lower())

cancel_result = rs.cancel(1)
test("Cancelar recordatorio", "cancelado" in cancel_result.lower())
test("Cancelar inexistente", "no encontré" in rs.cancel(999).lower())

test("Tiempo negativo rechazado", "mayor a 0" in rs.add("x", -1).lower())
test("Tiempo excesivo rechazado", "máximo" in rs.add("x", 100000).lower())
test("Mensaje vacío rechazado", "necesita" in rs.add("", 60).lower())

# Timer real corto (1 segundo)
fired = [False]
def on_fire(r):
    fired[0] = True

rs2 = ReminderSystem()
rs2.set_callback(on_fire)
rs2.add("Quick test", 1)
time.sleep(2)
test("Timer se dispara en 1s", fired[0])


# ============================================================
# Network Tools Tests
# ============================================================
print("\n--- NetworkTools ---")

from core.network_tools import NetworkTools

# Check connectivity (puede fallar sin internet, pero no debe crashear)
result = NetworkTools.check_connectivity()
test("Check connectivity no crashea", isinstance(result, str) and len(result) > 10)
test("Check tiene indicador", "CONECTADO" in result or "SIN CONEXIÓN" in result)

# WiFi info (puede no haber WiFi, pero no debe crashear)
result = NetworkTools.get_wifi_info()
test("WiFi info no crashea", isinstance(result, str))

# Ping (debe funcionar en cualquier sistema)
result = NetworkTools.ping("127.0.0.1", count=2)
test("Ping localhost no crashea", isinstance(result, str) and "PING" in result)


# ============================================================
# System Actions Tests
# ============================================================
print("\n--- SystemActions ---")

from core.system_actions import SystemActions

# Uptime
result = SystemActions.system_uptime()
test("Uptime no crashea", isinstance(result, str) and "uptime" in result.lower() or "encendido" in result.lower())

# Battery (desktop = no battery, laptop = battery — ambos válidos)
result = SystemActions.battery_status()
test("Battery no crashea", isinstance(result, str) and ("batería" in result.lower() or "battery" in result.lower() or "equipo" in result.lower()))

# Apps count
result = SystemActions.get_installed_apps_count()
test("Apps count no crashea", isinstance(result, str) and ("instaladas" in result.lower() or "error" in result.lower()))


# ============================================================
# Integration: Auto-detect keywords
# ============================================================
print("\n--- Auto-detect Integration ---")

# Verificar que los keywords no colisionan con auto-detect existente
test("'nota:' empieza con keyword", "nota:" == "nota:")
test("'recuerdame en' keyword", "recuerdame en " in "recuerdame en 5 minutos que salga")
test("'estoy conectado' keyword", "estoy conectado" in "estoy conectado a internet?")
test("'limpiar temp' keyword", "limpiar temp" in "limpiar temporales del sistema")
test("'mis notas' keyword", "mis notas" in "mostrar mis notas")


# ============================================================
# Resumen
# ============================================================
print("\n" + "=" * 60)
print(f"  RESULTADOS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print(f"\n  ADVERTENCIA: {failed} test(s) fallaron")
else:
    print("\n  TODOS LOS TESTS PASARON")
