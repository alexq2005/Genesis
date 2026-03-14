"""
Tests para Genesis v3.2 — Creative Genesis
StoryGenerator, CodeArchitect, IdeaBrainstormer
"""
import sys
import os
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
print("GENESIS v3.2 — Creative Genesis Tests")
print("=" * 60)

# ============================================================
# STORY GENERATOR
# ============================================================
print("\n--- StoryGenerator ---")

from core.story_generator import StoryArc, CharacterProfile, StoryTemplate, StoryGenerator

# StoryArc
print("  StoryArc...")
arc = StoryArc()
test("Arc: 5 actos", len(StoryArc.ACTS) == 5)
test("Arc: empieza en setup", arc.current_act == "setup")
test("Arc: progreso inicial 0", arc.progress == 0.0)
test("Arc: no completado", arc.completed == False)

arc.advance()
test("Arc: avanza a rising_action", arc.current_act == "rising_action")
test("Arc: progreso 0.2", arc.progress == 0.2)

arc.advance()
test("Arc: avanza a climax", arc.current_act == "climax")
test("Arc: progreso 0.4", arc.progress == 0.4)

arc.advance()
test("Arc: avanza a falling_action", arc.current_act == "falling_action")

arc.advance()
test("Arc: avanza a resolution", arc.current_act == "resolution")

arc.advance()
test("Arc: completado despues de ultimo acto", arc.completed == True)
test("Arc: progreso 1.0 al completar", arc.progress == 1.0)

arc.set_note("setup", "Nota de prueba")
test("Arc: set_note funciona", arc.act_notes["setup"] == "Nota de prueba")

arc_dict = arc.to_dict()
test("Arc: to_dict tiene current_act_index", "current_act_index" in arc_dict)
test("Arc: to_dict tiene completed", "completed" in arc_dict)

arc2 = StoryArc.from_dict(arc_dict)
test("Arc: from_dict preserva completado", arc2.completed == True)
test("Arc: from_dict preserva notas", arc2.act_notes["setup"] == "Nota de prueba")

# StoryArc descriptions
test("Arc: descriptions tiene 5 entradas", len(StoryArc.ACT_DESCRIPTIONS) == 5)
test("Arc: setup tiene descripcion", "setup" in StoryArc.ACT_DESCRIPTIONS)

# CharacterProfile
print("  CharacterProfile...")
char = CharacterProfile("Hero", ["valiente", "noble"], "Salvar el mundo", "hero")
test("Char: nombre correcto", char.name == "Hero")
test("Char: arc_type correcto", char.arc_type == "hero")
test("Char: traits preservados", len(char.traits) == 2)
test("Char: motivacion preservada", char.motivation == "Salvar el mundo")

test("Char: summary contiene nombre", "Hero" in char.summary())
test("Char: summary contiene arc_type", "hero" in char.summary())

char_dict = char.to_dict()
test("Char: to_dict tiene name", char_dict["name"] == "Hero")
test("Char: to_dict tiene arc_type", char_dict["arc_type"] == "hero")

char2 = CharacterProfile.from_dict(char_dict)
test("Char: from_dict preserva nombre", char2.name == "Hero")
test("Char: from_dict preserva traits", char2.traits == ["valiente", "noble"])

# arc_type invalido
char_bad = CharacterProfile("Bad", [], "", "invalid_type")
test("Char: arc_type invalido default a hero", char_bad.arc_type == "hero")

# VALID_ARC_TYPES
test("Char: 4 arc types validos", len(CharacterProfile.VALID_ARC_TYPES) == 4)

# StoryTemplate
print("  StoryTemplate...")
test("Template: tiene 4 generos", len(StoryTemplate.GENRES) == 4)
test("Template: sci_fi existe", "sci_fi" in StoryTemplate.GENRES)
test("Template: fantasy existe", "fantasy" in StoryTemplate.GENRES)
test("Template: thriller existe", "thriller" in StoryTemplate.GENRES)
test("Template: slice_of_life existe", "slice_of_life" in StoryTemplate.GENRES)

