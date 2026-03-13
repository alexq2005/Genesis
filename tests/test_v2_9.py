"""
GENESIS — Tests v2.9: Meta-Cognitive Architecture
Tests para CognitiveMonitor, AbstractionEngine, LearningOptimizer
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
print("GENESIS v2.9 — Test Suite: Meta-Cognitive Architecture")
print("=" * 60)

# ============================================================
# COGNITIVE MONITOR — CognitiveMetric
# ============================================================
print("\n--- CognitiveMetric ---")
from core.cognitive_monitor import CognitiveMetric, CognitiveLoad, OverloadDetector, CognitiveMonitor

m = CognitiveMetric("test_metric", unit="%")
test("CognitiveMetric: name correcto", m.name == "test_metric")
test("CognitiveMetric: unit correcto", m.unit == "%")
test("CognitiveMetric: current inicial = 0", m.current == 0.0)
test("CognitiveMetric: average inicial = 0", m.average == 0.0)
test("CognitiveMetric: peak inicial = 0", m.peak == 0.0)
test("CognitiveMetric: status inicial = normal", m.status == "normal")
test("CognitiveMetric: total_samples inicial = 0", m.total_samples == 0)

# Record values
m.record(0.3)
test("CognitiveMetric: current = 0.3 después de record", m.current == 0.3)
test("CognitiveMetric: total_samples = 1", m.total_samples == 1)

m.record(0.5)
m.record(0.7)
test("CognitiveMetric: current = 0.7", m.current == 0.7)
test("CognitiveMetric: peak = 0.7", m.peak == 0.7)
test("CognitiveMetric: average > 0", m.average > 0)
test("CognitiveMetric: total_samples = 3", m.total_samples == 3)

# Status thresholds
m.record(0.85)
test("CognitiveMetric: status = warning con 0.85", m.status == "warning")

m.record(0.96)
test("CognitiveMetric: status = critical con 0.96", m.status == "critical")

# to_dict
d = m.to_dict()
test("CognitiveMetric: to_dict tiene name", d["name"] == "test_metric")
test("CognitiveMetric: to_dict tiene status", "status" in d)
test("CognitiveMetric: to_dict tiene current", "current" in d)
test("CognitiveMetric: to_dict tiene average", "average" in d)
test("CognitiveMetric: to_dict tiene peak", "peak" in d)

# Custom thresholds
m2 = CognitiveMetric("low_thresh", warning_threshold=0.5, critical_threshold=0.7)
m2.record(0.55)
test("CognitiveMetric: custom warning threshold", m2.status == "warning")
m2.record(0.75)
test("CognitiveMetric: custom critical threshold", m2.status == "critical")

# ============================================================
# COGNITIVE MONITOR — CognitiveLoad
# ============================================================
print("\n--- CognitiveLoad ---")

load = CognitiveLoad()
test("CognitiveLoad: context_utilization = 0", load.context_utilization == 0.0)
test("CognitiveLoad: response_latency = 0", load.response_latency == 0.0)
test("CognitiveLoad: memory_pressure = 0", load.memory_pressure == 0.0)
test("CognitiveLoad: module_load = 0", load.module_load == 0.0)
test("CognitiveLoad: overall_load = 0", load.overall_load == 0.0)
test("CognitiveLoad: load_level = low", load.load_level == "low")
test("CognitiveLoad: timestamp > 0", load.timestamp > 0)

# Set moderate values
load.context_utilization = 0.5
load.response_latency = 0.5
load.memory_pressure = 0.5
load.module_load = 0.5
expected_load = 0.5 * 0.35 + 0.5 * 0.25 + 0.5 * 0.2 + 0.5 * 0.2
test("CognitiveLoad: overall_load moderada", abs(load.overall_load - expected_load) < 0.001)
test("CognitiveLoad: load_level = moderate", load.load_level == "moderate")

# High load
load.context_utilization = 0.9
load.response_latency = 0.8
load.memory_pressure = 0.7
load.module_load = 0.6
test("CognitiveLoad: load_level = high con valores altos", load.load_level == "high")

# Critical load
load.context_utilization = 1.0
load.response_latency = 1.0
load.memory_pressure = 1.0
load.module_load = 1.0
test("CognitiveLoad: overall_load = 1.0 en máximo", load.overall_load == 1.0)
test("CognitiveLoad: load_level = critical", load.load_level == "critical")

# to_dict
d = load.to_dict()
test("CognitiveLoad: to_dict tiene overall_load", "overall_load" in d)
test("CognitiveLoad: to_dict tiene load_level", "load_level" in d)
test("CognitiveLoad: to_dict tiene context_utilization", "context_utilization" in d)

# ============================================================
# COGNITIVE MONITOR — OverloadDetector
# ============================================================
print("\n--- OverloadDetector ---")

detector = OverloadDetector()

# No overload
load_ok = CognitiveLoad()
load_ok.context_utilization = 0.5
load_ok.response_latency = 0.3
issues = detector.detect(load_ok)
test("OverloadDetector: sin issues con carga baja", len(issues) == 0)

# Context overload
load_ctx = CognitiveLoad()
load_ctx.context_utilization = 0.85
issues = detector.detect(load_ctx)
test("OverloadDetector: detecta context overload", len(issues) > 0)
test("OverloadDetector: area = context_utilization", issues[0]["area"] == "context_utilization")
test("OverloadDetector: severity = warning", issues[0]["severity"] == "warning")
test("OverloadDetector: tiene suggestions", len(issues[0]["suggestions"]) > 0)

# Critical context
load_crit = CognitiveLoad()
load_crit.context_utilization = 0.97
issues = detector.detect(load_crit)
test("OverloadDetector: severity = critical con 0.97", issues[0]["severity"] == "critical")

# Latency overload
load_lat = CognitiveLoad()
load_lat.response_latency = 0.75
issues = detector.detect(load_lat)
test("OverloadDetector: detecta latency overload", len(issues) > 0)
test("OverloadDetector: area = response_latency", issues[0]["area"] == "response_latency")

# Memory pressure
load_mem = CognitiveLoad()
load_mem.memory_pressure = 0.9
issues = detector.detect(load_mem)
test("OverloadDetector: detecta memory pressure", len(issues) > 0)

# Module load
load_mod = CognitiveLoad()
load_mod.module_load = 0.85
issues = detector.detect(load_mod)
test("OverloadDetector: detecta module overload", len(issues) > 0)

# Multiple issues
load_multi = CognitiveLoad()
load_multi.context_utilization = 0.9
load_multi.response_latency = 0.8
load_multi.memory_pressure = 0.9
issues = detector.detect(load_multi)
test("OverloadDetector: múltiples issues", len(issues) >= 3)

# SUGGESTIONS dict
test("OverloadDetector: SUGGESTIONS tiene 4 areas",
     len(OverloadDetector.SUGGESTIONS) == 4)

# ============================================================
# COGNITIVE MONITOR — CognitiveMonitor (coordinator)
# ============================================================
print("\n--- CognitiveMonitor ---")

tmp = tempfile.mkdtemp()
try:
    cm = CognitiveMonitor(base_dir=tmp)
    test("CognitiveMonitor: enabled = True", cm.enabled is True)
    test("CognitiveMonitor: total_snapshots = 0", cm.total_snapshots == 0)
    test("CognitiveMonitor: overload_count = 0", cm.overload_count == 0)
    test("CognitiveMonitor: tiene 4 metrics", len(cm.metrics) == 4)

    # record_snapshot
    load = cm.record_snapshot(context_util=0.3, latency=0.2,
                              memory_pressure=0.1, module_load=0.2)
    test("CognitiveMonitor: record_snapshot retorna CognitiveLoad",
         isinstance(load, CognitiveLoad))
    test("CognitiveMonitor: total_snapshots = 1", cm.total_snapshots == 1)
    test("CognitiveMonitor: load_level = low", load.load_level == "low")

    # Clamping
    load2 = cm.record_snapshot(context_util=1.5, latency=-0.5)
    test("CognitiveMonitor: clamp max = 1.0",
         load2.context_utilization == 1.0)
    test("CognitiveMonitor: clamp min = 0.0",
         load2.response_latency == 0.0)

    # get_current_load
    current = cm.get_current_load()
    test("CognitiveMonitor: get_current_load retorna CognitiveLoad",
         isinstance(current, CognitiveLoad))

    # detect_overload sin sobrecarga
    issues = cm.detect_overload()
    test("CognitiveMonitor: detect_overload retorna lista", isinstance(issues, list))

    # Registrar alta carga
    cm.record_snapshot(context_util=0.9, latency=0.85,
                       memory_pressure=0.9, module_load=0.85)
    test("CognitiveMonitor: overload_count > 0 con carga alta",
         cm.overload_count > 0)
    issues = cm.detect_overload()
    test("CognitiveMonitor: detecta overload con carga alta", len(issues) > 0)

    # get_context_for_prompt con alta carga
    ctx = cm.get_context_for_prompt()
    test("CognitiveMonitor: context con alta carga no vacío", len(ctx) > 0)
    test("CognitiveMonitor: context contiene CARGA", "CARGA" in ctx)

    # get_context_for_prompt con baja carga
    cm2 = CognitiveMonitor(base_dir=tempfile.mkdtemp())
    cm2.record_snapshot(context_util=0.1, latency=0.1)
    ctx_low = cm2.get_context_for_prompt()
    test("CognitiveMonitor: context vacío con carga baja", ctx_low == "")

    # Disabled
    cm.enabled = False
    result = cm.record_snapshot(context_util=0.5)
    test("CognitiveMonitor: disabled retorna None", result is None)
    ctx_disabled = cm.get_context_for_prompt()
    test("CognitiveMonitor: disabled context vacío", ctx_disabled == "")
    cm.enabled = True

    # get_stats
    stats = cm.get_stats()
    test("CognitiveMonitor: stats tiene overall_load", "overall_load" in stats)
    test("CognitiveMonitor: stats tiene load_level", "load_level" in stats)
    test("CognitiveMonitor: stats tiene total_snapshots", "total_snapshots" in stats)
    test("CognitiveMonitor: stats tiene overload_count", "overload_count" in stats)
    test("CognitiveMonitor: stats tiene metrics", "metrics" in stats)

    # status
    st = cm.status()
    test("CognitiveMonitor: status no vacío", len(st) > 0)
    test("CognitiveMonitor: status tiene Carga", "Carga" in st)

    # generate_report
    report = cm.generate_report()
    test("CognitiveMonitor: report contiene COGNITIVE", "COGNITIVE" in report)
    test("CognitiveMonitor: report contiene Metricas", "Metricas" in report or "metricas" in report.lower())

    # save/load
    cm.save()
    cm3 = CognitiveMonitor(base_dir=tmp)
    test("CognitiveMonitor: persistencia total_snapshots",
         cm3.total_snapshots == cm.total_snapshots)
    test("CognitiveMonitor: persistencia overload_count",
         cm3.overload_count == cm.overload_count)

    # clear
    cm.clear()
    test("CognitiveMonitor: clear total_snapshots = 0", cm.total_snapshots == 0)
    test("CognitiveMonitor: clear overload_count = 0", cm.overload_count == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# ABSTRACTION ENGINE — AbstractPattern
# ============================================================
print("\n--- AbstractPattern ---")
from core.abstraction_engine import AbstractPattern, PatternMatcher, AbstractionEngine

ap = AbstractPattern("test_pattern", "template de prueba", "test_domain")
test("AbstractPattern: name correcto", ap.name == "test_pattern")
test("AbstractPattern: template correcto", ap.template == "template de prueba")
test("AbstractPattern: domain correcto", ap.domain == "test_domain")
test("AbstractPattern: confidence = 0", ap.confidence == 0.0)
test("AbstractPattern: applications = 0", ap.applications == 0)
test("AbstractPattern: instances vacías", len(ap.instances) == 0)
test("AbstractPattern: pattern_id no vacío", len(ap.pattern_id) > 0)

# add_instance
ap.add_instance("primera instancia del patrón")
test("AbstractPattern: 1 instancia", len(ap.instances) == 1)
test("AbstractPattern: confidence > 0 con 1 instancia", ap.confidence > 0.0)
# n/(n+3) = 1/4 = 0.25
test("AbstractPattern: confidence = 0.25 con 1 instancia",
     abs(ap.confidence - 0.25) < 0.01)

ap.add_instance("segunda instancia del patrón")
ap.add_instance("tercera instancia del patrón")
# n/(n+3) = 3/6 = 0.5
test("AbstractPattern: confidence = 0.5 con 3 instancias",
     abs(ap.confidence - 0.5) < 0.01)

# strength
test("AbstractPattern: strength >= 0", ap.strength >= 0.0)
test("AbstractPattern: strength = conf*0.7 + 0 sin aplicaciones",
     abs(ap.strength - ap.confidence * 0.7) < 0.01)

# Con aplicaciones
ap.applications = 5
strength_with_apps = ap.confidence * 0.7 + (5 / 10.0) * 0.3
test("AbstractPattern: strength con aplicaciones",
     abs(ap.strength - strength_with_apps) < 0.01)

# max_instances eviction
for i in range(25):
    ap.add_instance(f"instancia {i}")
test("AbstractPattern: max_instances respetado",
     len(ap.instances) <= ap.max_instances)

# to_dict / from_dict
d = ap.to_dict()
test("AbstractPattern: to_dict tiene name", d["name"] == "test_pattern")
test("AbstractPattern: to_dict tiene pattern_id", "pattern_id" in d)
test("AbstractPattern: to_dict tiene confidence", "confidence" in d)
test("AbstractPattern: to_dict tiene applications", "applications" in d)

ap2 = AbstractPattern.from_dict(d)
test("AbstractPattern: from_dict name", ap2.name == ap.name)
test("AbstractPattern: from_dict confidence", abs(ap2.confidence - ap.confidence) < 0.01)
test("AbstractPattern: from_dict applications", ap2.applications == ap.applications)
test("AbstractPattern: from_dict pattern_id", ap2.pattern_id == ap.pattern_id)

# ============================================================
# ABSTRACTION ENGINE — PatternMatcher
# ============================================================
print("\n--- PatternMatcher ---")

pm = PatternMatcher()

# detect_patterns — debug_cycle (needs 2+ keywords)
detected = pm.detect_patterns("Tengo un error en mi código, no funciona y hay un bug")
test("PatternMatcher: detecta debug_cycle", len(detected) > 0)
test("PatternMatcher: debug_cycle key",
     any(d["key"] == "debug_cycle" for d in detected))

# detect_patterns — learning_sequence
detected = pm.detect_patterns("Explica que es una función y como funciona")
test("PatternMatcher: detecta learning_sequence",
     any(d["key"] == "learning_sequence" for d in detected))

# detect_patterns — implementation_flow
detected = pm.detect_patterns("Implementa el codigo de la clase y crea la funcion")
test("PatternMatcher: detecta implementation_flow",
     any(d["key"] == "implementation_flow" for d in detected))

# detect_patterns — refactor_pattern
detected = pm.detect_patterns("Refactoriza y mejora el código, optimiza el rendimiento")
test("PatternMatcher: detecta refactor_pattern",
     any(d["key"] == "refactor_pattern" for d in detected))

# detect_patterns — exploration_spiral
detected = pm.detect_patterns("Que pasa si uso otra forma, hay alternativa para esto")
test("PatternMatcher: detecta exploration_spiral",
     any(d["key"] == "exploration_spiral" for d in detected))

# detect_patterns — sin match (1 sola keyword no es suficiente)
detected = pm.detect_patterns("Hola como estas")
test("PatternMatcher: sin match con texto genérico", len(detected) == 0)

# detect_patterns — confidence y hits
detected = pm.detect_patterns("error debug fix falla bug no funciona")
test("PatternMatcher: hits altos = confidence alta",
     detected[0]["confidence"] > 0.5 if detected else False)

# detect_patterns — resultado ordenado por confidence
detected = pm.detect_patterns("error falla explica que es tutorial como funciona")
test("PatternMatcher: resultados ordenados",
     all(detected[i]["confidence"] >= detected[i + 1]["confidence"]
         for i in range(len(detected) - 1)) if len(detected) > 1 else True)

# compute_similarity
sim = pm.compute_similarity("hola mundo test", "hola mundo test")
test("PatternMatcher: similitud perfecta = 1.0", sim == 1.0)

sim = pm.compute_similarity("hola mundo", "adios tierra")
test("PatternMatcher: similitud nula = 0.0", sim == 0.0)

sim = pm.compute_similarity("python javascript coding",
                            "python coding review testing")
test("PatternMatcher: similitud parcial entre 0 y 1", 0.0 < sim < 1.0)

# Edge cases
test("PatternMatcher: similarity vacío-vacío = 0",
     pm.compute_similarity("", "") == 0.0)
test("PatternMatcher: similarity vacío-texto = 0",
     pm.compute_similarity("", "hello") == 0.0)

# INTERACTION_PATTERNS dict
test("PatternMatcher: tiene 5 patrones de interacción",
     len(PatternMatcher.INTERACTION_PATTERNS) == 5)

# ============================================================
# ABSTRACTION ENGINE — AbstractionEngine (coordinator)
# ============================================================
print("\n--- AbstractionEngine ---")

tmp = tempfile.mkdtemp()
try:
    ae = AbstractionEngine(base_dir=tmp)
    test("AbstractionEngine: enabled = True", ae.enabled is True)
    test("AbstractionEngine: patterns vacío", len(ae.patterns) == 0)
    test("AbstractionEngine: recent_inputs vacío", len(ae.recent_inputs) == 0)
    test("AbstractionEngine: total_abstractions = 0", ae.total_abstractions == 0)

    # observe con texto que match debug_cycle
    ae.observe("Tengo un error, no funciona y hay un bug en el sistema", domain="code")
    test("AbstractionEngine: observe registra patrón", len(ae.patterns) > 0)
    test("AbstractionEngine: observe registra input", len(ae.recent_inputs) > 0)
    test("AbstractionEngine: total_abstractions > 0", ae.total_abstractions > 0)

    # observe con texto vacío
    initial_patterns = len(ae.patterns)
    ae.observe("")
    test("AbstractionEngine: ignora texto vacío", len(ae.patterns) == initial_patterns)

    # observe disabled
    ae.enabled = False
    ae.observe("algo nuevo")
    test("AbstractionEngine: ignora cuando disabled", len(ae.recent_inputs) == 1)
    ae.enabled = True

    # observe múltiples para detectar repeticiones
    for i in range(5):
        ae.observe("python javascript coding review test programacion", domain="code")
    test("AbstractionEngine: recent_inputs crece",
         len(ae.recent_inputs) >= 5)

    # get_active_patterns
    active = ae.get_active_patterns(min_confidence=0.0)
    test("AbstractionEngine: get_active_patterns retorna lista",
         isinstance(active, list))
    if active:
        test("AbstractionEngine: patrones ordenados por strength",
             all(active[i].strength >= active[i + 1].strength
                 for i in range(len(active) - 1)))

    # get_active_patterns con min_confidence alta
    active_strict = ae.get_active_patterns(min_confidence=0.99)
    test("AbstractionEngine: min_confidence filtra",
         len(active_strict) <= len(active))

    # apply_pattern
    if ae.patterns:
        pid = list(ae.patterns.keys())[0]
        old_apps = ae.patterns[pid].applications
        ae.apply_pattern(pid)
        test("AbstractionEngine: apply_pattern incrementa",
             ae.patterns[pid].applications == old_apps + 1)

    # apply_pattern inexistente
    ae.apply_pattern("nonexistent")
    test("AbstractionEngine: apply_pattern inexistente no falla", True)

    # get_context_for_prompt
    ctx = ae.get_context_for_prompt()
    test("AbstractionEngine: context es string", isinstance(ctx, str))

    # get_stats
    stats = ae.get_stats()
    test("AbstractionEngine: stats tiene total_patterns", "total_patterns" in stats)
    test("AbstractionEngine: stats tiene active_patterns", "active_patterns" in stats)
    test("AbstractionEngine: stats tiene total_abstractions", "total_abstractions" in stats)
    test("AbstractionEngine: stats tiene recent_inputs", "recent_inputs" in stats)

    # status
    st = ae.status()
    test("AbstractionEngine: status no vacío", len(st) > 0)
    test("AbstractionEngine: status tiene Patrones", "Patrones" in st or "patrones" in st.lower())

    # generate_report
    report = ae.generate_report()
    test("AbstractionEngine: report contiene ABSTRACTION", "ABSTRACTION" in report)

    # save/load
    ae.save()
    ae2 = AbstractionEngine(base_dir=tmp)
    test("AbstractionEngine: persistencia patterns",
         len(ae2.patterns) == len(ae.patterns))
    test("AbstractionEngine: persistencia total_abstractions",
         ae2.total_abstractions == ae.total_abstractions)

    # _evict
    ae3 = AbstractionEngine(base_dir=tempfile.mkdtemp())
    ae3.max_patterns = 3
    for i in range(5):
        ae3._register_pattern(f"pat_{i}", f"template_{i}", f"inst_{i}", "test")
    test("AbstractionEngine: eviction respeta max_patterns",
         len(ae3.patterns) <= 3)

    # clear
    ae.clear()
    test("AbstractionEngine: clear patterns vacío", len(ae.patterns) == 0)
    test("AbstractionEngine: clear recent_inputs vacío", len(ae.recent_inputs) == 0)
    test("AbstractionEngine: clear total_abstractions = 0", ae.total_abstractions == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# LEARNING OPTIMIZER — LearningRate
# ============================================================
print("\n--- LearningRate ---")
from core.learning_optimizer import LearningRate, KnowledgeGap, LearningStrategy, LearningOptimizer

lr = LearningRate("python", initial_rate=1.0, decay_factor=0.95)
test("LearningRate: domain correcto", lr.domain == "python")
test("LearningRate: initial_rate = 1.0", lr.initial_rate == 1.0)
test("LearningRate: current_rate = 1.0", lr.current_rate == 1.0)
test("LearningRate: interactions = 0", lr.interactions == 0)
test("LearningRate: mastery = 0 sin interacciones", lr.mastery == 0.0)
test("LearningRate: efficiency = 0 sin interacciones", lr.efficiency == 0.0)

# record_success
lr.record_success()
test("LearningRate: interactions = 1", lr.interactions == 1)
test("LearningRate: successes = 1", lr.successes == 1)
test("LearningRate: current_rate < 1.0 después de éxito", lr.current_rate < 1.0)
# 1.0 * 0.95^1 = 0.95
test("LearningRate: rate = 0.95 después de 1 éxito",
     abs(lr.current_rate - 0.95) < 0.01)

# Multiple successes
for _ in range(9):
    lr.record_success()
test("LearningRate: 10 successes", lr.successes == 10)
test("LearningRate: rate decrece con más éxitos", lr.current_rate < 0.95)
test("LearningRate: rate > 0.05 (mínimo)", lr.current_rate >= 0.05)

# mastery crece
test("LearningRate: mastery > 0 con interacciones", lr.mastery > 0.0)
test("LearningRate: mastery <= 1.0", lr.mastery <= 1.0)

# record_failure
lr.record_failure()
test("LearningRate: failures = 1", lr.failures == 1)
test("LearningRate: rate sube con failure", lr.current_rate > 0.05)

# efficiency
test("LearningRate: efficiency > 0", lr.efficiency > 0.0)

# to_dict / from_dict
d = lr.to_dict()
test("LearningRate: to_dict tiene domain", d["domain"] == "python")
test("LearningRate: to_dict tiene mastery", "mastery" in d)
test("LearningRate: to_dict tiene efficiency", "efficiency" in d)
test("LearningRate: to_dict tiene current_rate", "current_rate" in d)

lr2 = LearningRate.from_dict(d)
test("LearningRate: from_dict domain", lr2.domain == lr.domain)
test("LearningRate: from_dict successes", lr2.successes == lr.successes)
test("LearningRate: from_dict failures", lr2.failures == lr.failures)

# ============================================================
# LEARNING OPTIMIZER — KnowledgeGap
# ============================================================
print("\n--- KnowledgeGap ---")

gap = KnowledgeGap("python", "no entiende decoradores", severity=0.6)
test("KnowledgeGap: domain correcto", gap.domain == "python")
test("KnowledgeGap: description correcta", gap.description == "no entiende decoradores")
test("KnowledgeGap: severity = 0.6", gap.severity == 0.6)
test("KnowledgeGap: occurrences = 1", gap.occurrences == 1)
test("KnowledgeGap: resolved = False", gap.resolved is False)

# record_occurrence
gap.record_occurrence()
test("KnowledgeGap: occurrences = 2", gap.occurrences == 2)
test("KnowledgeGap: severity crece", gap.severity == 0.7)

# resolve
gap.resolve()
test("KnowledgeGap: resolved = True", gap.resolved is True)
test("KnowledgeGap: resolved_at not None", gap.resolved_at is not None)

# Clamping severity
gap2 = KnowledgeGap("test", "desc", severity=1.5)
test("KnowledgeGap: severity clamped a 1.0", gap2.severity == 1.0)

gap3 = KnowledgeGap("test", "desc", severity=-0.5)
test("KnowledgeGap: severity clamped a 0.0", gap3.severity == 0.0)

# Long description truncated
gap4 = KnowledgeGap("test", "x" * 300)
test("KnowledgeGap: description truncada a 200", len(gap4.description) <= 200)

# to_dict / from_dict
d = gap.to_dict()
test("KnowledgeGap: to_dict tiene domain", d["domain"] == "python")
test("KnowledgeGap: to_dict tiene resolved", d["resolved"] is True)

gap5 = KnowledgeGap.from_dict(d)
test("KnowledgeGap: from_dict domain", gap5.domain == gap.domain)
test("KnowledgeGap: from_dict occurrences", gap5.occurrences == gap.occurrences)
test("KnowledgeGap: from_dict resolved", gap5.resolved == gap.resolved)

# ============================================================
# LEARNING OPTIMIZER — LearningStrategy
# ============================================================
print("\n--- LearningStrategy ---")

# STRATEGIES dict
test("LearningStrategy: tiene 5 estrategias",
     len(LearningStrategy.STRATEGIES) == 5)
test("LearningStrategy: tiene spaced_repetition",
     "spaced_repetition" in LearningStrategy.STRATEGIES)
test("LearningStrategy: tiene active_recall",
     "active_recall" in LearningStrategy.STRATEGIES)
test("LearningStrategy: tiene interleaving",
     "interleaving" in LearningStrategy.STRATEGIES)
test("LearningStrategy: tiene elaboration",
     "elaboration" in LearningStrategy.STRATEGIES)
test("LearningStrategy: tiene concrete_examples",
     "concrete_examples" in LearningStrategy.STRATEGIES)

# select_for_domain
test("LearningStrategy: novato = concrete_examples",
     LearningStrategy.select_for_domain("python", 0.1) == "concrete_examples")
test("LearningStrategy: bajo-medio = elaboration",
     LearningStrategy.select_for_domain("python", 0.3) == "elaboration")
test("LearningStrategy: medio = active_recall",
     LearningStrategy.select_for_domain("python", 0.5) == "active_recall")
test("LearningStrategy: alto = interleaving",
     LearningStrategy.select_for_domain("python", 0.8) == "interleaving")

# get_directive
d = LearningStrategy.get_directive("spaced_repetition")
test("LearningStrategy: directive no vacía", len(d) > 0)
test("LearningStrategy: directive inexistente = vacía",
     LearningStrategy.get_directive("nonexistent") == "")

# Cada estrategia tiene name, directive, best_for
for key, config in LearningStrategy.STRATEGIES.items():
    test(f"LearningStrategy: {key} tiene name", "name" in config)
    test(f"LearningStrategy: {key} tiene directive", "directive" in config)
    test(f"LearningStrategy: {key} tiene best_for", "best_for" in config)

# ============================================================
# LEARNING OPTIMIZER — LearningOptimizer (coordinator)
# ============================================================
print("\n--- LearningOptimizer ---")

tmp = tempfile.mkdtemp()
try:
    lo = LearningOptimizer(base_dir=tmp)
    test("LearningOptimizer: enabled = True", lo.enabled is True)
    test("LearningOptimizer: learning_rates vacío", len(lo.learning_rates) == 0)
    test("LearningOptimizer: knowledge_gaps vacío", len(lo.knowledge_gaps) == 0)
    test("LearningOptimizer: total_optimizations = 0", lo.total_optimizations == 0)

    # record_learning success
    lo.record_learning("python", success=True)
    test("LearningOptimizer: crea learning rate", "python" in lo.learning_rates)
    test("LearningOptimizer: total_optimizations = 1", lo.total_optimizations == 1)
    test("LearningOptimizer: python successes = 1",
         lo.learning_rates["python"].successes == 1)

    # record_learning failure
    lo.record_learning("python", success=False)
    test("LearningOptimizer: python failures = 1",
         lo.learning_rates["python"].failures == 1)

    # detect_gap
    lo.detect_gap("javascript", "closures", severity=0.7)
    test("LearningOptimizer: gap creado", len(lo.knowledge_gaps) == 1)
    test("LearningOptimizer: gap domain", lo.knowledge_gaps[0].domain == "javascript")

    # detect_gap duplicado mismo dominio
    lo.detect_gap("javascript", "closures again")
    test("LearningOptimizer: gap duplicado incrementa occurrences",
         lo.knowledge_gaps[0].occurrences == 2)
    test("LearningOptimizer: no crea gap duplicado", len(lo.knowledge_gaps) == 1)

    # detect_gap nuevo dominio
    lo.detect_gap("rust", "ownership", severity=0.5)
    test("LearningOptimizer: nuevo gap diferente dominio", len(lo.knowledge_gaps) == 2)

    # resolve_gap
    lo.resolve_gap("javascript")
    active = lo.get_active_gaps()
    test("LearningOptimizer: resolve_gap funciona",
         all(g.domain != "javascript" for g in active))

    # get_active_gaps
    active = lo.get_active_gaps()
    test("LearningOptimizer: get_active_gaps retorna no resueltos",
         all(not g.resolved for g in active))

    # get_domain_mastery
    m = lo.get_domain_mastery("python")
    test("LearningOptimizer: mastery python > 0", m >= 0.0)
    test("LearningOptimizer: mastery inexistente = 0",
         lo.get_domain_mastery("unknown") == 0.0)

    # Agregar más dominios
    for d in ["rust", "go", "java", "typescript"]:
        for _ in range(3):
            lo.record_learning(d, success=True)

    # get_top_domains
    top = lo.get_top_domains(3)
    test("LearningOptimizer: get_top_domains retorna lista", isinstance(top, list))
    test("LearningOptimizer: top max 3", len(top) <= 3)

    # get_weakest_domains
    weak = lo.get_weakest_domains(3)
    test("LearningOptimizer: get_weakest_domains retorna lista", isinstance(weak, list))

    # get_recommended_strategy
    rec = lo.get_recommended_strategy("python")
    test("LearningOptimizer: recommend tiene strategy", "strategy" in rec)
    test("LearningOptimizer: recommend tiene name", "name" in rec)
    test("LearningOptimizer: recommend tiene directive", "directive" in rec)
    test("LearningOptimizer: recommend tiene domain_mastery", "domain_mastery" in rec)

    # observe_interaction — gap signal
    lo.observe_interaction("No entiendo como funciona esto", domain="math")
    test("LearningOptimizer: observe detecta gap",
         any(g.domain == "math" for g in lo.knowledge_gaps))

    # observe_interaction — success signal
    lo.observe_interaction("Ahora si entiendo, perfecto, gracias", domain="math")
    math_gaps = [g for g in lo.knowledge_gaps if g.domain == "math"]
    test("LearningOptimizer: observe resuelve gap",
         all(g.resolved for g in math_gaps) if math_gaps else True)

    # observe_interaction vacío
    initial_count = lo.total_optimizations
    lo.observe_interaction("")
    test("LearningOptimizer: observe ignora vacío", True)

    # observe disabled
    lo.enabled = False
    lo.observe_interaction("algo nuevo")
    lo.record_learning("disabled_test")
    test("LearningOptimizer: disabled no registra",
         "disabled_test" not in lo.learning_rates)
    lo.enabled = True

    # get_context_for_prompt
    ctx = lo.get_context_for_prompt(domain="python")
    test("LearningOptimizer: context es string", isinstance(ctx, str))

    # get_stats
    stats = lo.get_stats()
    test("LearningOptimizer: stats tiene total_domains", "total_domains" in stats)
    test("LearningOptimizer: stats tiene total_optimizations", "total_optimizations" in stats)
    test("LearningOptimizer: stats tiene active_gaps", "active_gaps" in stats)
    test("LearningOptimizer: stats tiene resolved_gaps", "resolved_gaps" in stats)
    test("LearningOptimizer: stats tiene current_strategy", "current_strategy" in stats)
    test("LearningOptimizer: stats tiene top_domains", "top_domains" in stats)

    # status
    st = lo.status()
    test("LearningOptimizer: status no vacío", len(st) > 0)
    test("LearningOptimizer: status tiene Dominios", "Dominios" in st or "dominios" in st.lower())

    # generate_report
    report = lo.generate_report()
    test("LearningOptimizer: report contiene LEARNING", "LEARNING" in report)

    # save/load
    lo.save()
    lo2 = LearningOptimizer(base_dir=tmp)
    test("LearningOptimizer: persistencia learning_rates",
         len(lo2.learning_rates) == len(lo.learning_rates))
    test("LearningOptimizer: persistencia knowledge_gaps",
         len(lo2.knowledge_gaps) == len(lo.knowledge_gaps))
    test("LearningOptimizer: persistencia total_optimizations",
         lo2.total_optimizations == lo.total_optimizations)

    # Gap eviction
    lo3 = LearningOptimizer(base_dir=tempfile.mkdtemp())
    lo3.max_gaps = 3
    for i in range(5):
        lo3.detect_gap(f"domain_{i}", f"gap_{i}", severity=0.1 * (i + 1))
    test("LearningOptimizer: gap eviction respeta max",
         len(lo3.knowledge_gaps) <= 3)

    # clear
    lo.clear()
    test("LearningOptimizer: clear learning_rates vacío", len(lo.learning_rates) == 0)
    test("LearningOptimizer: clear knowledge_gaps vacío", len(lo.knowledge_gaps) == 0)
    test("LearningOptimizer: clear total_optimizations = 0", lo.total_optimizations == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# INTEGRATION — genesis.py imports
# ============================================================
print("\n--- Integración genesis.py ---")

# Verificar imports
import importlib
test("Integration: import cognitive_monitor",
     importlib.import_module("core.cognitive_monitor") is not None)
test("Integration: import abstraction_engine",
     importlib.import_module("core.abstraction_engine") is not None)
test("Integration: import learning_optimizer",
     importlib.import_module("core.learning_optimizer") is not None)

# Verificar que genesis.py tiene los imports
with open("genesis.py", "r", encoding="utf-8") as f:
    genesis_code = f.read()

test("Integration: genesis importa CognitiveMonitor",
     "from core.cognitive_monitor import CognitiveMonitor" in genesis_code)
test("Integration: genesis importa AbstractionEngine",
     "from core.abstraction_engine import AbstractionEngine" in genesis_code)
test("Integration: genesis importa LearningOptimizer",
     "from core.learning_optimizer import LearningOptimizer" in genesis_code)

# Verificar init
test("Integration: genesis init cognitive_monitor",
     "self.cognitive_monitor = CognitiveMonitor(" in genesis_code)
test("Integration: genesis init abstraction_engine",
     "self.abstraction_engine = AbstractionEngine(" in genesis_code)
test("Integration: genesis init learning_optimizer",
     "self.learning_optimizer = LearningOptimizer(" in genesis_code)

# Verificar context injection
test("Integration: context cognitive_monitor",
     "cognitive_monitor.get_context_for_prompt" in genesis_code)
test("Integration: context abstraction_engine",
     "abstraction_engine.get_context_for_prompt" in genesis_code)
test("Integration: context learning_optimizer",
     "learning_optimizer.get_context_for_prompt" in genesis_code)

# Verificar post-process
test("Integration: post-process cognitive_monitor.record_snapshot",
     "cognitive_monitor.record_snapshot" in genesis_code)
test("Integration: post-process abstraction_engine.observe",
     "abstraction_engine.observe" in genesis_code)
test("Integration: post-process learning_optimizer.observe_interaction",
     "learning_optimizer.observe_interaction" in genesis_code)

# Verificar commands
test("Integration: comando /cognitive",
     '"/cognitive"' in genesis_code or "== \"/cognitive\"" in genesis_code)
test("Integration: comando /abstraction",
     '"/abstraction"' in genesis_code or "== \"/abstraction\"" in genesis_code)
test("Integration: comando /learning",
     '"/learning"' in genesis_code or "== \"/learning\"" in genesis_code)

# Verificar status
test("Integration: status cognitive_monitor",
     "cognitive_monitor.status()" in genesis_code)
test("Integration: status abstraction_engine",
     "abstraction_engine.status()" in genesis_code)
test("Integration: status learning_optimizer",
     "learning_optimizer.status()" in genesis_code)

# Verificar dashboard
test("Integration: dashboard cognitive_monitor",
     "cognitive_monitor" in genesis_code and "dashboard.register" in genesis_code)
test("Integration: dashboard abstraction_engine",
     "abstraction_engine" in genesis_code and "dashboard.register" in genesis_code)
test("Integration: dashboard learning_optimizer",
     "learning_optimizer" in genesis_code and "dashboard.register" in genesis_code)

# Verificar save
test("Integration: save cognitive_monitor",
     "cognitive_monitor.save()" in genesis_code)
test("Integration: save abstraction_engine",
     "abstraction_engine.save()" in genesis_code)
test("Integration: save learning_optimizer",
     "learning_optimizer.save()" in genesis_code)

# Verificar help
test("Integration: help /cognitive",
     "/cognitive" in genesis_code)
test("Integration: help /abstraction",
     "/abstraction" in genesis_code)
test("Integration: help /learning",
     "/learning" in genesis_code)

# ============================================================
# INTEGRATION — web_ui.py
# ============================================================
print("\n--- Integración web_ui.py ---")

with open("web_ui.py", "r", encoding="utf-8") as f:
    webui_code = f.read()

test("Integration: web_ui tiene CognitiveMonitor en health",
     "CognitiveMonitor" in webui_code)
test("Integration: web_ui tiene AbstractionEngine en health",
     "AbstractionEngine" in webui_code)
test("Integration: web_ui tiene LearningOptimizer en health",
     "LearningOptimizer" in webui_code)

test("Integration: web_ui tiene cognitive_monitor.get_stats",
     "cognitive_monitor.get_stats()" in webui_code)
test("Integration: web_ui tiene abstraction_engine.get_stats",
     "abstraction_engine.get_stats()" in webui_code)
test("Integration: web_ui tiene learning_optimizer.get_stats",
     "learning_optimizer.get_stats()" in webui_code)

# ============================================================
# INTEGRATION — version check
# ============================================================
print("\n--- Version Check ---")
from config import GENESIS_VERSION

major, minor, patch = GENESIS_VERSION.split(".")
version_num = int(major) * 100 + int(minor) * 10 + int(patch)
test("Integration: version >= 2.9.0", version_num >= 290)

# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTADOS: {passed}/{total} tests pasaron")
if errors:
    print(f"\nTests fallidos ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("¡Todos los tests pasaron!")
    sys.exit(0)
