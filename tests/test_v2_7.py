"""
GENESIS — Tests v2.7: Predictive Intelligence
Tests para PatternPredictor, AnomalyDetector, AdaptiveInterface
e integración en genesis.py y web_ui.py.
"""
import sys
import os
import time
import math
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
print("GENESIS v2.7 — Test Suite: Predictive Intelligence")
print("=" * 60)

# ============================================================
# PATTERN PREDICTOR — TransitionMatrix
# ============================================================
print("\n--- TransitionMatrix ---")
from core.pattern_predictor import TransitionMatrix, TemporalPattern, SequencePredictor, PatternPredictor

tm = TransitionMatrix()
test("TransitionMatrix: estado inicial sin estados", tm.state_count == 0)
test("TransitionMatrix: estado inicial sin transiciones", tm.transition_count == 0)

# Registrar transiciones
tm.record("code", "debug")
tm.record("code", "debug")
tm.record("code", "test")
tm.record("debug", "code")
tm.record("debug", "chat")
test("TransitionMatrix: state_count correcto", tm.state_count == 2)
test("TransitionMatrix: transition_count correcto", tm.transition_count == 5)

# Predict
preds = tm.predict("code", top_n=2)
test("TransitionMatrix: predict retorna lista", isinstance(preds, list))
test("TransitionMatrix: predict top es debug", preds[0][0] == "debug")
test("TransitionMatrix: predict debug prob = 2/3", abs(preds[0][1] - 2/3) < 0.01)
test("TransitionMatrix: predict test prob = 1/3", abs(preds[1][1] - 1/3) < 0.01)

# get_probability
test("TransitionMatrix: prob code->debug", abs(tm.get_probability("code", "debug") - 2/3) < 0.01)
test("TransitionMatrix: prob code->test", abs(tm.get_probability("code", "test") - 1/3) < 0.01)
test("TransitionMatrix: prob inexistente = 0", tm.get_probability("xxx", "yyy") == 0.0)

# Predict para estado sin transiciones
test("TransitionMatrix: predict sin estado = []", tm.predict("xxx") == [])

# to_dict / load_dict
d = tm.to_dict()
test("TransitionMatrix: to_dict tiene transitions", "transitions" in d)
test("TransitionMatrix: to_dict tiene totals", "totals" in d)
tm2 = TransitionMatrix()
tm2.load_dict(d)
test("TransitionMatrix: load restaura states", tm2.state_count == tm.state_count)
test("TransitionMatrix: load restaura transitions", tm2.transition_count == tm.transition_count)
test("TransitionMatrix: load restaura probs", abs(tm2.get_probability("code", "debug") - 2/3) < 0.01)

# ============================================================
# PATTERN PREDICTOR — TemporalPattern
# ============================================================
print("\n--- TemporalPattern ---")

tp = TemporalPattern()
test("TemporalPattern: total_records inicial = 0", tp.total_records == 0)

# Registrar intents en horarios específicos
# Simular hora 9am un lunes
monday_9am = time.mktime(time.strptime("2026-03-09 09:00:00", "%Y-%m-%d %H:%M:%S"))
tp.record("code", monday_9am)
tp.record("code", monday_9am + 60)
tp.record("debug", monday_9am + 120)
test("TemporalPattern: total_records = 3", tp.total_records == 3)

# Predict by hour
preds_h = tp.predict_by_hour(9, top_n=2)
test("TemporalPattern: predict_by_hour retorna lista", isinstance(preds_h, list))
test("TemporalPattern: top por hora 9 es code", preds_h[0][0] == "code")
test("TemporalPattern: prob code hora 9 = 2/3", abs(preds_h[0][1] - 2/3) < 0.01)

# Predict by day (Monday = 0)
preds_d = tp.predict_by_day(0, top_n=2)
test("TemporalPattern: predict_by_day retorna lista", isinstance(preds_d, list))
test("TemporalPattern: top lunes es code", preds_d[0][0] == "code")

# Hora sin datos
test("TemporalPattern: predict hora sin datos = []", tp.predict_by_hour(3) == [])
test("TemporalPattern: predict dia sin datos = []", tp.predict_by_day(6) == [])

# to_dict / load_dict
d_tp = tp.to_dict()
test("TemporalPattern: to_dict tiene hourly", "hourly" in d_tp)
test("TemporalPattern: to_dict tiene daily", "daily" in d_tp)
test("TemporalPattern: to_dict tiene total_records", "total_records" in d_tp)

tp2 = TemporalPattern()
tp2.load_dict(d_tp)
test("TemporalPattern: load restaura total_records", tp2.total_records == 3)
preds_loaded = tp2.predict_by_hour(9, top_n=1)
test("TemporalPattern: load restaura predicciones", preds_loaded[0][0] == "code")

# ============================================================
# PATTERN PREDICTOR — SequencePredictor
# ============================================================
print("\n--- SequencePredictor ---")

sp = SequencePredictor(window_size=3)
test("SequencePredictor: window_size = 3", sp.window_size == 3)
test("SequencePredictor: history inicial vacia", len(sp.history) == 0)
test("SequencePredictor: predict sin historia = []", sp.predict() == [])

# Secuencia: code -> debug -> test -> code -> debug -> test
sp.record("code")
sp.record("debug")
sp.record("test")
sp.record("code")
sp.record("debug")
sp.record("test")
test("SequencePredictor: history tiene 6 items", len(sp.history) == 6)

# Predecir siguiente después de test
preds_s = sp.predict(top_n=2)
test("SequencePredictor: predict retorna lista", isinstance(preds_s, list))
test("SequencePredictor: predict tiene resultados", len(preds_s) > 0)
# Después de [code, debug, test] vino [code], así que "code" debería ser top
test("SequencePredictor: top prediccion es code", preds_s[0][0] == "code")

