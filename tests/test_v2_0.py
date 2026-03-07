"""
Tests para Genesis v2.0.0
- EmbeddingsEngine (VectorStore, TFIDFEmbedder, busqueda semantica)
- DashboardAPI (collectors, snapshots, timelines, categorias)
- AutonomousMode (acciones, SafetyGuard, tick, ciclos)
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
# TEST 1: VectorStore basico
# ============================================================
print("\n=== TEST: VectorStore ===")
import numpy as np
from core.embeddings_engine import VectorStore, TFIDFEmbedder, EmbeddingsEngine

vs = VectorStore()
test("VectorStore vacio", vs.count() == 0)
test("VectorStore dimension inicial 0", vs.dimension == 0)

# Agregar vectores
v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
v3 = np.array([0.9, 0.1, 0.0], dtype=np.float32)

vs.add("doc1", v1, {"text": "primer doc"})
vs.add("doc2", v2, {"text": "segundo doc"})
vs.add("doc3", v3, {"text": "tercer doc"})

test("VectorStore count 3", vs.count() == 3)
test("VectorStore dimension 3", vs.dimension == 3)

# Buscar — doc1 y doc3 deben ser similares
results = vs.search(v1, top_k=3)
test("Search retorna resultados", len(results) > 0)
test("Search primer resultado es doc1 (identico)", results[0]["id"] == "doc1")
test("Search doc1 score = 1.0", results[0]["score"] == 1.0)
test("Search segundo resultado es doc3 (similar)", results[1]["id"] == "doc3")
test("Search doc3 score > 0.9", results[1]["score"] > 0.9)
test("Search doc2 tiene bajo score", results[2]["score"] < 0.2)

# Buscar con min_score
results_filtered = vs.search(v1, top_k=3, min_score=0.5)
test("Search con min_score filtra", len(results_filtered) == 2)

# Get vector
got = vs.get("doc1")
test("Get vector existente", got is not None)
test("Get vector correcto", np.allclose(got, v1))
test("Get vector inexistente None", vs.get("nope") is None)

# Remove
ok = vs.remove("doc2")
test("Remove retorna True", ok is True)
test("Remove decrementa count", vs.count() == 2)
test("Remove inexistente retorna False", vs.remove("nope") is False)

# Clear
vs.clear()
test("Clear limpia todo", vs.count() == 0)
test("Clear resetea dimension", vs.dimension == 0)


# ============================================================
# TEST 2: VectorStore persistencia
# ============================================================
print("\n=== TEST: VectorStore Persistencia ===")
tmp_dir = tempfile.mkdtemp()
try:
    store_path = os.path.join(tmp_dir, "test_store")
    vs_save = VectorStore(store_path=store_path)
    vs_save.add("a", np.array([1.0, 0.0], dtype=np.float32), {"text": "hola"})
    vs_save.add("b", np.array([0.0, 1.0], dtype=np.float32), {"text": "mundo"})
    vs_save.save()

    test("Save crea directorio", os.path.exists(store_path))
    test("Save crea metadata.json", os.path.exists(os.path.join(store_path, "metadata.json")))
    test("Save crea vectors.npy", os.path.exists(os.path.join(store_path, "vectors.npy")))

    # Cargar en nuevo store
    vs_load = VectorStore(store_path=store_path)
    test("Load restaura count", vs_load.count() == 2)
    test("Load restaura dimension", vs_load.dimension == 2)
    test("Load restaura vectores", vs_load.get("a") is not None)
    test("Load restaura metadata", vs_load.metadata.get("a", {}).get("text") == "hola")
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 3: TFIDFEmbedder
# ============================================================
print("\n=== TEST: TFIDFEmbedder ===")
embedder = TFIDFEmbedder(dimension=128)
test("Embedder name", embedder.name == "tfidf-fallback")
test("Embedder dimension", embedder.dimension == 128)

# Encode
vec1 = embedder.encode("Los coches electricos son el futuro")
test("Encode retorna ndarray", isinstance(vec1, np.ndarray))
test("Encode dimension correcta", len(vec1) == 128)
test("Encode normalizado (norma ~1)", abs(np.linalg.norm(vec1) - 1.0) < 0.01)

# Encode vacio
vec_empty = embedder.encode("")
test("Encode vacio es zero vector", np.linalg.norm(vec_empty) == 0.0)

# Encode batch
vecs = embedder.encode_batch(["hola mundo", "foo bar", "test test"])
test("Encode batch retorna lista", len(vecs) == 3)
test("Encode batch cada uno es ndarray", all(isinstance(v, np.ndarray) for v in vecs))

# Similitud: textos parecidos deberian ser mas similares
v_auto = embedder.encode("auto coche vehiculo")
v_auto2 = embedder.encode("auto coche transporte")
v_comida = embedder.encode("pizza pasta comida italiana")

sim_auto = float(np.dot(v_auto, v_auto2) / (np.linalg.norm(v_auto) * np.linalg.norm(v_auto2)))
sim_diff = float(np.dot(v_auto, v_comida) / (np.linalg.norm(v_auto) * np.linalg.norm(v_comida)))
test("Similitud textos relacionados > no relacionados", sim_auto > sim_diff)

# Hash trick: mismo token siempre va al mismo indice
idx1 = embedder._hash_token("python")
idx2 = embedder._hash_token("python")
test("Hash determinista", idx1 == idx2)
test("Hash en rango", 0 <= idx1 < 128)


# ============================================================
# TEST 4: EmbeddingsEngine
# ============================================================
print("\n=== TEST: EmbeddingsEngine ===")
tmp_dir = tempfile.mkdtemp()
try:
    engine = EmbeddingsEngine(base_dir=tmp_dir)
    # Sin sentence-transformers instalado, debe usar TF-IDF fallback
    test("Engine backend definido", engine.backend != "none")
    test("Engine model_name", engine.model_name == "all-MiniLM-L6-v2")

    # add_text
    ok1 = engine.add_text("t1", "Los coches electricos son el futuro del transporte")
    ok2 = engine.add_text("t2", "La pizza italiana es deliciosa")
    ok3 = engine.add_text("t3", "Vehiculos autonomos cambiaran las ciudades")
    test("add_text retorna True", ok1 and ok2 and ok3)
    test("Store tiene 3 docs", engine.store.count() == 3)

    # search
    results = engine.search("transporte del futuro", top_k=3)
    test("Search retorna resultados", len(results) > 0)
    test("Search total_searches incrementa", engine.total_searches == 1)
    test("Search total_encoded incrementa", engine.total_encoded > 0)

    # add_texts_batch
    items = [
        {"id": "b1", "text": "Machine learning con Python", "source": "test"},
        {"id": "b2", "text": "Deep learning y redes neuronales", "source": "test"},
    ]
    added = engine.add_texts_batch(items)
    test("Batch agrega 2", added == 2)
    test("Store tiene 5 docs", engine.store.count() == 5)

    # get_similar
    similar = engine.get_similar("t1", top_k=2)
    test("get_similar retorna lista", isinstance(similar, list))
    test("get_similar no incluye a si mismo", all(r["id"] != "t1" for r in similar))

    # get_similar inexistente
    similar_none = engine.get_similar("nope")
    test("get_similar inexistente vacio", len(similar_none) == 0)

    # Stats
    stats = engine.get_stats()
    test("Stats tiene backend", "backend" in stats)
    test("Stats tiene documents", stats["documents"] == 5)
    test("Stats tiene total_encoded", stats["total_encoded"] > 0)
    test("Stats tiene avg_encode_ms", "avg_encode_ms" in stats)

    # Status string
    status = engine.status()
    test("Status contiene Backend", "Backend" in status)

    # Report
    report = engine.generate_report()
    test("Report contiene EMBEDDINGS", "EMBEDDINGS" in report)
    test("Report contiene backend", engine.backend in report)

    # Save
    engine.save()
    store_dir = os.path.join(tmp_dir, "embeddings_data", "vector_store")
    test("Save persiste a disco", os.path.exists(store_dir))

    # Remove
    ok = engine.remove("t2")
    test("Remove retorna True", ok is True)
    test("Remove decrementa", engine.store.count() == 4)

    # Clear
    engine.clear()
    test("Clear limpia store", engine.store.count() == 0)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 5: MetricCollector
# ============================================================
print("\n=== TEST: MetricCollector ===")
from core.dashboard_api import MetricCollector, MetricTimeline, DashboardAPI

mc = MetricCollector("test_collector", lambda: {"cpu": 42, "mem": 80}, category="monitoring")
test("Collector name", mc.name == "test_collector")
test("Collector category", mc.category == "monitoring")
test("Collector initial count 0", mc.collect_count == 0)

data = mc.collect()
test("Collect retorna dict", isinstance(data, dict))
test("Collect cpu=42", data["cpu"] == 42)
test("Collect incrementa count", mc.collect_count == 1)
test("Collect guarda last_value", mc.last_value == data)

# Collector con error
mc_err = MetricCollector("error_col", lambda: 1/0)
data_err = mc_err.collect()
test("Collect con error tiene _error", "_error" in data_err)
test("Collect con error incrementa errors", mc_err.errors == 1)

# Collector retorna non-dict
mc_str = MetricCollector("str_col", lambda: "hello")
data_str = mc_str.collect()
test("Collect non-dict envuelve en dict", data_str == {"value": "hello"})


# ============================================================
# TEST 6: MetricTimeline
# ============================================================
print("\n=== TEST: MetricTimeline ===")
tl = MetricTimeline("test_tl", max_points=5)
test("Timeline vacia", len(tl.points) == 0)
test("Timeline get_latest None", tl.get_latest() is None)

tl.add_point({"cpu": 10})
tl.add_point({"cpu": 20})
tl.add_point({"cpu": 30})
test("Timeline tiene 3 puntos", len(tl.points) == 3)

latest = tl.get_latest()
test("Latest tiene values", latest is not None and latest["values"]["cpu"] == 30)

series = tl.get_series("cpu")
test("Series tiene 3 puntos", len(series) == 3)
test("Series primer valor 10", series[0]["value"] == 10)
test("Series ultimo valor 30", series[2]["value"] == 30)

# Serie inexistente
series_nope = tl.get_series("nope")
test("Serie inexistente vacia", len(series_nope) == 0)

# Max points
for i in range(10):
    tl.add_point({"cpu": 100 + i})
test("Max points respetado", len(tl.points) == 5)

# Get range
now = time.time()
tl2 = MetricTimeline("tl2")
tl2.add_point({"x": 1})
time.sleep(0.01)
mid = time.time()
tl2.add_point({"x": 2})
range_all = tl2.get_range(now - 1)
test("Get range retorna todos", len(range_all) == 2)
range_after = tl2.get_range(mid)
test("Get range filtra por tiempo", len(range_after) == 1)


# ============================================================
# TEST 7: DashboardAPI
# ============================================================
print("\n=== TEST: DashboardAPI ===")
dash = DashboardAPI()
test("Dashboard collectors vacio", len(dash.collectors) == 0)
test("Dashboard snapshots vacio", len(dash.snapshots) == 0)

# Register collectors
result = dash.register("brain", lambda: {"tokens": 1000, "model": "dolphin"}, "core")
test("Register retorna string", "registrado" in result)
dash.register("memory", lambda: {"long_term": 50, "short_term": 10}, "memory")
dash.register("profiler", lambda: {"ops": 42}, "monitoring")

test("3 collectors registrados", len(dash.collectors) == 3)

# Collect all
snapshot = dash.collect_all()
test("Collect retorna dict", isinstance(snapshot, dict))
test("Snapshot tiene timestamp", "timestamp" in snapshot)
test("Snapshot tiene subsystems", "subsystems" in snapshot)
test("Snapshot tiene categories", "categories" in snapshot)
test("Snapshot brain data", snapshot["subsystems"]["brain"]["data"]["tokens"] == 1000)
test("Snapshot por categoria", "core" in snapshot["categories"])
test("Total snapshots incrementa", dash.total_snapshots == 1)

# Get snapshot
snap2 = dash.get_snapshot()
test("Get snapshot retorna ultimo", snap2 == snapshot)

# Get subsystem
sub = dash.get_subsystem("brain")
test("Get subsystem retorna data", sub.get("tokens") == 1000)
sub_err = dash.get_subsystem("nope")
test("Get subsystem inexistente error", "error" in sub_err)

# Get timeline
dash.collect_all()  # Segundo snapshot para tener 2 puntos
timeline = dash.get_timeline("brain", "tokens")
test("Timeline tiene puntos", len(timeline) >= 2)
test("Timeline valores correctos", timeline[0]["value"] == 1000)

# Timeline inexistente
tl_nope = dash.get_timeline("nope", "x")
test("Timeline inexistente vacia", len(tl_nope) == 0)

# Categories
cats = dash.get_categories()
test("Categories tiene core", "core" in cats)
test("Categories core tiene brain", "brain" in cats["core"]["subsystems"])

# Summary
summary = dash.get_summary()
test("Summary tiene uptime", "uptime_seconds" in summary)
test("Summary tiene collectors count", summary["registered_collectors"] == 3)

# Generate dashboard text
dash_text = dash.generate_dashboard()
test("Dashboard text contiene GENESIS", "GENESIS" in dash_text)
test("Dashboard text contiene CORE", "CORE" in dash_text)

# Export JSON
json_str = dash.export_json()
test("Export JSON parseable", json.loads(json_str) is not None)

# Collector stats
cstats = dash.get_collector_stats()
test("Collector stats lista", len(cstats) == 3)
test("Collector stats tiene name", cstats[0]["name"] is not None)

# Unregister
ok = dash.unregister("profiler")
test("Unregister retorna True", ok is True)
test("Unregister decrementa", len(dash.collectors) == 2)
test("Unregister inexistente False", dash.unregister("nope") is False)

# Status
status = dash.status()
test("Status contiene Collectors", "Collectors" in status)


# ============================================================
# TEST 8: AutonomousAction
# ============================================================
print("\n=== TEST: AutonomousAction ===")
from core.autonomous_mode import AutonomousAction, SafetyGuard, AutonomousMode

counter = {"n": 0}
def increment():
    counter["n"] += 1
    return f"Count: {counter['n']}"

action = AutonomousAction(
    name="test_action",
    callback=increment,
    priority=7,
    cooldown_seconds=0.1,
    description="Accion de prueba",
    safe=True,
)
test("Action name", action.name == "test_action")
test("Action priority", action.priority == 7)
test("Action enabled", action.enabled is True)
test("Action safe", action.safe is True)
test("Action run_count 0", action.run_count == 0)
test("Action is_eligible inicialmente", action.is_eligible() is True)

# Execute
result = action.execute()
test("Execute retorna dict", isinstance(result, dict))
test("Execute success True", result["success"] is True)
test("Execute result contiene Count", "Count" in result["result"])
test("Execute run_count 1", action.run_count == 1)
test("Execute success_count 1", action.success_count == 1)
test("Execute duration_ms > 0", result["duration_ms"] >= 0)
test("Counter incremento", counter["n"] == 1)

# Cooldown
test("Despues de ejecutar, no eligible", action.is_eligible() is False)
time.sleep(0.15)
test("Despues de cooldown, eligible", action.is_eligible() is True)

# Execute con error
def fail_action():
    raise ValueError("Error de prueba")

action_fail = AutonomousAction("fail", fail_action, cooldown_seconds=0)
result_fail = action_fail.execute()
test("Execute con error success False", result_fail["success"] is False)
test("Execute con error tiene error msg", "Error de prueba" in result_fail["error"])
test("Failure count incrementa", action_fail.failure_count == 1)

# Disabled action
action.enabled = False
test("Disabled not eligible", action.is_eligible() is False)
action.enabled = True


# ============================================================
# TEST 9: SafetyGuard
# ============================================================
print("\n=== TEST: SafetyGuard ===")
guard = SafetyGuard()
test("Guard max_cycles default", guard.max_cycles == 1000)
test("Guard max_duration default", guard.max_duration_minutes == 120)
test("Guard max_consecutive_failures", guard.max_consecutive_failures == 5)
test("Guard forbidden actions", "delete_files" in guard.forbidden_actions)

# Check action safe
safe_action = AutonomousAction("ok_action", lambda: None, safe=True)
ok, msg = guard.check_action(safe_action)
test("Check safe action OK", ok is True)

# Check forbidden action
forbidden_action = AutonomousAction("delete_files", lambda: None, safe=True)
ok, msg = guard.check_action(forbidden_action)
test("Check forbidden action blocked", ok is False)
test("Violation registrada", len(guard.violations) == 1)

# Check non-safe action
unsafe_action = AutonomousAction("risky", lambda: None, safe=False)
ok, msg = guard.check_action(unsafe_action)
test("Check non-safe blocked", ok is False)

# Check cycle — normal
start = time.time()
ok, msg = guard.check_cycle(0, start, 0)
test("Cycle check normal OK", ok is True)

# Check cycle — max cycles
ok, msg = guard.check_cycle(1000, start, 0)
test("Cycle max cycles reached", ok is False)

# Check cycle — max actions per cycle
ok, msg = guard.check_cycle(0, start, 10)
test("Cycle max actions reached", ok is False)

# Record results
guard.record_result(True)
test("Record success resets failures", guard.consecutive_failures == 0)

for _ in range(5):
    guard.record_result(False)
test("5 failures consecutivas", guard.consecutive_failures == 5)
ok, msg = guard.check_cycle(0, start, 0)
test("Cycle bloqueado por failures", ok is False)

# Reset
guard.reset()
test("Reset limpia failures", guard.consecutive_failures == 0)
test("Reset limpia violations", len(guard.violations) == 0)


# ============================================================
# TEST 10: AutonomousMode basico
# ============================================================
print("\n=== TEST: AutonomousMode ===")
auto = AutonomousMode()
test("Auto inactivo", auto.active is False)
test("Auto sin acciones", len(auto.actions) == 0)

# Register actions
cnt = {"a": 0, "b": 0}
result = auto.register_action("action_a", lambda: cnt.update(a=cnt["a"]+1), priority=8, cooldown_seconds=0)
test("Register retorna string", "registrada" in result)
auto.register_action("action_b", lambda: cnt.update(b=cnt["b"]+1), priority=3, cooldown_seconds=0)
test("2 acciones registradas", len(auto.actions) == 2)

# Register duplicada
dup = auto.register_action("action_a", lambda: None)
test("Register duplicada rechazada", "ya existe" in dup)

# Start
start_msg = auto.start(max_cycles=50, max_duration_minutes=5)
test("Start activa", auto.active is True)
test("Start retorna info", "INICIADO" in start_msg)
test("Guard limites ajustados", auto.guard.max_cycles == 50)

# Start ya activo
already = auto.start()
test("Start ya activo avisa", "ya esta activo" in already)

# Tick
results = auto.tick()
test("Tick retorna resultados", len(results) > 0)
test("Tick ejecuta action_a primero (mayor prioridad)", results[0]["action"] == "action_a")
test("Total cycles incrementa", auto.total_cycles == 1)
test("Total actions incrementa", auto.total_actions > 0)

# Otro tick
results2 = auto.tick()
test("Segundo tick funciona", len(results2) > 0)

# Pause
pause_msg = auto.pause()
test("Pause responde", "PAUSADO" in pause_msg)
test("Paused flag", auto.paused is True)

# Tick en pausa — sin acciones
results_paused = auto.tick()
test("Tick en pausa vacio", len(results_paused) == 0)

# Resume
resume_msg = auto.resume()
test("Resume responde", "REANUDADO" in resume_msg)
test("Resumed flag", auto.paused is False)

# Toggle action
toggle_msg = auto.toggle_action("action_b")
test("Toggle desactiva", "desactivada" in toggle_msg)

# Toggle inexistente
toggle_nope = auto.toggle_action("nope")
test("Toggle inexistente avisa", "no encontrada" in toggle_nope)

# Remove action
remove_msg = auto.remove_action("action_b")
test("Remove retorna string", "eliminada" in remove_msg)
test("Remove decrementa", len(auto.actions) == 1)
test("Remove inexistente", "no encontrada" in auto.remove_action("nope"))

# Stop
stop_msg = auto.stop("test_done")
test("Stop desactiva", auto.active is False)
test("Stop retorna info", "DETENIDO" in stop_msg)
test("Stop reason guardada", auto.stop_reason == "test_done")

# Stop ya inactivo
already_stopped = auto.stop()
test("Stop inactivo avisa", "no esta activo" in already_stopped)

# Pause/resume inactivo
test("Pause inactivo", "no esta activo" in auto.pause())
test("Resume inactivo", "no esta activo" in auto.resume())


# ============================================================
# TEST 11: AutonomousMode auto-stop
# ============================================================
print("\n=== TEST: AutonomousMode Auto-Stop ===")
auto2 = AutonomousMode()
auto2.register_action("tick_action", lambda: "ok", cooldown_seconds=0)
auto2.start(max_cycles=3)

for i in range(5):
    auto2.tick()

test("Auto-stop por max_cycles", auto2.active is False)
test("Auto-stop reason", "ciclos" in auto2.stop_reason.lower() or "Limite" in auto2.stop_reason)


# ============================================================
# TEST 12: AutonomousMode consecutive failures
# ============================================================
print("\n=== TEST: AutonomousMode Consecutive Failures ===")
auto3 = AutonomousMode()
auto3.register_action("fail_action", lambda: 1/0, cooldown_seconds=0)
auto3.start(max_cycles=100)

for i in range(10):
    auto3.tick()

test("Auto-stop por failures", auto3.active is False)
test("Stop reason failures", "fallas" in auto3.stop_reason.lower() or "consecutivas" in auto3.stop_reason.lower())


# ============================================================
# TEST 13: AutonomousMode reportes
# ============================================================
print("\n=== TEST: AutonomousMode Reportes ===")
auto4 = AutonomousMode()
auto4.register_action("rep_action", lambda: "ok", priority=5, cooldown_seconds=0, description="Accion de reporte")
auto4.start()
auto4.tick()
auto4.tick()
auto4.stop()

# Action list
action_list = auto4.get_action_list()
test("Action list contiene nombre", "rep_action" in action_list)
test("Action list contiene prioridad", "P5" in action_list)

# Log report
log = auto4.get_log_report(5)
test("Log contiene acciones", "rep_action" in log)

# Generate report
report = auto4.generate_report()
test("Report contiene AUTONOMOUS", "AUTONOMOUS" in report)
test("Report contiene ACCIONES", "ACCIONES" in report)
test("Report contiene LOG", "LOG" in report)

# Status
status = auto4.status()
test("Status contiene Estado", "Estado" in status)
test("Status contiene Ciclos", "Ciclos" in status)

# Empty action list
auto5 = AutonomousMode()
empty_list = auto5.get_action_list()
test("Action list vacio msg", "No hay" in empty_list)

# Empty log
empty_log = auto5.get_log_report()
test("Log vacio msg", "Sin acciones" in empty_log)


# ============================================================
# TEST 14: SafetyGuard forbidden actions
# ============================================================
print("\n=== TEST: SafetyGuard Forbidden Actions ===")
auto6 = AutonomousMode()
auto6.register_action("delete_files", lambda: "deleted!", cooldown_seconds=0)
auto6.register_action("safe_check", lambda: "healthy", cooldown_seconds=0)
auto6.start()

results = auto6.tick()
# Solo safe_check deberia ejecutarse, delete_files es forbidden
action_names = [r["action"] for r in results]
test("Forbidden action no se ejecuta", "delete_files" not in action_names)
test("Safe action si se ejecuta", "safe_check" in action_names)
auto6.stop()


# ============================================================
# TEST 15: EmbeddingsEngine encode
# ============================================================
print("\n=== TEST: EmbeddingsEngine Encode ===")
tmp_dir = tempfile.mkdtemp()
try:
    eng = EmbeddingsEngine(base_dir=tmp_dir)

    v = eng.encode("Hola mundo")
    test("Encode retorna ndarray", isinstance(v, np.ndarray))
    test("Encode dimension > 0", len(v) > 0)
    test("total_encoded incrementa", eng.total_encoded == 1)

    batch = eng.encode_batch(["uno", "dos", "tres"])
    test("Encode batch retorna 3", len(batch) == 3)
    test("total_encoded batch suma", eng.total_encoded == 4)
    test("encode_time_ms > 0", eng.encode_time_ms > 0)
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 16: DashboardAPI max snapshots
# ============================================================
print("\n=== TEST: DashboardAPI Max Snapshots ===")
dash2 = DashboardAPI()
dash2.max_snapshots = 5
dash2.register("simple", lambda: {"x": 1})

for i in range(10):
    dash2.collect_all()

test("Max snapshots respetado", len(dash2.snapshots) == 5)
test("Total snapshots cuenta todas", dash2.total_snapshots == 10)


# ============================================================
# TEST 17: Integracion — imports en genesis.py
# ============================================================
print("\n=== TEST: Integracion imports ===")
genesis_path = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(genesis_path, "r", encoding="utf-8") as f:
    src = f.read()

test("Import EmbeddingsEngine", "from core.embeddings_engine import EmbeddingsEngine" in src)
test("Import DashboardAPI", "from core.dashboard_api import DashboardAPI" in src)
test("Import AutonomousMode", "from core.autonomous_mode import AutonomousMode" in src)


# ============================================================
# TEST 18: Integracion — init en genesis.py
# ============================================================
print("\n=== TEST: Integracion init ===")
test("Init self.embeddings", "self.embeddings = EmbeddingsEngine" in src)
test("Init self.dashboard", "self.dashboard = DashboardAPI" in src)
test("Init self.autonomous", "self.autonomous = AutonomousMode" in src)
test("Dashboard register collectors", "_register_dashboard_collectors" in src)


# ============================================================
# TEST 19: Integracion — comandos en genesis.py
# ============================================================
print("\n=== TEST: Integracion comandos ===")
# Embeddings commands
test("Comando /embeddings", '"/embeddings"' in src or "== \"/embeddings\"" in src)
test("Comando /emb", '"/emb"' in src)
test("Comando /embeddings add", '"/embeddings add "' in src or 'embeddings add' in src)
test("Comando /embeddings search", '"/embeddings search "' in src or 'embeddings search' in src)
test("Comando /embeddings similar", '"/embeddings similar "' in src or 'embeddings similar' in src)
test("Comando /embeddings save", '"embeddings save"' in src or '/embeddings save' in src)
test("Comando /embeddings clear", '"embeddings clear"' in src or '/embeddings clear' in src)

# Dashboard commands
test("Comando /dashboard", '"/dashboard"' in src or "== \"/dashboard\"" in src)
test("Comando /dash", '"/dash"' in src)
test("Comando /dashboard json", '"dashboard json"' in src or '/dashboard json' in src)
test("Comando /dashboard summary", '"dashboard summary"' in src or '/dashboard summary' in src)
test("Comando /dashboard categories", '"dashboard categories"' in src or '/dashboard categories' in src)
test("Comando /dashboard timeline", '"dashboard timeline"' in src or '/dashboard timeline' in src)

# Autonomous commands
test("Comando /autonomous", '"/autonomous"' in src or "== \"/autonomous\"" in src)
test("Comando /auto", '"/auto"' in src)
test("Comando /autonomous start", '"autonomous start"' in src or '/autonomous start' in src)
test("Comando /autonomous stop", '"autonomous stop"' in src or '/autonomous stop' in src)
test("Comando /autonomous pause", '"autonomous pause"' in src or '/autonomous pause' in src)
test("Comando /autonomous resume", '"autonomous resume"' in src or '/autonomous resume' in src)
test("Comando /autonomous actions", '"autonomous actions"' in src or '/autonomous actions' in src)
test("Comando /autonomous log", '"autonomous log"' in src or '/autonomous log' in src)
test("Comando /autonomous tick", '"autonomous tick"' in src or '/autonomous tick' in src)


# ============================================================
# TEST 20: Integracion — status en genesis.py
# ============================================================
print("\n=== TEST: Integracion status ===")
test("Status EMBEDDINGS", '"EMBEDDINGS:"' in src or "EMBEDDINGS:" in src)
test("Status DASHBOARD", '"DASHBOARD:"' in src or "DASHBOARD:" in src)
test("Status AUTONOMOUS", '"AUTONOMOUS MODE:"' in src or "AUTONOMOUS" in src)


# ============================================================
# TEST 21: Integracion — help en genesis.py
# ============================================================
print("\n=== TEST: Integracion help ===")
test("Help EMBEDDINGS ENGINE", "EMBEDDINGS ENGINE" in src)
test("Help DASHBOARD API", "DASHBOARD API" in src)
test("Help AUTONOMOUS MODE", "AUTONOMOUS MODE" in src)
test("Help /emb add", "/embeddings add" in src)
test("Help /dashboard json", "/dashboard json" in src)
test("Help /autonomous start", "/autonomous start" in src)


# ============================================================
# TEST 22: Version bump
# ============================================================
print("\n=== TEST: Version ===")
import config
test("Version >= 2.0.0", config.GENESIS_VERSION >= "2.0.0")


# ============================================================
# TEST 23: Makefile actualizado
# ============================================================
print("\n=== TEST: Makefile ===")
makefile_path = os.path.join(os.path.dirname(__file__), "..", "Makefile")
with open(makefile_path, "r", encoding="utf-8") as f:
    makefile_src = f.read()

test("Makefile tiene test-v20", "test-v20" in makefile_src)
test("Makefile tiene test_v2_0.py", "test_v2_0.py" in makefile_src)
test("Makefile .PHONY v20", "test-v20" in makefile_src)


# ============================================================
# TEST 24: VectorStore dimension mismatch
# ============================================================
print("\n=== TEST: VectorStore Dimension Mismatch ===")
vs_dim = VectorStore()
vs_dim.add("ok", np.array([1.0, 2.0], dtype=np.float32))
try:
    vs_dim.add("bad", np.array([1.0, 2.0, 3.0], dtype=np.float32))
    test("Dimension mismatch lanza error", False)
except ValueError:
    test("Dimension mismatch lanza error", True)


# ============================================================
# TEST 25: VectorStore search con zero vector
# ============================================================
print("\n=== TEST: VectorStore Zero Vector ===")
vs_zero = VectorStore()
vs_zero.add("z1", np.array([1.0, 0.0], dtype=np.float32))
results_zero = vs_zero.search(np.array([0.0, 0.0], dtype=np.float32))
test("Search zero query vacio", len(results_zero) == 0)


# ============================================================
# TEST 26: DashboardAPI format_value
# ============================================================
print("\n=== TEST: DashboardAPI _format_value ===")
d = DashboardAPI()
test("Format float", d._format_value(3.14159) == "3.1")
test("Format list", d._format_value([1, 2, 3]) == "(list)")
test("Format dict", d._format_value({"a": 1}) == "(dict)")
test("Format short string", d._format_value("hello") == "hello")
test("Format long string truncado", d._format_value("a" * 50).endswith("..."))


# ============================================================
# TEST 27: AutonomousMode log max
# ============================================================
print("\n=== TEST: AutonomousMode Log Max ===")
auto7 = AutonomousMode()
auto7.max_log = 5
auto7.register_action("log_test", lambda: "ok", cooldown_seconds=0)
auto7.start()

for i in range(10):
    auto7.tick()

test("Log max respetado", len(auto7.action_log) <= 5)
auto7.stop()


# ============================================================
# TEST 28: AutonomousAction stats acumulativas
# ============================================================
print("\n=== TEST: AutonomousAction Stats ===")
act_stats = AutonomousAction("stats_test", lambda: "ok", cooldown_seconds=0)
for _ in range(5):
    act_stats.execute()

test("Run count 5", act_stats.run_count == 5)
test("Success count 5", act_stats.success_count == 5)
test("Failure count 0", act_stats.failure_count == 0)
test("Total duration >= 0", act_stats.total_duration_ms >= 0)


# ============================================================
# TEST 29: DashboardAPI multiple collect_all
# ============================================================
print("\n=== TEST: DashboardAPI Multiple Collects ===")
dash3 = DashboardAPI()
counter_val = {"v": 0}
dash3.register("counter", lambda: {"val": counter_val["v"]})
counter_val["v"] = 10
dash3.collect_all()
counter_val["v"] = 20
dash3.collect_all()

tl = dash3.get_timeline("counter", "val")
test("Timeline refleja cambios", len(tl) == 2)
test("Timeline primer valor 10", tl[0]["value"] == 10)
test("Timeline segundo valor 20", tl[1]["value"] == 20)


# ============================================================
# TEST 30: EmbeddingsEngine data_dir creado
# ============================================================
print("\n=== TEST: EmbeddingsEngine Directories ===")
tmp_dir = tempfile.mkdtemp()
try:
    eng2 = EmbeddingsEngine(base_dir=tmp_dir)
    test("data_dir creado", os.path.exists(os.path.join(tmp_dir, "embeddings_data")))
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'='*50}")
print(f"  TESTS v2.0: {_passed} passed, {_failed} failed")
print(f"  TOTAL: {_passed + _failed}")
print(f"{'='*50}")

if _failed > 0:
    print(f"\n  [!] HAY {_failed} TESTS FALLIDOS")
    sys.exit(1)
else:
    print(f"\n  [OK] Todos los tests pasaron!")
    sys.exit(0)
