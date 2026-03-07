"""
Tests para Genesis v1.7.0
- AutoLearner (patrones, reglas, ajustes, persistencia)
- ConversationAnalytics (topics, engagement, gaps, report)
- AdaptivePrompts (experimentos, variantes, feedback, A/B)
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
# TEST 1: PatternTracker
# ============================================================
print("\n=== TEST: PatternTracker ===")
from core.auto_learner import PatternTracker, LearningRule, AutoLearner

pt = PatternTracker()

# Sin datos
test("Success rate sin datos = 0.5", pt.success_rate("anything") == 0.5)
test("Ranking vacio", len(pt.get_ranking()) == 0)

# Registrar datos
pt.record("coder", True)
pt.record("coder", True)
pt.record("coder", False)
pt.record("researcher", True)
pt.record("researcher", True)
pt.record("researcher", True)
pt.record("analyst", False)
pt.record("analyst", False)

test("Coder rate = 2/3", abs(pt.success_rate("coder") - 2/3) < 0.01)
test("Researcher rate = 1.0", pt.success_rate("researcher") == 1.0)
test("Analyst rate = 0.0", pt.success_rate("analyst") == 0.0)

# Ranking (necesita min 2 muestras)
ranking = pt.get_ranking()
test("Ranking tiene 3 items", len(ranking) == 3)
test("Researcher es primero", ranking[0]["key"] == "researcher")
test("Analyst es ultimo", ranking[-1]["key"] == "analyst")

# Serialization
d = pt.to_dict()
test("to_dict retorna dict", isinstance(d, dict))
test("to_dict tiene coder", "coder" in d)

pt2 = PatternTracker()
pt2.from_dict(d)
test("from_dict preserva rates", abs(pt2.success_rate("coder") - 2/3) < 0.01)


# ============================================================
# TEST 2: LearningRule
# ============================================================
print("\n=== TEST: LearningRule ===")

rule = LearningRule(
    rule_type="agent_preference",
    description="Coder es efectivo",
    confidence=0.85,
    action="boost_priority:coder",
    data={"agent": "coder", "rate": 0.85},
)

test("Rule tiene type", rule.rule_type == "agent_preference")
test("Rule tiene description", "Coder" in rule.description)
test("Rule tiene confidence", rule.confidence == 0.85)
test("Rule tiene action", rule.action == "boost_priority:coder")
test("Rule tiene data", rule.data["agent"] == "coder")

# Serialization
d = rule.to_dict()
test("to_dict tiene rule_type", d["rule_type"] == "agent_preference")
test("to_dict tiene confidence", d["confidence"] == 0.85)

r2 = LearningRule.from_dict(d)
test("from_dict preserva type", r2.rule_type == "agent_preference")
test("from_dict preserva confidence", r2.confidence == 0.85)
test("from_dict preserva action", r2.action == "boost_priority:coder")


# ============================================================
# TEST 3: AutoLearner — Basico
# ============================================================
print("\n=== TEST: AutoLearner — Basico ===")

tmpdir = tempfile.mkdtemp()
try:
    learner = AutoLearner(base_dir=tmpdir)

    test("Totals inician en 0", learner.total_positive == 0)
    test("Sin reglas al inicio", len(learner.rules) == 0)

    # Registrar interacciones
    learner.record_interaction(agent="coder", template="code", feedback=1, tags=["python"])
    learner.record_interaction(agent="coder", template="code", feedback=1, tags=["python"])
    learner.record_interaction(agent="researcher", template="research", feedback=-1, tags=["web"])

    test("Total positive = 2", learner.total_positive == 2)
    test("Total negative = 1", learner.total_negative == 1)
    test("3 interacciones registradas", len(learner.interactions) == 3)

    # Tracker de agentes
    test("Coder rate > 0.5", learner.agent_tracker.success_rate("coder") > 0.5)
    test("Researcher rate = 0", learner.agent_tracker.success_rate("researcher") == 0.0)

    # Tracker de templates
    test("Code rate > 0.5", learner.template_tracker.success_rate("code") > 0.5)

    # Tracker de combos
    test("coder+code registrado", learner.combo_tracker.counts["coder+code"]["total"] == 2)

    # Feedback neutral no afecta trackers
    learner.record_interaction(agent="coder", feedback=0)
    test("Neutral no cambia positive", learner.total_neutral == 1)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 4: AutoLearner — Insights y Reglas
# ============================================================
print("\n=== TEST: AutoLearner — Insights y Reglas ===")

tmpdir = tempfile.mkdtemp()
try:
    learner = AutoLearner(base_dir=tmpdir)

    # Generar muchas interacciones para triggear analisis
    for _ in range(6):
        learner.record_interaction(agent="coder", template="code", feedback=1)
    for _ in range(6):
        learner.record_interaction(agent="analyst", template="analysis", feedback=-1)

    # Forzar analisis
    learner._analyze_patterns()

    test("Insights no vacio", len(learner.get_insights()) > 50)
    test("Insights contiene Satisfaccion", "Satisfaccion" in learner.get_insights())

    # Ajustes de agentes
    adj = learner.get_agent_adjustments()
    test("Ajustes es dict", isinstance(adj, dict))

    # Status
    status = learner.status()
    test("Status contiene AutoLearner", "AutoLearner" in status)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 5: AutoLearner — Persistencia
# ============================================================
print("\n=== TEST: AutoLearner — Persistencia ===")

tmpdir = tempfile.mkdtemp()
try:
    l1 = AutoLearner(base_dir=tmpdir)
    l1.record_interaction(agent="coder", feedback=1)
    l1.record_interaction(agent="coder", feedback=1)
    l1.record_interaction(agent="analyst", feedback=-1)
    l1.save()

    # Verificar archivo existe
    filepath = os.path.join(tmpdir, "memory_data", "learning", "auto_learner.json")
    test("Archivo persistencia existe", os.path.exists(filepath))

    # Cargar en nueva instancia
    l2 = AutoLearner(base_dir=tmpdir)
    test("Positive preservado", l2.total_positive == 2)
    test("Negative preservado", l2.total_negative == 1)
    test("Tracker preservado", l2.agent_tracker.success_rate("coder") > 0.5)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 6: TopicTracker
# ============================================================
print("\n=== TEST: TopicTracker ===")
from core.conversation_analytics import TopicTracker, EngagementMetrics, KnowledgeGapDetector, ConversationAnalytics

tt = TopicTracker()

# Deteccion de topicos
topics = tt.detect_topics("escribe un programa en python con flask")
test("Detecta programacion", "programacion" in topics)
test("Detecta web", "web" in topics)

topics2 = tt.detect_topics("busca vulnerabilidades de seguridad en el servidor")
test("Detecta seguridad", "seguridad" in topics2)

topics3 = tt.detect_topics("hola, como estas?")
test("Sin topicos en saludo", len(topics3) == 0)

topics4 = tt.detect_topics("entrena un modelo de machine learning con pytorch")
test("Detecta ia_ml", "ia_ml" in topics4)

# Registro y ranking
tt.record("escribe una funcion en python para ordenar datos")
tt.record("programa un servidor web con flask")
tt.record("analiza la seguridad del sistema")

top = tt.get_top_topics()
test("Top topics no vacio", len(top) > 0)
test("Programacion tiene mas hits", top[0][0] == "programacion")

# Serialization
d = tt.to_dict()
test("to_dict tiene topic_counts", "topic_counts" in d)
tt2 = TopicTracker()
tt2.from_dict(d)
test("from_dict preserva counts", tt2.topic_counts == tt.topic_counts)


# ============================================================
# TEST 7: EngagementMetrics
# ============================================================
print("\n=== TEST: EngagementMetrics ===")

em = EngagementMetrics()

em.track_message("user", "Hola Genesis, como funciona Python?")
em.track_message("assistant", "Python es un lenguaje interpretado...")
em.track_message("user", "Y como hago una lista?")

test("Total messages = 3", em.total_messages == 3)
test("Query lengths registrados", len(em.query_lengths) == 2)
test("Avg query length > 0", em.get_avg_query_length() > 0)

em.track_response_time(2.5)
em.track_response_time(3.0)
test("Avg response time", abs(em.get_avg_response_time() - 2.75) < 0.01)

# Distribucion horaria
test("Mensajes por hora registrados", len(em.messages_per_hour) > 0)
test("Mensajes por dia registrados", len(em.messages_per_day) > 0)

# Sesion
em.end_session()
test("Sesion registrada", em.total_sessions == 1)
test("Session length guardada", len(em.session_lengths) == 1)
test("Avg session = 3 msgs", em.get_avg_session_length() == 3.0)

# Serialization
d = em.to_dict()
test("to_dict tiene total_messages", d["total_messages"] == 3)
em2 = EngagementMetrics()
em2.from_dict(d)
test("from_dict preserva total", em2.total_messages == 3)


# ============================================================
# TEST 8: KnowledgeGapDetector
# ============================================================
print("\n=== TEST: KnowledgeGapDetector ===")

gd = KnowledgeGapDetector()

# Registrar query y feedback negativo
gd.track_query("como implementar backpropagation?", tags=["ia_ml"])
gd.track_feedback(-1)
test("Gap registrado", len(gd.gaps) == 1)
test("Gap tiene query", "backpropagation" in gd.gaps[0]["query"])

# Otra query con feedback positivo
gd.track_query("que es una variable?", tags=["general"])
gd.track_feedback(1)
test("No gap para positivo", len(gd.gaps) == 1)

# Resolver gap anterior
gd.track_query("como implementar backpropagation?", tags=["ia_ml"])
gd.track_feedback(1)
test("Gap resuelto", len(gd.gaps) == 0)
test("Resuelto guardado", len(gd.resolved) == 1)

# Gap topics
gd.track_query("entrena un transformer", tags=["ia_ml"])
gd.track_feedback(-1)
gap_topics = gd.get_gap_topics()
test("Gap topics contiene ia_ml", "ia_ml" in gap_topics)

# Serialization
d = gd.to_dict()
test("to_dict tiene gaps", "gaps" in d)
gd2 = KnowledgeGapDetector()
gd2.from_dict(d)
test("from_dict preserva gaps", len(gd2.gaps) == len(gd.gaps))


# ============================================================
# TEST 9: ConversationAnalytics — Completo
# ============================================================
print("\n=== TEST: ConversationAnalytics — Completo ===")

tmpdir = tempfile.mkdtemp()
try:
    analytics = ConversationAnalytics(base_dir=tmpdir)

    # Trackear mensajes
    analytics.track_message("user", "escribe un programa en python para ordenar una lista")
    analytics.track_message("assistant", "Aqui tienes un programa para ordenar...")
    analytics.track_message("user", "ahora busca vulnerabilidades de seguridad")
    analytics.track_response(agent="coder", feedback=1, response_time=2.0)

    # Reporte
    report = analytics.generate_report()
    test("Reporte no vacio", len(report) > 50)
    test("Reporte contiene Mensajes", "Mensajes" in report)

    # Status
    status = analytics.status()
    test("Status contiene Analytics", "Analytics" in status)

    # Persistencia
    analytics.save()
    filepath = os.path.join(tmpdir, "memory_data", "analytics", "conversation_analytics.json")
    test("Archivo analytics existe", os.path.exists(filepath))

    # Cargar en nueva instancia
    a2 = ConversationAnalytics(base_dir=tmpdir)
    test("Total messages preservado", a2.engagement.total_messages == 3)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 10: PromptVariant
# ============================================================
print("\n=== TEST: PromptVariant ===")
from core.adaptive_prompts import PromptVariant, PromptExperiment, AdaptivePrompts

pv = PromptVariant(text="Eres un asistente util.", label="formal")

test("Variant tiene text", "asistente" in pv.text)
test("Variant tiene label", pv.label == "formal")
test("Success rate sin datos = 0.5", pv.success_rate == 0.5)

pv.record(True)
pv.record(True)
pv.record(False)
test("Total = 3", pv.total == 3)
test("Positive = 2", pv.positive == 2)
test("Success rate = 2/3", abs(pv.success_rate - 2/3) < 0.01)

# Serialization
d = pv.to_dict()
test("to_dict tiene success_rate", "success_rate" in d)
pv2 = PromptVariant.from_dict(d)
test("from_dict preserva text", pv2.text == pv.text)
test("from_dict preserva stats", pv2.total == 3)


# ============================================================
# TEST 11: PromptExperiment
# ============================================================
print("\n=== TEST: PromptExperiment ===")

exp = PromptExperiment(
    name="test_exp",
    base_prompt="Eres un asistente.",
    min_samples=3,
)

test("Experiment tiene name", exp.name == "test_exp")
test("Experiment tiene 1 variant (original)", len(exp.variants) == 1)
test("State = running", exp.state == "running")
test("Winner = None", exp.winner_index is None)

# Agregar variantes
idx1 = exp.add_variant("Eres un experto amable.", label="amable")
idx2 = exp.add_variant("Eres un tecnico conciso.", label="conciso")
test("3 variantes total", len(exp.variants) == 3)
test("idx1 = 1", idx1 == 1)
test("idx2 = 2", idx2 == 2)

# Seleccion
idx, text = exp.get_variant(strategy="random")
test("get_variant retorna tuple", isinstance(idx, int) and isinstance(text, str))

# Feedback — crear ganador claro (original 100% vs conciso 50% vs amable 0%)
for _ in range(4):
    exp.record_feedback(0, True)  # original: 4/4 = 100%
for _ in range(4):
    exp.record_feedback(1, False)  # amable: 0/4 = 0%
exp.record_feedback(2, True)   # conciso: 2/4 = 50%
exp.record_feedback(2, True)
exp.record_feedback(2, False)
exp.record_feedback(2, False)
# original=100%, conciso=50%, amable=0% -> diff original-conciso = 50% > 15% -> concluye
test("Experiment concluido", exp.state == "concluded")
test("Hay ganador", exp.winner_index is not None)

# Results
results = exp.get_results()
test("Results tiene name", results["name"] == "test_exp")
test("Results tiene state", results["state"] == "concluded")
test("Results tiene variants", len(results["variants"]) == 3)


# ============================================================
# TEST 12: PromptExperiment — No concluye sin suficientes muestras
# ============================================================
print("\n=== TEST: PromptExperiment — Min samples ===")

exp2 = PromptExperiment(name="early", base_prompt="Base.", min_samples=10)
exp2.add_variant("Variante A.")

# Solo 3 muestras (min es 10)
for _ in range(3):
    exp2.record_feedback(0, True)
    exp2.record_feedback(1, False)

test("No concluye con pocas muestras", exp2.state == "running")

# Serialization
d = exp2.to_dict()
exp3 = PromptExperiment.from_dict(d)
test("from_dict preserva state", exp3.state == "running")
test("from_dict preserva variants", len(exp3.variants) == 2)
test("from_dict preserva min_samples", exp3.min_samples == 10)


# ============================================================
# TEST 13: AdaptivePrompts — CRUD
# ============================================================
print("\n=== TEST: AdaptivePrompts — CRUD ===")

tmpdir = tempfile.mkdtemp()
try:
    ap = AdaptivePrompts(base_dir=tmpdir)

    # Crear
    result = ap.create_experiment("saludo", "Saluda.", ["Hola!", "Buenos dias!"])
    test("Crear experiment OK", "creado" in result)
    test("Experiment existe", "saludo" in ap.experiments)
    test("3 variantes", len(ap.experiments["saludo"].variants) == 3)

    # No duplicar
    result = ap.create_experiment("saludo", "Otro.", [])
    test("No permite duplicados", "ya existe" in result)

    # Get variant
    text = ap.get_variant("saludo")
    test("get_variant retorna texto", isinstance(text, str) and len(text) > 0)

    # Get variant inexistente
    test("Variant inexistente = None", ap.get_variant("fake") is None)

    # Record feedback
    result = ap.record_feedback("saludo", positive=True)
    test("Feedback registrado", "registrado" in result)

    # Get best
    best = ap.get_best("saludo")
    test("Get best retorna texto", isinstance(best, str))

    # List
    listing = ap.list_experiments()
    test("List contiene saludo", "saludo" in listing)

    # Delete
    result = ap.delete_experiment("saludo")
    test("Delete OK", "eliminado" in result)
    test("Ya no existe", "saludo" not in ap.experiments)

    # Active experiments
    ap.create_experiment("exp1", "Base1.", ["V1."])
    ap.create_experiment("exp2", "Base2.", ["V2."])
    active = ap.get_active_experiments()
    test("2 experiments activos", len(active) == 2)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 14: AdaptivePrompts — Persistencia
# ============================================================
print("\n=== TEST: AdaptivePrompts — Persistencia ===")

tmpdir = tempfile.mkdtemp()
try:
    ap1 = AdaptivePrompts(base_dir=tmpdir)
    ap1.create_experiment("test_persist", "Base prompt.", ["Variante A."])
    ap1.get_variant("test_persist")
    ap1.record_feedback("test_persist", positive=True)
    ap1.save()

    filepath = os.path.join(tmpdir, "memory_data", "adaptive_prompts", "adaptive_prompts.json")
    test("Archivo persistencia existe", os.path.exists(filepath))

    ap2 = AdaptivePrompts(base_dir=tmpdir)
    test("Experiment cargado", "test_persist" in ap2.experiments)
    test("Variantes preservadas", len(ap2.experiments["test_persist"].variants) == 2)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 15: AdaptivePrompts — Status
# ============================================================
print("\n=== TEST: AdaptivePrompts — Status ===")

tmpdir = tempfile.mkdtemp()
try:
    ap = AdaptivePrompts(base_dir=tmpdir)
    status = ap.status()
    test("Status contiene AdaptivePrompts", "AdaptivePrompts" in status)
    test("Status contiene 0 experiments", "0 experimentos" in status)

    ap.create_experiment("x", "X.", ["Y."])
    status2 = ap.status()
    test("Status actualiza count", "1 experimentos" in status2)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 16: Imports en genesis.py
# ============================================================
print("\n=== TEST: Imports en genesis.py ===")

import importlib
test("Import AutoLearner", importlib.import_module("core.auto_learner") is not None)
test("Import ConversationAnalytics", importlib.import_module("core.conversation_analytics") is not None)
test("Import AdaptivePrompts", importlib.import_module("core.adaptive_prompts") is not None)

with open("genesis.py", "r", encoding="utf-8") as f:
    genesis_src = f.read()

test("genesis.py importa AutoLearner", "from core.auto_learner import AutoLearner" in genesis_src)
test("genesis.py importa ConversationAnalytics", "from core.conversation_analytics import ConversationAnalytics" in genesis_src)
test("genesis.py importa AdaptivePrompts", "from core.adaptive_prompts import AdaptivePrompts" in genesis_src)


# ============================================================
# TEST 17: Comandos en genesis.py
# ============================================================
print("\n=== TEST: Comandos en genesis.py ===")

test("Comando /learn", "/learn" in genesis_src and "get_insights" in genesis_src)
test("Comando /learn rules", "/learn rules" in genesis_src)
test("Comando /learn adjustments", "/learn adjustments" in genesis_src)
test("Comando /analytics", "/analytics" in genesis_src and "generate_report" in genesis_src)
test("Comando /analytics gaps", "/analytics gaps" in genesis_src)
test("Comando /experiments", "/experiments" in genesis_src and "list_experiments" in genesis_src)
test("Comando /experiment create", "/experiment create" in genesis_src)
test("Comando /experiment delete", "/experiment delete" in genesis_src)


# ============================================================
# TEST 18: Status incluye nuevos subsistemas
# ============================================================
print("\n=== TEST: Status incluye nuevos subsistemas ===")

test("_cmd_status tiene AUTO-LEARNER", "AUTO-LEARNER:" in genesis_src)
test("_cmd_status tiene ANALYTICS", "ANALYTICS:" in genesis_src)
test("_cmd_status tiene ADAPTIVE PROMPTS", "ADAPTIVE PROMPTS:" in genesis_src)


# ============================================================
# TEST 19: Help incluye nuevos comandos
# ============================================================
print("\n=== TEST: Help incluye nuevos comandos ===")

test("Help documenta /learn", "/learn" in genesis_src and "insights" in genesis_src.lower())
test("Help documenta /analytics", "/analytics" in genesis_src and "Reporte" in genesis_src)
test("Help documenta /experiments", "/experiments" in genesis_src)
test("Help seccion APRENDIZAJE", "APRENDIZAJE ADAPTATIVO" in genesis_src)
test("Help seccion ANALYTICS", "ANALYTICS:" in genesis_src)
test("Help seccion EXPERIMENTOS", "EXPERIMENTOS A/B" in genesis_src)


# ============================================================
# TEST 20: Config version
# ============================================================
print("\n=== TEST: Config version ===")
# Reimportar config para obtener valor actualizado
import importlib
import config
importlib.reload(config)
test("Version es 1.7.0", config.GENESIS_VERSION >= "1.7.0")


# ============================================================
# TEST 21: Feedback integrado con learning
# ============================================================
print("\n=== TEST: Feedback integrado con learning ===")

test("genesis.py feedback + usa auto_learner", "auto_learner.record_interaction" in genesis_src)
test("genesis.py feedback + usa analytics", "analytics.track_response" in genesis_src)
test("genesis.py trackea _last_agent", "_last_agent" in genesis_src)
test("genesis.py trackea _last_template", "_last_template" in genesis_src)
test("genesis.py trackea _last_response_time", "_last_response_time" in genesis_src)


# ============================================================
# TEST 22: Edge cases
# ============================================================
print("\n=== TEST: Edge cases ===")

# AutoLearner con string vacio
tmpdir = tempfile.mkdtemp()
try:
    learner = AutoLearner(base_dir=tmpdir)
    learner.record_interaction(agent="", template="", feedback=0)
    test("Interaction con datos vacios no crashea", True)

    # Insights sin datos
    insights = learner.get_insights()
    test("Insights sin datos no crashea", "Sin datos" in insights or "0" in insights)

    # Get best agent sin datos
    best = learner.get_best_agent_for_template("nonexistent")
    test("Best agent sin datos = None", best is None)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# ConversationAnalytics con datos vacios
tmpdir = tempfile.mkdtemp()
try:
    analytics = ConversationAnalytics(base_dir=tmpdir)
    report = analytics.generate_report()
    test("Report vacio no crashea", isinstance(report, str))

    analytics.end_session()
    test("End session vacia no crashea", True)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# AdaptivePrompts feedback sin seleccion previa
tmpdir = tempfile.mkdtemp()
try:
    ap = AdaptivePrompts(base_dir=tmpdir)
    ap.create_experiment("test", "Base.", ["V1."])
    result = ap.record_feedback("test", positive=True)
    test("Feedback sin seleccion previa", "seleccion" in result.lower() or "activa" in result.lower())

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)

# PromptExperiment con 1 sola variante no puede concluir
exp_single = PromptExperiment(name="single", base_prompt="Solo uno.", min_samples=2)
for _ in range(5):
    exp_single.record_feedback(0, True)
# Con 1 sola variante no hay "segundo" para comparar, pero tampoco debe crashear
test("Single variant no crashea", exp_single.state in ("running", "concluded"))


# ============================================================
# TEST 23: AutoLearner max interactions limit
# ============================================================
print("\n=== TEST: AutoLearner — Limites ===")

tmpdir = tempfile.mkdtemp()
try:
    learner = AutoLearner(base_dir=tmpdir)
    learner.max_interactions = 10
    for i in range(20):
        learner.record_interaction(agent="coder", feedback=1)
    test("Interactions limitadas", len(learner.interactions) <= 10)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 24: ConversationAnalytics — Topic detection cobertura
# ============================================================
print("\n=== TEST: Topic detection cobertura ===")

tt = TopicTracker()

test("Detecta datos", "datos" in tt.detect_topics("analiza los datos en sql"))
test("Detecta sistema", "sistema" in tt.detect_topics("configura linux"))
test("Detecta creative", "creative" in tt.detect_topics("escribe un poema"))
test("Detecta general", "general" in tt.detect_topics("explica que es"))

# Trend
tt.record("escribe codigo python")
tt.record("escribe mas codigo python")
tt.record("ahora habla de seguridad")
trend = tt.get_recent_trend()
test("Trend no vacio", len(trend) > 0)


# ============================================================
# RESULTADO FINAL
# ============================================================
print(f"\n{'='*50}")
total = _passed + _failed
print(f"Tests v1.7: {_passed}/{total} passed, {_failed} failed")
if _failed > 0:
    print("ALGUNOS TESTS FALLARON!")
    sys.exit(1)
else:
    print("TODOS LOS TESTS PASARON!")
    sys.exit(0)