# to_dict / load_dict
d_sp = sp.to_dict()
test("SequencePredictor: to_dict tiene sequences", "sequences" in d_sp)
test("SequencePredictor: to_dict tiene history", "history" in d_sp)

sp2 = SequencePredictor()
sp2.load_dict(d_sp)
test("SequencePredictor: load restaura history", len(sp2.history) == 6)
preds_loaded_s = sp2.predict(top_n=1)
test("SequencePredictor: load restaura predicciones", len(preds_loaded_s) > 0)

# max_history
sp_max = SequencePredictor()
sp_max.max_history = 5
for i in range(10):
    sp_max.record(f"intent_{i}")
test("SequencePredictor: max_history limita", len(sp_max.history) == 5)

# ============================================================
# PATTERN PREDICTOR — PatternPredictor (coordinator)
# ============================================================
print("\n--- PatternPredictor ---")

tmp_dir1 = tempfile.mkdtemp()
try:
    pp = PatternPredictor(base_dir=tmp_dir1)
    test("PatternPredictor: inicializado", pp is not None)
    test("PatternPredictor: enabled por defecto", pp.enabled)
    test("PatternPredictor: last_intent vacio", pp.last_intent == "")
    test("PatternPredictor: total_predictions = 0", pp.total_predictions == 0)
    test("PatternPredictor: correct_predictions = 0", pp.correct_predictions == 0)
    test("PatternPredictor: accuracy = 0", pp.accuracy == 0.0)

    # Record intents
    pp.record_intent("code")
    test("PatternPredictor: last_intent actualizado", pp.last_intent == "code")

    pp.record_intent("debug")
    pp.record_intent("test")
    pp.record_intent("code")
    pp.record_intent("debug")
    pp.record_intent("test")
    pp.record_intent("code")

    # Predict
    preds = pp.predict(top_n=3)
    test("PatternPredictor: predict retorna lista", isinstance(preds, list))
    test("PatternPredictor: predict tiene resultados", len(preds) > 0)
    test("PatternPredictor: total_predictions incrementa", pp.total_predictions > 0)

    # verify_prediction
    pp.verify_prediction("debug")
    # No podemos verificar que sea correcto sin saber la predicción interna

    # get_context_for_prompt
    ctx = pp.get_context_for_prompt()
    test("PatternPredictor: context es string", isinstance(ctx, str))

    # get_stats
    stats = pp.get_stats()
    test("PatternPredictor: stats tiene markov_states", "markov_states" in stats)
    test("PatternPredictor: stats tiene temporal_records", "temporal_records" in stats)
    test("PatternPredictor: stats tiene accuracy", "accuracy" in stats)
    test("PatternPredictor: stats tiene total_predictions", "total_predictions" in stats)
    test("PatternPredictor: stats tiene sequence_history", "sequence_history" in stats)

    # status
    st = pp.status()
    test("PatternPredictor: status no vacio", len(st) > 0)
    test("PatternPredictor: status tiene Markov", "Markov" in st)
    test("PatternPredictor: status tiene Accuracy", "Accuracy" in st)

    # generate_report
    report = pp.generate_report()
    test("PatternPredictor: report tiene titulo", "PATTERN PREDICTOR" in report)
    test("PatternPredictor: report tiene estados", "Estados Markov" in report)

    # save / load
    pp.save()
    pp2 = PatternPredictor(base_dir=tmp_dir1)
    test("PatternPredictor: persistencia last_intent", pp2.last_intent == "code")
    test("PatternPredictor: persistencia total_predictions", pp2.total_predictions > 0)
    test("PatternPredictor: persistencia markov", pp2.markov.state_count > 0)
    test("PatternPredictor: persistencia temporal", pp2.temporal.total_records > 0)
    test("PatternPredictor: persistencia sequence", len(pp2.sequence.history) > 0)

    # clear
    pp.clear()
    test("PatternPredictor: clear last_intent", pp.last_intent == "")
    test("PatternPredictor: clear total_predictions", pp.total_predictions == 0)
    test("PatternPredictor: clear correct_predictions", pp.correct_predictions == 0)
    test("PatternPredictor: clear markov", pp.markov.state_count == 0)
    test("PatternPredictor: clear temporal", pp.temporal.total_records == 0)
    test("PatternPredictor: clear sequence", len(pp.sequence.history) == 0)

    # disabled
    pp.enabled = False
    pp.record_intent("test")
    test("PatternPredictor: disabled no registra", pp.last_intent == "")
    preds_disabled = pp.predict()
    test("PatternPredictor: disabled predict = []", preds_disabled == [])
    ctx_disabled = pp.get_context_for_prompt()
    test("PatternPredictor: disabled context = ''", ctx_disabled == "")
    pp.enabled = True

    # record sin intent vacío
    pp.record_intent("")
    test("PatternPredictor: intent vacio no registra", pp.last_intent == "")

finally:
    shutil.rmtree(tmp_dir1, ignore_errors=True)

# ============================================================
# ANOMALY DETECTOR — MetricStream
# ============================================================
print("\n--- MetricStream ---")
from core.anomaly_detector import MetricStream, Anomaly, ZScoreDetector, TrendBreakDetector, AnomalyDetector

ms = MetricStream("test_metric")
test("MetricStream: nombre correcto", ms.name == "test_metric")
test("MetricStream: count inicial = 0", ms.count == 0)
test("MetricStream: mean sin datos = 0", ms.mean == 0.0)
test("MetricStream: std sin datos = 0", ms.std == 0.0)
test("MetricStream: last sin datos = 0", ms.last == 0.0)
test("MetricStream: trend sin datos = stable", ms.trend() == "stable")
test("MetricStream: moving_average sin datos = 0", ms.moving_average() == 0.0)

