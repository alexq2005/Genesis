"""
Tests para Genesis v1.9.0
- TaskScheduler (tareas, ejecucion, log, pause/resume)
- ConfigManager (profiles, save/load, diff, export/import)
- PerformanceProfiler (timing, bottlenecks, trends, reports)
- Integracion en genesis.py (imports, comandos, status)
"""
import sys
import os
import tempfile
import shutil
import time
import json

# Forzar UTF-8 en stdout para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

# ============================================================
# Mini test framework
# ============================================================
_passed = 0
_failed = 0

def test(name, condition):
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        print(f"  [FAIL] {name}")


# ============================================================
# TEST 1: ScheduledTask basico
# ============================================================
print("\n=== TEST: ScheduledTask ===")
from core.task_scheduler import ScheduledTask, ExecutionLog, TaskScheduler

st = ScheduledTask(name="test_task", interval_seconds=60, description="Tarea de prueba")
test("Task name", st.name == "test_task")
test("Task interval", st.interval_seconds == 60.0)
test("Task description", st.description == "Tarea de prueba")
test("Task enabled por defecto", st.enabled == True)
test("Task run_count = 0", st.run_count == 0)
test("Task not due (recien creada)", not st.is_due())  # next_run en el futuro
test("Task format_interval 60s = 1m", st.format_interval() == "1m")

# Intervals
st_h = ScheduledTask(name="hourly", interval_seconds=3600)
test("Format interval hours", st_h.format_interval() == "1h")

st_s = ScheduledTask(name="fast", interval_seconds=30)
test("Format interval seconds", st_s.format_interval() == "30s")

# Minimo intervalo
st_min = ScheduledTask(name="min", interval_seconds=0)
test("Intervalo minimo = 1s", st_min.interval_seconds == 1.0)


# ============================================================
# TEST 2: ScheduledTask ejecucion
# ============================================================
print("\n=== TEST: ScheduledTask ejecucion ===")

counter = {"value": 0}
def increment_counter():
    counter["value"] += 1
    return f"count={counter['value']}"

st2 = ScheduledTask(name="counter", callback=increment_counter, interval_seconds=1)
result = st2.execute()
test("Execute retorna dict", isinstance(result, dict))
test("Execute success", result["success"] == True)
test("Execute result", "count=1" in result["result"])
test("Execute run_count", st2.run_count == 1)
test("Execute success_count", st2.success_count == 1)
test("Execute duration_ms >= 0", result["duration_ms"] >= 0)
test("Counter incrementado", counter["value"] == 1)

# Segunda ejecucion
st2.execute()
test("Counter incrementado 2x", counter["value"] == 2)
test("Run count 2", st2.run_count == 2)

# Ejecucion con error
def failing_fn():
    raise ValueError("Error de prueba")

st3 = ScheduledTask(name="failer", callback=failing_fn, interval_seconds=10)
result = st3.execute()
test("Execute fallo success=False", result["success"] == False)
test("Execute fallo tiene error", "Error de prueba" in result["error"])
test("Failure count", st3.failure_count == 1)
test("Last error guardado", "Error de prueba" in st3.last_error)

# Sin callback
st4 = ScheduledTask(name="noop", callback=None)
result = st4.execute()
test("Sin callback = success", result["success"] == True)

# Stats
stats = st2.get_stats()
test("Stats tiene name", stats["name"] == "counter")
test("Stats tiene run_count", stats["run_count"] == 2)
test("Stats tiene success_rate", stats["success_rate"] == 100.0)
test("Stats tiene avg_duration_ms", "avg_duration_ms" in stats)


# ============================================================
# TEST 3: ScheduledTask is_due
# ============================================================
print("\n=== TEST: ScheduledTask is_due ===")

st_due = ScheduledTask(name="due", interval_seconds=0.05)
# Force next_run to now
st_due.next_run = time.time() - 1
test("Task is due (next_run en pasado)", st_due.is_due())

st_due.enabled = False
test("Task disabled not due", not st_due.is_due())

st_due.enabled = True
st_due.execute()
test("Task not due despues de execute", not st_due.is_due() or st_due.interval_seconds <= 0.05)

# time_until_next
test("time_until_next >= 0", st_due.time_until_next() >= 0)


