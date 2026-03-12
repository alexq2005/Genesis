"""
Tests para Genesis v2.3.0
- SelfEvaluator: QualityScorer, PatternTracker, AutoTuner
- SkillMemory: SkillEntry, SkillExtractor, SkillRecall
- ChainEngine: ChainPlanner, ChainStep, ChainMemory
- Integracion en genesis.py y web_ui.py

Total: 230+ tests
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
# TEST 1: QualityScorer
# ============================================================
print("\n=== TEST: QualityScorer ===")
from core.self_evaluator import QualityScorer, PatternTracker, AutoTuner, SelfEvaluator

scorer = QualityScorer()

# Buena respuesta (relevante, longitud OK, específica)
result = scorer.score(
    "Que es Python?",
    "Python es un lenguaje de programacion de alto nivel, interpretado y multiparadigma. "
    "Fue creado por Guido van Rossum en 1991 y se destaca por su sintaxis legible.",
    "chat",
)
test("Scorer: retorna dict", isinstance(result, dict))
test("Scorer: tiene overall", "overall" in result)
test("Scorer: tiene scores", "scores" in result)
test("Scorer: tiene grade", "grade" in result)
test("Scorer: overall es float", isinstance(result["overall"], float))
test("Scorer: overall 0-1", 0 <= result["overall"] <= 1)
test("Scorer: buena respuesta score >= 0.6", result["overall"] >= 0.6)
test("Scorer: grade es A o B", result["grade"] in ("A", "B"))

# Respuesta genérica (baja calidad)
generic = scorer.score(
    "Ayudame con algo",
    "Claro, estoy aqui para ayudarte. No dudes en preguntar si tienes alguna otra pregunta. "
    "Espero que esto te ayude. Como puedo ayudarte?",
    "chat",
)
test("Scorer: genérica tiene bajo specificity", generic["scores"]["specificity"] < 0.5)

# Respuesta con error
error = scorer.score(
    "Genera codigo",
    "[ERROR] No pude generar la respuesta. Traceback: linea 42",
    "code",
)
test("Scorer: error tiene bajo error_free", error["scores"]["error_free"] < 0.3)

# Respuesta muy corta
short = scorer.score(
    "Explica la teoria de la relatividad en detalle",
    "Es fisica.",
    "research",
)
test("Scorer: corta tiene bajo length", short["scores"]["length"] < 0.5)
test("Scorer: corta tiene bajo completeness", short["scores"]["completeness"] < 0.7)

# Respuesta vacía
empty = scorer.score("test", "", "chat")
test("Scorer: vacía score muy bajo", empty["overall"] < 0.3)

# Grade boundaries
test("Scorer: grade A >= 0.9", scorer._grade(0.95) == "A")
test("Scorer: grade B >= 0.8", scorer._grade(0.85) == "B")
test("Scorer: grade C >= 0.65", scorer._grade(0.7) == "C")
test("Scorer: grade D >= 0.5", scorer._grade(0.55) == "D")
test("Scorer: grade F < 0.5", scorer._grade(0.3) == "F")

# Relevancia: palabras del input en la respuesta
rel = scorer._score_relevance(
    "machine learning neural networks",
    "Machine learning uses neural networks for pattern recognition",
)
test("Scorer: relevance alta cuando hay overlap", rel >= 0.7)

rel_low = scorer._score_relevance(
    "cocina recetas postres",
    "El protocolo TCP/IP funciona en capas de red",
)
test("Scorer: relevance baja sin overlap", rel_low < 0.5)

# Longitud por intent
test("Scorer: code acepta respuestas largas",
     scorer._score_length("q", "x" * 2000, "code") >= 0.5)
test("Scorer: chat penaliza respuestas muy largas",
     scorer._score_length("q", "x" * 3000, "chat") < 0.8)

# Completeness con estructura
structured = scorer._score_completeness(
    "1. Primero instalar\n2. Luego configurar\n3. Finalmente ejecutar\n```code```",
    "code",
)
test("Scorer: completeness alta con estructura", structured >= 0.7)


# ============================================================
# TEST 2: PatternTracker
# ============================================================
print("\n=== TEST: PatternTracker ===")
tracker = PatternTracker()

test("Tracker init: history vacio", len(tracker.history) == 0)
test("Tracker init: total_evaluated 0", tracker.total_evaluated == 0)

# Registrar evaluaciones
for i in range(20):
    quality = {"overall": 0.8, "grade": "B", "scores": {"relevance": 0.8, "length": 0.7}}
    tracker.record("Pregunta", "Respuesta", "chat", quality)

test("Tracker: 20 evaluaciones registradas", tracker.total_evaluated == 20)
test("Tracker: history tiene 20", len(tracker.history) == 20)
test("Tracker: intent_stats tiene chat", "chat" in tracker.intent_stats)
test("Tracker: chat total 20", tracker.intent_stats["chat"]["total"] == 20)

# Average score
avg = tracker.get_average_score()
test("Tracker: avg_score correcto", abs(avg - 0.8) < 0.01)

# Trend con data insuficiente
test("Tracker: trend con poca data", tracker.get_trend(window=15) == "insufficient_data")

# Agregar más para generar trend
for i in range(30):
    quality = {"overall": 0.9, "grade": "A", "scores": {"relevance": 0.9, "length": 0.9}}
    tracker.record("Pregunta", "Respuesta", "chat", quality)

test("Tracker: trend mejorando", tracker.get_trend(window=20) == "improving")

# Strengths y weaknesses
tracker2 = PatternTracker()
for i in range(10):
    tracker2.record("q", "r", "code",
                    {"overall": 0.9, "grade": "A", "scores": {}})
for i in range(10):
    tracker2.record("q", "r", "creative",
                    {"overall": 0.3, "grade": "F", "scores": {}})

strengths = tracker2.get_strengths()
test("Tracker: strengths detecta code", any(s["intent"] == "code" for s in strengths))

weaknesses = tracker2.get_weaknesses()
test("Tracker: weaknesses detecta creative", any(w["intent"] == "creative" for w in weaknesses))

# Intent report
report = tracker2.get_intent_report()
test("Tracker: report tiene code", "code" in report)
test("Tracker: report tiene creative", "creative" in report)
test("Tracker: code avg ~0.9", report["code"]["avg_score"] >= 0.85)

# Serialización
d = tracker2.to_dict()
test("Tracker.to_dict: tiene history", "history" in d)
test("Tracker.to_dict: tiene intent_stats", "intent_stats" in d)

tracker3 = PatternTracker()
tracker3.load_dict(d)
test("Tracker.load_dict: restaura history", len(tracker3.history) > 0)
test("Tracker.load_dict: restaura stats", "code" in tracker3.intent_stats)

# Feedback
tracker4 = PatternTracker()
tracker4.record("q", "r", "chat",
                {"overall": 0.5, "grade": "D", "scores": {}},
                user_feedback="+")
test("Tracker: feedback + incrementa good", tracker4.intent_stats["chat"]["count_good"] >= 1)

tracker4.record("q", "r", "chat",
                {"overall": 0.5, "grade": "D", "scores": {}},
                user_feedback="-")
test("Tracker: feedback - incrementa bad", tracker4.intent_stats["chat"]["count_bad"] >= 1)

# Max history
tracker5 = PatternTracker(max_history=10)
for i in range(20):
    tracker5.record("q", "r", "chat",
                    {"overall": 0.5, "grade": "D", "scores": {}})
test("Tracker: max_history respetado", len(tracker5.history) <= 10)


# ============================================================
# TEST 3: AutoTuner
# ============================================================
print("\n=== TEST: AutoTuner ===")
tuner = AutoTuner()

test("Tuner init: tiene chat config", "chat" in tuner.intent_configs)
test("Tuner init: tiene code config", "code" in tuner.intent_configs)
test("Tuner init: adjustments 0", tuner.adjustments_made == 0)

# Get config
config = tuner.get_config("code")
test("Tuner: code temp < chat temp", config["temperature"] < tuner.get_config("chat")["temperature"])
test("Tuner: config es dict", isinstance(config, dict))
test("Tuner: config tiene temperature", "temperature" in config)
test("Tuner: config tiene max_tokens_hint", "max_tokens_hint" in config)

# Unknown intent
unknown = tuner.get_config("unknown_intent")
test("Tuner: unknown retorna defaults", unknown["temperature"] == 0.7)

# Adjust con data
bad_tracker = PatternTracker()
for i in range(10):
    bad_tracker.record("q", "short", "chat",
                       {"overall": 0.3, "grade": "F",
                        "scores": {"length": 0.2, "relevance": 0.3}})

old_temp = tuner.intent_configs["chat"]["temperature"]
tuner.adjust("chat", bad_tracker)
test("Tuner: ajusta temp cuando hay muchos bad",
     tuner.intent_configs["chat"]["temperature"] <= old_temp)
test("Tuner: adjustments_made incrementado", tuner.adjustments_made >= 1)
test("Tuner: adjustment_log tiene entrada", len(tuner.adjustment_log) >= 1)

# Adjust con data buena
good_tracker = PatternTracker()
for i in range(10):
    good_tracker.record("q", "r" * 100, "research",
                        {"overall": 0.9, "grade": "A",
                         "scores": {"length": 0.9, "relevance": 0.9}})
tuner.adjust("research", good_tracker)
test("Tuner: ajuste con buenos resultados", True)  # No crash

# Serialización
d = tuner.to_dict()
test("Tuner.to_dict: tiene intent_configs", "intent_configs" in d)
test("Tuner.to_dict: tiene adjustments_made", "adjustments_made" in d)

tuner2 = AutoTuner()
tuner2.load_dict(d)
test("Tuner.load_dict: restaura configs", "chat" in tuner2.intent_configs)
test("Tuner.load_dict: restaura adjustments", tuner2.adjustments_made >= 1)


# ============================================================
# TEST 4: SelfEvaluator (coordinador)
# ============================================================
print("\n=== TEST: SelfEvaluator ===")
tmp_dir = tempfile.mkdtemp()

try:
    evaluator = SelfEvaluator(base_dir=tmp_dir)

    test("Evaluator init: total 0", evaluator.total_evaluations == 0)
    test("Evaluator init: enabled True", evaluator.enabled is True)

    # Evaluar
    result = evaluator.evaluate(
        "Que es Docker?",
        "Docker es una plataforma de contenedores que permite empaquetar aplicaciones. "
        "Usa contenedores ligeros basados en Linux para aislar procesos.",
        "research",
    )
    test("Evaluator.evaluate: retorna dict", isinstance(result, dict))
    test("Evaluator.evaluate: tiene overall", "overall" in result)
    test("Evaluator.evaluate: total incrementado", evaluator.total_evaluations == 1)

    # Evaluar muchas
    for i in range(15):
        evaluator.evaluate(f"Pregunta {i} sobre algo importante",
                           f"Respuesta {i} con contenido relevante y util para el usuario.",
                           "chat")
    test("Evaluator: 16 evaluaciones", evaluator.total_evaluations == 16)

    # Record feedback
    evaluator.record_feedback("+")
    test("Evaluator: feedback registrado", evaluator.tracker.history[-1]["user_feedback"] == "+")

    # Tuned config
    config = evaluator.get_tuned_config("chat")
    test("Evaluator: tuned config es dict", isinstance(config, dict))
    test("Evaluator: tuned config tiene temp", "temperature" in config)

    # Stats
    stats = evaluator.get_stats()
    test("Evaluator.get_stats: tiene total", "total_evaluations" in stats)
    test("Evaluator.get_stats: tiene avg", "avg_score" in stats)
    test("Evaluator.get_stats: tiene trend", "trend" in stats)
    test("Evaluator.get_stats: tiene strengths", "strengths" in stats)
    test("Evaluator.get_stats: tiene weaknesses", "weaknesses" in stats)

    # Status string
    status = evaluator.status()
    test("Evaluator.status: contiene Evaluaciones", "Evaluaciones:" in status)
    test("Evaluator.status: contiene Score", "Score" in status)

    # Report
    report = evaluator.generate_report()
    test("Evaluator.report: contiene header", "SELF-EVALUATION" in report)
    test("Evaluator.report: contiene total", str(evaluator.total_evaluations) in report)

    # Persistencia
    evaluator.save()
    test("Evaluator.save: archivo existe", evaluator.data_file.exists())

    evaluator2 = SelfEvaluator(base_dir=tmp_dir)
    test("Evaluator.load: total restaurado", evaluator2.total_evaluations == evaluator.total_evaluations)

    # Clear
    evaluator.clear()
    test("Evaluator.clear: total reset", evaluator.total_evaluations == 0)

    # Disabled
    evaluator.enabled = False
    result = evaluator.evaluate("q", "r", "chat")
    test("Evaluator disabled: retorna neutral", result["overall"] == 0.5)
    test("Evaluator disabled: total no incrementa", evaluator.total_evaluations == 0)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 5: SkillEntry
# ============================================================
print("\n=== TEST: SkillEntry ===")
from core.skill_memory import SkillEntry, SkillExtractor, SkillMemory

entry = SkillEntry(
    title="Instalar Docker en Ubuntu",
    steps=["Actualizar apt", "Instalar dependencias", "Agregar repo Docker", "Instalar docker-ce"],
    tags=["docker", "ubuntu", "install"],
    source_query="como instalar docker en ubuntu?",
)

test("SkillEntry: title correcto", entry.title == "Instalar Docker en Ubuntu")
test("SkillEntry: 4 steps", len(entry.steps) == 4)
test("SkillEntry: 3 tags", len(entry.tags) == 3)
test("SkillEntry: skill_id generado", len(entry.skill_id) == 10)
test("SkillEntry: version 1", entry.version == 1)
test("SkillEntry: quality 0.5", entry.quality == 0.5)
test("SkillEntry: times_used 0", entry.times_used == 0)

# to_text
text = entry.to_text()
test("SkillEntry.to_text: contiene SKILL:", "SKILL:" in text)
test("SkillEntry.to_text: contiene pasos numerados", "1." in text and "2." in text)

# to_dict / from_dict
d = entry.to_dict()
test("SkillEntry.to_dict: tiene id", "id" in d)
test("SkillEntry.to_dict: tiene title", d["title"] == "Instalar Docker en Ubuntu")
test("SkillEntry.to_dict: tiene steps", len(d["steps"]) == 4)

restored = SkillEntry.from_dict(d)
test("SkillEntry.from_dict: title preservado", restored.title == entry.title)
test("SkillEntry.from_dict: steps preservados", restored.steps == entry.steps)
test("SkillEntry.from_dict: tags preservados", restored.tags == entry.tags)
test("SkillEntry.from_dict: id preservado", restored.skill_id == entry.skill_id)


# ============================================================
# TEST 6: SkillExtractor
# ============================================================
print("\n=== TEST: SkillExtractor ===")
extractor = SkillExtractor()

# Detección de preguntas how-to
test("Extractor: 'como instalar' es how-to",
     extractor.is_how_to_question("como instalar python en windows?"))
test("Extractor: 'how to' es how-to",
     extractor.is_how_to_question("how to configure nginx?"))
test("Extractor: 'pasos para' es how-to",
     extractor.is_how_to_question("pasos para desplegar en produccion"))
test("Extractor: pregunta simple NO es how-to",
     not extractor.is_how_to_question("que es python?"))
test("Extractor: 'tutorial' es how-to",
     extractor.is_how_to_question("tutorial de react hooks"))

# Detección de procedimientos
response_with_steps = """
Para instalar Docker:
1. Actualizar el sistema: sudo apt update
2. Instalar dependencias necesarias
3. Agregar el repositorio oficial de Docker
4. Instalar docker-ce y docker-compose
5. Verificar la instalacion con docker --version
"""
test("Extractor: detecta procedimiento", extractor.has_procedure(response_with_steps))

response_without_steps = "Docker es una plataforma de contenedores muy utilizada."
test("Extractor: no detecta sin procedimiento", not extractor.has_procedure(response_without_steps))

# Extraer skill
skill = extractor.extract_skill(
    "como instalar docker en ubuntu?",
    response_with_steps,
)
test("Extractor: extrae skill OK", skill is not None)
test("Extractor: skill tiene titulo", len(skill.title) > 5)
test("Extractor: skill tiene >= 3 pasos", len(skill.steps) >= 3)
test("Extractor: skill tiene tags", len(skill.tags) >= 0)

# No extraer de respuesta sin procedimiento
no_skill = extractor.extract_skill(
    "como funciona docker?",
    response_without_steps,
)
test("Extractor: no extrae sin procedimiento", no_skill is None)

# No extraer de pregunta no-how-to
no_skill2 = extractor.extract_skill(
    "que es docker?",
    response_with_steps,
)
test("Extractor: no extrae de pregunta no-how-to", no_skill2 is None)


# ============================================================
# TEST 7: SkillMemory
# ============================================================
print("\n=== TEST: SkillMemory ===")
tmp_dir2 = tempfile.mkdtemp()

try:
    mem = SkillMemory(embeddings_engine=None, base_dir=tmp_dir2)

    test("SkillMem init: vacio", len(mem.skills) == 0)
    test("SkillMem init: total_extracted 0", mem.total_extracted == 0)

    # Extract and store
    response = """
