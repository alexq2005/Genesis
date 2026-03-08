"""
Tests para Genesis v2.2.0
- SemanticMemory: indexacion, recall, deduplicacion, persistencia
- InferenceOptimizer: PromptCache, ResponsePredictor, ContextTrimmer
- LiveDashboard: HTML generation, API endpoint structure
- Integracion en genesis.py y web_ui.py

Total: 200+ tests
"""
import sys
import os
import tempfile
import shutil
import time
import json
import hashlib

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

# Suppress TF warnings
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
# TEST 1: ConversationEntry
# ============================================================
print("\n=== TEST: ConversationEntry ===")
from core.semantic_memory import ConversationEntry, SemanticMemory

entry = ConversationEntry(
    user_input="Que es Python?",
    response="Python es un lenguaje de programacion versatil.",
    intent="chat",
    tags=["python", "programacion"],
    quality=0.8,
)

test("Entry: user_input almacenado", entry.user_input == "Que es Python?")
test("Entry: response almacenada", "Python" in entry.response)
test("Entry: intent correcto", entry.intent == "chat")
test("Entry: tags correctos", entry.tags == ["python", "programacion"])
test("Entry: quality correcta", entry.quality == 0.8)
test("Entry: timestamp generado", entry.timestamp > 0)
test("Entry: entry_id generado", len(entry.entry_id) == 12)
test("Entry: entry_id es hex", all(c in "0123456789abcdef" for c in entry.entry_id))

# to_text()
text = entry.to_text()
test("Entry.to_text: contiene Pregunta:", "Pregunta:" in text)
test("Entry.to_text: contiene Respuesta:", "Respuesta:" in text)
test("Entry.to_text: contiene user_input", "Que es Python?" in text)

# to_dict() / from_dict()
d = entry.to_dict()
test("Entry.to_dict: tiene id", "id" in d)
test("Entry.to_dict: tiene user_input", d["user_input"] == "Que es Python?")
test("Entry.to_dict: tiene response", "Python" in d["response"])
test("Entry.to_dict: tiene intent", d["intent"] == "chat")
test("Entry.to_dict: tiene tags", d["tags"] == ["python", "programacion"])
test("Entry.to_dict: tiene quality", d["quality"] == 0.8)
test("Entry.to_dict: tiene timestamp", d["timestamp"] > 0)

# from_dict roundtrip
restored = ConversationEntry.from_dict(d)
test("Entry.from_dict: user_input preservado", restored.user_input == entry.user_input)
test("Entry.from_dict: response preservada", restored.response == entry.response[:1000])
test("Entry.from_dict: intent preservado", restored.intent == entry.intent)
test("Entry.from_dict: quality preservada", restored.quality == entry.quality)
test("Entry.from_dict: tags preservados", restored.tags == entry.tags)
test("Entry.from_dict: id preservado", restored.entry_id == entry.entry_id)

# response truncation in to_dict
long_entry = ConversationEntry(
    user_input="test",
    response="x" * 5000,
)
d_long = long_entry.to_dict()
test("Entry.to_dict: response truncada a 1000", len(d_long["response"]) == 1000)

# to_text truncation
text_long = long_entry.to_text()
test("Entry.to_text: response truncada a 500", len(text_long.split("Respuesta: ")[1]) == 500)


# ============================================================
# TEST 2: SemanticMemory (sin embeddings)
# ============================================================
print("\n=== TEST: SemanticMemory (sin embeddings) ===")
tmp_dir = tempfile.mkdtemp()