# ============================================================
# TEST 4: ExecutionLog
# ============================================================
print("\n=== TEST: ExecutionLog ===")

log = ExecutionLog(max_entries=10)
test("Log vacio", len(log.entries) == 0)

# Agregar entries
for i in range(5):
    log.add({"task": "t1", "success": True, "timestamp": time.time()})
for i in range(3):
    log.add({"task": "t2", "success": False, "timestamp": time.time()})

test("Log tiene 8 entries", len(log.entries) == 8)
test("Get recent 3", len(log.get_recent(3)) == 3)
test("Get by task t1", len(log.get_by_task("t1")) == 5)
test("Get by task t2", len(log.get_by_task("t2")) == 3)
test("Get failures", len(log.get_failures()) == 3)

stats = log.get_stats()
test("Log stats total", stats["total_entries"] == 8)
test("Log stats successes", stats["successes"] == 5)
test("Log stats failures", stats["failures"] == 3)

# Max entries
for i in range(15):
    log.add({"task": "overflow", "success": True, "timestamp": time.time()})
test("Max entries respetado", len(log.entries) <= 10)

# Clear
log.clear()
test("Log clear", len(log.entries) == 0)


# ============================================================
# TEST 5: TaskScheduler basico
# ============================================================
print("\n=== TEST: TaskScheduler basico ===")

ts = TaskScheduler()
test("Scheduler enabled", ts.enabled == True)
test("Scheduler not paused", ts.paused == False)
test("No tasks initially", len(ts.tasks) == 0)

# Add task
result = ts.add_task("test1", lambda: "OK", interval_seconds=60, description="Test")
test("Add task exitoso", "registrada" in result)
test("Task exists", "test1" in ts.tasks)

# Add duplicada
result = ts.add_task("test1", lambda: "duplicate")
test("Add duplicada rechazada", "ya existe" in result)

# Toggle task
result = ts.toggle_task("test1")
test("Toggle task", "desactivada" in result)
test("Task disabled", ts.tasks["test1"].enabled == False)

result = ts.toggle_task("test1")
test("Toggle task again", "activada" in result)

# Remove task
result = ts.remove_task("test1")
test("Remove task", "eliminada" in result)
test("Task removed", "test1" not in ts.tasks)

# Remove inexistente
result = ts.remove_task("no_existe")
test("Remove inexistente", "no encontrada" in result)


# ============================================================
# TEST 6: TaskScheduler tick
# ============================================================
print("\n=== TEST: TaskScheduler tick ===")

ts2 = TaskScheduler()
tick_counter = {"value": 0}
def tick_fn():
    tick_counter["value"] += 1

ts2.add_task("ticker", tick_fn, interval_seconds=0.05)
# Force task to be due
ts2.tasks["ticker"].next_run = time.time() - 1

results = ts2.tick()
test("Tick ejecuta tareas due", len(results) >= 1)
test("Tick counter incrementado", tick_counter["value"] >= 1)
test("Total ticks incrementado", ts2.total_ticks >= 1)
test("Total executions", ts2.total_executions >= 1)

# Tick con scheduler paused
ts2.pause()
old_count = tick_counter["value"]
ts2.tasks["ticker"].next_run = time.time() - 1
results = ts2.tick()
test("Tick pausado no ejecuta", len(results) == 0)
test("Counter no cambio", tick_counter["value"] == old_count)

ts2.resume()
test("Resume OK", not ts2.paused)


# ============================================================
# TEST 7: TaskScheduler run_task_now
# ============================================================
print("\n=== TEST: TaskScheduler run_task_now ===")

ts3 = TaskScheduler()
ts3.add_task("immediate", lambda: "done!", interval_seconds=3600)

result = ts3.run_task_now("immediate")
test("Run now exitoso", "OK" in result or "done!" in result)

result = ts3.run_task_now("no_existe")
test("Run now inexistente", "no encontrada" in result)


# ============================================================
# TEST 8: TaskScheduler set_interval
# ============================================================
print("\n=== TEST: TaskScheduler set_interval ===")

ts4 = TaskScheduler()
ts4.add_task("adjustable", lambda: None, interval_seconds=60)

