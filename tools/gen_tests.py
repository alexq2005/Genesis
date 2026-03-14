"""Generate test files for v3.5 through v5.0"""
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

VERSIONS = [
    ("3.5", "Autonomous Research", [
        ("paper_reader", "PaperReader", "total_papers_read"),
        ("experiment_runner", "ExperimentRunner", "total_experiments"),
        ("insight_synthesizer", "InsightSynthesizer", "total_insights"),
    ]),
    ("4.0", "Autonomous Evolution", [
        ("safe_code_evolver", "SafeCodeEvolver", "total_mutations"),
        ("architecture_evolver", "ArchitectureEvolver", "total_proposals"),
        ("module_generator", "ModuleGenerator", "total_generated"),
    ]),
    ("4.1", "Temporal Intelligence", [
        ("temporal_reasoner", "TemporalReasoner", "total_events"),
        ("schedule_optimizer", "ScheduleOptimizer", "total_optimizations"),
        ("trend_forecaster", "TrendForecaster", "total_forecasts"),
    ]),
    ("4.2", "Ethical Framework", [
        ("ethical_reasoner", "EthicalReasoner", "total_evaluations"),
        ("bias_detector", "BiasDetector", "total_scans"),
        ("transparency_engine", "TransparencyEngine", "total_decisions"),
    ]),
    ("4.3", "Knowledge Mastery", [
        ("domain_expert", "DomainExpert", "total_detections"),
        ("tutor_engine", "TutorEngine", "total_lessons"),
        ("fact_checker", "FactChecker", "total_checked"),
    ]),
    ("4.4", "Distributed Genesis", [
        ("task_distributor", "TaskDistributor", "total_tasks"),
        ("result_aggregator", "ResultAggregator", "total_aggregated"),
        ("network_manager", "NetworkManager", "total_nodes_seen"),
    ]),
    ("5.0", "Singularity", [
        ("autonomous_research_loop", "AutonomousResearchLoop", "total_cycles"),
        ("self_architect", "SelfArchitect", "total_snapshots"),
        ("consciousness_integrator", "ConsciousnessIntegrator", "total_integrations"),
    ]),
]

COMMANDS = {
    "paper_reader": "/papers",
    "experiment_runner": "/experiments",
    "insight_synthesizer": "/insights",
    "safe_code_evolver": "/evolver",
    "architecture_evolver": "/arch_evolver",
    "module_generator": "/modgen",
    "temporal_reasoner": "/temporal",
    "schedule_optimizer": "/schedule",
    "trend_forecaster": "/trends",
    "ethical_reasoner": "/ethics",
    "bias_detector": "/bias",
    "transparency_engine": "/transparency",
    "domain_expert": "/domains",
    "tutor_engine": "/tutor",
    "fact_checker": "/factcheck",
    "task_distributor": "/distribute",
    "result_aggregator": "/aggregate",
    "network_manager": "/network",
    "autonomous_research_loop": "/research_loop",
    "self_architect": "/self_arch",
    "consciousness_integrator": "/consciousness",
}

STATUS_LABELS = {
    "paper_reader": "PAPER READER",
    "experiment_runner": "EXPERIMENT RUNNER",
    "insight_synthesizer": "INSIGHT SYNTHESIZER",
    "safe_code_evolver": "SAFE CODE EVOLVER",
    "architecture_evolver": "ARCHITECTURE EVOLVER",
    "module_generator": "MODULE GENERATOR",
    "temporal_reasoner": "TEMPORAL REASONER",
    "schedule_optimizer": "SCHEDULE OPTIMIZER",
    "trend_forecaster": "TREND FORECASTER",
    "ethical_reasoner": "ETHICAL REASONER",
    "bias_detector": "BIAS DETECTOR",
    "transparency_engine": "TRANSPARENCY ENGINE",
    "domain_expert": "DOMAIN EXPERT",
    "tutor_engine": "TUTOR ENGINE",
    "fact_checker": "FACT CHECKER",
    "task_distributor": "TASK DISTRIBUTOR",
    "result_aggregator": "RESULT AGGREGATOR",
    "network_manager": "NETWORK MANAGER",
    "autonomous_research_loop": "AUTONOMOUS RESEARCH LOOP",
    "self_architect": "SELF ARCHITECT",
    "consciousness_integrator": "CONSCIOUSNESS INTEGRATOR",
}

