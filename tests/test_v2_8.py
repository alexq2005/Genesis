"""
GENESIS — Tests v2.8: Reasoning Architecture
Tests para HypothesisEngine, ExplanationEngine, DialogueStrategist
e integración en genesis.py y web_ui.py.
"""
import sys
import os
import time
import tempfile
import shutil

# UTF-8 para Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

passed = 0
failed = 0
errors = []


def test(name, condition):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        errors.append(name)
        print(f"  [FAIL] {name}")


print("=" * 60)
print("GENESIS v2.8 — Test Suite: Reasoning Architecture")
print("=" * 60)

# ============================================================
# HYPOTHESIS ENGINE — Evidence
# ============================================================
print("\n--- Evidence ---")
from core.hypothesis_engine import Evidence, Hypothesis, HypothesisGenerator, HypothesisEvaluator, HypothesisEngine

e = Evidence("el cielo es azul", supports=True, weight=1.0, source="observacion")
test("Evidence: text correcto", e.text == "el cielo es azul")
test("Evidence: supports correcto", e.supports is True)
test("Evidence: weight correcto", e.weight == 1.0)
test("Evidence: source correcto", e.source == "observacion")
test("Evidence: timestamp > 0", e.timestamp > 0)

e_neg = Evidence("contradiccion", supports=False, weight=0.5)
test("Evidence: negative supports=False", e_neg.supports is False)

# Clamp weight
e_clamp = Evidence("test", weight=5.0)
test("Evidence: clamp weight max 2.0", e_clamp.weight == 2.0)
e_clamp2 = Evidence("test", weight=-1.0)
test("Evidence: clamp weight min 0.0", e_clamp2.weight == 0.0)

# to_dict / from_dict
d = e.to_dict()
test("Evidence: to_dict tiene text", d["text"] == "el cielo es azul")
test("Evidence: to_dict tiene supports", d["supports"] is True)
e2 = Evidence.from_dict(d)
test("Evidence: from_dict restaura text", e2.text == "el cielo es azul")
test("Evidence: from_dict restaura weight", e2.weight == 1.0)

# ============================================================
# HYPOTHESIS ENGINE — Hypothesis
# ============================================================
print("\n--- Hypothesis ---")

h = Hypothesis("el usuario prefiere respuestas cortas", domain="ux", context="observacion")
test("Hypothesis: statement correcto", h.statement == "el usuario prefiere respuestas cortas")
test("Hypothesis: domain correcto", h.domain == "ux")
test("Hypothesis: status = active", h.status == "active")
test("Hypothesis: confidence = 0.5", h.confidence == 0.5)
test("Hypothesis: plausibility = 0.5 sin evidencia", h.plausibility == 0.5)
test("Hypothesis: hyp_id generado", len(h.hyp_id) == 10)
test("Hypothesis: evidence_for vacio", len(h.evidence_for) == 0)
test("Hypothesis: evidence_against vacio", len(h.evidence_against) == 0)
test("Hypothesis: age_hours >= 0", h.age_hours >= 0)

# Add supporting evidence
h.add_evidence(Evidence("resumen breve", supports=True, weight=1.0))
h.add_evidence(Evidence("solo el codigo", supports=True, weight=1.0))
test("Hypothesis: evidence_for = 2", len(h.evidence_for) == 2)
test("Hypothesis: confidence > 0.5 con soporte", h.confidence > 0.5)

# Add contradicting evidence
h.add_evidence(Evidence("explica detalladamente", supports=False, weight=0.5))
test("Hypothesis: evidence_against = 1", len(h.evidence_against) == 1)
test("Hypothesis: confidence ajustada", h.confidence > 0.5)  # 2.0 vs 0.5

# Auto-confirm with lots of supporting evidence
h_confirm = Hypothesis("test confirmacion")
for _ in range(5):
    h_confirm.add_evidence(Evidence("soporte", supports=True, weight=1.0))
test("Hypothesis: auto-confirm con mucha evidencia", h_confirm.status == "confirmed")

# Auto-refute
h_refute = Hypothesis("test refutacion")
for _ in range(5):
    h_refute.add_evidence(Evidence("contra", supports=False, weight=1.0))
test("Hypothesis: auto-refute con mucha contradiccion", h_refute.status == "refuted")

# Plausibility
test("Hypothesis: plausibility en rango", 0.0 <= h.plausibility <= 1.0)