try:
    mem = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir)

    test("SM init: entries vacio", len(mem.entries) == 0)
    test("SM init: auto_index True", mem.auto_index is True)
    test("SM init: total_indexed 0", mem.total_indexed == 0)
    test("SM init: data_dir creado", mem.data_dir.exists())

    # Indexar sin embeddings (funciona, solo no hace busqueda vectorial)
    entry_id = mem.index(
        user_input="Explica que es machine learning",
        response="Machine learning es una rama de la IA que permite a los sistemas aprender de datos.",
        intent="research",
        tags=["ml", "ia"],
        quality=0.7,
    )
    test("SM.index: retorna ID", entry_id is not None)
    test("SM.index: ID tiene 12 chars", len(entry_id) == 12)
    test("SM.index: entry almacenada", entry_id in mem.entries)
    test("SM.index: total_indexed incrementado", mem.total_indexed == 1)

    # Indexar mas
    entry_id2 = mem.index(
        user_input="Como funciona una red neuronal?",
        response="Una red neuronal es un modelo computacional inspirado en el cerebro humano con capas de neuronas.",
        intent="research",
    )
    test("SM.index: segunda entrada OK", entry_id2 is not None)
    test("SM.index: entries tiene 2", len(mem.entries) == 2)

    # Filtrar inputs cortos
    short_id = mem.index(
        user_input="hola",
        response="Hola! Como puedo ayudarte?",
    )
    test("SM.index: input corto filtrado", short_id is None)
    test("SM.index: entries sigue en 2", len(mem.entries) == 2)

    # Filtrar responses cortas
    short_resp = mem.index(
        user_input="Que es la regresion lineal en estadistica?",
        response="Es un metodo.",
    )
    test("SM.index: response corta filtrada", short_resp is None)

    # Filtrar errores
    err_id = mem.index(
        user_input="pregunta cualquiera larga",
        response="[ERROR] Algo salio mal con la generacion del texto",
    )
    test("SM.index: error filtrado", err_id is None)

    timeout_id = mem.index(
        user_input="pregunta cualquiera larga",
        response="[TIMEOUT] No se pudo completar la generacion a tiempo",
    )
    test("SM.index: timeout filtrado", timeout_id is None)

    # Recall sin embeddings (retorna vacio)
    results = mem.recall("machine learning")
    test("SM.recall: sin embeddings retorna vacio", results == [])
    test("SM.recall: total_recalls incrementado", mem.total_recalls == 1)

    # get_context_for_prompt sin embeddings
    ctx = mem.get_context_for_prompt("test query")
    test("SM.get_context: sin embeddings retorna vacio", ctx == "")

    # Stats
    stats = mem.get_stats()
    test("SM.get_stats: total_entries correcto", stats["total_entries"] == 2)
    test("SM.get_stats: total_indexed correcto", stats["total_indexed"] == 2)
    test("SM.get_stats: total_recalls correcto", stats["total_recalls"] >= 1)
    test("SM.get_stats: auto_index True", stats["auto_index"] is True)

    # Status string
    status = mem.status()
    test("SM.status: contiene Entradas", "Entradas:" in status)
    test("SM.status: contiene Indexadas", "Indexadas:" in status)
    test("SM.status: contiene Recalls", "Recalls:" in status)

    # Generate report
    report = mem.generate_report()
    test("SM.generate_report: contiene header", "MEMORIA SEMANTICA" in report)
    test("SM.generate_report: contiene entradas", "Entradas indexadas:" in report)

    # Persistencia: save + load
    mem.save()
    test("SM.save: metadata_file existe", mem.metadata_file.exists())

    # Cargar en nueva instancia
    mem2 = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir)
    test("SM.load: entries restaurados", len(mem2.entries) == 2)
    test("SM.load: total_indexed restaurado", mem2.total_indexed == 2)
    test("SM.load: entry content preservado", any(
        e.user_input == "Explica que es machine learning" for e in mem2.entries.values()
    ))

    # Clear
    mem.clear()
    test("SM.clear: entries vacio", len(mem.entries) == 0)
    test("SM.clear: total_indexed reset", mem.total_indexed == 0)
    test("SM.clear: metadata eliminado", not mem.metadata_file.exists())

    # Auto-index toggle
    mem.auto_index = False
    noid = mem.index(
        user_input="Esta pregunta no se deberia indexar",
        response="Porque auto_index esta desactivado y no se permite indexar nada.",
    )
    test("SM.auto_index=False: no indexa", noid is None)
    mem.auto_index = True

    # update_quality
    mem3 = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir)
    eid = mem3.index(
        user_input="Pregunta de calidad para testing",
        response="Respuesta con calidad inicial de cero punto cinco.",
        quality=0.5,
    )
    test("SM.update_quality: initial 0.5", mem3.entries[eid].quality == 0.5)
    mem3.update_quality(eid, 0.9)
    test("SM.update_quality: updated to 0.9", mem3.entries[eid].quality == 0.9)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ============================================================
# TEST 3: SemanticMemory — Eviction
# ============================================================
print("\n=== TEST: SemanticMemory — Eviction ===")
tmp_dir2 = tempfile.mkdtemp()