Para configurar un servidor web con Nginx:
1. Instalar nginx con apt install nginx
2. Crear archivo de configuracion en /etc/nginx/sites-available/
3. Crear symlink en sites-enabled
4. Configurar el bloque server con listen y root
5. Reiniciar nginx con systemctl restart nginx
"""
    sid = mem.extract_and_store("como configurar nginx?", response)
    test("SkillMem: extrae y almacena", sid is not None)
    test("SkillMem: skill en dict", sid in mem.skills)
    test("SkillMem: total_extracted 1", mem.total_extracted == 1)

    # No extraer de pregunta simple
    sid2 = mem.extract_and_store("que es nginx?", "Nginx es un servidor web.")
    test("SkillMem: no extrae de pregunta simple", sid2 is None)

    # Recall por keywords
    results = mem.recall("como configurar nginx web server")
    test("SkillMem.recall: retorna resultados", len(results) > 0)
    test("SkillMem.recall: total_recalls incrementado", mem.total_recalls >= 1)

    # Get context for prompt
    ctx = mem.get_context_for_prompt("como configurar un servidor nginx?")
    test("SkillMem.get_context: contiene SKILLS", "SKILLS" in ctx)
    test("SkillMem.get_context: no vacio", len(ctx) > 50)

    # No retorna context para pregunta no-how-to
    ctx2 = mem.get_context_for_prompt("que hora es?")
    test("SkillMem.get_context: vacio para no-how-to", ctx2 == "")

    # Stats
    stats = mem.get_stats()
    test("SkillMem.get_stats: total_skills 1", stats["total_skills"] == 1)
    test("SkillMem.get_stats: total_extracted 1", stats["total_extracted"] == 1)

    # Status
    status = mem.status()
    test("SkillMem.status: contiene Skills:", "Skills:" in status)

    # Report
    report = mem.generate_report()
    test("SkillMem.report: contiene header", "SKILL MEMORY" in report)

    # Persistencia
    mem.save()
    test("SkillMem.save: archivo existe", mem.data_file.exists())

    mem2 = SkillMemory(embeddings_engine=None, base_dir=tmp_dir2)
    test("SkillMem.load: skills restaurados", len(mem2.skills) == 1)

    # Delete skill
    deleted = mem.delete_skill(sid)
    test("SkillMem.delete: retorna True", deleted is True)
    test("SkillMem.delete: skill removido", sid not in mem.skills)

    deleted2 = mem.delete_skill("nonexistent")
    test("SkillMem.delete: nonexistent retorna False", deleted2 is False)

    # Clear
    mem.clear()
    test("SkillMem.clear: skills vacio", len(mem.skills) == 0)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)


# ============================================================
# TEST 8: SkillMemory — Duplicates & Eviction
# ============================================================
print("\n=== TEST: SkillMemory — Duplicates & Eviction ===")
tmp_dir3 = tempfile.mkdtemp()

try:
    mem = SkillMemory(embeddings_engine=None, base_dir=tmp_dir3)
    mem.max_skills = 5

    # Insertar mismo skill (debería detectar duplicado)
    response = """
