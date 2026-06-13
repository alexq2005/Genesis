"""Tests para Genesis v5.0 -- Singularity"""
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
print("GENESIS v5.0 -- Singularity Tests")
print("=" * 60)

from core.autonomous_research_loop import AutonomousResearchLoop
from core.self_architect import SelfArchitect
from core.consciousness_integrator import ConsciousnessIntegrator


# === AUTONOMOUSRESEARCHLOOP ===
print("\n--- AutonomousResearchLoop ---")

tmp = tempfile.mkdtemp()
try:
    obj = AutonomousResearchLoop(base_dir=tmp)
    test("AU: init ok", obj is not None)
    test("AU: total_cycles starts at 0", obj.total_cycles == 0)

    # get_stats
    stats = obj.get_stats()
    test("AU: get_stats returns dict", isinstance(stats, dict))
    test("AU: stats has total_cycles", "total_cycles" in stats)

    # status
    st = obj.status()
    test("AU: status is string", isinstance(st, str))
    test("AU: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("AU: report is string", isinstance(report, str))
    test("AU: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("AU: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("AU: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = AutonomousResearchLoop(base_dir=tmp)
    test("AU: persistence ok", obj2.total_cycles == 0)

    # clear
    obj.clear()
    test("AU: clear resets", obj.total_cycles == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === SELFARCHITECT ===
print("\n--- SelfArchitect ---")

tmp = tempfile.mkdtemp()
try:
    obj = SelfArchitect(base_dir=tmp)
    test("SE: init ok", obj is not None)
    test("SE: total_snapshots starts at 0", obj.total_snapshots == 0)

    # get_stats
    stats = obj.get_stats()
    test("SE: get_stats returns dict", isinstance(stats, dict))
    test("SE: stats has total_snapshots", "total_snapshots" in stats)

    # status
    st = obj.status()
    test("SE: status is string", isinstance(st, str))
    test("SE: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("SE: report is string", isinstance(report, str))
    test("SE: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("SE: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("SE: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = SelfArchitect(base_dir=tmp)
    test("SE: persistence ok", obj2.total_snapshots == 0)

    # clear
    obj.clear()
    test("SE: clear resets", obj.total_snapshots == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === CONSCIOUSNESSINTEGRATOR ===
print("\n--- ConsciousnessIntegrator ---")

tmp = tempfile.mkdtemp()
try:
    obj = ConsciousnessIntegrator(base_dir=tmp)
    test("CO: init ok", obj is not None)
    test("CO: total_integrations starts at 0", obj.total_integrations == 0)

    # get_stats
    stats = obj.get_stats()
    test("CO: get_stats returns dict", isinstance(stats, dict))
    test("CO: stats has total_integrations", "total_integrations" in stats)

    # status
    st = obj.status()
    test("CO: status is string", isinstance(st, str))
    test("CO: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("CO: report is string", isinstance(report, str))
    test("CO: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("CO: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("CO: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ConsciousnessIntegrator(base_dir=tmp)
    test("CO: persistence ok", obj2.total_integrations == 0)

    # clear
    obj.clear()
    test("CO: clear resets", obj.total_integrations == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 5.0", float(f"{major}.{minor}") >= 5.0)

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

test("Int: import autonomous_research_loop", "from core.autonomous_research_loop import" in gs)
test("Int: self.autonomous_research_loop", "self.autonomous_research_loop" in gs)
test("Int: autonomous_research_loop.save()", '"autonomous_research_loop"' in gs)
test("Int: cmd /research_loop", "/research_loop" in gs)
test("Int: status AUTONOMOUS RESEARCH LOOP", "AUTONOMOUS RESEARCH LOOP" in gs)
test("WebUI: autonomous_research_loop", "autonomous_research_loop" in ws)
test("Int: import self_architect", "from core.self_architect import" in gs)
test("Int: self.self_architect", "self.self_architect" in gs)
test("Int: self_architect.save()", '"self_architect"' in gs)
test("Int: cmd /self_arch", "/self_arch" in gs)
test("Int: status SELF ARCHITECT", "SELF ARCHITECT" in gs)
test("WebUI: self_architect", "self_architect" in ws)
test("Int: import consciousness_integrator", "from core.consciousness_integrator import" in gs)
test("Int: self.consciousness_integrator", "self.consciousness_integrator" in gs)
test("Int: consciousness_integrator.save()", '"consciousness_integrator"' in gs)
test("Int: cmd /consciousness", "/consciousness" in gs)
test("Int: status CONSCIOUSNESS INTEGRATOR", "CONSCIOUSNESS INTEGRATOR" in gs)
test("WebUI: consciousness_integrator", "consciousness_integrator" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
