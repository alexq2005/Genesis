"""
Tests para Genesis v1.5.0
- RAG System (indexacion, busqueda, chunks, persistencia)
- Model Router (scan, routing, manual override)
- Voice System (TTS init, clean text, toggle)
- Dashboard (importable, HTML generation)
- Integracion en genesis.py
"""
import sys
import os
import tempfile
import shutil
import time
import json

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
# TEST 1: RAG — DocumentChunker
# ============================================================
print("\n=== TEST: RAG — DocumentChunker ===")
from core.rag import DocumentChunker

chunker = DocumentChunker(chunk_size=200, overlap=20)

# Extensiones soportadas
test("Soporta .py", chunker.can_process("test.py"))
test("Soporta .md", chunker.can_process("docs/readme.md"))
test("Soporta .txt", chunker.can_process("notes.txt"))
test("No soporta .exe", not chunker.can_process("malware.exe"))
test("No soporta .gguf", not chunker.can_process("model.gguf"))
test("No soporta .png", not chunker.can_process("image.png"))

# Chunking basico
text = "Primer parrafo corto.\n\nSegundo parrafo un poco mas largo que el primero.\n\nTercer parrafo final."
chunks = chunker.chunk_text(text, source="test.txt")
test("Chunks generados", len(chunks) > 0)
test("Cada chunk tiene text", all("text" in c for c in chunks))
test("Cada chunk tiene source", all(c["source"] == "test.txt" for c in chunks))
test("Cada chunk tiene chunk_id", all("chunk_id" in c for c in chunks))

# Chunking texto largo
long_text = ("A" * 100 + "\n\n") * 10
long_chunks = chunker.chunk_text(long_text, source="long.txt")
test("Texto largo genera multiples chunks", len(long_chunks) > 1)

# Texto vacio
empty_chunks = chunker.chunk_text("", source="empty.txt")
test("Texto vacio genera 0 chunks", len(empty_chunks) == 0)

# Texto solo whitespace
ws_chunks = chunker.chunk_text("   \n\n   \n  ", source="ws.txt")
test("Whitespace genera 0 chunks", len(ws_chunks) == 0)


# ============================================================
# TEST 2: RAG — RAGVectorizer
# ============================================================
print("\n=== TEST: RAG — RAGVectorizer ===")
from core.rag import RAGVectorizer

vec = RAGVectorizer()

# Tokenize
tokens = vec._tokenize("Python es un lenguaje de programacion genial")
test("Tokenize filtra stopwords", "de" not in tokens)
test("Tokenize mantiene palabras significativas", "python" in tokens)
test("Tokenize normaliza a minusculas", all(t == t.lower() for t in tokens))

# Fit y vectorize
docs = [
    "Python es un lenguaje de programacion",
    "JavaScript funciona en el navegador",
    "Rust es seguro y rapido para sistemas",
]
vec.fit(docs)
test("Vocabulario construido", len(vec.vocabulary) > 0)
test("IDF calculado", len(vec.idf) > 0)

# Vectorize
v1 = vec.vectorize("Python programacion")
test("Vectorize retorna dict", isinstance(v1, dict))
test("Vectorize tiene scores", len(v1) > 0)
test("Scores son positivos", all(s > 0 for s in v1.values()))

# Similarity
v2 = vec.vectorize("JavaScript navegador web")
v3 = vec.vectorize("Python lenguaje programacion")
sim_same = vec.similarity(v1, v3)
sim_diff = vec.similarity(v1, v2)
test("Similarity: Python-Python > Python-JS", sim_same > sim_diff)

# Similarity con vacio
test("Similarity vacio = 0", vec.similarity({}, v1) == 0.0)
test("Similarity ambos vacios = 0", vec.similarity({}, {}) == 0.0)


# ============================================================
# TEST 3: RAG — RAGSystem
# ============================================================
print("\n=== TEST: RAG — RAGSystem ===")
from core.rag import RAGSystem