# to_dict / from_dict
d_h = h.to_dict()
test("Hypothesis: to_dict tiene statement", d_h["statement"] == "el usuario prefiere respuestas cortas")
test("Hypothesis: to_dict tiene evidence_for", len(d_h["evidence_for"]) == 2)
test("Hypothesis: to_dict tiene evidence_against", len(d_h["evidence_against"]) == 1)

h2 = Hypothesis.from_dict(d_h)
test("Hypothesis: from_dict restaura statement", h2.statement == h.statement)
test("Hypothesis: from_dict restaura evidence", len(h2.evidence_for) == 2)
test("Hypothesis: from_dict restaura status", h2.status == h.status)

# ============================================================
# HYPOTHESIS ENGINE — HypothesisGenerator
# ============================================================
print("\n--- HypothesisGenerator ---")

hg = HypothesisGenerator()

# Especulativo
hyps = hg.extract_hypotheses("quizas el error esta en la configuracion del modelo")
test("HypothesisGenerator: detecta especulativo", len(hyps) > 0)
test("HypothesisGenerator: tipo especulativo", hyps[0]["type"] == "speculative" if hyps else False)

# Creencia
hyps2 = hg.extract_hypotheses("creo que el problema es la memoria insuficiente")
test("HypothesisGenerator: detecta creencia", len(hyps2) > 0)

# Condicional
hyps3 = hg.extract_hypotheses("si aumentamos el batch size, entonces mejora la precision")
test("HypothesisGenerator: detecta condicional", len(hyps3) > 0)

# Sin hipotesis
hyps4 = hg.extract_hypotheses("hola como estas")
test("HypothesisGenerator: sin hipotesis en saludo", len(hyps4) == 0)

# generate_from_observations
obs = ["el modelo tarda mucho en responder", "el modelo es lento con prompts largos",
       "el modelo necesita optimizacion"]
hyps5 = hg.generate_from_observations(obs)
test("HypothesisGenerator: genera desde observaciones", len(hyps5) > 0)

# Con pocas observaciones
hyps6 = hg.generate_from_observations(["solo una"])
test("HypothesisGenerator: pocas observaciones = []", len(hyps6) == 0)

# ============================================================
# HYPOTHESIS ENGINE — HypothesisEvaluator
# ============================================================
print("\n--- HypothesisEvaluator ---")

he = HypothesisEvaluator()

hyp = Hypothesis("el modelo funciona mejor con prompts cortos")

# Evaluar con texto relevante que soporta
result = he.evaluate(hyp, "los prompts cortos dan mejores resultados y el modelo responde rapido")
test("HypothesisEvaluator: incrementa evaluations", hyp.evaluations == 1)
test("HypothesisEvaluator: result tiene relevance", "relevance" in result)

# Evaluar con texto irrelevante
result2 = he.evaluate(hyp, "el clima esta nublado hoy")
test("HypothesisEvaluator: baja relevance para irrelevante", result2["relevance"] < 0.3)

# rank_hypotheses
hyps_list = [
    Hypothesis("alta plausibilidad"),
    Hypothesis("baja plausibilidad"),
]
hyps_list[0].add_evidence(Evidence("soporte", supports=True, weight=1.0))
ranked = he.rank_hypotheses(hyps_list)
test("HypothesisEvaluator: rank retorna lista", isinstance(ranked, list))
test("HypothesisEvaluator: solo activas en rank", all(h.status == "active" for h in ranked))

# ============================================================
# HYPOTHESIS ENGINE — HypothesisEngine (coordinator)
# ============================================================
print("\n--- HypothesisEngine ---")