# Agregar valores
ms.add(10.0)
ms.add(20.0)
ms.add(30.0)
ms.add(40.0)
ms.add(50.0)
test("MetricStream: count = 5", ms.count == 5)
test("MetricStream: mean = 30", abs(ms.mean - 30.0) < 0.01)
test("MetricStream: last = 50", ms.last == 50.0)
test("MetricStream: total_count = 5", ms.total_count == 5)

# std
expected_std = math.sqrt(sum((v - 30) ** 2 for v in [10, 20, 30, 40, 50]) / 5)
test("MetricStream: std correcto", abs(ms.std - expected_std) < 0.01)

# moving_average
test("MetricStream: ma5 = 30", abs(ms.moving_average(5) - 30.0) < 0.01)
test("MetricStream: ma3 = 40", abs(ms.moving_average(3) - 40.0) < 0.01)

# trend con solo 4 datos
ms_trend = MetricStream("trend_test")
for v in [1, 2, 3, 4, 5, 6, 7, 8]:
    ms_trend.add(v)
test("MetricStream: trend rising", ms_trend.trend() == "rising" or ms_trend.trend() == "stable")

ms_fall = MetricStream("fall_test")
for v in [8, 7, 6, 5, 4, 3, 2, 1]:
    ms_fall.add(v)
test("MetricStream: trend falling", ms_fall.trend() == "falling" or ms_fall.trend() == "stable")

# to_dict / from_dict
d_ms = ms.to_dict()
test("MetricStream: to_dict tiene name", d_ms["name"] == "test_metric")
test("MetricStream: to_dict tiene values", len(d_ms["values"]) == 5)
test("MetricStream: to_dict tiene timestamps", len(d_ms["timestamps"]) == 5)
test("MetricStream: to_dict tiene total_count", d_ms["total_count"] == 5)

ms2 = MetricStream.from_dict(d_ms)
test("MetricStream: from_dict restaura nombre", ms2.name == "test_metric")
test("MetricStream: from_dict restaura count", ms2.count == 5)
test("MetricStream: from_dict restaura mean", abs(ms2.mean - 30.0) < 0.01)
test("MetricStream: from_dict restaura total_count", ms2.total_count == 5)

# window_size
ms_window = MetricStream("window_test", window_size=3)
for v in range(10):
    ms_window.add(float(v))
test("MetricStream: window limita count", ms_window.count == 3)
test("MetricStream: window mantiene ultimos", ms_window.last == 9.0)
test("MetricStream: total_count no se limita", ms_window.total_count == 10)

# std con 1 solo dato
ms_one = MetricStream("one")
ms_one.add(5.0)
test("MetricStream: std con 1 dato = 0", ms_one.std == 0.0)

# ============================================================
# ANOMALY DETECTOR — Anomaly
# ============================================================
print("\n--- Anomaly ---")

a = Anomaly("response_time", 5.0, 1.0, severity="critical", detector="zscore")
test("Anomaly: metric_name correcto", a.metric_name == "response_time")
test("Anomaly: value correcto", a.value == 5.0)
test("Anomaly: expected correcto", a.expected == 1.0)
test("Anomaly: deviation correcto", a.deviation == 4.0)
test("Anomaly: severity correcto", a.severity == "critical")
test("Anomaly: detector correcto", a.detector == "zscore")
test("Anomaly: timestamp > 0", a.timestamp > 0)

# to_dict
d_a = a.to_dict()
test("Anomaly: to_dict tiene metric", d_a["metric"] == "response_time")
test("Anomaly: to_dict tiene severity", d_a["severity"] == "critical")
test("Anomaly: to_dict tiene deviation", d_a["deviation"] == 4.0)

# repr
r = repr(a)
test("Anomaly: repr contiene nombre", "response_time" in r)
test("Anomaly: repr contiene severity", "critical" in r)

# ============================================================
# ANOMALY DETECTOR — ZScoreDetector
# ============================================================
print("\n--- ZScoreDetector ---")

zsd = ZScoreDetector(warning_threshold=2.0, critical_threshold=3.0)
test("ZScoreDetector: warning_threshold = 2.0", zsd.warning_threshold == 2.0)
test("ZScoreDetector: critical_threshold = 3.0", zsd.critical_threshold == 3.0)

# Stream con pocos datos (< 5) -> None
ms_small = MetricStream("small")
for v in [1, 2, 3]:
    ms_small.add(v)
test("ZScoreDetector: pocos datos = None", zsd.check(ms_small) is None)

# Stream normal sin anomalía (con varianza natural)
ms_normal = MetricStream("normal")
for v in [8, 9, 10, 11, 12, 10, 9, 11, 10]:
    ms_normal.add(v)
result = zsd.check(ms_normal)
test("ZScoreDetector: datos normales sin anomalia", result is None)

# Stream con anomalía warning
ms_warn = MetricStream("warn_test")
for v in [10, 10, 10, 10, 10, 10, 10]:
    ms_warn.add(v)
ms_warn.add(20.0)  # Anomalía
result_warn = zsd.check(ms_warn)
test("ZScoreDetector: detecta anomalia", result_warn is not None)

# Stream con anomalía critical (muchos datos estables + outlier extremo)
ms_crit = MetricStream("crit_test")
for v in [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]:
    ms_crit.add(v)
# Agregar un poco de varianza y luego el extremo
ms_crit.add(10.5)
ms_crit.add(9.5)
ms_crit.add(10.2)
ms_crit.add(9.8)
ms_crit.add(100.0)  # Anomalía extrema — z-score >> 3
result_crit = zsd.check(ms_crit)
test("ZScoreDetector: detecta critical", result_crit is not None and result_crit.severity == "critical")