result = ts4.set_interval("adjustable", 120)
test("Set interval OK", "120" in result or "2m" in result)
test("Interval actualizado", ts4.tasks["adjustable"].interval_seconds == 120)

result = ts4.set_interval("no_existe", 30)
test("Set interval inexistente", "no encontrada" in result)


# ============================================================
# TEST 9: TaskScheduler reports
# ============================================================
print("\n=== TEST: TaskScheduler reports ===")

ts5 = TaskScheduler()
ts5.add_task("report_test", lambda: "OK", interval_seconds=30, description="Para reporte")

report = ts5.get_full_report()
test("Full report contiene TASK SCHEDULER", "TASK SCHEDULER" in report)
test("Full report contiene TAREAS", "TAREAS" in report)

task_list = ts5.get_task_list()
test("Task list contiene report_test", "report_test" in task_list)

log_report = ts5.get_log_report()
test("Log report sin ejecuciones", "Sin ejecuciones" in log_report)

status = ts5.status()
test("Status contiene Estado", "Estado" in status)
test("Status contiene Tareas", "Tareas" in status)

# Toggle global
result = ts5.toggle()
test("Toggle global", "DESACTIVADO" in result)
result = ts5.toggle()
test("Toggle global re-enable", "ACTIVADO" in result)

# Upcoming
upcoming = ts5.get_upcoming()
test("Upcoming tiene tareas", len(upcoming) >= 1)


# ============================================================
# TEST 10: ConfigProfile
# ============================================================
print("\n=== TEST: ConfigProfile ===")
from core.config_manager import ConfigProfile, ConfigDiff, ConfigManager

cp = ConfigProfile(name="test_profile", description="Perfil de test")
test("Profile name", cp.name == "test_profile")
test("Profile description", cp.description == "Perfil de test")
test("Profile sections vacio", len(cp.sections) == 0)

# Add sections
cp.add_section("general", {"key": "value", "number": 42})
cp.add_section("memory", {"capacity": 100})
test("2 secciones", len(cp.sections) == 2)
test("Get section", cp.get_section("general")["key"] == "value")
test("Get section inexistente", cp.get_section("nope") == {})

# to_dict / from_dict roundtrip
d = cp.to_dict()
test("to_dict tiene name", d["name"] == "test_profile")
test("to_dict tiene sections", len(d["sections"]) == 2)

cp2 = ConfigProfile.from_dict(d)
test("from_dict name", cp2.name == "test_profile")
test("from_dict sections", len(cp2.sections) == 2)
test("from_dict section data", cp2.get_section("general")["key"] == "value")

# summary
summary = cp.summary()
test("Summary contiene nombre", "test_profile" in summary)


# ============================================================
# TEST 11: ConfigDiff
# ============================================================
print("\n=== TEST: ConfigDiff ===")

diff = ConfigDiff("perfil_a", "perfil_b")
diff.added_sections = ["new_section"]
diff.removed_sections = ["old_section"]
diff.modified_sections = {"common": ["~ key: old -> new"]}

formatted = diff.format()
test("Diff contiene DIFF", "DIFF" in formatted)
test("Diff contiene NUEVAS", "NUEVAS" in formatted)
test("Diff contiene ELIMINADAS", "ELIMINADAS" in formatted)
test("Diff contiene MODIFICADAS", "MODIFICADAS" in formatted)

# Diff vacio
diff_empty = ConfigDiff("a", "b")
formatted_empty = diff_empty.format()
test("Diff vacio identicos", "identicos" in formatted_empty.lower())


# ============================================================
# TEST 12: ConfigManager basico
# ============================================================
print("\n=== TEST: ConfigManager basico ===")

tmpdir = tempfile.mkdtemp()
cm = ConfigManager(base_dir=tmpdir)
test("Profiles dir existe", cm.profiles_dir.exists())
test("No collectors", len(cm._collectors) == 0)
test("Active profile vacio", cm.active_profile == "")


# ============================================================
# TEST 13: ConfigManager save/load
# ============================================================
print("\n=== TEST: ConfigManager save/load ===")

# Registrar un collector
cm.register_collector("test_section", lambda: {"key": "value", "n": 42})
test("Collector registrado", "test_section" in cm._collectors)