tmp_dir1 = tempfile.mkdtemp()
try:
    engine = HypothesisEngine(base_dir=tmp_dir1)
    test("HypothesisEngine: inicializado", engine is not None)
    test("HypothesisEngine: enabled por defecto", engine.enabled)
    test("HypothesisEngine: hypotheses vacio", len(engine.hypotheses) == 0)
    test("HypothesisEngine: total_generated = 0", engine.total_generated == 0)

    # Formulate
    created = engine.formulate("creo que el modelo necesita mas contexto para responder bien")
    test("HypothesisEngine: formulate crea hipotesis", len(created) > 0)
    test("HypothesisEngine: total_generated incrementa", engine.total_generated > 0)
    test("HypothesisEngine: hipotesis almacenada", len(engine.hypotheses) > 0)

    # Formulate con texto sin hipotesis
    created2 = engine.formulate("hola mundo")
    test("HypothesisEngine: formulate sin hipotesis = []", len(created2) == 0)

    # Formulate disabled
    engine.enabled = False
    created3 = engine.formulate("quizas sea un error")
    test("HypothesisEngine: disabled formulate = []", len(created3) == 0)
    engine.enabled = True

    # Formulate vacio
    created4 = engine.formulate("")
    test("HypothesisEngine: formulate vacio = []", len(created4) == 0)

    # evaluate_against
    engine.evaluate_against("el contexto es importante para el modelo")
    test("HypothesisEngine: evaluate_against no falla", True)

    # get_active_hypotheses
    active = engine.get_active_hypotheses()
    test("HypothesisEngine: get_active retorna lista", isinstance(active, list))

    # get_hypothesis
    if engine.hypotheses:
        hyp_id = list(engine.hypotheses.keys())[0]
        found = engine.get_hypothesis(hyp_id)
        test("HypothesisEngine: get_hypothesis encuentra", found is not None)
    test("HypothesisEngine: get_hypothesis inexistente = None", engine.get_hypothesis("xxx") is None)

    # get_context_for_prompt
    ctx = engine.get_context_for_prompt()
    test("HypothesisEngine: context es string", isinstance(ctx, str))

    # get_stats
    stats = engine.get_stats()
    test("HypothesisEngine: stats tiene total_hypotheses", "total_hypotheses" in stats)
    test("HypothesisEngine: stats tiene active", "active" in stats)
    test("HypothesisEngine: stats tiene total_generated", "total_generated" in stats)

    # status
    st = engine.status()
    test("HypothesisEngine: status no vacio", len(st) > 0)
    test("HypothesisEngine: status tiene Hipotesis", "Hipotesis" in st or "hipotesis" in st.lower())

    # generate_report
    report = engine.generate_report()
    test("HypothesisEngine: report tiene titulo", "HYPOTHESIS ENGINE" in report)

    # save / load
    engine.save()
    engine2 = HypothesisEngine(base_dir=tmp_dir1)
    test("HypothesisEngine: persistencia hypotheses", len(engine2.hypotheses) > 0)
    test("HypothesisEngine: persistencia total_generated", engine2.total_generated > 0)

    # clear
    engine.clear()
    test("HypothesisEngine: clear hypotheses", len(engine.hypotheses) == 0)
    test("HypothesisEngine: clear total_generated", engine.total_generated == 0)

finally:
    shutil.rmtree(tmp_dir1, ignore_errors=True)

# ============================================================
# EXPLANATION ENGINE — Explanation
# ============================================================
print("\n--- Explanation ---")
from core.explanation_engine import Explanation, ExplanationTemplate, QualityScorer, ExplanationEngine

exp = Explanation("recursion", "Es cuando una funcion se llama a si misma.", level="simple", domain="cs")
test("Explanation: topic correcto", exp.topic == "recursion")
test("Explanation: content correcto", "funcion" in exp.content)
test("Explanation: level = simple", exp.level == "simple")
test("Explanation: domain = cs", exp.domain == "cs")
test("Explanation: uses = 0", exp.uses == 0)
test("Explanation: effectiveness = 0.5 sin feedback", exp.effectiveness == 0.5)
test("Explanation: exp_id generado", len(exp.exp_id) == 10)

# Invalid level → falls back to simple
exp_invalid = Explanation("test", "content", level="invalid")
test("Explanation: level invalido = simple", exp_invalid.level == "simple")

# Feedback
exp.record_feedback(True)
exp.record_feedback(True)
exp.record_feedback(False)
test("Explanation: positive_feedback = 2", exp.positive_feedback == 2)
test("Explanation: negative_feedback = 1", exp.negative_feedback == 1)
test("Explanation: effectiveness = 2/3", abs(exp.effectiveness - 2/3) < 0.01)

# relevance_score
test("Explanation: relevance_score en rango", 0.0 <= exp.relevance_score <= 1.0)

# to_dict / from_dict
d_exp = exp.to_dict()
test("Explanation: to_dict tiene topic", d_exp["topic"] == "recursion")
test("Explanation: to_dict tiene uses", d_exp["uses"] == 0)
exp2 = Explanation.from_dict(d_exp)
test("Explanation: from_dict restaura topic", exp2.topic == "recursion")
test("Explanation: from_dict restaura feedback", exp2.positive_feedback == 2)

# ============================================================
# EXPLANATION ENGINE — ExplanationTemplate
# ============================================================
print("\n--- ExplanationTemplate ---")

et = ExplanationTemplate()
d_simple = et.get_directive("recursion", "simple")
test("ExplanationTemplate: directive simple contiene topic", "recursion" in d_simple)
test("ExplanationTemplate: directive simple es string", isinstance(d_simple, str))