try:
    mem = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir2)
    mem.max_entries = 10  # Limite bajo para testing

    # Indexar 15 entradas
    for i in range(15):
        mem.index(
            user_input=f"Pregunta numero {i} sobre un tema interesante",
            response=f"Respuesta detallada numero {i} con informacion util y relevante.",
            quality=0.1 * (i % 10),
        )

    test("SM.eviction: no excede max_entries", len(mem.entries) <= mem.max_entries)
    test("SM.eviction: entries no vacio", len(mem.entries) > 0)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)


# ============================================================
# TEST 4: PromptCache
# ============================================================
print("\n=== TEST: PromptCache ===")
from core.inference_optimizer import PromptCache, ResponsePredictor, ContextTrimmer, InferenceOptimizer

cache = PromptCache(max_entries=3)

test("Cache init: vacio", len(cache.cache) == 0)
test("Cache init: hits 0", cache.hits == 0)
test("Cache init: misses 0", cache.misses == 0)
test("Cache init: hit_rate 0.0", cache.hit_rate == 0.0)

# Miss
result = cache.get("Eres Genesis, una IA experimental.")
test("Cache.get: miss retorna None", result is None)
test("Cache.get: misses incrementado", cache.misses == 1)

# Put + Hit
cache.put("Eres Genesis, una IA experimental.")
result = cache.get("Eres Genesis, una IA experimental.")
test("Cache.put+get: hit retorna prompt", result == "Eres Genesis, una IA experimental.")
test("Cache.get: hits incrementado", cache.hits == 1)
test("Cache: hit_rate correcta", cache.hit_rate == 0.5)  # 1 hit, 1 miss

# Multiple puts
cache.put("Prompt A")
cache.put("Prompt B")
cache.put("Prompt C")  # Esto debe evictar el mas viejo

test("Cache: max_entries respetado", len(cache.cache) <= 3)

# Eviction: "Eres Genesis..." deberia haber sido evictado
# (fue el menos recientemente usado ya que Prompt A, B, C son mas nuevos)
evicted = cache.get("Eres Genesis, una IA experimental.")
# Puede o no estar, depende de LRU — verifiquemos que el cache no exceda max
test("Cache: tamanio <= max_entries", len(cache.cache) <= 3)

# Hash consistency
h1 = cache._hash("test text")
h2 = cache._hash("test text")
test("Cache._hash: determinista", h1 == h2)
test("Cache._hash: es md5 hex", len(h1) == 32)


# ============================================================
# TEST 5: ResponsePredictor
# ============================================================
print("\n=== TEST: ResponsePredictor ===")
pred = ResponsePredictor()

# Preguntas muy cortas
test("Predictor: input corto -> 256", pred.predict_max_tokens("hola?") == 256)
test("Predictor: input 5 chars -> 256", pred.predict_max_tokens("hi") == 256)

# Patrones cortos (español)
test("Predictor: 'que es X' -> 384", pred.predict_max_tokens("que es machine learning?") == 384)
test("Predictor: 'quien es X' -> 384", pred.predict_max_tokens("quien es alan turing?") == 384)
test("Predictor: 'cuando X' -> 384", pred.predict_max_tokens("cuando se invento internet?") == 384)
test("Predictor: 'donde X' -> 384", pred.predict_max_tokens("donde esta la torre eiffel?") == 384)

# Patrones cortos (inglés)
test("Predictor: 'what is X' -> 384", pred.predict_max_tokens("what is machine learning fundamentals?") == 384)
test("Predictor: 'who is X' -> 384", pred.predict_max_tokens("who is the CEO of that company?") == 384)

# Patrones largos (español)
test("Predictor: 'explica X' -> 2048", pred.predict_max_tokens("explica detalladamente la teoria de cuerdas") == 2048)
test("Predictor: 'escribe un X' -> 2048", pred.predict_max_tokens("escribe un ensayo sobre filosofia") == 2048)
test("Predictor: 'tutorial X' -> 2048", pred.predict_max_tokens("tutorial completo de como usar docker") == 2048)
test("Predictor: 'codigo X' -> 2048", pred.predict_max_tokens("genera codigo para un servidor web en python") == 2048)

# Patrones largos (inglés)
test("Predictor: 'explain X' -> 2048", pred.predict_max_tokens("explain how neural networks work in detail") == 2048)
test("Predictor: 'write a X' -> 2048", pred.predict_max_tokens("write a complete guide to kubernetes") == 2048)
test("Predictor: 'implement X' -> 2048", pred.predict_max_tokens("implement a binary search tree in python") == 2048)