# Save
result = cm.save_profile("mi_perfil", "Descripcion del perfil")
test("Save exitoso", "guardado" in result.lower())
test("Active profile", cm.active_profile == "mi_perfil")

# Load
profile = cm.load_profile("mi_perfil")
test("Load exitoso", profile is not None)
test("Load name", profile.name == "mi_perfil")
test("Load tiene seccion", "test_section" in profile.sections)
test("Load seccion data", profile.sections["test_section"]["key"] == "value")

# Load inexistente
profile_none = cm.load_profile("no_existe")
test("Load inexistente", profile_none is None)


# ============================================================
# TEST 14: ConfigManager apply
# ============================================================
print("\n=== TEST: ConfigManager apply ===")

applied_data = {"applied": False}
def test_applier(data):
    applied_data["applied"] = True
    applied_data["data"] = data

cm.register_applier("test_section", test_applier)

result = cm.apply_profile("mi_perfil")
test("Apply exitoso", "aplicado" in result.lower())
test("Applier ejecutado", applied_data["applied"] == True)
test("Applier recibio data", applied_data["data"]["key"] == "value")

result = cm.apply_profile("no_existe")
test("Apply inexistente", "no encontrado" in result.lower())


# ============================================================
# TEST 15: ConfigManager delete
# ============================================================
print("\n=== TEST: ConfigManager delete ===")

# Primero crear otro para eliminar
cm.save_profile("para_borrar")
result = cm.delete_profile("para_borrar")
test("Delete exitoso", "eliminado" in result.lower())

result = cm.delete_profile("no_existe")
test("Delete inexistente", "no encontrado" in result.lower())


# ============================================================
# TEST 16: ConfigManager list
# ============================================================
print("\n=== TEST: ConfigManager list ===")

listing = cm.list_profiles()
test("List contiene mi_perfil", "mi_perfil" in listing)
test("List contiene PERFILES", "PERFILES" in listing)


# ============================================================
# TEST 17: ConfigManager compare
# ============================================================
print("\n=== TEST: ConfigManager compare ===")

# Crear segundo perfil diferente
cm.register_collector("extra_section", lambda: {"extra": True})
cm.save_profile("perfil_b", "Segundo perfil")

result = cm.compare_profiles("mi_perfil", "perfil_b")
test("Compare contiene DIFF", "DIFF" in result)
test("Compare muestra diferencias", "extra_section" in result or "NUEVAS" in result)

# Compare con inexistente
result = cm.compare_profiles("mi_perfil", "no_existe")
test("Compare inexistente", "no encontrado" in result.lower())


# ============================================================
# TEST 18: ConfigManager export/import
# ============================================================
print("\n=== TEST: ConfigManager export/import ===")

export_dir = tempfile.mkdtemp()
result = cm.export_profile("mi_perfil", export_dir)
test("Export exitoso", "exportado" in result.lower())

# Verificar archivo exportado
exported_files = list(os.listdir(export_dir))
test("Archivo exportado existe", len(exported_files) >= 1)

# Import
export_path = os.path.join(export_dir, exported_files[0])
result = cm.import_profile(export_path)
test("Import exitoso", "importado" in result.lower())

# Import inexistente
result = cm.import_profile("/ruta/inexistente.json")
test("Import inexistente", "no encontrado" in result.lower())

shutil.rmtree(tmpdir, ignore_errors=True)
shutil.rmtree(export_dir, ignore_errors=True)


# ============================================================
# TEST 19: ConfigManager status
# ============================================================
print("\n=== TEST: ConfigManager status ===")

cm2 = ConfigManager(base_dir=tempfile.mkdtemp())
status = cm2.status()
test("Status contiene Perfiles", "Perfiles" in status)
test("Status contiene Collectors", "Collectors" in status)

stats = cm2.get_stats()
test("Stats tiene profiles", "profiles" in stats)
test("Stats tiene collectors", "collectors" in stats)


# ============================================================
# TEST 20: TimingRecord
# ============================================================
print("\n=== TEST: TimingRecord ===")
from core.performance_profiler import TimingRecord, PerformanceProfiler