d_tech = et.get_directive("recursion", "technical")
test("ExplanationTemplate: directive technical diferente", d_tech != d_simple)

d_analogy = et.get_directive("recursion", "analogical")
test("ExplanationTemplate: directive analogical", "analogia" in d_analogy.lower() or "intuitivo" in d_analogy.lower())

d_steps = et.get_directive("recursion", "step_by_step")
test("ExplanationTemplate: directive step_by_step", "paso" in d_steps.lower())

# get_all_levels
all_levels = et.get_all_levels("test")
test("ExplanationTemplate: all_levels tiene 4 niveles", len(all_levels) == 4)

# ============================================================
# EXPLANATION ENGINE — QualityScorer
# ============================================================
print("\n--- QualityScorer ---")

qs = QualityScorer()

# Score buena explicacion simple
exp_good = Explanation("test", "Esto es como una caja dentro de otra caja. Cada caja contiene una version mas pequena. Es un patron que se repite.", level="simple")
score_good = qs.score(exp_good)
test("QualityScorer: buena explicacion > 0.3", score_good > 0.3)

# Score explicacion muy corta
exp_short = Explanation("test", "ok", level="simple")
score_short = qs.score(exp_short)
test("QualityScorer: explicacion corta score bajo", score_short < score_good)

# Score explicacion tecnica con detalle
exp_tech = Explanation("test", "La complejidad temporal del algoritmo es O(n log n) debido a la division recursiva del problema en subproblemas mas pequenos. Cada nivel de recursion procesa n elementos y hay log n niveles.", level="technical")
score_tech = qs.score(exp_tech)
test("QualityScorer: explicacion tecnica tiene score", score_tech > 0.0)

# Score con analogia
exp_analogy = Explanation("test", "Imagina que tienes un espejo frente a otro espejo. Cada reflejo es como una llamada recursiva, creando una version mas pequena.", level="analogical")
score_analogy = qs.score(exp_analogy)
test("QualityScorer: analogia detectada", score_analogy > 0.3)

# Score con pasos
exp_steps = Explanation("test", "1. Primero definimos la funcion. 2. Luego establecemos el caso base. 3. Finalmente hacemos la llamada recursiva.", level="step_by_step")
score_steps = qs.score(exp_steps)
test("QualityScorer: pasos detectados", score_steps > 0.3)

# ============================================================
# EXPLANATION ENGINE — ExplanationEngine (coordinator)
# ============================================================
print("\n--- ExplanationEngine ---")

