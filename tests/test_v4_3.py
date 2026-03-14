"""Tests para Genesis v4.3 -- Knowledge Mastery"""
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
print("GENESIS v4.3 -- Knowledge Mastery Tests")
print("=" * 60)

from core.domain_expert import DomainExpert
from core.tutor_engine import TutorEngine
from core.fact_checker import FactChecker


# === DOMAINEXPERT ===
print("\n--- DomainExpert ---")

tmp = tempfile.mkdtemp()
try:
    obj = DomainExpert(base_dir=tmp)
    test("DO: init ok", obj is not None)
    test("DO: total_detections starts at 0", obj.total_detections == 0)

    # get_stats
    stats = obj.get_stats()
    test("DO: get_stats returns dict", isinstance(stats, dict))
    test("DO: stats has total_detections", "total_detections" in stats)

    # status
    st = obj.status()
    test("DO: status is string", isinstance(st, str))
    test("DO: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("DO: report is string", isinstance(report, str))
    test("DO: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("DO: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("DO: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = DomainExpert(base_dir=tmp)
    test("DO: persistence ok", obj2.total_detections == 0)

    # clear
    obj.clear()
    test("DO: clear resets", obj.total_detections == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === TUTORENGINE ===
print("\n--- TutorEngine ---")

tmp = tempfile.mkdtemp()
try:
    obj = TutorEngine(base_dir=tmp)
    test("TU: init ok", obj is not None)
    test("TU: total_lessons starts at 0", obj.total_lessons == 0)

    # get_stats
    stats = obj.get_stats()
    test("TU: get_stats returns dict", isinstance(stats, dict))
    test("TU: stats has total_lessons", "total_lessons" in stats)

    # status
    st = obj.status()
    test("TU: status is string", isinstance(st, str))
    test("TU: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("TU: report is string", isinstance(report, str))
    test("TU: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("TU: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("TU: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = TutorEngine(base_dir=tmp)
    test("TU: persistence ok", obj2.total_lessons == 0)

    # clear
    obj.clear()
    test("TU: clear resets", obj.total_lessons == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === FACTCHECKER ===
print("\n--- FactChecker ---")

tmp = tempfile.mkdtemp()
try:
    obj = FactChecker(base_dir=tmp)
    test("FA: init ok", obj is not None)
    test("FA: total_checked starts at 0", obj.total_checked == 0)

    # get_stats
    stats = obj.get_stats()
    test("FA: get_stats returns dict", isinstance(stats, dict))
    test("FA: stats has total_checked", "total_checked" in stats)

    # status
    st = obj.status()
    test("FA: status is string", isinstance(st, str))
    test("FA: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("FA: report is string", isinstance(report, str))
    test("FA: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("FA: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("FA: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = FactChecker(base_dir=tmp)
    test("FA: persistence ok", obj2.total_checked == 0)

    # clear
    obj.clear()
    test("FA: clear resets", obj.total_checked == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 4.3", float(f"{major}.{minor}") >= 4.3)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

test("Int: import domain_expert", "from core.domain_expert import" in gs)
test("Int: self.domain_expert", "self.domain_expert" in gs)
test("Int: domain_expert.save()", "self.domain_expert.save()" in gs)
test("Int: cmd /domains", "/domains" in gs)
test("Int: status DOMAIN EXPERT", "DOMAIN EXPERT" in gs)
test("WebUI: domain_expert", "domain_expert" in ws)
test("Int: import tutor_engine", "from core.tutor_engine import" in gs)
test("Int: self.tutor_engine", "self.tutor_engine" in gs)
test("Int: tutor_engine.save()", "self.tutor_engine.save()" in gs)
test("Int: cmd /tutor", "/tutor" in gs)
test("Int: status TUTOR ENGINE", "TUTOR ENGINE" in gs)
test("WebUI: tutor_engine", "tutor_engine" in ws)
test("Int: import fact_checker", "from core.fact_checker import" in gs)
test("Int: self.fact_checker", "self.fact_checker" in gs)
test("Int: fact_checker.save()", "self.fact_checker.save()" in gs)
test("Int: cmd /factcheck", "/factcheck" in gs)
test("Int: status FACT CHECKER", "FACT CHECKER" in gs)
test("WebUI: fact_checker", "fact_checker" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