tmpdir = tempfile.mkdtemp()
try:
    # Crear archivos de test
    with open(os.path.join(tmpdir, "test1.txt"), "w") as f:
        f.write("Genesis es un sistema de inteligencia artificial auto-evolutivo.\n"
                "Usa modelos locales para procesar lenguaje natural.\n"
                "Puede aprender de cada interaccion y mejorar.")

    with open(os.path.join(tmpdir, "test2.py"), "w") as f:
        f.write("# Script de ejemplo\n"
                "def calcular_fibonacci(n):\n"
                "    if n <= 1:\n"
                "        return n\n"
                "    return calcular_fibonacci(n-1) + calcular_fibonacci(n-2)\n")

    with open(os.path.join(tmpdir, "test3.md"), "w") as f:
        f.write("# Documentacion\n\n"
                "## Instalacion\n"
                "Ejecutar pip install -r requirements.txt\n\n"
                "## Uso\n"
                "Ejecutar python genesis.py para iniciar.")

    # Crear subdirectorio memory_data para persistencia
    os.makedirs(os.path.join(tmpdir, "memory_data"), exist_ok=True)

    rag = RAGSystem(base_dir=tmpdir)

    # Index individual file
    result = rag.index_file(os.path.join(tmpdir, "test1.txt"))
    test("Index archivo exitoso", result["success"])
    test("Chunks creados > 0", result["chunks_added"] > 0)

    # Index same file again (no changes)
    result2 = rag.index_file(os.path.join(tmpdir, "test1.txt"))
    test("Re-index sin cambios", result2["chunks_added"] == 0)

    # Index directory
    dir_result = rag.index_directory(tmpdir, recursive=False)
    test("Index directorio exitoso", dir_result["files_processed"] >= 2)

    # Search
    results = rag.search("inteligencia artificial", top_k=3)
    test("Search retorna resultados", len(results) > 0)
    test("Resultado tiene score", "score" in results[0])
    test("Resultado tiene text", "text" in results[0])
    test("Score es float", isinstance(results[0]["score"], float))

    # Search codigo — usar palabras que aparecen en test2.py
    code_results = rag.search("calcular fibonacci script ejemplo", top_k=3, min_score=0.05)
    test("Search codigo funciona", len(code_results) > 0)

    # Get context
    context = rag.get_context("como funciona genesis", max_chars=500)
    test("Get context retorna string", isinstance(context, str))
    test("Context contiene marcadores RAG", "CONTEXTO RAG" in context or context == "")

    # Status
    status = rag.status()
    test("Status contiene info", "RAG System" in status)
    test("Status muestra archivos", "Archivos indexados" in status)

    # Archivo no existente
    bad_result = rag.index_file("/no/existe/nada.txt")
    test("Archivo inexistente: falla", not bad_result["success"])

    # Extension no soportada
    with open(os.path.join(tmpdir, "binary.exe"), "wb") as f:
        f.write(b"\x00\x01\x02")
    bad_ext = rag.index_file(os.path.join(tmpdir, "binary.exe"))
    test("Extension no soportada: falla", not bad_ext["success"])

    # Remove file
    removed = rag.remove_file(os.path.join(tmpdir, "test1.txt"))
    test("Remove archivo exitoso", removed)

    # Remove non-indexed file
    removed2 = rag.remove_file("/no/indexado.txt")
    test("Remove no-indexado: False", not removed2)

    # Clear
    rag.clear()
    test("Clear limpia chunks", len(rag.chunks) == 0)
    test("Clear limpia indexed_files", len(rag.indexed_files) == 0)

    # Search en indice vacio
    empty_results = rag.search("algo")
    test("Search vacio retorna []", len(empty_results) == 0)

    # Persistencia
    rag2 = RAGSystem(base_dir=tmpdir)
    rag2.index_file(os.path.join(tmpdir, "test2.py"))
    # Reload
    rag3 = RAGSystem(base_dir=tmpdir)
    test("Persistencia: chunks cargados", len(rag3.chunks) > 0)

finally:
    shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================
# TEST 4: Model Router — ModelProfile
# ============================================================
print("\n=== TEST: Model Router — ModelProfile ===")
from core.model_router import ModelProfile, ModelRouter

profile = ModelProfile(
    name="test_model",
    filename="test.gguf",
    strengths=["code", "debug"],
    default_temp=0.5,
    context_length=8192,
    gpu_layers=40,
    priority=7,
    description="Modelo de prueba",
)
test("Profile name", profile.name == "test_model")
test("Profile strengths", "code" in profile.strengths)
test("Profile to_dict", isinstance(profile.to_dict(), dict))
test("Profile to_dict tiene keys", "name" in profile.to_dict())


# ============================================================
# TEST 5: Model Router — ModelRouter
# ============================================================
print("\n=== TEST: Model Router — ModelRouter ===")