tr = TimingRecord(name="test_timing")
test("TimingRecord name", tr.name == "test_timing")
test("TimingRecord no samples", len(tr.samples) == 0)
test("Avg sin datos = 0", tr.avg_ms == 0.0)
test("P95 sin datos = 0", tr.p95_ms == 0.0)
test("P50 sin datos = 0", tr.p50_ms == 0.0)
test("Error rate sin datos = 0", tr.error_rate == 0.0)
test("Trend insufficient data", tr.trend() == "insufficient_data")

# Registrar samples
for i in range(20):
    tr.record(100.0)  # 100ms constante

test("20 samples", len(tr.samples) == 20)
test("Total calls", tr.total_calls == 20)
test("Avg = 100", tr.avg_ms == 100.0)
test("P50 = 100", tr.p50_ms == 100.0)
test("P95 = 100", tr.p95_ms == 100.0)
test("Min = 100", tr.min_time_ms == 100.0)
test("Max = 100", tr.max_time_ms == 100.0)
test("Trend stable", tr.trend() == "stable")

# Agregar errores
tr.record(200.0, error=True)
test("Error count", tr.errors == 1)
test("Error rate", tr.error_rate > 0)

# Max samples
tr2 = TimingRecord(name="limited", max_samples=5)
for i in range(10):
    tr2.record(float(i * 10))
test("Max samples respetado", len(tr2.samples) <= 5)

# Stats
stats = tr.get_stats()
test("Stats tiene name", stats["name"] == "test_timing")
test("Stats tiene total_calls", stats["total_calls"] == 21)
test("Stats tiene avg_ms", "avg_ms" in stats)
test("Stats tiene p95_ms", "p95_ms" in stats)
test("Stats tiene trend", "trend" in stats)


# ============================================================
# TEST 21: TimingRecord trends
# ============================================================
print("\n=== TEST: TimingRecord trends ===")

# Degrading: primera mitad rapida, segunda mitad lenta
tr_deg = TimingRecord(name="degrading")
for i in range(10):
    tr_deg.record(50.0)  # Primera mitad: 50ms
for i in range(10):
    tr_deg.record(150.0)  # Segunda mitad: 150ms (3x)
test("Trend degrading", tr_deg.trend() == "degrading")

# Improving: primera mitad lenta, segunda mitad rapida
tr_imp = TimingRecord(name="improving")
for i in range(10):
    tr_imp.record(150.0)
for i in range(10):
    tr_imp.record(50.0)
test("Trend improving", tr_imp.trend() == "improving")


# ============================================================
# TEST 22: PerformanceProfiler basico
# ============================================================
print("\n=== TEST: PerformanceProfiler basico ===")

pp = PerformanceProfiler()
test("Profiler enabled", pp.enabled == True)
test("No records", len(pp.records) == 0)

# start/stop
pp.start("test_op")
time.sleep(0.01)
duration = pp.stop("test_op")
test("Stop retorna duracion > 0", duration > 0)
test("Record creado", "test_op" in pp.records)
test("Record tiene 1 sample", pp.records["test_op"].total_calls == 1)

# Stop sin start
duration = pp.stop("no_started")
test("Stop sin start = 0", duration == 0.0)


# ============================================================
# TEST 23: PerformanceProfiler context manager
# ============================================================
print("\n=== TEST: PerformanceProfiler measure ===")

pp2 = PerformanceProfiler()

with pp2.measure("measured_op"):
    time.sleep(0.01)

test("Measure registro", "measured_op" in pp2.records)
test("Measure calls = 1", pp2.records["measured_op"].total_calls == 1)
test("Measure avg > 0", pp2.records["measured_op"].avg_ms > 0)

# Measure con error
try:
    with pp2.measure("error_op"):
        raise ValueError("test error")
except ValueError:
    pass

test("Error op registrada", "error_op" in pp2.records)
test("Error op errors = 1", pp2.records["error_op"].errors == 1)


# ============================================================
# TEST 24: PerformanceProfiler record_direct
# ============================================================
print("\n=== TEST: PerformanceProfiler record_direct ===")

pp3 = PerformanceProfiler()
pp3.record_direct("direct_op", 42.5)
pp3.record_direct("direct_op", 57.5)
test("Direct record", pp3.records["direct_op"].total_calls == 2)
test("Direct avg", pp3.records["direct_op"].avg_ms == 50.0)