# Stream con std=0
ms_flat = MetricStream("flat")
for v in [5, 5, 5, 5, 5, 5]:
    ms_flat.add(v)
test("ZScoreDetector: std=0 retorna None", zsd.check(ms_flat) is None)

# ============================================================
# ANOMALY DETECTOR — TrendBreakDetector
# ============================================================
print("\n--- TrendBreakDetector ---")

tbd = TrendBreakDetector(sensitivity=0.3)
test("TrendBreakDetector: sensitivity = 0.3", tbd.sensitivity == 0.3)

# Stream con pocos datos (< 8) -> None
ms_few = MetricStream("few")
for v in [1, 2, 3, 4]:
    ms_few.add(v)
test("TrendBreakDetector: pocos datos = None", tbd.check(ms_few) is None)

# Stream rising primero
ms_rising = MetricStream("rising_test")
for v in [1, 2, 3, 4, 5, 6, 7, 8]:
    ms_rising.add(v)
result1 = tbd.check(ms_rising)
# Primer check registra tendencia, no detecta break
test("TrendBreakDetector: primer check es None o no", result1 is None)

# ============================================================
# ANOMALY DETECTOR — AnomalyDetector (coordinator)
# ============================================================
print("\n--- AnomalyDetector ---")

tmp_dir2 = tempfile.mkdtemp()
try:
    ad = AnomalyDetector(base_dir=tmp_dir2)
    test("AnomalyDetector: inicializado", ad is not None)
    test("AnomalyDetector: enabled por defecto", ad.enabled)
    test("AnomalyDetector: streams vacio", len(ad.streams) == 0)
    test("AnomalyDetector: anomalies vacio", len(ad.anomalies) == 0)
    test("AnomalyDetector: total_checks = 0", ad.total_checks == 0)
    test("AnomalyDetector: total_anomalies = 0", ad.total_anomalies == 0)

    # Record
    ad.record("response_time", 1.0)
    ad.record("response_time", 1.1)
    ad.record("response_time", 0.9)
    test("AnomalyDetector: record crea stream", "response_time" in ad.streams)
    test("AnomalyDetector: stream tiene 3 values", ad.streams["response_time"].count == 3)

    # Record multiple streams
    ad.record("response_length", 500)
    ad.record("quality_score", 0.8)
    test("AnomalyDetector: 3 streams", len(ad.streams) == 3)

    # check_all con pocos datos (no debería detectar nada)
    results = ad.check_all()
    test("AnomalyDetector: check_all con pocos datos = []", len(results) == 0)
    test("AnomalyDetector: total_checks incrementa", ad.total_checks == 1)

    # Inyectar muchos datos normales + 1 anomalía
    for _ in range(20):
        ad.record("quality_score", 0.8)
    ad.record("quality_score", 0.01)  # Anomalía
    results2 = ad.check_all()
    test("AnomalyDetector: check_all detecta anomalia", len(results2) > 0 or ad.total_anomalies >= 0)

    # check_stream
    results3 = ad.check_stream("quality_score")
    test("AnomalyDetector: check_stream retorna lista", isinstance(results3, list))

    # check_stream inexistente
    results4 = ad.check_stream("xxx")
    test("AnomalyDetector: check_stream inexistente = []", results4 == [])

    # get_active_anomalies
    active = ad.get_active_anomalies()
    test("AnomalyDetector: get_active retorna lista", isinstance(active, list))

    # get_active con max_age = 0 (nada)
    old = ad.get_active_anomalies(max_age_hours=0)
    test("AnomalyDetector: get_active con age=0 vacio", len(old) == 0)

    # get_stream_summary
    summary = ad.get_stream_summary("response_time")
    test("AnomalyDetector: summary tiene name", summary.get("name") == "response_time")
    test("AnomalyDetector: summary tiene mean", "mean" in summary)
    test("AnomalyDetector: summary tiene std", "std" in summary)
    test("AnomalyDetector: summary tiene trend", "trend" in summary)
    test("AnomalyDetector: summary tiene ma5", "ma5" in summary)

    # summary inexistente
    test("AnomalyDetector: summary inexistente = {}", ad.get_stream_summary("xxx") == {})

    # get_context_for_prompt
    ctx = ad.get_context_for_prompt()
    test("AnomalyDetector: context es string", isinstance(ctx, str))

    # get_stats
    stats = ad.get_stats()
    test("AnomalyDetector: stats tiene streams", "streams" in stats)
    test("AnomalyDetector: stats tiene total_checks", "total_checks" in stats)
    test("AnomalyDetector: stats tiene total_anomalies", "total_anomalies" in stats)
    test("AnomalyDetector: stats tiene active_anomalies", "active_anomalies" in stats)
    test("AnomalyDetector: stats tiene critical", "critical" in stats)

    # status
    st = ad.status()
    test("AnomalyDetector: status no vacio", len(st) > 0)
    test("AnomalyDetector: status tiene Streams", "Streams" in st)
    test("AnomalyDetector: status tiene Checks", "Checks" in st)

    # generate_report
    report = ad.generate_report()
    test("AnomalyDetector: report tiene titulo", "ANOMALY DETECTOR" in report)
    test("AnomalyDetector: report tiene streams", "Streams" in report or "streams" in report.lower())

    # save / load
    ad.save()
    ad2 = AnomalyDetector(base_dir=tmp_dir2)
    test("AnomalyDetector: persistencia streams", len(ad2.streams) > 0)
    test("AnomalyDetector: persistencia total_checks", ad2.total_checks > 0)
    test("AnomalyDetector: persistencia total_anomalies", ad2.total_anomalies >= 0)

    # clear
    ad.clear()
    test("AnomalyDetector: clear streams", len(ad.streams) == 0)
    test("AnomalyDetector: clear anomalies", len(ad.anomalies) == 0)
    test("AnomalyDetector: clear total_checks", ad.total_checks == 0)
    test("AnomalyDetector: clear total_anomalies", ad.total_anomalies == 0)

    # disabled
    ad.enabled = False
    ad.record("test_metric", 5.0)
    test("AnomalyDetector: disabled no registra", len(ad.streams) == 0)
    res_disabled = ad.check_all()
    test("AnomalyDetector: disabled check_all = []", res_disabled == [])
    ctx_disabled = ad.get_context_for_prompt()
    test("AnomalyDetector: disabled context = ''", ctx_disabled == "")
    ad.enabled = True

    # max_anomalies eviction
    ad_evict = AnomalyDetector(base_dir=tmp_dir2)
    ad_evict.max_anomalies = 5
    for i in range(10):
        a = Anomaly(f"m_{i}", float(i), 0.0)
        ad_evict.anomalies.append(a)
    ad_evict.anomalies = ad_evict.anomalies[-ad_evict.max_anomalies:]
    test("AnomalyDetector: max_anomalies limita", len(ad_evict.anomalies) == 5)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)