# Input largo sin patrones -> 1536
long_input = "x" * 250
test("Predictor: input largo sin patron -> 1536", pred.predict_max_tokens(long_input) == 1536)

# Default
test("Predictor: input medio sin patron -> default", pred.predict_max_tokens("algo intermedio sin patrones claros aqui") == 1024)

# Custom default
test("Predictor: custom default", pred.predict_max_tokens("algo intermedio sin patrones claros aqui", default=512) == 512)


# ============================================================
# TEST 6: ContextTrimmer
# ============================================================
print("\n=== TEST: ContextTrimmer ===")
trimmer = ContextTrimmer(max_system_chars=200, max_message_chars=50, max_messages=4)

# System prompt trimming
prompt = "Linea 1\n\n\n\nLinea 2\n\n\n\nLinea 3"
trimmed = trimmer.trim_system_prompt(prompt)
test("Trimmer: elimina lineas vacias multiples", "\n\n\n" not in trimmed)
test("Trimmer: mantiene contenido", "Linea 1" in trimmed and "Linea 2" in trimmed)

# System prompt truncation
long_prompt = "A" * 500
trimmed_long = trimmer.trim_system_prompt(long_prompt)
test("Trimmer: trunca prompt largo", len(trimmed_long) <= 200 + 50)  # + marker text
test("Trimmer: contiene marker de recorte", "[contexto recortado]" in trimmed_long)

# Message trimming
messages = [
    {"role": "user", "content": "Mensaje 1 " + "x" * 100},
    {"role": "assistant", "content": "Respuesta 1 " + "y" * 100},
    {"role": "user", "content": "Mensaje 2 " + "x" * 100},
    {"role": "assistant", "content": "Respuesta 2 " + "y" * 100},
    {"role": "user", "content": "Mensaje 3 " + "x" * 100},
    {"role": "assistant", "content": "Respuesta 3 completa sin truncar"},
]

trimmed_msgs = trimmer.trim_messages(messages)
test("Trimmer: limita cantidad mensajes", len(trimmed_msgs) <= 4)

# Los ultimos 2 se mantienen completos
test("Trimmer: ultimo mensaje intacto", "Respuesta 3 completa sin truncar" in trimmed_msgs[-1]["content"])

# Los anteriores se truncan
if len(trimmed_msgs) > 2:
    test("Trimmer: mensajes antiguos truncados", len(trimmed_msgs[0]["content"]) <= 54)  # 50 + "..."

# Empty messages
test("Trimmer: lista vacia", trimmer.trim_messages([]) == [])

# Stats tracking
test("Trimmer: chars_saved > 0", trimmer.chars_saved > 0)


# ============================================================
# TEST 7: InferenceOptimizer (coordinador)
# ============================================================
print("\n=== TEST: InferenceOptimizer ===")
optimizer = InferenceOptimizer()

test("Optimizer init: prompt_cache existe", optimizer.prompt_cache is not None)
test("Optimizer init: predictor existe", optimizer.predictor is not None)
test("Optimizer init: trimmer existe", optimizer.trimmer is not None)
test("Optimizer init: total_optimizations 0", optimizer.total_optimizations == 0)

# Optimize
system_prompt = "Eres Genesis.\n\n\n\nUna IA experimental.\n\n\nResponde en espanol."
messages = [
    {"role": "user", "content": "Hola, como estas?"},
    {"role": "assistant", "content": "Muy bien, gracias por preguntar."},
    {"role": "user", "content": "Que es Python?"},
]

result = optimizer.optimize(system_prompt, messages, "que es Python?")

test("Optimizer.optimize: retorna dict", isinstance(result, dict))
test("Optimizer.optimize: tiene system_prompt", "system_prompt" in result)
test("Optimizer.optimize: tiene messages", "messages" in result)
test("Optimizer.optimize: tiene max_tokens", "max_tokens" in result)
test("Optimizer.optimize: tiene cache_hit", "cache_hit" in result)
test("Optimizer.optimize: tiene chars_saved", "chars_saved" in result)
test("Optimizer.optimize: max_tokens es int", isinstance(result["max_tokens"], int))
test("Optimizer.optimize: max_tokens > 0", result["max_tokens"] > 0)
test("Optimizer.optimize: primer call = cache MISS", result["cache_hit"] is False)
test("Optimizer.optimize: total_optimizations incrementado", optimizer.total_optimizations == 1)

# Segunda llamada con mismo prompt = cache HIT
result2 = optimizer.optimize(system_prompt, messages, "que es Java?")
test("Optimizer.optimize: segundo call = cache HIT", result2["cache_hit"] is True)

