"""
GENESIS — Tests v2.6: Cognitive Architecture
Tests para CausalReasoner, ConceptSynthesizer, StrategicPlanner
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
print("GENESIS v2.6 — Test Suite: Cognitive Architecture")
print("=" * 60)

# ============================================================
# CAUSAL REASONER TESTS
# ============================================================
print("\n--- CausalLink ---")
from core.causal_reasoner import CausalLink, CausalGraph, CausalInference, CausalReasoner

# CausalLink basics
link = CausalLink("lluvia", "inundacion", confidence=0.6, evidence="observacion", domain="clima")
test("CausalLink: causa correcta", link.cause == "lluvia")
test("CausalLink: efecto correcto", link.effect == "inundacion")
test("CausalLink: confianza correcta", link.confidence == 0.6)
test("CausalLink: dominio correcto", link.domain == "clima")
test("CausalLink: evidence correcto", link.evidence == "observacion")
test("CausalLink: id generado", len(link.link_id) == 10)
test("CausalLink: reinforcements inicial = 1", link.reinforcements == 1)
test("CausalLink: contradictions inicial = 0", link.contradictions == 0)

# strength property
test("CausalLink: strength = confidence al inicio", link.strength == 0.6)

# reinforce
link.reinforce("mas evidencia")
test("CausalLink: reinforce sube confidence", link.confidence == 0.65)
test("CausalLink: reinforce incrementa reinforcements", link.reinforcements == 2)
test("CausalLink: reinforce actualiza evidence", link.evidence == "mas evidencia")

# contradict
link.contradict()
test("CausalLink: contradict baja confidence", link.confidence == 0.55)
test("CausalLink: contradict incrementa contradictions", link.contradictions == 1)

# strength con contradiccion
ratio = link.reinforcements / (link.reinforcements + link.contradictions)
expected_strength = link.confidence * ratio
test("CausalLink: strength ajustada por ratio", abs(link.strength - expected_strength) < 0.01)

# to_dict / from_dict
d = link.to_dict()
test("CausalLink: to_dict tiene 'cause'", d["cause"] == "lluvia")
link2 = CausalLink.from_dict(d)
test("CausalLink: from_dict restaura cause", link2.cause == "lluvia")
test("CausalLink: from_dict restaura confidence", abs(link2.confidence - 0.55) < 0.01)
test("CausalLink: from_dict restaura reinforcements", link2.reinforcements == 2)

# Confidence bounds
link_max = CausalLink("a", "b", confidence=2.0)
test("CausalLink: confidence clamped max 1.0", link_max.confidence == 1.0)
link_min = CausalLink("a", "b", confidence=-0.5)
test("CausalLink: confidence clamped min 0.0", link_min.confidence == 0.0)

# Evidence truncation
long_evidence = "x" * 500
link_trunc = CausalLink("a", "b", evidence=long_evidence)
test("CausalLink: evidence truncada a 300", len(link_trunc.evidence) == 300)

# CausalLink cause/effect normalization
link_norm = CausalLink("  FUEGO  ", "  HUMO  ")
test("CausalLink: causa normalizada", link_norm.cause == "fuego")
test("CausalLink: efecto normalizado", link_norm.effect == "humo")

print("\n--- CausalGraph ---")
graph = CausalGraph()

l1 = CausalLink("fuego", "humo")
l2 = CausalLink("humo", "alarma")
l3 = CausalLink("alarma", "evacuacion")
l4 = CausalLink("cortocircuito", "fuego")

graph.add_link(l1)
graph.add_link(l2)
graph.add_link(l3)
graph.add_link(l4)

test("CausalGraph: 4 links", graph.link_count == 4)
test("CausalGraph: node_count", graph.node_count == 5)

# get_causes_of
causes_of_humo = graph.get_causes_of("humo")
test("CausalGraph: causes of humo", len(causes_of_humo) >= 1)
test("CausalGraph: cause of humo is fuego", causes_of_humo[0].cause == "fuego")

# get_effects_of
effects_of_fuego = graph.get_effects_of("fuego")
test("CausalGraph: effects of fuego", len(effects_of_fuego) >= 1)
test("CausalGraph: effect of fuego is humo", effects_of_fuego[0].effect == "humo")

# Refuerzo automático (add_link duplicado)
l_dup = CausalLink("fuego", "humo", evidence="nueva evidencia")
graph.add_link(l_dup)
test("CausalGraph: duplicado reforzado, no duplicado", graph.link_count == 4)
fuego_link = [l for l in graph.links.values() if l.cause == "fuego" and l.effect == "humo"][0]
test("CausalGraph: link reforzado tiene reinforcements > 1", fuego_link.reinforcements > 1)

# trace_chain (BFS forward)
chains = graph.trace_chain("cortocircuito", max_depth=5)
test("CausalGraph: trace_chain produce cadenas", len(chains) >= 1)
# Debería encontrar cortocircuito -> fuego -> humo -> alarma -> evacuacion
all_effects = set()
for level in chains:
    for l in level:
        all_effects.add(l.effect)
test("CausalGraph: chain contiene 'fuego'", "fuego" in all_effects)

# trace_reverse (BFS backward)
reverse = graph.trace_reverse("evacuacion", max_depth=5)
test("CausalGraph: trace_reverse produce cadenas", len(reverse) >= 1)
all_causes = set()
for level in reverse:
    for l in level:
        all_causes.add(l.cause)
test("CausalGraph: reverse contiene 'alarma'", "alarma" in all_causes)

# strongest_links
strongest = graph.strongest_links(2)
test("CausalGraph: strongest_links retorna lista", len(strongest) <= 2)

# to_dict / load_dict
gd = graph.to_dict()
test("CausalGraph: to_dict tiene links", len(gd["links"]) == 4)
graph2 = CausalGraph()
graph2.load_dict(gd)
test("CausalGraph: load_dict restaura links", graph2.link_count == 4)
test("CausalGraph: load_dict restaura nodes", graph2.node_count == 5)

print("\n--- CausalInference ---")
inf = CausalInference()

# extract_causal_pairs
text1 = "la falta de agua causa deshidratacion. La contaminacion provoca enfermedades."
pairs1 = inf.extract_causal_pairs(text1)
test("CausalInference: extrae pares causales", len(pairs1) >= 1)

# Pattern: porque (invertir)
text2 = "el paciente murio porque no recibio tratamiento"
pairs2 = inf.extract_causal_pairs(text2)
test("CausalInference: pattern 'porque' detectado", len(pairs2) >= 1)

# Pattern: si...entonces
text3 = "si llueve entonces hay inundacion"
pairs3 = inf.extract_causal_pairs(text3)
test("CausalInference: pattern 'si entonces' detectado", len(pairs3) >= 1)

# Pattern: lleva a
text4 = "la deforestacion lleva a la erosion"
pairs4 = inf.extract_causal_pairs(text4)
test("CausalInference: pattern 'lleva a' detectado", len(pairs4) >= 1)

# is_causal_question
test("CausalInference: detecta 'por que'", inf.is_causal_question("por que llueve?"))
test("CausalInference: detecta 'que causa'", inf.is_causal_question("que causa la lluvia?"))
test("CausalInference: detecta 'que pasa si'", inf.is_causal_question("que pasa si no llueve?"))
test("CausalInference: no detecta pregunta normal", not inf.is_causal_question("como estas?"))

# build_explanation
test_chains = [[CausalLink("fuego", "humo", confidence=0.8)]]
explanation = inf.build_explanation(test_chains, question="por que hay humo?")
test("CausalInference: explanation no vacia", len(explanation) > 0)
test("CausalInference: explanation contiene causa", "fuego" in explanation)

# build_explanation vacia
test("CausalInference: explanation vacia si no hay chains", inf.build_explanation([]) == "")

print("\n--- CausalReasoner ---")
tmp_dir = tempfile.mkdtemp()

try:
    cr = CausalReasoner(base_dir=tmp_dir)
    test("CausalReasoner: inicializado", cr.graph.link_count == 0)

    # extract_and_store
    stored = cr.extract_and_store("la contaminacion causa enfermedades respiratorias")
    test("CausalReasoner: extract_and_store retorna > 0", stored > 0)
    test("CausalReasoner: graph tiene links", cr.graph.link_count > 0)
    test("CausalReasoner: total_extracted incrementado", cr.total_extracted > 0)

    # why
    cr.graph.add_link(CausalLink("estres", "insomnio"))
    cr.graph.add_link(CausalLink("insomnio", "fatiga"))
    explanation = cr.why("fatiga")
    test("CausalReasoner: why retorna explicacion", len(explanation) > 0)
    test("CausalReasoner: total_queries incrementado", cr.total_queries > 0)

    # what_if
    what_if = cr.what_if("estres")
    test("CausalReasoner: what_if retorna explicacion", len(what_if) > 0)

    # get_context_for_prompt
    ctx = cr.get_context_for_prompt("por que hay fatiga?")
    test("CausalReasoner: context para pregunta causal", len(ctx) > 0)

    ctx_no = cr.get_context_for_prompt("hola como estas?")
    test("CausalReasoner: sin context para pregunta no causal", ctx_no == "")

    # add_manual_link
    lid = cr.add_manual_link("calor", "expansion", confidence=0.8)
    test("CausalReasoner: add_manual_link retorna id", len(lid) > 0)

    # get_stats
    stats = cr.get_stats()
    test("CausalReasoner: stats tiene total_links", "total_links" in stats)
    test("CausalReasoner: stats tiene total_nodes", "total_nodes" in stats)

    # status
    st = cr.status()
    test("CausalReasoner: status no vacio", len(st) > 0)

    # generate_report
    report = cr.generate_report()
    test("CausalReasoner: report contiene titulo", "CAUSAL REASONER" in report)

    # save / load
    cr.save()
    cr2 = CausalReasoner(base_dir=tmp_dir)
    test("CausalReasoner: persistencia links", cr2.graph.link_count > 0)
    test("CausalReasoner: persistencia total_extracted", cr2.total_extracted > 0)

    # clear
    cr.clear()
    test("CausalReasoner: clear limpia graph", cr.graph.link_count == 0)
    test("CausalReasoner: clear limpia totals", cr.total_extracted == 0)

    # disabled
    cr.enabled = False
    stored_disabled = cr.extract_and_store("algo causa algo")
    test("CausalReasoner: disabled no extrae", stored_disabled == 0)
    cr.enabled = True

    # empty text
    stored_empty = cr.extract_and_store("")
    test("CausalReasoner: texto vacio retorna 0", stored_empty == 0)

    # _extract_subject
    subj = cr._extract_subject("por que llueve mucho?")
    test("CausalReasoner: extract_subject funciona", len(subj) > 0)

    # Eviction
    cr_evict = CausalReasoner(base_dir=tmp_dir)
    cr_evict.max_links = 5
    for i in range(10):
        cr_evict.graph.add_link(CausalLink(f"causa_{i}", f"efecto_{i}"))
    cr_evict._evict()
    test("CausalReasoner: eviction reduce a max_links", cr_evict.graph.link_count <= 5)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)

# ============================================================
# CONCEPT SYNTHESIZER TESTS
# ============================================================
print("\n--- Concept ---")
from core.concept_synthesizer import (
    Concept, Synthesis, AnalogyFinder, SynthesisEngine, ConceptSynthesizer
)

c1 = Concept("red neuronal", domain="ia_ml", properties=["adaptativo", "jerarquico", "distribuido"])
test("Concept: nombre correcto", c1.name == "red neuronal")
test("Concept: dominio correcto", c1.domain == "ia_ml")
test("Concept: properties correctas", len(c1.properties) == 3)
test("Concept: id generado", len(c1.concept_id) == 10)
test("Concept: usage_count = 0", c1.usage_count == 0)
test("Concept: synthesis_count = 0", c1.synthesis_count == 0)

c2 = Concept("ecosistema", domain="biologia", properties=["adaptativo", "distribuido", "robusto"])

# similarity
sim = c1.similarity(c2)
test("Concept: similarity > 0 (props compartidas)", sim > 0)

# is_cross_domain
test("Concept: is_cross_domain ia/bio", c1.is_cross_domain(c2))
c3 = Concept("perceptron", domain="ia_ml")
test("Concept: not cross_domain same domain", not c1.is_cross_domain(c3))

# similarity with no properties
c_empty = Concept("vacio")
test("Concept: similarity 0 sin properties", c1.similarity(c_empty) == 0.0)

# to_dict / from_dict
cd = c1.to_dict()
test("Concept: to_dict tiene name", cd["name"] == "red neuronal")
c_restored = Concept.from_dict(cd)
test("Concept: from_dict restaura name", c_restored.name == "red neuronal")
test("Concept: from_dict restaura domain", c_restored.domain == "ia_ml")
test("Concept: from_dict restaura properties", len(c_restored.properties) == 3)

# Name/domain normalization
c_norm = Concept("  ALGORITMO  ", domain="  PROGRAMACION  ")
test("Concept: name normalizado", c_norm.name == "algoritmo")
test("Concept: domain normalizado", c_norm.domain == "programacion")

print("\n--- Synthesis ---")
syn = Synthesis()
syn.source_concepts = ["red neuronal", "ecosistema"]
syn.source_domains = ["ia_ml", "biologia"]
syn.insight = "Combinar adaptativo es interesante"
syn.analogy = "red neuronal es como ecosistema"
syn.novelty_score = 0.7

test("Synthesis: id generado", len(syn.synthesis_id) == 10)
test("Synthesis: source_concepts", len(syn.source_concepts) == 2)

# to_text
text = syn.to_text()
test("Synthesis: to_text no vacio", len(text) > 0)
test("Synthesis: to_text contiene insight", "adaptativo" in text)

# to_dict / from_dict
sd = syn.to_dict()
test("Synthesis: to_dict tiene novelty_score", sd["novelty_score"] == 0.7)
syn2 = Synthesis.from_dict(sd)
test("Synthesis: from_dict restaura concepts", syn2.source_concepts == ["red neuronal", "ecosistema"])
test("Synthesis: from_dict restaura novelty", syn2.novelty_score == 0.7)

print("\n--- AnalogyFinder ---")
af = AnalogyFinder()

concepts = [
    Concept("red neuronal", domain="ia_ml", properties=["adaptativo", "jerarquico", "distribuido"]),
    Concept("ecosistema", domain="biologia", properties=["adaptativo", "distribuido", "robusto"]),
    Concept("blockchain", domain="programacion", properties=["distribuido", "robusto"]),
    Concept("perceptron", domain="ia_ml", properties=["adaptativo", "jerarquico"]),
]

analogies = af.find_analogies(concepts, min_similarity=0.2)
test("AnalogyFinder: encuentra analogias cross-domain", len(analogies) > 0)

# Verificar que son cross-domain
for a in analogies:
    test(f"AnalogyFinder: {a['concept_a'].name} x {a['concept_b'].name} es cross-domain",
         a["concept_a"].domain != a["concept_b"].domain)

# find_transfer_opportunities
source = concepts[0]  # red neuronal
opps = af.find_transfer_opportunities(source, concepts)
test("AnalogyFinder: transfer opportunities", isinstance(opps, list))

# Analogias vacías (solo mismo dominio)
same_domain = [
    Concept("a", domain="x", properties=["p1"]),
    Concept("b", domain="x", properties=["p1"]),
]
no_analogies = af.find_analogies(same_domain)
test("AnalogyFinder: sin analogias same-domain", len(no_analogies) == 0)

print("\n--- SynthesisEngine ---")
se = SynthesisEngine()

syn_result = se.synthesize(concepts[0], concepts[1])
test("SynthesisEngine: genera synthesis", syn_result is not None)
test("SynthesisEngine: insight no vacio", len(syn_result.insight) > 0)
test("SynthesisEngine: analogy no vacia", len(syn_result.analogy) > 0)
test("SynthesisEngine: novelty_score > 0", syn_result.novelty_score > 0)
test("SynthesisEngine: source_concepts set", len(syn_result.source_concepts) == 2)
test("SynthesisEngine: source_domains set", len(syn_result.source_domains) == 2)

# Novelty: cross-domain > same-domain
c_same1 = Concept("a", domain="x", properties=["p1"])
c_same2 = Concept("b", domain="x", properties=["p2"])
syn_same = se.synthesize(c_same1, c_same2)
test("SynthesisEngine: novelty cross-domain > same-domain",
     syn_result.novelty_score > syn_same.novelty_score)

# synthesis_count incrementado
test("SynthesisEngine: synthesis_count incrementado", concepts[0].synthesis_count > 0)

print("\n--- ConceptSynthesizer ---")
tmp_dir2 = tempfile.mkdtemp()

try:
    cs = ConceptSynthesizer(base_dir=tmp_dir2)
    test("ConceptSynthesizer: inicializado", len(cs.concepts) == 0)

    # extract_concept (necesita >=2 keywords del dominio para detectar)
    c = cs.extract_concept("la red neuronal es un modelo de inferencia con training rapido", name="red neuronal")
    test("ConceptSynthesizer: extract retorna Concept", c is not None)
    test("ConceptSynthesizer: concept almacenado", len(cs.concepts) > 0)
    test("ConceptSynthesizer: total_concepts > 0", cs.total_concepts > 0)
    test("ConceptSynthesizer: domain detectado", c.domain != "general")

    # extract existing concept (update) — necesita mismo domain para match
    c_dup = cs.extract_concept("red neuronal modelo neural training distribuida", name="red neuronal")
    test("ConceptSynthesizer: existing concept updated", c_dup.usage_count > 0)

    # extract otro concepto cross-domain
    c_bio = cs.extract_concept("la celula tiene evolucion y mutacion, es un organismo adaptativo", name="celula")
    test("ConceptSynthesizer: segundo concepto extraido", len(cs.concepts) >= 2)

    # synthesize_pair
    syn_pair = cs.synthesize_pair("red neuronal", "celula")
    test("ConceptSynthesizer: synthesize_pair funciona", syn_pair is not None)
    test("ConceptSynthesizer: synthesis almacenada", len(cs.syntheses) > 0)
    test("ConceptSynthesizer: total_syntheses > 0", cs.total_syntheses > 0)

    # synthesize_pair con concepto inexistente
    syn_none = cs.synthesize_pair("inexistente", "celula")
    test("ConceptSynthesizer: synthesize_pair None si no existe", syn_none is None)

    # find_analogies
    analogies = cs.find_analogies()
    test("ConceptSynthesizer: find_analogies retorna lista", isinstance(analogies, list))

    # auto_synthesize
    auto_results = cs.auto_synthesize()
    test("ConceptSynthesizer: auto_synthesize retorna lista", isinstance(auto_results, list))

    # get_context_for_prompt
    ctx = cs.get_context_for_prompt("red neuronal celula adaptativo")
    # Puede ser vacío si no hay match suficiente
    test("ConceptSynthesizer: get_context retorna string", isinstance(ctx, str))

    # get_stats
    stats = cs.get_stats()
    test("ConceptSynthesizer: stats tiene total_concepts", "total_concepts" in stats)
    test("ConceptSynthesizer: stats tiene domains", "domains" in stats)

    # status
    st = cs.status()
    test("ConceptSynthesizer: status no vacio", len(st) > 0)

    # generate_report
    report = cs.generate_report()
    test("ConceptSynthesizer: report contiene titulo", "CONCEPT SYNTHESIZER" in report)

    # save / load
    cs.save()
    cs2 = ConceptSynthesizer(base_dir=tmp_dir2)
    test("ConceptSynthesizer: persistencia concepts", len(cs2.concepts) > 0)
    test("ConceptSynthesizer: persistencia total_concepts", cs2.total_concepts > 0)

    # clear
    cs.clear()
    test("ConceptSynthesizer: clear limpia concepts", len(cs.concepts) == 0)
    test("ConceptSynthesizer: clear limpia syntheses", len(cs.syntheses) == 0)
    test("ConceptSynthesizer: clear limpia totals", cs.total_concepts == 0)

    # disabled
    cs.enabled = False
    c_disabled = cs.extract_concept("algo")
    test("ConceptSynthesizer: disabled retorna None", c_disabled is None)
    cs.enabled = True

    # empty text
    c_empty = cs.extract_concept("")
    test("ConceptSynthesizer: texto vacio retorna None", c_empty is None)

    # Domain detection
    test("ConceptSynthesizer: detecta dominio programacion",
         cs._detect_domain("funcion algoritmo python codigo") == "programacion")
    test("ConceptSynthesizer: detecta dominio ia_ml",
         cs._detect_domain("modelo neural training inferencia") == "ia_ml")
    test("ConceptSynthesizer: detecta dominio general sin keywords",
         cs._detect_domain("hola que tal") == "general")

    # Property detection
    props = cs._detect_properties("rapido y distribuido")
    test("ConceptSynthesizer: detecta property rapido", "rapido" in props)
    test("ConceptSynthesizer: detecta property distribuido", "distribuido" in props)

    # Eviction
    cs_evict = ConceptSynthesizer(base_dir=tmp_dir2)
    cs_evict.max_concepts = 3
    for i in range(6):
        c = Concept(f"concepto_{i}", domain=f"dom_{i}", properties=[f"p_{i}"])
        cs_evict.concepts[c.concept_id] = c
        cs_evict.total_concepts += 1
    cs_evict._evict_concepts()
    test("ConceptSynthesizer: eviction reduce a max", len(cs_evict.concepts) <= 3)

finally:
    shutil.rmtree(tmp_dir2, ignore_errors=True)

# ============================================================
# STRATEGIC PLANNER TESTS
# ============================================================
print("\n--- Phase ---")
from core.strategic_planner import Phase, Milestone, PlanGraph, AdaptiveScheduler, StrategicPlanner

p = Phase("investigacion", description="Investigar el tema", priority=8, estimated_effort=2.0)
test("Phase: nombre correcto", p.name == "investigacion")
test("Phase: description correcta", p.description == "Investigar el tema")
test("Phase: priority correcta", p.priority == 8)
test("Phase: estimated_effort correcto", p.estimated_effort == 2.0)
test("Phase: status = pending", p.status == "pending")
test("Phase: progress = 0", p.progress == 0.0)
test("Phase: id generado", len(p.phase_id) == 10)

# is_ready
test("Phase: ready sin prereqs", p.is_ready(set()))

p_with_deps = Phase("implementacion")
p_with_deps.prerequisites = ["dep1"]
test("Phase: not ready con prereqs no cumplidos", not p_with_deps.is_ready(set()))
test("Phase: ready con prereqs cumplidos", p_with_deps.is_ready({"dep1"}))

# start
p.start()
test("Phase: start cambia a in_progress", p.status == "in_progress")
test("Phase: start setea started_at", p.started_at is not None)

# update_progress
p.update_progress(0.5)
test("Phase: update_progress a 0.5", p.progress == 0.5)

# complete
p.complete()
test("Phase: complete cambia a completed", p.status == "completed")
test("Phase: complete setea progress 1.0", p.progress == 1.0)
test("Phase: complete setea completed_at", p.completed_at is not None)

# block
p2 = Phase("diseño")
p2.block("falta info")
test("Phase: block cambia a blocked", p2.status == "blocked")
test("Phase: block agrega nota", len(p2.notes) == 1)

# update_progress auto-complete
p3 = Phase("testing")
p3.update_progress(1.0)
test("Phase: auto-complete en progress 1.0", p3.status == "completed")

# update_progress auto-start
p4 = Phase("coding")
p4.update_progress(0.3)
test("Phase: auto-start en progress > 0", p4.status == "in_progress")

# Priority bounds
p_bounds = Phase("x", priority=15)
test("Phase: priority capped at 10", p_bounds.priority == 10)
p_bounds2 = Phase("y", priority=-3)
test("Phase: priority min 1", p_bounds2.priority == 1)

# elapsed_hours
p5 = Phase("test elapsed")
p5.started_at = time.time() - 3600  # 1 hora atrás
test("Phase: elapsed_hours > 0", p5.elapsed_hours > 0)

# efficiency
p6 = Phase("eff", estimated_effort=2.0)
p6.started_at = time.time() - 7200  # 2 horas
test("Phase: efficiency ~ 1.0", abs(p6.efficiency - 1.0) < 0.1)

# to_dict / from_dict
pd = p.to_dict()
test("Phase: to_dict tiene name", pd["name"] == "investigacion")
p_restored = Phase.from_dict(pd)
test("Phase: from_dict restaura name", p_restored.name == "investigacion")
test("Phase: from_dict restaura status", p_restored.status == "completed")

# Phase not ready when completed
p_completed = Phase("done")
p_completed.status = "completed"
test("Phase: completed not ready", not p_completed.is_ready(set()))

print("\n--- Milestone ---")
ms = Milestone("alpha release", target_phases=["p1", "p2"], description="Primera version")
test("Milestone: nombre correcto", ms.name == "alpha release")
test("Milestone: target_phases", len(ms.target_phases) == 2)
test("Milestone: not reached initially", not ms.reached)

# check
test("Milestone: not reached sin phases", not ms.check({"p1"}))
test("Milestone: reached con todas", ms.check({"p1", "p2", "p3"}))
test("Milestone: reached = True", ms.reached)
test("Milestone: reached_at set", ms.reached_at is not None)

# to_dict / from_dict
md = ms.to_dict()
test("Milestone: to_dict tiene name", md["name"] == "alpha release")
ms_restored = Milestone.from_dict(md)
test("Milestone: from_dict restaura name", ms_restored.name == "alpha release")
test("Milestone: from_dict restaura reached", ms_restored.reached)

# check empty targets
ms_empty = Milestone("empty")
test("Milestone: empty targets no reached", not ms_empty.check(set()))

print("\n--- PlanGraph ---")
pg = PlanGraph()

ph1 = Phase("diseño", priority=9)
ph2 = Phase("backend", priority=7)
ph3 = Phase("frontend", priority=7)
ph4 = Phase("testing", priority=8)
ph5 = Phase("deploy", priority=6)

id1 = pg.add_phase(ph1)
id2 = pg.add_phase(ph2)
id3 = pg.add_phase(ph3)
id4 = pg.add_phase(ph4)
id5 = pg.add_phase(ph5)

# Add dependencies: backend/frontend dependen de diseño, testing de ambos, deploy de testing
pg.add_dependency(id2, id1)  # backend <- diseño
pg.add_dependency(id3, id1)  # frontend <- diseño
pg.add_dependency(id4, id2)  # testing <- backend
pg.add_dependency(id4, id3)  # testing <- frontend
pg.add_dependency(id5, id4)  # deploy <- testing

test("PlanGraph: 5 fases", len(pg.phases) == 5)

# get_ready_phases (solo diseño al inicio)
ready = pg.get_ready_phases()
test("PlanGraph: solo diseño ready al inicio", len(ready) == 1)
test("PlanGraph: diseño es la fase ready", ready[0].name == "diseño")

# overall_progress
test("PlanGraph: progress 0% al inicio", pg.overall_progress == 0.0)

# Complete diseño -> backend y frontend quedan ready
ph1.complete()
ready2 = pg.get_ready_phases()
test("PlanGraph: backend y frontend ready tras diseño", len(ready2) == 2)
ready_names = {p.name for p in ready2}
test("PlanGraph: backend en ready", "backend" in ready_names)
test("PlanGraph: frontend en ready", "frontend" in ready_names)

# overall_progress after 1/5 completed
test("PlanGraph: progress 20% tras diseño", abs(pg.overall_progress - 0.2) < 0.01)

# topological_sort
topo = pg.topological_sort()
test("PlanGraph: topo sort tiene 5 fases", len(topo) == 5)
# diseño debe estar antes que backend y frontend
test("PlanGraph: topo sort diseño primero", topo.index(id1) < topo.index(id2))
test("PlanGraph: topo sort testing después de backend", topo.index(id4) > topo.index(id2))

# get_critical_path
critical = pg.get_critical_path()
test("PlanGraph: critical path existe", len(critical) > 1)

# get_in_progress / get_blocked
test("PlanGraph: sin in_progress al inicio", len(pg.get_in_progress()) == 0)
ph2.start()
test("PlanGraph: 1 in_progress tras start", len(pg.get_in_progress()) == 1)
test("PlanGraph: sin blocked al inicio", len(pg.get_blocked_phases()) == 0)

# Milestones
ms1 = Milestone("MVP", target_phases=[id1, id2])
pg.add_milestone(ms1)
ph2.complete()
newly = pg.check_milestones()
test("PlanGraph: milestone MVP alcanzado", len(newly) == 1)
test("PlanGraph: milestone name correcto", newly[0].name == "MVP")

# to_dict / load_dict
pgd = pg.to_dict()
test("PlanGraph: to_dict tiene phases", len(pgd["phases"]) == 5)
test("PlanGraph: to_dict tiene milestones", len(pgd["milestones"]) == 1)
pg2 = PlanGraph()
pg2.load_dict(pgd)
test("PlanGraph: load_dict restaura phases", len(pg2.phases) == 5)
test("PlanGraph: load_dict restaura milestones", len(pg2.milestones) == 1)

# completed_phase_ids
test("PlanGraph: completed_phase_ids", len(pg.completed_phase_ids) == 2)

print("\n--- AdaptiveScheduler ---")
scheduler = AdaptiveScheduler()

# Reset para test
pg_test = PlanGraph()
pa = Phase("a", priority=5)
pb = Phase("b", priority=5)
pb.status = "blocked"
pc = Phase("c", priority=5)
pc.status = "in_progress"
pc.started_at = time.time() - 7200  # 2h ago
pc.progress = 0.6
pc.estimated_effort = 0.5  # Should take 0.5h but took 2h
pg_test.add_phase(pa)
pg_test.add_phase(pb)
pg_test.add_phase(pc)

changes = scheduler.adapt(pg_test)
test("AdaptiveScheduler: adapt produce cambios", len(changes) > 0)
test("AdaptiveScheduler: blocked baja prioridad", pb.priority < 5)

# suggest_next
suggestions = scheduler.suggest_next(pg_test)
test("AdaptiveScheduler: suggest_next retorna lista", isinstance(suggestions, list))

# estimate_completion
remaining = scheduler.estimate_completion(pg_test)
test("AdaptiveScheduler: estimate_completion > 0", remaining > 0)

# feedback
pg_test2 = PlanGraph()
pf = Phase("feedback_phase", priority=5)
pid_f = pg_test2.add_phase(pf)
changes2 = scheduler.adapt(pg_test2, feedback={pid_f: 9})
test("AdaptiveScheduler: feedback sube prioridad", pf.priority == 9)

print("\n--- StrategicPlanner ---")
tmp_dir3 = tempfile.mkdtemp()

try:
    sp = StrategicPlanner(base_dir=tmp_dir3)
    test("StrategicPlanner: inicializado", len(sp.plans) == 0)

    # create_plan
    plan = sp.create_plan("proyecto genesis v3")
    test("StrategicPlanner: plan creado", plan is not None)
    test("StrategicPlanner: active_plan set", sp.active_plan == "proyecto genesis v3")
    test("StrategicPlanner: total_plans_created = 1", sp.total_plans_created == 1)

    # add_phase
    pid1 = sp.add_phase("investigacion", description="Investigar tech", priority=9,
                         estimated_effort=2.0, actions=["leer papers", "evaluar tools"])
    test("StrategicPlanner: fase agregada", len(pid1) > 0)

    pid2 = sp.add_phase("diseño", priority=8, depends_on=["investigacion"])
    test("StrategicPlanner: fase con dependencia", len(pid2) > 0)

    pid3 = sp.add_phase("implementacion", priority=7, depends_on=["diseño"])
    test("StrategicPlanner: tercera fase", len(pid3) > 0)

    # add_milestone
    ms_id = sp.add_milestone("MVP", phase_names=["investigacion", "diseño"],
                             description="Minimo viable")
    test("StrategicPlanner: milestone agregado", len(ms_id) > 0)

    # suggest_next
    next_phases = sp.suggest_next()
    test("StrategicPlanner: suggest_next funciona", len(next_phases) > 0)
    test("StrategicPlanner: primera sugerida = investigacion", next_phases[0].name == "investigacion")

    # complete_phase
    result = sp.complete_phase("investigacion")
    test("StrategicPlanner: complete_phase success", result["success"])
    test("StrategicPlanner: total_phases_completed > 0", sp.total_phases_completed > 0)

    # Verify diseño is now ready
    next_after = sp.suggest_next()
    test("StrategicPlanner: diseño ready tras investigacion",
         any(p.name == "diseño" for p in next_after))

    # Complete diseño -> milestone MVP should be reached
    result2 = sp.complete_phase("diseño")
    test("StrategicPlanner: milestone MVP reached", len(result2["milestones_reached"]) > 0)
    test("StrategicPlanner: total_milestones_reached > 0", sp.total_milestones_reached > 0)

    # update_phase_progress
    ok = sp.update_phase_progress("implementacion", 0.5)
    test("StrategicPlanner: update_progress funciona", ok)

    # block_phase
    pid4 = sp.add_phase("deploy", priority=5, depends_on=["implementacion"])
    ok_block = sp.block_phase("deploy", "falta servidor")
    test("StrategicPlanner: block_phase funciona", ok_block)

    # adapt
    changes = sp.adapt()
    test("StrategicPlanner: adapt retorna lista", isinstance(changes, list))

    # get_context_for_prompt
    ctx = sp.get_context_for_prompt()
    test("StrategicPlanner: context no vacio", len(ctx) > 0)
    test("StrategicPlanner: context contiene plan name", "proyecto genesis" in ctx.lower())

    # auto_track
    sp.auto_track("implementacion terminado completado", "todo listo")
    impl_phase = None
    for p in sp.get_active_plan().phases.values():
        if p.name == "implementacion":
            impl_phase = p
    test("StrategicPlanner: auto_track detecta completado", impl_phase.status == "completed")

    # get_stats
    stats = sp.get_stats()
    test("StrategicPlanner: stats tiene total_plans", "total_plans" in stats)
    test("StrategicPlanner: stats tiene active_plan", "active_plan" in stats)
    test("StrategicPlanner: stats tiene active_plan_info", "active_plan_info" in stats)

    # status
    st = sp.status()
    test("StrategicPlanner: status no vacio", len(st) > 0)

    # generate_report
    report = sp.generate_report()
    test("StrategicPlanner: report contiene titulo", "STRATEGIC PLANNER" in report)
    test("StrategicPlanner: report contiene nombre plan", "proyecto genesis" in report.lower())

    # save / load
    sp.save()
    sp2 = StrategicPlanner(base_dir=tmp_dir3)
    test("StrategicPlanner: persistencia plans", len(sp2.plans) > 0)
    test("StrategicPlanner: persistencia active_plan", sp2.active_plan == "proyecto genesis v3")
    test("StrategicPlanner: persistencia phases", len(sp2.get_active_plan().phases) > 0)

    # clear
    sp.clear()
    test("StrategicPlanner: clear limpia plans", len(sp.plans) == 0)
    test("StrategicPlanner: clear limpia active_plan", sp.active_plan is None)

    # Operaciones sin plan activo
    test("StrategicPlanner: add_phase sin plan = vacio", sp.add_phase("x") == "")
    test("StrategicPlanner: add_milestone sin plan = vacio", sp.add_milestone("x") == "")
    test("StrategicPlanner: suggest_next sin plan = []", sp.suggest_next() == [])
    test("StrategicPlanner: adapt sin plan = []", sp.adapt() == [])
    ctx_empty = sp.get_context_for_prompt()
    test("StrategicPlanner: context sin plan = vacio", ctx_empty == "")

    result_fail = sp.complete_phase("x")
    test("StrategicPlanner: complete sin plan falla", not result_fail["success"])

    test("StrategicPlanner: update sin plan = False", not sp.update_phase_progress("x", 0.5))
    test("StrategicPlanner: block sin plan = False", not sp.block_phase("x"))

    # status sin plan activo
    st_empty = sp.status()
    test("StrategicPlanner: status sin plan", "Sin plan activo" in st_empty)

    # disabled
    sp.enabled = False
    plan_none = sp.create_plan("test")
    test("StrategicPlanner: disabled retorna None", plan_none is None)
    sp.enabled = True

    # Eviction
    sp_evict = StrategicPlanner(base_dir=tmp_dir3)
    sp_evict.max_plans = 2
    for i in range(5):
        sp_evict.create_plan(f"plan_{i}")
        plan_obj = sp_evict.get_active_plan()
        p = Phase(f"done_{i}")
        p.complete()
        plan_obj.add_phase(p)
    sp_evict._evict_plans()
    test("StrategicPlanner: eviction reduce plans", len(sp_evict.plans) <= 3)

finally:
    shutil.rmtree(tmp_dir3, ignore_errors=True)

# ============================================================
# INTEGRATION TESTS — genesis.py
# ============================================================
print("\n--- Integración genesis.py ---")

# Test imports
try:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # El refactor a MIXINS movio codigo de genesis.py a core/genesis_*.py.
    # Concatenamos las fuentes para verificar la integracion real.
    source = open(os.path.join(_root, "genesis.py"), encoding="utf-8").read()
    for _mod in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
        source += "\n" + open(os.path.join(_root, "core", _mod), encoding="utf-8").read()
    test("genesis.py: import CausalReasoner", "from core.causal_reasoner import CausalReasoner" in source)
    test("genesis.py: import ConceptSynthesizer", "from core.concept_synthesizer import ConceptSynthesizer" in source)
    test("genesis.py: import StrategicPlanner", "from core.strategic_planner import StrategicPlanner" in source)

    # Init (lazy: instanciacion dentro de _init_lazy_module en genesis.py)
    test("genesis.py: init causal_reasoner", "CausalReasoner(" in source)
    test("genesis.py: init concept_synth", "ConceptSynthesizer(" in source)
    test("genesis.py: init strategic_planner", "StrategicPlanner(" in source)

    # Context injection
    test("genesis.py: causal context injection", "causal_reasoner.get_context_for_prompt" in source)
    test("genesis.py: synth context injection", "concept_synth.get_context_for_prompt" in source)
    test("genesis.py: planner context injection", "strategic_planner.get_context_for_prompt" in source)

    # Post-processing
    test("genesis.py: causal extract_and_store", "causal_reasoner.extract_and_store" in source)
    test("genesis.py: concept extract_concept", "concept_synth.extract_concept" in source)
    test("genesis.py: planner auto_track", "strategic_planner.auto_track" in source)

    # Commands
    test("genesis.py: comando /causal", '"/causal"' in source or "cmd == \"/causal\"" in source)
    test("genesis.py: comando /synthesis", '"/synthesis"' in source or "cmd == \"/synthesis\"" in source)
    test("genesis.py: comando /planner", '"/planner"' in source or "cmd == \"/planner\"" in source)

    # Save (save_all() usa la lista saveable_modules con el nombre del modulo)
    test("genesis.py: save causal", '"causal_reasoner"' in source)
    test("genesis.py: save concept_synth", '"concept_synth"' in source)
    test("genesis.py: save strategic_planner", '"strategic_planner"' in source)

    # Status
    test("genesis.py: status CAUSAL REASONER", "CAUSAL REASONER" in source)
    test("genesis.py: status CONCEPT SYNTHESIZER", "CONCEPT SYNTHESIZER" in source)
    test("genesis.py: status STRATEGIC PLANNER", "STRATEGIC PLANNER" in source)

    # Dashboard
    test("genesis.py: dashboard causal", "causal_reasoner" in source and "dashboard.register" in source)
    test("genesis.py: dashboard concept_synth", "concept_synth" in source and "dashboard.register" in source)
    test("genesis.py: dashboard strategic_planner", "strategic_planner" in source and "dashboard.register" in source)

    # Help
    test("genesis.py: help /causal", "/causal" in source)
    test("genesis.py: help /synthesis", "/synthesis" in source)
    test("genesis.py: help /planner", "/planner" in source)

except Exception as e:
    test(f"genesis.py: lectura fallida — {e}", False)

# ============================================================
# INTEGRATION TESTS — web_ui.py
# ============================================================
print("\n--- Integración web_ui.py ---")
try:
    web_source = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    "web_ui.py"), encoding="utf-8").read()
    test("web_ui.py: causal_reasoner en dashboard", "causal_reasoner" in web_source)
    test("web_ui.py: concept_synth en dashboard", "concept_synth" in web_source)
    test("web_ui.py: strategic_planner en dashboard", "strategic_planner" in web_source)
    test("web_ui.py: CausalReasoner en subsystems", "CausalReasoner" in web_source)
    test("web_ui.py: ConceptSynth en subsystems", "ConceptSynth" in web_source)
    test("web_ui.py: StrategicPlanner en subsystems", "StrategicPlanner" in web_source)
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
test(f"Version >= 2.6 (actual: {GENESIS_VERSION})", version_num >= 26)

# ============================================================
# EDGE CASES & ADVANCED
# ============================================================
print("\n--- Edge Cases ---")

# CausalGraph con nodo aislado
g_edge = CausalGraph()
g_edge.add_link(CausalLink("a", "b"))
test("Edge: causes of nodo sin causas = []", len(g_edge.get_causes_of("a")) == 0)
test("Edge: effects of nodo sin efectos = []", len(g_edge.get_effects_of("b")) == 0)

# PlanGraph vacío
pg_empty = PlanGraph()
test("Edge: overall_progress vacio = 0", pg_empty.overall_progress == 0.0)
test("Edge: topological_sort vacio = []", pg_empty.topological_sort() == [])
test("Edge: critical_path vacio = []", pg_empty.get_critical_path() == [])

# Concept similarity simétrica
c_a = Concept("x", properties=["p1", "p2"])
c_b = Concept("y", properties=["p2", "p3"])
test("Edge: similarity simétrica", c_a.similarity(c_b) == c_b.similarity(c_a))

# Phase elapsed sin start
p_no_start = Phase("no start")
test("Edge: elapsed sin start = 0", p_no_start.elapsed_hours == 0.0)

# Phase efficiency sin start
test("Edge: efficiency sin start = 1.0", p_no_start.efficiency == 1.0)

# CausalLink strength sin datos (total=0)
l_fresh = CausalLink.__new__(CausalLink)
l_fresh.confidence = 0.5
l_fresh.reinforcements = 0
l_fresh.contradictions = 0
test("Edge: strength con 0 total = confidence", l_fresh.strength == 0.5)

# Milestone check sin targets
ms_no_targets = Milestone("empty")
test("Edge: milestone sin targets no reached", not ms_no_targets.check({"p1", "p2"}))

# AdaptiveScheduler con plan vacío
sched_empty = AdaptiveScheduler()
pg_e = PlanGraph()
test("Edge: suggest_next plan vacio", sched_empty.suggest_next(pg_e) == [])
test("Edge: estimate_completion plan vacio", sched_empty.estimate_completion(pg_e) == 0.0)
test("Edge: adapt plan vacio", sched_empty.adapt(pg_e) == [])

# CausalInference max 5 pares
ci = CausalInference()
long_text = ". ".join([f"causa_{i} provoca efecto_{i}" for i in range(20)])
pairs = ci.extract_causal_pairs(long_text)
test("Edge: extract_causal_pairs max 5", len(pairs) <= 5)

# StrategicPlanner _find_phase_id parcial
tmp_dir4 = tempfile.mkdtemp()
try:
    sp_find = StrategicPlanner(base_dir=tmp_dir4)
    sp_find.create_plan("test")
    sp_find.add_phase("investigacion de mercado")
    plan_obj = sp_find.get_active_plan()
    found = sp_find._find_phase_id(plan_obj, "mercado")
    test("Edge: _find_phase_id parcial funciona", len(found) > 0)
    not_found = sp_find._find_phase_id(plan_obj, "xyz_inexistente")
    test("Edge: _find_phase_id no encontrado = ''", not_found == "")
finally:
    shutil.rmtree(tmp_dir4, ignore_errors=True)

# PlanGraph add_dependency con id inexistente (no crash)
pg_dep = PlanGraph()
ph_test = Phase("test")
pg_dep.add_phase(ph_test)
pg_dep.add_dependency(ph_test.phase_id, "inexistente")  # Should not crash
test("Edge: add_dependency inexistente no crashea", True)
test("Edge: add_dependency inexistente no agrega", len(ph_test.prerequisites) == 0)

# ConceptSynthesizer _find_concept parcial
tmp_dir5 = tempfile.mkdtemp()
try:
    cs_find = ConceptSynthesizer(base_dir=tmp_dir5)
    c_long = Concept("machine learning avanzado", domain="ia_ml")
    cs_find.concepts[c_long.concept_id] = c_long
    found_c = cs_find._find_concept("machine learning")
    test("Edge: _find_concept parcial funciona", found_c is not None)
    not_found_c = cs_find._find_concept("xyz_inexistente")
    test("Edge: _find_concept no encontrado = None", not_found_c is None)
finally:
    shutil.rmtree(tmp_dir5, ignore_errors=True)

# Multiple plans
tmp_dir6 = tempfile.mkdtemp()
try:
    sp_multi = StrategicPlanner(base_dir=tmp_dir6)
    sp_multi.create_plan("plan a")
    sp_multi.add_phase("fase a1")
    sp_multi.create_plan("plan b")
    sp_multi.add_phase("fase b1")
    test("Edge: multiple plans stored", len(sp_multi.plans) == 2)
    test("Edge: active plan es ultimo", sp_multi.active_plan == "plan b")
    test("Edge: plan a tiene fases", len(sp_multi.plans["plan a"].phases) == 1)
    test("Edge: plan b tiene fases", len(sp_multi.plans["plan b"].phases) == 1)
finally:
    shutil.rmtree(tmp_dir6, ignore_errors=True)

# auto_track sin plan activo (no crash)
sp_noplan = StrategicPlanner.__new__(StrategicPlanner)
sp_noplan.plans = {}
sp_noplan.active_plan = None
sp_noplan.total_phases_completed = 0
try:
    sp_noplan.auto_track("test", "test")
    test("Edge: auto_track sin plan no crashea", True)
except Exception:
    test("Edge: auto_track sin plan no crashea", False)

# CausalReasoner get_context sin links
tmp_dir7 = tempfile.mkdtemp()
try:
    cr_empty = CausalReasoner(base_dir=tmp_dir7)
    ctx_empty = cr_empty.get_context_for_prompt("por que algo?")
    test("Edge: context sin links = vacio", ctx_empty == "")
finally:
    shutil.rmtree(tmp_dir7, ignore_errors=True)

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTADOS: {passed}/{total} tests passed")
if errors:
    print(f"\nFAILED ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED!")
    sys.exit(0)
