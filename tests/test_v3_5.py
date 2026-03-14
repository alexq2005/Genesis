"""Tests para Genesis v3.5 -- Autonomous Research"""
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
print("GENESIS v3.5 -- Autonomous Research Tests")
print("=" * 60)

from core.paper_reader import PaperReader
from core.experiment_runner import ExperimentRunner
from core.insight_synthesizer import InsightSynthesizer


# === PAPERREADER ===
print("\n--- PaperReader ---")

tmp = tempfile.mkdtemp()
try:
    obj = PaperReader(base_dir=tmp)
    test("PA: init ok", obj is not None)
    test("PA: total_papers_read starts at 0", obj.total_papers_read == 0)

    # get_stats
    stats = obj.get_stats()
    test("PA: get_stats returns dict", isinstance(stats, dict))
    test("PA: stats has total_papers_read", "total_papers_read" in stats)

    # status
    st = obj.status()
    test("PA: status is string", isinstance(st, str))
    test("PA: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("PA: report is string", isinstance(report, str))
    test("PA: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("PA: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("PA: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = PaperReader(base_dir=tmp)
    test("PA: persistence ok", obj2.total_papers_read == 0)

    # clear
    obj.clear()
    test("PA: clear resets", obj.total_papers_read == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === EXPERIMENTRUNNER ===
print("\n--- ExperimentRunner ---")

tmp = tempfile.mkdtemp()
try:
    obj = ExperimentRunner(base_dir=tmp)
    test("EX: init ok", obj is not None)
    test("EX: total_experiments starts at 0", obj.total_experiments == 0)

    # get_stats
    stats = obj.get_stats()
    test("EX: get_stats returns dict", isinstance(stats, dict))
    test("EX: stats has total_experiments", "total_experiments" in stats)

    # status
    st = obj.status()
    test("EX: status is string", isinstance(st, str))
    test("EX: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("EX: report is string", isinstance(report, str))
    test("EX: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("EX: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("EX: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ExperimentRunner(base_dir=tmp)
    test("EX: persistence ok", obj2.total_experiments == 0)

    # clear
    obj.clear()
    test("EX: clear resets", obj.total_experiments == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === INSIGHTSYNTHESIZER ===
print("\n--- InsightSynthesizer ---")

tmp = tempfile.mkdtemp()
try:
    obj = InsightSynthesizer(base_dir=tmp)
    test("IN: init ok", obj is not None)
    test("IN: total_insights starts at 0", obj.total_insights == 0)

    # get_stats
    stats = obj.get_stats()
    test("IN: get_stats returns dict", isinstance(stats, dict))
    test("IN: stats has total_insights", "total_insights" in stats)

    # status
    st = obj.status()
    test("IN: status is string", isinstance(st, str))
    test("IN: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("IN: report is string", isinstance(report, str))
    test("IN: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("IN: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("IN: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = InsightSynthesizer(base_dir=tmp)
    test("IN: persistence ok", obj2.total_insights == 0)

    # clear
    obj.clear()
    test("IN: clear resets", obj.total_insights == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 3.5", float(f"{major}.{minor}") >= 3.5)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

test("Int: import paper_reader", "from core.paper_reader import" in gs)
test("Int: self.paper_reader", "self.paper_reader" in gs)
test("Int: paper_reader.save()", "self.paper_reader.save()" in gs)
test("Int: cmd /papers", "/papers" in gs)
test("Int: status PAPER READER", "PAPER READER" in gs)
test("WebUI: paper_reader", "paper_reader" in ws)
test("Int: import experiment_runner", "from core.experiment_runner import" in gs)
test("Int: self.experiment_runner", "self.experiment_runner" in gs)
test("Int: experiment_runner.save()", "self.experiment_runner.save()" in gs)
test("Int: cmd /experiments", "/experiments" in gs)
test("Int: status EXPERIMENT RUNNER", "EXPERIMENT RUNNER" in gs)
test("WebUI: experiment_runner", "experiment_runner" in ws)
test("Int: import insight_synthesizer", "from core.insight_synthesizer import" in gs)
test("Int: self.insight_synthesizer", "self.insight_synthesizer" in gs)
test("Int: insight_synthesizer.save()", "self.insight_synthesizer.save()" in gs)
test("Int: cmd /insights", "/insights" in gs)
test("Int: status INSIGHT SYNTHESIZER", "INSIGHT SYNTHESIZER" in gs)
test("WebUI: insight_synthesizer", "insight_synthesizer" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