tmp_dir2 = tempfile.mkdtemp()
try:
    ee = ExplanationEngine(base_dir=tmp_dir2)
    test("ExplanationEngine: inicializado", ee is not None)
    test("ExplanationEngine: enabled por defecto", ee.enabled)
    test("ExplanationEngine: explanations vacio", len(ee.explanations) == 0)
    test("ExplanationEngine: total_generated = 0", ee.total_generated == 0)

    # Store
    exp1 = ee.store("recursion", "Una funcion que se llama a si misma.", level="simple", domain="cs")
    test("ExplanationEngine: store retorna Explanation", exp1 is not None)
    test("ExplanationEngine: total_generated = 1", ee.total_generated == 1)
    test("ExplanationEngine: quality_score calculado", exp1.quality_score > 0)

    exp2 = ee.store("recursion", "La recursion es un patron algoritmico complejo donde una funcion invoca su propia definicion con un subconjunto reducido del problema original. Requiere un caso base para terminar.", level="technical", domain="cs")
    test("ExplanationEngine: multiple explanaciones mismo topic", ee.total_generated == 2)

    # Store disabled
    ee.enabled = False
    exp_disabled = ee.store("test", "content")
    test("ExplanationEngine: disabled store = None", exp_disabled is None)
    ee.enabled = True

    # Store vacio
    test("ExplanationEngine: store vacio = None", ee.store("", "") is None)
    test("ExplanationEngine: store sin content = None", ee.store("topic", "") is None)

    # Find
    results = ee.find("recursion")
    test("ExplanationEngine: find retorna lista", isinstance(results, list))
    test("ExplanationEngine: find encuentra 2", len(results) == 2)

    # Find con nivel
    results_simple = ee.find("recursion", level="simple")
    test("ExplanationEngine: find con nivel = 1", len(results_simple) == 1)

    # Find parcial
    results_partial = ee.find("recurs")
    test("ExplanationEngine: find parcial funciona", len(results_partial) > 0)

    # Find inexistente
    results_none = ee.find("xxxyyy")
    test("ExplanationEngine: find inexistente = []", len(results_none) == 0)

    # get_best
    best = ee.get_best("recursion")
    test("ExplanationEngine: get_best retorna Explanation", best is not None)
    test("ExplanationEngine: get_best incrementa uses", best.uses == 1)

    # get_best inexistente
    test("ExplanationEngine: get_best inexistente = None", ee.get_best("xxx") is None)

    # get_directive
    directive = ee.get_directive("test", "simple")
    test("ExplanationEngine: get_directive es string", isinstance(directive, str))
    test("ExplanationEngine: get_directive contiene topic", "test" in directive)

    # record_feedback
    ee.record_feedback(exp1.exp_id, True)
    test("ExplanationEngine: record_feedback incrementa", exp1.positive_feedback == 1)

    # detect_explanation_need
    detection = ee.detect_explanation_need("que es una variable?")
    test("ExplanationEngine: detecta necesidad", detection["needs_explanation"])
    test("ExplanationEngine: detecta nivel simple", detection["level"] == "simple")
    test("ExplanationEngine: detecta topic", len(detection["topic"]) > 0)

    detection2 = ee.detect_explanation_need("paso a paso como instalar python")
    test("ExplanationEngine: detecta step_by_step", detection2["level"] == "step_by_step")

    detection_none = ee.detect_explanation_need("hola como estas")
    test("ExplanationEngine: no detecta en saludo", not detection_none["needs_explanation"])

    # get_context_for_prompt
    ctx = ee.get_context_for_prompt("que es recursion?")
    test("ExplanationEngine: context con explicacion previa", len(ctx) > 0)

    ctx_none = ee.get_context_for_prompt("hola")
    test("ExplanationEngine: context sin necesidad = ''", ctx_none == "")

    # get_stats
    stats = ee.get_stats()
    test("ExplanationEngine: stats tiene total_explanations", "total_explanations" in stats)
    test("ExplanationEngine: stats tiene topics", "topics" in stats)
    test("ExplanationEngine: stats tiene levels", "levels" in stats)
    test("ExplanationEngine: stats tiene avg_quality", "avg_quality" in stats)

    # status
    st = ee.status()
    test("ExplanationEngine: status no vacio", len(st) > 0)

    # generate_report
    report = ee.generate_report()
    test("ExplanationEngine: report tiene titulo", "EXPLANATION ENGINE" in report)

    # save / load
    ee.save()
    ee2 = ExplanationEngine(base_dir=tmp_dir2)
    test("ExplanationEngine: persistencia explanations", len(ee2.explanations) > 0)
    test("ExplanationEngine: persistencia total_generated", ee2.total_generated > 0)
    test("ExplanationEngine: persistencia topic_index", len(ee2.topic_index) > 0)

    # clear
    ee.clear()
    test("ExplanationEngine: clear explanations", len(ee.explanations) == 0)
    test("ExplanationEngine: clear topic_index", len(ee.topic_index) == 0)
    test("ExplanationEngine: clear total_generated", ee.total_generated == 0)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)

# ============================================================
# DIALOGUE STRATEGIST — DialogueStrategy
# ============================================================
print("\n--- DialogueStrategy ---")
from core.dialogue_strategist import DialogueStrategy, StrategySelector, EngagementTracker, DialogueStrategist

ds = DialogueStrategy("socratic")
test("DialogueStrategy: key correcto", ds.key == "socratic")
test("DialogueStrategy: name Socratico", ds.name == "Socrático")
test("DialogueStrategy: directive no vacia", len(ds.directive) > 0)
test("DialogueStrategy: conditions es lista", isinstance(ds.conditions, list))
test("DialogueStrategy: engagement_boost > 0", ds.engagement_boost > 0)

# Todos los tipos
for key in DialogueStrategy.STRATEGIES:
    s = DialogueStrategy(key)
    test(f"DialogueStrategy: {key} tiene nombre", len(s.name) > 0)

# Tipo inválido → didactic
ds_invalid = DialogueStrategy("invalid")
test("DialogueStrategy: invalido = didactic", ds_invalid.name == "Didáctico")

# ============================================================
# DIALOGUE STRATEGIST — StrategySelector
# ============================================================
print("\n--- StrategySelector ---")

ss = StrategySelector()

# Señales explícitas
test("StrategySelector: por que -> socratic", ss.select("por que pasa esto?") == "socratic")
test("StrategySelector: explica -> didactic", ss.select("explica como funciona") == "didactic")
test("StrategySelector: que pasa si -> exploratory", ss.select("que pasa si cambio esto?") == "exploratory")
test("StrategySelector: fix error -> directive", ss.select("fix este error rapido") == "directive")
test("StrategySelector: diseñemos -> collaborative", ss.select("diseñemos la arquitectura") == "collaborative")
test("StrategySelector: resumen -> reflective", ss.select("dame un resumen hasta ahora") == "reflective")

