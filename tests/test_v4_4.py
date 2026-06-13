"""Tests para Genesis v4.4 -- Distributed Genesis"""
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
print("GENESIS v4.4 -- Distributed Genesis Tests")
print("=" * 60)

from core.task_distributor import TaskDistributor
from core.result_aggregator import ResultAggregator
from core.network_manager import NetworkManager


# === TASKDISTRIBUTOR ===
print("\n--- TaskDistributor ---")

tmp = tempfile.mkdtemp()
try:
    obj = TaskDistributor(base_dir=tmp)
    test("TA: init ok", obj is not None)
    test("TA: total_tasks starts at 0", obj.total_tasks == 0)

    # get_stats
    stats = obj.get_stats()
    test("TA: get_stats returns dict", isinstance(stats, dict))
    test("TA: stats has total_tasks", "total_tasks" in stats)

    # status
    st = obj.status()
    test("TA: status is string", isinstance(st, str))
    test("TA: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("TA: report is string", isinstance(report, str))
    test("TA: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("TA: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("TA: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = TaskDistributor(base_dir=tmp)
    test("TA: persistence ok", obj2.total_tasks == 0)

    # clear
    obj.clear()
    test("TA: clear resets", obj.total_tasks == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === RESULTAGGREGATOR ===
print("\n--- ResultAggregator ---")

tmp = tempfile.mkdtemp()
try:
    obj = ResultAggregator(base_dir=tmp)
    test("RE: init ok", obj is not None)
    test("RE: total_aggregated starts at 0", obj.total_aggregated == 0)

    # get_stats
    stats = obj.get_stats()
    test("RE: get_stats returns dict", isinstance(stats, dict))
    test("RE: stats has total_aggregated", "total_aggregated" in stats)

    # status
    st = obj.status()
    test("RE: status is string", isinstance(st, str))
    test("RE: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("RE: report is string", isinstance(report, str))
    test("RE: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("RE: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("RE: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = ResultAggregator(base_dir=tmp)
    test("RE: persistence ok", obj2.total_aggregated == 0)

    # clear
    obj.clear()
    test("RE: clear resets", obj.total_aggregated == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === NETWORKMANAGER ===
print("\n--- NetworkManager ---")

tmp = tempfile.mkdtemp()
try:
    obj = NetworkManager(base_dir=tmp)
    test("NE: init ok", obj is not None)
    test("NE: total_nodes_seen starts at 0", obj.total_nodes_seen == 0)

    # get_stats
    stats = obj.get_stats()
    test("NE: get_stats returns dict", isinstance(stats, dict))
    test("NE: stats has total_nodes_seen", "total_nodes_seen" in stats)

    # status
    st = obj.status()
    test("NE: status is string", isinstance(st, str))
    test("NE: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("NE: report is string", isinstance(report, str))
    test("NE: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("NE: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("NE: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = NetworkManager(base_dir=tmp)
    test("NE: persistence ok", obj2.total_nodes_seen == 0)

    # clear
    obj.clear()
    test("NE: clear resets", obj.total_nodes_seen == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)


# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 4.4", float(f"{major}.{minor}") >= 4.4)

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

test("Int: import task_distributor", "from core.task_distributor import" in gs)
test("Int: self.task_distributor", "self.task_distributor" in gs)
test("Int: task_distributor.save()", '"task_distributor"' in gs)
test("Int: cmd /distribute", "/distribute" in gs)
test("Int: status TASK DISTRIBUTOR", "TASK DISTRIBUTOR" in gs)
test("WebUI: task_distributor", "task_distributor" in ws)
test("Int: import result_aggregator", "from core.result_aggregator import" in gs)
test("Int: self.result_aggregator", "self.result_aggregator" in gs)
test("Int: result_aggregator.save()", '"result_aggregator"' in gs)
test("Int: cmd /aggregate", "/aggregate" in gs)
test("Int: status RESULT AGGREGATOR", "RESULT AGGREGATOR" in gs)
test("WebUI: result_aggregator", "result_aggregator" in ws)
test("Int: import network_manager", "from core.network_manager import" in gs)
test("Int: self.network_manager", "self.network_manager" in gs)
test("Int: network_manager.save()", '"network_manager"' in gs)
test("Int: cmd /network", "/network" in gs)
test("Int: status NETWORK MANAGER", "NETWORK MANAGER" in gs)
test("WebUI: network_manager", "network_manager" in ws)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