# ============================================================
# TEST 25: PerformanceProfiler bottlenecks
# ============================================================
print("\n=== TEST: PerformanceProfiler bottlenecks ===")

pp4 = PerformanceProfiler()
pp4.record_direct("fast", 10.0)
pp4.record_direct("medium", 100.0)
pp4.record_direct("slow", 1000.0)

bottlenecks = pp4.get_bottlenecks(2)
test("Bottlenecks top 2", len(bottlenecks) == 2)
test("Bottleneck mas lento primero", bottlenecks[0]["name"] == "slow")
test("Bottleneck segundo", bottlenecks[1]["name"] == "medium")

# Most called
pp4.record_direct("fast", 10.0)
pp4.record_direct("fast", 10.0)
most = pp4.get_most_called(1)
test("Most called = fast", most[0]["name"] == "fast")

# Highest error rate
pp4.record_direct("buggy", 50.0, error=True)
pp4.record_direct("buggy", 50.0, error=True)
highest_err = pp4.get_highest_error_rate(1)
test("Highest error rate = buggy", highest_err[0]["name"] == "buggy")


# ============================================================
# TEST 26: PerformanceProfiler slow operations
# ============================================================
print("\n=== TEST: PerformanceProfiler slow operations ===")

pp5 = PerformanceProfiler()
pp5.slow_threshold_ms = 100.0
pp5.record_direct("quick", 50.0)
pp5.record_direct("slow_one", 200.0)

slow = pp5.get_slow_operations()
test("Slow operations", len(slow) >= 1)
test("Slow op name", slow[0]["name"] == "slow_one")


# ============================================================
# TEST 27: PerformanceProfiler degrading
# ============================================================
print("\n=== TEST: PerformanceProfiler degrading ===")

pp6 = PerformanceProfiler()
# Simular degradacion
for i in range(10):
    pp6.record_direct("degrading_op", 50.0)
for i in range(10):
    pp6.record_direct("degrading_op", 200.0)

degrading = pp6.get_degrading()
test("Degrading detectado", len(degrading) >= 1)
test("Degrading op name", degrading[0]["name"] == "degrading_op")


# ============================================================
# TEST 28: PerformanceProfiler toggle y reset
# ============================================================
print("\n=== TEST: PerformanceProfiler toggle/reset ===")

pp7 = PerformanceProfiler()
pp7.record_direct("data", 100.0)

pp7.toggle()
test("Toggle desactiva", pp7.enabled == False)

pp7.record_direct("ignored", 50.0)
test("No registra cuando disabled", "ignored" not in pp7.records)

pp7.toggle()
test("Toggle reactiva", pp7.enabled == True)

pp7.reset("data")
test("Reset individual", "data" not in pp7.records)

pp7.record_direct("a", 10.0)
pp7.record_direct("b", 20.0)
pp7.reset()
test("Reset all", len(pp7.records) == 0)


# ============================================================
# TEST 29: PerformanceProfiler reports
# ============================================================
print("\n=== TEST: PerformanceProfiler reports ===")

pp8 = PerformanceProfiler()
pp8.record_direct("brain.generate", 150.0)
pp8.record_direct("memory.retrieve", 30.0)
pp8.record_direct("rag.search", 80.0)

report = pp8.generate_report()
test("Report contiene PERFORMANCE", "PERFORMANCE" in report)
test("Report contiene brain.generate", "brain.generate" in report)
test("Report contiene TOP 5", "TOP 5" in report)

status = pp8.status()
test("Status contiene Estado", "Estado" in status)
test("Status contiene Subsistemas", "Subsistemas" in status)

# Report sin datos
pp_empty = PerformanceProfiler()
report_empty = pp_empty.generate_report()
test("Report vacio", "Sin datos" in report_empty)


# ============================================================
# TEST 30: Imports v1.9
# ============================================================
print("\n=== TEST: Imports v1.9 ===")

try:
    from core.task_scheduler import TaskScheduler, ScheduledTask, ExecutionLog
    test("Import TaskScheduler", True)
except ImportError:
    test("Import TaskScheduler", False)

try:
    from core.config_manager import ConfigManager, ConfigProfile, ConfigDiff
    test("Import ConfigManager", True)
except ImportError:
    test("Import ConfigManager", False)

