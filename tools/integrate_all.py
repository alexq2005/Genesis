"""
Script to integrate all remaining modules (v3.5-v5.0) into genesis.py and web_ui.py
"""
import os, sys

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

VERSIONS = [
    ("3.5", "Autonomous Research", [
        ("paper_reader", "PaperReader", True),
        ("experiment_runner", "ExperimentRunner", False),
        ("insight_synthesizer", "InsightSynthesizer", True),
    ], "research"),
    ("4.0", "Autonomous Evolution", [
        ("safe_code_evolver", "SafeCodeEvolver", False),
        ("architecture_evolver", "ArchitectureEvolver", False),
        ("module_generator", "ModuleGenerator", False),
    ], "evolution"),
    ("4.1", "Temporal Intelligence", [
        ("temporal_reasoner", "TemporalReasoner", True),
        ("schedule_optimizer", "ScheduleOptimizer", False),
        ("trend_forecaster", "TrendForecaster", False),
    ], "temporal"),
    ("4.2", "Ethical Framework", [
        ("ethical_reasoner", "EthicalReasoner", True),
        ("bias_detector", "BiasDetector", False),
        ("transparency_engine", "TransparencyEngine", False),
    ], "ethics"),
    ("4.3", "Knowledge Mastery", [
        ("domain_expert", "DomainExpert", True),
        ("tutor_engine", "TutorEngine", True),
        ("fact_checker", "FactChecker", True),
    ], "knowledge"),
    ("4.4", "Distributed Genesis", [
        ("task_distributor", "TaskDistributor", False),
        ("result_aggregator", "ResultAggregator", False),
        ("network_manager", "NetworkManager", False),
    ], "distributed"),
    ("5.0", "Singularity", [
        ("autonomous_research_loop", "AutonomousResearchLoop", False),
        ("self_architect", "SelfArchitect", False),
        ("consciousness_integrator", "ConsciousnessIntegrator", False),
    ], "singularity"),
]

BANNER_ATTRS = {
    "paper_reader": "total_papers",
    "experiment_runner": "total_experiments",
    "insight_synthesizer": "total_insights",
    "safe_code_evolver": "total_mutations",
    "architecture_evolver": "total_proposals",
    "module_generator": "total_generated",
    "temporal_reasoner": "total_events",
    "schedule_optimizer": "total_optimized",
    "trend_forecaster": "total_forecasts",
    "ethical_reasoner": "total_evaluations",
    "bias_detector": "total_scans",
    "transparency_engine": "total_traces",
    "domain_expert": "total_queries",
    "tutor_engine": "total_sessions",
    "fact_checker": "total_checks",
    "task_distributor": "total_distributed",
    "result_aggregator": "total_aggregated",
    "network_manager": "total_connections",
    "autonomous_research_loop": "total_cycles",
    "self_architect": "total_snapshots",
    "consciousness_integrator": "total_integrations",
}

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