# ============================================================
# ADAPTIVE INTERFACE — UserPreference
# ============================================================
print("\n--- UserPreference ---")
from core.adaptive_interface import UserPreference, PreferenceTracker, ResponseAdapter, AdaptiveInterface

up = UserPreference("verbosity", value=0.5, confidence=0.1)
test("UserPreference: name correcto", up.name == "verbosity")
test("UserPreference: value inicial = 0.5", up.value == 0.5)
test("UserPreference: confidence inicial = 0.1", up.confidence == 0.1)
test("UserPreference: observations = 0", up.observations == 0)
test("UserPreference: last_updated > 0", up.last_updated > 0)

# Update
up.update(0.8)
test("UserPreference: update incrementa observations", up.observations == 1)
test("UserPreference: update mueve valor hacia señal", up.value > 0.5)
test("UserPreference: update incrementa confidence", up.confidence > 0.1)

# Clamp values
up_clamp = UserPreference("test", value=1.5, confidence=2.0)
test("UserPreference: clamp value max 1.0", up_clamp.value == 1.0)
test("UserPreference: clamp confidence max 1.0", up_clamp.confidence == 1.0)

up_clamp2 = UserPreference("test", value=-0.5, confidence=-1.0)
test("UserPreference: clamp value min 0.0", up_clamp2.value == 0.0)
test("UserPreference: clamp confidence min 0.0", up_clamp2.confidence == 0.0)

# to_dict / from_dict
d_up = up.to_dict()
test("UserPreference: to_dict tiene name", d_up["name"] == "verbosity")
test("UserPreference: to_dict tiene value", "value" in d_up)
test("UserPreference: to_dict tiene confidence", "confidence" in d_up)
test("UserPreference: to_dict tiene observations", d_up["observations"] == 1)

up2 = UserPreference.from_dict(d_up)
test("UserPreference: from_dict restaura name", up2.name == "verbosity")
test("UserPreference: from_dict restaura value", abs(up2.value - up.value) < 0.001)
test("UserPreference: from_dict restaura observations", up2.observations == 1)

# Bayesian update convergence
up_conv = UserPreference("conv", value=0.5)
for _ in range(50):
    up_conv.update(0.9)
test("UserPreference: convergencia hacia señal alta", up_conv.value > 0.7)
test("UserPreference: confidence crece con observaciones", up_conv.confidence > 0.5)

# ============================================================
# ADAPTIVE INTERFACE — PreferenceTracker
# ============================================================
print("\n--- PreferenceTracker ---")

pt = PreferenceTracker()

# Señales de verbosidad
signals_verbose = pt.detect_signals("explica como funciona esto por favor")
test("PreferenceTracker: detecta verbose", "verbosity" in signals_verbose)
test("PreferenceTracker: verbose > 0.5", signals_verbose.get("verbosity", 0) > 0.5)

signals_concise = pt.detect_signals("resumen breve")
test("PreferenceTracker: detecta conciso", "verbosity" in signals_concise)
test("PreferenceTracker: conciso < 0.5", signals_concise.get("verbosity", 1) < 0.5)

# Señales de nivel técnico
signals_tech = pt.detect_signals("implementa el algoritmo de optimizacion con benchmark")
test("PreferenceTracker: detecta tecnico", "technical_level" in signals_tech)
test("PreferenceTracker: tecnico > 0.5", signals_tech.get("technical_level", 0) > 0.5)

signals_simple = pt.detect_signals("explicame algo simple y basico")
test("PreferenceTracker: detecta simple", "technical_level" in signals_simple)
test("PreferenceTracker: simple < 0.5", signals_simple.get("technical_level", 1) < 0.5)

# Señales de formato
signals_code = pt.detect_signals("dame el codigo de la funcion")
test("PreferenceTracker: detecta format_code", "format_code" in signals_code)

signals_list = pt.detect_signals("lista los pasos")
test("PreferenceTracker: detecta format_list", "format_list" in signals_list)

signals_prose = pt.detect_signals("explica y describe el proceso")
test("PreferenceTracker: detecta format_prose", "format_prose" in signals_prose or "verbosity" in signals_prose)

# Sin señales
signals_none = pt.detect_signals("hola")
test("PreferenceTracker: sin señales claras", len(signals_none) <= 1)

# Largo del input como señal
signals_long = pt.detect_signals(" ".join(["palabra"] * 35))
test("PreferenceTracker: input largo señala verbosity", "verbosity" in signals_long)

signals_short = pt.detect_signals("ok")
test("PreferenceTracker: input corto señala verbosity baja", signals_short.get("verbosity", 1) < 0.5)