# Sin señales → default didactic
test("StrategySelector: sin señales -> didactic", ss.select("hola") == "didactic")

# Con intent
test("StrategySelector: intent code -> directive", ss.select("algo", intent="code") == "directive")
test("StrategySelector: intent explain -> didactic", ss.select("algo", intent="explain") == "didactic")

# Conversación larga → reflective boost
test("StrategySelector: conv larga -> posible reflective",
     isinstance(ss.select("algo", conversation_length=25), str))

# ============================================================
# DIALOGUE STRATEGIST — EngagementTracker
# ============================================================
print("\n--- EngagementTracker ---")

et_tracker = EngagementTracker()
test("EngagementTracker: total_interactions = 0", et_tracker.total_interactions == 0)

# Record
et_tracker.record("socratic", 500)
et_tracker.record("socratic", 600)
et_tracker.record("didactic", 300)
test("EngagementTracker: total_interactions = 3", et_tracker.total_interactions == 3)
test("EngagementTracker: socratic usage = 2", et_tracker.strategy_usage["socratic"] == 2)

# Feedback
et_tracker.record_feedback("socratic", True)
et_tracker.record_feedback("socratic", True)
et_tracker.record_feedback("socratic", False)
test("EngagementTracker: effectiveness socratic = 2/3",
     abs(et_tracker.get_effectiveness("socratic") - 2/3) < 0.01)

# Effectiveness sin feedback
test("EngagementTracker: effectiveness sin feedback = 0.5",
     et_tracker.get_effectiveness("xxx") == 0.5)

# get_best_strategy
best = et_tracker.get_best_strategy()
test("EngagementTracker: best strategy es string", isinstance(best, str))

# to_dict / load_dict
d_et = et_tracker.to_dict()
test("EngagementTracker: to_dict tiene usage", "usage" in d_et)
test("EngagementTracker: to_dict tiene feedback", "feedback" in d_et)

et2 = EngagementTracker()
et2.load_dict(d_et)
test("EngagementTracker: load restaura usage", et2.strategy_usage["socratic"] == 2)
test("EngagementTracker: load restaura interactions", et2.total_interactions == 3)

# ============================================================
# DIALOGUE STRATEGIST — DialogueStrategist (coordinator)
# ============================================================
print("\n--- DialogueStrategist ---")

tmp_dir3 = tempfile.mkdtemp()
try:
    strategist = DialogueStrategist(base_dir=tmp_dir3)
    test("DialogueStrategist: inicializado", strategist is not None)
    test("DialogueStrategist: enabled por defecto", strategist.enabled)
    test("DialogueStrategist: current_strategy = didactic", strategist.current_strategy == "didactic")

    # select_strategy
    strategy = strategist.select_strategy("por que pasa esto?")
    test("DialogueStrategist: select retorna DialogueStrategy", isinstance(strategy, DialogueStrategy))
    test("DialogueStrategist: current_strategy actualizado", strategist.current_strategy == strategy.key)
    test("DialogueStrategist: history incrementa", len(strategist.strategy_history) > 0)

    # record_interaction
    strategist.record_interaction(response_length=500)
    test("DialogueStrategist: record_interaction incrementa tracker",
         strategist.tracker.total_interactions > 0)

    # record_feedback
    strategist.record_feedback(True)
    test("DialogueStrategist: record_feedback no falla", True)

    # get_context_for_prompt
    ctx = strategist.get_context_for_prompt("explica como funciona")
    test("DialogueStrategist: context es string", isinstance(ctx, str))
    test("DialogueStrategist: context contiene ESTRATEGIA", "ESTRATEGIA" in ctx)

    # get_context disabled
    strategist.enabled = False
    ctx_disabled = strategist.get_context_for_prompt("test")
    test("DialogueStrategist: disabled context = ''", ctx_disabled == "")
    strategist.enabled = True

    # get_context vacio
    ctx_empty = strategist.get_context_for_prompt("")
    test("DialogueStrategist: context vacio = ''", ctx_empty == "")

    # get_available_strategies
    available = strategist.get_available_strategies()
    test("DialogueStrategist: 6 estrategias disponibles", len(available) == 6)

    # get_strategy_info
    info = strategist.get_strategy_info("socratic")
    test("DialogueStrategist: info tiene key", info.get("key") == "socratic")
    test("DialogueStrategist: info tiene name", "name" in info)
    test("DialogueStrategist: info tiene effectiveness", "effectiveness" in info)

    # info inexistente
    info_none = strategist.get_strategy_info("xxx")
    test("DialogueStrategist: info inexistente = {}", info_none == {})

    # get_stats
    stats = strategist.get_stats()
    test("DialogueStrategist: stats tiene current_strategy", "current_strategy" in stats)
    test("DialogueStrategist: stats tiene total_interactions", "total_interactions" in stats)
    test("DialogueStrategist: stats tiene strategy_stats", "strategy_stats" in stats)

    # status
    st = strategist.status()
    test("DialogueStrategist: status no vacio", len(st) > 0)

    # generate_report
    report = strategist.generate_report()
    test("DialogueStrategist: report tiene titulo", "DIALOGUE STRATEGIST" in report)

    # save / load
    strategist.save()
    strategist2 = DialogueStrategist(base_dir=tmp_dir3)
    test("DialogueStrategist: persistencia current_strategy",
         strategist2.current_strategy == strategist.current_strategy)
    test("DialogueStrategist: persistencia history", len(strategist2.strategy_history) > 0)
    test("DialogueStrategist: persistencia tracker",
         strategist2.tracker.total_interactions > 0)

    # clear
    strategist.clear()
    test("DialogueStrategist: clear current_strategy", strategist.current_strategy == "didactic")
    test("DialogueStrategist: clear history", len(strategist.strategy_history) == 0)
    test("DialogueStrategist: clear tracker", strategist.tracker.total_interactions == 0)