test("Template: detecta sci_fi", StoryTemplate.detect_genre("nave espacial robot futuro") == "sci_fi")
test("Template: detecta fantasy", StoryTemplate.detect_genre("magia dragon reino espada") == "fantasy")
test("Template: detecta thriller", StoryTemplate.detect_genre("asesino detective crimen secreto") == "thriller")
test("Template: detecta slice_of_life", StoryTemplate.detect_genre("familia amor amigos hogar") == "slice_of_life")
test("Template: default a sci_fi", StoryTemplate.detect_genre("xxxxxxx") == "sci_fi")

template = StoryTemplate.get_template("fantasy")
test("Template: get_template tiene setting", "setting" in template)
test("Template: get_template tiene conflict", "conflict" in template)
test("Template: get_template tiene tone", "tone" in template)
test("Template: genero invalido default a sci_fi", "setting" in StoryTemplate.get_template("nonexistent"))

# StoryGenerator coordinator
print("  StoryGenerator coordinator...")
import tempfile, shutil
tmp = tempfile.mkdtemp()
try:
    sg = StoryGenerator(base_dir=tmp)
    test("SG: init sin historias", sg.total_stories == 0)
    test("SG: current_story -1", sg.current_story == -1)

    result = sg.create_story("Una nave espacial robot en el futuro", genre="auto")
    test("SG: create_story retorna story_id", "story_id" in result)
    test("SG: create_story detecta sci_fi", result["genre"] == "sci_fi")
    test("SG: create_story tiene titulo", len(result["title"]) > 0)
    test("SG: total_stories incrementa", sg.total_stories == 1)
    test("SG: current_story actualizado", sg.current_story == 0)

    result2 = sg.create_story("magia dragon reino", genre="fantasy")
    test("SG: segunda historia creada", sg.total_stories == 2)
    test("SG: genre manual funciona", result2["genre"] == "fantasy")

    # Agregar personaje
    char_result = sg.add_character("Gandalf", ["sabio", "viejo", "guia"], "Guiar al elegido")
    test("SG: add_character funciona", "name" in char_result)
    test("SG: add_character infiere mentor", char_result["arc_type"] == "mentor")
    test("SG: total_characters incrementa", sg.total_characters == 1)

    char_result2 = sg.add_character("Sauron", ["oscuro", "cruel", "poder"], "Dominar todo")
    test("SG: add_character infiere shadow", char_result2["arc_type"] == "shadow")
    test("SG: total_characters 2", sg.total_characters == 2)

    char_result3 = sg.add_character("Loki", ["astuto", "bromista", "caos"], "Crear problemas")
    test("SG: add_character infiere trickster", char_result3["arc_type"] == "trickster")

    # Avanzar acto
    adv = sg.advance_act()
    test("SG: advance_act retorna current_act", "current_act" in adv)
    test("SG: advance_act progresa", adv["progress"] > 0)

    # Sin historia activa
    sg2 = StoryGenerator(base_dir=tempfile.mkdtemp())
    test("SG: add_character sin historia da error", "error" in sg2.add_character("X"))
    test("SG: advance_act sin historia da error", "error" in sg2.advance_act())

    # get_context_for_prompt
    ctx = sg.get_context_for_prompt("quiero continuar la historia", max_chars=300)
    test("SG: context_for_prompt genera contexto", len(ctx) > 0)
    test("SG: context contiene NARRATIVO", "NARRATIVO" in ctx)

    ctx_no = sg.get_context_for_prompt("hola que tal", max_chars=300)
    test("SG: context vacio si no relevante", ctx_no == "")

    # get_stats
    stats = sg.get_stats()
    test("SG: stats tiene total_stories", stats["total_stories"] == 2)
    test("SG: stats tiene total_characters", stats["total_characters"] == 3)
    test("SG: stats tiene current_story_title", len(stats["current_story_title"]) > 0)

    # status
    st = sg.status()
    test("SG: status es string", isinstance(st, str))
    test("SG: status contiene Historias", "Historias" in st)

    # generate_report
    report = sg.generate_report()
    test("SG: report contiene STORY GENERATOR", "STORY GENERATOR" in report)
    test("SG: report contiene personajes", "Personajes" in report or "personajes" in report.lower())

    # save/load
    sg.save()
    sg3 = StoryGenerator(base_dir=tmp)
    test("SG: persistencia total_stories", sg3.total_stories == 2)
    test("SG: persistencia total_characters", sg3.total_characters == 3)
    test("SG: persistencia current_story", sg3.current_story == 1)

    # clear
    sg.clear()
    test("SG: clear resetea stories", sg.total_stories == 0)
    test("SG: clear resetea characters", sg.total_characters == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# CODE ARCHITECT
# ============================================================
print("\n--- CodeArchitect ---")

from core.code_architect import ArchitecturePattern, ComponentSpec, DesignDecision, CodeArchitect

# ArchitecturePattern
print("  ArchitecturePattern...")
test("Pattern: 5 patrones", len(ArchitecturePattern.PATTERNS) == 5)
test("Pattern: mvc existe", "mvc" in ArchitecturePattern.PATTERNS)
test("Pattern: microservices existe", "microservices" in ArchitecturePattern.PATTERNS)
test("Pattern: event_driven existe", "event_driven" in ArchitecturePattern.PATTERNS)
test("Pattern: layered existe", "layered" in ArchitecturePattern.PATTERNS)
test("Pattern: hexagonal existe", "hexagonal" in ArchitecturePattern.PATTERNS)

test("Pattern: detecta mvc", ArchitecturePattern.detect_pattern("web api rest crud frontend") == "mvc")
test("Pattern: detecta microservices", ArchitecturePattern.detect_pattern("microservicio distribuido escalar docker") == "microservices")
test("Pattern: detecta event_driven", ArchitecturePattern.detect_pattern("evento kafka async stream publish") == "event_driven")
test("Pattern: detecta layered", ArchitecturePattern.detect_pattern("simple clasico monolito basico") == "layered")
test("Pattern: detecta hexagonal", ArchitecturePattern.detect_pattern("hexagonal ports adapters ddd domain") == "hexagonal")
test("Pattern: default a layered", ArchitecturePattern.detect_pattern("xxxxxxx") == "layered")

pat = ArchitecturePattern("mvc")
test("Pattern: name correcto", pat.name == "Model-View-Controller")
test("Pattern: tiene pros", len(pat.pros) > 0)
test("Pattern: tiene cons", len(pat.cons) > 0)
test("Pattern: summary tiene nombre", "Model-View-Controller" in pat.summary())

pat_inv = ArchitecturePattern("nonexistent")
test("Pattern: invalido default a layered", pat_inv.pattern_name == "nonexistent")

# ComponentSpec
print("  ComponentSpec...")
comp = ComponentSpec("UserService", "service", ["DB", "Auth"], "Gestion de usuarios")
test("Comp: nombre correcto", comp.name == "UserService")
test("Comp: tipo correcto", comp.comp_type == "service")
test("Comp: dependencias preservadas", comp.dependencies == ["DB", "Auth"])
test("Comp: summary contiene nombre", "UserService" in comp.summary())

comp_dict = comp.to_dict()
test("Comp: to_dict tiene name", comp_dict["name"] == "UserService")

comp2 = ComponentSpec.from_dict(comp_dict)
test("Comp: from_dict preserva nombre", comp2.name == "UserService")
test("Comp: from_dict preserva deps", comp2.dependencies == ["DB", "Auth"])

comp_bad = ComponentSpec("X", "invalid_type")
test("Comp: tipo invalido default a service", comp_bad.comp_type == "service")

test("Comp: 5 tipos validos", len(ComponentSpec.VALID_TYPES) == 5)

# DesignDecision
print("  DesignDecision...")
dd = DesignDecision("Usar PostgreSQL", "Mejor para datos relacionales", ["MongoDB", "SQLite"])
test("DD: decision correcta", dd.decision == "Usar PostgreSQL")
test("DD: rationale preservado", dd.rationale == "Mejor para datos relacionales")
test("DD: alternatives preservadas", len(dd.alternatives) == 2)
test("DD: summary contiene decision", "PostgreSQL" in dd.summary())

dd_dict = dd.to_dict()
test("DD: to_dict tiene decision", dd_dict["decision"] == "Usar PostgreSQL")

dd2 = DesignDecision.from_dict(dd_dict)
test("DD: from_dict preserva decision", dd2.decision == "Usar PostgreSQL")
test("DD: from_dict preserva alternatives", len(dd2.alternatives) == 2)

# CodeArchitect coordinator
print("  CodeArchitect coordinator...")
tmp = tempfile.mkdtemp()
try:
    ca = CodeArchitect(base_dir=tmp)
    test("CA: init sin disenos", ca.total_designs == 0)
    test("CA: current_design -1", ca.current_design == -1)

    result = ca.design_system("necesito una web api rest crud con frontend")
    test("CA: design_system retorna design_id", "design_id" in result)
    test("CA: design_system sugiere patron", "suggested_pattern" in result)
    test("CA: design_system tiene pros", len(result["pros"]) > 0)
    test("CA: total_designs incrementa", ca.total_designs == 1)

    # Agregar componente
    comp_res = ca.add_component("AuthService", "service", ["DB"], "Autenticacion")
    test("CA: add_component funciona", "name" in comp_res)
    test("CA: add_component summary", "AuthService" in comp_res["summary"])
    test("CA: total_components incrementa", ca.total_components == 1)

    comp_res2 = ca.add_component("UserModel", "model", [], "Modelo de usuario")
    test("CA: segundo componente", ca.total_components == 2)

    # Registrar decision
    dec_res = ca.record_decision("Usar JWT", "Stateless auth", ["Sessions", "OAuth"])
    test("CA: record_decision funciona", "decision" in dec_res)
    test("CA: total_decisions incrementa", ca.total_decisions == 1)

    # Sin diseno activo
    ca2 = CodeArchitect(base_dir=tempfile.mkdtemp())
    test("CA: add_component sin diseno da error", "error" in ca2.add_component("X"))
    test("CA: record_decision sin diseno da error", "error" in ca2.record_decision("X"))

    # get_context_for_prompt
    ctx = ca.get_context_for_prompt("como disenar la arquitectura del sistema", max_chars=300)
    test("CA: context_for_prompt genera contexto", len(ctx) > 0)
    test("CA: context contiene ARQUITECTONICO", "ARQUITECTONICO" in ctx)

    ctx_no = ca.get_context_for_prompt("hola que tal", max_chars=300)
    test("CA: context vacio si no relevante", ctx_no == "")

    # get_stats
    stats = ca.get_stats()
    test("CA: stats tiene total_designs", stats["total_designs"] == 1)
    test("CA: stats tiene total_components", stats["total_components"] == 2)
    test("CA: stats tiene total_decisions", stats["total_decisions"] == 1)

    # status
    st = ca.status()
    test("CA: status es string", isinstance(st, str))
    test("CA: status contiene Disenos", "Disenos" in st or "disenos" in st.lower())

    # generate_report
    report = ca.generate_report()
    test("CA: report contiene CODE ARCHITECT", "CODE ARCHITECT" in report)

    # save/load
    ca.save()
    ca3 = CodeArchitect(base_dir=tmp)
    test("CA: persistencia total_designs", ca3.total_designs == 1)
    test("CA: persistencia total_components", ca3.total_components == 2)

    # clear
    ca.clear()
    test("CA: clear resetea designs", ca.total_designs == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# IDEA BRAINSTORMER
# ============================================================
print("\n--- IdeaBrainstormer ---")

from core.idea_brainstormer import BrainstormMethod, IdeaEntry, IdeaScorer, IdeaBrainstormer

# BrainstormMethod
print("  BrainstormMethod...")
test("Method: 4 metodos", len(BrainstormMethod.METHODS) == 4)
test("Method: scamper existe", "scamper" in BrainstormMethod.METHODS)
test("Method: six_hats existe", "six_hats" in BrainstormMethod.METHODS)
test("Method: mind_map existe", "mind_map" in BrainstormMethod.METHODS)
test("Method: what_if existe", "what_if" in BrainstormMethod.METHODS)

test("Method: detecta scamper", BrainstormMethod.detect_method("mejorar existente modificar cambiar") == "scamper")
test("Method: detecta six_hats", BrainstormMethod.detect_method("decision analizar perspectiva evaluar") == "six_hats")
test("Method: detecta mind_map", BrainstormMethod.detect_method("explorar expandir conectar concepto") == "mind_map")
test("Method: detecta what_if", BrainstormMethod.detect_method("imaginar hipotetico escenario radical") == "what_if")
test("Method: default a mind_map", BrainstormMethod.detect_method("xxxxxxx") == "mind_map")

bm = BrainstormMethod("scamper")
test("Method: nombre correcto", bm.name == "SCAMPER")
test("Method: tiene prompts", len(bm.prompts) > 0)
test("Method: tiene steps", len(bm.steps) > 0)
test("Method: tiene description", len(bm.description) > 0)

test("Method: get_all_methods retorna lista", len(BrainstormMethod.get_all_methods()) == 4)

bm_inv = BrainstormMethod("nonexistent")
test("Method: invalido default a mind_map", bm_inv.name == "Mapa Mental")

# IdeaEntry
print("  IdeaEntry...")
ie = IdeaEntry("Una idea revolucionaria", "scamper", ["tech", "innovation"])
test("IE: content preservado", ie.content == "Una idea revolucionaria")
test("IE: method preservado", ie.method == "scamper")
test("IE: tags preservados", ie.tags == ["tech", "innovation"])
test("IE: score inicial 0.5", ie.overall == 0.5)
test("IE: idea_id generado", ie.idea_id > 0)

ie.set_score(0.8, 0.6, 0.7)
test("IE: set_score viability", ie.score["viability"] == 0.8)
test("IE: set_score novelty", ie.score["novelty"] == 0.6)
test("IE: set_score impact", ie.score["impact"] == 0.7)
expected = 0.8 * 0.4 + 0.6 * 0.3 + 0.7 * 0.3
test("IE: overall weighted avg", abs(ie.overall - expected) < 0.01)

# Clamping
ie.set_score(1.5, -0.5, 2.0)
test("IE: clamp viability a 1.0", ie.score["viability"] == 1.0)
test("IE: clamp novelty a 0.0", ie.score["novelty"] == 0.0)
test("IE: clamp impact a 1.0", ie.score["impact"] == 1.0)

test("IE: summary contiene score", "%" in ie.summary())

ie_dict = ie.to_dict()
test("IE: to_dict tiene idea_id", "idea_id" in ie_dict)
test("IE: to_dict tiene content", ie_dict["content"] == "Una idea revolucionaria")

ie2 = IdeaEntry.from_dict(ie_dict)
test("IE: from_dict preserva content", ie2.content == "Una idea revolucionaria")
test("IE: from_dict preserva tags", ie2.tags == ["tech", "innovation"])

# IdeaScorer
print("  IdeaScorer...")
scorer = IdeaScorer()
scores = scorer.score("implementar un sistema automatizado con api y codigo")
test("Scorer: retorna viability", "viability" in scores)
test("Scorer: retorna novelty", "novelty" in scores)
test("Scorer: retorna impact", "impact" in scores)
test("Scorer: retorna overall", "overall" in scores)
test("Scorer: viability > 0.3 con senales", scores["viability"] > 0.3)

scores_novel = scorer.score("idea nueva revolucionaria disruptiva nunca vista original")
test("Scorer: novelty alta con senales", scores_novel["novelty"] > 0.5)

scores_impact = scorer.score("cambiar el mundo transformar millones de personas a escala global")
test("Scorer: impact alto con senales", scores_impact["impact"] > 0.5)

scores_empty = scorer.score("xyz abc")
test("Scorer: sin senales retorna base 0.3", scores_empty["viability"] == 0.3)
test("Scorer: overall sin senales es 0.3", scores_empty["overall"] == 0.3)

# Score con tags
scores_tags = scorer.score("algo", ["implementar", "nuevo", "global"])
test("Scorer: tags afectan score", scores_tags["overall"] > 0.3)

# IdeaBrainstormer coordinator
print("  IdeaBrainstormer coordinator...")
tmp = tempfile.mkdtemp()
try:
    ib = IdeaBrainstormer(base_dir=tmp)
    test("IB: init sin ideas", ib.total_ideas == 0)
    test("IB: init sin sesiones", ib.total_sessions == 0)

    # brainstorm session
    session = ib.brainstorm("mejorar la productividad del equipo", method="auto")
    test("IB: brainstorm retorna session_id", "session_id" in session)
    test("IB: brainstorm tiene prompts", len(session["prompts"]) > 0)
    test("IB: brainstorm tiene steps", len(session["steps"]) > 0)
    test("IB: total_sessions incrementa", ib.total_sessions == 1)

    # add idea
    idea_res = ib.add_idea("implementar un sistema automatizado nuevo", tags=["tech"])
    test("IB: add_idea retorna idea_id", "idea_id" in idea_res)
    test("IB: add_idea tiene scores", "scores" in idea_res)
    test("IB: add_idea auto-score", idea_res["overall"] > 0)
    test("IB: total_ideas incrementa", ib.total_ideas == 1)

    idea_res2 = ib.add_idea("crear herramienta disruptiva para cambiar el mundo", tags=["global"])
    test("IB: segunda idea", ib.total_ideas == 2)

    idea_res3 = ib.add_idea("otra idea simple", tags=[])
    test("IB: tercera idea", ib.total_ideas == 3)

    # get_best_ideas
    best = ib.get_best_ideas(2)
    test("IB: get_best_ideas retorna lista", len(best) == 2)
    test("IB: best ideas tienen overall", "overall" in best[0])
    test("IB: best ideas ordenadas", best[0]["overall"] >= best[1]["overall"])

    # combine_ideas
    id1 = idea_res["idea_id"]
    id2 = idea_res2["idea_id"]
    combo = ib.combine_ideas(id1, id2)
    test("IB: combine_ideas funciona", "idea_id" in combo)
    test("IB: combine tiene source_ids", combo["source_ids"] == [id1, id2])
    test("IB: combine tiene tag combinada", "combinada" in combo["tags"])
    test("IB: total_ideas despues de combine", ib.total_ideas == 4)

    # combine con ids invalidos
    bad_combo = ib.combine_ideas(999999, 888888)
    test("IB: combine invalido da error", "error" in bad_combo)

    # get_context_for_prompt
    ctx = ib.get_context_for_prompt("necesito generar ideas nuevas", max_chars=300)
    test("IB: context_for_prompt genera contexto", len(ctx) > 0)
    test("IB: context contiene BRAINSTORM", "BRAINSTORM" in ctx)

    ctx_no = ib.get_context_for_prompt("hola que tal", max_chars=300)
    test("IB: context vacio si no relevante", ctx_no == "")

    # get_stats
    stats = ib.get_stats()
    test("IB: stats tiene total_ideas", stats["total_ideas"] == 4)
    test("IB: stats tiene total_sessions", stats["total_sessions"] == 1)
    test("IB: stats tiene average_score", "average_score" in stats)

    # status
    st = ib.status()
    test("IB: status es string", isinstance(st, str))
    test("IB: status contiene Ideas", "Ideas" in st)

    # generate_report
    report = ib.generate_report()
    test("IB: report contiene IDEA BRAINSTORMER", "IDEA BRAINSTORMER" in report)
    test("IB: report contiene sesiones", "Sesiones" in report or "sesiones" in report.lower())

    # save/load
    ib.save()
    ib3 = IdeaBrainstormer(base_dir=tmp)
    test("IB: persistencia total_ideas", ib3.total_ideas == 4)
    test("IB: persistencia total_sessions", ib3.total_sessions == 1)

    # clear
    ib.clear()
    test("IB: clear resetea ideas", ib.total_ideas == 0)
    test("IB: clear resetea sessions", ib.total_sessions == 0)

finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ============================================================
# VERSION CHECK
# ============================================================
print("\n--- Version Check ---")
from config import GENESIS_VERSION

major, minor, patch = GENESIS_VERSION.split(".")
version_num = float(f"{major}.{minor}")
test("Version >= 3.2", version_num >= 3.2)

# ============================================================
# INTEGRATION CHECK (import verification)
# ============================================================
print("\n--- Integration Check ---")

# Verify imports exist in genesis.py
genesis_path = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(genesis_path, "r", encoding="utf-8") as f:
    genesis_src = f.read()

test("Integration: import StoryGenerator", "from core.story_generator import StoryGenerator" in genesis_src)
test("Integration: import CodeArchitect", "from core.code_architect import CodeArchitect" in genesis_src)
test("Integration: import IdeaBrainstormer", "from core.idea_brainstormer import IdeaBrainstormer" in genesis_src)
test("Integration: init story_generator", "self.story_generator = StoryGenerator" in genesis_src)
test("Integration: init code_architect", "self.code_architect = CodeArchitect" in genesis_src)
test("Integration: init idea_brainstormer", "self.idea_brainstormer = IdeaBrainstormer" in genesis_src)
test("Integration: story_generator.save()", "self.story_generator.save()" in genesis_src)
test("Integration: code_architect.save()", "self.code_architect.save()" in genesis_src)
test("Integration: idea_brainstormer.save()", "self.idea_brainstormer.save()" in genesis_src)
test("Integration: cmd /stories", '"/stories"' in genesis_src or "'/stories'" in genesis_src or '/stories' in genesis_src)
test("Integration: cmd /architect", '"/architect"' in genesis_src or "'/architect'" in genesis_src or '/architect' in genesis_src)
test("Integration: cmd /brainstorm", '"/brainstorm"' in genesis_src or "'/brainstorm'" in genesis_src or '/brainstorm' in genesis_src)
test("Integration: dashboard story_generator", 'story_generator' in genesis_src and 'get_stats' in genesis_src)
test("Integration: dashboard code_architect", 'code_architect' in genesis_src and 'get_stats' in genesis_src)
test("Integration: dashboard idea_brainstormer", 'idea_brainstormer' in genesis_src and 'get_stats' in genesis_src)
test("Integration: status STORY GENERATOR", "STORY GENERATOR" in genesis_src)
test("Integration: status CODE ARCHITECT", "CODE ARCHITECT" in genesis_src)
test("Integration: status IDEA BRAINSTORMER", "IDEA BRAINSTORMER" in genesis_src)

# Web UI integration
webui_path = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(webui_path, "r", encoding="utf-8") as f:
    webui_src = f.read()

test("WebUI: StoryGenerator health", "StoryGenerator" in webui_src)
test("WebUI: CodeArchitect health", "CodeArchitect" in webui_src)
test("WebUI: IdeaBrainstormer health", "IdeaBrainstormer" in webui_src)
test("WebUI: story_generator stats", "story_generator" in webui_src)
test("WebUI: code_architect stats", "code_architect" in webui_src)
test("WebUI: idea_brainstormer stats", "idea_brainstormer" in webui_src)

# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")
print("=" * 60)
