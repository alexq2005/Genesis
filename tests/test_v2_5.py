"""
Tests para Genesis v2.5.0
- GoalManager: Goal, GoalTracker, GoalSuggester
- ReflectionEngine: ReflectionEntry, SelfAnalyzer
- ContextRouter: ContextSource, ContextBudget
- Integracion en genesis.py y web_ui.py

Total: 260+ tests
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
    else:
        _failed += 1
        print(f"  FAIL: {name}")


def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


# ============================================================
# GOAL MANAGER TESTS
# ============================================================

section("Goal — Estructura basica")

from core.goal_manager import Goal, GoalTracker, GoalSuggester, GoalManager

g1 = Goal(title="Aprender Python", description="Dominar Python 3.11", priority=8)
test("Goal: title correcto", g1.title == "Aprender Python")
test("Goal: description correcta", g1.description == "Dominar Python 3.11")
test("Goal: priority correcta", g1.priority == 8)
test("Goal: status inicial active", g1.status == "active")
test("Goal: progress inicial 0", g1.progress == 0.0)
test("Goal: is_active True", g1.is_active)
test("Goal: id generado", len(g1.goal_id) > 0)
test("Goal: created_at set", g1.created_at > 0)
test("Goal: age_hours >= 0", g1.age_hours >= 0)

section("Goal — Priority clamping")

g_low = Goal(priority=0)
test("Goal: priority min clamp", g_low.priority == 1)
g_high = Goal(priority=15)
test("Goal: priority max clamp", g_high.priority == 10)
g_normal = Goal(priority=5)
test("Goal: priority normal", g_normal.priority == 5)

section("Goal — update_progress")

g2 = Goal(title="Test progress", priority=5)
g2.update_progress(0.5, "Medio camino")
test("Goal: progress actualizado", g2.progress == 0.5)
test("Goal: note agregada", len(g2.notes) == 1)
test("Goal: note text correcto", g2.notes[0]["text"] == "Medio camino")
test("Goal: updated_at actualizado", g2.updated_at > g2.created_at - 1)

# Progress clamping
g2.update_progress(1.5)
test("Goal: progress clamp max", g2.progress == 1.0)
test("Goal: auto-complete at 1.0", g2.status == "completed")
test("Goal: completed_at set", g2.completed_at > 0)

g3 = Goal(title="Progress neg")
g3.update_progress(-0.5)
test("Goal: progress clamp min", g3.progress == 0.0)

section("Goal — complete/abandon/pause/resume")

g4 = Goal(title="Completar")
g4.complete("Terminado!")
test("Goal: complete status", g4.status == "completed")
test("Goal: complete progress 1.0", g4.progress == 1.0)
test("Goal: complete note", len(g4.notes) == 1)

g5 = Goal(title="Abandonar")
g5.abandon("No es viable")
test("Goal: abandon status", g5.status == "abandoned")
test("Goal: abandon note", "Abandonado:" in g5.notes[0]["text"])

g6 = Goal(title="Pausar")
g6.pause()
test("Goal: pause status", g6.status == "paused")
test("Goal: paused is not active", not g6.is_active)
g6.resume()
test("Goal: resume status", g6.status == "active")
test("Goal: resumed is_active", g6.is_active)

section("Goal — to_text / to_dict / from_dict")

g7 = Goal(title="Test serial", priority=7)
g7.tags = ["python", "test"]
g7.update_progress(0.3)
text = g7.to_text()
test("Goal: to_text contiene titulo", "Test serial" in text)
test("Goal: to_text contiene P7", "P7" in text)

d = g7.to_dict()
test("Goal: to_dict tiene id", "id" in d)
test("Goal: to_dict tiene title", d["title"] == "Test serial")
test("Goal: to_dict tiene priority", d["priority"] == 7)
test("Goal: to_dict tiene tags", d["tags"] == ["python", "test"])

g7_restored = Goal.from_dict(d)
test("Goal: from_dict title", g7_restored.title == "Test serial")
test("Goal: from_dict priority", g7_restored.priority == 7)
test("Goal: from_dict progress", abs(g7_restored.progress - 0.3) < 0.01)
test("Goal: from_dict tags", g7_restored.tags == ["python", "test"])

section("Goal — is_stale")

g_stale = Goal(title="Stale test")
g_stale.updated_at = time.time() - (50 * 3600)  # 50 horas sin actualizar
test("Goal: is_stale True after 50h", g_stale.is_stale)

g_fresh = Goal(title="Fresh test")
test("Goal: is_stale False when fresh", not g_fresh.is_stale)

section("Goal — Notes limit")

g_notes = Goal(title="Notes limit")
for i in range(25):
    g_notes.update_progress(min(0.9, i * 0.04), f"Note {i}")
test("Goal: notes capped at 20", len(g_notes.notes) <= 20)


# ============================================================
# GOAL TRACKER TESTS
# ============================================================

section("GoalTracker — Prioritize")

tracker = GoalTracker()
goals = [
    Goal(title="Low", priority=3),
    Goal(title="High", priority=9),
    Goal(title="Mid", priority=5),
]
prioritized = tracker.prioritize(goals)
test("GoalTracker: prioritize order", prioritized[0].title == "High")
test("GoalTracker: prioritize order 2", prioritized[1].title == "Mid")
test("GoalTracker: prioritize order 3", prioritized[2].title == "Low")

section("GoalTracker — Focus goal")

focus = tracker.get_focus_goal(goals)
test("GoalTracker: focus is highest priority", focus.title == "High")

empty_focus = tracker.get_focus_goal([])
test("GoalTracker: focus on empty is None", empty_focus is None)

section("GoalTracker — check_stale")

stale_goals = [
    Goal(title="Stale"),
    Goal(title="Fresh"),
]
stale_goals[0].updated_at = time.time() - (50 * 3600)
stale_results = tracker.check_stale(stale_goals)
test("GoalTracker: check_stale finds 1", len(stale_results) == 1)
test("GoalTracker: check_stale correct", stale_results[0].title == "Stale")

section("GoalTracker — auto_progress_from_keywords")

g_auto = Goal(title="Aprender Python avanzado")
g_auto.tags = ["programacion"]
delta = tracker.auto_progress_from_keywords(g_auto, "estuve programando en python avanzado hoy con funciones")
test("GoalTracker: auto_progress > 0 for matching text", delta > 0)

delta_empty = tracker.auto_progress_from_keywords(g_auto, "")
test("GoalTracker: auto_progress 0 for empty", delta_empty == 0)

delta_unrelated = tracker.auto_progress_from_keywords(g_auto, "el clima está bonito hoy")
test("GoalTracker: auto_progress 0 for unrelated", delta_unrelated == 0)

# Completed goal should not progress
g_done = Goal(title="Done")
g_done.complete()
delta_done = tracker.auto_progress_from_keywords(g_done, "Done es relevante")
test("GoalTracker: no progress on completed", delta_done == 0)


# ============================================================
# GOAL SUGGESTER TESTS
# ============================================================

section("GoalSuggester — from meta-learner insights")

from core.meta_learner import LearningInsight

suggester = GoalSuggester()

ins_bad = LearningInsight(
    category="intent",
    description="Bajo rendimiento en 'code' (avg: 0.35)",
    confidence=0.7,
    recommendation="Ajustar estrategia",
)
ins_good = LearningInsight(
    category="intent",
    description="Excelente rendimiento en 'chat' (avg: 0.9)",
    confidence=0.8,
    recommendation="Mantener",
)
ins_low_conf = LearningInsight(
    category="intent",
    description="Bajo rendimiento en 'xyz'",
    confidence=0.2,  # Baja confianza
)

suggestions = suggester.suggest_from_meta_learner([ins_bad, ins_good, ins_low_conf])
test("GoalSuggester: suggestions generated", len(suggestions) >= 1)
test("GoalSuggester: low confidence filtered", len(suggestions) == 2)  # ins_low_conf filtered
titles = [s.title for s in suggestions]
test("GoalSuggester: improvement suggestion", any("code" in t.lower() for t in titles))
test("GoalSuggester: consistency suggestion", any("chat" in t.lower() for t in titles))
test("GoalSuggester: source is suggested", all(s.source == "suggested" for s in suggestions))

section("GoalSuggester — from topics")

topics = {"python": 10, "javascript": 7, "sql": 2, "rust": 1}
topic_suggestions = suggester.suggest_from_topics(topics)
test("GoalSuggester: topic suggestions generated", len(topic_suggestions) >= 1)
# Solo python y javascript tienen count >= 5
test("GoalSuggester: topics filter by count", len(topic_suggestions) == 2)

section("GoalSuggester — from gaps")

gaps = ["machine learning", "docker"]
gap_suggestions = suggester.suggest_from_gaps(gaps)
test("GoalSuggester: gap suggestions generated", len(gap_suggestions) == 2)
test("GoalSuggester: gap titles correct", any("machine learning" in s.title.lower() for s in gap_suggestions))


# ============================================================
# GOAL MANAGER TESTS
# ============================================================

section("GoalManager — Coordinator")

tmpdir = tempfile.mkdtemp()
try:
    gm = GoalManager(base_dir=os.path.join(tmpdir, "goals"))
    test("GoalManager: creado", gm is not None)
    test("GoalManager: no goals initially", len(gm.goals) == 0)
    test("GoalManager: enabled", gm.enabled)

    # Crear metas
    goal1 = gm.create_goal("Dominar Python", priority=8, tags=["python"])
    test("GoalManager: create goal", goal1 is not None)
    test("GoalManager: total_created", gm.total_created == 1)

    goal2 = gm.create_goal("Aprender Docker", priority=6, tags=["docker"])
    test("GoalManager: second goal", gm.total_created == 2)

    # Duplicate detection
    dup = gm.create_goal("Dominar Python avanzado", priority=9)
    test("GoalManager: duplicate returns existing", dup.goal_id == goal1.goal_id)
    test("GoalManager: total still 2 after dup", gm.total_created == 2)

    # Active goals
    active = gm.get_active_goals()
    test("GoalManager: 2 active goals", len(active) == 2)
    test("GoalManager: priority order", active[0].priority >= active[1].priority)

    # Update progress
    ok = gm.update_progress(goal1.goal_id, 0.5, "Half way")
    test("GoalManager: update_progress True", ok)
    test("GoalManager: progress updated", goal1.progress == 0.5)

    # Complete
    ok = gm.complete_goal(goal2.goal_id, "Done!")
    test("GoalManager: complete True", ok)
    test("GoalManager: total_completed 1", gm.total_completed == 1)
    test("GoalManager: active now 1", len(gm.get_active_goals()) == 1)

    # Abandon
    goal3 = gm.create_goal("Abandonable", priority=3)
    ok = gm.abandon_goal(goal3.goal_id, "Not viable")
    test("GoalManager: abandon True", ok)
    test("GoalManager: total_abandoned 1", gm.total_abandoned == 1)

    # Focus goal
    focus = gm.get_focus_goal()
    test("GoalManager: focus is goal1", focus.goal_id == goal1.goal_id)

    # Auto track
    gm.auto_track("estuve programando en python avanzado hoy", "Muy bien con python")
    test("GoalManager: auto_track updated progress", goal1.progress > 0.5)

    # Suggest goals
    suggestions = gm.suggest_goals(
        insights=[ins_bad],
        topic_counts={"python": 10},
        negative_topics=["docker"],
    )
    test("GoalManager: suggest_goals works", len(suggestions) >= 1)

    # Context for prompt
    ctx = gm.get_context_for_prompt(max_chars=400)
    test("GoalManager: context not empty", len(ctx) > 0)
    test("GoalManager: context has METAS", "[METAS ACTIVAS]" in ctx)

    # Stats
    stats = gm.get_stats()
    test("GoalManager: stats has total_created", "total_created" in stats)
    test("GoalManager: stats has active_goals", "active_goals" in stats)

    # Status
    status = gm.status()
    test("GoalManager: status not empty", len(status) > 0)

    # Report
    report = gm.generate_report()
    test("GoalManager: report has GOAL MANAGER", "GOAL MANAGER" in report)

    # Persistence
    gm.save()
    gm2 = GoalManager(base_dir=os.path.join(tmpdir, "goals"))
    test("GoalManager: persistence total_created", gm2.total_created == gm.total_created)
    test("GoalManager: persistence goals count", len(gm2.goals) == len(gm.goals))
    test("GoalManager: persistence total_completed", gm2.total_completed == gm.total_completed)

    # Clear
    gm.clear()
    test("GoalManager: clear goals", len(gm.goals) == 0)
    test("GoalManager: clear total_created", gm.total_created == 0)

    # Disabled
    gm.enabled = False
    result = gm.create_goal("Should not create")
    test("GoalManager: disabled returns None", result is None)
    gm.enabled = True

    # _find_goal non-existent
    test("GoalManager: find nonexistent returns None", gm._find_goal("xyz") is None)

finally:
    shutil.rmtree(tmpdir)


# ============================================================
# REFLECTION ENGINE TESTS
# ============================================================

section("ReflectionEntry — Estructura basica")

from core.reflection_engine import ReflectionEntry, SelfAnalyzer, ReflectionEngine

entry = ReflectionEntry()
test("ReflectionEntry: id generado", len(entry.reflection_id) > 0)
test("ReflectionEntry: timestamp set", entry.timestamp > 0)
test("ReflectionEntry: observations empty", entry.observations == [])
test("ReflectionEntry: strengths empty", entry.strengths == [])
test("ReflectionEntry: blind_spots empty", entry.blind_spots == [])
test("ReflectionEntry: improvement_plan empty", entry.improvement_plan == [])
test("ReflectionEntry: confidence 0", entry.confidence == 0.0)
test("ReflectionEntry: age_hours >= 0", entry.age_hours >= 0)

section("ReflectionEntry — to_dict / from_dict")

entry.trigger = "periodic"
entry.observations = ["Calidad mejorando"]
entry.strengths = ["Código excelente"]
entry.blind_spots = ["Creatividad baja"]
entry.improvement_plan = ["Aumentar temperature para creative"]
entry.confidence = 0.75
entry.data_points = 4

d = entry.to_dict()
test("ReflectionEntry: to_dict has id", "id" in d)
test("ReflectionEntry: to_dict trigger", d["trigger"] == "periodic")
test("ReflectionEntry: to_dict observations", len(d["observations"]) == 1)
test("ReflectionEntry: to_dict confidence", d["confidence"] == 0.75)

restored = ReflectionEntry.from_dict(d)
test("ReflectionEntry: from_dict trigger", restored.trigger == "periodic")
test("ReflectionEntry: from_dict strengths", restored.strengths == ["Código excelente"])
test("ReflectionEntry: from_dict data_points", restored.data_points == 4)

section("ReflectionEntry — to_text")

text = entry.to_text()
test("ReflectionEntry: to_text has Reflexión", "Reflexión" in text)
test("ReflectionEntry: to_text has strengths", "Código excelente" in text)


# ============================================================
# SELF ANALYZER TESTS
# ============================================================

section("SelfAnalyzer — Quality trend")

analyzer = SelfAnalyzer()

# Insufficient data
result = analyzer.analyze_quality_trend([0.5, 0.6])
test("SelfAnalyzer: quality insufficient", not result["sufficient_data"])

# Improving trend
scores_improving = [0.3, 0.35, 0.4, 0.4, 0.45, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85]
result = analyzer.analyze_quality_trend(scores_improving)
test("SelfAnalyzer: quality sufficient", result["sufficient_data"])
test("SelfAnalyzer: quality improving", result["trend"] == "improving")
test("SelfAnalyzer: quality change positive", result["change"] > 0)

# Declining trend
scores_declining = [0.8, 0.75, 0.7, 0.65, 0.6, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
result = analyzer.analyze_quality_trend(scores_declining)
test("SelfAnalyzer: quality declining", result["trend"] == "declining")
test("SelfAnalyzer: quality change negative", result["change"] < 0)

# Stable
scores_stable = [0.5] * 20
result = analyzer.analyze_quality_trend(scores_stable)
test("SelfAnalyzer: quality stable", result["trend"] == "stable")

section("SelfAnalyzer — Intent distribution")

# Insufficient data
result = analyzer.analyze_intent_distribution({"code": 5})
test("SelfAnalyzer: intent insufficient", not result["sufficient_data"])

# Normal distribution
result = analyzer.analyze_intent_distribution({"code": 15, "chat": 10, "research": 5})
test("SelfAnalyzer: intent sufficient", result["sufficient_data"])
test("SelfAnalyzer: intent dominant", result["dominant_intent"] == "code")
test("SelfAnalyzer: intent no high concentration", not result["high_concentration"])

# High concentration
result = analyzer.analyze_intent_distribution({"code": 80, "chat": 10, "other": 10})
test("SelfAnalyzer: intent high concentration", result["high_concentration"])

# Under-served
result = analyzer.analyze_intent_distribution({"code": 50, "chat": 45, "rare": 2, "tiny": 1})
test("SelfAnalyzer: under_served detected", len(result["under_served"]) > 0)

section("SelfAnalyzer — Feedback ratio")

# Insufficient
result = analyzer.analyze_feedback_ratio(3, 2)
test("SelfAnalyzer: feedback insufficient", not result["sufficient_data"])

# Excellent
result = analyzer.analyze_feedback_ratio(90, 10)
test("SelfAnalyzer: feedback excellent", result["sentiment"] == "excellent")
test("SelfAnalyzer: feedback ratio 0.9", result["ratio"] == 0.9)

# Poor
result = analyzer.analyze_feedback_ratio(10, 90)
test("SelfAnalyzer: feedback poor", result["sentiment"] == "poor")

# Mixed
result = analyzer.analyze_feedback_ratio(50, 50)
test("SelfAnalyzer: feedback mixed", result["sentiment"] == "mixed")

# Good
result = analyzer.analyze_feedback_ratio(70, 30)
test("SelfAnalyzer: feedback good", result["sentiment"] == "good")

section("SelfAnalyzer — Personality drift")

# Insufficient
result = analyzer.analyze_personality_drift(0.1, 5)
test("SelfAnalyzer: drift insufficient", not result["sufficient_data"])

# High drift
result = analyzer.analyze_personality_drift(0.4, 50)
test("SelfAnalyzer: drift high", result["stability"] == "high_drift")

# Stable
result = analyzer.analyze_personality_drift(0.03, 50)
test("SelfAnalyzer: drift very stable", result["stability"] == "very_stable")

# Moderate
result = analyzer.analyze_personality_drift(0.2, 50)
test("SelfAnalyzer: drift moderate", result["stability"] == "moderate_drift")

section("SelfAnalyzer — generate_reflection")

reflection = analyzer.generate_reflection(
    quality_data={"sufficient_data": True, "trend": "declining", "change": -0.1,
                  "avg_first_half": 0.6, "avg_second_half": 0.5},
    feedback_data={"sufficient_data": True, "ratio": 0.45, "sentiment": "mixed",
                   "positive": 45, "negative": 55},
    intent_data={"sufficient_data": True, "distribution": {"code": 0.8, "chat": 0.1, "rare": 0.02},
                 "dominant_intent": "code", "concentration": 0.8, "high_concentration": True,
                 "under_served": ["rare"], "total_intents": 3},
    personality_data={"sufficient_data": True, "distance": 0.4, "evolutions": 100,
                      "stability": "high_drift"},
)
test("SelfAnalyzer: reflection has observations", len(reflection.observations) > 0)
test("SelfAnalyzer: reflection has blind_spots", len(reflection.blind_spots) > 0)
test("SelfAnalyzer: reflection has plan", len(reflection.improvement_plan) > 0)
test("SelfAnalyzer: reflection confidence > 0", reflection.confidence > 0)
test("SelfAnalyzer: reflection data_points 4", reflection.data_points == 4)

# All good scenario
reflection_good = analyzer.generate_reflection(
    quality_data={"sufficient_data": True, "trend": "improving", "change": 0.1,
                  "avg_first_half": 0.6, "avg_second_half": 0.7},
    feedback_data={"sufficient_data": True, "ratio": 0.85, "sentiment": "excellent",
                   "positive": 85, "negative": 15},
    personality_data={"sufficient_data": True, "distance": 0.03, "evolutions": 50,
                      "stability": "very_stable"},
)
test("SelfAnalyzer: good reflection has strengths", len(reflection_good.strengths) > 0)

# Empty data
reflection_empty = analyzer.generate_reflection()
test("SelfAnalyzer: empty reflection works", reflection_empty.data_points == 0)


# ============================================================
# REFLECTION ENGINE COORDINATOR TESTS
# ============================================================

section("ReflectionEngine — Coordinator")

tmpdir = tempfile.mkdtemp()
try:
    re_engine = ReflectionEngine(base_dir=os.path.join(tmpdir, "reflection"))
    test("ReflectionEngine: creado", re_engine is not None)
    test("ReflectionEngine: no reflections", len(re_engine.reflections) == 0)
    test("ReflectionEngine: enabled", re_engine.enabled)

    # Tick + should_reflect
    for i in range(24):
        re_engine.tick()
    test("ReflectionEngine: should_reflect False at 24", not re_engine.should_reflect())
    re_engine.tick()  # Now at 25
    test("ReflectionEngine: should_reflect True at 25", re_engine.should_reflect())

    # Reflect
    entry = re_engine.reflect(
        eval_scores=[0.5] * 20,
        intent_counts={"code": 15, "chat": 10},
        positive_feedback=80,
        negative_feedback=20,
        personality_distance=0.1,
        personality_evolutions=50,
    )
    test("ReflectionEngine: reflect returns entry", entry is not None)
    test("ReflectionEngine: total_reflections 1", re_engine.total_reflections == 1)
    test("ReflectionEngine: entry stored", len(re_engine.reflections) == 1)

    # Latest
    latest = re_engine.get_latest()
    test("ReflectionEngine: latest exists", latest is not None)
    test("ReflectionEngine: latest is entry", latest.reflection_id == entry.reflection_id)

    # Context for prompt
    ctx = re_engine.get_context_for_prompt(max_chars=400)
    # May be empty if no significant findings, but should not error
    test("ReflectionEngine: context works", ctx is not None)

    # Stats
    stats = re_engine.get_stats()
    test("ReflectionEngine: stats has total", "total_reflections" in stats)
    test("ReflectionEngine: stats has next", "next_reflection_in" in stats)

    # Status
    status = re_engine.status()
    test("ReflectionEngine: status not empty", len(status) > 0)

    # Report
    report = re_engine.generate_report()
    test("ReflectionEngine: report has title", "REFLECTION ENGINE" in report)

    # Persistence
    re_engine.save()
    re2 = ReflectionEngine(base_dir=os.path.join(tmpdir, "reflection"))
    test("ReflectionEngine: persistence total", re2.total_reflections == 1)
    test("ReflectionEngine: persistence reflections", len(re2.reflections) == 1)
    test("ReflectionEngine: persistence counter", re2.interaction_counter == 25)

    # Clear
    re_engine.clear()
    test("ReflectionEngine: clear reflections", len(re_engine.reflections) == 0)
    test("ReflectionEngine: clear total", re_engine.total_reflections == 0)

    # Disabled
    re_engine.enabled = False
    result = re_engine.reflect()
    test("ReflectionEngine: disabled returns None", result is None)
    re_engine.enabled = True

    # No latest when empty
    test("ReflectionEngine: no latest after clear", re_engine.get_latest() is None)

finally:
    shutil.rmtree(tmpdir)


# ============================================================
# CONTEXT ROUTER TESTS
# ============================================================

section("ContextSource — Estructura basica")

from core.context_router import ContextSource, ContextBudget, ContextRouter

src = ContextSource(
    name="test_source",
    getter=lambda inp, mc: f"contexto para: {inp[:20]}",
    max_chars=500,
    base_priority=0.7,
    keywords=["python", "codigo"],
)
test("ContextSource: name correcto", src.name == "test_source")
test("ContextSource: max_chars", src.max_chars == 500)
test("ContextSource: base_priority", src.base_priority == 0.7)
test("ContextSource: keywords", src.keywords == ["python", "codigo"])
test("ContextSource: enabled", src.enabled)
test("ContextSource: total_used 0", src.total_used == 0)
test("ContextSource: avg_usefulness 0.5", src.avg_usefulness == 0.5)

section("ContextSource — score_relevance")

score_python = src.score_relevance("necesito ayuda con codigo python")
score_unrelated = src.score_relevance("el clima de hoy")
test("ContextSource: score with keywords > without", score_python > score_unrelated)
test("ContextSource: score unrelated > 0", score_unrelated > 0)

src_disabled = ContextSource(name="disabled")
src_disabled.enabled = False
test("ContextSource: disabled score 0", src_disabled.score_relevance("test") == 0.0)

section("ContextSource — get_context")

ctx = src.get_context("test input", 500)
test("ContextSource: get_context returns string", isinstance(ctx, str))
test("ContextSource: get_context not empty", len(ctx) > 0)
test("ContextSource: total_used incremented", src.total_used == 1)
test("ContextSource: total_chars tracked", src.total_chars_provided > 0)

# No getter
src_no_getter = ContextSource(name="no_getter")
ctx_none = src_no_getter.get_context("test", 500)
test("ContextSource: no getter returns empty", ctx_none == "")

# Error in getter
src_error = ContextSource(name="error", getter=lambda i, m: 1/0)
ctx_error = src_error.get_context("test", 500)
test("ContextSource: error returns empty", ctx_error == "")

section("ContextSource — record_usefulness")

src2 = ContextSource(name="useful_test")
src2.record_usefulness(True)
test("ContextSource: usefulness increased", src2.avg_usefulness > 0.5)
for _ in range(10):
    src2.record_usefulness(False)
test("ContextSource: usefulness decreased after negatives", src2.avg_usefulness < 0.5)

section("ContextSource — to_dict")

d = src.to_dict()
test("ContextSource: to_dict has name", d["name"] == "test_source")
test("ContextSource: to_dict has total_used", "total_used" in d)
test("ContextSource: to_dict has avg_usefulness", "avg_usefulness" in d)


# ============================================================
# CONTEXT BUDGET TESTS
# ============================================================

section("ContextBudget — Allocation")

budget = ContextBudget(total_budget=3000)

src_a = ContextSource(name="A", max_chars=1000, base_priority=0.8)
src_b = ContextSource(name="B", max_chars=800, base_priority=0.4)
src_c = ContextSource(name="C", max_chars=600, base_priority=0.2)

allocations = budget.allocate([(src_a, 0.8), (src_b, 0.4), (src_c, 0.2)])
test("ContextBudget: 3 allocations", len(allocations) == 3)
test("ContextBudget: A gets most", allocations["A"] > allocations["B"])
test("ContextBudget: B gets more than C", allocations["B"] > allocations["C"])
test("ContextBudget: total <= budget", sum(allocations.values()) <= 3000)
test("ContextBudget: A <= max_chars", allocations["A"] <= 1000)

# Minimum allocation
allocations2 = budget.allocate([(src_a, 0.99), (src_c, 0.01)])
test("ContextBudget: min allocation >= 100", all(v >= 100 for v in allocations2.values()))

# Empty
test("ContextBudget: empty allocation", budget.allocate([]) == {})

# Low scores filtered
allocations3 = budget.allocate([(src_a, 0.8), (src_c, 0.05)])
test("ContextBudget: low score filtered", "C" not in allocations3)


# ============================================================
# CONTEXT ROUTER COORDINATOR TESTS
# ============================================================

section("ContextRouter — Coordinator")

tmpdir = tempfile.mkdtemp()
try:
    router = ContextRouter(base_dir=os.path.join(tmpdir, "router"), total_budget=2000)
    test("ContextRouter: creado", router is not None)
    test("ContextRouter: enabled", router.enabled)

    # Register sources
    router.register_source(
        "memory",
        getter=lambda inp, mc: f"[MEM] recordando sobre {inp[:15]}...",
        max_chars=800, base_priority=0.7,
        keywords=["recuerda", "antes"],
    )
    router.register_source(
        "skills",
        getter=lambda inp, mc: f"[SKILL] como hacer {inp[:15]}...",
        max_chars=600, base_priority=0.6,
        keywords=["como", "instalar", "crear"],
    )
    router.register_source(
        "goals",
        getter=lambda inp, mc: "[META] Aprender Python (80%)",
        max_chars=400, base_priority=0.3,
        keywords=["meta", "objetivo"],
    )
    test("ContextRouter: 3 sources registered", len(router.sources) == 3)

    # Route
    result = router.route("como instalar docker y crear contenedores")
    test("ContextRouter: route returns string", isinstance(result, str))
    test("ContextRouter: route not empty", len(result) > 0)
    test("ContextRouter: total_routes 1", router.total_routes == 1)
    test("ContextRouter: allocation history 1", len(router.allocation_history) == 1)

    # Route with keyword match
    result2 = router.route("recuerda lo que hablamos antes sobre python")
    test("ContextRouter: memory route not empty", len(result2) > 0)

    # Route empty (disabled)
    router.enabled = False
    result_disabled = router.route("test")
    test("ContextRouter: disabled returns empty", result_disabled == "")
    router.enabled = True

    # Feedback
    router.record_feedback(True)
    test("ContextRouter: feedback recorded", True)  # No error

    router.record_feedback(False, active_sources=["memory"])
    mem_source = router.sources["memory"]
    test("ContextRouter: feedback affects usefulness", mem_source.avg_usefulness != 0.5)

    # Source stats
    source_stats = router.get_source_stats()
    test("ContextRouter: source_stats has memory", "memory" in source_stats)
    test("ContextRouter: source_stats has total_used", "total_used" in source_stats["memory"])

    # Stats
    stats = router.get_stats()
    test("ContextRouter: stats has total_routes", "total_routes" in stats)
    test("ContextRouter: stats has registered_sources", stats["registered_sources"] == 3)

    # Status
    status = router.status()
    test("ContextRouter: status not empty", len(status) > 0)

    # Report
    report = router.generate_report()
    test("ContextRouter: report has title", "CONTEXT ROUTER" in report)

    # Persistence
    router.save()
    router2 = ContextRouter(base_dir=os.path.join(tmpdir, "router"))
    test("ContextRouter: persistence total_routes", router2.total_routes == router.total_routes)
    test("ContextRouter: persistence sources restored", len(router2.sources) == 3)
    # Re-register getters (persistence only saves stats, not lambdas)
    router2.register_source(
        "memory",
        getter=lambda inp, mc: f"[MEM] recordando...",
        max_chars=800, base_priority=0.7,
    )
    test("ContextRouter: re-register keeps stats", router2.sources["memory"].total_used > 0)

    # Clear
    router.clear()
    test("ContextRouter: clear total_routes", router.total_routes == 0)
    test("ContextRouter: clear sources kept", len(router.sources) == 3)

finally:
    shutil.rmtree(tmpdir)


# ============================================================
# INTEGRATION TESTS — genesis.py
# ============================================================

section("Genesis.py — Imports v2.5")

import importlib
test("Import: GoalManager", importlib.import_module("core.goal_manager") is not None)
test("Import: ReflectionEngine", importlib.import_module("core.reflection_engine") is not None)
test("Import: ContextRouter", importlib.import_module("core.context_router") is not None)

section("Genesis.py — Integration checks")

genesis_src = open("genesis.py", "r", encoding="utf-8").read()

# Imports
test("Genesis: import GoalManager", "from core.goal_manager import GoalManager" in genesis_src)
test("Genesis: import ReflectionEngine", "from core.reflection_engine import ReflectionEngine" in genesis_src)
test("Genesis: import ContextRouter", "from core.context_router import ContextRouter" in genesis_src)

# Init
test("Genesis: goal_manager init", "self.goal_manager = GoalManager(" in genesis_src)
test("Genesis: reflection init", "self.reflection = ReflectionEngine(" in genesis_src)
test("Genesis: context_router init", "self.context_router = ContextRouter(" in genesis_src)

# Context injection
test("Genesis: goals context injection", "goals_context = self.goal_manager.get_context_for_prompt" in genesis_src)
test("Genesis: reflection context injection", "reflection_context = self.reflection.get_context_for_prompt" in genesis_src)

# Post-process
test("Genesis: goal auto_track", "self.goal_manager.auto_track(" in genesis_src)
test("Genesis: reflection tick", "self.reflection.tick()" in genesis_src)
test("Genesis: reflection should_reflect", "self.reflection.should_reflect()" in genesis_src)

# Commands
test("Genesis: /goals command", '"/goals"' in genesis_src or 'cmd == "/goals"' in genesis_src)
test("Genesis: /reflection command", '"/reflection"' in genesis_src or 'cmd == "/reflection"' in genesis_src)
test("Genesis: /router command", '"/router"' in genesis_src or 'cmd == "/router"' in genesis_src)

# Dashboard collectors
test("Genesis: goal_manager dashboard", '"goal_manager"' in genesis_src)
test("Genesis: reflection dashboard", '"reflection"' in genesis_src and "lambda: self.reflection.get_stats()" in genesis_src)
test("Genesis: context_router dashboard", '"context_router"' in genesis_src)

# Save on exit
test("Genesis: goal_manager save", "self.goal_manager.save()" in genesis_src)
test("Genesis: reflection save", "self.reflection.save()" in genesis_src)
test("Genesis: context_router save", "self.context_router.save()" in genesis_src)

# Status sections
test("Genesis: GOAL MANAGER status", "GOAL MANAGER" in genesis_src)
test("Genesis: REFLECTION ENGINE status", "REFLECTION ENGINE" in genesis_src)
test("Genesis: CONTEXT ROUTER status", "CONTEXT ROUTER" in genesis_src)

# Help text
test("Genesis: /goals help", "/goals" in genesis_src)
test("Genesis: /reflection help", "/reflection" in genesis_src)
test("Genesis: /router help", "/router" in genesis_src)

# Banner
test("Genesis: goals banner", "goal_manager.get_active_goals()" in genesis_src)
test("Genesis: reflection banner", "reflection.total_reflections" in genesis_src)
test("Genesis: context_router banner", "context_router.sources" in genesis_src)

# Context sources setup
test("Genesis: _setup_context_sources method", "_setup_context_sources" in genesis_src)
test("Genesis: semantic_memory source", '"semantic_memory"' in genesis_src)
test("Genesis: goals source registered", '"goals"' in genesis_src)
test("Genesis: reflection source registered", '"reflection"' in genesis_src)


# ============================================================
# INTEGRATION TESTS — web_ui.py
# ============================================================

section("Web UI — Integration checks")

web_src = open("web_ui.py", "r", encoding="utf-8").read()

test("WebUI: goal_manager data", "goal_manager" in web_src)
test("WebUI: reflection data", "g.reflection.get_stats()" in web_src)
test("WebUI: context_router data", "g.context_router.get_stats()" in web_src)
test("WebUI: GoalManager health", "GoalManager" in web_src)
test("WebUI: Reflection health", "Reflection" in web_src)
test("WebUI: ContextRouter health", "ContextRouter" in web_src)


# ============================================================
# VERSION CHECK
# ============================================================

section("Version check")

from config import GENESIS_VERSION

test("Version >= 2.5.0", GENESIS_VERSION >= "2.5.0")


# ============================================================
# EDGE CASES
# ============================================================

section("Edge cases")

# Goal with empty title
g_empty = Goal(title="", description="", priority=5)
test("Edge: empty title Goal works", g_empty.goal_id is not None)
test("Edge: empty title to_text works", isinstance(g_empty.to_text(), str))

# ReflectionEntry with no data
entry_empty = ReflectionEntry()
text = entry_empty.to_text()
test("Edge: empty reflection to_text", isinstance(text, str))

# ContextSource with no keywords but with getter
src_no_kw = ContextSource(name="no_kw", getter=lambda i, m: "ctx", base_priority=0.5)
score = src_no_kw.score_relevance("test input")
test("Edge: no keywords score > 0", score > 0)

# GoalManager with max goals exceeded
tmpdir = tempfile.mkdtemp()
try:
    gm_max = GoalManager(base_dir=os.path.join(tmpdir, "max_goals"))
    gm_max.max_goals = 5
    # Create some, complete/abandon some, then create more to trigger eviction
    for i in range(3):
        g = gm_max.create_goal(f"Goal {i}", priority=i + 1, source="auto")
        g.complete()
    for i in range(3, 6):
        g = gm_max.create_goal(f"Goal {i}", priority=i + 1, source="auto")
        g.abandon()
        g.created_at = time.time() - (200 * 3600)  # Old enough to evict
    for i in range(6, 10):
        gm_max.create_goal(f"Goal {i}", priority=i + 1, source="auto")
    test("Edge: max_goals eviction works", len(gm_max.goals) <= gm_max.max_goals + 1)
finally:
    shutil.rmtree(tmpdir)

# Multiple reflections
tmpdir = tempfile.mkdtemp()
try:
    re_multi = ReflectionEngine(base_dir=os.path.join(tmpdir, "multi_ref"))
    for i in range(5):
        re_multi.reflect(
            eval_scores=[0.5] * 20,
            intent_counts={"code": 20},
            positive_feedback=50,
            negative_feedback=50,
        )
    test("Edge: 5 reflections stored", len(re_multi.reflections) == 5)
    test("Edge: total_reflections 5", re_multi.total_reflections == 5)
finally:
    shutil.rmtree(tmpdir)

# ContextRouter with all sources disabled
tmpdir = tempfile.mkdtemp()
try:
    router_empty = ContextRouter(base_dir=os.path.join(tmpdir, "empty_router"))
    router_empty.register_source("disabled_src", getter=lambda i, m: "test")
    router_empty.sources["disabled_src"].enabled = False
    result = router_empty.route("test")
    test("Edge: all disabled returns empty", result == "")
finally:
    shutil.rmtree(tmpdir)

# GoalManager suggest_goals with no data
gm_no_data = GoalManager.__new__(GoalManager)
gm_no_data.goals = []
gm_no_data.tracker = GoalTracker()
gm_no_data.suggester = GoalSuggester()
gm_no_data.enabled = True
suggestions_empty = gm_no_data.suggest_goals()
test("Edge: suggest_goals empty returns []", suggestions_empty == [])

# ReflectionEngine context_for_prompt with old reflection
tmpdir = tempfile.mkdtemp()
try:
    re_old = ReflectionEngine(base_dir=os.path.join(tmpdir, "old_ref"))
    entry_old = re_old.reflect(eval_scores=[0.5] * 20)
    entry_old.timestamp = time.time() - (25 * 3600)  # 25 hours ago
    re_old.reflections[-1] = entry_old
    ctx = re_old.get_context_for_prompt()
    test("Edge: old reflection returns empty context", ctx == "")
finally:
    shutil.rmtree(tmpdir)


# ============================================================
# RESULTS
# ============================================================
print(f"\n{'='*60}")
print(f"  GENESIS v2.5 Tests: {_passed}/{_passed + _failed} passed")
if _failed == 0:
    print(f"  ALL TESTS PASSED!")
else:
    print(f"  {_failed} FAILED")
print(f"{'='*60}")

sys.exit(0 if _failed == 0 else 1)