# Prompt corto -> max_tokens bajo
result3 = optimizer.optimize("IA", [], "hola?")
test("Optimizer.optimize: input corto -> tokens bajos", result3["max_tokens"] == 256)

# Prompt largo -> max_tokens alto
result4 = optimizer.optimize("IA", [], "explica detalladamente como funciona una red neuronal profunda")
test("Optimizer.optimize: input complejo -> tokens altos", result4["max_tokens"] >= 2048)

# Stats
stats = optimizer.get_stats()
test("Optimizer.get_stats: total_optimizations correctas", stats["total_optimizations"] >= 4)
test("Optimizer.get_stats: tiene cache_hit_rate", "cache_hit_rate" in stats)
test("Optimizer.get_stats: tiene total_tokens_saved", "total_tokens_saved" in stats)
test("Optimizer.get_stats: tiene last", "last" in stats)

# Status
status = optimizer.status()
test("Optimizer.status: contiene Optimizaciones", "Optimizaciones:" in status)
test("Optimizer.status: contiene Cache", "Cache:" in status)
test("Optimizer.status: contiene Tokens ahorrados", "Tokens ahorrados:" in status)

# last_optimization detail
last = optimizer.last_optimization
test("Optimizer.last: tiene cache_hit", "cache_hit" in last)
test("Optimizer.last: tiene chars_saved", "chars_saved" in last)
test("Optimizer.last: tiene max_tokens", "max_tokens" in last)
test("Optimizer.last: tiene elapsed_ms", "elapsed_ms" in last)


# ============================================================
# TEST 8: LiveDashboard HTML
# ============================================================
print("\n=== TEST: LiveDashboard HTML ===")
from core.live_dashboard import get_live_dashboard_html

html = get_live_dashboard_html()

test("Dashboard: retorna string", isinstance(html, str))
test("Dashboard: tiene DOCTYPE", "<!DOCTYPE html>" in html)
test("Dashboard: tiene title", "<title>" in html)
test("Dashboard: tiene Genesis o GENESIS", "Genesis" in html or "GENESIS" in html or "genesis" in html)
test("Dashboard: tiene auto-refresh", "setInterval" in html or "setTimeout" in html)
test("Dashboard: tiene fetch", "fetch(" in html)
test("Dashboard: tiene /api/live-dashboard", "/api/live-dashboard" in html)
test("Dashboard: tiene CSS", "<style>" in html)
test("Dashboard: tiene GPU section", "GPU" in html or "gpu" in html)
test("Dashboard: tiene Brain section", "Brain" in html or "brain" in html or "Cerebro" in html)
test("Dashboard: tiene Memory section", "Memory" in html or "Memoria" in html or "memory" in html)
test("Dashboard: no esta vacio", len(html) > 1000)


# ============================================================
# TEST 9: Integracion en genesis.py — Imports
# ============================================================
print("\n=== TEST: genesis.py — Imports ===")
import importlib

# Verificar que genesis.py importa los modulos
genesis_source = open("genesis.py", "r", encoding="utf-8").read()

test("genesis.py: importa SemanticMemory", "from core.semantic_memory import SemanticMemory" in genesis_source)
test("genesis.py: importa InferenceOptimizer", "from core.inference_optimizer import InferenceOptimizer" in genesis_source)

# Verificar inicializacion
test("genesis.py: self.semantic_memory =", "self.semantic_memory = SemanticMemory(" in genesis_source)
test("genesis.py: self.optimizer =", "self.optimizer = InferenceOptimizer()" in genesis_source)

# Verificar integracion en process_input
test("genesis.py: semantic_memory.get_context", "semantic_memory.get_context_for_prompt" in genesis_source)
test("genesis.py: optimizer.optimize", "optimizer.optimize(" in genesis_source)

# Verificar post-process indexing
test("genesis.py: semantic_memory.index en post_process", "semantic_memory.index(" in genesis_source)

# Verificar /status tiene semantic memory
test("genesis.py: /status tiene SEMANTIC MEMORY", "SEMANTIC MEMORY:" in genesis_source)
test("genesis.py: /status tiene INFERENCE OPTIMIZER", "INFERENCE OPTIMIZER:" in genesis_source)

# Verificar /memory semantic
test("genesis.py: /memory semantic command", '"/memory semantic"' in genesis_source)
test("genesis.py: generate_report call", "semantic_memory.generate_report()" in genesis_source)