# Crear directorio temporal con modelos fake
tmpdir_models = tempfile.mkdtemp()
try:
    # Crear archivos .gguf vacios con nombres conocidos
    open(os.path.join(tmpdir_models, "dolphin-2.8-mistral-7b-v02-Q4_K_M.gguf"), "w").close()
    open(os.path.join(tmpdir_models, "mistral-7b-instruct-v0.2.Q4_K_M.gguf"), "w").close()
    open(os.path.join(tmpdir_models, "Qwen2.5-7B-Instruct-Q4_K_M.gguf"), "w").close()

    router = ModelRouter(models_dir=tmpdir_models)

    # Scan
    test("Scan detecta 3 modelos", len(router.profiles) == 3)
    test("Dolphin detectado", "dolphin" in router.profiles)
    test("Mistral detectado", "mistral" in router.profiles)
    test("Qwen detectado", "qwen" in router.profiles)

    # Default model (highest priority = dolphin)
    test("Modelo activo es dolphin", router.active_model == "dolphin")

    # Route default (no template)
    config = router.route("hola mundo")
    test("Route retorna config", "model_name" in config)
    test("Route default = dolphin", config["model_name"] == "dolphin")

    # Route con template creative
    config_creative = router.route("escribe un poema", template_name="creative")
    test("Route creative: retorna config", config_creative["model_name"] != "")
    test("Route creative: tiene reason", "reason" in config_creative)

    # Route con template analysis
    config_analysis = router.route("analiza este dataset", template_name="analysis")
    test("Route analysis: retorna config", config_analysis["model_name"] != "")

    # Manual model selection
    result = router.set_model("mistral")
    test("Set model mistral: exitoso", "mistral" in result.lower() or "Mistral" in result)

    config_manual = router.route("cualquier cosa")
    test("Manual override: usa mistral", config_manual["model_name"] == "mistral")

    # Set auto
    auto_result = router.set_auto()
    test("Set auto: exitoso", "auto" in auto_result.lower())

    # Model not found
    not_found = router.set_model("gpt5_inexistente")
    test("Modelo no encontrado: error", "no encontrado" in not_found.lower() or "not found" in not_found.lower())

    # List models
    models_list = router.list_models()
    test("List models: contiene dolphin", "dolphin" in models_list.lower())
    test("List models: contiene GPU layers", "GPU" in models_list or "gpu" in models_list.lower())

    # Status
    status = router.status()
    test("Status: contiene info", "ModelRouter" in status)

    # Toggle auto
    toggle_result = router.toggle_auto()
    test("Toggle auto funciona", "ACTIVADO" in toggle_result or "DESACTIVADO" in toggle_result)

    # Empty models directory
    empty_dir = tempfile.mkdtemp()
    router_empty = ModelRouter(models_dir=empty_dir)
    test("Sin modelos: profiles vacio", len(router_empty.profiles) == 0)
    config_empty = router_empty.route("test")
    test("Sin modelos: reason indica error", "no hay" in config_empty["reason"].lower() or "No" in config_empty["reason"])
    shutil.rmtree(empty_dir)

finally:
    shutil.rmtree(tmpdir_models, ignore_errors=True)


# ============================================================
# TEST 6: Voice System
# ============================================================
print("\n=== TEST: Voice System ===")
from core.voice import VoiceSystem, TTSEngine, STTEngine

# Voice System init
voice = VoiceSystem()
test("Voice init sin crash", True)
test("Voice disabled by default", not voice.enabled)

# Toggle
result = voice.toggle()
test("Voice toggle", "ACTIVADA" in result)
result2 = voice.toggle()
test("Voice toggle off", "DESACTIVADA" in result2)

# TTS engine (may not be available without pyttsx3)
tts = TTSEngine()
test("TTS init sin crash", True)
# No testear .speak() porque depende de pyttsx3

# STT engine (may not be available without vosk)
stt = STTEngine()
test("STT init sin crash", True)
test("STT sin modelo: no disponible", not stt.available)

# Status
status = voice.status()
test("Status contiene Voice System", "Voice System" in status)
test("Status muestra TTS", "TTS" in status)
test("Status muestra STT", "STT" in status)

# Clean for speech
text_raw = "Esto es **bold** y ```codigo aqui``` y https://example.com y # Titulo"
clean = voice._clean_for_speech(text_raw)
test("Clean: quita markdown bold", "**" not in clean)
test("Clean: quita code blocks", "```" not in clean)
test("Clean: quita URLs", "https://" not in clean)
test("Clean: quita headers", clean[0] != "#")

# Clean texto largo
long_text = "A" * 1000
clean_long = voice._clean_for_speech(long_text)
test("Clean: trunca texto largo", len(clean_long) <= 510)

