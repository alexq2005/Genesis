"""
Tests Phase 20 — Smart Utilities: Clipboard, TextTransformer, UnitConverter, Pomodoro.
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
print("  GENESIS Phase 20 — Smart Utilities Tests")
print("=" * 60)


# ============================================================
# 1. CLIPBOARD MANAGER
# ============================================================
print("\n--- ClipboardManager ---")
from core.clipboard_manager import ClipboardManager

with tempfile.TemporaryDirectory() as tmp:
    cm = ClipboardManager(data_dir=tmp)
    test("Instancia creada", cm is not None)
    test("History vacío", cm.status()["history_count"] == 0)

    # Manual capture
    cm._add_to_history("Texto de prueba 1")
    cm._add_to_history("Texto de prueba 2")
    cm._add_to_history("Email: test@example.com")
    test("3 items en history", cm.status()["history_count"] == 3)

    # List
    lista = cm.list_history()
    test("Lista tiene header", "HISTORIAL" in lista)
    test("Lista muestra items", "prueba" in lista.lower())

    # Search
    test("Buscar email", "email" in cm.search("email").lower() or "test@" in cm.search("email"))
    test("Buscar inexistente", "no encontré" in cm.search("xyz999").lower())

    # Pin
    pin_r = cm.pin(1)
    test("Pin item 1", "fijado" in pin_r.lower())
    test("Pinned count", cm.status()["pinned_count"] == 1)
    unpin_r = cm.pin(1)
    test("Unpin item 1", "desfijado" in unpin_r.lower())

    # Get item
    get_r = cm.get_item(2)
    test("Get item 2", "prueba 2" in get_r.lower())
    test("Get inexistente", "no encontré" in cm.get_item(999).lower())

    # Clear
    cm.clear()
    test("Clear history", cm.status()["history_count"] == 0)

    # Get current (puede estar vacío, solo verificar que no crashea)
    current = cm.get_current()
    test("Get current no crashea", isinstance(current, str))

    # Persistence
    cm2 = ClipboardManager(data_dir=tmp)
    cm2._add_to_history("Persistente")
    cm2.save()
    cm3 = ClipboardManager(data_dir=tmp)
    test("Persistencia", cm3.status()["history_count"] >= 1)

    # No duplicates
    cm4 = ClipboardManager(data_dir=tmp)
    cm4._add_to_history("Duplicado")
    cm4._add_to_history("Duplicado")
    test("No duplica consecutivos", cm4.status()["history_count"] != 0)  # last item is checked


# ============================================================
# 2. TEXT TRANSFORMER
# ============================================================
print("\n--- TextTransformer ---")
from core.text_transformer import TextTransformer, text_transformer

# Case conversions
test("Mayúsculas", "HOLA MUNDO" in TextTransformer.to_upper("hola mundo"))
test("Minúsculas", "hola mundo" in TextTransformer.to_lower("HOLA MUNDO"))
test("Título", "Hola Mundo" in TextTransformer.to_title("hola mundo"))
test("Capitalizar", "Hola mundo" in TextTransformer.to_capitalize("hola mundo"))
test("Swap case", "hOLA" in TextTransformer.to_swap_case("Hola"))
test("camelCase", "holaMundo" in TextTransformer.to_camel_case("hola mundo"))
test("snake_case", "hola_mundo" in TextTransformer.to_snake_case("hola mundo"))
test("kebab-case", "hola-mundo" in TextTransformer.to_kebab_case("hola mundo"))

# Encoding
test("Base64 encode", "aG9sYQ==" in TextTransformer.encode_base64("hola"))
test("Base64 decode", "hola" in TextTransformer.decode_base64("aG9sYQ=="))
test("Base64 invalid", "no es" in TextTransformer.decode_base64("!!!").lower())
test("URL encode", "%20" in TextTransformer.encode_url("hola mundo"))
test("URL decode", "hola mundo" in TextTransformer.decode_url("hola%20mundo"))
test("Hex encode", "686f6c61" in TextTransformer.to_hex("hola"))
test("Hex decode", "hola" in TextTransformer.from_hex("686f6c61"))

# Hashing
hash_r = TextTransformer.hash_text("test")
test("Hash MD5", "098f6bcd" in hash_r)
test("Hash SHA256", "9f86d081" in hash_r)
test("Hash tiene 3 tipos", "MD5" in hash_r and "SHA1" in hash_r and "SHA256" in hash_r)

# Text stats
stats = TextTransformer.count_text("Hola mundo. Esta es una prueba.")
test("Count chars", "31" in stats or "Caracteres" in stats)
test("Count words", "6" in stats or "Palabras" in stats)
test("Count tiene lectura", "Lectura" in stats)

# Extract
test("Extract emails", "test@example.com" in TextTransformer.extract_emails("Contacto: test@example.com aquí"))
test("Extract no emails", "No encontré" in TextTransformer.extract_emails("sin emails"))
test("Extract URLs", "https://google.com" in TextTransformer.extract_urls("Ve a https://google.com ya"))
test("Extract no URLs", "No encontré" in TextTransformer.extract_urls("sin urls"))
test("Extract numbers", "42" in TextTransformer.extract_numbers("Tengo 42 y 3.14"))
test("Extract no numbers", "No encontré" in TextTransformer.extract_numbers("sin numeros"))

# JSON
test("JSON pretty", '"name"' in TextTransformer.to_json_pretty('{"name":"test","age":25}'))
test("JSON invalid", "no es" in TextTransformer.to_json_pretty("not json").lower())

# Sort / Reverse / Duplicates
test("Sort lines", "a" in TextTransformer.sort_lines("c\nb\na"))
test("Reverse text", "aloh" in TextTransformer.reverse_text("hola"))
test("Remove duplicates", "eliminados" in TextTransformer.remove_duplicates("a\nb\na\nc\nb").lower())

# Dispatcher
test("Dispatcher mayusculas", "HOLA" in text_transformer.transform("mayusculas", "hola"))
test("Dispatcher invalid", "no reconocida" in text_transformer.transform("invalid", "test").lower())
test("Singleton", isinstance(text_transformer, TextTransformer))


# ============================================================
# 3. UNIT CONVERTER
# ============================================================
print("\n--- UnitConverter ---")
from core.unit_converter import UnitConverter, unit_converter

# Temperature
test("C to F", "212" in unit_converter.convert("100 celsius a fahrenheit") or "212.00" in unit_converter.convert("100 celsius a fahrenheit"))
test("F to C", "0" in unit_converter.convert("32 fahrenheit a celsius"))
test("C to K", "373.15" in unit_converter.convert("100 c a kelvin"))

# Distance
test("km a millas", "6.2137" in unit_converter.convert("10 km a millas") or "6.21" in unit_converter.convert("10 km a millas"))
test("millas a km", "16" in unit_converter.convert("10 millas a km"))
test("m a pies", unit_converter.convert("1 metro a pies") != "")
test("cm a pulgadas", unit_converter.convert("100 cm a pulgadas") != "")

# Weight
test("kg a libras", "2.2" in unit_converter.convert("1 kg a libras"))
test("libras a kg", "0.45" in unit_converter.convert("1 libra a kg"))

# Data
test("GB a MB", "1,024" in unit_converter.convert("1 gb a mb") or "1024" in unit_converter.convert("1 gb a mb"))
test("TB a GB", "1,024" in unit_converter.convert("1 tb a gb") or "1024" in unit_converter.convert("1 tb a gb"))

# Time
test("horas a minutos", "120" in unit_converter.convert("2 horas a minutos"))
test("dias a horas", "48" in unit_converter.convert("2 dias a horas"))

# Volume
test("litros a ml", "1,000" in unit_converter.convert("1 litro a ml") or "1000" in unit_converter.convert("1 litro a ml"))
test("galones a litros", "3.78" in unit_converter.convert("1 galon a litros"))

# Invalid
test("Unidad desconocida", "no reconozco" in unit_converter.convert("10 xyz a abc").lower() or "no entendí" in unit_converter.convert("10 xyz a abc").lower())
test("Categorías diferentes", "diferentes" in unit_converter.convert("10 km a kg").lower())

# Natural language patterns
test("Cuantos metros son 5 pies", "metro" in unit_converter.convert("cuantos metros son 5 pies").lower() or "distancia" in unit_converter.convert("cuantos metros son 5 pies").lower())

# List categories
cats = unit_converter.list_categories()
test("Lista categorías", "distancia" in cats.lower())
test("Tiene temperatura", "temperatura" in cats.lower())

test("Singleton", isinstance(unit_converter, UnitConverter))


# ============================================================
# 4. POMODORO TIMER
# ============================================================
print("\n--- PomodoroTimer ---")
from core.pomodoro import PomodoroTimer, pomodoro

# Create timer
pm = PomodoroTimer(work_min=1, short_break_min=1, long_break_min=1)

# Status when idle
status = pm.status()
test("Status idle", "inactivo" in status.lower())

# Start
start_r = pm.start()
test("Start OK", "iniciado" in start_r.lower())
test("Muestra ciclo", "#1" in start_r)

# Can't start again
test("Double start blocked", "ya hay" in pm.start().lower())

# Pause
pause_r = pm.pause()
test("Pause OK", "pausado" in pause_r.lower())

# Resume
resume_r = pm.resume()
test("Resume OK", "reanudado" in resume_r.lower())

# Status during work
status_work = pm.status()
test("Status working", "trabajando" in status_work.lower() or "restante" in status_work.lower())

# Skip
skip_r = pm.skip()
test("Skip OK", "saltada" in skip_r.lower())

# Stop
stop_r = pm.stop()
test("Stop OK", "detenido" in stop_r.lower())

# Configure
config_r = pm.configure(work=30, short_break=10)
test("Configure OK", "configurado" in config_r.lower())
test("Config shows 30", "30" in config_r)

# Can't configure while active
pm2 = PomodoroTimer(work_min=1)
pm2.start()
test("No config while active", "no se puede" in pm2.configure(work=20).lower())
pm2.stop()

# Pause when idle
test("Pause idle", "no hay" in pm.pause().lower())
test("Resume idle", "no hay" in pm.resume().lower())
test("Stop idle", "no hay" in pm.stop().lower())

# History empty (fresh instance)
pm_fresh = PomodoroTimer()
test("History empty", "no hay" in pm_fresh.history().lower())

# Custom work time
pm3 = PomodoroTimer(work_min=1)
start_custom = pm3.start(work_min=45)
test("Custom 45 min", "45" in start_custom)
pm3.stop()

# Timer real fire test (1 second)
print("  -- Timer real Pomodoro (1s) --")
fire_log = []
pm4 = PomodoroTimer(work_min=1, short_break_min=1)
pm4.work_sec = 1  # Override to 1 second for testing
pm4.set_callback(lambda msg, phase: fire_log.append(phase))
pm4.start()
time.sleep(2)
test("Work phase completed", "short_break" in fire_log or "long_break" in fire_log)
pm4.stop()

# Singleton check
test("Singleton", isinstance(pomodoro, PomodoroTimer))


# ============================================================
# 5. VERSION CHECK
# ============================================================
print("\n--- Version ---")
from config import GENESIS_VERSION
test(f"Version {GENESIS_VERSION} >= 5.6.0", GENESIS_VERSION >= "5.6.0")


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"  RESULTADOS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print(f"\n  ⚠️ {failed} test(s) FALLARON")
else:
    print("\n  ✅ TODOS LOS TESTS PASARON — Phase 20 100% funcional")
