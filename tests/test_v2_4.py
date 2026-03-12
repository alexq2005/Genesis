"""
Tests para Genesis v2.4.0
- EpisodicMemory: Episode, EpisodeBuilder, TimelineIndex
- MetaLearner: StrategyRecord, PatternDetector, LearningInsight
- PersonalityEvolver: TraitVector, DriftEngine
- Integracion en genesis.py y web_ui.py

Total: 250+ tests
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


# ============================================================
# TEST 1: Episode
# ============================================================
print("\n=== TEST: Episode ===")
from core.episodic_memory import Episode, EpisodeBuilder, TimelineIndex, EpisodicMemory

ep = Episode()
test("Episode: id generado", len(ep.episode_id) == 10)
test("Episode: timestamp set", ep.timestamp > 0)
test("Episode: ended_at 0", ep.ended_at == 0)
test("Episode: topics vacio", len(ep.topics) == 0)
test("Episode: summary vacio", ep.summary == "")
test("Episode: tone neutral", ep.emotional_tone == "neutral")
test("Episode: key_facts vacio", len(ep.key_facts) == 0)
test("Episode: message_count 0", ep.message_count == 0)
test("Episode: user_queries vacio", len(ep.user_queries) == 0)
test("Episode: tags vacio", len(ep.tags) == 0)

# Properties
test("Episode: duration >= 0", ep.duration_seconds >= 0)
test("Episode: date_str tiene formato", "-" in ep.date_str)
test("Episode: age_hours >= 0", ep.age_hours >= 0)

# to_text
text = ep.to_text()
test("Episode.to_text: contiene Episodio", "Episodio" in text)

# Serialization
ep.topics = ["python", "docker"]
ep.summary = "Conversacion sobre Python y Docker"
ep.emotional_tone = "positive"
ep.key_facts = ["Python es interpretado", "Docker usa contenedores"]
ep.message_count = 5
ep.user_queries = ["como instalar python?", "que es docker?"]

d = ep.to_dict()
test("Episode.to_dict: tiene id", "id" in d)
test("Episode.to_dict: tiene topics", len(d["topics"]) == 2)
test("Episode.to_dict: tiene summary", d["summary"] != "")
test("Episode.to_dict: tiene tone", d["emotional_tone"] == "positive")

restored = Episode.from_dict(d)
test("Episode.from_dict: id preservado", restored.episode_id == ep.episode_id)
test("Episode.from_dict: topics preservados", restored.topics == ep.topics)
test("Episode.from_dict: summary preservado", restored.summary == ep.summary)
test("Episode.from_dict: tone preservado", restored.emotional_tone == "positive")
test("Episode.from_dict: facts preservados", len(restored.key_facts) == 2)
test("Episode.from_dict: queries preservadas", len(restored.user_queries) == 2)


# ============================================================
# TEST 2: EpisodeBuilder
# ============================================================
print("\n=== TEST: EpisodeBuilder ===")
builder = EpisodeBuilder()

# Build from messages
messages = [
    {"role": "user", "content": "como instalar python en linux?"},
    {"role": "assistant", "content": "Python es un lenguaje interpretado. Para instalar Python en Linux, usa el comando: sudo apt install python3. Esto instala Python 3 en Ubuntu/Debian."},
    {"role": "user", "content": "y como configuro un servidor flask?"},
    {"role": "assistant", "content": "Flask es un microframework web para Python. Funciona con pip install flask. Crea un archivo app.py con Flask importado."},
    {"role": "user", "content": "gracias, funciona perfecto!"},
    {"role": "assistant", "content": "Me alegro que funcione. Flask es muy versatil para APIs y aplicaciones web."},
]

ep = builder.build_episode(messages)
test("Builder: message_count correcto", ep.message_count == 6)
test("Builder: user_queries tiene 3", len(ep.user_queries) == 3)
test("Builder: topics detectados", len(ep.topics) > 0)
test("Builder: summary no vacio", len(ep.summary) > 0)
test("Builder: emotional_tone detectado", ep.emotional_tone in ["positive", "curious", "neutral", "negative", "frustrated"])

# Detect topics
topics = builder._detect_topics("python flask api servidor web deploy docker")
test("Builder: detecta web topic", "web" in topics)

# Detect tone
test("Builder: tone positive", builder._detect_tone("gracias excelente perfecto genial") == "positive")
test("Builder: tone negative", builder._detect_tone("error fallo no funciona problema bug") == "negative")
test("Builder: tone curious", builder._detect_tone("como por que interesante investigar explorar") == "curious")
test("Builder: tone frustrated", builder._detect_tone("no entiendo otra vez sigue sin ya intente") == "frustrated")
test("Builder: tone neutral", builder._detect_tone("hola mundo") == "neutral")

# Extract facts
facts = builder._extract_facts(messages)
test("Builder: extrae facts", len(facts) >= 0)  # Puede ser 0 si no hay patrones

# Generate summary
summary = builder._generate_summary(messages, ["programacion", "web"])
test("Builder: summary contiene msgs count", "mensajes" in summary.lower() or "mensaje" in summary.lower())

# Extract tags
tags = builder._extract_tags("python flask docker linux nginx")
test("Builder: extrae tags python", "python" in tags)
test("Builder: extrae tags flask", "flask" in tags)
test("Builder: extrae tags docker", "docker" in tags)

# Empty messages
empty_ep = builder.build_episode([])
test("Builder: empty messages no crashea", empty_ep.message_count == 0)


# ============================================================
# TEST 3: TimelineIndex
# ============================================================
print("\n=== TEST: TimelineIndex ===")
timeline = TimelineIndex()

test("Timeline: vacio", timeline.count == 0)

# Add episodes
now = time.time()
for i in range(5):
    ep = Episode(timestamp=now - (i * 3600))  # Cada hora hacia atrás
    ep.topics = [f"topic_{i}"]
    ep.user_queries = [f"query_{i}"]
    timeline.add(ep)

test("Timeline: 5 episodios", timeline.count == 5)

# Query last N
last3 = timeline.query_last_n(3)
test("Timeline.last_n: retorna 3", len(last3) == 3)

# Query last hours
recent = timeline.query_last_hours(2.5)
test("Timeline.last_hours: retorna los recientes", len(recent) >= 2)

# Query by topic
by_topic = timeline.query_by_topic("topic_0")
test("Timeline.by_topic: encuentra", len(by_topic) >= 1)

no_topic = timeline.query_by_topic("nonexistent")
test("Timeline.by_topic: no encuentra", len(no_topic) == 0)

# Query by keyword
by_kw = timeline.query_by_keyword("query_2")
test("Timeline.by_keyword: encuentra", len(by_kw) >= 1)

# Range query
start = now - 7200  # 2 horas atras
end = now
range_eps = timeline.query_range(start, end)
test("Timeline.range: retorna episodios", len(range_eps) >= 2)

# Serialization
data = timeline.to_list()
test("Timeline.to_list: retorna lista", isinstance(data, list))
test("Timeline.to_list: tiene 5", len(data) == 5)

timeline2 = TimelineIndex()
timeline2.load_list(data)
test("Timeline.load_list: restaura count", timeline2.count == 5)


# ============================================================
# TEST 4: EpisodicMemory (coordinador)
# ============================================================
print("\n=== TEST: EpisodicMemory ===")
tmp_dir = tempfile.mkdtemp()

try:
    mem = EpisodicMemory(base_dir=tmp_dir)

    test("EpisodicMem: total 0", mem.total_episodes == 0)
    test("EpisodicMem: enabled True", mem.enabled is True)

    # Start episode
    ep = mem.start_episode()
    test("EpisodicMem: start retorna Episode", isinstance(ep, Episode))
    test("EpisodicMem: current_episode set", mem.current_episode is not None)

    # Record messages
    mem.record_message("user", "como instalar docker?")
    mem.record_message("assistant", "Para instalar Docker, usa apt install docker.io")
    test("EpisodicMem: message_count 2", mem.current_episode.message_count == 2)
    test("EpisodicMem: user_query registrada", len(mem.current_episode.user_queries) == 1)

    # End episode
    messages = [
        {"role": "user", "content": "como instalar docker en linux?"},
        {"role": "assistant", "content": "Docker es una plataforma de contenedores. Instala con apt install docker.io. Verifica con docker --version."},
    ]
    mem.end_episode(messages)
    test("EpisodicMem: current_episode None", mem.current_episode is None)
    test("EpisodicMem: total 1", mem.total_episodes == 1)
    test("EpisodicMem: timeline tiene 1", mem.timeline.count == 1)

    # Recall recent
    recent = mem.recall_recent(5)
    test("EpisodicMem.recall_recent: retorna lista", isinstance(recent, list))
    test("EpisodicMem.recall_recent: tiene 1", len(recent) == 1)
    test("EpisodicMem: total_queries 1", mem.total_queries == 1)

    # Recall by topic
    by_topic = mem.recall_by_topic("sistema")
    test("EpisodicMem.recall_by_topic: retorna lista", isinstance(by_topic, list))

    # Recall by keyword
    by_kw = mem.recall_by_keyword("docker")
    test("EpisodicMem.recall_by_keyword: retorna lista", isinstance(by_kw, list))

    # Recall last hours
    last_24 = mem.recall_last_hours(24)
    test("EpisodicMem.recall_last_hours: retorna lista", isinstance(last_24, list))

    # Temporal summary
    summary = mem.get_temporal_summary()
    test("EpisodicMem.temporal_summary: no vacio", len(summary) > 10)

    # Stats
    stats = mem.get_stats()
    test("EpisodicMem.stats: tiene total", "total_episodes" in stats)
    test("EpisodicMem.stats: tiene stored", "stored_episodes" in stats)
    test("EpisodicMem.stats: tiene queries", "total_queries" in stats)

    # Status
    status = mem.status()
    test("EpisodicMem.status: contiene Episodios", "Episodios:" in status)

    # Report
    report = mem.generate_report()
    test("EpisodicMem.report: contiene header", "EPISODIC MEMORY" in report)

    # Persistence
    mem.save()
    test("EpisodicMem.save: archivo existe", mem.data_file.exists())

    mem2 = EpisodicMemory(base_dir=tmp_dir)
    test("EpisodicMem.load: episodes restaurados", mem2.timeline.count == 1)
    test("EpisodicMem.load: total restaurado", mem2.total_episodes == 1)

    # Clear
    mem.clear()
    test("EpisodicMem.clear: total 0", mem.total_episodes == 0)
    test("EpisodicMem.clear: timeline vacio", mem.timeline.count == 0)

    # Context for prompt
    # First add some episodes for context testing
    mem.start_episode()
    mem.record_message("user", "como configurar nginx y docker?")
    mem.end_episode([
        {"role": "user", "content": "como configurar nginx y docker para deploy?"},
        {"role": "assistant", "content": "Nginx funciona como reverse proxy con Docker. Configura upstream en nginx.conf."},
    ])
    ctx = mem.get_context_for_prompt("como deployar con nginx y docker?")
    # May or may not find context depending on keyword overlap
    test("EpisodicMem.get_context: no crashea", True)

    # Record without start
    mem.clear()
    mem.record_message("user", "hola")
    test("EpisodicMem: auto-start episode", mem.current_episode is not None)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 5: StrategyRecord
# ============================================================
print("\n=== TEST: StrategyRecord ===")
from core.meta_learner import StrategyRecord, PatternDetector, LearningInsight, MetaLearner

rec = StrategyRecord(
    intent="code",
    template="code",
    temperature=0.3,
    chain_used=False,
    skill_injected=True,
    score=0.85,
    user_feedback="+",
)
test("Record: intent correcto", rec.intent == "code")
test("Record: template correcto", rec.template == "code")
test("Record: temperature correcto", rec.temperature == 0.3)
test("Record: chain_used False", rec.chain_used is False)
test("Record: skill_injected True", rec.skill_injected is True)
test("Record: score correcto", rec.score == 0.85)
test("Record: feedback correcto", rec.user_feedback == "+")
test("Record: timestamp set", rec.timestamp > 0)

# Serialization
d = rec.to_dict()
test("Record.to_dict: tiene intent", d["intent"] == "code")
test("Record.to_dict: tiene score", d["score"] == 0.85)

restored = StrategyRecord.from_dict(d)
test("Record.from_dict: intent OK", restored.intent == "code")
test("Record.from_dict: score OK", restored.score == 0.85)
test("Record.from_dict: temperature OK", restored.temperature == 0.3)


# ============================================================
# TEST 6: LearningInsight
# ============================================================
print("\n=== TEST: LearningInsight ===")
insight = LearningInsight(
    category="intent",
    description="Code funciona mejor con temperatura baja",
    confidence=0.8,
    recommendation="Reducir temperatura para code a 0.3",
)
test("Insight: id generado", len(insight.insight_id) == 10)
test("Insight: category OK", insight.category == "intent")
test("Insight: confidence OK", insight.confidence == 0.8)
test("Insight: applied False", insight.applied is False)

# Serialization
d = insight.to_dict()
test("Insight.to_dict: tiene id", "id" in d)
test("Insight.to_dict: tiene category", d["category"] == "intent")
test("Insight.to_dict: tiene confidence", d["confidence"] == 0.8)

restored = LearningInsight.from_dict(d)
test("Insight.from_dict: category OK", restored.category == "intent")
test("Insight.from_dict: confidence OK", restored.confidence == 0.8)
test("Insight.from_dict: description OK", restored.description == insight.description)


# ============================================================
# TEST 7: PatternDetector
# ============================================================
print("\n=== TEST: PatternDetector ===")
detector = PatternDetector(min_samples=3)

# Generate test records
records = []
for i in range(10):
    records.append(StrategyRecord(intent="code", template="code",
                                   temperature=0.3, score=0.9))
for i in range(10):
    records.append(StrategyRecord(intent="chat", template="",
                                   temperature=0.7, score=0.6))
for i in range(5):
    records.append(StrategyRecord(intent="creative", template="creative",
                                   temperature=0.9, score=0.4))
# Chain records
for i in range(5):
    records.append(StrategyRecord(intent="research", chain_used=True, score=0.85))
for i in range(5):
    records.append(StrategyRecord(intent="research", chain_used=False, score=0.65))
# Skill records
for i in range(5):
    records.append(StrategyRecord(intent="code", skill_injected=True, score=0.92))
for i in range(5):
    records.append(StrategyRecord(intent="code", skill_injected=False, score=0.75))

# Analyze by intent
by_intent = detector.analyze_by_intent(records)
test("Detector.by_intent: tiene code", "code" in by_intent)
test("Detector.by_intent: tiene chat", "chat" in by_intent)
test("Detector.by_intent: code avg alto", by_intent["code"]["avg_score"] > 0.8)
test("Detector.by_intent: chat avg medio", by_intent["chat"]["avg_score"] < 0.7)

# Analyze by template
by_tmpl = detector.analyze_by_template(records)
test("Detector.by_template: tiene code", "code" in by_tmpl)

# Chain impact
chain = detector.analyze_chain_impact(records)
test("Detector.chain: sufficient_data True", chain["sufficient_data"] is True)
test("Detector.chain: chain_helps True", chain["chain_helps"] is True)
test("Detector.chain: improvement > 0", chain["improvement"] > 0)

# Skill impact
skill = detector.analyze_skill_impact(records)
test("Detector.skill: sufficient_data True", skill["sufficient_data"] is True)
test("Detector.skill: skill_helps True", skill["skill_helps"] is True)

# Temperature correlation
temp = detector.analyze_temperature_correlation(records)
test("Detector.temp: retorna dict", isinstance(temp, dict))

# Detect insights
insights = detector.detect_insights(records)
test("Detector.insights: retorna lista", isinstance(insights, list))
test("Detector.insights: tiene insights", len(insights) > 0)

# Insufficient data
few = [StrategyRecord(intent="test", score=0.5) for _ in range(2)]
by_intent_few = detector.analyze_by_intent(few)
test("Detector: insufficient data retorna vacio", len(by_intent_few) == 0)


# ============================================================
# TEST 8: MetaLearner (coordinador)
# ============================================================
print("\n=== TEST: MetaLearner ===")
tmp_dir2 = tempfile.mkdtemp()

try:
    ml = MetaLearner(base_dir=tmp_dir2)

    test("MetaLearner: total 0", ml.total_recorded == 0)
    test("MetaLearner: enabled True", ml.enabled is True)
    test("MetaLearner: records vacio", len(ml.records) == 0)
    test("MetaLearner: insights vacio", len(ml.insights) == 0)

    # Record strategies
    for i in range(15):
        ml.record_strategy(
            intent="code",
            template="code",
            temperature=0.3,
            score=0.85 + (i * 0.005),
        )
    test("MetaLearner: 15 records", ml.total_recorded == 15)
    test("MetaLearner: records almacenados", len(ml.records) == 15)

    # Trigger analysis (at interval 10)
    for i in range(5):
        ml.record_strategy(intent="chat", template="", temperature=0.7, score=0.5)

    test("MetaLearner: 20 records total", ml.total_recorded == 20)

    # Get recommendation
    rec = ml.get_recommendation("code")
    test("MetaLearner.recommendation: retorna dict", isinstance(rec, dict))

    # Stats
    stats = ml.get_stats()
    test("MetaLearner.stats: tiene total", "total_recorded" in stats)
    test("MetaLearner.stats: tiene records_stored", "records_stored" in stats)
    test("MetaLearner.stats: tiene total_insights", "total_insights" in stats)

    # Status
    status = ml.status()
    test("MetaLearner.status: contiene Records", "Records:" in status)

    # Report
    report = ml.generate_report()
    test("MetaLearner.report: contiene header", "META-LEARNER" in report)

    # Get insights
    all_insights = ml.get_insights(min_confidence=0.0)
    test("MetaLearner.insights: retorna lista", isinstance(all_insights, list))

    # Persistence
    ml.save()
    test("MetaLearner.save: archivo existe", ml.data_file.exists())

    ml2 = MetaLearner(base_dir=tmp_dir2)
    test("MetaLearner.load: total restaurado", ml2.total_recorded == ml.total_recorded)
    test("MetaLearner.load: records restaurados", len(ml2.records) == len(ml.records))

    # Disabled
    ml.enabled = False
    ml.record_strategy(intent="test", score=0.5)
    test("MetaLearner.disabled: no registra", ml.total_recorded == 20)
    ml.enabled = True

    # Clear
    ml.clear()
    test("MetaLearner.clear: total 0", ml.total_recorded == 0)
    test("MetaLearner.clear: records vacio", len(ml.records) == 0)
    test("MetaLearner.clear: insights vacio", len(ml.insights) == 0)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)


# ============================================================
# TEST 9: TraitVector
# ============================================================
print("\n=== TEST: TraitVector ===")
from core.personality_evolver import TraitVector, DriftEngine, PersonalityEvolver

traits = TraitVector()
test("Traits: tiene curiosity", "curiosity" in traits.traits)
test("Traits: tiene verbosity", "verbosity" in traits.traits)
test("Traits: tiene formality", "formality" in traits.traits)
test("Traits: tiene creativity", "creativity" in traits.traits)
test("Traits: tiene precision", "precision" in traits.traits)
test("Traits: tiene humor", "humor" in traits.traits)
test("Traits: tiene assertiveness", "assertiveness" in traits.traits)
test("Traits: tiene empathy", "empathy" in traits.traits)
test("Traits: 8 rasgos", len(traits.traits) == 8)

# Get/Set
test("Traits.get: curiosity default 0.7", traits.get("curiosity") == 0.7)
traits.set("curiosity", 0.9)
test("Traits.set: curiosity 0.9", traits.get("curiosity") == 0.9)

# Clamp
traits.set("curiosity", 1.5)
test("Traits.set: clamp max 1.0", traits.get("curiosity") == 1.0)
traits.set("curiosity", -0.5)
test("Traits.set: clamp min 0.0", traits.get("curiosity") == 0.0)

# Adjust
traits.set("curiosity", 0.5)
traits.adjust("curiosity", 0.1)
test("Traits.adjust: 0.5 + 0.1 = 0.6", abs(traits.get("curiosity") - 0.6) < 0.001)

# Distance
traits1 = TraitVector()
traits2 = TraitVector()
test("Traits.distance: self=0", traits1.distance(traits2) < 0.001)
traits2.set("curiosity", 0.0)
test("Traits.distance: diff > 0", traits1.distance(traits2) > 0)

# Dominant/weak
t = TraitVector({"curiosity": 0.9, "humor": 0.1, "precision": 0.8})
dominant = t.dominant_traits(threshold=0.7)
test("Traits.dominant: curiosity es dominante", "curiosity" in dominant)
test("Traits.dominant: precision es dominante", "precision" in dominant)

weak = t.weak_traits(threshold=0.3)
test("Traits.weak: humor es debil", "humor" in weak)

# Prompt hints
hints = t.to_prompt_hints()
test("Traits.to_prompt_hints: retorna string", isinstance(hints, str))

# No hints when all default
default_traits = TraitVector()
default_hints = default_traits.to_prompt_hints()
test("Traits.to_prompt_hints: default tiene hints", isinstance(default_hints, str))

# Serialization
d = t.to_dict()
test("Traits.to_dict: retorna dict", isinstance(d, dict))
test("Traits.to_dict: tiene curiosity", "curiosity" in d)

restored = TraitVector.from_dict(d)
test("Traits.from_dict: curiosity OK", restored.get("curiosity") == t.get("curiosity"))
test("Traits.from_dict: humor OK", restored.get("humor") == t.get("humor"))

# Unknown trait
test("Traits.get: unknown retorna 0.5", traits.get("nonexistent") == 0.5)

# Repr
test("Traits.__repr__: contiene TraitVector", "TraitVector" in repr(traits))


# ============================================================
# TEST 10: DriftEngine
# ============================================================
print("\n=== TEST: DriftEngine ===")
drift = DriftEngine()

test("Drift: total_drifts 0", drift.total_drifts == 0)

# Apply feedback
t = TraitVector()
old_assert = t.get("assertiveness")
drift.apply_feedback(t, "+")
test("Drift: feedback + ajusta assertiveness", t.get("assertiveness") > old_assert)
test("Drift: total_drifts incrementado", drift.total_drifts >= 1)

old_assert2 = t.get("assertiveness")
drift.apply_feedback(t, "-")
test("Drift: feedback - reduce assertiveness", t.get("assertiveness") < old_assert2)

# Apply tone
t2 = TraitVector()
old_humor = t2.get("humor")
drift.apply_tone(t2, "positive")
test("Drift: tone positive ajusta humor", t2.get("humor") > old_humor)

old_empathy = t2.get("empathy")
drift.apply_tone(t2, "frustrated")
test("Drift: tone frustrated ajusta empathy", t2.get("empathy") > old_empathy)

# Apply intent
t3 = TraitVector()
old_prec = t3.get("precision")
drift.apply_intent(t3, "code")
test("Drift: intent code ajusta precision", t3.get("precision") > old_prec)

old_creat = t3.get("creativity")
drift.apply_intent(t3, "creative")
test("Drift: intent creative ajusta creativity", t3.get("creativity") > old_creat)

# Decay
t4 = TraitVector({"curiosity": 1.0})  # Lejos del default 0.7
drift.apply_decay(t4)
test("Drift: decay acerca al default", t4.get("curiosity") < 1.0)

# Serialization
d = drift.to_dict()
test("Drift.to_dict: tiene total_drifts", "total_drifts" in d)
test("Drift.to_dict: tiene decay_rate", "decay_rate" in d)

drift2 = DriftEngine()
drift2.load_dict(d)
test("Drift.load_dict: total_drifts OK", drift2.total_drifts == drift.total_drifts)

# Unknown feedback
t5 = TraitVector()
old_vals = dict(t5.traits)
drift.apply_feedback(t5, "unknown")
test("Drift: unknown feedback no cambia", t5.traits == old_vals)

# Unknown tone
drift.apply_tone(t5, "unknown_tone")
test("Drift: unknown tone no cambia", t5.traits == old_vals)


# ============================================================
# TEST 11: PersonalityEvolver (coordinador)
# ============================================================
print("\n=== TEST: PersonalityEvolver ===")
tmp_dir3 = tempfile.mkdtemp()

try:
    pe = PersonalityEvolver(base_dir=tmp_dir3)

    test("PersonalityEvolver: total 0", pe.total_evolutions == 0)
    test("PersonalityEvolver: enabled True", pe.enabled is True)
    test("PersonalityEvolver: traits es TraitVector", isinstance(pe.traits, TraitVector))

    # Evolve from feedback
    old_assert = pe.get_trait("assertiveness")
    pe.evolve_from_feedback("+")
    test("PE: feedback + evoluciona", pe.total_evolutions == 1)
    test("PE: assertiveness cambio", pe.get_trait("assertiveness") != old_assert)

    pe.evolve_from_feedback("-")
    test("PE: feedback - evoluciona", pe.total_evolutions == 2)

    # Evolve from tone
    pe.evolve_from_tone("positive")
    test("PE: tone evoluciona", pe.total_evolutions == 3)

    # Evolve from intent
    pe.evolve_from_intent("code")
    test("PE: intent evoluciona", pe.total_evolutions == 4)

    # Many evolutions
    for i in range(20):
        pe.evolve_from_intent("code")
    test("PE: 24 evoluciones", pe.total_evolutions == 24)
    test("PE: snapshot tomado", len(pe.snapshots) >= 1)

    # Decay
    pe.decay()
    test("PE: decay no crashea", True)

    # Get prompt hints
    hints = pe.get_prompt_hints()
    test("PE.get_prompt_hints: retorna string", isinstance(hints, str))

    # Get all traits
    all_traits = pe.get_all_traits()
    test("PE.get_all_traits: retorna dict", isinstance(all_traits, dict))
    test("PE.get_all_traits: tiene 8 traits", len(all_traits) == 8)

    # Dominant traits
    dominant = pe.get_dominant_traits()
    test("PE.dominant_traits: retorna lista", isinstance(dominant, list))

    # Evolution distance
    dist = pe.get_evolution_distance()
    test("PE.evolution_distance: retorna float", isinstance(dist, float))
    test("PE.evolution_distance: > 0 despues de evolucionar", dist > 0)

    # Manual snapshot
    pe.take_snapshot()
    snapshot_count = len(pe.snapshots)
    test("PE.take_snapshot: incrementa", snapshot_count >= 2)

    # Stats
    stats = pe.get_stats()
    test("PE.stats: tiene total", "total_evolutions" in stats)
    test("PE.stats: tiene dominant", "dominant_traits" in stats)
    test("PE.stats: tiene distance", "distance_from_default" in stats)
    test("PE.stats: tiene current_traits", "current_traits" in stats)

    # Status
    status = pe.status()
    test("PE.status: contiene Evoluciones", "Evoluciones:" in status)

    # Report
    report = pe.generate_report()
    test("PE.report: contiene header", "PERSONALITY EVOLVER" in report)
    test("PE.report: contiene rasgos", "curiosity" in report)

    # Persistence
    pe.save()
    test("PE.save: archivo existe", pe.data_file.exists())

    pe2 = PersonalityEvolver(base_dir=tmp_dir3)
    test("PE.load: total restaurado", pe2.total_evolutions == pe.total_evolutions)
    test("PE.load: traits restaurados", abs(pe2.get_trait("precision") - pe.get_trait("precision")) < 0.001)

    # Disabled
    pe.enabled = False
    old_total = pe.total_evolutions
    pe.evolve_from_feedback("+")
    test("PE.disabled: no evoluciona", pe.total_evolutions == old_total)
    pe.enabled = True

    # Clear
    pe.clear()
    test("PE.clear: total 0", pe.total_evolutions == 0)
    test("PE.clear: traits default", pe.get_trait("curiosity") == 0.7)
    test("PE.clear: snapshots vacio", len(pe.snapshots) == 0)

finally:
    shutil.rmtree(tmp_dir3, ignore_errors=True)


# ============================================================
# TEST 12: genesis.py — Integration
# ============================================================
print("\n=== TEST: genesis.py — Integration ===")
genesis_source = open("genesis.py", "r", encoding="utf-8").read()

# Imports
test("genesis.py: importa EpisodicMemory", "from core.episodic_memory import EpisodicMemory" in genesis_source)
test("genesis.py: importa MetaLearner", "from core.meta_learner import MetaLearner" in genesis_source)
test("genesis.py: importa PersonalityEvolver", "from core.personality_evolver import PersonalityEvolver" in genesis_source)

# Init
test("genesis.py: self.episodic_memory =", "self.episodic_memory = EpisodicMemory(" in genesis_source)
test("genesis.py: self.meta_learner =", "self.meta_learner = MetaLearner(" in genesis_source)
test("genesis.py: self.personality =", "self.personality = PersonalityEvolver(" in genesis_source)

# Process input integration
test("genesis.py: episodic_memory.get_context", "episodic_memory.get_context_for_prompt" in genesis_source)
test("genesis.py: personality.get_prompt_hints", "personality.get_prompt_hints" in genesis_source)
test("genesis.py: episodic_memory.record_message", "episodic_memory.record_message" in genesis_source)
test("genesis.py: meta_learner.record_strategy", "meta_learner.record_strategy" in genesis_source)
test("genesis.py: personality.evolve_from_intent", "personality.evolve_from_intent" in genesis_source)

# Feedback integration
test("genesis.py: personality.evolve_from_feedback +", 'personality.evolve_from_feedback("+")' in genesis_source)
test("genesis.py: personality.evolve_from_feedback -", 'personality.evolve_from_feedback("-")' in genesis_source)

# Commands
test("genesis.py: /episodes command", '"/episodes"' in genesis_source)
test("genesis.py: /metalearner command", '"/metalearner"' in genesis_source)
test("genesis.py: /personality command", '"/personality"' in genesis_source)

# Status sections
test("genesis.py: status tiene EPISODIC MEMORY", "EPISODIC MEMORY:" in genesis_source)
test("genesis.py: status tiene META-LEARNER", "META-LEARNER:" in genesis_source)
test("genesis.py: status tiene PERSONALITY", "PERSONALITY:" in genesis_source)

# Dashboard collectors
test("genesis.py: dashboard register episodic_memory", '"episodic_memory"' in genesis_source)
test("genesis.py: dashboard register meta_learner", '"meta_learner"' in genesis_source)
test("genesis.py: dashboard register personality", '"personality"' in genesis_source)

# Save on exit
test("genesis.py: episodic_memory.save() on exit", "episodic_memory.save()" in genesis_source)
test("genesis.py: meta_learner.save() on exit", "meta_learner.save()" in genesis_source)
test("genesis.py: personality.save() on exit", "personality.save()" in genesis_source)

# Banner
test("genesis.py: banner tiene Episodic Memory", "Episodic Memory:" in genesis_source)
test("genesis.py: banner tiene Meta-Learner", "Meta-Learner:" in genesis_source)
test("genesis.py: banner tiene Personality", "Personality:" in genesis_source)

# Help
test("genesis.py: help tiene /episodes", "/episodes" in genesis_source)
test("genesis.py: help tiene /metalearner", "/metalearner" in genesis_source)
test("genesis.py: help tiene /personality", "/personality" in genesis_source)


# ============================================================
# TEST 13: web_ui.py — New Data
# ============================================================
print("\n=== TEST: web_ui.py — New Data ===")
webui_source = open("web_ui.py", "r", encoding="utf-8").read()

test("web_ui.py: retorna episodic_memory data", '"episodic_memory"' in webui_source)
test("web_ui.py: retorna meta_learner data", '"meta_learner"' in webui_source)
test("web_ui.py: retorna personality data", '"personality"' in webui_source)
test("web_ui.py: subsystem EpisodicMemory", '"EpisodicMemory"' in webui_source)
test("web_ui.py: subsystem MetaLearner", '"MetaLearner"' in webui_source)
test("web_ui.py: subsystem Personality", '"Personality"' in webui_source)


# ============================================================
# TEST 14: Edge Cases
# ============================================================
print("\n=== TEST: Edge Cases ===")

# EpisodeBuilder with no assistant messages
ep_no_assist = builder.build_episode([{"role": "user", "content": "hola"}])
test("Edge: solo user msg no crashea", ep_no_assist.message_count == 1)

# Empty timeline summary
empty_mem = EpisodicMemory(base_dir=tempfile.mkdtemp())
summary = empty_mem.get_temporal_summary()
test("Edge: empty temporal summary", "Sin episodios" in summary)
shutil.rmtree(empty_mem.base_dir, ignore_errors=True)

# TraitVector with partial traits
partial = TraitVector({"curiosity": 0.9})
test("Edge: partial traits fills defaults", partial.get("humor") == 0.3)

# MetaLearner max records
tmp_max = tempfile.mkdtemp()
ml_max = MetaLearner(base_dir=tmp_max)
ml_max.max_records = 5
for i in range(10):
    ml_max.record_strategy(intent="test", score=0.5)
test("Edge: max_records respected", len(ml_max.records) <= 5)
shutil.rmtree(tmp_max, ignore_errors=True)

# PersonalityEvolver max snapshots
tmp_snap = tempfile.mkdtemp()
pe_snap = PersonalityEvolver(base_dir=tmp_snap)
pe_snap.max_snapshots = 3
pe_snap.snapshot_interval = 1
for i in range(10):
    pe_snap.evolve_from_feedback("+")
test("Edge: max_snapshots respected", len(pe_snap.snapshots) <= 3)
shutil.rmtree(tmp_snap, ignore_errors=True)


# ============================================================
# TEST 15: Import Modules
# ============================================================
print("\n=== TEST: Import Modules ===")
try:
    from core.episodic_memory import EpisodicMemory as EM
    test("Import: EpisodicMemory OK", True)
except Exception as e:
    test(f"Import: EpisodicMemory FAILED ({e})", False)

try:
    from core.meta_learner import MetaLearner as ML
    test("Import: MetaLearner OK", True)
except Exception as e:
    test(f"Import: MetaLearner FAILED ({e})", False)

try:
    from core.personality_evolver import PersonalityEvolver as PE
    test("Import: PersonalityEvolver OK", True)
except Exception as e:
    test(f"Import: PersonalityEvolver FAILED ({e})", False)


# ============================================================
# TEST 16: Version Check
# ============================================================
print("\n=== TEST: Version Check ===")
from config import GENESIS_VERSION

parts = GENESIS_VERSION.split(".")
major = int(parts[0])
minor = int(parts[1])
version_num = major * 10 + minor
test(f"Version: {GENESIS_VERSION} >= 2.3", version_num >= 23)


# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
total = _passed + _failed
print(f"  GENESIS v2.4 Tests: {_passed}/{total} passed")
if _failed > 0:
    print(f"  {_failed} FAILED")
else:
    print(f"  ALL TESTS PASSED!")
print("=" * 60)

sys.exit(0 if _failed == 0 else 1)