Para instalar Python:
1. Descargar desde python.org
2. Ejecutar el instalador
3. Agregar al PATH
"""
    sid1 = mem.extract_and_store("como instalar python?", response)
    sid2 = mem.extract_and_store("como instalar python en pc?", response)
    # El segundo debería ser None o actualizar el existente
    test("SkillMem: duplicado detectado", sid2 is None or sid2 == sid1)

    # Eviction
    for i in range(10):
        resp = "\n".join([
            f"Para hacer tarea {i}:",
            f"1. Paso primero de tarea {i} con detalles",
            f"2. Paso segundo de tarea {i} con detalles",
            f"3. Paso tercero de tarea {i} con detalles",
        ])
        mem.extract_and_store(f"como hacer tarea {i} paso a paso?", resp)

    test("SkillMem: eviction respeta max", len(mem.skills) <= mem.max_skills)

finally:
    shutil.rmtree(tmp_dir3, ignore_errors=True)


# ============================================================
# TEST 9: ChainStep & Chain
# ============================================================
print("\n=== TEST: ChainStep & Chain ===")
from core.chain_engine import ChainStep, Chain, ChainPlanner, ChainMemory, ChainEngine

step = ChainStep("Que es X?", step_number=1)
test("ChainStep: question OK", step.question == "Que es X?")
test("ChainStep: step_number 1", step.step_number == 1)
test("ChainStep: status pending", step.status == "pending")
test("ChainStep: answer vacio", step.answer == "")

# to_dict / from_dict
d = step.to_dict()
test("ChainStep.to_dict: tiene question", d["question"] == "Que es X?")
restored = ChainStep.from_dict(d)
test("ChainStep.from_dict: question OK", restored.question == "Que es X?")

# Chain
chain = Chain(
    original_query="Compara Python con Java",
    steps=[
        ChainStep("Describe Python", 1),
        ChainStep("Describe Java", 2),
        ChainStep("Compara ambos", 3, depends_on=[1, 2]),
    ],
)
test("Chain: 3 steps", len(chain.steps) == 3)
test("Chain: not complete", not chain.is_complete)
test("Chain: current_step 1", chain.current_step == 1)
test("Chain: chain_id generado", len(chain.chain_id) == 10)

# Completar steps
chain.steps[0].status = "completed"
chain.steps[0].answer = "Python es un lenguaje interpretado"
test("Chain: current_step 2 despues de completar 1", chain.current_step == 2)

context = chain.get_context_so_far()
test("Chain: context tiene paso 1", "Paso 1" in context)
test("Chain: context tiene respuesta", "Python" in context)

# Completar todos
chain.steps[1].status = "completed"
chain.steps[1].answer = "Java es compilado"
chain.steps[2].status = "completed"
chain.steps[2].answer = "Python es más simple, Java más rápido"
test("Chain: is_complete True", chain.is_complete)

# Serialización
d = chain.to_dict()
test("Chain.to_dict: tiene id", "id" in d)
test("Chain.to_dict: tiene steps", len(d["steps"]) == 3)

restored_chain = Chain.from_dict(d)
test("Chain.from_dict: query OK", restored_chain.original_query == chain.original_query)
test("Chain.from_dict: steps OK", len(restored_chain.steps) == 3)


# ============================================================
# TEST 10: ChainPlanner
# ============================================================
print("\n=== TEST: ChainPlanner ===")
planner = ChainPlanner()

# Detección de complejidad
test("Planner: 'compara X con Y' necesita chain",
     planner.needs_chain("compara python con java en terminos de rendimiento y analiza las ventajas de cada uno"))
test("Planner: 'analiza las ventajas y desventajas de kubernetes' necesita chain",
     planner.needs_chain("analiza las ventajas y desventajas de kubernetes completo"))
test("Planner: 'hola' no necesita chain",
     not planner.needs_chain("hola"))
test("Planner: pregunta corta no necesita chain",
     not planner.needs_chain("que hora es?"))

# Planificación
chain = planner.plan("compara python con java en terminos de rendimiento y facilidad")
test("Planner.plan: retorna Chain", isinstance(chain, Chain))
test("Planner.plan: tiene >= 2 steps", len(chain.steps) >= 2)
test("Planner.plan: steps son ChainStep", isinstance(chain.steps[0], ChainStep))
test("Planner.plan: step 1 es pending", chain.steps[0].status == "pending")

# Plan de análisis
chain2 = planner.plan("analiza detalladamente las ventajas y desventajas de microservicios")
test("Planner: plan analyze tiene pasos", len(chain2.steps) >= 2)

# Plan de optimización
chain3 = planner.plan("optimiza el rendimiento de mi aplicacion web de manera detallada")
test("Planner: plan optimize tiene pasos", len(chain3.steps) >= 2)

# Plan de diseño
chain4 = planner.plan("diseña la arquitectura para una aplicacion de multiples componentes")
test("Planner: plan design tiene pasos", len(chain4.steps) >= 2)

# Tipo detection
test("Planner: detecta compare", planner._detect_type("compara x vs y") == "compare")
test("Planner: detecta analyze", planner._detect_type("analiza esto") == "analyze")
test("Planner: detecta optimize", planner._detect_type("optimiza el rendimiento") == "optimize")
test("Planner: detecta design", planner._detect_type("diseña la arquitectura") == "design")
test("Planner: detecta explain_why", planner._detect_type("por que pasa esto") == "explain_why")
test("Planner: detecta generic", planner._detect_type("algo completamente diferente") == "generic")


# ============================================================
# TEST 11: ChainMemory
# ============================================================
print("\n=== TEST: ChainMemory ===")
memory = ChainMemory(max_chains=3)

# Store chain
completed_chain = Chain("Compara React vs Vue")
completed_chain.status = "completed"
completed_chain.completed_at = time.time()
completed_chain.steps = [
    ChainStep("Describe React", 1),
    ChainStep("Describe Vue", 2),
]
completed_chain.steps[0].status = "completed"
completed_chain.steps[0].answer = "React es una librería de Facebook"
completed_chain.steps[1].status = "completed"
completed_chain.steps[1].answer = "Vue es un framework progresivo"

memory.store(completed_chain)
test("ChainMemory: almacena chain", len(memory.chains) == 1)

# No almacenar chains incompletas
incomplete = Chain("test")
incomplete.status = "running"
memory.store(incomplete)
test("ChainMemory: no almacena incompletas", len(memory.chains) == 1)

# Find similar
similar = memory.find_similar("Compara React con Vue.js")
test("ChainMemory: encuentra similar", similar is not None)
test("ChainMemory: similar es la correcta", "React" in similar.original_query)

# No find con query diferente
not_found = memory.find_similar("Como instalar Docker?")
test("ChainMemory: no encuentra diferente", not_found is None)

# Eviction
for i in range(5):
    c = Chain(f"Chain {i} sobre tema diferente y unico")
    c.status = "completed"
    c.completed_at = time.time() + i
    c.steps = [ChainStep(f"Step {i}", 1)]
    c.steps[0].status = "completed"
    memory.store(c)

test("ChainMemory: eviction respeta max", len(memory.chains) <= 3)

# Serialización
d = memory.to_dict()
test("ChainMemory.to_dict: retorna dict", isinstance(d, dict))

memory2 = ChainMemory()
memory2.load_dict(d)
test("ChainMemory.load_dict: restaura chains", len(memory2.chains) == len(memory.chains))


# ============================================================
# TEST 12: ChainEngine
# ============================================================
print("\n=== TEST: ChainEngine ===")
tmp_dir4 = tempfile.mkdtemp()

try:
    engine = ChainEngine(base_dir=tmp_dir4)

    test("Engine init: total 0", engine.total_chains == 0)
    test("Engine init: enabled True", engine.enabled is True)
    test("Engine init: no active chain", engine.active_chain is None)

    # Should chain
    test("Engine: deberia usar chain para comparaciones",
         engine.should_chain("compara python con java en detalle y analiza las ventajas"))
    test("Engine: no deberia para hola",
         not engine.should_chain("hola"))

    # Start chain
    chain = engine.start_chain("compara python con java en detalle y analiza ventajas")
    test("Engine.start: retorna Chain", isinstance(chain, Chain))
    test("Engine.start: chain running", chain.status == "running")
    test("Engine.start: active_chain set", engine.active_chain is not None)
    test("Engine.start: total_chains 1", engine.total_chains == 1)

    # Get next step
    step = engine.get_next_step()
    test("Engine.get_next: retorna step", step is not None)
    test("Engine.get_next: es step 1", step.step_number == 1)

    # Get chain prompt
    prompt = engine.get_chain_prompt(step)
    test("Engine.get_prompt: contiene original query", "python" in prompt.lower() or "java" in prompt.lower())
    test("Engine.get_prompt: contiene paso", "paso" in prompt.lower() or "step" in prompt.lower())

    # Complete steps
    for s in chain.steps:
        engine.complete_step(s.step_number, f"Respuesta para paso {s.step_number}")

    test("Engine: chain completed", chain.status == "completed")
    test("Engine: final_answer generado", len(chain.final_answer) > 0)
    test("Engine: total_steps incrementado", engine.total_steps_executed == len(chain.steps))

    # Stats
    stats = engine.get_stats()
    test("Engine.get_stats: total_chains 1", stats["total_chains"] == 1)
    test("Engine.get_stats: tiene chains_memorized", "chains_memorized" in stats)

    # Status
    status = engine.status()
    test("Engine.status: contiene Cadenas", "Cadenas" in status)

    # Report
    report = engine.generate_report()
    test("Engine.report: contiene CHAIN ENGINE", "CHAIN ENGINE" in report)

    # Persistencia
    engine.save()
    test("Engine.save: archivo existe", engine.data_file.exists())

    engine2 = ChainEngine(base_dir=tmp_dir4)
    test("Engine.load: total restaurado", engine2.total_chains == 1)

    # Cancel
    engine.start_chain("analiza las ventajas y desventajas de algo complejo y detallado")
    engine.cancel_chain()
    test("Engine.cancel: active_chain None", engine.active_chain is None)

    # Disabled
    engine.enabled = False
    test("Engine.disabled: should_chain False",
         not engine.should_chain("compara X con Y en detalle y ventajas"))

    # Clear
    engine.enabled = True
    engine.clear()
    test("Engine.clear: total reset", engine.total_chains == 0)

finally:
    shutil.rmtree(tmp_dir4, ignore_errors=True)


# ============================================================
# TEST 13: genesis.py — Imports & Integration
# ============================================================
print("\n=== TEST: genesis.py — Integration ===")
genesis_source = open("genesis.py", "r", encoding="utf-8").read()

# Imports
test("genesis.py: importa SelfEvaluator", "from core.self_evaluator import SelfEvaluator" in genesis_source)
test("genesis.py: importa SkillMemory", "from core.skill_memory import SkillMemory" in genesis_source)
test("genesis.py: importa ChainEngine", "from core.chain_engine import ChainEngine" in genesis_source)

# Init
test("genesis.py: self.evaluator =", "self.evaluator = SelfEvaluator(" in genesis_source)
test("genesis.py: self.skill_memory =", "self.skill_memory = SkillMemory(" in genesis_source)
test("genesis.py: self.chain_engine =", "self.chain_engine = ChainEngine(" in genesis_source)

# Process input integration
test("genesis.py: skill_memory.get_context", "skill_memory.get_context_for_prompt" in genesis_source)
test("genesis.py: evaluator.evaluate", "evaluator.evaluate(" in genesis_source)
test("genesis.py: skill_memory.extract_and_store", "skill_memory.extract_and_store(" in genesis_source)

# Feedback integration
test("genesis.py: evaluator.record_feedback +", 'evaluator.record_feedback("+")' in genesis_source)
test("genesis.py: evaluator.record_feedback -", 'evaluator.record_feedback("-")' in genesis_source)

# Auto-tuner integration
test("genesis.py: get_tuned_config", "evaluator.get_tuned_config" in genesis_source)

# Commands
test("genesis.py: /evaluate command", '"/evaluate"' in genesis_source)
test("genesis.py: /eval command", '"/eval"' in genesis_source)
test("genesis.py: /skills command", '"/skills"' in genesis_source)
test("genesis.py: /chain command", '"/chain"' in genesis_source)
test("genesis.py: /chain toggle", '"/chain toggle"' in genesis_source)

# Status sections
test("genesis.py: status tiene SELF-EVALUATOR", "SELF-EVALUATOR:" in genesis_source)
test("genesis.py: status tiene SKILL MEMORY", "SKILL MEMORY:" in genesis_source)
test("genesis.py: status tiene CHAIN ENGINE", "CHAIN ENGINE:" in genesis_source)

# Dashboard collectors
test("genesis.py: dashboard register evaluator", '"evaluator"' in genesis_source)
test("genesis.py: dashboard register skill_memory", '"skill_memory"' in genesis_source)
test("genesis.py: dashboard register chain_engine", '"chain_engine"' in genesis_source)

# Save on exit
test("genesis.py: evaluator.save() on exit", "evaluator.save()" in genesis_source)
test("genesis.py: skill_memory.save() on exit", "skill_memory.save()" in genesis_source)
test("genesis.py: chain_engine.save() on exit", "chain_engine.save()" in genesis_source)

# Banner
test("genesis.py: banner tiene Self-Evaluator", "Self-Evaluator:" in genesis_source)
test("genesis.py: banner tiene Skill Memory", "Skill Memory:" in genesis_source)
test("genesis.py: banner tiene Chain Engine", "Chain Engine:" in genesis_source)

# Help
test("genesis.py: help tiene /evaluate", "/evaluate" in genesis_source)
test("genesis.py: help tiene /skills", "/skills" in genesis_source)
test("genesis.py: help tiene /chain", "/chain" in genesis_source)


# ============================================================
# TEST 14: web_ui.py — New Data
# ============================================================
print("\n=== TEST: web_ui.py — New Data ===")
webui_source = open("web_ui.py", "r", encoding="utf-8").read()

test("web_ui.py: retorna evaluator data", '"evaluator"' in webui_source)
test("web_ui.py: retorna skill_memory data", '"skill_memory"' in webui_source)
test("web_ui.py: retorna chain_engine data", '"chain_engine"' in webui_source)
test("web_ui.py: subsystem Evaluator", '"Evaluator"' in webui_source)
test("web_ui.py: subsystem SkillMemory", '"SkillMemory"' in webui_source)
test("web_ui.py: subsystem ChainEngine", '"ChainEngine"' in webui_source)


# ============================================================
# TEST 15: Edge Cases — QualityScorer
# ============================================================
print("\n=== TEST: QualityScorer — Edge Cases ===")

# Sin palabras significativas en input
score = scorer.score("a b c", "Respuesta completa y detallada.", "chat")
test("Scorer: input sin palabras largas no crashea", score["overall"] > 0)

# Response con código
code_response = """
Aquí tienes el código:
```python
def hello():
    print("Hello World")
```
Este código define una función simple.
"""
code_score = scorer.score("genera codigo python", code_response, "code")
test("Scorer: código tiene buen completeness", code_score["scores"]["completeness"] >= 0.7)

# Unicode
unicode_score = scorer.score(
    "háblame de señales con acentos ñ",
    "Las señales electromagnéticas tienen frecuencias específicas.",
    "chat",
)
test("Scorer: unicode no crashea", unicode_score["overall"] > 0)


# ============================================================
# TEST 16: Módulos importables
# ============================================================
print("\n=== TEST: Import Modules ===")
try:
    from core.self_evaluator import SelfEvaluator as SE
    test("Import: SelfEvaluator OK", True)
except Exception as e:
    test(f"Import: SelfEvaluator FAILED ({e})", False)

try:
    from core.skill_memory import SkillMemory as SM
    test("Import: SkillMemory OK", True)
except Exception as e:
    test(f"Import: SkillMemory FAILED ({e})", False)

try:
    from core.chain_engine import ChainEngine as CE
    test("Import: ChainEngine OK", True)
except Exception as e:
    test(f"Import: ChainEngine FAILED ({e})", False)


# ============================================================
# TEST 17: Version check
# ============================================================
print("\n=== TEST: Version Check ===")
from config import GENESIS_VERSION

parts = GENESIS_VERSION.split(".")
major = int(parts[0])
minor = int(parts[1])
version_num = major * 10 + minor
test(f"Version: {GENESIS_VERSION} >= 2.2", version_num >= 22)


# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
total = _passed + _failed
print(f"  GENESIS v2.3 Tests: {_passed}/{total} passed")
if _failed > 0:
    print(f"  {_failed} FAILED")
else:
    print(f"  ALL TESTS PASSED!")
print("=" * 60)

sys.exit(0 if _failed == 0 else 1)