HELP_DESCS = {
    "paper_reader": "Ver papers analizados y secciones extraidas",
    "experiment_runner": "Ver experimentos ejecutados y resultados",
    "insight_synthesizer": "Ver insights sintetizados y cadenas de evidencia",
    "safe_code_evolver": "Ver mutaciones de codigo y fitness",
    "architecture_evolver": "Ver propuestas de evolucion arquitectonica",
    "module_generator": "Ver modulos generados y brechas detectadas",
    "temporal_reasoner": "Ver eventos temporales y lineas de tiempo",
    "schedule_optimizer": "Ver horarios optimizados y slots",
    "trend_forecaster": "Ver tendencias y predicciones",
    "ethical_reasoner": "Ver evaluaciones eticas y dilemas",
    "bias_detector": "Ver sesgos detectados y reportes",
    "transparency_engine": "Ver trazas de decision y explicaciones",
    "domain_expert": "Ver dominios de expertise y consultas",
    "tutor_engine": "Ver sesiones de tutoria y curriculos",
    "fact_checker": "Ver verificaciones de hechos y fuentes",
    "task_distributor": "Ver tareas distribuidas y balanceo de carga",
    "result_aggregator": "Ver resultados agregados y consenso",
    "network_manager": "Ver nodos de red y descubrimiento",
    "autonomous_research_loop": "Ver ciclos de investigacion autonoma",
    "self_architect": "Ver snapshots y propuestas de refactoreo",
    "consciousness_integrator": "Ver estado de consciencia integrada",
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

# ============================================================
# GENESIS.PY
# ============================================================
with open("genesis.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. IMPORTS
import_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        import_lines.append(f"from core.{mod_name} import {cls_name}")
import_block = "\n".join(import_lines)

old = "from core.knowledge_sharing import KnowledgeSharing\n\n\nclass Genesis:"
new = f"from core.knowledge_sharing import KnowledgeSharing\n{import_block}\n\n\nclass Genesis:"
content = content.replace(old, new)

# 2. INITS
init_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        attr = BANNER_ATTRS.get(mod_name, "total_count")
        init_lines.append(f"""
        # Inicializar {cls_name}
        self.{mod_name} = {cls_name}(
            base_dir=str(BASE_DIR / "data" / "{mod_name}"),
        )
        self.log.info(f"{cls_name}: {{self.{mod_name}.{attr}}}")""")
init_block = "\n".join(init_lines)

old = '        self.log.info(f"KnowledgeSharing: {self.knowledge_sharing.total_shared} compartidos")\n\n        # Configurar evolucion autonoma'
new = f'        self.log.info(f"KnowledgeSharing: {{self.knowledge_sharing.total_shared}} compartidos")\n{init_block}\n\n        # Configurar evolucion autonoma'
content = content.replace(old, new)

# 3. CONTEXT INJECTION
ctx_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, has_user_input in modules:
        if has_user_input:
            ctx_lines.append(f"""
        # {cls_name}: contexto
        {mod_name}_ctx = self.{mod_name}.get_context_for_prompt(user_input, max_chars=200)
        if {mod_name}_ctx:
            system_prompt += f"\\n\\n{{{mod_name}_ctx}}" """)
        else:
            ctx_lines.append(f"""
        # {cls_name}: contexto
        {mod_name}_ctx = self.{mod_name}.get_context_for_prompt(max_chars=200)
        if {mod_name}_ctx:
            system_prompt += f"\\n\\n{{{mod_name}_ctx}}" """)
ctx_block = "\n".join(ctx_lines)

old_ctx = """        knowledge_ctx = self.knowledge_sharing.get_context_for_prompt(user_input, max_chars=200)
        if knowledge_ctx:
            system_prompt += f"\\n\\n{knowledge_ctx}"

        # Fase 0: Planificacion"""
new_ctx = f"""        knowledge_ctx = self.knowledge_sharing.get_context_for_prompt(user_input, max_chars=200)
        if knowledge_ctx:
            system_prompt += f"\\n\\n{{knowledge_ctx}}"
{ctx_block}

        # Fase 0: Planificacion"""
content = content.replace(old_ctx, new_ctx)

# 4. COMMANDS
cmd_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        cmd = COMMANDS[mod_name]
        cmd_lines.append(f'        elif cmd == "{cmd}":\n            return self.{mod_name}.generate_report()')
cmd_block = "\n".join(cmd_lines)

old_cmd = '        elif cmd == "/knowledge":\n            return self.knowledge_sharing.generate_report()\n        elif cmd == "/memory semantic":'
new_cmd = f'        elif cmd == "/knowledge":\n            return self.knowledge_sharing.generate_report()\n{cmd_block}\n        elif cmd == "/memory semantic":'
content = content.replace(old_cmd, new_cmd)

# 5. DASHBOARD
dash_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        dash_lines.append(f'        self.dashboard.register("{mod_name}", lambda: self.{mod_name}.get_stats(), "{category}")')
dash_block = "\n".join(dash_lines)

old_dash = '        self.dashboard.register("knowledge_sharing", lambda: self.knowledge_sharing.get_stats(), "collaborative")\n\n    def _save_session(self):'
new_dash = f'        self.dashboard.register("knowledge_sharing", lambda: self.knowledge_sharing.get_stats(), "collaborative")\n{dash_block}\n\n    def _save_session(self):'
content = content.replace(old_dash, new_dash)

# 6. SAVE
save_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        save_lines.append(f"            self.{mod_name}.save()")
save_block = "\n".join(save_lines)

old_save = "            self.knowledge_sharing.save()\n            self.heartbeat.stop()"
new_save = f"            self.knowledge_sharing.save()\n{save_block}\n            self.heartbeat.stop()"
content = content.replace(old_save, new_save)

# 7. STATUS
status_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        label = STATUS_LABELS[mod_name]
        status_lines.append(f'            f"",\n            f"{label}:",\n            self.{mod_name}.status(),')
status_block = "\n".join(status_lines)

old_status = """            f"KNOWLEDGE SHARING:",
            self.knowledge_sharing.status(),
            f"",
            f"EVOLUCION AUTONOMA:\""""
new_status = f"""            f"KNOWLEDGE SHARING:",
            self.knowledge_sharing.status(),
{status_block}
            f"",
            f"EVOLUCION AUTONOMA:\""""
content = content.replace(old_status, new_status)

# 8. BANNER
banner_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        attr = BANNER_ATTRS.get(mod_name, "total_count")
        banner_lines.append(f'    if genesis.{mod_name}.{attr} > 0:\n        print(f"  {cls_name}: {{genesis.{mod_name}.{attr}}}")')
banner_block = "\n".join(banner_lines)

old_banner = """    if genesis.knowledge_sharing.total_shared > 0:
        print(f"  Knowledge Sharing: {genesis.knowledge_sharing.total_shared} compartidos")

    # Mostrar evolucion autonoma"""
new_banner = f"""    if genesis.knowledge_sharing.total_shared > 0:
        print(f"  Knowledge Sharing: {{genesis.knowledge_sharing.total_shared}} compartidos")
{banner_block}

    # Mostrar evolucion autonoma"""
content = content.replace(old_banner, new_banner)

# 9. HELP
help_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        cmd = COMMANDS[mod_name]
        desc = HELP_DESCS[mod_name]
        label = STATUS_LABELS[mod_name]
        help_lines.append(f"\n  {label}:\n  {cmd:<19}-- {desc}")
help_block = "\n".join(help_lines)

old_help = """  KNOWLEDGE SHARING:
  /knowledge         -- Ver paquetes de conocimiento compartidos

  /last_debate"""
new_help = f"""  KNOWLEDGE SHARING:
  /knowledge         -- Ver paquetes de conocimiento compartidos
{help_block}

  /last_debate"""
content = content.replace(old_help, new_help)

with open("genesis.py", "w", encoding="utf-8") as f:
    f.write(content)
print("genesis.py: OK")

# ============================================================
# WEB_UI.PY
# ============================================================
with open("web_ui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Health grid
health_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        health_lines.append(f'            ("{cls_name}", lambda: True),')
health_block = "\n".join(health_lines)

old_health = '            ("KnowledgeSharing", lambda: True),\n            ("Scheduler", lambda: True),'
new_health = f'            ("KnowledgeSharing", lambda: True),\n{health_block}\n            ("Scheduler", lambda: True),'
content = content.replace(old_health, new_health)

# API stats
api_lines = []
for ver, title, modules, category in VERSIONS:
    for mod_name, cls_name, _ in modules:
        api_lines.append(f'            "{mod_name}": g.{mod_name}.get_stats(),')
api_block = "\n".join(api_lines)

old_api = '            "knowledge_sharing": g.knowledge_sharing.get_stats(),\n            "autonomous": auto_data,'
new_api = f'            "knowledge_sharing": g.knowledge_sharing.get_stats(),\n{api_block}\n            "autonomous": auto_data,'
content = content.replace(old_api, new_api)

with open("web_ui.py", "w", encoding="utf-8") as f:
    f.write(content)
print("web_ui.py: OK")
print("\nAll v3.5-v5.0 integrations applied!")