finally:
    shutil.rmtree(tmp_dir3, ignore_errors=True)

# ============================================================
# INTEGRATION TESTS — genesis.py
# ============================================================
print("\n--- Integración genesis.py ---")

try:
    source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "genesis.py"), encoding="utf-8").read()

    # Imports
    test("genesis.py: import HypothesisEngine", "from core.hypothesis_engine import HypothesisEngine" in source)
    test("genesis.py: import ExplanationEngine", "from core.explanation_engine import ExplanationEngine" in source)
    test("genesis.py: import DialogueStrategist", "from core.dialogue_strategist import DialogueStrategist" in source)

    # Init
    test("genesis.py: init hypothesis_engine", "self.hypothesis_engine = HypothesisEngine(" in source)
    test("genesis.py: init explanation_engine", "self.explanation_engine = ExplanationEngine(" in source)
    test("genesis.py: init dialogue_strategist", "self.dialogue_strategist = DialogueStrategist(" in source)

    # Context injection
    test("genesis.py: hypothesis context injection", "hypothesis_engine.get_context_for_prompt" in source)
    test("genesis.py: explanation context injection", "explanation_engine.get_context_for_prompt" in source)
    test("genesis.py: dialogue context injection", "dialogue_strategist.get_context_for_prompt" in source)

    # Post-processing
    test("genesis.py: hypothesis formulate", "hypothesis_engine.formulate" in source)
    test("genesis.py: hypothesis evaluate_against", "hypothesis_engine.evaluate_against" in source)
    test("genesis.py: explanation store", "explanation_engine.store" in source)
    test("genesis.py: dialogue record_interaction", "dialogue_strategist.record_interaction" in source)

    # Commands
    test("genesis.py: comando /hypothesis", '"/hypothesis"' in source or 'cmd == "/hypothesis"' in source)
    test("genesis.py: comando /explanations", '"/explanations"' in source or 'cmd == "/explanations"' in source)
    test("genesis.py: comando /dialogue", '"/dialogue"' in source or 'cmd == "/dialogue"' in source)

    # Save
    test("genesis.py: save hypothesis_engine", "hypothesis_engine.save()" in source)
    test("genesis.py: save explanation_engine", "explanation_engine.save()" in source)
    test("genesis.py: save dialogue_strategist", "dialogue_strategist.save()" in source)

    # Status
    test("genesis.py: status HYPOTHESIS ENGINE", "HYPOTHESIS ENGINE" in source)
    test("genesis.py: status EXPLANATION ENGINE", "EXPLANATION ENGINE" in source)
    test("genesis.py: status DIALOGUE STRATEGIST", "DIALOGUE STRATEGIST" in source)

    # Dashboard
    test("genesis.py: dashboard hypothesis_engine",
         '"hypothesis_engine"' in source and "hypothesis_engine.get_stats" in source)
    test("genesis.py: dashboard explanation_engine",
         '"explanation_engine"' in source and "explanation_engine.get_stats" in source)
    test("genesis.py: dashboard dialogue_strategist",
         '"dialogue_strategist"' in source and "dialogue_strategist.get_stats" in source)

    # Help
    test("genesis.py: help /hypothesis", "/hypothesis" in source)
    test("genesis.py: help /explanations", "/explanations" in source)
    test("genesis.py: help /dialogue", "/dialogue" in source)

    # Banner
    test("genesis.py: banner Hypothesis Engine", "Hypothesis Engine" in source)
    test("genesis.py: banner Explanation Engine", "Explanation Engine" in source)
    test("genesis.py: banner Dialogue Strategist", "Dialogue Strategist" in source)

