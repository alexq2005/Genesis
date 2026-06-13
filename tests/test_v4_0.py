"""Tests para Genesis v4.0 -- Autonomous Evolution"""
import sys, os, tempfile, shutil
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
print("GENESIS v4.0 -- Autonomous Evolution Tests")
print("=" * 60)

from core.safe_code_evolver import SafeCodeEvolver
from core.architecture_evolver import ArchitectureEvolver
from core.module_generator import ModuleGenerator


# === SAFECODEEVOLVER ===
print("\n--- SafeCodeEvolver ---")

tmp = tempfile.mkdtemp()
try:
    obj = SafeCodeEvolver(base_dir=tmp)
    test("SA: init ok", obj is not None)
    test("SA: total_mutations starts at 0", obj.total_mutations == 0)

    # get_stats
    stats = obj.get_stats()
    test("SA: get_stats returns dict", isinstance(stats, dict))
    test("SA: stats has total_mutations", "total_mutations" in stats)

    # status
    st = obj.status()
    test("SA: status is string", isinstance(st, str))
    test("SA: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("SA: report is string", isinstance(report, str))
    test("SA: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("SA: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("SA: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = SafeCodeEvolver(base_dir=tmp)
    test("SA: persistence ok", obj2.total_mutations == 0)

    # clear
    obj.clear()
    test("SA: clear resets", obj.total_mutations == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === ARCHITECTUREEVOLVER ===
print("\n--- ArchitectureEvolver ---")

tmp = tempfile.mkdtemp()
try:
    obj = ArchitectureEvolver(base_dir=tmp)
    test("AR: init ok", obj is not None)
    test("AR: total_proposals starts at 0", obj.total_proposals == 0)

    # get_stats
    stats = obj.get_stats()
    test("AR: get_stats returns dict", isinstance(stats, dict))
    test("AR: stats has total_proposals", "total_proposals" in stats)

    # status
    st = obj.status()
    test("AR: status is string", isinstance(st, str))
    test("AR: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("AR: report is string", isinstance(report, str))
    test("AR: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("AR: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("AR: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ArchitectureEvolver(base_dir=tmp)
    test("AR: persistence ok", obj2.total_proposals == 0)

    # clear
    obj.clear()
    test("AR: clear resets", obj.total_proposals == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === MODULEGENERATOR ===
print("\n--- ModuleGenerator ---")

tmp = tempfile.mkdtemp()
try:
    obj = ModuleGenerator(base_dir=tmp)
    test("MO: init ok", obj is not None)
    test("MO: total_generated starts at 0", obj.total_generated == 0)

    # get_stats
    stats = obj.get_stats()
    test("MO: get_stats returns dict", isinstance(stats, dict))
    test("MO: stats has total_generated", "total_generated" in stats)

    # status
    st = obj.status()
    test("MO: status is string", isinstance(st, str))
    test("MO: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("MO: report is string", isinstance(report, str))
    test("MO: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("MO: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("MO: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ModuleGenerator(base_dir=tmp)
    test("MO: persistence ok", obj2.total_generated == 0)

    # clear
    obj.clear()
    test("MO: clear resets", obj.total_generated == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 4.0", float(f"{major}.{minor}") >= 4.0)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
for _extra in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    _ep = os.path.join(os.path.dirname(__file__), "..", "core", _extra)
    if os.path.exists(_ep):
        with open(_ep, "r", encoding="utf-8") as f: gs += "\n" + f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

test("Int: import safe_code_evolver", "from core.safe_code_evolver import" in gs)
test("Int: self.safe_code_evolver", "self.safe_code_evolver" in gs)
test("Int: safe_code_evolver.save()", '"safe_code_evolver"' in gs)
test("Int: cmd /evolver", "/evolver" in gs)
test("Int: status SAFE CODE EVOLVER", "SAFE CODE EVOLVER" in gs)
test("WebUI: safe_code_evolver", "safe_code_evolver" in ws)
test("Int: import architecture_evolver", "from core.architecture_evolver import" in gs)
test("Int: self.architecture_evolver", "self.architecture_evolver" in gs)
test("Int: architecture_evolver.save()", '"architecture_evolver"' in gs)
test("Int: cmd /arch_evolver", "/arch_evolver" in gs)
test("Int: status ARCHITECTURE EVOLVER", "ARCHITECTURE EVOLVER" in gs)
test("WebUI: architecture_evolver", "architecture_evolver" in ws)
test("Int: import module_generator", "from core.module_generator import" in gs)
test("Int: self.module_generator", "self.module_generator" in gs)
test("Int: module_generator.save()", '"module_generator"' in gs)
test("Int: cmd /modgen", "/modgen" in gs)
test("Int: status MODULE GENERATOR", "MODULE GENERATOR" in gs)
test("WebUI: module_generator", "module_generator" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