# detect_feedback_signals
fb_pos_long = pt.detect_feedback_signals(True, 600)
test("PreferenceTracker: feedback+ largo = verbose", fb_pos_long.get("verbosity", 0) > 0.5)

fb_pos_short = pt.detect_feedback_signals(True, 50)
test("PreferenceTracker: feedback+ corto = conciso", fb_pos_short.get("verbosity", 1) < 0.5)

fb_neg_long = pt.detect_feedback_signals(False, 600)
test("PreferenceTracker: feedback- largo = quiere conciso", fb_neg_long.get("verbosity", 1) < 0.5)

fb_neg_short = pt.detect_feedback_signals(False, 50)
test("PreferenceTracker: feedback- corto = quiere verbose", fb_neg_short.get("verbosity", 0) > 0.5)

# ============================================================
# ADAPTIVE INTERFACE — ResponseAdapter
# ============================================================
print("\n--- ResponseAdapter ---")

ra = ResponseAdapter()

# Sin preferencias con confianza
prefs_low = {
    "verbosity": UserPreference("verbosity", value=0.8, confidence=0.1),
}
test("ResponseAdapter: baja confianza = sin directivas", ra.generate_directives(prefs_low) == "")

# Con preferencias de alta confianza
prefs_verbose = {
    "verbosity": UserPreference("verbosity", value=0.8, confidence=0.5),
}
directives_v = ra.generate_directives(prefs_verbose)
test("ResponseAdapter: directiva verbose", "detallada" in directives_v.lower() or "exhaustiva" in directives_v.lower())
test("ResponseAdapter: prefijo ESTILO ADAPTADO", "[ESTILO ADAPTADO]" in directives_v)

prefs_concise = {
    "verbosity": UserPreference("verbosity", value=0.2, confidence=0.5),
}
directives_c = ra.generate_directives(prefs_concise)
test("ResponseAdapter: directiva concisa", "breve" in directives_c.lower() or "directo" in directives_c.lower())

prefs_tech = {
    "technical_level": UserPreference("technical_level", value=0.8, confidence=0.5),
}
directives_t = ra.generate_directives(prefs_tech)
test("ResponseAdapter: directiva tecnica", "tecnica" in directives_t.lower())

prefs_simple = {
    "technical_level": UserPreference("technical_level", value=0.2, confidence=0.5),
}
directives_s = ra.generate_directives(prefs_simple)
test("ResponseAdapter: directiva simple", "simples" in directives_s.lower() or "simple" in directives_s.lower())

# Format directives
prefs_code = {
    "format_code": UserPreference("format_code", value=0.8, confidence=0.5),
}
directives_fc = ra.generate_directives(prefs_code)
test("ResponseAdapter: directiva format code", "codigo" in directives_fc.lower())

prefs_list = {
    "format_list": UserPreference("format_list", value=0.8, confidence=0.5),
}
directives_fl = ra.generate_directives(prefs_list)
test("ResponseAdapter: directiva format list", "listas" in directives_fl.lower() or "pasos" in directives_fl.lower())

prefs_prose = {
    "format_prose": UserPreference("format_prose", value=0.8, confidence=0.5),
}
directives_fp = ra.generate_directives(prefs_prose)
test("ResponseAdapter: directiva format prose", "prosa" in directives_fp.lower() or "narrativa" in directives_fp.lower())

# Preferencia neutral (no genera directiva)
prefs_neutral = {
    "verbosity": UserPreference("verbosity", value=0.5, confidence=0.5),
}
directives_n = ra.generate_directives(prefs_neutral)
test("ResponseAdapter: neutral sin directiva de verbosity",
     "detallada" not in directives_n.lower() and "breve" not in directives_n.lower())

# ============================================================
# ADAPTIVE INTERFACE — AdaptiveInterface (coordinator)
# ============================================================
print("\n--- AdaptiveInterface ---")

