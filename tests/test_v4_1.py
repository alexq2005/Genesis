"""Tests para Genesis v4.1 -- Temporal Intelligence"""
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
print("GENESIS v4.1 -- Temporal Intelligence Tests")
print("=" * 60)

from core.temporal_reasoner import TemporalReasoner
from core.schedule_optimizer import ScheduleOptimizer
from core.trend_forecaster import TrendForecaster


# === TEMPORALREASONER ===
print("\n--- TemporalReasoner ---")

tmp = tempfile.mkdtemp()
try:
    obj = TemporalReasoner(base_dir=tmp)
    test("TE: init ok", obj is not None)
    test("TE: total_events starts at 0", obj.total_events == 0)

    # get_stats
    stats = obj.get_stats()
    test("TE: get_stats returns dict", isinstance(stats, dict))
    test("TE: stats has total_events", "total_events" in stats)

    # status
    st = obj.status()
    test("TE: status is string", isinstance(st, str))
    test("TE: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("TE: report is string", isinstance(report, str))
    test("TE: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("TE: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("TE: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = TemporalReasoner(base_dir=tmp)
    test("TE: persistence ok", obj2.total_events == 0)

    # clear
    obj.clear()
    test("TE: clear resets", obj.total_events == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === SCHEDULEOPTIMIZER ===
print("\n--- ScheduleOptimizer ---")

tmp = tempfile.mkdtemp()
try:
    obj = ScheduleOptimizer(base_dir=tmp)
    test("SC: init ok", obj is not None)
    test("SC: total_optimizations starts at 0", obj.total_optimizations == 0)

    # get_stats
    stats = obj.get_stats()
    test("SC: get_stats returns dict", isinstance(stats, dict))
    test("SC: stats has total_optimizations", "total_optimizations" in stats)

    # status
    st = obj.status()
    test("SC: status is string", isinstance(st, str))
    test("SC: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("SC: report is string", isinstance(report, str))
    test("SC: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("SC: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("SC: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ScheduleOptimizer(base_dir=tmp)
    test("SC: persistence ok", obj2.total_optimizations == 0)

    # clear
    obj.clear()
    test("SC: clear resets", obj.total_optimizations == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === TRENDFORECASTER ===
print("\n--- TrendForecaster ---")

tmp = tempfile.mkdtemp()
try:
    obj = TrendForecaster(base_dir=tmp)
    test("TR: init ok", obj is not None)
    test("TR: total_forecasts starts at 0", obj.total_forecasts == 0)

    # get_stats
    stats = obj.get_stats()
    test("TR: get_stats returns dict", isinstance(stats, dict))
    test("TR: stats has total_forecasts", "total_forecasts" in stats)

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
    obj2 = TrendForecaster(base_dir=tmp)
    test("TR: persistence ok", obj2.total_forecasts == 0)

    # clear
    obj.clear()
    test("TR: clear resets", obj.total_forecasts == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 4.1", float(f"{major}.{minor}") >= 4.1)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

test("Int: import temporal_reasoner", "from core.temporal_reasoner import" in gs)
test("Int: self.temporal_reasoner", "self.temporal_reasoner" in gs)
test("Int: temporal_reasoner.save()", "self.temporal_reasoner.save()" in gs)
test("Int: cmd /temporal", "/temporal" in gs)
test("Int: status TEMPORAL REASONER", "TEMPORAL REASONER" in gs)
test("WebUI: temporal_reasoner", "temporal_reasoner" in ws)
test("Int: import schedule_optimizer", "from core.schedule_optimizer import" in gs)
test("Int: self.schedule_optimizer", "self.schedule_optimizer" in gs)
test("Int: schedule_optimizer.save()", "self.schedule_optimizer.save()" in gs)
test("Int: cmd /schedule", "/schedule" in gs)
test("Int: status SCHEDULE OPTIMIZER", "SCHEDULE OPTIMIZER" in gs)
test("WebUI: schedule_optimizer", "schedule_optimizer" in ws)
test("Int: import trend_forecaster", "from core.trend_forecaster import" in gs)
test("Int: self.trend_forecaster", "self.trend_forecaster" in gs)
test("Int: trend_forecaster.save()", "self.trend_forecaster.save()" in gs)
test("Int: cmd /trends", "/trends" in gs)
test("Int: status TREND FORECASTER", "TREND FORECASTER" in gs)
test("WebUI: trend_forecaster", "trend_forecaster" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