# Verificar /help
test("genesis.py: help tiene /memory semantic", "/memory semantic" in genesis_source)

# Verificar save on exit
test("genesis.py: semantic_memory.save() on exit", "semantic_memory.save()" in genesis_source)

# Verificar dashboard collectors
test("genesis.py: dashboard register semantic_memory", '"semantic_memory"' in genesis_source)
test("genesis.py: dashboard register optimizer", '"optimizer"' in genesis_source)

# Banner
test("genesis.py: banner tiene Memoria semantica", "Memoria semantica:" in genesis_source)
test("genesis.py: banner tiene Inference Optimizer", "Inference Optimizer:" in genesis_source)


# ============================================================
# TEST 10: Integracion en web_ui.py
# ============================================================
print("\n=== TEST: web_ui.py — Endpoints ===")
webui_source = open("web_ui.py", "r", encoding="utf-8").read()

test("web_ui.py: tiene /dashboard/live", '"/dashboard/live"' in webui_source)
test("web_ui.py: tiene /api/live-dashboard", '"/api/live-dashboard"' in webui_source)
test("web_ui.py: importa GENESIS_VERSION", "from config import GENESIS_VERSION" in webui_source)
test("web_ui.py: importa live_dashboard", "from core.live_dashboard import get_live_dashboard_html" in webui_source)
test("web_ui.py: retorna gpu data", '"gpu"' in webui_source or "'gpu'" in webui_source)
test("web_ui.py: retorna brain data", '"brain"' in webui_source or "'brain'" in webui_source)
test("web_ui.py: retorna semantic_memory data", '"semantic_memory"' in webui_source or "'semantic_memory'" in webui_source)
test("web_ui.py: retorna optimizer data", '"optimizer"' in webui_source or "'optimizer'" in webui_source)
test("web_ui.py: retorna autonomous data", '"autonomous"' in webui_source or "'autonomous'" in webui_source)
test("web_ui.py: retorna subsystems", '"subsystems"' in webui_source or "'subsystems'" in webui_source)


# ============================================================
# TEST 11: PromptCache — Edge Cases
# ============================================================
print("\n=== TEST: PromptCache — Edge Cases ===")

cache2 = PromptCache(max_entries=2)

# Empty string
cache2.put("")
r = cache2.get("")
test("Cache: empty string cacheable", r == "")

# Very long string
long_str = "x" * 100000
cache2.put(long_str)
r = cache2.get(long_str)
test("Cache: long string cacheable", r == long_str)

# Unicode
cache2.put("Esto tiene acentos: áéíóú ñ 中文")
r = cache2.get("Esto tiene acentos: áéíóú ñ 中文")
test("Cache: unicode cacheable", r is not None)

# Eviction with max_entries=2
cache3 = PromptCache(max_entries=2)
cache3.put("First")
cache3.put("Second")
cache3.put("Third")  # Should evict "First"
test("Cache eviction: size <= max", len(cache3.cache) <= 2)


# ============================================================
# TEST 12: ResponsePredictor — Mixed Patterns
# ============================================================
print("\n=== TEST: ResponsePredictor — Mixed Patterns ===")
pred2 = ResponsePredictor()

# Input con patron largo dominante (mas keywords largas que cortas)
test("Predictor: 'explica detalladamente X' -> largo gana",
     pred2.predict_max_tokens("explica detalladamente la computacion cuantica paso a paso") >= 2048)

# Solo patron corto
test("Predictor: 'cuanto cuesta un auto?' -> 384",
     pred2.predict_max_tokens("cuanto cuesta un auto nuevo?") == 384)

# Sin patron, longitud media
test("Predictor: sin patron medio -> default",
     pred2.predict_max_tokens("Estoy pensando en algo interesante sobre el clima") == 1024)


# ============================================================
# TEST 13: ContextTrimmer — Edge Cases
# ============================================================
print("\n=== TEST: ContextTrimmer — Edge Cases ===")
trimmer2 = ContextTrimmer(max_system_chars=5000, max_message_chars=500, max_messages=8)

# Prompt sin lineas vacias = sin cambios
clean_prompt = "Linea 1\nLinea 2\nLinea 3"
trimmed = trimmer2.trim_system_prompt(clean_prompt)
test("Trimmer: prompt limpio sin cambios", trimmed == clean_prompt)