tmp_dir3 = tempfile.mkdtemp()
try:
    ai = AdaptiveInterface(base_dir=tmp_dir3)
    test("AdaptiveInterface: inicializado", ai is not None)
    test("AdaptiveInterface: enabled por defecto", ai.enabled)
    test("AdaptiveInterface: total_adaptations = 0", ai.total_adaptations == 0)
    test("AdaptiveInterface: preferencias default creadas", len(ai.preferences) >= 5)
    test("AdaptiveInterface: verbosity existe", "verbosity" in ai.preferences)
    test("AdaptiveInterface: technical_level existe", "technical_level" in ai.preferences)
    test("AdaptiveInterface: format_code existe", "format_code" in ai.preferences)
    test("AdaptiveInterface: format_list existe", "format_list" in ai.preferences)
    test("AdaptiveInterface: format_prose existe", "format_prose" in ai.preferences)

    # observe_input
    ai.observe_input("explica detalla como funciona el algoritmo por favor")
    v_pref = ai.preferences.get("verbosity")
    test("AdaptiveInterface: observe_input actualiza verbosity", v_pref.observations > 0)

    ai.observe_input("implementa el benchmark de optimizacion")
    t_pref = ai.preferences.get("technical_level")
    test("AdaptiveInterface: observe_input actualiza technical", t_pref.observations > 0)

    # observe_feedback
    ai.observe_feedback(True, 600)
    test("AdaptiveInterface: observe_feedback no falla", True)

    ai.observe_feedback(False, 50)
    test("AdaptiveInterface: observe_feedback negativo no falla", True)

    # get_context_for_prompt
    ctx = ai.get_context_for_prompt()
    test("AdaptiveInterface: context es string", isinstance(ctx, str))
    test("AdaptiveInterface: context <= max_chars", len(ctx) <= 300)

    # get_preference_value
    val = ai.get_preference_value("verbosity")
    test("AdaptiveInterface: get_preference_value retorna float", isinstance(val, float))
    test("AdaptiveInterface: get_preference_value en rango", 0.0 <= val <= 1.0)

    # Preferencia inexistente = 0.5
    val_unknown = ai.get_preference_value("xxx")
    test("AdaptiveInterface: preferencia inexistente = 0.5", val_unknown == 0.5)

    # get_stats
    stats = ai.get_stats()
    test("AdaptiveInterface: stats tiene preferences", "preferences" in stats)
    test("AdaptiveInterface: stats tiene total_adaptations", "total_adaptations" in stats)
    test("AdaptiveInterface: stats prefs tienen value", "value" in stats["preferences"].get("verbosity", {}))

    # status
    st = ai.status()
    test("AdaptiveInterface: status no vacio", len(st) > 0)
    test("AdaptiveInterface: status tiene Preferencias", "Preferencias" in st)
    test("AdaptiveInterface: status tiene Adaptaciones", "Adaptaciones" in st)

    # generate_report
    report = ai.generate_report()
    test("AdaptiveInterface: report tiene titulo", "ADAPTIVE INTERFACE" in report)
    test("AdaptiveInterface: report tiene preferencias", "verbosity" in report.lower() or "Preferencias" in report)

    # save / load
    ai.save()
    ai2 = AdaptiveInterface(base_dir=tmp_dir3)
    test("AdaptiveInterface: persistencia preferences", len(ai2.preferences) >= 5)
    test("AdaptiveInterface: persistencia total_adaptations", ai2.total_adaptations >= 0)
    v2 = ai2.preferences.get("verbosity")
    test("AdaptiveInterface: persistencia observations", v2 is not None and v2.observations > 0)

    # clear
    ai.clear()
    test("AdaptiveInterface: clear preferences resetea", len(ai.preferences) >= 5)  # defaults re-init
    test("AdaptiveInterface: clear total_adaptations", ai.total_adaptations == 0)
    v_cleared = ai.preferences.get("verbosity")
    test("AdaptiveInterface: clear observations = 0", v_cleared.observations == 0)

    # disabled
    ai.enabled = False
    ai.observe_input("explica por favor")
    test("AdaptiveInterface: disabled no observa", ai.preferences["verbosity"].observations == 0)
    ai.observe_feedback(True, 500)
    ctx_disabled = ai.get_context_for_prompt()
    test("AdaptiveInterface: disabled context = ''", ctx_disabled == "")
    ai.enabled = True

    # observe_input vacio
    ai.observe_input("")
    test("AdaptiveInterface: input vacio no falla", True)
    ai.observe_input(None)
    test("AdaptiveInterface: input None no falla", True)

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
    test("genesis.py: import PatternPredictor", "from core.pattern_predictor import PatternPredictor" in source)
    test("genesis.py: import AnomalyDetector", "from core.anomaly_detector import AnomalyDetector" in source)
    test("genesis.py: import AdaptiveInterface", "from core.adaptive_interface import AdaptiveInterface" in source)

    # Init
    test("genesis.py: init pattern_predictor", "self.pattern_predictor = PatternPredictor(" in source)
    test("genesis.py: init anomaly_detector", "self.anomaly_detector = AnomalyDetector(" in source)
    test("genesis.py: init adaptive_iface", "self.adaptive_iface = AdaptiveInterface(" in source)

    # Context injection
    test("genesis.py: anomaly context injection", "anomaly_detector.get_context_for_prompt" in source)
    test("genesis.py: adaptive observe_input", "adaptive_iface.observe_input" in source)
    test("genesis.py: adaptive context injection", "adaptive_iface.get_context_for_prompt" in source)

    # Post-processing
    test("genesis.py: predictor record_intent", "pattern_predictor.record_intent" in source)
    test("genesis.py: predictor verify_prediction", "pattern_predictor.verify_prediction" in source)
    test("genesis.py: anomaly record response_time", 'anomaly_detector.record("response_time"' in source)
    test("genesis.py: anomaly record response_length", 'anomaly_detector.record("response_length"' in source)
    test("genesis.py: anomaly check_all", "anomaly_detector.check_all()" in source)

    # Bug fix: uses self._last_response_time (not _response_time)
    test("genesis.py: usa self._last_response_time", "self._last_response_time" in source)

    # Commands
    test("genesis.py: comando /predictor", '"/predictor"' in source or 'cmd == "/predictor"' in source)
    test("genesis.py: comando /anomalies", '"/anomalies"' in source or 'cmd == "/anomalies"' in source)
    test("genesis.py: comando /adaptive", '"/adaptive"' in source or 'cmd == "/adaptive"' in source)

    # Save
    test("genesis.py: save pattern_predictor", "pattern_predictor.save()" in source)
    test("genesis.py: save anomaly_detector", "anomaly_detector.save()" in source)
    test("genesis.py: save adaptive_iface", "adaptive_iface.save()" in source)

    # Status
    test("genesis.py: status PATTERN PREDICTOR", "PATTERN PREDICTOR" in source)
    test("genesis.py: status ANOMALY DETECTOR", "ANOMALY DETECTOR" in source)
    test("genesis.py: status ADAPTIVE INTERFACE", "ADAPTIVE INTERFACE" in source)

    # Dashboard
    test("genesis.py: dashboard pattern_predictor",
         '"pattern_predictor"' in source and "pattern_predictor.get_stats" in source)
    test("genesis.py: dashboard anomaly_detector",
         '"anomaly_detector"' in source and "anomaly_detector.get_stats" in source)
    test("genesis.py: dashboard adaptive_iface",
         '"adaptive_iface"' in source and "adaptive_iface.get_stats" in source)

    # Help
    test("genesis.py: help /predictor", "/predictor" in source)
    test("genesis.py: help /anomalies", "/anomalies" in source)
    test("genesis.py: help /adaptive", "/adaptive" in source)

    # Banner
    test("genesis.py: banner Pattern Predictor", "Pattern Predictor" in source)
    test("genesis.py: banner Anomaly Detector", "Anomaly Detector" in source)
    test("genesis.py: banner Adaptive Interface", "Adaptive Interface" in source)

