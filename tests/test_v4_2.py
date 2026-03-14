"""Tests para Genesis v4.2 -- Ethical Framework"""
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
print("GENESIS v4.2 -- Ethical Framework Tests")
print("=" * 60)

from core.ethical_reasoner import EthicalReasoner
from core.bias_detector import BiasDetector
from core.transparency_engine import TransparencyEngine


# === ETHICALREASONER ===
print("\n--- EthicalReasoner ---")

tmp = tempfile.mkdtemp()
try:
    obj = EthicalReasoner(base_dir=tmp)
    test("ET: init ok", obj is not None)
    test("ET: total_evaluations starts at 0", obj.total_evaluations == 0)

    # get_stats
    stats = obj.get_stats()
    test("ET: get_stats returns dict", isinstance(stats, dict))
    test("ET: stats has total_evaluations", "total_evaluations" in stats)

    # status
    st = obj.status()
    test("ET: status is string", isinstance(st, str))
    test("ET: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("ET: report is string", isinstance(report, str))
    test("ET: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("ET: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("ET: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = EthicalReasoner(base_dir=tmp)
    test("ET: persistence ok", obj2.total_evaluations == 0)

    # clear
    obj.clear()
    test("ET: clear resets", obj.total_evaluations == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === BIASDETECTOR ===
print("\n--- BiasDetector ---")

tmp = tempfile.mkdtemp()
try:
    obj = BiasDetector(base_dir=tmp)
    test("BI: init ok", obj is not None)
    test("BI: total_scans starts at 0", obj.total_scans == 0)

    # get_stats
    stats = obj.get_stats()
    test("BI: get_stats returns dict", isinstance(stats, dict))
    test("BI: stats has total_scans", "total_scans" in stats)

    # status
    st = obj.status()
    test("BI: status is string", isinstance(st, str))
    test("BI: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("BI: report is string", isinstance(report, str))
    test("BI: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("BI: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("BI: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = BiasDetector(base_dir=tmp)
    test("BI: persistence ok", obj2.total_scans == 0)

    # clear
    obj.clear()
    test("BI: clear resets", obj.total_scans == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === TRANSPARENCYENGINE ===
print("\n--- TransparencyEngine ---")

tmp = tempfile.mkdtemp()
try:
    obj = TransparencyEngine(base_dir=tmp)
    test("TR: init ok", obj is not None)
    test("TR: total_decisions starts at 0", obj.total_decisions == 0)

    # get_stats
    stats = obj.get_stats()
    test("TR: get_stats returns dict", isinstance(stats, dict))
    test("TR: stats has total_decisions", "total_decisions" in stats)

    # status
    st = obj.status()
    test("TR: status is string", isinstance(st, str))
    test("TR: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("TR: report is string", isinstance(report, str))
    test("TR: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("TR: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("TR: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = TransparencyEngine(base_dir=tmp)
    test("TR: persistence ok", obj2.total_decisions == 0)

    # clear
    obj.clear()
    test("TR: clear resets", obj.total_decisions == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 4.2", float(f"{major}.{minor}") >= 4.2)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

test("Int: import ethical_reasoner", "from core.ethical_reasoner import" in gs)
test("Int: self.ethical_reasoner", "self.ethical_reasoner" in gs)
test("Int: ethical_reasoner.save()", "self.ethical_reasoner.save()" in gs)
test("Int: cmd /ethics", "/ethics" in gs)
test("Int: status ETHICAL REASONER", "ETHICAL REASONER" in gs)
test("WebUI: ethical_reasoner", "ethical_reasoner" in ws)
test("Int: import bias_detector", "from core.bias_detector import" in gs)
test("Int: self.bias_detector", "self.bias_detector" in gs)
test("Int: bias_detector.save()", "self.bias_detector.save()" in gs)
test("Int: cmd /bias", "/bias" in gs)
test("Int: status BIAS DETECTOR", "BIAS DETECTOR" in gs)
test("WebUI: bias_detector", "bias_detector" in ws)
test("Int: import transparency_engine", "from core.transparency_engine import" in gs)
test("Int: self.transparency_engine", "self.transparency_engine" in gs)
test("Int: transparency_engine.save()", "self.transparency_engine.save()" in gs)
test("Int: cmd /transparency", "/transparency" in gs)
test("Int: status TRANSPARENCY ENGINE", "TRANSPARENCY ENGINE" in gs)
test("WebUI: transparency_engine", "transparency_engine" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