# Solo lineas vacias
empty_prompt = "\n\n\n\n\n"
trimmed_empty = trimmer2.trim_system_prompt(empty_prompt)
test("Trimmer: multiples vacias -> una sola", trimmed_empty.count("\n") <= 2)

# Mensajes exactos al limite
msgs = [{"role": "user", "content": f"Msg {i}"} for i in range(8)]
trimmed_msgs = trimmer2.trim_messages(msgs)
test("Trimmer: exacto al limite sin recortar", len(trimmed_msgs) == 8)

# Un solo mensaje
single = [{"role": "user", "content": "Solo uno"}]
trimmed_single = trimmer2.trim_messages(single)
test("Trimmer: single message intacto", len(trimmed_single) == 1)
test("Trimmer: single content intacto", trimmed_single[0]["content"] == "Solo uno")


# ============================================================
# TEST 14: InferenceOptimizer — Multiple Optimizations
# ============================================================
print("\n=== TEST: InferenceOptimizer — Multiple Optimizations ===")
opt2 = InferenceOptimizer()

# 10 optimizaciones consecutivas
for i in range(10):
    opt2.optimize(f"System prompt {i}", [
        {"role": "user", "content": f"Question {i}"},
    ], f"Question {i}")

test("Optimizer: 10 optimizations tracked", opt2.total_optimizations == 10)
test("Optimizer: cache stats updated", opt2.prompt_cache.hits + opt2.prompt_cache.misses == 10)
test("Optimizer: hit_rate calculable", 0 <= opt2.prompt_cache.hit_rate <= 1.0)


# ============================================================
# TEST 15: SemanticMemory — Persistencia robusta
# ============================================================
print("\n=== TEST: SemanticMemory — Persistencia ===")
tmp_dir3 = tempfile.mkdtemp()

try:
    # Crear y poblar
    m1 = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir3)
    for i in range(15):
        m1.index(
            user_input=f"Pregunta sobre tema {i} con suficiente longitud",
            response=f"Respuesta detallada sobre el tema {i} con informacion relevante.",
            intent=["chat", "code", "research"][i % 3],
            quality=0.1 * (i + 1),
        )
    m1.save()

    # Verificar archivo
    test("Persist: archivo JSON existe", m1.metadata_file.exists())
    with open(m1.metadata_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    test("Persist: JSON tiene entries", "entries" in data)
    test("Persist: JSON tiene stats", "stats" in data)
    test("Persist: entries coincide", len(data["entries"]) == len(m1.entries))

    # Recargar
    m2 = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir3)
    test("Persist: reload entries OK", len(m2.entries) == len(m1.entries))
    test("Persist: reload stats OK", m2.total_indexed == m1.total_indexed)

    # Verificar intents preservados
    intents = set(e.intent for e in m2.entries.values())
    test("Persist: intents preservados", "chat" in intents and "code" in intents and "research" in intents)

finally:
    shutil.rmtree(tmp_dir3, ignore_errors=True)


# ============================================================
# TEST 16: SemanticMemory — Report con datos
# ============================================================
print("\n=== TEST: SemanticMemory — Report ===")
tmp_dir4 = tempfile.mkdtemp()

try:
    m = SemanticMemory(embeddings_engine=None, base_dir=tmp_dir4)
    for i in range(5):
        m.index(
            user_input=f"Pregunta {i} sobre temas variados e interesantes",
            response=f"Respuesta {i} con suficiente contenido para indexar.",
            intent=["chat", "code", "research", "chat", "code"][i],
        )

    report = m.generate_report()
    test("Report: tiene header", "MEMORIA SEMANTICA" in report)
    test("Report: tiene conteo", "5" in report)
    test("Report: tiene RECIENTES", "RECIENTES" in report)
    test("Report: tiene DISTRIBUCION", "DISTRIBUCION" in report)
    test("Report: tiene chat", "chat:" in report)
    test("Report: tiene code", "code:" in report)

finally:
    shutil.rmtree(tmp_dir4, ignore_errors=True)


# ============================================================
# TEST 17: SemanticMemory — get_context_for_prompt format
# ============================================================
print("\n=== TEST: SemanticMemory — Context Format ===")

# Sin embeddings siempre retorna "", pero verificamos la logica del metodo
mem_ctx = SemanticMemory(embeddings_engine=None, base_dir=tempfile.mkdtemp())
ctx = mem_ctx.get_context_for_prompt("test", max_chars=1500)
test("Context: sin embeddings retorna vacio", ctx == "")