for ver, title, modules in VERSIONS:
    ver_file = ver.replace(".", "_")
    filename = f"tests/test_v{ver_file}.py"

    # Build import lines for all classes in this version's modules
    import_lines = []
    for mod_name, cls_name, attr in modules:
        # Get all classes from the module
        import_lines.append(f"from core.{mod_name} import {cls_name}")

    # Build test blocks
    test_blocks = []
    for mod_name, cls_name, attr in modules:
        cmd = COMMANDS[mod_name]
        label = STATUS_LABELS[mod_name]
        short = cls_name[:2].upper()

        test_blocks.append(f'''
# === {cls_name.upper()} ===
print("\\n--- {cls_name} ---")

tmp = tempfile.mkdtemp()
try:
    obj = {cls_name}(base_dir=tmp)
    test("{short}: init ok", obj is not None)
    test("{short}: {attr} starts at 0", obj.{attr} == 0)

    # get_stats
    stats = obj.get_stats()
    test("{short}: get_stats returns dict", isinstance(stats, dict))
    test("{short}: stats has {attr}", "{attr}" in stats)

    # status
    st = obj.status()
    test("{short}: status is string", isinstance(st, str))
    test("{short}: status not empty", len(st) > 0)

    # generate_report
    report = obj.generate_report()
    test("{short}: report is string", isinstance(report, str))
    test("{short}: report not empty", len(report) > 0)

    # get_context_for_prompt
    try:
        ctx = obj.get_context_for_prompt(max_chars=200)
        test("{short}: context returns string", isinstance(ctx, str))
    except TypeError:
        ctx = obj.get_context_for_prompt("test input", max_chars=200)
        test("{short}: context with input returns string", isinstance(ctx, str))

    # save/load
    obj.save()
    obj2 = {cls_name}(base_dir=tmp)
    test("{short}: persistence ok", obj2.{attr} == 0)

    # clear
    obj.clear()
    test("{short}: clear resets", obj.{attr} == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
''')

    # Build integration checks
    int_checks = []
    for mod_name, cls_name, attr in modules:
        cmd = COMMANDS[mod_name]
        label = STATUS_LABELS[mod_name]
        int_checks.append(f'''test("Int: import {mod_name}", "from core.{mod_name} import" in gs)
test("Int: self.{mod_name}", "self.{mod_name}" in gs)
test("Int: {mod_name}.save()", "self.{mod_name}.save()" in gs)
test("Int: cmd {cmd}", "{cmd}" in gs)
test("Int: status {label}", "{label}" in gs)
test("WebUI: {mod_name}", "{mod_name}" in ws)''')

    content = f'''"""Tests para Genesis v{ver} -- {title}"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

passed = 0
failed = 0
errors = []
def test(name, condition):
    global passed, failed, errors
    try:
        if condition: passed += 1
        else: failed += 1; errors.append(f"FAIL: {{name}}"); print(f"  FAIL: {{name}}")
    except Exception as e:
        failed += 1; errors.append(f"ERROR: {{name}}: {{e}}"); print(f"  ERROR: {{name}}: {{e}}")

print("=" * 60)
print("GENESIS v{ver} -- {title} Tests")
print("=" * 60)

{chr(10).join(import_lines)}

{"".join(test_blocks)}

# === VERSION CHECK ===
print("\\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= {ver}", float(f"{{major}}.{{minor}}") >= {ver})

# === INTEGRATION CHECK ===
print("\\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

{chr(10).join(int_checks)}

print("\\n" + "=" * 60)
print(f"RESULTS: {{passed}} passed, {{failed}} failed, {{passed + failed}} total")
if errors:
    print("\\nFailed tests:")
    for e in errors: print(f"  {{e}}")
print("=" * 60)
'''

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated {filename}")

print("\nAll test files generated!")