try:
    from core.performance_profiler import PerformanceProfiler, TimingRecord
    test("Import PerformanceProfiler", True)
except ImportError:
    test("Import PerformanceProfiler", False)


# ============================================================
# TEST 31: Genesis imports v1.9
# ============================================================
print("\n=== TEST: Genesis imports v1.9 ===")
import genesis as g_module
source = open(g_module.__file__, "r", encoding="utf-8").read()

test("genesis.py importa TaskScheduler", "from core.task_scheduler import TaskScheduler" in source)
test("genesis.py importa ConfigManager", "from core.config_manager import ConfigManager" in source)
test("genesis.py importa PerformanceProfiler", "from core.performance_profiler import PerformanceProfiler" in source)


# ============================================================
# TEST 32: Comandos v1.9 en genesis.py
# ============================================================
print("\n=== TEST: Comandos v1.9 ===")

test("Comando /scheduler en source", "/scheduler" in source)
test("Comando /sched en source", "/sched" in source)
test("Comando /scheduler tasks en source", "/scheduler tasks" in source)
test("Comando /scheduler toggle en source", "/scheduler toggle" in source)
test("Comando /scheduler run en source", "/scheduler run" in source)
test("Comando /config en source", '"/config"' in source or "== \"/config\"" in source)
test("Comando /config save en source", "/config save" in source)
test("Comando /config load en source", "/config load" in source)
test("Comando /config compare en source", "/config compare" in source)
test("Comando /profiler en source", "/profiler" in source)
test("Comando /perf en source", "/perf" in source)
test("Comando /profiler bottlenecks en source", "/profiler bottlenecks" in source)


# ============================================================
# TEST 33: Status v1.9
# ============================================================
print("\n=== TEST: Status v1.9 ===")

test("SCHEDULER en status", "SCHEDULER" in source)
test("CONFIG MANAGER en status", "CONFIG MANAGER" in source)
test("PROFILER en status", "PROFILER" in source)


# ============================================================
# TEST 34: Help v1.9
# ============================================================
print("\n=== TEST: Help v1.9 ===")

test("Help TASK SCHEDULER", "TASK SCHEDULER" in source)
test("Help CONFIG MANAGER", "CONFIG MANAGER" in source)
test("Help PERFORMANCE PROFILER", "PERFORMANCE PROFILER" in source)
test("Help /scheduler tasks", "/scheduler tasks" in source)
test("Help /config save", "/config save" in source)
test("Help /profiler bottlenecks", "/profiler bottlenecks" in source)


# ============================================================
# TEST 35: Config version
# ============================================================
print("\n=== TEST: Config version ===")
import importlib
import config
importlib.reload(config)
test("Version >= 1.9.0", config.GENESIS_VERSION >= "1.9.0")


# ============================================================
# TEST 36: Edge cases
# ============================================================
print("\n=== TEST: Edge cases ===")

# TaskScheduler toggle inexistente
ts_edge = TaskScheduler()
result = ts_edge.toggle_task("nope")
test("Toggle task inexistente", "no encontrada" in result)

# Set interval inexistente
result = ts_edge.set_interval("nope", 30)
test("Set interval inexistente", "no encontrada" in result)

# Profiler start/stop disabled
pp_edge = PerformanceProfiler()
pp_edge.enabled = False
pp_edge.start("disabled")
pp_edge.record_direct("disabled", 100.0)
test("Profiler disabled no registra", "disabled" not in pp_edge.records)

# ConfigManager empty list
cm_edge = ConfigManager(base_dir=tempfile.mkdtemp())
listing = cm_edge.list_profiles()
test("List vacia", "No hay perfiles" in listing)

# TimingRecord min/max edge
tr_edge = TimingRecord(name="edge")
stats_edge = tr_edge.get_stats()
test("Stats min sin datos = 0", stats_edge["min_ms"] == 0)
test("Stats max sin datos = 0", stats_edge["max_ms"] == 0)


# ============================================================
# Resultado final
# ============================================================
print(f"\n{'='*60}")
print(f"  RESULTADO: {_passed} passed, {_failed} failed de {_passed + _failed} tests")
print(f"{'='*60}")

if _failed > 0:
    sys.exit(1)