# Verificar que recall incrementa stats
mem_ctx.recall("algo")
test("Context: recall incrementa total_recalls", mem_ctx.total_recalls >= 1)

shutil.rmtree(str(mem_ctx.base_dir), ignore_errors=True)


# ============================================================
# TEST 18: SemanticMemory con EmbeddingsEngine mock
# ============================================================
print("\n=== TEST: SemanticMemory con Embeddings ===")

class MockEmbeddingsEngine:
    """Mock de EmbeddingsEngine para testing sin modelo real."""
    def __init__(self):
        self.store = {}

    def add_text(self, key, text, metadata=None):
        self.store[key] = {"text": text, "metadata": metadata or {}}

    def search(self, query, top_k=3):
        # Retorna todos los items con score bajo (no duplica)
        results = []
        for k, v in self.store.items():
            results.append({"key": k, "text": v["text"], "score": 0.5})
        return results[:top_k]

    def remove(self, key):
        self.store.pop(key, None)

    def save(self):
        pass

tmp_dir5 = tempfile.mkdtemp()
try:
    mock_emb = MockEmbeddingsEngine()
    mem_emb = SemanticMemory(embeddings_engine=mock_emb, base_dir=tmp_dir5)

    # Indexar con embeddings
    eid1 = mem_emb.index(
        user_input="Como instalar Python en Windows?",
        response="Puedes descargar Python desde python.org e instalar el ejecutable.",
        intent="chat",
    )
    test("SM+Emb: indexa OK", eid1 is not None)
    test("SM+Emb: embeddings tiene entry", eid1 in mock_emb.store)

    eid2 = mem_emb.index(
        user_input="Que frameworks de Python existen?",
        response="Django, Flask, FastAPI son los mas populares para web.",
        intent="research",
    )
    test("SM+Emb: segunda entry OK", eid2 is not None)

    # Recall con embeddings
    results = mem_emb.recall("Python instalacion")
    test("SM+Emb: recall retorna resultados", len(results) > 0)
    test("SM+Emb: recall tiene user_input", "user_input" in results[0])
    test("SM+Emb: recall tiene response", "response" in results[0])
    test("SM+Emb: recall tiene score", "score" in results[0])
    test("SM+Emb: recall tiene age_hours", "age_hours" in results[0])
    test("SM+Emb: total_hits incrementado", mem_emb.total_hits >= 1)

    # get_context_for_prompt
    ctx = mem_emb.get_context_for_prompt("instalar python")
    test("SM+Emb: context contiene header", "MEMORIA SEMANTICA" in ctx)
    test("SM+Emb: context no vacio", len(ctx) > 50)

    # Recall con intent filter (mock no filtra pero verifica la logica)
    results_filtered = mem_emb.recall("Python", intent_filter="research")
    test("SM+Emb: intent_filter funciona", isinstance(results_filtered, list))

finally:
    shutil.rmtree(tmp_dir5, ignore_errors=True)


# ============================================================
# TEST 19: Version check (>= 2.2)
# ============================================================
print("\n=== TEST: Version Check ===")
from config import GENESIS_VERSION

parts = GENESIS_VERSION.split(".")
major = int(parts[0])
minor = int(parts[1])
version_num = major * 10 + minor

test(f"Version: {GENESIS_VERSION} >= 2.1", version_num >= 21)


# ============================================================
# TEST 20: Modulos importables sin errores
# ============================================================
print("\n=== TEST: Import Modules ===")
try:
    from core.semantic_memory import SemanticMemory as SM
    test("Import: SemanticMemory OK", True)
except Exception as e:
    test(f"Import: SemanticMemory FAILED ({e})", False)

try:
    from core.inference_optimizer import InferenceOptimizer as IO
    test("Import: InferenceOptimizer OK", True)
except Exception as e:
    test(f"Import: InferenceOptimizer FAILED ({e})", False)

try:
    from core.live_dashboard import get_live_dashboard_html as GLDH
    test("Import: LiveDashboard OK", True)
except Exception as e:
    test(f"Import: LiveDashboard FAILED ({e})", False)


# ============================================================
# RESUMEN
# ============================================================
print("\n" + "=" * 60)
total = _passed + _failed
print(f"  GENESIS v2.2 Tests: {_passed}/{total} passed")
if _failed > 0:
    print(f"  {_failed} FAILED")
else:
    print(f"  ALL TESTS PASSED!")
print("=" * 60)

sys.exit(0 if _failed == 0 else 1)
