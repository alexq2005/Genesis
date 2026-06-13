"""
Tests para Genesis v3.3 — Sensory Expansion
ImageAnalyzer, DiagramGenerator, VoicePersonality
"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

passed = 0
failed = 0
errors = []

def test(name, condition):
    global passed, failed, errors
    try:
        if condition:
            passed += 1
        else:
            failed += 1
            errors.append(f"FAIL: {name}")
            print(f"  FAIL: {name}")
    except Exception as e:
        failed += 1
        errors.append(f"ERROR: {name}: {e}")
        print(f"  ERROR: {name}: {e}")

print("=" * 60)
print("GENESIS v3.3 — Sensory Expansion Tests")
print("=" * 60)

# ============================================================
# IMAGE ANALYZER
# ============================================================
print("\n--- ImageAnalyzer ---")
from core.image_analyzer import ImageMetadata, AnalysisResult, AnalysisCache, ImageAnalyzer

print("  ImageMetadata...")
meta = ImageMetadata("test/screenshots/captura_app.png")
test("Meta: filename correcto", meta.filename == "captura_app.png")
test("Meta: stem correcto", meta.stem == "captura_app")
test("Meta: extension .png", meta.extension == ".png")
test("Meta: format PNG", meta.format == "PNG")
test("Meta: is_image true", meta.is_image())
test("Meta: size_bytes 0 (no existe)", meta.size_bytes == 0)
test("Meta: exists false", meta.exists == False)

meta2 = ImageMetadata("test/file.txt")
test("Meta: archivo no imagen", meta2.format == "Unknown")
test("Meta: is_image false", not meta2.is_image())

meta3 = ImageMetadata("test/image.jpg")
test("Meta: jpg es JPEG", meta3.format == "JPEG")

meta4 = ImageMetadata("test/image.svg")
test("Meta: svg es SVG", meta4.format == "SVG")

test("Meta: IMAGE_EXTENSIONS tiene 10+", len(ImageMetadata.IMAGE_EXTENSIONS) >= 10)

# to_dict/from_dict
md = meta.to_dict()
test("Meta: to_dict tiene path", md["path"] == "test/screenshots/captura_app.png")
meta_r = ImageMetadata.from_dict(md)
test("Meta: from_dict preserva format", meta_r.format == "PNG")
test("Meta: from_dict preserva stem", meta_r.stem == "captura_app")

# size_human
test("Meta: size_human con 0 bytes", meta.size_human() == "0 B")

print("  AnalysisResult...")
ar = AnalysisResult(meta)
test("AR: description vacia", ar.description == "")
test("AR: tags vacios", ar.tags == [])
test("AR: confidence 0", ar.confidence == 0.0)
ar.description = "Test"
ar.tags = ["test"]
ar.confidence = 0.8
ar_dict = ar.to_dict()
test("AR: to_dict tiene description", ar_dict["description"] == "Test")
ar2 = AnalysisResult.from_dict(ar_dict)
test("AR: from_dict preserva description", ar2.description == "Test")
test("AR: from_dict preserva tags", ar2.tags == ["test"])

print("  AnalysisCache...")
cache = AnalysisCache(max_entries=3)
test("Cache: vacio inicialmente", len(cache.cache) == 0)
cache.put("a.png", {"desc": "a"})
cache.put("b.png", {"desc": "b"})
test("Cache: 2 entradas", len(cache.cache) == 2)
test("Cache: get hit", cache.get("a.png") is not None)
test("Cache: hits 1", cache.hits == 1)
test("Cache: get miss", cache.get("z.png") is None)
test("Cache: misses 1", cache.misses == 1)
cache.put("c.png", {"desc": "c"})
cache.put("d.png", {"desc": "d"})  # should evict oldest
test("Cache: eviccion a max_entries", len(cache.cache) <= 3)

cache_dict = cache.to_dict()
test("Cache: to_dict tiene hits", "hits" in cache_dict)
cache2 = AnalysisCache.from_dict(cache_dict, max_entries=3)
test("Cache: from_dict preserva hits", cache2.hits == cache.hits)

print("  ImageAnalyzer coordinator...")
tmp = tempfile.mkdtemp()
try:
    ia = ImageAnalyzer(base_dir=tmp)
    test("IA: init sin analizadas", ia.total_analyzed == 0)

    # Crear archivo de prueba
    test_img = os.path.join(tmp, "screenshot_test.png")
    with open(test_img, "wb") as f:
        f.write(b"\x89PNG" + b"\x00" * 100)  # fake PNG header

    result = ia.analyze(test_img)
    test("IA: analyze retorna dict", isinstance(result, dict))
    test("IA: analyze tiene description", "description" in result)
    test("IA: analyze tiene tags", "tags" in result)
    test("IA: analyze tiene confidence", "confidence" in result)
    test("IA: total_analyzed incrementa", ia.total_analyzed == 1)
    test("IA: tags incluye screenshot", "screenshot" in result.get("tags", []))

    # Cache hit
    result2 = ia.analyze(test_img)
    test("IA: cache hit marcado", result2.get("cached") == True)
    test("IA: total_analyzed no cambia en hit", ia.total_analyzed == 1)

    # Describe
    desc = ia.describe(test_img)
    test("IA: describe retorna string", isinstance(desc, str))
    test("IA: describe no vacio", len(desc) > 0)

    # Analizar archivo no imagen
    test_txt = os.path.join(tmp, "readme.txt")
    with open(test_txt, "w") as f:
        f.write("test")
    result3 = ia.analyze(test_txt)
    test("IA: no imagen tiene tag no_imagen", "no_imagen" in result3.get("tags", []))

    # get_context_for_prompt
    ctx = ia.get_context_for_prompt("analiza esta imagen", max_chars=200)
    test("IA: context con keyword imagen", len(ctx) > 0)
    ctx_no = ia.get_context_for_prompt("hola que tal")
    test("IA: context vacio sin keyword", ctx_no == "")

    # Stats
    stats = ia.get_stats()
    test("IA: stats tiene total_analyzed", stats["total_analyzed"] >= 1)
    test("IA: stats tiene cache_hits", "cache_hits" in stats)

    # Status / report
    test("IA: status es string", isinstance(ia.status(), str))
    test("IA: report contiene IMAGE ANALYZER", "IMAGE ANALYZER" in ia.generate_report())

    # Save/load
    ia.save()
    ia2 = ImageAnalyzer(base_dir=tmp)
    test("IA: persistencia total_analyzed", ia2.total_analyzed >= 1)

    # Clear
    ia.clear()
    test("IA: clear resetea", ia.total_analyzed == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# DIAGRAM GENERATOR
# ============================================================
print("\n--- DiagramGenerator ---")
from core.diagram_generator import DiagramType, DiagramSpec, DiagramDetector, DiagramGenerator

print("  DiagramType...")
test("DT: 6 tipos", len(DiagramType.TYPES) == 6)
test("DT: flowchart existe", "flowchart" in DiagramType.TYPES)
test("DT: sequence existe", "sequence" in DiagramType.TYPES)
test("DT: class_diagram existe", "class_diagram" in DiagramType.TYPES)
test("DT: er_diagram existe", "er_diagram" in DiagramType.TYPES)
test("DT: state existe", "state" in DiagramType.TYPES)
test("DT: gantt existe", "gantt" in DiagramType.TYPES)
test("DT: list_types retorna 6", len(DiagramType.list_types()) == 6)

dt = DiagramType("flowchart")
test("DT: header correcto", "flowchart" in dt.header)
test("DT: description no vacia", len(dt.description) > 0)

print("  DiagramSpec...")
spec = DiagramSpec("Test diagram", "flowchart")
test("DS: titulo preservado", spec.title == "Test diagram")
test("DS: tipo preservado", spec.diagram_type == "flowchart")
test("DS: nodos vacios", len(spec.nodes) == 0)

spec.add_node("A", "Inicio")
spec.add_node("B", "Fin")
test("DS: add_node funciona", len(spec.nodes) == 2)
spec.add_node("A", "Duplicado")  # No debe duplicar
test("DS: no duplica nodos", len(spec.nodes) == 2)

spec.add_edge("A", "B", "ir a")
test("DS: add_edge funciona", len(spec.edges) == 1)

spec.add_edge("B", "C")  # C auto-creado
test("DS: edge auto-crea nodos", len(spec.nodes) == 3)

spec_dict = spec.to_dict()
test("DS: to_dict tiene title", spec_dict["title"] == "Test diagram")
spec2 = DiagramSpec.from_dict(spec_dict)
test("DS: from_dict preserva nodos", len(spec2.nodes) == 3)
test("DS: from_dict preserva edges", len(spec2.edges) == 2)

print("  DiagramDetector...")
dd = DiagramDetector()
test("DD: detecta flowchart", dd.detect("diagrama de flujo proceso pasos") == "flowchart")
test("DD: detecta sequence", dd.detect("secuencia interaccion mensajes api") == "sequence")
test("DD: detecta class_diagram", dd.detect("clases herencia objetos atributos") == "class_diagram")
test("DD: detecta er_diagram", dd.detect("entidad relacion base de datos tabla") == "er_diagram")
test("DD: detecta state", dd.detect("estados transicion maquina de estados") == "state")
test("DD: detecta gantt", dd.detect("gantt cronograma planificacion fases") == "gantt")
test("DD: default flowchart", dd.detect("xxxxxxx") == "flowchart")

elems = dd.extract_elements("Login --> Dashboard")
test("DD: extract_elements finds edges", len(elems["edges"]) >= 1)
test("DD: extract_elements finds nodes", len(elems["nodes"]) >= 2)

elems2 = dd.extract_elements("- Paso 1\n- Paso 2\n- Paso 3")
test("DD: extract list items", len(elems2["nodes"]) >= 3)

print("  DiagramGenerator coordinator...")
tmp = tempfile.mkdtemp()
try:
    dg = DiagramGenerator(base_dir=tmp)
    test("DG: init sin diagramas", dg.total_diagrams == 0)

    result = dg.generate("Usuario -> Login -> Dashboard -> Logout", diagram_type="flowchart")
    test("DG: generate retorna dict", isinstance(result, dict))
    test("DG: tiene mermaid", "mermaid" in result)
    test("DG: tiene tipo", result["type"] == "flowchart")
    test("DG: tiene nodos", result["nodes"] > 0)
    test("DG: mermaid contiene bloque", "```mermaid" in result["mermaid"])
    test("DG: total_diagrams incrementa", dg.total_diagrams == 1)

    # Auto-detect
    result2 = dg.generate("entidad Usuario relacion con tabla Pedido en base de datos", diagram_type="auto")
    test("DG: auto-detect funciona", result2["type"] == "er_diagram")
    test("DG: total_diagrams 2", dg.total_diagrams == 2)

    # Manual nodes/edges
    dg.add_node("X", "Nodo X")
    dg.add_edge("X", "Y", "conecta")
    mermaid = dg.get_mermaid()
    test("DG: get_mermaid no vacio", len(mermaid) > 0)

    # Context
    ctx = dg.get_context_for_prompt("quiero un diagrama de flujo", max_chars=200)
    test("DG: context con keyword", len(ctx) > 0)
    test("DG: context contiene DIAGRAMA", "DIAGRAMA" in ctx)
    ctx_no = dg.get_context_for_prompt("hola que tal")
    test("DG: context vacio sin keyword", ctx_no == "")

    # Stats
    stats = dg.get_stats()
    test("DG: stats tiene total_diagrams", stats["total_diagrams"] >= 2)
    test("DG: stats tiene type_counts", "type_counts" in stats)

    # Status / report
    test("DG: status string", isinstance(dg.status(), str))
    test("DG: report contiene DIAGRAM", "DIAGRAM" in dg.generate_report())

    # Save/load
    dg.save()
    dg2 = DiagramGenerator(base_dir=tmp)
    test("DG: persistencia total_diagrams", dg2.total_diagrams >= 2)

    # Clear
    dg.clear()
    test("DG: clear resetea", dg.total_diagrams == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# VOICE PERSONALITY
# ============================================================
print("\n--- VoicePersonality ---")
from core.voice_personality import VocalStyle, EmotionalVoice, ProsodyRule, VoicePersonality

print("  VocalStyle...")
vs = VocalStyle()
test("VS: speed default 1.0", vs.speed == 1.0)
test("VS: pitch default 1.0", vs.pitch == 1.0)
test("VS: emphasis default 0.5", vs.emphasis_level == 0.5)
test("VS: pause default 0.3", vs.pause_frequency == 0.3)

vs.apply_adjustment(speed_delta=0.5, pitch_delta=-0.3)
test("VS: adjust speed", vs.speed == 1.5)
test("VS: adjust pitch", vs.pitch == 0.7)

# Clamping
vs2 = VocalStyle(speed=3.0, pitch=-1.0)
test("VS: clamp speed max 2.0", vs2.speed == 2.0)
test("VS: clamp pitch min 0.5", vs2.pitch == 0.5)

desc = vs.describe()
test("VS: describe retorna string", isinstance(desc, str))
test("VS: describe no vacio", len(desc) > 0)

vs_dict = vs.to_dict()
test("VS: to_dict tiene speed", "speed" in vs_dict)
vs3 = VocalStyle.from_dict(vs_dict)
test("VS: from_dict preserva speed", vs3.speed == vs.speed)

print("  EmotionalVoice...")
ev = EmotionalVoice()
test("EV: 8 emociones", len(ev.EMOTION_ADJUSTMENTS) == 8)
test("EV: frustracion existe", "frustracion" in ev.EMOTION_ADJUSTMENTS)
test("EV: alegria existe", "alegria" in ev.EMOTION_ADJUSTMENTS)
test("EV: neutral existe", "neutral" in ev.EMOTION_ADJUSTMENTS)

adj = ev.get_adjustment("frustracion")
test("EV: adjustment tiene speed_delta", "speed_delta" in adj)
test("EV: adjustment tiene description", "description" in adj)

adj_unknown = ev.get_adjustment("desconocida")
test("EV: emocion desconocida usa neutral", adj_unknown == ev.EMOTION_ADJUSTMENTS["neutral"])

style = VocalStyle()
ev.apply_to_style(style, "alegria", intensity=1.0)
test("EV: apply aumenta speed para alegria", style.speed > 1.0)
test("EV: apply aumenta pitch para alegria", style.pitch > 1.0)

# Intensity scaling
style2 = VocalStyle()
ev.apply_to_style(style2, "alegria", intensity=0.5)
test("EV: intensity 0.5 ajusta menos", style2.speed < style.speed)

test("EV: list_emotions retorna lista", len(ev.list_emotions()) == 8)

print("  ProsodyRule...")
test("PR: 6 content types", len(ProsodyRule.CONTENT_RULES) == 6)
test("PR: explanation existe", "explanation" in ProsodyRule.CONTENT_RULES)
test("PR: code existe", "code" in ProsodyRule.CONTENT_RULES)

pr = ProsodyRule("explanation")
test("PR: condition no vacia", len(pr.condition) > 0)
test("PR: description no vacia", len(pr.description) > 0)

style3 = VocalStyle()
pr.apply(style3)
test("PR: apply ajusta pausas", style3.pause_frequency > 0.3)

test("PR: list_content_types retorna 6", len(ProsodyRule.list_content_types()) == 6)

print("  VoicePersonality coordinator...")
tmp = tempfile.mkdtemp()
try:
    vp = VoicePersonality(base_dir=tmp)
    test("VP: init sin adaptaciones", vp.total_adaptations == 0)
    test("VP: emocion neutral", vp.current_emotion == "neutral")

    result = vp.adapt_to_emotion("alegria", intensity=0.8)
    test("VP: adapt retorna dict", isinstance(result, dict))
    test("VP: adapt tiene emotion", result["emotion"] == "alegria")
    test("VP: adapt tiene vocal_directives", "vocal_directives" in result)
    test("VP: total_adaptations incrementa", vp.total_adaptations == 1)
    test("VP: current_emotion actualizada", vp.current_emotion == "alegria")

    result2 = vp.adapt_to_content("code")
    test("VP: adapt_content retorna dict", isinstance(result2, dict))
    test("VP: adapt_content tiene content_type", result2["content_type"] == "code")
    test("VP: total_adaptations 2", vp.total_adaptations == 2)

    # Directives
    directives = vp.get_vocal_directives()
    test("VP: directives no vacio", len(directives) > 0)

    # Context
    ctx = vp.get_context_for_prompt(emotion="frustracion", max_chars=200)
    test("VP: context con emocion", len(ctx) > 0)
    test("VP: context contiene VOZ", "VOZ" in ctx)

    ctx_empty = vp.get_context_for_prompt()
    test("VP: context no vacio con estado actual", len(ctx_empty) > 0)

    # Stats
    stats = vp.get_stats()
    test("VP: stats tiene total_adaptations", stats["total_adaptations"] >= 2)
    test("VP: stats tiene emotion_counts", "emotion_counts" in stats)

    # Status / report
    test("VP: status string", isinstance(vp.status(), str))
    report = vp.generate_report()
    test("VP: report contiene VOICE", "VOICE" in report)

    # Save/load
    vp.save()
    vp2 = VoicePersonality(base_dir=tmp)
    test("VP: persistencia total_adaptations", vp2.total_adaptations >= 2)
    test("VP: persistencia current_emotion", vp2.current_emotion != "neutral")

    # Clear
    vp.clear()
    test("VP: clear resetea", vp.total_adaptations == 0)
    test("VP: clear emocion neutral", vp.current_emotion == "neutral")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# VERSION CHECK
# ============================================================
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 3.3", float(f"{major}.{minor}") >= 3.3)

# ============================================================
# INTEGRATION CHECK
# ============================================================
print("\n--- Integration Check ---")
genesis_path = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
# El refactor a MIXINS movio codigo de genesis.py a core/genesis_*.py.
# Concatenamos las fuentes para verificar la integracion real.
with open(genesis_path, "r", encoding="utf-8") as f:
    genesis_src = f.read()
for _mod in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    with open(os.path.join(os.path.dirname(__file__), "..", "core", _mod), "r", encoding="utf-8") as f:
        genesis_src += "\n" + f.read()

test("Int: import ImageAnalyzer", "from core.image_analyzer import ImageAnalyzer" in genesis_src)
test("Int: import DiagramGenerator", "from core.diagram_generator import DiagramGenerator" in genesis_src)
test("Int: import VoicePersonality", "from core.voice_personality import VoicePersonality" in genesis_src)
# Init lazy: instanciacion dentro de _init_lazy_module en genesis.py
test("Int: init image_analyzer", "ImageAnalyzer(" in genesis_src)
test("Int: init diagram_generator", "DiagramGenerator(" in genesis_src)
test("Int: init voice_personality", "VoicePersonality(" in genesis_src)
# save_all() usa la lista saveable_modules con el nombre del modulo
test("Int: image_analyzer.save()", '"image_analyzer"' in genesis_src)
test("Int: diagram_generator.save()", '"diagram_generator"' in genesis_src)
test("Int: voice_personality.save()", '"voice_personality"' in genesis_src)
test("Int: cmd /images", "/images" in genesis_src)
test("Int: cmd /diagrams", "/diagrams" in genesis_src)
test("Int: cmd /voice", "/voice" in genesis_src)
test("Int: status IMAGE ANALYZER", "IMAGE ANALYZER" in genesis_src)
test("Int: status DIAGRAM GENERATOR", "DIAGRAM GENERATOR" in genesis_src)
test("Int: status VOICE PERSONALITY", "VOICE PERSONALITY" in genesis_src)

webui_path = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(webui_path, "r", encoding="utf-8") as f:
    webui_src = f.read()
test("WebUI: ImageAnalyzer", "ImageAnalyzer" in webui_src)
test("WebUI: DiagramGenerator", "DiagramGenerator" in webui_src)
test("WebUI: VoicePersonality", "VoicePersonality" in webui_src)
test("WebUI: image_analyzer stats", "image_analyzer" in webui_src)
test("WebUI: diagram_generator stats", "diagram_generator" in webui_src)
test("WebUI: voice_personality stats", "voice_personality" in webui_src)

# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")
print("=" * 60)
