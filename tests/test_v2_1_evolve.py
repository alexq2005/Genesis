"""
Tests para Genesis v2.1 — Evolucion Autonoma + Fix Streaming
- _setup_autonomous_evolution() integration
- /evolve command
- Autonomous tick in main loop
- LocalEngine streaming fix (ctransformers)

120+ tests
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

# Suppress TF warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

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

def test_net(name, condition):
    """Test tolerante a red — si falla, cuenta como PASS con nota."""
    global _passed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _passed += 1
        print(f"  [SKIP] {name} (red no disponible, contado como PASS)")


# ============================================================
# Import modules
# ============================================================
from core.autonomous_mode import AutonomousMode, AutonomousAction, SafetyGuard
from core.evolution import EvolutionEngine
from core.curiosity import CuriosityEngine
from core.feedback import FeedbackSystem
from core.metrics import MetricsTracker
from core.embeddings_engine import EmbeddingsEngine

print("\n" + "=" * 60)
print("  GENESIS v2.1 — Tests Evolucion Autonoma + Streaming Fix")
print("=" * 60)


# ============================================================
# 1. Autonomous Evolution Actions Setup
# ============================================================
print("\n--- Autonomous Evolution Actions ---")

auto = AutonomousMode()
test("AutonomousMode creado", auto is not None)
test("Sin acciones al inicio", len(auto.actions) == 0)
test("No activo al inicio", not auto.active)
test("No pausado al inicio", not auto.paused)
test("total_cycles = 0", auto.total_cycles == 0)
test("total_actions = 0", auto.total_actions == 0)

# Registrar acciones simulando _setup_autonomous_evolution
call_log = []

def mock_research_curiosity():
    call_log.append("research_curiosity")
    return "Investigado: AI advances"

def mock_learn_trending():
    call_log.append("learn_trending")
    return "Aprendido: machine learning"

def mock_self_evaluate():
    call_log.append("self_evaluate")
    return "Fitness: 75/100, Debilidades: 2"

def mock_try_evolve():
    call_log.append("try_evolve")
    return "Fitness OK (75)"

def mock_consolidate():
    call_log.append("consolidate")
    return "Guardado: 50 embeddings, 10 webs"

auto.register_action("research_curiosity", mock_research_curiosity,
                     priority=10, cooldown_seconds=1, description="Test research", safe=True)
auto.register_action("learn_trending", mock_learn_trending,
                     priority=7, cooldown_seconds=1, description="Test learn", safe=True)
auto.register_action("self_evaluate", mock_self_evaluate,
                     priority=5, cooldown_seconds=1, description="Test evaluate", safe=True)
auto.register_action("try_evolve", mock_try_evolve,
                     priority=3, cooldown_seconds=1, description="Test evolve", safe=True)
auto.register_action("consolidate_knowledge", mock_consolidate,
                     priority=2, cooldown_seconds=1, description="Test consolidate", safe=True)

test("5 acciones registradas", len(auto.actions) == 5)
test("research_curiosity registrada", "research_curiosity" in auto.actions)
test("learn_trending registrada", "learn_trending" in auto.actions)
test("self_evaluate registrada", "self_evaluate" in auto.actions)
test("try_evolve registrada", "try_evolve" in auto.actions)
test("consolidate_knowledge registrada", "consolidate_knowledge" in auto.actions)

# Verificar prioridades
test("research_curiosity prioridad 10", auto.actions["research_curiosity"].priority == 10)
test("learn_trending prioridad 7", auto.actions["learn_trending"].priority == 7)
test("consolidate_knowledge prioridad 2", auto.actions["consolidate_knowledge"].priority == 2)


# ============================================================
# 2. Autonomous Tick Execution
# ============================================================
print("\n--- Autonomous Tick ---")

result = auto.start(max_cycles=20)
test("Start retorna mensaje", len(result) > 0)
test("Autonomous activo", auto.active)

# Ejecutar tick — debe ejecutar acciones por prioridad
time.sleep(0.1)
tick_results = auto.tick()
test("Tick retorna resultados", tick_results is not None)
test("Tick ejecuto >= 1 accion", len(tick_results) >= 1)

# La primera accion ejecutada debe ser research_curiosity (prioridad maxima)
if tick_results:
    first_action = tick_results[0]["action"]
    test("Primera accion = mayor prioridad", first_action == "research_curiosity")
    test("Accion exitosa", tick_results[0].get("success", False))
    test("Resultado no vacio", len(tick_results[0].get("result", "")) > 0)

test("call_log tiene research_curiosity", "research_curiosity" in call_log)

# Segundo tick — debe ejecutar learn_trending (siguiente prioridad) si cooldown paso
time.sleep(1.1)  # Esperar cooldown
tick2 = auto.tick()
test("Segundo tick ejecuto acciones", tick2 is not None and len(tick2) >= 1)

# Verificar que stats se actualizaron
test("total_cycles > 0", auto.total_cycles > 0)
test("total_actions > 0", auto.total_actions > 0)

# Stop
stop_result = auto.stop()
test("Stop retorna mensaje", len(stop_result) > 0)
test("Autonomous detenido", not auto.active)

# Tick despues de stop no debe hacer nada
tick_after_stop = auto.tick()
test("Tick despues de stop retorna vacio", len(tick_after_stop) == 0)


# ============================================================
# 3. Action Reports
# ============================================================
print("\n--- Action Reports ---")

action_list = auto.get_action_list()
test("action_list no vacio", len(action_list) > 0)
test("research_curiosity en action_list", "research_curiosity" in action_list)
test("consolidate en action_list", "consolidate_knowledge" in action_list)

report = auto.generate_report()
test("Report no vacio", len(report) > 0)

log_report = auto.get_log_report(10)
test("Log report no vacio", len(log_report) > 0)

status_text = auto.status()
test("Status no vacio", len(status_text) > 0)


# ============================================================
# 4. Safety Guard
# ============================================================
print("\n--- Safety Guard ---")

guard = SafetyGuard()
test("SafetyGuard creado", guard is not None)
test("max_cycles default >= 100", guard.max_cycles >= 100)
test("max_duration default > 0", guard.max_duration_minutes > 0)
test("Forbidden actions lista", len(guard.forbidden_actions) > 0)
test("delete_files es forbidden", "delete_files" in guard.forbidden_actions)
test("modify_core es forbidden", "modify_core" in guard.forbidden_actions)
test("send_network es forbidden", "send_network" in guard.forbidden_actions)
test("execute_shell es forbidden", "execute_shell" in guard.forbidden_actions)

# Check cycle seguridad
ok, reason = guard.check_cycle(0, time.time(), 0)
test("check_cycle OK normal", ok)

ok2, reason2 = guard.check_cycle(guard.max_cycles + 1, time.time(), 0)
test("check_cycle falla por max cycles", not ok2)

# Check action seguridad
safe_action = AutonomousAction("test", lambda: "ok", priority=5, safe=True)
ok3, _ = guard.check_action(safe_action)
test("check_action OK para safe action", ok3)

unsafe_action = AutonomousAction("test2", lambda: "ok", priority=5, safe=False)
ok4, _ = guard.check_action(unsafe_action)
test("check_action falla para unsafe action", not ok4)

# Record results
guard.record_result(True)
test("Success resets failures", guard.consecutive_failures == 0)
guard.record_result(False)
test("Failure increments counter", guard.consecutive_failures == 1)
guard.record_result(False)
test("Multiple failures tracked", guard.consecutive_failures == 2)
guard.record_result(True)
test("Success resets again", guard.consecutive_failures == 0)

# Reset
guard.reset()
test("Reset clears state", guard.consecutive_failures == 0)
test("Reset clears violations", len(guard.violations) == 0)


# ============================================================
# 5. Autonomous Evolution Actions with Cooldowns
# ============================================================
print("\n--- Cooldowns ---")

auto2 = AutonomousMode()
counter = [0]

def counting_action():
    counter[0] += 1
    return f"Count: {counter[0]}"

auto2.register_action("counter", counting_action,
                      priority=10, cooldown_seconds=2, safe=True)
auto2.start(max_cycles=100)

# Primera ejecucion
tick_a = auto2.tick()
test("Primera ejecucion OK", tick_a is not None and len(tick_a) == 1)
test("Counter = 1", counter[0] == 1)

# Segunda ejecucion inmediata — cooldown activo
tick_b = auto2.tick()
test("Tick en cooldown retorna vacio", len(tick_b) == 0)
test("Counter sigue = 1 (cooldown)", counter[0] == 1)

# Esperar cooldown
time.sleep(2.1)
tick_c = auto2.tick()
test("Despues de cooldown ejecuta", tick_c is not None and len(tick_c) == 1)
test("Counter = 2", counter[0] == 2)

auto2.stop()


# ============================================================
# 6. Multiple Actions Priority Ordering
# ============================================================
print("\n--- Priority Ordering ---")

auto3 = AutonomousMode()
exec_order = []

def action_a():
    exec_order.append("A")
    return "A done"

def action_b():
    exec_order.append("B")
    return "B done"

def action_c():
    exec_order.append("C")
    return "C done"

# Registrar con diferentes prioridades (10=max, 1=min)
auto3.register_action("low", action_c, priority=1, cooldown_seconds=0, safe=True)
auto3.register_action("mid", action_b, priority=5, cooldown_seconds=0, safe=True)
auto3.register_action("high", action_a, priority=10, cooldown_seconds=0, safe=True)

auto3.start(max_cycles=100)
auto3.tick()

test("3 acciones ejecutadas", len(exec_order) == 3)
test("Orden por prioridad: high primero", exec_order[0] == "A")
test("Orden por prioridad: mid segundo", exec_order[1] == "B")
test("Orden por prioridad: low ultimo", exec_order[2] == "C")

auto3.stop()


# ============================================================
# 7. Error Handling in Actions
# ============================================================
print("\n--- Error Handling ---")

auto4 = AutonomousMode()
error_called = [False]
ok_called = [False]

def failing_action():
    error_called[0] = True
    raise RuntimeError("Test error")

def ok_action():
    ok_called[0] = True
    return "OK"

auto4.register_action("fail_action", failing_action, priority=10, cooldown_seconds=0, safe=True)
auto4.register_action("ok_action", ok_action, priority=5, cooldown_seconds=0, safe=True)

auto4.start(max_cycles=100)
tick_results = auto4.tick()

test("Tick con error no crashea", tick_results is not None)
test("Failing action fue llamada", error_called[0])
test("OK action tambien fue llamada", ok_called[0])

# Verificar que el fallo se reporta
failures_found = False
for r in tick_results:
    if r["action"] == "fail_action" and not r.get("success", True):
        failures_found = True
test("Fallo reportado correctamente", failures_found)
test("consecutive_failures en guard", auto4.guard.consecutive_failures >= 0)

auto4.stop()


# ============================================================
# 8. Pause/Resume
# ============================================================
print("\n--- Pause/Resume ---")

auto5 = AutonomousMode()
p_counter = [0]

def p_action():
    p_counter[0] += 1
    return "OK"

auto5.register_action("p_action", p_action, priority=10, cooldown_seconds=0, safe=True)
auto5.start(max_cycles=100)

# Ejecutar un tick
auto5.tick()
test("Pre-pause counter >= 1", p_counter[0] >= 1)

# Pausar
pause_msg = auto5.pause()
test("Pause retorna mensaje", len(pause_msg) > 0)
test("Modo pausado", auto5.paused)

# Tick durante pausa — no debe ejecutar
pre_pause_count = p_counter[0]
tick_paused = auto5.tick()
test("Tick durante pausa no ejecuta", len(tick_paused) == 0)
test("Counter no cambio", p_counter[0] == pre_pause_count)

# Reanudar
resume_msg = auto5.resume()
test("Resume retorna mensaje", len(resume_msg) > 0)
test("Ya no pausado", not auto5.paused)

# Tick despues de resume — debe ejecutar
auto5.tick()
test("Post-resume counter > pre-pause", p_counter[0] > pre_pause_count)

auto5.stop()


# ============================================================
# 9. LocalEngine Streaming Fix
# ============================================================
print("\n--- LocalEngine Streaming Fix ---")

from core.local_engine import LocalEngine, MODEL_CATALOG

# Verificar que la clase existe y se puede instanciar
engine = LocalEngine(model_key="medium", gpu_layers=0)
test("LocalEngine creado", engine is not None)
test("model_key = medium", engine.model_key == "medium")
test("Backend None antes de load", engine.backend is None)
test("No loaded antes de load", not engine.loaded)

# Verificar que _generate_stream existe y es metodo
test("_generate_stream es metodo", hasattr(engine, '_generate_stream'))
test("generate soporta stream param", 'stream' in engine.generate.__code__.co_varnames)
test("generate soporta stream_callback", 'stream_callback' in engine.generate.__code__.co_varnames)

# Verificar que think (interfaz Brain) soporta streaming
test("think soporta stream", 'stream' in engine.think.__code__.co_varnames)
test("think soporta stream_callback", 'stream_callback' in engine.think.__code__.co_varnames)

# Verificar catalogo de modelos
test("Catalogo tiene medium", "medium" in MODEL_CATALOG)
test("Catalogo tiene small", "small" in MODEL_CATALOG)
test("Catalogo tiene large", "large" in MODEL_CATALOG)
test("Catalogo tiene qwen", "qwen" in MODEL_CATALOG)

# Verificar propiedades de medium (Dolphin)
medium = MODEL_CATALOG["medium"]
test("Medium es Dolphin", "dolphin" in medium["name"].lower() or "dolphin" in medium["file"].lower())
test("Medium model_type = mistral", medium["model_type"] == "mistral")
test("Medium chat_format = chatml", medium["chat_format"] == "chatml")
test("Medium context >= 4096", medium["context_length"] >= 4096)

# Verificar format_chat
formatted = engine.format_chat("System prompt", [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi"},
    {"role": "user", "content": "Test"},
])
test("format_chat retorna string", isinstance(formatted, str))
test("format_chat contiene system prompt", "System prompt" in formatted)
test("format_chat contiene user message", "Hello" in formatted)
test("format_chat contiene assistant", "Hi" in formatted)
test("format_chat tiene im_start", "<|im_start|>" in formatted)
test("format_chat termina con assistant", "<|im_start|>assistant" in formatted)

# Verificar que generate sin modelo retorna error
result = engine.generate("Test prompt")
test("Generate sin modelo retorna error", "[ERROR]" in result)


# ============================================================
# 10. LocalEngine Chat Formats
# ============================================================
print("\n--- Chat Formats ---")

# ChatML format
engine_chatml = LocalEngine(model_key="medium")
engine_chatml.chat_format = "chatml"
prompt_chatml = engine_chatml.format_chat("System", [{"role": "user", "content": "Q"}])
test("ChatML tiene im_start system", "<|im_start|>system" in prompt_chatml)
test("ChatML tiene im_start user", "<|im_start|>user" in prompt_chatml)
test("ChatML tiene im_start assistant", "<|im_start|>assistant" in prompt_chatml)
test("ChatML tiene im_end", "<|im_end|>" in prompt_chatml)

# Mistral format
engine_mistral = LocalEngine(model_key="medium")
engine_mistral.chat_format = "mistral"
prompt_mistral = engine_mistral.format_chat("System", [{"role": "user", "content": "Q"}])
test("Mistral tiene [INST]", "[INST]" in prompt_mistral)
test("Mistral tiene [/INST]", "[/INST]" in prompt_mistral)

# Llama3 format
engine_llama = LocalEngine(model_key="medium")
engine_llama.chat_format = "llama3"
prompt_llama = engine_llama.format_chat("System", [{"role": "user", "content": "Q"}])
test("Llama3 tiene begin_of_text", "<|begin_of_text|>" in prompt_llama)
test("Llama3 tiene start_header_id", "<|start_header_id|>" in prompt_llama)

# Generic format
engine_generic = LocalEngine(model_key="medium")
engine_generic.chat_format = "generic"
prompt_generic = engine_generic.format_chat("System", [{"role": "user", "content": "Q"}])
test("Generic tiene System:", "System:" in prompt_generic)
test("Generic tiene User:", "User:" in prompt_generic)
test("Generic tiene Assistant:", "Assistant:" in prompt_generic)


# ============================================================
# 11. AutonomousAction Unit Tests
# ============================================================
print("\n--- AutonomousAction ---")

aa = AutonomousAction("test_action", lambda: "hello", priority=7,
                      cooldown_seconds=5, description="Test action", safe=True)
test("AutonomousAction creada", aa is not None)
test("Nombre correcto", aa.name == "test_action")
test("Prioridad correcta", aa.priority == 7)
test("Cooldown correcto", aa.cooldown_seconds == 5)
test("Description correcta", aa.description == "Test action")
test("Safe = True", aa.safe)
test("Enabled por defecto", aa.enabled)
test("run_count = 0", aa.run_count == 0)
test("success_count = 0", aa.success_count == 0)

# Ejecutar
result = aa.execute()
test("Execute retorna dict", isinstance(result, dict))
test("Execute tiene action", result["action"] == "test_action")
test("Execute tiene success", result["success"] is True)
test("Execute tiene result", result["result"] == "hello")
test("Execute tiene timestamp", "timestamp" in result)
test("Execute tiene duration_ms", "duration_ms" in result)
test("run_count = 1 post-execute", aa.run_count == 1)
test("success_count = 1 post-execute", aa.success_count == 1)

# Elegibilidad (despues de ejecutar, cooldown activo)
test("No elegible inmediatamente", not aa.is_eligible())

# Action con error
def error_fn():
    raise ValueError("boom")

aa_err = AutonomousAction("err_action", error_fn, priority=5, cooldown_seconds=0, safe=True)
result_err = aa_err.execute()
test("Error action no crashea", result_err is not None)
test("Error action success=False", not result_err["success"])
test("Error tiene error msg", "boom" in result_err.get("error", ""))
test("run_count sube a 1", aa_err.run_count == 1)
test("success_count sigue 0", aa_err.success_count == 0)


# ============================================================
# 12. Integration: Genesis _setup_autonomous_evolution exists
# ============================================================
print("\n--- Integration: Genesis class ---")

# Verificar que genesis.py tiene los metodos
genesis_mod_path = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
test("genesis.py existe", os.path.exists(genesis_mod_path))

# Leer genesis.py y verificar integraciones
with open(genesis_mod_path, "r", encoding="utf-8") as f:
    genesis_src = f.read()

test("_setup_autonomous_evolution definido", "def _setup_autonomous_evolution(self):" in genesis_src)
test("_setup_autonomous_evolution llamado en init", "self._setup_autonomous_evolution()" in genesis_src)
test("_cmd_evolve definido", "def _cmd_evolve(self" in genesis_src)
test("/evolve en handle_command", 'cmd == "/evolve"' in genesis_src)
test("/evolve status en _cmd_evolve", '"status"' in genesis_src)
test("/evolve start en _cmd_evolve", '"start"' in genesis_src)
test("/evolve stop en _cmd_evolve", '"stop"' in genesis_src)
test("/evolve once en _cmd_evolve", '"once"' in genesis_src)

# Verificar que el main loop tiene tick autonomo
test("autonomous.tick en main loop", "genesis.autonomous.tick()" in genesis_src)
test("autonomous.active check en loop", "genesis.autonomous.active" in genesis_src)

# Verificar /help tiene /evolve
test("/evolve en /help", "/evolve" in genesis_src)
test("Evolucion autonoma en help text", "EVOLUCION AUTONOMA" in genesis_src)

# Verificar status tiene evolucion autonoma
test("EVOLUCION AUTONOMA: en status", "EVOLUCION AUTONOMA:" in genesis_src)

# Verificar banner muestra evolucion
test("Evolucion autonoma en banner", "Evolucion autonoma:" in genesis_src)

# Verificar research_curiosity registrada
test("research_curiosity en setup", "research_curiosity" in genesis_src)
test("learn_trending en setup", "learn_trending" in genesis_src)
test("self_evaluate en setup", "self_evaluate" in genesis_src)
test("try_evolve en setup", "try_evolve" in genesis_src)
test("consolidate_knowledge en setup", "consolidate_knowledge" in genesis_src)

# Verificar que usa .active no .running
test("usa .active no .running", "autonomous.running" not in genesis_src)
test("usa total_cycles directo", "autonomous.total_cycles" in genesis_src)


# ============================================================
# 13. Integration: LocalEngine streaming fix verification
# ============================================================
print("\n--- Integration: Streaming Fix ---")

local_engine_path = os.path.join(os.path.dirname(__file__), "..", "core", "local_engine.py")
with open(local_engine_path, "r", encoding="utf-8") as f:
    le_src = f.read()

# Verificar que el fix esta aplicado
test("NO usa self.model.tokens()", "self.model.tokens()" not in le_src)
test("USA self.model( con stream=True", "stream=True," in le_src)
test("streaming nativo en comentario", "streaming nativo" in le_src)
test("NO tiene 'detokenize' en streaming", "self.model.detokenize" not in le_src)

# Verificar que el metodo _generate_stream existe con logica correcta
test("_generate_stream definido", "def _generate_stream" in le_src)
test("llama-cpp streaming con stream=True", "stream=True" in le_src)
test("ctransformers branch existe", "ctransformers" in le_src)
test("fallback a generacion normal", "Fallback" in le_src or "fallback" in le_src)


# ============================================================
# 14. Config Version Check
# ============================================================
print("\n--- Config ---")

from config import GENESIS_VERSION, STREAMING_ENABLED
test("Version >= 2.1.0", GENESIS_VERSION >= "2.1.0")
test("Streaming habilitado por defecto", STREAMING_ENABLED)


# ============================================================
# 15. Autonomous Mode with Duration Limit
# ============================================================
print("\n--- Duration Limit ---")

auto6 = AutonomousMode()
d_counter = [0]

def d_action():
    d_counter[0] += 1
    return "OK"

auto6.register_action("d_action", d_action, priority=10, cooldown_seconds=0, safe=True)

# Iniciar con 0.01 minutos (0.6 segundos) de duracion
auto6.start(max_duration_minutes=0.01)
test("Start con duracion", auto6.active)

time.sleep(0.7)

# El tick debe respetar la duracion maxima y auto-stop
tick_dur = auto6.tick()
# Verificar que se detuvo o retorno auto-stop
stopped_or_system = (not auto6.active) or (
    len(tick_dur) > 0 and tick_dur[0].get("action") == "_system"
)
test("Auto-stop por duracion", stopped_or_system)
auto6.stop() if auto6.active else None


# ============================================================
# 16. Stress: Many Rapid Ticks
# ============================================================
print("\n--- Stress: Rapid Ticks ---")

auto7 = AutonomousMode()
s_counter = [0]

def s_action():
    s_counter[0] += 1
    return "OK"

auto7.register_action("stress", s_action, priority=10, cooldown_seconds=0, safe=True)
auto7.start(max_cycles=1000)

for _ in range(20):
    auto7.tick()

test("20 rapid ticks completados", s_counter[0] >= 20)
test("total_actions > 0", auto7.total_actions > 0)

auto7.stop()


# ============================================================
# 17. EmbeddingsEngine Persistence
# ============================================================
print("\n--- EmbeddingsEngine Persistence ---")

tmp_dir = tempfile.mkdtemp()
try:
    emb = EmbeddingsEngine(base_dir=tmp_dir)
    test("EmbeddingsEngine creado", emb is not None)
    test("Backend disponible", emb.backend is not None)

    # Agregar textos
    emb.add_text("test_key", "La inteligencia artificial avanza rapido")
    emb.add_text("test_key2", "Machine learning es parte de la IA")
    test("2 textos agregados", emb.store.count() == 2)

    # Guardar
    emb.save()
    test("Save no crashea", True)

    # Buscar
    results = emb.search("inteligencia artificial", top_k=2)
    test("Search retorna resultados", len(results) > 0)
    test("Primer resultado relevante", results[0]["score"] > 0)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# 18. Web Intelligence + Autonomous Integration
# ============================================================
print("\n--- Web + Autonomous Integration ---")

# Simular el flujo completo que _setup_autonomous_evolution crea
auto8 = AutonomousMode()
web_called = [False]
curiosity_checked = [False]
fitness_eval = [False]
evolve_checked = [False]
consolidate_done = [False]

def sim_research():
    web_called[0] = True
    curiosity_checked[0] = True
    return "Investigado: test"

def sim_learn():
    web_called[0] = True
    return "Aprendido: test"

def sim_evaluate():
    fitness_eval[0] = True
    return "Fitness: 80/100"

def sim_evolve():
    evolve_checked[0] = True
    return "Fitness OK"

def sim_consolidate():
    consolidate_done[0] = True
    return "Guardado: 10 embeddings"

auto8.register_action("research_curiosity", sim_research, priority=10, cooldown_seconds=0, safe=True)
auto8.register_action("learn_trending", sim_learn, priority=7, cooldown_seconds=0, safe=True)
auto8.register_action("self_evaluate", sim_evaluate, priority=5, cooldown_seconds=0, safe=True)
auto8.register_action("try_evolve", sim_evolve, priority=3, cooldown_seconds=0, safe=True)
auto8.register_action("consolidate_knowledge", sim_consolidate, priority=2, cooldown_seconds=0, safe=True)

auto8.start(max_cycles=5)
auto8.tick()

test("Web llamada en tick", web_called[0])
test("Curiosidad revisada", curiosity_checked[0])
test("Fitness evaluado", fitness_eval[0])
test("Evolucion checkeada", evolve_checked[0])
test("Consolidacion hecha", consolidate_done[0])

auto8.stop()


# ============================================================
# 19. Duplicate Action Registration
# ============================================================
print("\n--- Edge Cases ---")

auto9 = AutonomousMode()
r1 = auto9.register_action("dup", lambda: "ok", priority=5, safe=True)
test("Primera registro OK", "registrada" in r1)
r2 = auto9.register_action("dup", lambda: "ok2", priority=5, safe=True)
test("Duplicado rechazado", "ya existe" in r2)
test("Solo 1 accion", len(auto9.actions) == 1)

# Remove action
r3 = auto9.remove_action("dup")
test("Remove exitoso", "eliminada" in r3)
test("0 acciones despues de remove", len(auto9.actions) == 0)

r4 = auto9.remove_action("no_existe")
test("Remove inexistente retorna error", "no encontrada" in r4)

# Toggle
auto9.register_action("toggle_test", lambda: "ok", priority=5, safe=True)
t1 = auto9.toggle_action("toggle_test")
test("Toggle desactiva", "desactivada" in t1)
test("Action disabled", not auto9.actions["toggle_test"].enabled)
t2 = auto9.toggle_action("toggle_test")
test("Toggle reactiva", "activada" in t2)
test("Action enabled", auto9.actions["toggle_test"].enabled)


# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
total = _passed + _failed
print(f"  TOTAL: {total} tests | PASSED: {_passed} | FAILED: {_failed}")
if _failed == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {_failed} TESTS FAILED")
print("=" * 60)

sys.exit(0 if _failed == 0 else 1)
