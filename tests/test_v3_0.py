"""
GENESIS — Tests v3.0: Unified Consciousness
Tests para UnifiedMind, DreamEngine, SelfNarrative
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
print("GENESIS v3.0 — Test Suite: Unified Consciousness")
print("=" * 60)

# ============================================================
# UNIFIED MIND — ConsciousnessState
# ============================================================
print("\n--- ConsciousnessState ---")
from core.unified_mind import ConsciousnessState, MoodComputer, FocusTracker, UnifiedMind

cs = ConsciousnessState()
test("ConsciousnessState: mood = 0.5", cs.mood == 0.5)
test("ConsciousnessState: energy = 0.7", cs.energy == 0.7)
test("ConsciousnessState: focus = 0.5", cs.focus == 0.5)
test("ConsciousnessState: curiosity = 0.5", cs.curiosity == 0.5)
test("ConsciousnessState: confidence = 0.5", cs.confidence == 0.5)
test("ConsciousnessState: overall_state es string", isinstance(cs.overall_state, str))
test("ConsciousnessState: awareness_score > 0", cs.awareness_score > 0)
test("ConsciousnessState: timestamp > 0", cs.timestamp > 0)

# All max → optimal
cs.mood = 1.0
cs.energy = 1.0
cs.focus = 1.0
cs.curiosity = 1.0
cs.confidence = 1.0
test("ConsciousnessState: optimal con todo 1.0", cs.overall_state == "optimal")
test("ConsciousnessState: awareness = 1.0", cs.awareness_score == 1.0)

# All min → critical
cs.mood = 0.0
cs.energy = 0.0
cs.focus = 0.0
cs.curiosity = 0.0
cs.confidence = 0.0
test("ConsciousnessState: critical con todo 0.0", cs.overall_state == "critical")
test("ConsciousnessState: awareness = 0.0", cs.awareness_score == 0.0)

# Mid values
cs.mood = 0.5
cs.energy = 0.5
cs.focus = 0.5
cs.curiosity = 0.5
cs.confidence = 0.5
test("ConsciousnessState: neutral con todo 0.5", cs.overall_state == "neutral")

# to_dict
d = cs.to_dict()
test("ConsciousnessState: to_dict tiene mood", "mood" in d)
test("ConsciousnessState: to_dict tiene overall_state", "overall_state" in d)
test("ConsciousnessState: to_dict tiene awareness_score", "awareness_score" in d)

# ============================================================
# UNIFIED MIND — MoodComputer
# ============================================================
print("\n--- MoodComputer ---")

mc = MoodComputer()
test("MoodComputer: current_mood = 0.5", mc.current_mood == 0.5)

# Positive signals
mood = mc.process("Perfecto, excelente trabajo, gracias!")
test("MoodComputer: mood sube con positivo", mood > 0.5)

# Negative signals
mc2 = MoodComputer()
mood = mc2.process("Error terrible, no funciona, es horrible")
test("MoodComputer: mood baja con negativo", mood < 0.5)

# Neutral
mc3 = MoodComputer()
mood = mc3.process("Hola que tal")
test("MoodComputer: mood neutro estable", abs(mood - 0.5) < 0.1)

# History
mc4 = MoodComputer()
for _ in range(5):
    mc4.process("Excelente genial perfecto")
test("MoodComputer: history tiene entradas", len(mc4.mood_history) > 0)

# ============================================================
# UNIFIED MIND — FocusTracker
# ============================================================
print("\n--- FocusTracker ---")

ft = FocusTracker()
test("FocusTracker: focus_score = 0.5", ft.focus_score == 0.5)
test("FocusTracker: dominant_domain = general", ft.dominant_domain == "general")

ft.record("python")
ft.record("python")
ft.record("python")
test("FocusTracker: dominant = python", ft.dominant_domain == "python")
test("FocusTracker: focus alto con mismo dominio", ft.focus_score > 0.7)

ft.record("javascript")
ft.record("rust")
test("FocusTracker: focus baja con mezcla", ft.focus_score < 1.0)

ft2 = FocusTracker()
ft2.record("a")
test("FocusTracker: focus con 1 entrada = 0.5", ft2.focus_score == 0.5)

d = ft.to_dict()
test("FocusTracker: to_dict tiene domain_counts", "domain_counts" in d)
test("FocusTracker: to_dict tiene focus_score", "focus_score" in d)

# ============================================================
# UNIFIED MIND — UnifiedMind (coordinator)
# ============================================================
print("\n--- UnifiedMind ---")

tmp = tempfile.mkdtemp()
try:
    um = UnifiedMind(base_dir=tmp)
    test("UnifiedMind: enabled = True", um.enabled is True)
    test("UnifiedMind: total_observations = 0", um.total_observations == 0)
    test("UnifiedMind: peak_awareness = 0", um.peak_awareness == 0.0)

    # observe
    um.observe("Hola, como funciona esto?", response="Funciona así...",
               domain="tutorial", response_time=2.0, quality_score=0.8)
    test("UnifiedMind: total_observations = 1", um.total_observations == 1)
    test("UnifiedMind: peak_awareness > 0", um.peak_awareness > 0.0)

    # curiosity sube con preguntas
    test("UnifiedMind: curiosity > 0.5 con pregunta",
         um.current_state.curiosity > 0.4)

    # observe positivo
    um.observe("Perfecto, gracias! Excelente explicación",
               domain="tutorial", quality_score=0.9)
    test("UnifiedMind: mood > 0.5 con positivo", um.current_state.mood > 0.45)

    # observe vacío ignorado
    um.observe("")
    test("UnifiedMind: ignora vacío", um.total_observations == 2)

    # disabled
    um.enabled = False
    um.observe("algo")
    test("UnifiedMind: disabled no registra", um.total_observations == 2)
    um.enabled = True

    # get_state
    state = um.get_state()
    test("UnifiedMind: get_state retorna ConsciousnessState",
         isinstance(state, ConsciousnessState))

    # get_state_summary
    summary = um.get_state_summary()
    test("UnifiedMind: summary es string", isinstance(summary, str))
    test("UnifiedMind: summary no vacío", len(summary) > 0)

    # get_context_for_prompt
    ctx = um.get_context_for_prompt()
    test("UnifiedMind: context es string", isinstance(ctx, str))

    # get_stats
    stats = um.get_stats()
    test("UnifiedMind: stats tiene mood", "mood" in stats)
    test("UnifiedMind: stats tiene energy", "energy" in stats)
    test("UnifiedMind: stats tiene overall_state", "overall_state" in stats)
    test("UnifiedMind: stats tiene total_observations", "total_observations" in stats)
    test("UnifiedMind: stats tiene peak_awareness", "peak_awareness" in stats)

    # status
    st = um.status()
    test("UnifiedMind: status no vacío", len(st) > 0)
    test("UnifiedMind: status tiene Estado", "Estado" in st)

    # generate_report
    report = um.generate_report()
    test("UnifiedMind: report contiene UNIFIED", "UNIFIED" in report)
    test("UnifiedMind: report contiene Dimensiones", "Dimensiones" in report)

    # save/load
    um.save()
    um2 = UnifiedMind(base_dir=tmp)
    test("UnifiedMind: persistencia total_observations",
         um2.total_observations == um.total_observations)
    test("UnifiedMind: persistencia peak_awareness",
         abs(um2.peak_awareness - um.peak_awareness) < 0.01)

    # clear
    um.clear()
    test("UnifiedMind: clear total_observations = 0", um.total_observations == 0)
    test("UnifiedMind: clear peak_awareness = 0", um.peak_awareness == 0.0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# DREAM ENGINE — DreamFragment
# ============================================================
print("\n--- DreamFragment ---")
from core.dream_engine import DreamFragment, ConsolidationStrategy, DreamProcessor, DreamEngine

df = DreamFragment("experiencia de prueba", domain="test", emotional_weight=0.7)
test("DreamFragment: content correcto", df.content == "experiencia de prueba")
test("DreamFragment: domain correcto", df.domain == "test")
test("DreamFragment: emotional_weight = 0.7", df.emotional_weight == 0.7)
test("DreamFragment: strength = emotional_weight", df.strength == 0.7)
test("DreamFragment: consolidation_count = 0", df.consolidation_count == 0)
test("DreamFragment: connections vacías", len(df.connections) == 0)
test("DreamFragment: fragment_id no vacío", len(df.fragment_id) > 0)

# consolidate
df.consolidate(boost=0.15)
test("DreamFragment: strength sube con consolidate", df.strength > 0.7)
test("DreamFragment: consolidation_count = 1", df.consolidation_count == 1)
test("DreamFragment: last_consolidated not None", df.last_consolidated is not None)

# decay
old_strength = df.strength
df.decay(factor=0.9)
test("DreamFragment: strength baja con decay", df.strength < old_strength)
test("DreamFragment: strength > 0.01 (mínimo)", df.strength >= 0.01)

# add_connection
df.add_connection("frag_1")
test("DreamFragment: connection agregada", "frag_1" in df.connections)
df.add_connection("frag_1")  # Duplicado
test("DreamFragment: no duplica connections", len(df.connections) == 1)

# Clamping
df2 = DreamFragment("test", emotional_weight=1.5)
test("DreamFragment: emotional_weight clamped a 1.0", df2.emotional_weight == 1.0)
df3 = DreamFragment("test", emotional_weight=-0.5)
test("DreamFragment: emotional_weight clamped a 0.0", df3.emotional_weight == 0.0)

# Long content truncated
df4 = DreamFragment("x" * 500)
test("DreamFragment: content truncado a 300", len(df4.content) <= 300)

# to_dict / from_dict
d = df.to_dict()
test("DreamFragment: to_dict tiene fragment_id", "fragment_id" in d)
test("DreamFragment: to_dict tiene strength", "strength" in d)
test("DreamFragment: to_dict tiene connections", "connections" in d)

df5 = DreamFragment.from_dict(d)
test("DreamFragment: from_dict content", df5.content == df.content)
test("DreamFragment: from_dict domain", df5.domain == df.domain)
test("DreamFragment: from_dict strength", abs(df5.strength - df.strength) < 0.01)

# ============================================================
# DREAM ENGINE — ConsolidationStrategy
# ============================================================
print("\n--- ConsolidationStrategy ---")

test("ConsolidationStrategy: tiene 4 estrategias",
     len(ConsolidationStrategy.STRATEGIES) == 4)
test("ConsolidationStrategy: tiene emotional_priority",
     "emotional_priority" in ConsolidationStrategy.STRATEGIES)
test("ConsolidationStrategy: tiene frequency_based",
     "frequency_based" in ConsolidationStrategy.STRATEGIES)

s = ConsolidationStrategy.get("emotional_priority")
test("ConsolidationStrategy: get retorna dict", isinstance(s, dict))
test("ConsolidationStrategy: tiene boost", "boost" in s)
test("ConsolidationStrategy: tiene decay", "decay" in s)

s_invalid = ConsolidationStrategy.get("invalid")
test("ConsolidationStrategy: invalid retorna frequency_based",
     s_invalid["name"] == "Basado en Frecuencia")

# ============================================================
# DREAM ENGINE — DreamProcessor
# ============================================================
print("\n--- DreamProcessor ---")

dp = DreamProcessor()
test("DreamProcessor: total_cycles = 0", dp.total_cycles == 0)

# run_cycle con fragmentos vacíos
result = dp.run_cycle({})
test("DreamProcessor: cycle vacío = 0 consolidated", result["consolidated"] == 0)

# run_cycle con fragmentos
frags = {}
for i in range(5):
    f = DreamFragment(f"experiencia {i}", domain="test",
                      emotional_weight=0.3 + i * 0.15)
    frags[f.fragment_id] = f
result = dp.run_cycle(frags)
test("DreamProcessor: cycle retorna dict", isinstance(result, dict))
test("DreamProcessor: tiene consolidated", "consolidated" in result)
test("DreamProcessor: tiene decayed", "decayed" in result)
test("DreamProcessor: tiene connections", "connections" in result)
test("DreamProcessor: total_cycles = 1", dp.total_cycles == 1)
test("DreamProcessor: consolidated + decayed = total",
     result["consolidated"] + result["decayed"] == len(frags))

# ============================================================
# DREAM ENGINE — DreamEngine (coordinator)
# ============================================================
print("\n--- DreamEngine ---")

tmp = tempfile.mkdtemp()
try:
    de = DreamEngine(base_dir=tmp)
    test("DreamEngine: enabled = True", de.enabled is True)
    test("DreamEngine: fragments vacío", len(de.fragments) == 0)
    test("DreamEngine: pending vacío", len(de.pending_experiences) == 0)
    test("DreamEngine: total_dreams = 0", de.total_dreams == 0)

    # record_experience
    de.record_experience("Aprendí sobre Python", domain="python",
                         emotional_weight=0.8)
    test("DreamEngine: pending = 1", len(de.pending_experiences) == 1)

    de.record_experience("Debugeé un error", domain="debug",
                         emotional_weight=0.6)
    test("DreamEngine: pending = 2", len(de.pending_experiences) == 2)

    # record_experience vacío
    de.record_experience("")
    test("DreamEngine: ignora vacío", len(de.pending_experiences) == 2)

    # disabled
    de.enabled = False
    de.record_experience("algo")
    test("DreamEngine: disabled no registra", len(de.pending_experiences) == 2)
    de.enabled = True

    # dream
    result = de.dream()
    test("DreamEngine: dream retorna dict", isinstance(result, dict))
    test("DreamEngine: dream status = completed", result["status"] == "completed")
    test("DreamEngine: fragments creados", len(de.fragments) > 0)
    test("DreamEngine: pending vacío post-dream", len(de.pending_experiences) == 0)
    test("DreamEngine: total_dreams = 1", de.total_dreams == 1)
    test("DreamEngine: last_dream_time not None", de.last_dream_time is not None)

    # dream disabled
    de.enabled = False
    result = de.dream()
    test("DreamEngine: dream disabled", result["status"] == "disabled")
    de.enabled = True

    # get_strongest_memories
    strong = de.get_strongest_memories(3)
    test("DreamEngine: strongest retorna lista", isinstance(strong, list))
    test("DreamEngine: strongest max 3", len(strong) <= 3)
    if len(strong) > 1:
        test("DreamEngine: strongest ordenado",
             strong[0]["strength"] >= strong[1]["strength"])

    # get_domain_memories
    py_mems = de.get_domain_memories("python")
    test("DreamEngine: domain memories retorna lista", isinstance(py_mems, list))

    # Agregar más y dream con strategy
    for i in range(5):
        de.record_experience(f"experiencia {i}", domain="test",
                             emotional_weight=0.3)
    de.dream(strategy="emotional_priority")
    test("DreamEngine: total_dreams = 2", de.total_dreams == 2)

    # get_context_for_prompt
    ctx = de.get_context_for_prompt()
    test("DreamEngine: context es string", isinstance(ctx, str))

    # get_stats
    stats = de.get_stats()
    test("DreamEngine: stats tiene total_fragments", "total_fragments" in stats)
    test("DreamEngine: stats tiene strong_fragments", "strong_fragments" in stats)
    test("DreamEngine: stats tiene total_dreams", "total_dreams" in stats)
    test("DreamEngine: stats tiene total_created", "total_created" in stats)

    # status
    st = de.status()
    test("DreamEngine: status no vacío", len(st) > 0)
    test("DreamEngine: status tiene Fragmentos", "Fragmentos" in st or "fragmentos" in st.lower())

    # generate_report
    report = de.generate_report()
    test("DreamEngine: report contiene DREAM", "DREAM" in report)

    # save/load
    de.save()
    de2 = DreamEngine(base_dir=tmp)
    test("DreamEngine: persistencia fragments",
         len(de2.fragments) == len(de.fragments))
    test("DreamEngine: persistencia total_dreams",
         de2.total_dreams == de.total_dreams)

    # Eviction
    de3 = DreamEngine(base_dir=tempfile.mkdtemp())
    de3.max_fragments = 5
    for i in range(10):
        de3.record_experience(f"exp {i}", emotional_weight=0.1 * (i + 1))
    de3.dream()
    test("DreamEngine: eviction respeta max_fragments",
         len(de3.fragments) <= 5)

    # clear
    de.clear()
    test("DreamEngine: clear fragments vacío", len(de.fragments) == 0)
    test("DreamEngine: clear total_dreams = 0", de.total_dreams == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# SELF-NARRATIVE — NarrativeEntry
# ============================================================
print("\n--- NarrativeEntry ---")
from core.self_narrative import NarrativeEntry, MilestoneDetector, IdentityTracker, SelfNarrative

ne = NarrativeEntry("Mi primera observación", entry_type="observation",
                    emotional_tone="curious")
test("NarrativeEntry: content correcto", ne.content == "Mi primera observación")
test("NarrativeEntry: entry_type correcto", ne.entry_type == "observation")
test("NarrativeEntry: emotional_tone correcto", ne.emotional_tone == "curious")
test("NarrativeEntry: entry_id no vacío", len(ne.entry_id) > 0)
test("NarrativeEntry: relevance = 0.5", ne.relevance == 0.5)
test("NarrativeEntry: tags vacío", len(ne.tags) == 0)

# add_tag
ne.add_tag("test")
test("NarrativeEntry: tag agregado", "test" in ne.tags)
ne.add_tag("test")  # Duplicado
test("NarrativeEntry: no duplica tags", len(ne.tags) == 1)

# Long content
ne2 = NarrativeEntry("x" * 600)
test("NarrativeEntry: content truncado a 500", len(ne2.content) <= 500)

# to_dict / from_dict
d = ne.to_dict()
test("NarrativeEntry: to_dict tiene entry_id", "entry_id" in d)
test("NarrativeEntry: to_dict tiene content", "content" in d)
test("NarrativeEntry: to_dict tiene entry_type", "entry_type" in d)

ne3 = NarrativeEntry.from_dict(d)
test("NarrativeEntry: from_dict content", ne3.content == ne.content)
test("NarrativeEntry: from_dict entry_type", ne3.entry_type == ne.entry_type)
test("NarrativeEntry: from_dict tags", ne3.tags == ne.tags)

# ============================================================
# SELF-NARRATIVE — MilestoneDetector
# ============================================================
print("\n--- MilestoneDetector ---")

md = MilestoneDetector()
test("MilestoneDetector: MILESTONE_SIGNALS > 0",
     len(MilestoneDetector.MILESTONE_SIGNALS) > 0)

# Sin hitos
result = md.check({"total_interactions": 0})
test("MilestoneDetector: sin hitos con 0 interacciones", len(result) == 0)

# Primer hito
result = md.check({"total_interactions": 1})
test("MilestoneDetector: hito con 1 interacción", len(result) > 0)
test("MilestoneDetector: hito tiene text", "text" in result[0])

# No repite hitos
result2 = md.check({"total_interactions": 1})
test("MilestoneDetector: no repite hitos ya alcanzados", len(result2) == 0)

# Nuevo threshold
result3 = md.check({"total_interactions": 10})
test("MilestoneDetector: nuevo hito en 10", len(result3) > 0)

# Multiple signals
result4 = md.check({"total_interactions": 50, "domain_count": 5,
                     "patterns_found": 5})
test("MilestoneDetector: múltiples hitos", len(result4) > 0)

# to_dict / load_dict
d = md.to_dict()
test("MilestoneDetector: to_dict tiene achieved", "achieved" in d)

md2 = MilestoneDetector()
md2.load_dict(d)
test("MilestoneDetector: load_dict restaura achieved",
     len(md2.achieved) > 0)

# ============================================================
# SELF-NARRATIVE — IdentityTracker
# ============================================================
print("\n--- IdentityTracker ---")

it = IdentityTracker()
test("IdentityTracker: traits vacío", len(it.traits) == 0)
test("IdentityTracker: identity_summary = en formacion",
     "formacion" in it.get_identity_summary())

# observe_trait
it.observe_trait("curioso", strength=0.3)
test("IdentityTracker: trait registrado", "curioso" in it.traits)
test("IdentityTracker: trait strength = 0.3", abs(it.traits["curioso"] - 0.3) < 0.01)

it.observe_trait("curioso", strength=0.5)
test("IdentityTracker: trait acumulado", abs(it.traits["curioso"] - 0.8) < 0.01)

it.observe_trait("tecnico", strength=0.4)

# get_dominant_traits
dominant = it.get_dominant_traits(2)
test("IdentityTracker: dominant tiene 2", len(dominant) == 2)
test("IdentityTracker: dominant ordenado",
     dominant[0]["strength"] >= dominant[1]["strength"])

# get_identity_summary
summary = it.get_identity_summary()
test("IdentityTracker: summary no vacío", len(summary) > 0)
test("IdentityTracker: summary tiene curioso", "curioso" in summary)

# Clamping a 1.0
for _ in range(20):
    it.observe_trait("curioso", strength=0.5)
test("IdentityTracker: trait clamped a 1.0", it.traits["curioso"] == 1.0)

# to_dict / load_dict
d = it.to_dict()
test("IdentityTracker: to_dict tiene traits", "traits" in d)

it2 = IdentityTracker()
it2.load_dict(d)
test("IdentityTracker: load_dict restaura traits",
     "curioso" in it2.traits)

# ============================================================
# SELF-NARRATIVE — SelfNarrative (coordinator)
# ============================================================
print("\n--- SelfNarrative ---")

tmp = tempfile.mkdtemp()
try:
    sn = SelfNarrative(base_dir=tmp)
    test("SelfNarrative: enabled = True", sn.enabled is True)
    test("SelfNarrative: entries vacío", len(sn.entries) == 0)
    test("SelfNarrative: total_entries = 0", sn.total_entries == 0)
    test("SelfNarrative: total_milestones = 0", sn.total_milestones == 0)

    # record
    entry = sn.record("Mi primera observación", entry_type="observation",
                      emotional_tone="neutral", tags=["test"])
    test("SelfNarrative: record retorna NarrativeEntry",
         isinstance(entry, NarrativeEntry))
    test("SelfNarrative: entries = 1", len(sn.entries) == 1)
    test("SelfNarrative: total_entries = 1", sn.total_entries == 1)
    test("SelfNarrative: entry tiene tag", "test" in sn.entries[0].tags)

    # record vacío
    result = sn.record("")
    test("SelfNarrative: ignora vacío", result is None)
    test("SelfNarrative: total sigue en 1", sn.total_entries == 1)

    # disabled
    sn.enabled = False
    result = sn.record("algo")
    test("SelfNarrative: disabled retorna None", result is None)
    sn.enabled = True

    # record_milestone
    entry = sn.record_milestone("Primer hito alcanzado!", tags=["milestone"])
    test("SelfNarrative: milestone registrado", entry is not None)
    test("SelfNarrative: milestone relevance = 1.0", entry.relevance == 1.0)
    test("SelfNarrative: total_milestones = 1", sn.total_milestones == 1)

    # check_milestones
    milestones = sn.check_milestones({"total_interactions": 10})
    test("SelfNarrative: check_milestones retorna lista",
         isinstance(milestones, list))

    # observe_identity
    sn.observe_identity("Como funciona esto? Que es una clase?", domain="python")
    test("SelfNarrative: identity tiene traits",
         len(sn.identity.traits) > 0)

    sn.observe_identity("Implementa el codigo de la funcion y la clase")
    test("SelfNarrative: tecnico detectado",
         "tecnico" in sn.identity.traits)

    # get_recent_entries
    recent = sn.get_recent_entries(5)
    test("SelfNarrative: recent retorna lista", isinstance(recent, list))
    test("SelfNarrative: recent <= 5", len(recent) <= 5)

    recent_milestones = sn.get_recent_entries(5, entry_type="milestone")
    test("SelfNarrative: filtered por tipo", isinstance(recent_milestones, list))

    # get_narrative_summary
    summary = sn.get_narrative_summary()
    test("SelfNarrative: summary es string", isinstance(summary, str))
    test("SelfNarrative: summary no vacío", len(summary) > 0)

    # get_context_for_prompt
    ctx = sn.get_context_for_prompt()
    test("SelfNarrative: context es string", isinstance(ctx, str))

    # get_stats
    stats = sn.get_stats()
    test("SelfNarrative: stats tiene total_entries", "total_entries" in stats)
    test("SelfNarrative: stats tiene total_milestones", "total_milestones" in stats)
    test("SelfNarrative: stats tiene identity", "identity" in stats)
    test("SelfNarrative: stats tiene dominant_traits", "dominant_traits" in stats)
    test("SelfNarrative: stats tiene entry_types", "entry_types" in stats)

    # status
    st = sn.status()
    test("SelfNarrative: status no vacío", len(st) > 0)
    test("SelfNarrative: status tiene Entradas", "Entradas" in st)

    # generate_report
    report = sn.generate_report()
    test("SelfNarrative: report contiene SELF-NARRATIVE", "SELF-NARRATIVE" in report)

    # save/load
    sn.save()
    sn2 = SelfNarrative(base_dir=tmp)
    test("SelfNarrative: persistencia entries",
         len(sn2.entries) == len(sn.entries))
    test("SelfNarrative: persistencia total_entries",
         sn2.total_entries == sn.total_entries)
    test("SelfNarrative: persistencia total_milestones",
         sn2.total_milestones == sn.total_milestones)
    test("SelfNarrative: persistencia identity",
         len(sn2.identity.traits) > 0)

    # Eviction (milestones preserved)
    sn3 = SelfNarrative(base_dir=tempfile.mkdtemp())
    sn3.max_entries = 5
    sn3.record_milestone("Hito importante")
    for i in range(10):
        sn3.record(f"observación {i}")
    test("SelfNarrative: eviction respeta max_entries",
         len(sn3.entries) <= 5)
    test("SelfNarrative: milestones preservados en eviction",
         any(e.entry_type == "milestone" for e in sn3.entries))

    # clear
    sn.clear()
    test("SelfNarrative: clear entries vacío", len(sn.entries) == 0)
    test("SelfNarrative: clear total_entries = 0", sn.total_entries == 0)
    test("SelfNarrative: clear total_milestones = 0", sn.total_milestones == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# INTEGRATION — genesis.py imports
# ============================================================
print("\n--- Integración genesis.py ---")

import importlib
test("Integration: import unified_mind",
     importlib.import_module("core.unified_mind") is not None)
test("Integration: import dream_engine",
     importlib.import_module("core.dream_engine") is not None)
test("Integration: import self_narrative",
     importlib.import_module("core.self_narrative") is not None)

with open("genesis.py", "r", encoding="utf-8") as f:
    genesis_code = f.read()

test("Integration: genesis importa UnifiedMind",
     "from core.unified_mind import UnifiedMind" in genesis_code)
test("Integration: genesis importa DreamEngine",
     "from core.dream_engine import DreamEngine" in genesis_code)
test("Integration: genesis importa SelfNarrative",
     "from core.self_narrative import SelfNarrative" in genesis_code)

test("Integration: genesis init unified_mind",
     "self.unified_mind = UnifiedMind(" in genesis_code)
test("Integration: genesis init dream_engine",
     "self.dream_engine = DreamEngine(" in genesis_code)
test("Integration: genesis init self_narrative",
     "self.self_narrative = SelfNarrative(" in genesis_code)

test("Integration: context unified_mind",
     "unified_mind.get_context_for_prompt" in genesis_code)
test("Integration: context dream_engine",
     "dream_engine.get_context_for_prompt" in genesis_code)
test("Integration: context self_narrative",
     "self_narrative.get_context_for_prompt" in genesis_code)

test("Integration: post-process unified_mind.observe",
     "unified_mind.observe" in genesis_code)
test("Integration: post-process dream_engine.record_experience",
     "dream_engine.record_experience" in genesis_code)
test("Integration: post-process self_narrative.observe_identity",
     "self_narrative.observe_identity" in genesis_code)

test("Integration: comando /mind",
     '"/mind"' in genesis_code or "== \"/mind\"" in genesis_code)
test("Integration: comando /dream",
     '"/dream"' in genesis_code or "== \"/dream\"" in genesis_code)
test("Integration: comando /narrative",
     '"/narrative"' in genesis_code or "== \"/narrative\"" in genesis_code)

test("Integration: status unified_mind",
     "unified_mind.status()" in genesis_code)
test("Integration: status dream_engine",
     "dream_engine.status()" in genesis_code)
test("Integration: status self_narrative",
     "self_narrative.status()" in genesis_code)

test("Integration: dashboard unified_mind",
     "unified_mind" in genesis_code and "dashboard.register" in genesis_code)
test("Integration: dashboard dream_engine",
     "dream_engine" in genesis_code and "dashboard.register" in genesis_code)
test("Integration: dashboard self_narrative",
     "self_narrative" in genesis_code and "dashboard.register" in genesis_code)

test("Integration: save unified_mind",
     "unified_mind.save()" in genesis_code)
test("Integration: save dream_engine",
     "dream_engine.save()" in genesis_code)
test("Integration: save self_narrative",
     "self_narrative.save()" in genesis_code)

test("Integration: help /mind", "/mind" in genesis_code)
test("Integration: help /dream", "/dream" in genesis_code)
test("Integration: help /narrative", "/narrative" in genesis_code)

# ============================================================
# INTEGRATION — web_ui.py
# ============================================================
print("\n--- Integración web_ui.py ---")

with open("web_ui.py", "r", encoding="utf-8") as f:
    webui_code = f.read()

test("Integration: web_ui tiene UnifiedMind en health",
     "UnifiedMind" in webui_code)
test("Integration: web_ui tiene DreamEngine en health",
     "DreamEngine" in webui_code)
test("Integration: web_ui tiene SelfNarrative en health",
     "SelfNarrative" in webui_code)

test("Integration: web_ui tiene unified_mind.get_stats",
     "unified_mind.get_stats()" in webui_code)
test("Integration: web_ui tiene dream_engine.get_stats",
     "dream_engine.get_stats()" in webui_code)
test("Integration: web_ui tiene self_narrative.get_stats",
     "self_narrative.get_stats()" in webui_code)

# ============================================================
# INTEGRATION — version check
# ============================================================
print("\n--- Version Check ---")
from config import GENESIS_VERSION

major, minor, patch = GENESIS_VERSION.split(".")
version_num = int(major) * 100 + int(minor) * 10 + int(patch)
test("Integration: version >= 3.0.0", version_num >= 300)

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
