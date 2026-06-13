"""
GENESIS — Tests v3.1: Social Intelligence
Tests para EmotionReader, EmpathyEngine, ConflictResolver
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
print("GENESIS v3.1 — Test Suite: Social Intelligence")
print("=" * 60)

# ============================================================
# EMOTION READER — EmotionSignal
# ============================================================
print("\n--- EmotionSignal ---")
from core.emotion_reader import EmotionSignal, EmotionClassifier, EmotionHistory, EmotionReader

sig = EmotionSignal("alegria", 0.8, "gracias")
test("EmotionSignal: emotion = alegria", sig.emotion == "alegria")
test("EmotionSignal: intensity = 0.8", sig.intensity == 0.8)
test("EmotionSignal: source = gracias", sig.source == "gracias")
test("EmotionSignal: timestamp > 0", sig.timestamp > 0)

d = sig.to_dict()
test("EmotionSignal: to_dict tiene emotion", d["emotion"] == "alegria")
test("EmotionSignal: to_dict tiene intensity", d["intensity"] == 0.8)

sig2 = EmotionSignal.from_dict(d)
test("EmotionSignal: from_dict restaura emotion", sig2.emotion == "alegria")
test("EmotionSignal: from_dict restaura intensity", sig2.intensity == 0.8)

# ============================================================
# EMOTION READER — EmotionClassifier
# ============================================================
print("\n--- EmotionClassifier ---")
ec = EmotionClassifier()

# Alegria
signals = ec.classify("Gracias, funciona perfecto!")
test("Classifier: detecta alegria", signals[0].emotion == "alegria")
test("Classifier: intensity > 0", signals[0].intensity > 0)

# Frustracion
signals = ec.classify("No funciona, hay un error terrible")
test("Classifier: detecta frustracion", signals[0].emotion == "frustracion")

# Confusion
signals = ec.classify("que quiere decir eso, me confunde, no me queda claro")
test("Classifier: detecta confusion", signals[0].emotion == "confusion")

# Curiosidad
signals = ec.classify("Como funciona esto? Me gustaria saber")
test("Classifier: detecta curiosidad", signals[0].emotion == "curiosidad")

# Urgencia
signals = ec.classify("Necesito esto urgente, rapido por favor")
test("Classifier: detecta urgencia", signals[0].emotion == "urgencia")

# Neutral
signals = ec.classify("hola")
test("Classifier: texto neutral -> neutral", signals[0].emotion == "neutral")

# Multiples señales
signals = ec.classify("No funciona y no entiendo el error")
test("Classifier: multiples emociones detectadas", len(signals) >= 2)

# Puntuacion !!!
signals_exc = ec.classify("NO FUNCIONA!!!")
test("Classifier: !!! amplifica intensidad", any(s.emotion == "frustracion" for s in signals_exc))

# Puntuacion ???
signals_q = ec.classify("Que es esto??? No entiendo nada???")
test("Classifier: ??? amplifica confusion", any(s.emotion == "confusion" for s in signals_q))

# Mayusculas amplifica
signals_upper = ec.classify("NO FUNCIONA NADA")
frustracion_signals = [s for s in signals_upper if s.emotion == "frustracion"]
test("Classifier: mayusculas amplifica intensidad", len(frustracion_signals) > 0 and frustracion_signals[0].intensity > 0.3)

# get_primary_emotion
primary = ec.get_primary_emotion("Genial, me encanta!")
test("Classifier: get_primary_emotion -> alegria", primary == "alegria")

primary_neutral = ec.get_primary_emotion("ok")
test("Classifier: get_primary_emotion texto plano -> neutral", primary_neutral == "neutral")

# Señales ordenadas por intensidad
signals = ec.classify("No funciona y es urgente!")
test("Classifier: signals ordenadas por intensidad", signals[0].intensity >= signals[-1].intensity)

# ============================================================
# EMOTION READER — EmotionHistory
# ============================================================
print("\n--- EmotionHistory ---")
eh = EmotionHistory(max_entries=50)

test("History: inicia vacia", eh.total_readings == 0)
test("History: trend insufficient_data", eh.get_trend() == "insufficient_data")
test("History: dominant_emotion -> neutral", eh.get_dominant_emotion() == "neutral")

# Registrar señales
eh.record([EmotionSignal("alegria", 0.8)])
eh.record([EmotionSignal("alegria", 0.7)])
eh.record([EmotionSignal("alegria", 0.6)])
test("History: 3 registros", eh.total_readings == 3)
test("History: dominant -> alegria", eh.get_dominant_emotion() == "alegria")
test("History: trend mejorando", eh.get_trend() == "mejorando")

# Tendencia empeorando
eh2 = EmotionHistory()
eh2.record([EmotionSignal("frustracion", 0.8)])
eh2.record([EmotionSignal("frustracion", 0.7)])
eh2.record([EmotionSignal("frustracion", 0.6)])
test("History: trend empeorando con frustracion", eh2.get_trend() == "empeorando")

# Estable
eh3 = EmotionHistory()
eh3.record([EmotionSignal("neutral", 0.3)])
eh3.record([EmotionSignal("neutral", 0.3)])
eh3.record([EmotionSignal("neutral", 0.3)])
test("History: trend estable con neutral", eh3.get_trend() == "estable")

# get_recent_emotions
recent = eh.get_recent_emotions(2)
test("History: get_recent_emotions retorna 2", len(recent) == 2)

# record con lista vacia no crashea
eh.record([])
test("History: record vacio no crashea", True)

# maxlen funciona
eh_small = EmotionHistory(max_entries=3)
for i in range(5):
    eh_small.record([EmotionSignal("alegria", 0.5)])
test("History: maxlen 3 mantiene 3", len(eh_small.entries) == 3)

# ============================================================
# EMOTION READER — EmotionReader (coordinador)
# ============================================================
print("\n--- EmotionReader (coordinador) ---")
tmp = tempfile.mkdtemp()
try:
    er = EmotionReader(base_dir=os.path.join(tmp, "emotion"))

    test("EmotionReader: inicia con 0 lecturas", er.total_readings == 0)

    result = er.read("Gracias, perfecto!")
    test("EmotionReader: read retorna dict", isinstance(result, dict))
    test("EmotionReader: read tiene primary", "primary" in result)
    test("EmotionReader: read detecta alegria", result["primary"] == "alegria")
    test("EmotionReader: read tiene intensity", result["intensity"] > 0)
    test("EmotionReader: read tiene trend", "trend" in result)
    test("EmotionReader: total_readings = 1", er.total_readings == 1)

    # Read frustracion
    result2 = er.read("No funciona nada, error total")
    test("EmotionReader: detecta frustracion", result2["primary"] == "frustracion")
    test("EmotionReader: total_readings = 2", er.total_readings == 2)

    # Read curiosidad
    result3 = er.read("Como funciona esto?")
    test("EmotionReader: detecta curiosidad", result3["primary"] == "curiosidad")

    # Context for prompt
    ctx = er.get_context_for_prompt("No funciona!!!", max_chars=300)
    test("EmotionReader: context no vacio para frustracion", len(ctx) > 0)
    test("EmotionReader: context contiene EMOCIONAL", "EMOCIONAL" in ctx)

    ctx_neutral = er.get_context_for_prompt("ok")
    test("EmotionReader: context puede ser vacio para neutral", isinstance(ctx_neutral, str))

    # Stats
    stats = er.get_stats()
    test("EmotionReader: stats tiene total_readings", "total_readings" in stats)
    test("EmotionReader: stats tiene dominant_emotion", "dominant_emotion" in stats)
    test("EmotionReader: stats tiene emotion_counts", "emotion_counts" in stats)

    # Status
    status = er.status()
    test("EmotionReader: status es string", isinstance(status, str))
    test("EmotionReader: status tiene Lecturas", "Lecturas" in status)

    # Report
    report = er.generate_report()
    test("EmotionReader: report tiene EMOTION READER", "EMOTION READER" in report)

    # Save/Load
    er.save()
    er2 = EmotionReader(base_dir=os.path.join(tmp, "emotion"))
    test("EmotionReader: save/load preserva total_readings", er2.total_readings == er.total_readings)
    test("EmotionReader: save/load preserva history", len(er2.history.entries) > 0)

    # Clear
    er.clear()
    test("EmotionReader: clear resetea", er.total_readings == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# EMPATHY ENGINE — EmpathyStrategy
# ============================================================
print("\n--- EmpathyStrategy ---")
from core.empathy_engine import EmpathyStrategy, StrategySelector, EffectivenessTracker, EmpathyEngine

es = EmpathyStrategy("validar")
test("EmpathyStrategy: name = validar", es.name == "validar")
test("EmpathyStrategy: tiene description", len(es.description) > 0)
test("EmpathyStrategy: tiene prompt_modifier", len(es.prompt_modifier) > 0)
test("EmpathyStrategy: tiene triggers", len(es.triggers) > 0)
test("EmpathyStrategy: tiene priority", es.priority > 0)

es2 = EmpathyStrategy("celebrar")
test("EmpathyStrategy: celebrar tiene triggers", "alegria" in es2.triggers)

all_strategies = EmpathyStrategy.get_all()
test("EmpathyStrategy: 5 estrategias", len(all_strategies) == 5)
test("EmpathyStrategy: validar en lista", "validar" in all_strategies)

# Estrategia inexistente -> fallback a validar
es_unknown = EmpathyStrategy("inexistente")
test("EmpathyStrategy: fallback funciona", es_unknown.name == "inexistente")

# ============================================================
# EMPATHY ENGINE — StrategySelector
# ============================================================
print("\n--- StrategySelector ---")
ss = StrategySelector()

# Frustracion -> validar o redirigir
sel = ss.select("frustracion", 0.8)
test("StrategySelector: frustracion -> estrategia valida", sel in ["validar", "redirigir", "calmar"])

# Alegria -> celebrar
sel = ss.select("alegria", 0.8)
test("StrategySelector: alegria -> celebrar", sel == "celebrar")

# Confusion -> validar o profundizar
sel = ss.select("confusion", 0.5)
test("StrategySelector: confusion -> validar/profundizar", sel in ["validar", "profundizar"])

# Urgencia -> calmar o redirigir
sel = ss.select("urgencia", 0.9)
test("StrategySelector: urgencia -> calmar/redirigir", sel in ["calmar", "redirigir"])

# Con historial recurrente -> redirigir
history = [
    {"emotion": "frustracion"}, {"emotion": "frustracion"},
    {"emotion": "frustracion"},
]
sel = ss.select("frustracion", 0.8, history=history)
test("StrategySelector: frustracion recurrente -> redirigir", sel == "redirigir")

# Emocion desconocida -> fallback
sel = ss.select("asombro", 0.5)
test("StrategySelector: emocion desconocida -> validar", sel == "validar")

# ============================================================
# EMPATHY ENGINE — EffectivenessTracker
# ============================================================
print("\n--- EffectivenessTracker ---")
et = EffectivenessTracker()
test("EffectivenessTracker: inicia vacio", et.total_uses == 0)

et.record_use("validar")
et.record_use("validar")
et.record_use("celebrar")
test("EffectivenessTracker: 3 usos totales", et.total_uses == 3)
test("EffectivenessTracker: validar = 2 usos", et.usage["validar"] == 2)

# Feedback
et.record_feedback("validar", positive=True)
et.record_feedback("validar", positive=True)
et.record_feedback("validar", positive=False)
test("EffectivenessTracker: efectividad validar = 66%", abs(et.get_effectiveness("validar") - 0.666) < 0.01)

# Sin feedback -> 0.5
test("EffectivenessTracker: sin feedback -> 0.5", et.get_effectiveness("redirigir") == 0.5)

# Best strategy
best = et.get_best_strategy()
test("EffectivenessTracker: best strategy es string", isinstance(best, str))

# Serialización
d = et.to_dict()
test("EffectivenessTracker: to_dict tiene usage", "usage" in d)
et2 = EffectivenessTracker.from_dict(d)
test("EffectivenessTracker: from_dict preserva total_uses", et2.total_uses == 3)
test("EffectivenessTracker: from_dict preserva feedback", et2.feedback_positive["validar"] == 2)

# ============================================================
# EMPATHY ENGINE — EmpathyEngine (coordinador)
# ============================================================
print("\n--- EmpathyEngine (coordinador) ---")
tmp = tempfile.mkdtemp()
try:
    ee = EmpathyEngine(base_dir=os.path.join(tmp, "empathy"))

    test("EmpathyEngine: inicia con 0 respuestas", ee.total_empathy_responses == 0)
    test("EmpathyEngine: estrategia inicial = validar", ee.current_strategy == "validar")

    # Respond
    result = ee.respond("frustracion", 0.8)
    test("EmpathyEngine: respond retorna dict", isinstance(result, dict))
    test("EmpathyEngine: respond tiene strategy", "strategy" in result)
    test("EmpathyEngine: respond tiene prompt_modifier", "prompt_modifier" in result)
    test("EmpathyEngine: total_empathy_responses = 1", ee.total_empathy_responses == 1)
    test("EmpathyEngine: last_emotion = frustracion", ee.last_emotion == "frustracion")

    result2 = ee.respond("alegria", 0.9)
    test("EmpathyEngine: alegria -> celebrar", result2["strategy"] == "celebrar")

    # Context for prompt
    ctx = ee.get_context_for_prompt("frustracion", 0.8, max_chars=300)
    test("EmpathyEngine: context no vacio", len(ctx) > 0)
    test("EmpathyEngine: context tiene EMPATIA", "EMPATIA" in ctx)

    # Context vacio para neutral/baja intensidad
    ctx_empty = ee.get_context_for_prompt("neutral", 0.1)
    test("EmpathyEngine: context vacio para neutral baja", ctx_empty == "")

    # Feedback
    ee.record_feedback(positive=True)
    test("EmpathyEngine: feedback no crashea", True)

    # Stats
    stats = ee.get_stats()
    test("EmpathyEngine: stats tiene total_empathy_responses", "total_empathy_responses" in stats)
    test("EmpathyEngine: stats tiene effectiveness", "effectiveness" in stats)
    test("EmpathyEngine: stats tiene best_strategy", "best_strategy" in stats)

    # Status
    status = ee.status()
    test("EmpathyEngine: status es string", isinstance(status, str))
    test("EmpathyEngine: status tiene Respuestas", "Respuestas" in status)

    # Report
    report = ee.generate_report()
    test("EmpathyEngine: report tiene EMPATHY ENGINE", "EMPATHY ENGINE" in report)

    # Save/Load
    ee.save()
    ee2 = EmpathyEngine(base_dir=os.path.join(tmp, "empathy"))
    test("EmpathyEngine: save/load preserva total", ee2.total_empathy_responses == ee.total_empathy_responses)
    test("EmpathyEngine: save/load preserva last_emotion", ee2.last_emotion == ee.last_emotion)

    # Clear
    ee.clear()
    test("EmpathyEngine: clear resetea", ee.total_empathy_responses == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# CONFLICT RESOLVER — ConflictSignal
# ============================================================
print("\n--- ConflictSignal ---")
from core.conflict_resolver import ConflictSignal, ConflictDetector, ResolutionStrategy, EscalationTracker, ConflictResolver

cs = ConflictSignal("moderate", "no es correcto", "eso no es correcto")
test("ConflictSignal: level = moderate", cs.level == "moderate")
test("ConflictSignal: trigger correcto", cs.trigger == "no es correcto")
test("ConflictSignal: text truncado a 200", len(cs.text) <= 200)
test("ConflictSignal: timestamp > 0", cs.timestamp > 0)

d = cs.to_dict()
test("ConflictSignal: to_dict tiene level", d["level"] == "moderate")

# ============================================================
# CONFLICT RESOLVER — ConflictDetector
# ============================================================
print("\n--- ConflictDetector ---")
cd = ConflictDetector()

# Severe
sig = cd.detect("Ya te dije que no funciona, no entendes nada!")
test("ConflictDetector: detecta severe", sig is not None and sig.level == "severe")

# Moderate
sig = cd.detect("No, eso esta mal")
test("ConflictDetector: detecta moderate", sig is not None and sig.level == "moderate")

# Mild
sig = cd.detect("No exactamente, casi pero no")
test("ConflictDetector: detecta mild", sig is not None and sig.level == "mild")

# Sin conflicto
sig = cd.detect("Si, eso esta bien, gracias")
test("ConflictDetector: no conflicto -> None", sig is None)

# is_correction
test("ConflictDetector: 'no, eso esta mal' es correccion", cd.is_correction("no, eso esta mal"))
test("ConflictDetector: 'gracias' no es correccion", not cd.is_correction("gracias perfecto"))

# Texto vacio
sig = cd.detect("")
test("ConflictDetector: texto vacio -> None", sig is None)

# ============================================================
# CONFLICT RESOLVER — ResolutionStrategy
# ============================================================
print("\n--- ResolutionStrategy ---")
rs = ResolutionStrategy("conceder")
test("ResolutionStrategy: name = conceder", rs.name == "conceder")
test("ResolutionStrategy: tiene description", len(rs.description) > 0)
test("ResolutionStrategy: tiene prompt", len(rs.prompt) > 0)
test("ResolutionStrategy: tiene for_levels", len(rs.for_levels) > 0)

rs2 = ResolutionStrategy("clarificar")
test("ResolutionStrategy: clarificar tiene mild", "mild" in rs2.for_levels)

rs3 = ResolutionStrategy("alternativa")
test("ResolutionStrategy: alternativa existe", rs3.name == "alternativa")

# ============================================================
# CONFLICT RESOLVER — EscalationTracker
# ============================================================
print("\n--- EscalationTracker ---")
et = EscalationTracker(window=10)

test("EscalationTracker: inicia sin conflictos", et.total_conflicts == 0)
test("EscalationTracker: no escalando", not et.is_escalating())
test("EscalationTracker: resolution_rate = 1.0", et.get_resolution_rate() == 1.0)

# Conflictos
et.record_conflict("moderate")
et.record_conflict("moderate")
test("EscalationTracker: 2 conflictos", et.total_conflicts == 2)
test("EscalationTracker: 2 no escala", not et.is_escalating())

# 3+ conflictos -> escala
et.record_conflict("severe")
et.record_conflict("severe")
et.record_conflict("severe")
test("EscalationTracker: 5 conflictos escala", et.is_escalating())

# Resolucion
et.record_resolution()
test("EscalationTracker: 1 resuelto", et.resolved == 1)

# Serialización
d = et.to_dict()
test("EscalationTracker: to_dict tiene events", "events" in d)
et2 = EscalationTracker.from_dict(d)
test("EscalationTracker: from_dict preserva total", et2.total_conflicts == et.total_conflicts)

# ============================================================
# CONFLICT RESOLVER — ConflictResolver (coordinador)
# ============================================================
print("\n--- ConflictResolver (coordinador) ---")
tmp = tempfile.mkdtemp()
try:
    cr = ConflictResolver(base_dir=os.path.join(tmp, "conflict"))

    test("ConflictResolver: inicia sin conflictos", cr.tracker.total_conflicts == 0)

    # Analizar conflicto
    result = cr.analyze("No, eso esta mal, te equivocas")
    test("ConflictResolver: detect conflict", result["conflict"] is True)
    test("ConflictResolver: tiene level", "level" in result)
    test("ConflictResolver: tiene strategy", "strategy" in result)
    test("ConflictResolver: tiene prompt_modifier", "prompt_modifier" in result)
    test("ConflictResolver: tiene is_escalating", "is_escalating" in result)

    # Sin conflicto
    result2 = cr.analyze("Si, perfecto, gracias")
    test("ConflictResolver: no conflict", result2["conflict"] is False)

    # Context for prompt con conflicto
    ctx = cr.get_context_for_prompt("Ya te dije, no entendes nada")
    test("ConflictResolver: context no vacio para conflicto", len(ctx) > 0)
    test("ConflictResolver: context tiene CONFLICTO", "CONFLICTO" in ctx)

    # Context vacio sin conflicto
    ctx2 = cr.get_context_for_prompt("Ok, gracias")
    test("ConflictResolver: context vacio sin conflicto", ctx2 == "")

    # Resolución después de conflicto
    cr.analyze("no, esta mal")  # Genera conflicto
    cr.current_conflict = ConflictSignal("moderate", "test", "test")
    cr.analyze("ok gracias, ahora si")  # Resuelve
    test("ConflictResolver: resolucion detectada", cr.total_resolved > 0)

    # Stats
    stats = cr.get_stats()
    test("ConflictResolver: stats tiene total_conflicts", "total_conflicts" in stats)
    test("ConflictResolver: stats tiene resolution_rate", "resolution_rate" in stats)
    test("ConflictResolver: stats tiene top_patterns", "top_patterns" in stats)

    # Status
    status = cr.status()
    test("ConflictResolver: status es string", isinstance(status, str))
    test("ConflictResolver: status tiene Conflictos", "Conflictos" in status)

    # Report
    report = cr.generate_report()
    test("ConflictResolver: report tiene CONFLICT RESOLVER", "CONFLICT RESOLVER" in report)

    # Save/Load
    cr.save()
    cr2 = ConflictResolver(base_dir=os.path.join(tmp, "conflict"))
    test("ConflictResolver: save/load preserva total_resolved", cr2.total_resolved == cr.total_resolved)
    test("ConflictResolver: save/load preserva patterns", len(cr2.conflict_patterns) > 0)

    # Clear
    cr.clear()
    test("ConflictResolver: clear resetea conflictos", cr.tracker.total_conflicts == 0)
    test("ConflictResolver: clear resetea resueltos", cr.total_resolved == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# INTEGRACION — Imports
# ============================================================
print("\n--- Integracion ---")
from config import GENESIS_VERSION

test("Version >= 3.1.0", GENESIS_VERSION >= "3.1.0")

# Verificar imports en genesis.py
import genesis as g_mod

# El refactor a MIXINS movio codigo de la clase Genesis a core/genesis_*.py
# y los imports de estos modulos son ahora lazy (dentro de _init_lazy_module).
# Concatenamos la fuente de la clase con la de los mixins para la integracion real.
import inspect
genesis_source = inspect.getsource(g_mod.Genesis)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
genesis_source += "\n" + open(os.path.join(_root, "genesis.py"), encoding="utf-8").read()
for _mod in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    genesis_source += "\n" + open(os.path.join(_root, "core", _mod), encoding="utf-8").read()

# Imports lazy: la clase se importa dentro de _init_lazy_module en genesis.py
test("Integracion: EmotionReader importado", "from core.emotion_reader import EmotionReader" in genesis_source)
test("Integracion: EmpathyEngine importado", "from core.empathy_engine import EmpathyEngine" in genesis_source)
test("Integracion: ConflictResolver importado", "from core.conflict_resolver import ConflictResolver" in genesis_source)
test("Integracion: emotion_reader en Genesis", "emotion_reader" in genesis_source)
test("Integracion: empathy_engine en Genesis", "empathy_engine" in genesis_source)
test("Integracion: conflict_resolver en Genesis", "conflict_resolver" in genesis_source)

# Verificar context injection
test("Integracion: emotion_reader context en process", "emotion_context" in genesis_source)
test("Integracion: empathy_engine context en process", "empathy_context" in genesis_source)
test("Integracion: conflict_resolver context en process", "conflict_context" in genesis_source)

# Verificar comandos
test("Integracion: /emotions comando", '"/emotions"' in genesis_source)
test("Integracion: /empathy comando", '"/empathy"' in genesis_source)
test("Integracion: /conflict comando", '"/conflict"' in genesis_source)

# Verificar saves
# save_all() usa la lista saveable_modules con el nombre del modulo (ya no self.X.save())
test("Integracion: emotion_reader.save()", '"emotion_reader"' in genesis_source)
test("Integracion: empathy_engine.save()", '"empathy_engine"' in genesis_source)
test("Integracion: conflict_resolver.save()", '"conflict_resolver"' in genesis_source)

# Verificar status
test("Integracion: EMOTION READER en status", "EMOTION READER" in genesis_source)
test("Integracion: EMPATHY ENGINE en status", "EMPATHY ENGINE" in genesis_source)
test("Integracion: CONFLICT RESOLVER en status", "CONFLICT RESOLVER" in genesis_source)

# Verificar dashboard
test("Integracion: emotion_reader en dashboard", "emotion_reader" in genesis_source and "register" in genesis_source)

# Verificar web_ui.py
web_source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_ui.py"), encoding="utf-8").read()
test("Integracion web: EmotionReader en health grid", "EmotionReader" in web_source)
test("Integracion web: EmpathyEngine en health grid", "EmpathyEngine" in web_source)
test("Integracion web: ConflictResolver en health grid", "ConflictResolver" in web_source)
test("Integracion web: emotion_reader stats", "emotion_reader" in web_source)
test("Integracion web: empathy_engine stats", "empathy_engine" in web_source)
test("Integracion web: conflict_resolver stats", "conflict_resolver" in web_source)

# ============================================================
# RESULTADOS
# ============================================================
print("\n" + "=" * 60)
print(f"RESULTADOS: {passed} passed, {failed} failed de {passed + failed} tests")
if errors:
    print(f"\nTests fallidos:")
    for e in errors:
        print(f"  - {e}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
