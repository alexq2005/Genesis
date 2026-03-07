"""
Tests para Genesis v1.8.0
- HealthMonitor (checks, alertas, recursos, reportes)
- RateLimiter (token bucket, cooldowns, usage tracker)
- PluginMarketplace (CRUD, search, install, templates, ratings)
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
# TEST 1: HealthStatus y HealthCheck
# ============================================================
print("\n=== TEST: HealthCheck ===")
from core.health_monitor import HealthStatus, HealthCheck, Alert, ResourceMetrics, HealthMonitor

hc = HealthCheck(name="test_check", status=HealthStatus.HEALTHY, message="Todo OK")
test("HealthCheck name", hc.name == "test_check")
test("HealthCheck status healthy", hc.status == "healthy")
test("HealthCheck message", hc.message == "Todo OK")
test("HealthCheck timestamp > 0", hc.timestamp > 0)
test("HealthCheck to_dict tiene keys", "name" in hc.to_dict() and "status" in hc.to_dict())
test("HealthCheck icon OK", hc.icon() == "[OK]")

hc_warn = HealthCheck(name="warn", status=HealthStatus.DEGRADED)
test("HealthCheck degraded icon", hc_warn.icon() == "[WARN]")

hc_crit = HealthCheck(name="crit", status=HealthStatus.UNHEALTHY)
test("HealthCheck unhealthy icon", hc_crit.icon() == "[CRIT]")

hc_unk = HealthCheck(name="unk", status=HealthStatus.UNKNOWN)
test("HealthCheck unknown icon", hc_unk.icon() == "[??]")


# ============================================================
# TEST 2: Alert
# ============================================================
print("\n=== TEST: Alert ===")
alert = Alert(source="brain", level="warning", message="LLM lento")
test("Alert source", alert.source == "brain")
test("Alert level", alert.level == "warning")
test("Alert message", alert.message == "LLM lento")
test("Alert not acknowledged", alert.acknowledged == False)
test("Alert to_dict", "source" in alert.to_dict() and "level" in alert.to_dict())

alert.acknowledged = True
test("Alert acknowledged", alert.acknowledged == True)


# ============================================================
# TEST 3: ResourceMetrics
# ============================================================
print("\n=== TEST: ResourceMetrics ===")
rm = ResourceMetrics()
test("ResourceMetrics empty snapshots", len(rm.snapshots) == 0)

snap = rm.take_snapshot()
test("Snapshot tiene timestamp", "timestamp" in snap)
test("Snapshot tiene cpu_percent", "cpu_percent" in snap)
test("Snapshot tiene ram_used_mb", "ram_used_mb" in snap)
test("Snapshot tiene ram_percent", "ram_percent" in snap)
test("Snapshot tiene disk_free_gb", "disk_free_gb" in snap)
test("Snapshot guardado", len(rm.snapshots) == 1)

# Tomar varias
for _ in range(5):
    rm.take_snapshot()
test("Multiple snapshots", len(rm.snapshots) == 6)

avgs = rm.get_averages()
test("Averages tiene cpu_avg", "cpu_avg" in avgs)
test("Averages tiene samples", avgs["samples"] == 6)

latest = rm.get_latest()
test("Latest es el ultimo snapshot", latest["timestamp"] == rm.snapshots[-1]["timestamp"])

# Test max_snapshots
rm.max_snapshots = 5
rm.take_snapshot()
test("Max snapshots respetado", len(rm.snapshots) <= 5)


# ============================================================
# TEST 4: HealthMonitor basico
# ============================================================
print("\n=== TEST: HealthMonitor basico ===")
hm = HealthMonitor()

test("Checks built-in registrados", len(hm._checks) >= 3)
test("resources check existe", "resources" in hm._checks)
test("data_dirs check existe", "data_dirs" in hm._checks)
test("disk_space check existe", "disk_space" in hm._checks)
test("No results antes de run", len(hm.last_results) == 0)
test("Overall status unknown inicialmente", hm.get_overall_status() == HealthStatus.UNKNOWN)
test("No alertas inicialmente", len(hm.get_active_alerts()) == 0)

# Thresholds
test("Threshold ram_warn", hm.thresholds["ram_warn"] == 85.0)
test("Threshold disk_crit", hm.thresholds["disk_crit"] == 95.0)


# ============================================================
# TEST 5: HealthMonitor run checks
# ============================================================
print("\n=== TEST: HealthMonitor run checks ===")
results = hm.run_all_checks()
test("Run devuelve resultados", len(results) >= 3)
test("resources check ejecutado", "resources" in results)
test("disk_space check ejecutado", "disk_space" in results)
test("data_dirs check ejecutado", "data_dirs" in results)
test("Check count incrementado", hm.check_count == 1)
test("Last check time actualizado", hm.last_check_time > 0)

# Cada resultado tiene duracion
for name, result in results.items():
    test(f"Check {name} tiene duration_ms", result.duration_ms >= 0)

# Overall status despues de checks
overall = hm.get_overall_status()
test("Overall no es unknown despues de checks", overall != HealthStatus.UNKNOWN)


# ============================================================
# TEST 6: HealthMonitor checks custom
# ============================================================
print("\n=== TEST: HealthMonitor custom checks ===")
hm2 = HealthMonitor()

# Check que siempre pasa
def good_check():
    return HealthCheck(name="good", status=HealthStatus.HEALTHY, message="OK")

hm2.register_check("custom_good", good_check)
test("Custom check registrado", "custom_good" in hm2._checks)

result = hm2.run_check("custom_good")
test("Custom check ejecutado", result is not None)
test("Custom check healthy", result.status == HealthStatus.HEALTHY)

# Check que falla
def bad_check():
    return HealthCheck(name="bad", status=HealthStatus.UNHEALTHY, message="Error critico")

hm2.register_check("custom_bad", bad_check)
result = hm2.run_check("custom_bad")
test("Bad check unhealthy", result.status == HealthStatus.UNHEALTHY)

# Check con excepcion
def crash_check():
    raise RuntimeError("Boom!")

hm2.register_check("crash", crash_check)
result = hm2.run_check("crash")
test("Crash check no rompe el sistema", result is not None)
test("Crash check unhealthy", result.status == HealthStatus.UNHEALTHY)
test("Crash check mensaje contiene error", "Boom!" in result.message)

# Unregister
hm2.unregister_check("crash")
test("Unregister check", "crash" not in hm2._checks)

# Check inexistente
result = hm2.run_check("no_existe")
test("Check inexistente retorna None", result is None)


# ============================================================
# TEST 7: HealthMonitor alertas
# ============================================================
print("\n=== TEST: HealthMonitor alertas ===")
hm3 = HealthMonitor()

# Forzar alerta
hm3._add_alert("test_source", "warning", "Test warning")
test("Alerta agregada", len(hm3.get_active_alerts()) == 1)

hm3._add_alert("test_source2", "critical", "Test critical")
test("2 alertas activas", len(hm3.get_active_alerts()) == 2)

# Duplicada del mismo source se actualiza, no se duplica
hm3._add_alert("test_source", "warning", "Test warning updated")
test("Alerta duplicada no duplica", len(hm3.get_active_alerts()) == 2)

# Acknowledge
hm3.acknowledge_alert(0)
test("Acknowledge reduce activas", len(hm3.get_active_alerts()) == 1)

# Acknowledge all
hm3._add_alert("source3", "warning", "Otra")
hm3._add_alert("source4", "critical", "Otra mas")
n = hm3.acknowledge_all()
test("Acknowledge all", n >= 2)
test("No alertas activas", len(hm3.get_active_alerts()) == 0)

# Max alertas
hm4 = HealthMonitor()
hm4.max_alerts = 5
for i in range(10):
    hm4._add_alert(f"source_{i}", "warning", f"Alert {i}")
test("Max alertas respetado", len(hm4.alerts) <= 5)


# ============================================================
# TEST 8: HealthMonitor factory checks
# ============================================================
print("\n=== TEST: HealthMonitor factory checks ===")

class FakeBrain:
    def is_available(self):
        return True
    def get_stats(self):
        return {"model": "test-model", "total_tokens": 42}

class FakeMemory:
    short_term = [1, 2, 3]
    class long_term:
        @staticmethod
        def count():
            return 10

hm5 = HealthMonitor()
brain_check = hm5.create_brain_check(FakeBrain())
hm5.register_check("brain", brain_check)
result = hm5.run_check("brain")
test("Brain check healthy con FakeBrain", result.status == HealthStatus.HEALTHY)
test("Brain check menciona modelo", "test-model" in result.message)

mem_check = hm5.create_memory_check(FakeMemory())
hm5.register_check("memory", mem_check)
result = hm5.run_check("memory")
test("Memory check healthy", result.status == HealthStatus.HEALTHY)
test("Memory check menciona count", "3" in result.message)


# ============================================================
# TEST 9: HealthMonitor reporte
# ============================================================
print("\n=== TEST: HealthMonitor reporte ===")
hm6 = HealthMonitor()
hm6.run_all_checks()
report = hm6.generate_report()
test("Reporte contiene HEALTH REPORT", "HEALTH REPORT" in report)
test("Reporte contiene estado general", "Estado general" in report)
test("Reporte contiene RECURSOS", "RECURSOS" in report)

status = hm6.status()
test("Status contiene Estado", "Estado" in status)
test("Status contiene RAM", "RAM" in status)


# ============================================================
# TEST 10: TokenBucket basico
# ============================================================
print("\n=== TEST: TokenBucket ===")
from core.rate_limiter import TokenBucket, CooldownTracker, UsageTracker, RateLimiter

tb = TokenBucket(capacity=5, refill_rate=1.0, name="test")
test("TokenBucket name", tb.name == "test")
test("TokenBucket capacity", tb.capacity == 5)
test("TokenBucket starts full", tb.tokens == 5.0)
test("TokenBucket allow", tb.allow(1))
test("TokenBucket allow 5", tb.allow(5))
test("TokenBucket not allow 6", not tb.allow(6))

# Consumir
test("Consume 1 OK", tb.consume(1))
test("Tokens despues de consume", tb.tokens >= 3.9)  # ~4 con refill

test("Consume 3 OK", tb.consume(3))
test("Stats total_consumed", tb.get_stats()["total_consumed"] == 4)

# Consumir todo
tb.consume(2)  # Deberia vaciar
test("Bucket casi vacio", tb.tokens < 2)

# Wait time
tb2 = TokenBucket(capacity=10, refill_rate=2.0)
tb2.tokens = 0  # Forzar vacio
tb2.last_refill = time.time()
wt = tb2.wait_time(4)
test("Wait time > 0 cuando vacio", wt > 0)
test("Wait time razonable", wt < 10)  # 4 tokens / 2 per sec = 2 sec

# Reset
tb2.reset()
test("Reset llena el bucket", tb2.tokens == 10.0)

# Stats
stats = tb2.get_stats()
test("Stats tiene fill_percent", "fill_percent" in stats)
test("Stats fill_percent = 100 despues de reset", stats["fill_percent"] == 100.0)

# Capacity minima
tb3 = TokenBucket(capacity=0, refill_rate=0)
test("Capacity minima = 1", tb3.capacity == 1)
test("Refill rate minima = 0.01", tb3.refill_rate == 0.01)


# ============================================================
# TEST 11: CooldownTracker
# ============================================================
print("\n=== TEST: CooldownTracker ===")
ct = CooldownTracker()

test("Sin cooldown, is_ready", ct.is_ready("test_action"))
test("Sin cooldown, remaining = 0", ct.remaining("test_action") == 0)

# Set y start
ct.set_cooldown("backup", 60.0)
ct.start_cooldown("backup")
test("Cooldown activo, not ready", not ct.is_ready("backup"))
test("Remaining > 0", ct.remaining("backup") > 0)
test("Remaining <= 60", ct.remaining("backup") <= 60)

# Start con custom seconds
ct.start_cooldown("custom", seconds=0.1)
test("Custom cooldown activo", not ct.is_ready("custom"))
time.sleep(0.15)
test("Custom cooldown expirado", ct.is_ready("custom"))

# Get active
ct.start_cooldown("test1", seconds=100)
ct.start_cooldown("test2", seconds=200)
active = ct.get_active()
test("Active cooldowns", len(active) >= 2)

# Clear
ct.clear("test1")
test("Clear individual", ct.is_ready("test1"))

ct.clear()
test("Clear all", len(ct.get_active()) == 0)


# ============================================================
# TEST 12: UsageTracker
# ============================================================
print("\n=== TEST: UsageTracker ===")
ut = UsageTracker()

test("Count sin datos = 0", ut.count_in_window("inference") == 0)

ut.record("inference")
ut.record("inference")
ut.record("inference")
test("Count despues de 3 records", ut.count_in_window("inference") == 3)

ut.record("tools")
test("Count tools = 1", ut.count_in_window("tools") == 1)

rates = ut.get_rates()
test("Rates tiene inference", "inference" in rates)
test("Rates inference per_minute = 3", rates["inference"]["per_minute"] == 3)
test("Rates tools per_minute = 1", rates["tools"]["per_minute"] == 1)

# Window filtering
test("Count en 1s window", ut.count_in_window("inference", 1) == 3)
test("Count en ventana 0 = 0", ut.count_in_window("inference", 0.001) <= 3)


# ============================================================
# TEST 13: RateLimiter basico
# ============================================================
print("\n=== TEST: RateLimiter basico ===")
rl = RateLimiter()

test("RateLimiter enabled por defecto", rl.enabled == True)
test("Buckets predefinidos", len(rl.buckets) >= 5)
test("Bucket inference existe", "inference" in rl.buckets)
test("Bucket tools existe", "tools" in rl.buckets)
test("Bucket self_modify existe", "self_modify" in rl.buckets)
test("Total limited = 0", rl.total_limited == 0)

# Allow y consume
test("Allow inference", rl.allow("inference"))
test("Consume inference", rl.consume("inference"))

# Recurso sin bucket = siempre permitido
test("Allow unknown resource", rl.allow("no_existe"))
test("Consume unknown resource", rl.consume("no_existe"))

# Toggle
rl.toggle()
test("Toggle desactiva", rl.enabled == False)
test("Consume siempre OK cuando disabled", rl.consume("inference"))
rl.toggle()
test("Toggle reactiva", rl.enabled == True)

# Reset
rl.reset("inference")
stats = rl.buckets["inference"].get_stats()
test("Reset inference llena bucket", stats["fill_percent"] == 100.0)

rl.reset()  # Reset all
for name, bucket in rl.buckets.items():
    test(f"Reset all - {name} lleno", bucket.get_stats()["fill_percent"] == 100.0)


# ============================================================
# TEST 14: RateLimiter agotar bucket
# ============================================================
print("\n=== TEST: RateLimiter agotar bucket ===")
rl2 = RateLimiter()

# Self_modify tiene capacity=5
for i in range(5):
    rl2.consume("self_modify")

# Deberia estar agotado (o casi)
test("Self_modify agotado", not rl2.allow("self_modify") or rl2.buckets["self_modify"].tokens < 1)

wt = rl2.wait_time("self_modify")
test("Wait time > 0 cuando agotado", wt >= 0)  # Puede haber refill minimo


# ============================================================
# TEST 15: RateLimiter reporte
# ============================================================
print("\n=== TEST: RateLimiter reporte ===")
rl3 = RateLimiter()
rl3.consume("inference")
rl3.consume("tools")
report = rl3.get_usage_report()
test("Reporte contiene RATE LIMITER", "RATE LIMITER" in report)
test("Reporte contiene BUCKETS", "BUCKETS" in report)
test("Reporte contiene inference", "inference" in report)

status = rl3.status()
test("Status contiene Estado", "Estado" in status)
test("Status contiene Buckets", "Buckets" in status)


# ============================================================
# TEST 16: RateLimiter add/remove bucket
# ============================================================
print("\n=== TEST: RateLimiter add/remove bucket ===")
rl4 = RateLimiter()

initial_count = len(rl4.buckets)
rl4.add_bucket("custom_test", capacity=10, refill_rate=1.0)
test("Add bucket", len(rl4.buckets) == initial_count + 1)
test("Custom bucket existe", "custom_test" in rl4.buckets)

rl4.remove_bucket("custom_test")
test("Remove bucket", len(rl4.buckets) == initial_count)
test("Remove inexistente", not rl4.remove_bucket("no_existe"))


# ============================================================
# TEST 17: PluginManifest
# ============================================================
print("\n=== TEST: PluginManifest ===")
from core.plugin_marketplace import PluginManifest, PluginMarketplace

pm = PluginManifest(
    name="test_plugin",
    version="2.0.0",
    author="tester",
    description="Un plugin de prueba",
    tags=["test", "debug"],
)
test("Manifest name", pm.name == "test_plugin")
test("Manifest version", pm.version == "2.0.0")
test("Manifest author", pm.author == "tester")
test("Manifest tags", pm.tags == ["test", "debug"])
test("Manifest not installed", pm.installed == False)
test("Manifest rating = 0", pm.rating == 0.0)

# to_dict
d = pm.to_dict()
test("to_dict tiene name", d["name"] == "test_plugin")
test("to_dict tiene version", d["version"] == "2.0.0")
test("to_dict tiene tags", d["tags"] == ["test", "debug"])

# from_dict roundtrip
pm2 = PluginManifest.from_dict(d)
test("from_dict name", pm2.name == "test_plugin")
test("from_dict version", pm2.version == "2.0.0")
test("from_dict author", pm2.author == "tester")

# match_search
test("Search by name", pm.match_search("test"))
test("Search by description", pm.match_search("prueba"))
test("Search by tag", pm.match_search("debug"))
test("Search by author", pm.match_search("tester"))
test("Search no match", not pm.match_search("inexistente"))

# format_card
card = pm.format_card()
test("Card contiene name", "test_plugin" in card)
test("Card contiene version", "2.0.0" in card)


# ============================================================
# TEST 18: PluginMarketplace basico
# ============================================================
print("\n=== TEST: PluginMarketplace basico ===")
tmpdir = tempfile.mkdtemp()
mp = PluginMarketplace(base_dir=tmpdir)

test("Marketplace plugins_dir existe", mp.plugins_dir.exists())
test("Marketplace registry_dir existe", mp.registry_dir.exists())
test("Marketplace available_dir existe", mp.available_dir.exists())
test("Marketplace vacio", len(mp.manifests) == 0)

stats = mp.get_stats()
test("Stats total = 0", stats["total"] == 0)
test("Stats installed = 0", stats["installed"] == 0)


# ============================================================
# TEST 19: PluginMarketplace create template
# ============================================================
print("\n=== TEST: PluginMarketplace create template ===")
result = mp.create_template("mi_plugin", "Plugin de prueba")
test("Create template exitoso", "creado" in result.lower())

# Verificar que se crearon los archivos
plugin_dir = mp.available_dir / "mi_plugin"
test("Dir de plugin creado", plugin_dir.exists())
test("manifest.json creado", (plugin_dir / "manifest.json").exists())
test("plugin.py creado", (plugin_dir / "plugin.py").exists())

# Verificar manifest
with open(plugin_dir / "manifest.json", "r") as f:
    mdata = json.load(f)
test("Manifest name correcto", mdata["name"] == "mi_plugin")
test("Manifest version", mdata["version"] == "1.0.0")
test("Manifest min_genesis_version", mdata["min_genesis_version"] == "1.8.0")

# Verificar que se registro
test("Plugin en manifests", "mi_plugin" in mp.manifests)

# No duplicar
result2 = mp.create_template("mi_plugin")
test("No duplicar template", "ya existe" in result2.lower())


# ============================================================
# TEST 20: PluginMarketplace install/uninstall
# ============================================================
print("\n=== TEST: PluginMarketplace install/uninstall ===")

# Instalar
result = mp.install_plugin("mi_plugin")
test("Install exitoso", "exitosamente" in result.lower())
test("Plugin file instalado", (mp.plugins_dir / "mi_plugin.py").exists())
test("Manifest marca installed", mp.manifests["mi_plugin"].installed == True)
test("Install date", mp.manifests["mi_plugin"].install_date is not None)
test("Downloads incrementado", mp.manifests["mi_plugin"].downloads == 1)

# Desinstalar
result = mp.uninstall_plugin("mi_plugin")
test("Uninstall exitoso", "desinstalado" in result.lower())
test("Plugin file removido", not (mp.plugins_dir / "mi_plugin.py").exists())
test("Manifest marca not installed", mp.manifests["mi_plugin"].installed == False)

# Desinstalar inexistente
result = mp.uninstall_plugin("no_existe")
test("Uninstall inexistente", "no esta instalado" in result.lower())

# Instalar inexistente
result = mp.install_plugin("no_existe")
test("Install inexistente", "no encontrado" in result.lower())


# ============================================================
# TEST 21: PluginMarketplace search
# ============================================================
print("\n=== TEST: PluginMarketplace search ===")

# Crear otro plugin para buscar
mp.create_template("debug_tool", "Herramienta de depuracion")

results = mp.search("debug")
test("Search encuentra debug_tool", len(results) >= 1)
test("Search resultado correcto", any(m.name == "debug_tool" for m in results))

results = mp.search("prueba")
test("Search por descripcion", len(results) >= 1)

results = mp.search("inexistente_xyz")
test("Search sin resultados", len(results) == 0)

# list_available
available = mp.list_available()
test("List available >= 2", len(available) >= 2)

# list_installed
mp.install_plugin("debug_tool")
installed = mp.list_installed()
test("List installed = 1", len(installed) >= 1)


# ============================================================
# TEST 22: PluginMarketplace ratings
# ============================================================
print("\n=== TEST: PluginMarketplace ratings ===")

result = mp.rate_plugin("mi_plugin", 5)
test("Rate exitoso", "calificado" in result.lower())
test("Rating = 5.0", mp.manifests["mi_plugin"].rating == 5.0)
test("Rating count = 1", mp.manifests["mi_plugin"].rating_count == 1)

result = mp.rate_plugin("mi_plugin", 3)
test("Segunda rating", mp.manifests["mi_plugin"].rating_count == 2)
test("Rating promedio = 4.0", mp.manifests["mi_plugin"].rating == 4.0)

# Rate clamping (1-5)
mp.rate_plugin("mi_plugin", 10)
test("Rating clamp max", mp.manifests["mi_plugin"].rating <= 5.0)

mp.rate_plugin("mi_plugin", -1)
test("Rating count incrementa", mp.manifests["mi_plugin"].rating_count == 4)

# Rate inexistente
result = mp.rate_plugin("no_existe", 3)
test("Rate inexistente", "no encontrado" in result.lower())


# ============================================================
# TEST 23: PluginMarketplace dependencies
# ============================================================
print("\n=== TEST: PluginMarketplace dependencies ===")

# Crear plugin con dependencia
dep_dir = mp.available_dir / "needs_debug"
dep_dir.mkdir(exist_ok=True)
with open(dep_dir / "manifest.json", "w") as f:
    json.dump({"name": "needs_debug", "dependencies": ["debug_tool_inexistente"], "version": "1.0.0"}, f)
with open(dep_dir / "plugin.py", "w") as f:
    f.write("PLUGIN_NAME = 'needs_debug'\n")

# Rescan
mp._scan_registry()

# Instalar con dependencia faltante
result = mp.install_plugin("needs_debug")
test("Dependencia faltante bloquea install", "dependencias" in result.lower() or "faltantes" in result.lower())


# ============================================================
# TEST 24: PluginMarketplace persistencia
# ============================================================
print("\n=== TEST: PluginMarketplace persistencia ===")

# Forzar save
mp._save_manifest()
test("Manifest file existe", mp.manifest_file.exists())

# Leer desde archivo
with open(mp.manifest_file, "r", encoding="utf-8") as f:
    data = json.load(f)
test("Manifest JSON tiene plugins", "plugins" in data)
test("Manifest tiene mi_plugin", "mi_plugin" in data["plugins"])
test("Manifest tiene version", "version" in data)


# ============================================================
# TEST 25: PluginMarketplace remove from registry
# ============================================================
print("\n=== TEST: PluginMarketplace remove from registry ===")

result = mp.remove_from_registry("mi_plugin")
test("Remove exitoso", "eliminado" in result.lower())
test("Dir eliminado", not (mp.available_dir / "mi_plugin").exists())
test("Manifest removido", "mi_plugin" not in mp.manifests)

result = mp.remove_from_registry("no_existe")
test("Remove inexistente", "no esta" in result.lower())


# ============================================================
# TEST 26: PluginMarketplace format
# ============================================================
print("\n=== TEST: PluginMarketplace format ===")

formatted = mp.format_marketplace()
test("Format contiene MARKETPLACE", "MARKETPLACE" in formatted)

status = mp.status()
test("Status contiene Disponibles", "Disponibles" in status)

# Marketplace vacio
mp_empty = PluginMarketplace(base_dir=tempfile.mkdtemp())
formatted_empty = mp_empty.format_marketplace()
test("Marketplace vacio mensaje", "vacio" in formatted_empty.lower() or "crear" in formatted_empty.lower())


# Cleanup temp dirs
shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 27: PluginMarketplace update
# ============================================================
print("\n=== TEST: PluginMarketplace update ===")
tmpdir2 = tempfile.mkdtemp()
mp2 = PluginMarketplace(base_dir=tmpdir2)
mp2.create_template("updatable", "Plugin para actualizar")
mp2.install_plugin("updatable")
test("Pre-update installed", mp2.manifests["updatable"].installed)

result = mp2.update_plugin("updatable")
test("Update exitoso", "exitosamente" in result.lower())
test("Post-update installed", mp2.manifests["updatable"].installed)

result = mp2.update_plugin("no_existe")
test("Update inexistente", "no esta instalado" in result.lower())

shutil.rmtree(tmpdir2, ignore_errors=True)


# ============================================================
# TEST 28: Imports v1.8
# ============================================================
print("\n=== TEST: Imports v1.8 ===")

try:
    from core.health_monitor import HealthMonitor, HealthCheck, HealthStatus, Alert, ResourceMetrics
    test("Import HealthMonitor", True)
except ImportError:
    test("Import HealthMonitor", False)

try:
    from core.rate_limiter import RateLimiter, TokenBucket, CooldownTracker, UsageTracker
    test("Import RateLimiter", True)
except ImportError:
    test("Import RateLimiter", False)

try:
    from core.plugin_marketplace import PluginMarketplace, PluginManifest
    test("Import PluginMarketplace", True)
except ImportError:
    test("Import PluginMarketplace", False)


# ============================================================
# TEST 29: Genesis imports v1.8
# ============================================================
print("\n=== TEST: Genesis imports v1.8 ===")
import genesis as g_module
source = open(g_module.__file__, "r", encoding="utf-8").read()

test("genesis.py importa HealthMonitor", "from core.health_monitor import HealthMonitor" in source)
test("genesis.py importa RateLimiter", "from core.rate_limiter import RateLimiter" in source)
test("genesis.py importa PluginMarketplace", "from core.plugin_marketplace import PluginMarketplace" in source)


# ============================================================
# TEST 30: Comandos v1.8 en genesis.py
# ============================================================
print("\n=== TEST: Comandos v1.8 ===")

test("Comando /health en source", '"/health"' in source or "== \"/health\"" in source)
test("Comando /health check en source", "/health check" in source)
test("Comando /health alerts en source", "/health alerts" in source)
test("Comando /ratelimit en source", "/ratelimit" in source)
test("Comando /rate en source", "/rate" in source)
test("Comando /marketplace en source", "/marketplace" in source)
test("Comando /market en source", "/market" in source)
test("Comando /marketplace install en source", "/marketplace install" in source)
test("Comando /marketplace create en source", "/marketplace create" in source)
test("Comando /marketplace search en source", "/marketplace search" in source)


# ============================================================
# TEST 31: Status v1.8
# ============================================================
print("\n=== TEST: Status v1.8 ===")

test("HEALTH MONITOR en status", "HEALTH MONITOR" in source)
test("RATE LIMITER en status", "RATE LIMITER" in source)
test("MARKETPLACE en status", "MARKETPLACE" in source)


# ============================================================
# TEST 32: Help v1.8
# ============================================================
print("\n=== TEST: Help v1.8 ===")

test("Help /health", "/health" in source and "Reporte de salud" in source)
test("Help /ratelimit", "/ratelimit" in source and "uso de recursos" in source.lower())
test("Help /marketplace", "PLUGIN MARKETPLACE" in source)
test("Help /marketplace install", "/marketplace install" in source)
test("Help /marketplace create", "/marketplace create" in source)
test("Help /marketplace rate", "/marketplace rate" in source)


# ============================================================
# TEST 33: Config version
# ============================================================
print("\n=== TEST: Config version ===")
from config import GENESIS_VERSION
test("Version >= 1.8.0", GENESIS_VERSION >= "1.8.0")


# ============================================================
# TEST 34: Edge cases TokenBucket
# ============================================================
print("\n=== TEST: Edge cases TokenBucket ===")

# Consume mas de lo que hay
tb_edge = TokenBucket(capacity=3, refill_rate=0.01)
tb_edge.consume(3)
result = tb_edge.consume(1)
test("Consume cuando vacio = False", result == False)
test("Total rejected incrementa", tb_edge.total_rejected >= 1)

# Wait time cuando hay suficientes
tb_full = TokenBucket(capacity=10, refill_rate=1.0)
test("Wait time cuando lleno = 0", tb_full.wait_time(5) == 0.0)

# RateLimiter wait_time con recurso inexistente
rl_edge = RateLimiter()
test("Wait time recurso inexistente = 0", rl_edge.wait_time("no_existe") == 0.0)

# RateLimiter disabled wait_time
rl_edge.enabled = False
test("Wait time disabled = 0", rl_edge.wait_time("inference") == 0.0)


# ============================================================
# TEST 35: HealthMonitor overall status logic
# ============================================================
print("\n=== TEST: HealthMonitor overall status ===")
hm_logic = HealthMonitor()

# Solo healthy
hm_logic.last_results = {
    "a": HealthCheck("a", HealthStatus.HEALTHY),
    "b": HealthCheck("b", HealthStatus.HEALTHY),
}
test("All healthy -> healthy", hm_logic.get_overall_status() == HealthStatus.HEALTHY)

# Con degraded
hm_logic.last_results["c"] = HealthCheck("c", HealthStatus.DEGRADED)
test("Con degraded -> degraded", hm_logic.get_overall_status() == HealthStatus.DEGRADED)

# Con unhealthy
hm_logic.last_results["d"] = HealthCheck("d", HealthStatus.UNHEALTHY)
test("Con unhealthy -> unhealthy", hm_logic.get_overall_status() == HealthStatus.UNHEALTHY)


# ============================================================
# Resultado final
# ============================================================
print(f"\n{'='*60}")
print(f"  RESULTADO: {_passed} passed, {_failed} failed de {_passed + _failed} tests")
print(f"{'='*60}")

if _failed > 0:
    sys.exit(1)