except Exception as e:
    test(f"genesis.py: lectura fallida — {e}", False)

# ============================================================
# INTEGRATION TESTS — web_ui.py
# ============================================================
print("\n--- Integración web_ui.py ---")
try:
    web_source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "web_ui.py"), encoding="utf-8").read()
    test("web_ui.py: hypothesis_engine en dashboard", "hypothesis_engine" in web_source)
    test("web_ui.py: explanation_engine en dashboard", "explanation_engine" in web_source)
    test("web_ui.py: dialogue_strategist en dashboard", "dialogue_strategist" in web_source)
    test("web_ui.py: HypothesisEngine en subsystems", "HypothesisEngine" in web_source)
    test("web_ui.py: ExplanationEngine en subsystems", "ExplanationEngine" in web_source)
    test("web_ui.py: DialogueStrategist en subsystems", "DialogueStrategist" in web_source)
except Exception as e:
    test(f"web_ui.py: lectura fallida — {e}", False)

# ============================================================
# VERSION CHECK
# ============================================================
print("\n--- Version Check ---")
from config import GENESIS_VERSION

version_parts = GENESIS_VERSION.split(".")
major = int(version_parts[0])
minor = int(version_parts[1])
version_num = major * 10 + minor
test(f"Version >= 2.8 (actual: {GENESIS_VERSION})", version_num >= 28)

# ============================================================
# EDGE CASES
# ============================================================
print("\n--- Edge Cases ---")

# Hypothesis sin evidencia
h_empty = Hypothesis("test sin evidencia")
test("Edge: plausibility sin evidencia = 0.5", h_empty.plausibility == 0.5)

# Evidence from_dict parcial
e_partial = Evidence.from_dict({"text": "test"})
test("Edge: Evidence from_dict parcial", e_partial.text == "test")
test("Edge: Evidence default supports = True", e_partial.supports is True)

# Explanation LEVELS
test("Edge: Explanation LEVELS tiene 4", len(Explanation.LEVELS) == 4)

# ExplanationEngine eviction
tmp_evict = tempfile.mkdtemp()
ee_evict = ExplanationEngine(base_dir=tmp_evict)
ee_evict.max_explanations = 3
for i in range(10):
    ee_evict.store(f"topic_{i}", f"contenido de prueba numero {i} con detalle suficiente para calidad.", domain="test")
test("Edge: eviction limita explanations", len(ee_evict.explanations) <= 4)
shutil.rmtree(tmp_evict, ignore_errors=True)

# HypothesisEngine eviction
tmp_evict2 = tempfile.mkdtemp()
he_evict = HypothesisEngine(base_dir=tmp_evict2)
he_evict.max_hypotheses = 3
for i in range(10):
    h = Hypothesis(f"hipotesis numero {i}")
    he_evict.hypotheses[h.hyp_id] = h
he_evict._evict()
test("Edge: hypothesis eviction limita", len(he_evict.hypotheses) <= 3)
shutil.rmtree(tmp_evict2, ignore_errors=True)

# DialogueStrategist max_history
tmp_hist = tempfile.mkdtemp()
ds_hist = DialogueStrategist(base_dir=tmp_hist)
ds_hist.max_history = 5
for i in range(20):
    ds_hist.select_strategy(f"explica algo {i}")
test("Edge: max_history limita", len(ds_hist.strategy_history) <= 5)
shutil.rmtree(tmp_hist, ignore_errors=True)

# QualityScorer con explicacion de longitud 1000+
exp_long = Explanation("test", "x " * 600, level="simple")
score_long = QualityScorer().score(exp_long)
test("Edge: explicacion muy larga tiene score bajo", score_long < 0.8)

# EngagementTracker best sin datos
et_empty = EngagementTracker()
test("Edge: best sin datos = didactic", et_empty.get_best_strategy() == "didactic")

# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"RESULTADOS: {passed} passed, {failed} failed de {passed + failed} tests")
if errors:
    print(f"\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
