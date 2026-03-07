"""
Tests para Genesis v1.6.0
- Agent System (agentes, deteccion, delegacion, pipelines)
- Workflow Engine (workflows predefinidos, ejecucion, custom)
- Session Manager (crear, cambiar, eliminar, persistencia)
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
# TEST 1: Agent — Estructura basica
# ============================================================
print("\n=== TEST: Agent — Estructura basica ===")
from core.agents import Agent, AgentSystem

# Crear agente manual
agent = Agent(
    name="test_agent",
    role="Tester",
    system_prompt="Eres un tester.",
    capabilities=["test", "qa"],
    temperature=0.5,
    priority=7,
)

test("Agent tiene nombre", agent.name == "test_agent")
test("Agent tiene rol", agent.role == "Tester")
test("Agent tiene system_prompt", "tester" in agent.system_prompt.lower())
test("Agent tiene capabilities", agent.capabilities == ["test", "qa"])
test("Agent tiene temperature", agent.temperature == 0.5)
test("Agent tiene priority", agent.priority == 7)
test("Agent enabled por defecto", agent.enabled is True)
test("Agent tasks_completed inicia en 0", agent.tasks_completed == 0)
test("Agent total_time inicia en 0", agent.total_time == 0.0)

# to_dict
d = agent.to_dict()
test("to_dict tiene name", d["name"] == "test_agent")
test("to_dict tiene role", d["role"] == "Tester")
test("to_dict tiene avg_time", "avg_time" in d)
test("to_dict tiene tasks_completed", d["tasks_completed"] == 0)


# ============================================================
# TEST 2: AgentSystem — Agentes predefinidos
# ============================================================
print("\n=== TEST: AgentSystem — Agentes predefinidos ===")
system = AgentSystem(brain=None)

test("6 agentes predefinidos", len(system.agents) == 6)
test("Agente researcher existe", "researcher" in system.agents)
test("Agente coder existe", "coder" in system.agents)
test("Agente analyst existe", "analyst" in system.agents)
test("Agente creative existe", "creative" in system.agents)
test("Agente security existe", "security" in system.agents)
test("Agente planner existe", "planner" in system.agents)
test("Sistema enabled por defecto", system.enabled is True)
test("Historial vacio al inicio", len(system.history) == 0)

# Verificar roles
test("Researcher es Investigador", system.agents["researcher"].role == "Investigador")
test("Coder es Programador", system.agents["coder"].role == "Programador")
test("Creative es Creativo", system.agents["creative"].role == "Creativo")
test("Security es Especialista", "Seguridad" in system.agents["security"].role)
test("Planner es Planificador", system.agents["planner"].role == "Planificador")

# Verificar capabilities unicas
test("Researcher tiene research", "research" in system.agents["researcher"].capabilities)
test("Coder tiene code", "code" in system.agents["coder"].capabilities)
test("Coder tiene debug", "debug" in system.agents["coder"].capabilities)
test("Creative tiene creative", "creative" in system.agents["creative"].capabilities)
test("Security tiene security", "security" in system.agents["security"].capabilities)
test("Planner tiene planning", "planning" in system.agents["planner"].capabilities)


# ============================================================
# TEST 3: AgentSystem — Deteccion automatica
# ============================================================
print("\n=== TEST: AgentSystem — Deteccion automatica ===")

# Keywords de investigacion
test("'busca' -> researcher", system.detect_agent("busca informacion sobre Python") == "researcher")
test("'investiga' -> researcher", system.detect_agent("investiga machine learning") == "researcher")

# Keywords de codigo
test("'codigo' -> coder", system.detect_agent("escribe el codigo de una funcion") == "coder")
test("'programa' -> coder", system.detect_agent("programa un servidor web") == "coder")
test("'bug' -> coder", system.detect_agent("hay un bug en la linea 42") == "coder")
test("'fix' -> coder", system.detect_agent("necesito un fix para este error") == "coder")

# Keywords de analisis
test("'analiza' -> analyst", system.detect_agent("analiza estos datos de ventas") == "analyst")
test("'compara' -> analyst", system.detect_agent("compara dos frameworks") == "analyst")

# Keywords de creatividad
test("'poema' -> creative", system.detect_agent("escribe un poema sobre el mar") == "creative")
test("'historia' -> creative", system.detect_agent("inventa una historia de terror") == "creative")

# Keywords de seguridad
test("'seguridad' -> security", system.detect_agent("revisa la seguridad del servidor") == "security")
test("'vulnerabilidad' -> security", system.detect_agent("busca vulnerabilidad en el codigo") == "security")

# Keywords de planificacion
test("'planifica' -> planner", system.detect_agent("planifica el roadmap del proyecto") == "planner")
# "arquitectura" esta en coder (priority 8) Y planner (priority 6), coder gana el desempate
test("'arquitectura' -> coder (priority)", system.detect_agent("diseña la arquitectura del sistema") == "coder")

# Texto sin keywords reconocidos
test("Sin match retorna None", system.detect_agent("hola como estas") is None)

# Texto mixto (debe elegir el mas fuerte)
detected = system.detect_agent("analiza el codigo y busca vulnerabilidades de seguridad")
test("Mixto seguridad+code -> resuelve por peso", detected in ("security", "coder", "analyst"))


# ============================================================
# TEST 4: AgentSystem — Delegacion (sin LLM)
# ============================================================
print("\n=== TEST: AgentSystem — Delegacion (sin LLM) ===")

# Delegacion sin brain — retorna agente seleccionado
result = system.delegate("escribe un programa en Python", use_brain=False)
test("Delegate retorna dict", isinstance(result, dict))
test("Delegate tiene agent", "agent" in result)
test("Delegate tiene response", "response" in result)
test("Delegate tiene time", "time" in result)
test("Delegate tiene success", "success" in result)
test("Agente detectado es coder", result["agent"] == "coder")

# Forzar agente especifico
result2 = system.delegate("algo random", agent_name="creative", use_brain=False)
test("Forzar agente creative", result2["agent"] == "creative")
test("Role del creative", result2["role"] == "Creativo")

# Historial se actualiza
test("Historial tiene entradas", len(system.history) >= 2)

# Stats del agente se actualizan
test("Coder tiene 1+ tarea", system.agents["coder"].tasks_completed >= 1)
test("Creative tiene 1+ tarea", system.agents["creative"].tasks_completed >= 1)


# ============================================================
# TEST 5: AgentSystem — Add/Remove/Toggle agentes
# ============================================================
print("\n=== TEST: AgentSystem — Add/Remove/Toggle ===")

# Agregar agente custom
result = system.add_agent("custom_test", "Test Bot", "Haces tests.", ["test"])
test("Agregar agente custom OK", "creado" in result)
test("Custom existe en agents", "custom_test" in system.agents)
test("Ahora hay 7 agentes", len(system.agents) == 7)

# No duplicar
result = system.add_agent("custom_test", "Otro", "Otro.")
test("No permite duplicados", "ya existe" in result)

# Toggle agente
result = system.toggle_agent("custom_test")
test("Toggle desactiva", "desactivado" in result)
test("custom_test disabled", not system.agents["custom_test"].enabled)

result = system.toggle_agent("custom_test")
test("Toggle reactiva", "activado" in result)
test("custom_test enabled", system.agents["custom_test"].enabled)

# No eliminar predefinidos
result = system.remove_agent("coder")
test("No elimina predefinido", "predefinido" in result)

# Eliminar custom
result = system.remove_agent("custom_test")
test("Eliminar custom OK", "eliminado" in result)
test("Vuelve a 6 agentes", len(system.agents) == 6)

# Toggle sistema completo
result = system.toggle()
test("Toggle sistema OFF", "DESACTIVADO" in result)
test("Sistema disabled", not system.enabled)

result = system.toggle()
test("Toggle sistema ON", "ACTIVADO" in result)
test("Sistema enabled", system.enabled)


# ============================================================
# TEST 6: AgentSystem — Pipeline (sin LLM)
# ============================================================
print("\n=== TEST: AgentSystem — Pipeline ===")

# Sin brain, delegate retorna response vacia -> pipeline se detiene en paso 1 (break)
# Esto es comportamiento correcto: un agente que falla detiene el pipeline
result = system.pipeline(["researcher", "analyst"], "test input", context="test context")
test("Pipeline retorna dict", isinstance(result, dict))
test("Pipeline tiene steps", "steps" in result)
test("Pipeline ejecuta hasta fallo", len(result["steps"]) >= 1)
test("Pipeline tiene final_response", "final_response" in result)
test("Pipeline tiene total_time", "total_time" in result)
test("Pipeline tiene agents_used", "agents_used" in result)
test("Pipeline agents_used es lista", isinstance(result["agents_used"], list))

# Pipeline con agente inexistente — no crashea
result2 = system.pipeline(["fake_agent", "coder"], "test")
test("Pipeline con fake agent no crashea", len(result2["steps"]) >= 1)
test("Fake agent tiene error", "error" in result2["steps"][0])


# ============================================================
# TEST 7: AgentSystem — List/History/Status
# ============================================================
print("\n=== TEST: AgentSystem — List/History/Status ===")

listing = system.list_agents()
test("list_agents retorna string", isinstance(listing, str))
test("list_agents contiene researcher", "researcher" in listing)
test("list_agents contiene coder", "coder" in listing)
test("list_agents muestra capabilities", "Capabilities" in listing)

history = system.get_history()
test("get_history retorna string", isinstance(history, str))
test("get_history contiene entradas", "Historial" in history or "Sin historial" in history)

status = system.status()
test("status retorna string", isinstance(status, str))
test("status contiene AgentSystem", "AgentSystem" in status)


# ============================================================
# TEST 8: Workflow — Estructura basica
# ============================================================
print("\n=== TEST: Workflow — Estructura basica ===")
from core.workflows import Workflow, WorkflowStep, WorkflowEngine

step = WorkflowStep(
    name="Test Step",
    agent="coder",
    prompt_template="Analiza: {input}\nContexto: {context}",
)

test("Step tiene name", step.name == "Test Step")
test("Step tiene agent", step.agent == "coder")
test("Step tiene prompt_template", "{input}" in step.prompt_template)
test("Step tiene action default", step.action == "delegate")

wf = Workflow(name="test_wf", description="Test workflow", steps=[step], tags=["test"])
test("Workflow tiene name", wf.name == "test_wf")
test("Workflow tiene 1 step", len(wf.steps) == 1)
test("Workflow tiene tags", wf.tags == ["test"])
test("Workflow times_run inicia en 0", wf.times_run == 0)

d = wf.to_dict()
test("to_dict tiene name", d["name"] == "test_wf")
test("to_dict tiene steps count", d["steps"] == 1)


# ============================================================
# TEST 9: WorkflowEngine — Workflows predefinidos
# ============================================================
print("\n=== TEST: WorkflowEngine — Workflows predefinidos ===")
engine = WorkflowEngine(agent_system=None)

test("4 workflows predefinidos", len(engine.workflows) == 4)
test("code_review existe", "code_review" in engine.workflows)
test("research_deep existe", "research_deep" in engine.workflows)
test("debug_fix existe", "debug_fix" in engine.workflows)
test("project_scaffold existe", "project_scaffold" in engine.workflows)

# Verificar estructura de code_review
cr = engine.workflows["code_review"]
test("code_review tiene 3 pasos", len(cr.steps) == 3)
test("code_review tags incluye code", "code" in cr.tags)
test("code_review primer paso es Analisis", "Analisis" in cr.steps[0].name)
test("code_review usa coder", cr.steps[0].agent == "coder")

# Verificar research_deep
rd = engine.workflows["research_deep"]
test("research_deep tiene 3 pasos", len(rd.steps) == 3)
test("research_deep usa researcher", rd.steps[0].agent == "researcher")

# Verificar debug_fix
df = engine.workflows["debug_fix"]
test("debug_fix tiene 3 pasos", len(df.steps) == 3)
test("debug_fix primer paso Diagnostico", "Diagnostico" in df.steps[0].name)

# Verificar project_scaffold
ps = engine.workflows["project_scaffold"]
test("project_scaffold tiene 3 pasos", len(ps.steps) == 3)
test("project_scaffold usa planner", ps.steps[0].agent == "planner")


# ============================================================
# TEST 10: WorkflowEngine — Ejecucion (sin LLM)
# ============================================================
print("\n=== TEST: WorkflowEngine — Ejecucion (sin LLM) ===")

# Sin agent_system -> pasos simulados
result = engine.run("code_review", "def foo(): pass")
test("Run retorna dict", isinstance(result, dict))
test("Run tiene workflow", result["workflow"] == "code_review")
test("Run tiene steps", len(result["steps"]) == 3)
test("Run tiene final_output", "final_output" in result)
test("Run tiene total_time", result["total_time"] >= 0)
test("Run tiene success", "success" in result)

# Workflow inexistente
result_bad = engine.run("nonexistent", "test")
test("Workflow inexistente no crashea", not result_bad["success"])
test("Workflow inexistente tiene mensaje", "no encontrado" in result_bad["final_output"])

# Stats se actualizan
test("code_review times_run = 1", engine.workflows["code_review"].times_run == 1)

# Historial se actualiza
test("Historial tiene 1 entrada", len(engine.history) == 1)


# ============================================================
# TEST 11: WorkflowEngine — Custom workflows
# ============================================================
print("\n=== TEST: WorkflowEngine — Custom workflows ===")

result = engine.create_workflow(
    "my_workflow",
    "Mi workflow custom",
    [
        {"name": "Paso 1", "agent": "coder", "prompt_template": "Haz: {input}"},
        {"name": "Paso 2", "agent": "analyst"},
    ],
)
test("Crear workflow custom OK", "creado" in result)
test("Ahora hay 5 workflows", len(engine.workflows) == 5)
test("Custom tiene tag custom", "custom" in engine.workflows["my_workflow"].tags)
test("Custom tiene 2 pasos", len(engine.workflows["my_workflow"].steps) == 2)

# No duplicar
result2 = engine.create_workflow("my_workflow", "Otro", [])
test("No permite duplicados", "ya existe" in result2)


# ============================================================
# TEST 12: WorkflowEngine — List/History/Status
# ============================================================
print("\n=== TEST: WorkflowEngine — List/History/Status ===")

listing = engine.list_workflows()
test("list_workflows retorna string", isinstance(listing, str))
test("list_workflows contiene code_review", "code_review" in listing)
test("list_workflows muestra Pipeline", "Pipeline" in listing)

history = engine.get_history()
test("get_history retorna string", isinstance(history, str))

status = engine.status()
test("status retorna string", isinstance(status, str))
test("status contiene WorkflowEngine", "WorkflowEngine" in status)


# ============================================================
# TEST 13: Session — Estructura basica
# ============================================================
print("\n=== TEST: Session — Estructura basica ===")
from core.sessions import Session, SessionManager

session = Session("test_session", name="Test", topic="Testing")
test("Session tiene id", session.session_id == "test_session")
test("Session tiene name", session.name == "Test")
test("Session tiene topic", session.topic == "Testing")
test("Session messages vacio", len(session.messages) == 0)
test("Session tiene created_at", session.created_at > 0)

# Agregar mensajes
session.add_message("user", "Hola")
session.add_message("assistant", "Hola!")
test("2 mensajes agregados", len(session.messages) == 2)
test("Primer mensaje es user", session.messages[0]["role"] == "user")
test("Segundo mensaje es assistant", session.messages[1]["role"] == "assistant")
test("Mensaje tiene timestamp", "timestamp" in session.messages[0])
test("last_access actualizado", session.last_access > session.created_at - 1)

# get_messages con limit
all_msgs = session.get_messages()
test("get_messages retorna todos", len(all_msgs) == 2)
limited = session.get_messages(limit=1)
test("get_messages con limit=1", len(limited) == 1)
test("Limit retorna ultimo", limited[0]["content"] == "Hola!")

# clear_messages
session.clear_messages()
test("clear_messages limpia", len(session.messages) == 0)


# ============================================================
# TEST 14: Session — Serialization
# ============================================================
print("\n=== TEST: Session — Serialization ===")

s1 = Session("s1", name="Session One", topic="Serialization test")
s1.add_message("user", "Test message")
s1.metadata = {"key": "value"}

d = s1.to_dict()
test("to_dict tiene session_id", d["session_id"] == "s1")
test("to_dict tiene messages", len(d["messages"]) == 1)
test("to_dict tiene message_count", d["message_count"] == 1)
test("to_dict tiene metadata", d["metadata"] == {"key": "value"})
test("to_dict tiene created_at", "created_at" in d)

# Round-trip: to_dict -> from_dict
s2 = Session.from_dict(d)
test("from_dict preserva id", s2.session_id == "s1")
test("from_dict preserva name", s2.name == "Session One")
test("from_dict preserva topic", s2.topic == "Serialization test")
test("from_dict preserva messages", len(s2.messages) == 1)
test("from_dict preserva metadata", s2.metadata == {"key": "value"})
test("from_dict preserva created_at", s2.created_at == s1.created_at)


# ============================================================
# TEST 15: SessionManager — CRUD
# ============================================================
print("\n=== TEST: SessionManager — CRUD ===")

# Usar directorio temporal
tmpdir = tempfile.mkdtemp()
try:
    sm = SessionManager(base_dir=tmpdir)

    # Default session existe
    test("Default session creada", "default" in sm.sessions)
    test("Active es default", sm.active_id == "default")

    # Crear nueva
    result = sm.create("proyecto_web", "Desarrollo frontend")
    test("Crear session OK", "creada" in result)
    test("proyecto_web existe", "proyecto_web" in sm.sessions)
    test("Active cambia a nueva", sm.active_id == "proyecto_web")

    # Crear con nombre sucio
    result = sm.create("Mi Sesion!!", "Test")
    test("Sanitiza nombre", "mi_sesion" in sm.sessions)

    # No duplicar
    result = sm.create("proyecto_web", "Otro")
    test("No permite duplicados", "ya existe" in result)

    # Switch
    result = sm.switch("default")
    test("Switch a default OK", "default" in sm.active_id)
    test("Switch muestra info", "mensajes" in result)

    # Switch parcial
    result = sm.switch("proyecto")
    test("Switch parcial encuentra", sm.active_id == "proyecto_web")

    # Switch inexistente
    result = sm.switch("nonexistent")
    test("Switch inexistente falla", "no encontrada" in result)

    # Rename
    result = sm.rename("proyecto_web", "Frontend v2")
    test("Rename OK", "renombrada" in result.lower() or "Frontend" in result)
    test("Nombre actualizado", sm.sessions["proyecto_web"].name == "Frontend v2")

    # Delete — no activa
    sm.switch("default")
    result = sm.delete("mi_sesion")
    test("Delete OK", "eliminada" in result)
    test("mi_sesion ya no existe", "mi_sesion" not in sm.sessions)

    # Delete — no puede eliminar activa
    result = sm.delete("default")
    test("No elimina sesion activa", "activa" in result.lower())

    # Delete — no puede eliminar unica (si queda 1)
    # Hay 2: default y proyecto_web
    sm.switch("proyecto_web")
    sm.delete("default")
    # Ahora solo queda proyecto_web
    result = sm.delete("proyecto_web")
    test("No elimina unica sesion", "unica" in result.lower() or "activa" in result.lower())

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 16: SessionManager — Messages
# ============================================================
print("\n=== TEST: SessionManager — Messages ===")

tmpdir = tempfile.mkdtemp()
try:
    sm = SessionManager(base_dir=tmpdir)

    # Agregar mensajes a sesion activa
    sm.add_message("user", "Hola Genesis")
    sm.add_message("assistant", "Hola!")
    sm.add_message("user", "Como estas?")

    msgs = sm.get_messages()
    test("3 mensajes en sesion", len(msgs) == 3)
    test("Primer mensaje correcto", msgs[0]["content"] == "Hola Genesis")

    msgs_limited = sm.get_messages(limit=2)
    test("Limit 2 mensajes", len(msgs_limited) == 2)
    test("Ultimos 2 mensajes", msgs_limited[0]["content"] == "Hola!")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 17: SessionManager — Persistencia
# ============================================================
print("\n=== TEST: SessionManager — Persistencia ===")

tmpdir = tempfile.mkdtemp()
try:
    # Crear y guardar
    sm1 = SessionManager(base_dir=tmpdir)
    sm1.create("persistente", "Test de persistencia")
    sm1.add_message("user", "Mensaje persistente")
    sm1.save_all()

    # Verificar archivos
    sessions_dir = os.path.join(tmpdir, "memory_data", "sessions")
    test("Directorio sessions existe", os.path.isdir(sessions_dir))

    files = os.listdir(sessions_dir)
    test("Hay archivos JSON", len(files) >= 1)
    test("Archivo persistente.json existe", "persistente.json" in files)

    # Cargar en nueva instancia
    sm2 = SessionManager(base_dir=tmpdir)
    test("Sesion persistente cargada", "persistente" in sm2.sessions)
    test("Mensajes preservados", len(sm2.sessions["persistente"].messages) == 1)
    test("Contenido correcto", sm2.sessions["persistente"].messages[0]["content"] == "Mensaje persistente")

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 18: SessionManager — List/Status
# ============================================================
print("\n=== TEST: SessionManager — List/Status ===")

tmpdir = tempfile.mkdtemp()
try:
    sm = SessionManager(base_dir=tmpdir)
    sm.create("session_a", "Tema A")
    sm.create("session_b", "Tema B")

    listing = sm.list_sessions()
    test("list_sessions retorna string", isinstance(listing, str))
    test("list_sessions contiene session_a", "session_a" in listing)
    test("list_sessions contiene session_b", "session_b" in listing)
    test("list_sessions muestra ACTIVA", "ACTIVA" in listing)
    test("list_sessions muestra total", "Total" in listing)

    status = sm.status()
    test("status retorna string", isinstance(status, str))
    test("status contiene sesiones", "sesiones" in status.lower() or "Sessions" in status)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 19: Imports en genesis.py
# ============================================================
print("\n=== TEST: Imports en genesis.py ===")

# Verificar que genesis.py importa los nuevos modulos
import importlib
test("Import AgentSystem", importlib.import_module("core.agents") is not None)
test("Import WorkflowEngine", importlib.import_module("core.workflows") is not None)
test("Import SessionManager", importlib.import_module("core.sessions") is not None)

# Verificar que genesis.py tiene las lineas de import
with open("genesis.py", "r", encoding="utf-8") as f:
    genesis_src = f.read()

test("genesis.py importa AgentSystem", "from core.agents import AgentSystem" in genesis_src)
test("genesis.py importa WorkflowEngine", "from core.workflows import WorkflowEngine" in genesis_src)
test("genesis.py importa SessionManager", "from core.sessions import SessionManager" in genesis_src)


# ============================================================
# TEST 20: Comandos en genesis.py
# ============================================================
print("\n=== TEST: Comandos en genesis.py ===")

test("Comando /agents", '"/agents"' in genesis_src or "== \"/agents\"" in genesis_src or '/agents' in genesis_src)
test("Comando /delegate", '/delegate' in genesis_src)
test("Comando /workflows", '/workflows' in genesis_src)
test("Comando /workflow run", '/workflow run' in genesis_src)
test("Comando /sessions", '/sessions' in genesis_src)
test("Comando /session new", '/session new' in genesis_src)
test("Comando /session switch", '/session switch' in genesis_src)
test("Comando /session delete", '/session delete' in genesis_src)
test("Comando /session rename", '/session rename' in genesis_src)
test("Comando /agent toggle", '/agent toggle' in genesis_src)
test("Comando /agent history", '/agent history' in genesis_src)
test("Comando /workflow history", '/workflow history' in genesis_src)


# ============================================================
# TEST 21: Config version
# ============================================================
print("\n=== TEST: Config version ===")
from config import GENESIS_VERSION
test("Version es 1.6.0", GENESIS_VERSION == "1.6.0")


# ============================================================
# TEST 22: Status incluye nuevos subsistemas
# ============================================================
print("\n=== TEST: Status incluye nuevos subsistemas ===")

test("_cmd_status tiene AGENTES", "AGENTES:" in genesis_src or "agent_system.status()" in genesis_src)
test("_cmd_status tiene WORKFLOWS", "WORKFLOWS:" in genesis_src or "workflow_engine.status()" in genesis_src)
test("_cmd_status tiene SESIONES", "SESIONES:" in genesis_src or "session_manager.status()" in genesis_src)


# ============================================================
# TEST 23: Help incluye nuevos comandos
# ============================================================
print("\n=== TEST: Help incluye nuevos comandos ===")

test("Help documenta /agents", "/agents" in genesis_src and "Listar agentes" in genesis_src)
test("Help documenta /delegate", "/delegate" in genesis_src and "Delegar tarea" in genesis_src)
test("Help documenta /workflows", "/workflows" in genesis_src and "Listar workflows" in genesis_src)
test("Help documenta /sessions", "/sessions" in genesis_src and "Listar todas las sesiones" in genesis_src)
test("Help documenta MULTI-AGENTE", "SISTEMA MULTI-AGENTE" in genesis_src)
test("Help documenta SESIONES seccion", "SESIONES:" in genesis_src)


# ============================================================
# TEST 24: Edge cases
# ============================================================
print("\n=== TEST: Edge cases ===")

# AgentSystem — detect_agent con string vacio
test("detect_agent string vacio", system.detect_agent("") is None)

# Session con ID vacio
s_empty = Session("", name="Empty")
test("Session con ID vacio", s_empty.session_id == "")

# SessionManager create con ID invalido
tmpdir = tempfile.mkdtemp()
try:
    sm = SessionManager(base_dir=tmpdir)
    result = sm.create("!!!", "Bad ID")
    test("ID invalido rechazado", "invalido" in result.lower())

    # Create con espacios
    result = sm.create("mi sesion", "With spaces")
    test("Espacios se sanitizan", "mi_sesion" in sm.sessions or "misesion" in sm.sessions)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# WorkflowEngine — run con input vacio
result = engine.run("code_review", "")
test("Run con input vacio no crashea", isinstance(result, dict))

# AgentSystem — delegate con todos desactivados
system_disabled = AgentSystem(brain=None)
for agent in system_disabled.agents.values():
    agent.enabled = False
# Con todos disabled, debe manejar gracefully
detected = system_disabled.detect_agent("codigo python")
test("Todos disabled -> detect None", detected is None)


# ============================================================
# TEST 25: KEYWORD_MAP cobertura
# ============================================================
print("\n=== TEST: KEYWORD_MAP cobertura ===")

km = AgentSystem.KEYWORD_MAP
test("KEYWORD_MAP tiene busca", "busca" in km)
test("KEYWORD_MAP tiene codigo", "codigo" in km)
test("KEYWORD_MAP tiene seguridad", "seguridad" in km)
test("KEYWORD_MAP tiene planifica", "planifica" in km)
test("KEYWORD_MAP tiene test", "test" in km)
test("KEYWORD_MAP tiene refactoriza", "refactoriza" in km)
test("KEYWORD_MAP mapea busca->research", km["busca"] == "research")
test("KEYWORD_MAP mapea codigo->code", km["codigo"] == "code")
test("KEYWORD_MAP mapea seguridad->security", km["seguridad"] == "security")


# ============================================================
# RESULTADO FINAL
# ============================================================
print(f"\n{'='*50}")
total = _passed + _failed
print(f"Tests v1.6: {_passed}/{total} passed, {_failed} failed")
if _failed > 0:
    print("ALGUNOS TESTS FALLARON!")
    sys.exit(1)
else:
    print("TODOS LOS TESTS PASARON!")
    sys.exit(0)