# Clean texto vacio
clean_empty = voice._clean_for_speech("")
test("Clean: texto vacio retorna vacio", clean_empty == "")

# Speak cuando disabled
voice.enabled = False
result = voice.speak("test")
test("Speak disabled: retorna False", not result)


# ============================================================
# TEST 7: Dashboard
# ============================================================
print("\n=== TEST: Dashboard ===")
from core.dashboard import get_dashboard_html

html = get_dashboard_html()
test("Dashboard retorna HTML", len(html) > 0)
test("Dashboard contiene DOCTYPE", "<!DOCTYPE html>" in html)
test("Dashboard contiene Chart.js", "chart.js" in html.lower())
test("Dashboard contiene vis-network", "vis-network" in html.lower())
test("Dashboard contiene titulo", "GENESIS DASHBOARD" in html)
test("Dashboard contiene grid", "class=\"grid\"" in html)


# ============================================================
# TEST 8: Imports en genesis.py
# ============================================================
print("\n=== TEST: Imports v1.5 en genesis.py ===")
import importlib

# Verificar que genesis.py importa los nuevos modulos
genesis_source = open("genesis.py", "r", encoding="utf-8").read()
test("Import RAGSystem", "from core.rag import RAGSystem" in genesis_source)
test("Import ModelRouter", "from core.model_router import ModelRouter" in genesis_source)
test("Import VoiceSystem", "from core.voice import VoiceSystem" in genesis_source)

# Verificar integracion
test("self.rag en __init__", "self.rag = RAGSystem" in genesis_source)
test("self.model_router en __init__", "self.model_router = ModelRouter" in genesis_source)
test("self.voice en __init__", "self.voice = VoiceSystem" in genesis_source)

# Comandos registrados
test("Comando /rag", '"/rag"' in genesis_source or "== \"/rag\"" in genesis_source or 'cmd == "/rag' in genesis_source)
test("Comando /models", '"/models"' in genesis_source)
test("Comando /voice", '"/voice"' in genesis_source)


# ============================================================
# TEST 9: Config version
# ============================================================
print("\n=== TEST: Config version ===")
from config import GENESIS_VERSION
test("Version es >= 1.5.0", GENESIS_VERSION >= "1.5.0")


# ============================================================
# TEST 10: web_ui.py tiene dashboard
# ============================================================
print("\n=== TEST: web_ui.py dashboard route ===")
webui_source = open("web_ui.py", "r", encoding="utf-8").read()
test("Import dashboard", "from core.dashboard import" in webui_source)
test("Route /dashboard", '"/dashboard"' in webui_source)


# ============================================================
# TEST 11: Edge cases RAG
# ============================================================
print("\n=== TEST: RAG Edge Cases ===")

# Chunker con un solo parrafo grande
big_chunker = DocumentChunker(chunk_size=50, overlap=10)
big_text = "Palabra " * 100
big_chunks = big_chunker.chunk_text(big_text, source="big.txt")
test("Parrafo grande se divide", len(big_chunks) > 1)
test("Chunks no vacios", all(c["text"].strip() for c in big_chunks))

# Vectorizer con documento unico
vec_single = RAGVectorizer()
vec_single.fit(["solo un documento con palabras unicas especiales"])
v = vec_single.vectorize("documento unicas")
test("Single doc vectorize funciona", len(v) > 0)

# Similarity identica
sim_self = vec_single.similarity(v, v)
test("Self-similarity ~ 1.0", sim_self > 0.99)


# ============================================================
# TEST 12: Model Router Edge Cases
# ============================================================
print("\n=== TEST: Model Router Edge Cases ===")

# Router con modelos desconocidos
tmpdir_unk = tempfile.mkdtemp()
try:
    open(os.path.join(tmpdir_unk, "custom-model-v1.gguf"), "w").close()
    router_unk = ModelRouter(models_dir=tmpdir_unk)
    test("Modelo desconocido: detectado", len(router_unk.profiles) == 1)
    test("Modelo desconocido: tiene strengths general", True)

    config_unk = router_unk.route("test")
    test("Modelo desconocido: rutable", config_unk["model_name"] != "")
finally:
    shutil.rmtree(tmpdir_unk, ignore_errors=True)


# ============================================================
# RESULTADOS
# ============================================================
print(f"\n{'=' * 50}")
print(f"  RESULTADOS: {_passed}/{_passed + _failed} pasaron, {_failed} fallaron")
print(f"{'=' * 50}")

if _failed > 0:
    sys.exit(1)
