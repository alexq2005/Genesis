"""
GENESIS — Tests v3.0: capacidades nuevas (sesión 2026-06-12)
Cubre: índices (programas/carpetas), email (validación/config), mutación
quirúrgica (_tolerant_replace), parser de hora del despertador, helpers de música.
Todo determinístico y SIN red (no envía mails ni toca YouTube).
"""
import sys
import os
import tempfile
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
errors = []


def test(name, condition):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  [FAIL] {name}")


print("=" * 60)
print("GENESIS v3.0 — Test Suite: Capacidades nuevas")
print("=" * 60)

# ============================================================
# _tolerant_replace (motor de auto-mejora / mutación quirúrgica)
# ============================================================
print("\n--- _tolerant_replace (mutación quirúrgica) ---")
from core.genesis_commands import GenesisCommandsMixin as GC

_code = "class A:\n    def foo(self):\n        x = 1\n        return x\n"
# match exacto
_r1 = GC._tolerant_replace(_code, "        x = 1", "        x = 2")
test("replace exacto", _r1 is not None and "x = 2" in _r1)
# match tolerante a sangría (old con 4 espacios vs file con 8) + re-indent anidado
_old = "def foo(self):\n    x = 1\n    return x"
_new = "def foo(self):\n    x = 1\n    if x < 0:\n        x = 0\n    return x"
_r2 = GC._tolerant_replace(_code, _old, _new)
test("replace tolerante encuentra el bloque", _r2 is not None)
if _r2:
    import ast
    try:
        ast.parse(_r2)
        test("resultado re-indentado es Python VÁLIDO", True)
    except SyntaxError:
        test("resultado re-indentado es Python VÁLIDO", False)
    test("preserva anidación (if dentro)", "            x = 0" in _r2)
# no-match → None
test("sin match → None", GC._tolerant_replace(_code, "no existe esto", "x") is None)
# ambiguo → None
_amb = "a = 1\nb = 2\na = 1\n"
test("ambiguo (2 ocurrencias) → None", GC._tolerant_replace(_amb, "a = 1", "a = 9") is None)

# ============================================================
# Parser de hora del despertador
# ============================================================
print("\n--- _parse_clock_time (despertador) ---")
from core.genesis_tools import GenesisToolsMixin as GT

test("'a las 7' devuelve segundos > 0", (GT._parse_clock_time("despertame a las 7") or 0) > 0)
test("'7:30' parsea", (GT._parse_clock_time("a las 7:30") or 0) > 0)
test("hora inválida (a las 99) → None", GT._parse_clock_time("a las 99") is None)
test("sin hora → None", GT._parse_clock_time("hola que tal") is None)
_pm = GT._parse_clock_time("a las 7 de la tarde")
_am = GT._parse_clock_time("a las 7 de la mañana")
test("pm != am (conversión horaria)", _pm is not None and _am is not None and _pm != _am)

# ============================================================
# Email — validación y config (SIN enviar)
# ============================================================
print("\n--- email_sender (sin red) ---")
from core import email_sender as ES

test("valid_email acepta correcto", ES.valid_email("alexq2005@gmail.com"))
test("valid_email rechaza basura", not ES.valid_email("no-es-mail"))
test("send_email a dirección inválida no explota", ES.send_email("xxx", "s", "b").get("ok") is False)
test("is_configured devuelve bool", isinstance(ES.is_configured(), bool))

print("\n--- email_reader (sin red) ---")
from core import email_reader as ER

test("is_configured devuelve bool", isinstance(ER.is_configured(), bool))
test("_decode maneja None", ER._decode(None) == "")
test("_decode texto plano", ER._decode("hola") == "hola")

# ============================================================
# Índice de carpetas — scan/find/prune con dir temporal
# ============================================================
print("\n--- folder_index (temp dir, determinístico) ---")
from core import folder_index as FI

_tmp = tempfile.mkdtemp(prefix="gx_fi_")
try:
    os.makedirs(os.path.join(_tmp, "carpeta_prueba_xyz"))
    os.makedirs(os.path.join(_tmp, "otra"))
    _orig_roots = FI._ROOTS
    _orig_cache = FI._CACHE
    FI._ROOTS = [_tmp]
    FI._CACHE = os.path.join(_tmp, "_idx.json")
    FI._IDX = None
    n = FI.refresh()
    test("scan indexa carpetas del temp", n >= 2)
    hits = FI.find("carpeta_prueba_xyz")
    test("find encuentra carpeta exacta", len(hits) == 1)
    # prune-on-access: borrar y volver a buscar
    shutil.rmtree(os.path.join(_tmp, "carpeta_prueba_xyz"))
    hits2 = FI.find("carpeta_prueba_xyz")
    test("prune-on-access: borrada → no aparece", hits2 == [])
    FI._ROOTS = _orig_roots
    FI._CACHE = _orig_cache
    FI._IDX = None
finally:
    shutil.rmtree(_tmp, ignore_errors=True)

# ============================================================
# Índice de programas — API no explota
# ============================================================
print("\n--- program_index ---")
from core import program_index as PI

test("count() devuelve int", isinstance(PI.count(), int))
test("find('noexiste_zzz') → None", PI.find("noexiste_zzz_qwerty") is None)

# ============================================================
# music_player — helpers sin red
# ============================================================
print("\n--- music_player (helpers sin red) ---")
from core import music_player as MP

test("ytmusic_available devuelve bool", isinstance(MP.ytmusic_available(), bool))
test("cookies_available devuelve bool", isinstance(MP.cookies_available(), bool))
test("_cdp_ytm_target no explota sin CDP", MP._cdp_ytm_target() is None or isinstance(MP._cdp_ytm_target(), dict))

# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTADOS: {passed}/{total} tests pasaron")
if errors:
    print(f"\nTests fallidos ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("¡Todos los tests pasaron!")
    sys.exit(0)