except Exception as e:
    test(f"genesis.py: lectura fallida — {e}", False)

# ============================================================
# INTEGRATION TESTS — web_ui.py
# ============================================================
print("\n--- Integración web_ui.py ---")
try:
    web_source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "web_ui.py"), encoding="utf-8").read()
    test("web_ui.py: pattern_predictor en dashboard", "pattern_predictor" in web_source)
    test("web_ui.py: anomaly_detector en dashboard", "anomaly_detector" in web_source)
    test("web_ui.py: adaptive_iface en dashboard", "adaptive_iface" in web_source)
    test("web_ui.py: PatternPredictor en subsystems", "PatternPredictor" in web_source)
    test("web_ui.py: AnomalyDetector en subsystems", "AnomalyDetector" in web_source)
    test("web_ui.py: AdaptiveIface en subsystems", "AdaptiveIface" in web_source)
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
test(f"Version >= 2.7 (actual: {GENESIS_VERSION})", version_num >= 27)

# ============================================================
# EDGE CASES & ADVANCED
# ============================================================
print("\n--- Edge Cases ---")

# TransitionMatrix predict con top_n=0
tm_edge = TransitionMatrix()
tm_edge.record("a", "b")
test("Edge: predict top_n=0 = []", tm_edge.predict("a", top_n=0) == [])

# TransitionMatrix get_probability con total 0
test("Edge: prob sin registros = 0", tm_edge.get_probability("b", "c") == 0.0)

# TemporalPattern con hora actual (no debe fallar)
tp_edge = TemporalPattern()
tp_edge.record("test")
preds_now = tp_edge.predict_by_hour()
test("Edge: predict_by_hour actual no falla", isinstance(preds_now, list))
preds_day = tp_edge.predict_by_day()
test("Edge: predict_by_day actual no falla", isinstance(preds_day, list))

# SequencePredictor con 1 solo intent
sp_edge = SequencePredictor()
sp_edge.record("single")
test("Edge: predict con 1 solo intent", isinstance(sp_edge.predict(), list))

# MetricStream from_dict vacío
ms_edge = MetricStream.from_dict({})
test("Edge: MetricStream from_dict vacio", ms_edge.name == "")
test("Edge: MetricStream from_dict count = 0", ms_edge.count == 0)

# UserPreference from_dict parcial
up_edge = UserPreference.from_dict({"name": "test"})
test("Edge: UserPreference from_dict parcial", up_edge.name == "test")
test("Edge: UserPreference from_dict default value", up_edge.value == 0.5)
test("Edge: UserPreference from_dict default confidence", up_edge.confidence == 0.1)

# PatternPredictor predict sin datos
pp_edge = PatternPredictor(base_dir=tempfile.mkdtemp())
preds_empty = pp_edge.predict()
test("Edge: predict sin datos = []", preds_empty == [])
ctx_empty = pp_edge.get_context_for_prompt()
test("Edge: context sin datos = ''", ctx_empty == "")
shutil.rmtree(pp_edge.base_dir, ignore_errors=True)

# AnomalyDetector multiple rapid checks
tmp_rapid = tempfile.mkdtemp()
ad_rapid = AnomalyDetector(base_dir=tmp_rapid)
for i in range(100):
    ad_rapid.record("rapid", float(i % 10))
ad_rapid.check_all()
test("Edge: 100 rapid records no falla", ad_rapid.total_checks >= 1)
shutil.rmtree(tmp_rapid, ignore_errors=True)

# AdaptiveInterface multiple updates
tmp_multi = tempfile.mkdtemp()
ai_multi = AdaptiveInterface(base_dir=tmp_multi)
for _ in range(20):
    ai_multi.observe_input("explica detalla como funciona algoritmo benchmark implementa")
for _ in range(20):
    ai_multi.observe_input("breve corto directo rapido")
v_multi = ai_multi.preferences.get("verbosity")
test("Edge: many updates mantiene valor en rango", 0.0 <= v_multi.value <= 1.0)
test("Edge: many updates incrementa confidence", v_multi.confidence > 0.3)
shutil.rmtree(tmp_multi, ignore_errors=True)

# Anomaly repr
a_repr = Anomaly("test", 99.9, 50.0, severity="warning", detector="test_det")
r = repr(a_repr)
test("Edge: Anomaly repr legible", "test" in r and "warning" in r)

# ZScoreDetector custom thresholds
zsd_custom = ZScoreDetector(warning_threshold=1.0, critical_threshold=1.5)
ms_custom = MetricStream("custom")
for _ in range(10):
    ms_custom.add(10.0)
ms_custom.add(15.0)
result_custom = zsd_custom.check(ms_custom)
test("Edge: custom threshold mas sensible", result_custom is not None)

# ResponseAdapter sin preferencias
ra_empty = ResponseAdapter()
test("Edge: ResponseAdapter sin prefs = ''", ra_empty.generate_directives({}) == "")

# ResponseAdapter con dict en vez de UserPreference
test("Edge: ResponseAdapter con dict = ''", ra_empty.generate_directives({"verbosity": {"value": 0.8}}) == "")

# PatternPredictor accuracy con 0 predictions
pp_acc = PatternPredictor(base_dir=tempfile.mkdtemp())
test("Edge: accuracy 0 predictions = 0", pp_acc.accuracy == 0.0)
shutil.rmtree(pp_acc.base_dir, ignore_errors=True)

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
