"""
Genesis Commands Mixin.

Contiene todos los command handlers (/status, /help, /evolve, etc.):
- handle_command: dispatcher principal
- _cmd_*: handlers individuales de cada comando
- Mutación y evolución de código
"""
import json
import os
import re
import time


class GenesisCommandsMixin:
    """Mixin con todos los command handlers de Genesis."""

    def handle_command(self, command: str) -> str:
        """Procesa comandos especiales (empiezan con /)."""
        cmd = command.strip().lower()

        # Feedback rapido: + y - (sin /)
        if cmd in ("+", "👍"):
            fb_result = self.feedback.rate(positive=True)
            self.auto_learner.record_interaction(
                agent=self._last_agent, template=self._last_template,
                feedback=1, tags=self._last_tags,
                response_time=self._last_response_time,
            )
            self.analytics.track_response(
                agent=self._last_agent, feedback=1,
                response_time=self._last_response_time,
            )
            self.evaluator.record_feedback("+")
            self.personality.evolve_from_feedback("+")
            return fb_result
        elif cmd in ("-", "👎"):
            fb_result = self.feedback.rate(positive=False)
            self.auto_learner.record_interaction(
                agent=self._last_agent, template=self._last_template,
                feedback=-1, tags=self._last_tags,
                response_time=self._last_response_time,
            )
            self.analytics.track_response(
                agent=self._last_agent, feedback=-1,
                response_time=self._last_response_time,
            )
            self.evaluator.record_feedback("-")
            self.personality.evolve_from_feedback("-")
            return fb_result

        if cmd == "/status":
            return self._cmd_status()
        elif cmd == "/evaluate" or cmd == "/eval":
            return self.evaluator.generate_report()
        elif cmd == "/skills":
            return self.skill_memory.generate_report()
        elif cmd == "/chain":
            return self.chain_engine.generate_report()
        elif cmd == "/chain toggle":
            self.chain_engine.enabled = not self.chain_engine.enabled
            state = "habilitado" if self.chain_engine.enabled else "deshabilitado"
            return f"Chain Engine: {state}"
        elif cmd == "/episodes":
            return self.episodic_memory.generate_report()
        elif cmd == "/metalearner":
            return self.meta_learner.generate_report()
        elif cmd == "/personality":
            return self.personality.generate_report()
        elif cmd == "/goals":
            return self.goal_manager.generate_report()
        elif cmd == "/reflection":
            return self.reflection.generate_report()
        elif cmd == "/router":
            return self.context_router.generate_report()
        elif cmd == "/causal":
            return self.causal_reasoner.generate_report()
        elif cmd == "/synthesis":
            return self.concept_synth.generate_report()
        elif cmd == "/planner":
            return self.strategic_planner.generate_report()
        elif cmd == "/predictor":
            return self.pattern_predictor.generate_report()
        elif cmd == "/anomalies":
            return self.anomaly_detector.generate_report()
        elif cmd == "/adaptive":
            return self.adaptive_iface.generate_report()
        elif cmd == "/hypothesis":
            return self.hypothesis_engine.generate_report()
        elif cmd == "/explanations":
            return self.explanation_engine.generate_report()
        elif cmd == "/dialogue":
            return self.dialogue_strategist.generate_report()
        elif cmd == "/cognitive":
            return self.cognitive_monitor.generate_report()
        elif cmd == "/abstraction":
            return self.abstraction_engine.generate_report()
        elif cmd == "/learning":
            return self.learning_optimizer.generate_report()
        elif cmd == "/mind":
            return self.unified_mind.generate_report()
        elif cmd == "/dream":
            return self.dream_engine.generate_report()
        elif cmd == "/narrative":
            return self.self_narrative.generate_report()
        elif cmd == "/emotions":
            return self.emotion_reader.generate_report()
        elif cmd == "/empathy":
            return self.empathy_engine.generate_report()
        elif cmd == "/conflict":
            return self.conflict_resolver.generate_report()
        elif cmd == "/stories":
            return self.story_generator.generate_report()
        elif cmd == "/architect":
            return self.code_architect.generate_report()
        elif cmd == "/brainstorm":
            return self.idea_brainstormer.generate_report()
        elif cmd == "/images":
            return self.image_analyzer.generate_report()
        elif cmd == "/diagrams":
            return self.diagram_generator.generate_report()
        elif cmd == "/voice":
            return self.voice_personality.generate_report()
        elif cmd == "/peer_debate":
            return self.peer_debate.generate_report()
        elif cmd == "/consensus":
            return self.consensus_engine.generate_report()
        elif cmd == "/knowledge":
            return self.knowledge_sharing.generate_report()
        elif cmd == "/papers":
            return self.paper_reader.generate_report()
        elif cmd == "/experiments":
            return self.experiment_runner.generate_report()
        elif cmd == "/insights":
            return self.insight_synthesizer.generate_report()
        elif cmd == "/evolver":
            return self.safe_code_evolver.generate_report()
        elif cmd == "/arch_evolver":
            return self.architecture_evolver.generate_report()
        elif cmd == "/modgen":
            return self.module_generator.generate_report()
        elif cmd == "/temporal":
            return self.temporal_reasoner.generate_report()
        elif cmd == "/schedule":
            return self.schedule_optimizer.generate_report()
        elif cmd == "/trends":
            return self.trend_forecaster.generate_report()
        elif cmd == "/ethics":
            return self.ethical_reasoner.generate_report()
        elif cmd == "/bias":
            return self.bias_detector.generate_report()
        elif cmd == "/transparency":
            return self.transparency_engine.generate_report()
        elif cmd == "/domains":
            return self.domain_expert.generate_report()
        elif cmd == "/tutor":
            return self.tutor_engine.generate_report()
        elif cmd == "/factcheck":
            return self.fact_checker.generate_report()
        elif cmd == "/distribute":
            return self.task_distributor.generate_report()
        elif cmd == "/aggregate":
            return self.result_aggregator.generate_report()
        elif cmd == "/network":
            return self.network_manager.generate_report()
        elif cmd == "/research_loop":
            return self.autonomous_research_loop.generate_report()
        elif cmd == "/self_arch":
            return self.self_architect.generate_report()
        elif cmd == "/consciousness":
            return self.consciousness_integrator.generate_report()
        elif cmd == "/memory semantic":
            return self.semantic_memory.generate_report()
        elif cmd == "/memory":
            return self._cmd_memory()
        elif cmd == "/debate":
            return self._cmd_debate()
        elif cmd == "/evolution":
            return self._cmd_evolution()
        elif cmd == "/curiosity":
            return self._cmd_curiosity()
        elif cmd == "/thinking":
            self.show_thinking = not self.show_thinking
            state = "activado" if self.show_thinking else "desactivado"
            return f"Modo pensamiento visible: {state}"
        elif cmd == "/debate toggle":
            self.debate.enabled = not self.debate.enabled
            state = "activado" if self.debate.enabled else "desactivado"
            return f"Debate interno: {state}"
        elif cmd == "/rollback":
            if self.evolution.rollback():
                return f"Revertido a generacion {self.evolution.get_generation()}"
            return "No se puede revertir mas."
        elif cmd == "/last_debate":
            return self.debate.get_last_debate_log()
        elif cmd == "/code_memory":
            return self._cmd_code_memory()
        elif cmd == "/feedback":
            return self._cmd_feedback()
        elif cmd == "/metrics":
            return self._cmd_metrics()
        elif cmd == "/report":
            return self._cmd_report()
        elif cmd == "/errors":
            return self._cmd_errors()
        elif cmd == "/context":
            return self._cmd_context()
        elif cmd == "/plan":
            return self._cmd_plan()
        elif cmd == "/plan cancel":
            self.task_planner.cancel()
            return "Plan cancelado."
        elif cmd.startswith("/workspace"):
            return self._cmd_workspace(command.strip())
        elif cmd == "/heartbeat":
            return self._cmd_heartbeat()
        elif cmd == "/heartbeat on":
            self.heartbeat.start()
            return "Heartbeat iniciado. Genesis investigara autonomamente."
        elif cmd == "/heartbeat off":
            self.heartbeat.stop()
            return "Heartbeat detenido."
        elif cmd == "/heartbeat notify on":
            self.heartbeat._notify_enabled = True
            return "🔔 Notificaciones desktop activadas."
        elif cmd == "/heartbeat notify off":
            self.heartbeat._notify_enabled = False
            return "🔕 Notificaciones desktop desactivadas."
        elif cmd == "/heartbeat log":
            return self.heartbeat.log.format_recent(20)
        elif cmd == "/heartbeat findings" or cmd == "/hallazgos":
            return self.heartbeat.get_recent_findings(10)
        elif cmd.startswith("/investigar "):
            topic = command[len("/investigar "):].strip()
            if not topic:
                return "Uso: /investigar <tema>"
            self.curiosity.add_question(topic, priority=1.0)
            if not self.heartbeat.running:
                self.heartbeat.start()
            return f"🔬 Tema añadido a cola de investigación: {topic}\nGenesis lo investigará en el próximo ciclo ({self.heartbeat.interval // 60} min)."
        elif cmd == "/evolucionar":
            return self._cmd_confirm_evolution()
        elif cmd == "/rechazar":
            self.heartbeat.reject_evolution()
            return "Evolucion rechazada. Genesis permanece en su generacion actual."
        elif cmd == "/stream":
            self.streaming = not self.streaming
            state = "activado" if self.streaming else "desactivado"
            return f"Streaming: {state}"
        elif cmd == "/backup":
            return self._cmd_backup()
        elif cmd == "/backups":
            return self._cmd_list_backups()
        elif cmd.startswith("/export"):
            arg = command.strip()[7:].strip()
            return self.export_snapshot(arg)
        elif cmd.startswith("/import"):
            arg = command.strip()[7:].strip()
            if not arg:
                return "Uso: /import <ruta_al_snapshot.json>"
            return self.import_snapshot(arg)
        elif cmd == "/logs":
            return self._cmd_logs()
        elif cmd == "/debug":
            self.logger.console_enabled = not self.logger.console_enabled
            state = "activado" if self.logger.console_enabled else "desactivado"
            return f"Logs en consola: {state}"
        # === PLUGINS ===
        elif cmd == "/plugins":
            return self._cmd_plugins()
        elif cmd.startswith("/plugin reload"):
            arg = command.strip()[14:].strip()
            if arg:
                return self.plugins.reload_plugin(arg) and f"Plugin '{arg}' recargado." or f"Error recargando '{arg}'."
            return "Uso: /plugin reload <nombre>"
        elif cmd.startswith("/plugin toggle"):
            arg = command.strip()[14:].strip()
            if arg:
                return self.plugins.toggle_plugin(arg)
            return "Uso: /plugin toggle <nombre>"
        # === JARVIS BRIEFING ===
        elif cmd == "/briefing" or cmd == "/brief" or cmd == "/jarvis":
            return self._cmd_briefing()
        # === SELF-MODIFIER ===
        elif cmd == "/mutate" or cmd.startswith("/mutate "):
            return self._cmd_mutate(command.strip())
        elif cmd == "/self_history":
            return self._cmd_self_history()
        elif cmd == "/self_status":
            return self.self_modifier.status()
        elif cmd == "/self_diff":
            return self.self_modifier.get_pending_diff()
        elif cmd == "/apply":
            return self._cmd_apply_change()
        elif cmd == "/reject":
            return self.self_modifier.reject_change()
        elif cmd == "/self_rollback":
            return self.self_modifier.rollback_last()
        elif cmd == "/timeout":
            return self._cmd_timeout(command.strip())
        # === TOOL CREATOR ===
        elif cmd == "/tools":
            return self._cmd_custom_tools()
        elif cmd.startswith("/tool_delete"):
            arg = command.strip()[12:].strip()
            if arg:
                return self.tool_creator.delete_tool(arg)
            return "Uso: /tool_delete <nombre>"
        elif cmd.startswith("/tool_toggle"):
            arg = command.strip()[12:].strip()
            if arg:
                return self.tool_creator.toggle_tool(arg)
            return "Uso: /tool_toggle <nombre>"
        # === KNOWLEDGE GRAPH ===
        elif cmd == "/knowledge" or cmd == "/kg":
            return self._cmd_knowledge_graph()
        elif cmd.startswith("/kg_search"):
            arg = command.strip()[10:].strip()
            if arg:
                return self._cmd_kg_search(arg)
            return "Uso: /kg_search <concepto>"
        # === PROMPT TEMPLATES ===
        elif cmd == "/templates":
            return self.templates.list_templates()
        elif cmd.startswith("/template"):
            arg = command.strip()[9:].strip()
            if arg:
                return self.templates.set_active(arg)
            return self.templates.list_templates()
        # === PROACTIVE MODE ===
        elif cmd == "/proactive":
            return self.proactive.toggle()
        elif cmd == "/proactive actions":
            actions = self.proactive.SAFE_ACTIONS
            lines = [
                "  ━━━ ACCIONES PROACTIVAS DISPONIBLES ━━━",
            ]
            for aid, info in actions.items():
                lines.append(f"  [{aid}] {info['name']} — {info['description']}")
            lines.append(f"\n  Ejecutadas: {len(self.proactive.executed_actions)}")
            return "\n".join(lines)
        elif cmd.startswith("/proactive run "):
            action_id = command.strip()[14:].strip()
            result = self.proactive.execute_action(action_id, genesis=self)
            if "error" in result:
                return f"[ERROR] {result['error']}"
            return result.get("result", "Accion completada")
        # === SCREENSHOT ===
        elif cmd == "/screenshot" or cmd.startswith("/screenshot "):
            return self._cmd_screenshot(command.strip())
        # === NOTIFICATIONS ===
        elif cmd.startswith("/notify "):
            msg = command.strip()[7:].strip()
            if not msg:
                return "Uso: /notify <mensaje>"
            return self._cmd_notify(msg)
        # === CHART DEMO ===
        elif cmd == "/chart demo":
            return self._cmd_chart_demo()
        # === DOCUMENT GENERATOR ===
        elif cmd == "/doc" or cmd == "/docs":
            return self.doc_generator.list_documents()
        elif cmd.startswith("/doc export "):
            return self._cmd_doc_export(command.strip())
        elif cmd.startswith("/doc "):
            return self._cmd_doc_create(command.strip())
        # === PROJECT GENERATOR ===
        elif cmd.startswith("/generate"):
            return self._cmd_generate(command.strip())
        # === RAG SYSTEM ===
        elif cmd == "/rag" or cmd == "/rag status":
            return self.rag.status()
        elif cmd.startswith("/rag add"):
            arg = command.strip()[8:].strip()
            if not arg:
                return "Uso: /rag add <archivo_o_directorio>"
            return self._cmd_rag_add(arg)
        elif cmd.startswith("/rag search"):
            arg = command.strip()[11:].strip()
            if not arg:
                return "Uso: /rag search <consulta>"
            return self._cmd_rag_search(arg)
        elif cmd == "/rag clear":
            self.rag.clear()
            return "Indice RAG limpiado completamente."
        # === MODEL ROUTER ===
        elif cmd == "/models":
            return self.model_router.list_models()
        elif cmd.startswith("/model "):
            arg = command.strip()[7:].strip()
            if arg == "auto":
                return self.model_router.set_auto()
            return self.model_router.set_model(arg)
        # === VOICE ===
        elif cmd == "/voice":
            return self.voice.toggle()
        elif cmd == "/voice status":
            return self.voice.status()
        elif cmd.startswith("/voice rate"):
            try:
                rate = int(command.strip()[11:].strip())
                self.voice.tts.set_rate(rate)
                return f"Velocidad de voz: {rate} wpm"
            except ValueError:
                return "Uso: /voice rate <numero> (ej: 175)"
        elif cmd == "/voice voices":
            voices = self.voice.tts.list_voices()
            if not voices:
                return "No hay voces disponibles (pyttsx3 no instalado)"
            lines = ["Voces disponibles:"]
            for v in voices:
                lines.append(f"  [{v['id']}] {v['name']}")
            return "\n".join(lines)
        elif cmd.startswith("/voice set"):
            try:
                vid = int(command.strip()[10:].strip())
                return self.voice.tts.set_voice(vid)
            except ValueError:
                return "Uso: /voice set <id>"
        # === AGENT SYSTEM ===
        elif cmd == "/agents":
            return self.agent_system.list_agents()
        elif cmd == "/agent toggle":
            return self.agent_system.toggle()
        elif cmd.startswith("/agent toggle "):
            arg = command.strip()[14:].strip()
            return self.agent_system.toggle_agent(arg)
        elif cmd.startswith("/delegate"):
            arg = command.strip()[9:].strip()
            if not arg:
                return "Uso: /delegate <tarea> o /delegate <agente> <tarea>"
            # Verificar si el primer argumento es un agente
            parts = arg.split(maxsplit=1)
            if parts[0].lower() in self.agent_system.agents and len(parts) > 1:
                result = self.agent_system.delegate(parts[1], agent_name=parts[0].lower())
            else:
                result = self.agent_system.delegate(arg)
            agent_name = result.get("agent", "?")
            role = result.get("role", "?")
            response = result.get("response", "Sin respuesta")
            return f"[Agente: {agent_name} ({role})]\n\n{response}"
        elif cmd == "/agent history":
            return self.agent_system.get_history()
        # === WORKFLOW ENGINE ===
        elif cmd == "/workflows":
            return self.workflow_engine.list_workflows()
        elif cmd.startswith("/workflow run "):
            arg = command.strip()[13:].strip()
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Uso: /workflow run <nombre_workflow> <input>"
            wf_name = parts[0]
            wf_input = parts[1]
            result = self.workflow_engine.run(wf_name, wf_input)
            lines = [f"Workflow: {result['workflow']} ({result['total_time']}s)"]
            for step in result.get("steps", []):
                status = "OK" if step["success"] else "FAIL"
                lines.append(f"  [{status}] {step['name']} ({step['agent']}, {step['time']}s)")
            if result.get("final_output"):
                lines.append(f"\n{result['final_output'][:1000]}")
            return "\n".join(lines)
        elif cmd == "/workflow history":
            return self.workflow_engine.get_history()
        # === SESSION MANAGER ===
        elif cmd == "/sessions":
            return self.session_manager.list_sessions()
        elif cmd.startswith("/session new "):
            arg = command.strip()[13:].strip()
            parts = arg.split(maxsplit=1)
            sid = parts[0]
            topic = parts[1] if len(parts) > 1 else ""
            return self.session_manager.create(sid, topic)
        elif cmd.startswith("/session switch "):
            arg = command.strip()[16:].strip()
            return self.session_manager.switch(arg)
        elif cmd.startswith("/session delete "):
            arg = command.strip()[16:].strip()
            return self.session_manager.delete(arg)
        elif cmd.startswith("/session rename "):
            arg = command.strip()[16:].strip()
            parts = arg.split(maxsplit=1)
            if len(parts) < 2:
                return "Uso: /session rename <id> <nuevo_nombre>"
            return self.session_manager.rename(parts[0], parts[1])
        # === AUTO LEARNER ===
        elif cmd == "/learn" or cmd == "/learning":
            return self.auto_learner.get_insights()
        elif cmd == "/learn rules":
            return self.auto_learner.get_rules_summary()
        elif cmd == "/learn adjustments":
            adj = self.auto_learner.get_agent_adjustments()
            if not adj:
                return "Sin ajustes recomendados (se necesitan mas interacciones con feedback)."
            lines = ["=== Ajustes Recomendados de Agentes ==="]
            for agent, delta in adj.items():
                direction = "subir" if delta > 0 else "bajar"
                lines.append(f"  {agent}: {direction} prioridad en {abs(delta)}")
            return "\n".join(lines)
        # === CONVERSATION ANALYTICS ===
        elif cmd == "/analytics":
            return self.analytics.generate_report()
        elif cmd == "/analytics gaps":
            gaps = self.analytics.gaps.get_gaps(10)
            if not gaps:
                return "Sin gaps de conocimiento detectados."
            lines = ["=== Knowledge Gaps ==="]
            for gap in gaps:
                lines.append(f"  - {gap['query'][:100]}")
            return "\n".join(lines)
        # === ADAPTIVE PROMPTS ===
        elif cmd == "/experiments":
            return self.adaptive_prompts.list_experiments()
        elif cmd.startswith("/experiment create "):
            arg = command.strip()[18:].strip()
            parts = arg.split("|")
            if len(parts) < 2:
                return "Uso: /experiment create <nombre>|<prompt_base>|<variante1>|<variante2>"
            name = parts[0].strip()
            base = parts[1].strip()
            variants = [p.strip() for p in parts[2:] if p.strip()]
            return self.adaptive_prompts.create_experiment(name, base, variants)
        elif cmd.startswith("/experiment delete "):
            arg = command.strip()[18:].strip()
            return self.adaptive_prompts.delete_experiment(arg)

        # --- v1.8 Health Monitor ---
        elif cmd == "/health":
            return self.health_monitor.generate_report()
        elif cmd == "/health check":
            self.health_monitor.run_all_checks()
            return self.health_monitor.generate_report()
        elif cmd == "/health alerts":
            alerts = self.health_monitor.get_active_alerts()
            if not alerts:
                return "  No hay alertas activas."
            lines = [f"  ALERTAS ACTIVAS ({len(alerts)}):"]
            for i, a in enumerate(alerts):
                lines.append(f"    [{i}] [{a.level.upper()}] {a.source}: {a.message}")
            return "\n".join(lines)
        elif cmd.startswith("/health ack"):
            arg = command.strip()[11:].strip()
            if arg == "all":
                n = self.health_monitor.acknowledge_all()
                return f"  {n} alertas reconocidas."
            try:
                idx = int(arg)
                if self.health_monitor.acknowledge_alert(idx):
                    return f"  Alerta [{idx}] reconocida."
                return f"  Indice invalido: {idx}"
            except ValueError:
                return "  Uso: /health ack <indice> o /health ack all"

        # --- v1.8 Rate Limiter ---
        elif cmd == "/ratelimit" or cmd == "/rate":
            return self.rate_limiter.get_usage_report()
        elif cmd == "/ratelimit toggle" or cmd == "/rate toggle":
            state = self.rate_limiter.toggle()
            return f"  Rate Limiter: {'ACTIVADO' if state else 'DESACTIVADO'}"
        elif cmd == "/ratelimit reset" or cmd == "/rate reset":
            self.rate_limiter.reset()
            return "  Todos los buckets reseteados a capacidad completa."

        # --- v1.8 Plugin Marketplace ---
        elif cmd == "/marketplace" or cmd == "/market":
            return self.marketplace.format_marketplace()
        elif cmd.startswith("/marketplace search ") or cmd.startswith("/market search "):
            arg = command.strip().split(" ", 2)[-1].strip()
            results = self.marketplace.search(arg)
            if not results:
                return f"  No se encontraron plugins para '{arg}'."
            lines = [f"  Resultados para '{arg}':"]
            for m in results:
                lines.append(m.format_card())
            return "\n".join(lines)
        elif cmd.startswith("/marketplace install ") or cmd.startswith("/market install "):
            arg = command.strip().split(" ", 2)[-1].strip()
            result = self.marketplace.install_plugin(arg)
            # Recargar plugins despues de instalar
            if "exitosamente" in result:
                self.plugins.load_all(genesis=self)
            return result
        elif cmd.startswith("/marketplace uninstall ") or cmd.startswith("/market uninstall "):
            arg = command.strip().split(" ", 2)[-1].strip()
            result = self.marketplace.uninstall_plugin(arg)
            if "desinstalado" in result.lower():
                self.plugins.unload_plugin(arg)
            return result
        elif cmd.startswith("/marketplace create ") or cmd.startswith("/market create "):
            parts = command.strip().split(" ", 2)
            arg = parts[-1].strip() if len(parts) > 2 else ""
            # Separar nombre y descripcion por |
            if "|" in arg:
                name, desc = arg.split("|", 1)
                return self.marketplace.create_template(name.strip(), desc.strip())
            return self.marketplace.create_template(arg)
        elif cmd.startswith("/marketplace rate ") or cmd.startswith("/market rate "):
            parts = command.strip().split()
            if len(parts) >= 4:
                name = parts[2]
                try:
                    stars = int(parts[3])
                    return self.marketplace.rate_plugin(name, stars)
                except ValueError:
                    return "  Uso: /marketplace rate <nombre> <1-5>"
            return "  Uso: /marketplace rate <nombre> <1-5>"

        # --- v1.9 Task Scheduler ---
        elif cmd == "/scheduler" or cmd == "/sched":
            return self.scheduler.get_full_report()
        elif cmd == "/scheduler tasks" or cmd == "/sched tasks":
            return self.scheduler.get_task_list()
        elif cmd == "/scheduler toggle" or cmd == "/sched toggle":
            return self.scheduler.toggle()
        elif cmd == "/scheduler pause" or cmd == "/sched pause":
            return self.scheduler.pause()
        elif cmd == "/scheduler resume" or cmd == "/sched resume":
            return self.scheduler.resume()
        elif cmd.startswith("/scheduler run ") or cmd.startswith("/sched run "):
            arg = command.strip().split()[-1]
            return self.scheduler.run_task_now(arg)
        elif cmd.startswith("/scheduler toggle ") or cmd.startswith("/sched toggle "):
            arg = command.strip().split()[-1]
            return self.scheduler.toggle_task(arg)
        elif cmd == "/scheduler log" or cmd == "/sched log":
            return self.scheduler.get_log_report()

        # --- v1.9 Config Manager ---
        elif cmd == "/config" or cmd == "/config list":
            return self.config_manager.list_profiles()
        elif cmd.startswith("/config save "):
            parts = command.strip().split(" ", 2)
            name = parts[2] if len(parts) > 2 else "default"
            return self.config_manager.save_profile(name)
        elif cmd.startswith("/config load "):
            arg = command.strip().split()[-1]
            return self.config_manager.apply_profile(arg)
        elif cmd.startswith("/config delete "):
            arg = command.strip().split()[-1]
            return self.config_manager.delete_profile(arg)
        elif cmd.startswith("/config compare "):
            parts = command.strip().split()
            if len(parts) >= 4:
                return self.config_manager.compare_profiles(parts[2], parts[3])
            return "  Uso: /config compare <perfil_a> <perfil_b>"
        elif cmd.startswith("/config export "):
            parts = command.strip().split(" ", 3)
            if len(parts) >= 4:
                return self.config_manager.export_profile(parts[2], parts[3])
            return "  Uso: /config export <nombre> <ruta>"
        elif cmd.startswith("/config import "):
            arg = command.strip()[14:].strip()
            return self.config_manager.import_profile(arg)

        # --- v1.9 Performance Profiler ---
        elif cmd == "/profiler" or cmd == "/perf":
            return self.profiler.generate_report()
        elif cmd == "/profiler toggle" or cmd == "/perf toggle":
            state = self.profiler.toggle()
            return f"  Profiler: {'ACTIVADO' if state else 'DESACTIVADO'}"
        elif cmd == "/profiler reset" or cmd == "/perf reset":
            self.profiler.reset()
            return "  Profiler reseteado."
        elif cmd == "/profiler bottlenecks" or cmd == "/perf bottlenecks":
            bottlenecks = self.profiler.get_bottlenecks(10)
            if not bottlenecks:
                return "  Sin datos de profiling."
            lines = ["  TOP 10 BOTTLENECKS:"]
            for b in bottlenecks:
                lines.append(
                    f"    {b['name']:30s} avg:{b['avg_ms']:8.1f}ms  "
                    f"p95:{b['p95_ms']:8.1f}ms  calls:{b['total_calls']}"
                )
            return "\n".join(lines)
        elif cmd == "/profiler slow" or cmd == "/perf slow":
            slow = self.profiler.get_slow_operations()
            if not slow:
                return "  No hay operaciones lentas."
            lines = ["  OPERACIONES LENTAS:"]
            for s in slow:
                lines.append(
                    f"    {s['name']:30s} avg:{s['avg_ms']:.1f}ms  max:{s['max_ms']:.1f}ms"
                )
            return "\n".join(lines)

        # --- v2.0 Embeddings Engine ---
        elif cmd == "/embeddings" or cmd == "/emb":
            return self.embeddings.generate_report()
        elif cmd.startswith("/embeddings add ") or cmd.startswith("/emb add "):
            parts = command.strip().split(" ", 3)
            if len(parts) >= 4:
                doc_id = parts[2]
                text = parts[3]
                ok = self.embeddings.add_text(doc_id, text, source="manual")
                return f"  Documento '{doc_id}' {'agregado' if ok else 'ERROR al agregar'}."
            return "  Uso: /embeddings add <id> <texto>"
        elif cmd.startswith("/embeddings search ") or cmd.startswith("/emb search "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /embeddings search <query>"
            results = self.embeddings.search(query, top_k=10)
            if not results:
                return "  Sin resultados."
            lines = [f"  BUSQUEDA SEMANTICA: '{query}'", ""]
            for r in results:
                text_preview = r["metadata"].get("text", "")[:80]
                lines.append(f"    [{r['score']:.3f}] {r['id']}: {text_preview}...")
            return "\n".join(lines)
        elif cmd.startswith("/embeddings similar ") or cmd.startswith("/emb similar "):
            doc_id = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not doc_id:
                return "  Uso: /embeddings similar <doc_id>"
            results = self.embeddings.get_similar(doc_id, top_k=5)
            if not results:
                return f"  Sin documentos similares a '{doc_id}'."
            lines = [f"  SIMILARES A '{doc_id}':"]
            for r in results:
                lines.append(f"    [{r['score']:.3f}] {r['id']}")
            return "\n".join(lines)
        elif cmd == "/embeddings save" or cmd == "/emb save":
            self.embeddings.save()
            return "  Vector store guardado a disco."
        elif cmd == "/embeddings clear" or cmd == "/emb clear":
            self.embeddings.clear()
            return "  Vector store limpiado."

        # --- v2.0 Dashboard API ---
        elif cmd == "/dashboard" or cmd == "/dash":
            return self.dashboard.generate_dashboard()
        elif cmd == "/dashboard json" or cmd == "/dash json":
            return self.dashboard.export_json()
        elif cmd == "/dashboard summary" or cmd == "/dash summary":
            summary = self.dashboard.get_summary()
            lines = ["  RESUMEN EJECUTIVO:"]
            for k, v in summary.items():
                lines.append(f"    {k}: {v}")
            return "\n".join(lines)
        elif cmd == "/dashboard categories" or cmd == "/dash categories":
            cats = self.dashboard.get_categories()
            lines = ["  CATEGORIAS:"]
            for cat, info in cats.items():
                desc = info.get("description", "")
                subs = ", ".join(info.get("subsystems", []))
                lines.append(f"    [{cat}] {desc}")
                lines.append(f"      -> {subs}")
            return "\n".join(lines)
        elif cmd.startswith("/dashboard timeline ") or cmd.startswith("/dash timeline "):
            parts = command.strip().split()
            if len(parts) >= 4:
                sub = parts[2]
                metric = parts[3]
                series = self.dashboard.get_timeline(sub, metric)
                if not series:
                    return f"  Sin datos para {sub}.{metric}"
                lines = [f"  TIMELINE: {sub}.{metric} ({len(series)} puntos)"]
                for p in series[-10:]:
                    from datetime import datetime
                    ts = datetime.fromtimestamp(p["timestamp"]).strftime("%H:%M:%S")
                    lines.append(f"    [{ts}] {p['value']}")
                return "\n".join(lines)
            return "  Uso: /dashboard timeline <subsistema> <metrica>"

        # --- v2.0 Autonomous Mode ---
        elif cmd == "/autonomous" or cmd == "/auto":
            return self.autonomous.generate_report()
        elif cmd == "/autonomous start" or cmd == "/auto start":
            return self.autonomous.start()
        elif cmd.startswith("/autonomous start ") or cmd.startswith("/auto start "):
            parts = command.strip().split()
            cycles = 0
            duration = 0
            for p in parts[2:]:
                if p.isdigit():
                    cycles = int(p)
                elif p.endswith("m") and p[:-1].isdigit():
                    duration = float(p[:-1])
            return self.autonomous.start(max_cycles=cycles, max_duration_minutes=duration)
        elif cmd == "/autonomous stop" or cmd == "/auto stop":
            return self.autonomous.stop()
        elif cmd == "/autonomous pause" or cmd == "/auto pause":
            return self.autonomous.pause()
        elif cmd == "/autonomous resume" or cmd == "/auto resume":
            return self.autonomous.resume()
        elif cmd == "/autonomous actions" or cmd == "/auto actions":
            return f"  ACCIONES REGISTRADAS:\n{self.autonomous.get_action_list()}"
        elif cmd == "/autonomous log" or cmd == "/auto log":
            return f"  LOG AUTONOMO:\n{self.autonomous.get_log_report(20)}"
        elif cmd == "/autonomous tick" or cmd == "/auto tick":
            results = self.autonomous.tick()
            if not results:
                return "  Tick: sin acciones ejecutadas."
            lines = ["  TICK AUTONOMO:"]
            for r in results:
                status = "OK" if r.get("success") else "FAIL"
                lines.append(f"    {r['action']}: {status} ({r.get('duration_ms', 0):.0f}ms)")
            return "\n".join(lines)

        # --- v2.1 Evolucion Autonoma (atajo) ---
        elif cmd == "/evolve":
            return self._cmd_evolve(command.strip())
        elif cmd.startswith("/evolve "):
            return self._cmd_evolve(command.strip())

        # --- v2.1 Web Intelligence ---
        elif cmd == "/web" or cmd == "/internet":
            return self.web.generate_report()
        elif cmd.startswith("/web search ") or cmd.startswith("/internet search "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web search <query>"
            results = self.web.search(query)
            if not results:
                return f"  Sin resultados para \"{query}\". Verificar conexion."
            lines = [f"  RESULTADOS: \"{query}\"", ""]
            for i, r in enumerate(results):
                lines.append(f"    {i+1}. {r.title[:65]}")
                lines.append(f"       {r.url}")
                lines.append(f"       {r.snippet[:100]}")
                lines.append("")
            return "\n".join(lines)
        elif cmd.startswith("/web read "):
            url = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not url:
                return "  Uso: /web read <url>"
            page = self.web.read(url)
            if not page:
                return f"  No se pudo leer: {url}"
            lines = [
                f"  PAGINA: {page.title}",
                f"  URL: {page.url}",
                f"  Palabras: {page.word_count} | Tiempo: {page.fetch_time_ms:.0f}ms",
                f"  Links: {len(page.links)}",
                "",
                page.get_summary(1500),
            ]
            return "\n".join(lines)
        elif cmd.startswith("/web learn "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web learn <tema>"
            return self.web.search_and_learn(query, max_results=5, max_pages=3)
        elif cmd.startswith("/web news "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web news <tema>"
            results = self.web.search_news(query)
            if not results:
                return f"  Sin noticias para \"{query}\"."
            lines = [f"  NOTICIAS: \"{query}\"", ""]
            for i, r in enumerate(results):
                lines.append(f"    {i+1}. {r.title[:65]}")
                lines.append(f"       {r.url}")
                lines.append("")
            return "\n".join(lines)
        elif cmd == "/web history":
            return self.web.get_search_history(15)
        elif cmd == "/web learned" or cmd == "/web memory":
            return self.web.get_learned_summary(15)
        elif cmd.startswith("/web recall "):
            query = command.strip().split(" ", 2)[2] if len(command.strip().split(" ", 2)) > 2 else ""
            if not query:
                return "  Uso: /web recall <query>"
            results = self.web.recall(query, top_k=10)
            if not results:
                return f"  Sin conocimiento aprendido sobre \"{query}\"."
            lines = [f"  RECALL: \"{query}\"", ""]
            for r in results:
                source = r["metadata"].get("source", "")
                text = r["metadata"].get("text", "")[:100]
                lines.append(f"    [{r['score']:.3f}] {source}")
                lines.append(f"      {text}...")
                lines.append("")
            return "\n".join(lines)

        elif cmd == "/help":
            return self._cmd_help()
        elif cmd in ("/exit", "/quit", "/salir"):
            self._save_session()
            try:
                self.episodic_memory.end_episode(
                    [{"role": "user", "content": q} for q in (self.episodic_memory.current_episode.user_queries if self.episodic_memory.current_episode else [])]
                )
            except (AttributeError, TypeError):
                pass
            self.heartbeat.stop()
            self.running = False
            return "Cerrando Genesis..."
        else:
            # Intentar ejecutar como comando de plugin
            plugin_result = self.plugins.handle_command(command.strip())
            if plugin_result is not None:
                return plugin_result
            return f"Comando desconocido: {cmd}. Escribe /help para ver comandos."

    def _cmd_status(self) -> str:
        """Muestra el estado completo de Genesis."""
        lines = [
            f"╔══ {GENESIS_NAME} v{GENESIS_VERSION} ══╗",
            f"",
            f"CEREBRO:",
        ]
        stats = self.brain.get_stats()
        lines += [
            f"  Proveedor: {stats.get('provider', LLM_PROVIDER)}",
            f"  Modelo: {stats.get('model', 'unknown')}",
            f"  Disponible: {'Si' if self.brain.is_available() else 'NO'}",
            f"  Tokens usados: {stats.get('total_tokens', 0)}",
            f"",
            f"MEMORIA:",
            self.memory.status(),
            f"",
            f"EVOLUCION:",
            self.evolution.status(),
            f"",
            f"DEBATE:",
            self.debate.status(),
            f"",
            f"CURIOSIDAD:",
            self.curiosity.status(),
            f"",
            f"CODIGO:",
            self.code_memory.format_stats(),
            f"",
            f"WORKSPACE:",
            self.workspace.status(),
            f"",
            f"FEEDBACK:",
            self.feedback.status(),
            f"",
            f"METRICAS:",
            self.metrics.status(),
            f"",
            f"ERRORES:",
            self.error_memory.status(),
            f"",
            f"PLAN:",
            self.task_planner.status(),
            f"",
            f"ROUTER:",
            self.router.status(),
            f"",
            f"CONTEXTO:",
            self.context_manager.status(),
            f"",
            f"SUMMARIZER:",
            self.summarizer.status(),
            f"",
            f"HEARTBEAT:",
            self.heartbeat.status(),
            f"",
            f"LOGGER:",
            self.logger.status(),
            f"",
            f"BACKUPS:",
            self.backup_manager.status(),
            f"",
            f"KNOWLEDGE GRAPH:",
            self.knowledge_graph.status(),
            f"",
            f"TOOLS CUSTOM:",
            self.tool_creator.status(),
            f"",
            f"PLUGINS:",
            self.plugins.status(),
            f"",
            f"AUTO-MODIFICACION:",
            self.self_modifier.status(),
            f"",
            f"PROMPT TEMPLATES:",
            self.templates.status(),
            f"",
            f"PROACTIVO:",
            self.proactive.status(),
            f"",
            f"GENERADOR DE PROYECTOS:",
            self.project_generator.status(),
            f"",
            f"RAG:",
            f"  Archivos: {len(self.rag.indexed_files)} | Chunks: {len(self.rag.chunks)} | Queries: {self.rag.total_queries}",
            f"",
            f"MODEL ROUTER:",
            self.model_router.status(),
            f"",
            f"VOZ:",
            f"  TTS: {'disponible' if self.voice.tts.available else 'NO'} | STT: {'disponible' if self.voice.stt.available else 'NO'} | Estado: {'ON' if self.voice.enabled else 'OFF'}",
            f"",
            f"AGENTES:",
            self.agent_system.status(),
            f"",
            f"WORKFLOWS:",
            self.workflow_engine.status(),
            f"",
            f"SESIONES:",
            self.session_manager.status(),
            f"",
            f"AUTO-LEARNER:",
            self.auto_learner.status(),
            f"",
            f"ANALYTICS:",
            self.analytics.status(),
            f"",
            f"ADAPTIVE PROMPTS:",
            self.adaptive_prompts.status(),
            f"",
            f"HEALTH MONITOR:",
            self.health_monitor.status(),
            f"",
            f"RATE LIMITER:",
            self.rate_limiter.status(),
            f"",
            f"MARKETPLACE:",
            self.marketplace.status(),
            f"",
            f"SCHEDULER:",
            self.scheduler.status(),
            f"",
            f"CONFIG MANAGER:",
            self.config_manager.status(),
            f"",
            f"PROFILER:",
            self.profiler.status(),
            f"",
            f"EMBEDDINGS:",
            self.embeddings.status(),
            f"",
            f"DASHBOARD:",
            self.dashboard.status(),
            f"",
            f"AUTONOMOUS MODE:",
            self.autonomous.status(),
            f"",
            f"WEB INTELLIGENCE:",
            self.web.status(),
            f"",
            f"SEMANTIC MEMORY:",
            self.semantic_memory.status(),
            f"",
            f"INFERENCE OPTIMIZER:",
            self.optimizer.status(),
            f"",
            f"SELF-EVALUATOR:",
            self.evaluator.status(),
            f"",
            f"SKILL MEMORY:",
            self.skill_memory.status(),
            f"",
            f"CHAIN ENGINE:",
            self.chain_engine.status(),
            f"",
            f"EPISODIC MEMORY:",
            self.episodic_memory.status(),
            f"",
            f"META-LEARNER:",
            self.meta_learner.status(),
            f"",
            f"PERSONALITY:",
            self.personality.status(),
            f"",
            f"GOAL MANAGER:",
            self.goal_manager.status(),
            f"",
            f"REFLECTION ENGINE:",
            self.reflection.status(),
            f"",
            f"CONTEXT ROUTER:",
            self.context_router.status(),
            f"",
            f"CAUSAL REASONER:",
            self.causal_reasoner.status(),
            f"",
            f"CONCEPT SYNTHESIZER:",
            self.concept_synth.status(),
            f"",
            f"STRATEGIC PLANNER:",
            self.strategic_planner.status(),
            f"",
            f"PATTERN PREDICTOR:",
            self.pattern_predictor.status(),
            f"",
            f"ANOMALY DETECTOR:",
            self.anomaly_detector.status(),
            f"",
            f"ADAPTIVE INTERFACE:",
            self.adaptive_iface.status(),
            f"",
            f"HYPOTHESIS ENGINE:",
            self.hypothesis_engine.status(),
            f"",
            f"EXPLANATION ENGINE:",
            self.explanation_engine.status(),
            f"",
            f"DIALOGUE STRATEGIST:",
            self.dialogue_strategist.status(),
            f"",
            f"COGNITIVE MONITOR:",
            self.cognitive_monitor.status(),
            f"",
            f"ABSTRACTION ENGINE:",
            self.abstraction_engine.status(),
            f"",
            f"LEARNING OPTIMIZER:",
            self.learning_optimizer.status(),
            f"",
            f"UNIFIED MIND:",
            self.unified_mind.status(),
            f"",
            f"DREAM ENGINE:",
            self.dream_engine.status(),
            f"",
            f"SELF-NARRATIVE:",
            self.self_narrative.status(),
            f"",
            f"EMOTION READER:",
            self.emotion_reader.status(),
            f"",
            f"EMPATHY ENGINE:",
            self.empathy_engine.status(),
            f"",
            f"CONFLICT RESOLVER:",
            self.conflict_resolver.status(),
            f"",
            f"STORY GENERATOR:",
            self.story_generator.status(),
            f"",
            f"CODE ARCHITECT:",
            self.code_architect.status(),
            f"",
            f"IDEA BRAINSTORMER:",
            self.idea_brainstormer.status(),
            f"",
            f"IMAGE ANALYZER:",
            self.image_analyzer.status(),
            f"",
            f"DIAGRAM GENERATOR:",
            self.diagram_generator.status(),
            f"",
            f"VOICE PERSONALITY:",
            self.voice_personality.status(),
            f"",
            f"PEER DEBATE:",
            self.peer_debate.status(),
            f"",
            f"CONSENSUS ENGINE:",
            self.consensus_engine.status(),
            f"",
            f"KNOWLEDGE SHARING:",
            self.knowledge_sharing.status(),
            f"",
            f"PAPER READER:",
            self.paper_reader.status(),
            f"",
            f"EXPERIMENT RUNNER:",
            self.experiment_runner.status(),
            f"",
            f"INSIGHT SYNTHESIZER:",
            self.insight_synthesizer.status(),
            f"",
            f"SAFE CODE EVOLVER:",
            self.safe_code_evolver.status(),
            f"",
            f"ARCHITECTURE EVOLVER:",
            self.architecture_evolver.status(),
            f"",
            f"MODULE GENERATOR:",
            self.module_generator.status(),
            f"",
            f"TEMPORAL REASONER:",
            self.temporal_reasoner.status(),
            f"",
            f"SCHEDULE OPTIMIZER:",
            self.schedule_optimizer.status(),
            f"",
            f"TREND FORECASTER:",
            self.trend_forecaster.status(),
            f"",
            f"ETHICAL REASONER:",
            self.ethical_reasoner.status(),
            f"",
            f"BIAS DETECTOR:",
            self.bias_detector.status(),
            f"",
            f"TRANSPARENCY ENGINE:",
            self.transparency_engine.status(),
            f"",
            f"DOMAIN EXPERT:",
            self.domain_expert.status(),
            f"",
            f"TUTOR ENGINE:",
            self.tutor_engine.status(),
            f"",
            f"FACT CHECKER:",
            self.fact_checker.status(),
            f"",
            f"TASK DISTRIBUTOR:",
            self.task_distributor.status(),
            f"",
            f"RESULT AGGREGATOR:",
            self.result_aggregator.status(),
            f"",
            f"NETWORK MANAGER:",
            self.network_manager.status(),
            f"",
            f"AUTONOMOUS RESEARCH LOOP:",
            self.autonomous_research_loop.status(),
            f"",
            f"SELF ARCHITECT:",
            self.self_architect.status(),
            f"",
            f"CONSCIOUSNESS INTEGRATOR:",
            self.consciousness_integrator.status(),
            f"",
            f"EVOLUCION AUTONOMA:",
            f"  Estado: {'ACTIVA' if self.autonomous.active else 'inactiva'}",
            f"  Acciones: {len(self.autonomous.actions)} registradas",
            f"  Ciclos: {self.autonomous.total_cycles}",
            f"  Ejecutadas: {self.autonomous.total_actions}",
            f"",
            f"STREAMING: {'activado' if self.streaming else 'desactivado'}",
            f"TIMEOUT LLM: {self.llm_timeout}s",
        ]
        return "\n".join(lines)

    def _cmd_memory(self) -> str:
        """Muestra el contenido de la memoria."""
        lines = ["=== MEMORIA DE LARGO PLAZO ==="]
        lines.append(self.memory.long_term.get_all_formatted())
        lines.append("\n=== MEMORIA EMOCIONAL ===")
        emotional_ctx = self.memory.emotional.get_emotional_context()
        lines.append(emotional_ctx if emotional_ctx else "Vacia")
        return "\n".join(lines)

    def _cmd_debate(self) -> str:
        """Muestra estado del debate."""
        return self.debate.status()

    def _cmd_evolution(self) -> str:
        """Muestra estado de evolucion."""
        lines = ["=== ESTADO DE EVOLUCION ==="]
        lines.append(self.evolution.status())
        lines.append(f"\n=== PROMPT ACTUAL (Gen {self.evolution.get_generation()}) ===")
        lines.append(self.evolution.get_current_prompt()[:500])
        if len(self.evolution.get_current_prompt()) > 500:
            lines.append("... [truncado]")
        return "\n".join(lines)

    def _cmd_curiosity(self) -> str:
        """Muestra preguntas pendientes de curiosidad."""
        lines = ["=== CURIOSIDAD ACTIVA ==="]
        pending = self.curiosity.get_pending_questions(10)
        if pending:
            for q in pending:
                lines.append(f"  [{q['priority']:.1f}] {q['question']}")
        else:
            lines.append("  No hay preguntas pendientes.")
        return "\n".join(lines)

    def _cmd_workspace(self, command: str) -> str:
        """Gestiona el workspace activo."""
        parts = command.split(maxsplit=1)

        # /workspace (sin args) — mostrar estado
        if len(parts) == 1:
            return f"=== WORKSPACE ===\n{self.workspace.status()}"

        arg = parts[1].strip()

        # /workspace clear — limpiar
        if arg == "clear":
            self.workspace.clear()
            return "Workspace limpiado."

        # /workspace scan — re-escanear
        if arg == "scan":
            if not self.workspace.is_set():
                return "No hay workspace activo. Usa /workspace <ruta>"
            result = self.workspace.scan()
            return f"=== WORKSPACE RE-ESCANEADO ===\n{result}"

        # /workspace <ruta> — establecer nuevo workspace
        result = self.workspace.set(arg)
        return f"=== WORKSPACE ESTABLECIDO ===\n{result}"

    def _cmd_feedback(self) -> str:
        """Muestra estadisticas de feedback."""
        lines = ["=== FEEDBACK DEL USUARIO ==="]
        lines.append(self.feedback.format_stats())

        # Ultimos ratings negativos (para analisis)
        failures = self.feedback.get_recent_failures(3)
        if failures:
            lines.append("\n  Ultimas respuestas negativas:")
            for f in failures:
                lines.append(f"    - {f['user_input'][:80]}...")
        return "\n".join(lines)

    def _cmd_metrics(self) -> str:
        """Muestra metricas de rendimiento."""
        lines = []
        lines.append(self.metrics.format_session_report())
        lines.append("")
        lines.append(self.metrics.format_historical_report())
        return "\n".join(lines)

    def _cmd_report(self) -> str:
        """Reporte completo combinando feedback + metricas + evolucion."""
        lines = [
            f"╔══ REPORTE COMPLETO — {GENESIS_NAME} v{GENESIS_VERSION} ══╗\n",
        ]

        # Fitness combinado
        feedback_fitness = self.feedback.get_fitness_from_feedback()
        metrics_fitness = self.metrics.get_session_fitness()
        historical_fitness = self.metrics.get_historical_fitness()
        combined = int(feedback_fitness * 0.4 + metrics_fitness * 0.3 + historical_fitness * 0.3)

        lines.append(f"  FITNESS COMBINADO: {combined}/100")
        lines.append(f"    De feedback usuario: {feedback_fitness}/100 (peso 40%)")
        lines.append(f"    De sesion actual:    {metrics_fitness}/100 (peso 30%)")
        lines.append(f"    De historial:        {historical_fitness}/100 (peso 30%)")
        lines.append(f"")

        # Tendencia
        lines.append(f"  Tendencia: {self.metrics.get_trend()}")
        lines.append(f"  Aprobacion: {self.feedback.get_satisfaction_rate()*100:.0f}%")
        lines.append(f"")

        # Evolucion
        gen = self.evolution.get_generation()
        lines.append(f"  Generacion: {gen}")
        lines.append(f"  Evoluciones: {self.evolution.state.get('total_evolutions', 0)}")
        lines.append(f"")

        # Resumen de sesion
        s = self.metrics.session
        lines.append(f"  Sesion actual:")
        lines.append(f"    Interacciones: {s['interactions']}")
        if s['code_runs'] > 0:
            rate = self.metrics.get_code_success_rate() * 100
            lines.append(f"    Codigo: {s['code_runs']} ejecuciones, {rate:.0f}% exito")
        lines.append(f"    Herramientas: {sum(s['tool_uses'].values())} usos")

        lines.append(f"\n╚══{'═' * 42}══╝")
        return "\n".join(lines)

    def _cmd_errors(self) -> str:
        """Muestra la memoria de errores."""
        lines = ["=== MEMORIA DE ERRORES ==="]
        lines.append(self.error_memory.format_stats())
        return "\n".join(lines)

    def _cmd_context(self) -> str:
        """Muestra el presupuesto de tokens y estado del contexto."""
        budget = self.context_manager.get_budget_status()
        pct = (budget["total_used"] / budget["usable_tokens"] * 100
               if budget["usable_tokens"] > 0 else 0)

        lines = [
            "=== PRESUPUESTO DE CONTEXTO ===",
            f"",
            f"  Contexto total:    {budget['max_context']} tokens",
            f"  Reserva respuesta: {budget['response_reserve']} tokens",
            f"  Tokens usables:    {budget['usable_tokens']} tokens",
            f"",
            f"  System prompt:",
            f"    Presupuesto: {budget['system_budget']} tokens",
            f"    Usado:       {budget['system_used']} tokens",
            f"",
            f"  Conversacion:",
            f"    Presupuesto: {budget['conversation_budget']} tokens",
            f"    Usado:       {budget['conversation_used']} tokens",
            f"",
            f"  Total usado: {budget['total_used']}/{budget['usable_tokens']} ({pct:.0f}%)",
            f"  Tokens libres: {budget['free_tokens']}",
            f"  Overflows: {budget['total_overflows']}",
        ]

        if budget["sections_trimmed"]:
            lines.append(f"\n  Secciones recortadas: {', '.join(budget['sections_trimmed'])}")

        # Info del summarizer
        lines.append(f"\n  SUMMARIZER:")
        lines.append(f"  {self.summarizer.status()}")

        return "\n".join(lines)

    def _cmd_plan(self) -> str:
        """Muestra el plan activo."""
        return self.task_planner.format_plan()

    def _cmd_code_memory(self) -> str:
        """Muestra la memoria de codigo."""
        lines = ["=== MEMORIA DE CODIGO ==="]
        lines.append(self.code_memory.format_stats())

        # Mostrar ultimas soluciones
        if self.code_memory.solutions:
            lines.append(f"\n  Ultimas soluciones:")
            for sol in self.code_memory.solutions[-5:]:
                task = sol["task"][:60]
                lang = sol["language"]
                code_lines = len(sol["code"].split("\n"))
                lines.append(f"    [{lang}] {task} ({code_lines} lineas)")
        return "\n".join(lines)

    def _cmd_heartbeat(self) -> str:
        """Muestra estado del heartbeat."""
        lines = ["=== HEARTBEAT ==="]
        lines.append(self.heartbeat.status())
        return "\n".join(lines)

    def _cmd_backup(self) -> str:
        """Crea un backup manual de todos los datos."""
        result = self.backup_manager.create_backup(label="manual")
        if result:
            return f"Backup creado: {result.name}"
        return "No habia datos para respaldar."

    def _cmd_list_backups(self) -> str:
        """Lista los backups disponibles."""
        backups = self.backup_manager.list_backups()
        if not backups:
            return "No hay backups disponibles."
        lines = ["=== BACKUPS DISPONIBLES ==="]
        for b in backups:
            t = time.strftime("%d/%m/%Y %H:%M", time.localtime(b["created"]))
            lines.append(f"  {b['name']} — {t} ({b['files']} archivos, {b['size_kb']:.1f} KB)")
        return "\n".join(lines)

    def _cmd_logs(self) -> str:
        """Muestra los ultimos logs."""
        return self.logger.get_recent_logs(n=30, level="INFO")

    def _cmd_plugins(self) -> str:
        """Lista los plugins instalados."""
        lines = ["=== PLUGINS ==="]
        lines.append(self.plugins.list_plugins())
        lines.append(f"\n  Directorio: {self.plugins.plugins_dir}")
        lines.append(f"  Para crear plugins, agrega archivos .py en esa carpeta.")
        plugin_help = self.plugins.get_commands_help()
        if plugin_help:
            lines.append(f"\n{plugin_help}")
        return "\n".join(lines)

    def _cmd_self_history(self) -> str:
        """Muestra historial de auto-modificaciones."""
        lines = ["=== HISTORIAL DE AUTO-MODIFICACIONES ==="]
        lines.append(self.self_modifier.format_history(15))
        return "\n".join(lines)

    def _cmd_apply_change(self) -> str:
        """Aplica el cambio pendiente del self-modifier."""
        if not self.self_modifier.pending_change:
            return "No hay cambio pendiente. Genesis debe proponer uno primero."
        result = self.self_modifier.apply_change()
        self.log.info(f"Self-Modifier: {result['message']}")
        return result["message"]

    def _cmd_mutate(self, command: str) -> str:
        """
        Genesis muta su propio codigo fuente.

        /mutate              — Analiza un modulo y propone mejoras
        /mutate <archivo>    — Muta un archivo especifico (ej: core/tools.py)
        /mutate auto         — Deja que Genesis elija que mutar
        /mutate list         — Lista archivos mutables

        Flujo:
        1. Lee el archivo objetivo
        2. Le pide al LLM que proponga mejoras
        3. Valida syntax Python + patrones peligrosos
        4. Muestra diff al usuario
        5. El usuario aprueba con /apply o rechaza con /reject
        """
        parts = command.split(maxsplit=1)
        arg = parts[1].strip() if len(parts) > 1 else "auto"

        if arg == "list":
            return self._mutate_list_files()

        if arg == "auto":
            target_file = self._mutate_pick_target()
            if not target_file:
                return "No se encontro un archivo candidato para mutar."
        else:
            target_file = arg
            # Normalizar separadores
            target_file = target_file.replace("\\", "/")

        # Verificar que el archivo existe
        from pathlib import Path as P
        full_path = (P(self.self_modifier.genesis_dir) / target_file).resolve()
        if not full_path.exists():
            return f"Archivo no encontrado: {target_file}"

        if not str(full_path).endswith(".py"):
            return "Solo se pueden mutar archivos .py"

        # Leer contenido actual
        try:
            current_code = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return f"Error leyendo {target_file}: {e}"

        if len(current_code) > 15000:
            # Para archivos muy grandes, solo enviar las primeras 300 lineas
            code_lines = current_code.split("\n")
            analysis_code = "\n".join(code_lines[:300])
            truncated = True
        else:
            analysis_code = current_code
            truncated = False

        # Pedir al LLM que proponga mejoras
        mutate_prompt = (
            f"TAREA: Analizar y mejorar este codigo Python de Genesis.\n"
            f"Archivo: {target_file}\n"
            f"{'(NOTA: Codigo truncado a 300 lineas por tamaño)' if truncated else ''}\n\n"
            f"CODIGO ACTUAL:\n```python\n{analysis_code}\n```\n\n"
            f"INSTRUCCIONES:\n"
            f"1. Identifica UNA mejora concreta (bug, optimizacion, nueva funcionalidad menor)\n"
            f"2. Genera el archivo COMPLETO con la mejora aplicada\n"
            f"3. NO cambies la estructura general, solo haz la mejora puntual\n"
            f"4. Mantén TODOS los imports, clases y metodos existentes\n"
            f"5. Si el codigo esta truncado, devuelve solo la parte que modificas\n"
            f"6. Responde SOLO con el codigo Python mejorado, sin explicaciones\n"
            f"7. NO uses bloques ``` markdown, solo el codigo puro\n"
        )

        self.log.info(f"Self-Modifier: Analizando {target_file} para mutacion...")
        print(f"  Analizando {target_file} ({len(current_code)} bytes)...")

        new_code = self.brain.quick_think(
            mutate_prompt,
            system=(
                "Eres un ingeniero de software experto. Analiza el codigo y genera "
                "una version mejorada. Responde UNICAMENTE con codigo Python valido. "
                "Sin explicaciones, sin markdown, sin bloques de codigo. Solo Python puro."
            ),
            temperature=0.3,
        )

        if not new_code or len(new_code) < 50 or "[ERROR]" in new_code:
            return f"El LLM no pudo generar una mejora para {target_file}."

        # Limpiar posibles artefactos del LLM
        new_code = new_code.strip()
        if new_code.startswith("```"):
            lines = new_code.split("\n")
            # Remover primera y ultima linea de bloques de codigo
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            new_code = "\n".join(lines)

        # Si el archivo estaba truncado, no reemplazar todo — abortar
        if truncated and len(new_code.split("\n")) < len(current_code.split("\n")) * 0.5:
            return (
                f"Archivo {target_file} es muy grande ({len(current_code.split(chr(10)))} lineas). "
                f"La mutacion parcial no es segura. Usa /mutate <archivo_mas_pequeno>."
            )

        # Si estaba truncado, usar el codigo original con el nuevo pegado
        if truncated:
            new_code = new_code  # El LLM devolvio solo la parte modificada
            # Concatenar con el resto del archivo original
            original_lines = current_code.split("\n")
            new_lines = new_code.split("\n")
            if len(new_lines) <= 300:
                # Reemplazar las primeras 300 lineas con las nuevas
                merged = new_lines + original_lines[300:]
                new_code = "\n".join(merged)

        # Proponer el cambio via SelfModifier (valida syntax, seguridad, diff)
        result = self.self_modifier.propose_change(
            filepath=target_file,
            new_content=new_code,
            reason="auto-mutacion",
            description=f"Mutacion automatica de {target_file} via LLM",
        )

        status = result.get("status")
        if status == "rejected":
            return f"Mutacion RECHAZADA por seguridad: {result.get('error', 'desconocido')}"
        elif status == "no_change":
            return f"El LLM no genero cambios para {target_file}. El codigo ya esta optimo."
        elif status == "pending":
            lines = [
                f"  === MUTACION PROPUESTA: {target_file} ===",
                f"  +{result['additions']} lineas / -{result['deletions']} lineas",
            ]
            if result.get("is_critical"):
                lines.append("  ⚠ ARCHIVO CRITICO — requiere confirmacion")
            if result.get("warnings"):
                for w in result["warnings"]:
                    lines.append(f"  ⚠ {w}")
            lines.append("")
            # Mostrar diff (primeras 40 lineas)
            diff_lines = result["diff"].split("\n")
            for dl in diff_lines[:40]:
                lines.append(f"  {dl}")
            if len(diff_lines) > 40:
                lines.append(f"  ... ({len(diff_lines) - 40} lineas mas)")
            lines.append("")
            lines.append("  Escribe /apply para aplicar o /reject para rechazar.")
            lines.append("  Usa /self_diff para ver el diff completo.")
            return "\n".join(lines)
        else:
            return f"Estado inesperado: {status}"

    def _auto_mutate_code(self) -> dict:
        """
        Mutacion autonoma de codigo: elige un archivo, genera mejora via LLM,
        valida y aplica automaticamente (sin intervencion del usuario).

        Seguridad: SelfModifier valida AST, detecta patrones peligrosos,
        corre tests despues de aplicar, y auto-revierte si fallan.

        Returns:
            dict con: mutated (bool), file, diff_summary, message
        """
        from pathlib import Path as P

        # 1. Elegir archivo candidato
        target_file = self._mutate_pick_target()
        if not target_file:
            return {"mutated": False, "message": "No hay archivos candidatos para mutar"}

        full_path = (P(self.self_modifier.genesis_dir) / target_file).resolve()
        if not full_path.exists():
            return {"mutated": False, "message": f"Archivo no encontrado: {target_file}"}

        # 2. Leer contenido actual
        try:
            current_code = full_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return {"mutated": False, "message": f"Error leyendo {target_file}: {e}"}

        # Limitar a archivos razonables (no genesis.py de 8000+ lineas)
        if len(current_code) > 15000:
            return {"mutated": False, "message": f"{target_file} demasiado grande para mutacion auto"}

        # 3. Pedir al LLM que proponga UNA mejora concreta
        mutate_prompt = (
            f"TAREA: Analizar y mejorar este codigo Python de Genesis.\n"
            f"Archivo: {target_file}\n\n"
            f"CODIGO ACTUAL:\n```python\n{current_code}\n```\n\n"
            f"INSTRUCCIONES:\n"
            f"1. Identifica UNA mejora concreta: bug fix, optimizacion, mejor manejo de errores, "
            f"o micro-funcionalidad nueva que encaje naturalmente\n"
            f"2. Genera el archivo COMPLETO con la mejora aplicada\n"
            f"3. NO cambies la estructura general, solo haz la mejora puntual\n"
            f"4. Manten TODOS los imports, clases y metodos existentes\n"
            f"5. Responde SOLO con el codigo Python mejorado, sin explicaciones\n"
            f"6. NO uses bloques ``` markdown, solo el codigo puro\n"
        )

        new_code = self.brain.quick_think(
            mutate_prompt,
            system=(
                "Eres un ingeniero de software experto. Analiza el codigo y genera "
                "una version mejorada. Responde UNICAMENTE con codigo Python valido. "
                "Sin explicaciones, sin markdown, sin bloques de codigo. Solo Python puro."
            ),
            temperature=0.3,
        )

        if not new_code or len(new_code) < 50 or "[ERROR]" in new_code:
            return {"mutated": False, "message": f"LLM no genero mejora para {target_file}"}

        # 4. Limpiar artefactos del LLM
        new_code = new_code.strip()
        if new_code.startswith("```"):
            code_lines = new_code.split("\n")
            if code_lines[0].startswith("```"):
                code_lines = code_lines[1:]
            if code_lines and code_lines[-1].strip() == "```":
                code_lines = code_lines[:-1]
            new_code = "\n".join(code_lines)

        # 5. Proponer via SelfModifier (valida syntax + seguridad)
        result = self.self_modifier.propose_change(
            filepath=target_file,
            new_content=new_code,
            reason="auto-mutacion-evolve",
            description=f"Mutacion automatica durante ciclo /evolve",
        )

        status = result.get("status")
        if status == "rejected":
            return {"mutated": False, "message": f"Rechazado por seguridad: {result.get('error')}"}
        elif status == "no_change":
            return {"mutated": False, "message": f"{target_file} sin cambios (ya optimo)"}
        elif status != "pending":
            return {"mutated": False, "message": f"Estado inesperado: {status}"}

        # 6. Auto-aplicar (SelfModifier corre tests y auto-revierte si fallan)
        apply_result = self.self_modifier.apply_change()
        apply_status = apply_result.get("status")

        if apply_status == "applied":
            return {
                "mutated": True,
                "file": target_file,
                "additions": result.get("additions", 0),
                "deletions": result.get("deletions", 0),
                "message": apply_result["message"],
            }
        elif apply_status == "reverted":
            return {
                "mutated": False,
                "file": target_file,
                "message": f"Mutacion revertida (tests fallaron): {apply_result['message'][:200]}",
            }
        else:
            return {"mutated": False, "message": f"Error aplicando: {apply_result.get('message', '')}"}

    def _mutate_list_files(self) -> str:
        """Lista archivos que Genesis puede mutar."""
        from pathlib import Path as P
        genesis_dir = P(self.self_modifier.genesis_dir)
        lines = ["  === ARCHIVOS MUTABLES ===", ""]

        # Core modules
        core_dir = genesis_dir / "core"
        if core_dir.exists():
            py_files = sorted(core_dir.glob("*.py"))
            lines.append("  core/")
            for f in py_files:
                rel = f"core/{f.name}"
                is_critical = rel in self.self_modifier.CRITICAL_FILES
                is_immutable = rel in self.self_modifier.IMMUTABLE_FILES
                marker = " [INMUTABLE]" if is_immutable else (" [CRITICO]" if is_critical else "")
                size = f.stat().st_size
                lines.append(f"    {f.name} ({size:,} bytes){marker}")

        # Root files
        root_py = sorted(genesis_dir.glob("*.py"))
        if root_py:
            lines.append("\n  raiz/")
            for f in root_py:
                is_critical = f.name in self.self_modifier.CRITICAL_FILES
                marker = " [CRITICO]" if is_critical else ""
                size = f.stat().st_size
                lines.append(f"    {f.name} ({size:,} bytes){marker}")

        lines.append(f"\n  Total: {len(py_files) + len(root_py)} archivos Python")
        lines.append("  Usa /mutate <archivo> para proponer mutacion")
        return "\n".join(lines)

    def _mutate_pick_target(self) -> str:
        """Elige automaticamente un archivo candidato para mutar."""
        import random
        from pathlib import Path as P
        genesis_dir = P(self.self_modifier.genesis_dir)

        # Candidatos: archivos en core/ que NO sean criticos ni inmutables
        candidates = []
        core_dir = genesis_dir / "core"
        if core_dir.exists():
            for f in core_dir.glob("*.py"):
                rel = f"core/{f.name}"
                if rel in self.self_modifier.IMMUTABLE_FILES:
                    continue
                if rel in self.self_modifier.CRITICAL_FILES:
                    continue  # Saltar criticos en modo auto
                if f.name.startswith("__"):
                    continue
                size = f.stat().st_size
                if size < 500 or size > 14000:
                    continue  # Ni muy chicos ni muy grandes (alineado con _auto_mutate_code)
                candidates.append(rel)

        if not candidates:
            return ""

        # Elegir uno al azar (en futuro: elegir basado en metricas)
        return random.choice(candidates)

    def _cmd_custom_tools(self) -> str:
        """Lista las herramientas custom."""
        lines = ["=== HERRAMIENTAS CUSTOM ==="]
        lines.append(self.tool_creator.list_tools())
        lines.append(f"\n  Directorio: {self.tool_creator.tools_dir}")
        lines.append(f"  Genesis puede crear nuevas herramientas automaticamente")
        lines.append(f"  cuando detecta que necesita una que no tiene.")
        return "\n".join(lines)

    def _cmd_knowledge_graph(self) -> str:
        """Muestra el knowledge graph."""
        lines = ["=== KNOWLEDGE GRAPH ==="]
        lines.append(self.knowledge_graph.status())
        lines.append(f"\n  Top conceptos:")
        lines.append(self.knowledge_graph.format_graph(top_n=15))
        return "\n".join(lines)

    def _cmd_kg_search(self, query: str) -> str:
        """Busca en el knowledge graph."""
        results = self.knowledge_graph.search(query)
        if not results:
            return f"No se encontro '{query}' en el Knowledge Graph."
        lines = [f"=== BUSQUEDA: '{query}' ==="]
        for r in results:
            lines.append(f"\n  {r['concept']} ({r['mentions']} menciones)")
            related = self.knowledge_graph.get_related(r['concept'], depth=1, max_results=5)
            if related:
                rel_str = ", ".join(f"{x['concept']}({x['weight']})" for x in related)
                lines.append(f"    Relacionado: {rel_str}")
            for snippet in r.get('snippets', [])[:2]:
                lines.append(f"    - {snippet}")
        return "\n".join(lines)

    def _cmd_timeout(self, command: str) -> str:
        """Gestiona el timeout del LLM."""
        parts = command.split()
        if len(parts) >= 2:
            try:
                new_timeout = int(parts[1])
                if 10 <= new_timeout <= 600:
                    self.llm_timeout = new_timeout
                    return f"Timeout del LLM: {new_timeout} segundos"
                return "Timeout debe estar entre 10 y 600 segundos."
            except ValueError:
                pass
        return f"Timeout actual: {self.llm_timeout}s\n  Uso: /timeout <segundos>"

    def _cmd_evolve(self, command: str) -> str:
        """
        Inicia la evolucion autonoma — Genesis busca, aprende y evoluciona solo.
        /evolve          — Ciclo completo: prompt + codigo + conocimiento (7 pasos)
        /evolve start    — Iniciar evolucion continua (N ciclos o Xm minutos)
        /evolve stop     — Detener evolucion continua
        /evolve status   — Ver estado de la evolucion autonoma
        /evolve once     — Ejecutar un solo tick de evolucion
        """
        parts = command.split()
        sub = parts[1] if len(parts) > 1 else ""

        if sub == "status":
            # Estado detallado de la evolucion autonoma
            lines = [
                f"  === EVOLUCION AUTONOMA ===",
                f"  Estado: {'ACTIVA' if self.autonomous.active else 'DETENIDA'}",
                f"  Generacion: {self.evolution.get_generation()}",
                f"  Acciones registradas: {len(self.autonomous.actions)}",
                f"  Ciclos completados: {self.autonomous.total_cycles}",
                f"  Acciones ejecutadas: {self.autonomous.total_actions}",
                f"  Fallos consecutivos: {self.autonomous.guard.consecutive_failures}",
                f"",
                f"  Subsistemas conectados:",
                f"    Curiosidad: {len(self.curiosity.get_pending_questions(100))} preguntas pendientes",
                f"    Web: {self.web.total_learned} paginas aprendidas",
                f"    Embeddings: {self.embeddings.store.count()} documentos",
                f"    Fitness: {self.feedback.get_fitness_from_feedback()}/100",
            ]
            return "\n".join(lines)

        elif sub == "stop":
            return self.autonomous.stop()

        elif sub == "once":
            # Un solo tick
            results = self.autonomous.tick()
            if not results:
                return "  Tick de evolucion: sin acciones ejecutadas."
            lines = ["  TICK DE EVOLUCION:"]
            for r in results:
                status = "OK" if r.get("success") else "FAIL"
                lines.append(f"    {r['action']}: {status} — {r.get('result', '')[:80]}")
            return "\n".join(lines)

        elif sub == "start" or sub == "":
            # Ejecutar ciclo completo de evolucion autonoma
            if sub == "start":
                # Parsear argumentos opcionales
                cycles = 0
                duration = 0
                for p in parts[2:]:
                    if p.isdigit():
                        cycles = int(p)
                    elif p.endswith("m") and p[:-1].isdigit():
                        duration = float(p[:-1])
                if cycles == 0 and duration == 0:
                    cycles = 50  # Default: 50 ciclos
                result = self.autonomous.start(max_cycles=cycles, max_duration_minutes=duration)

                # Ejecutar los ticks inmediatamente
                lines = [result, ""]
                total_actions = 0
                tick_count = 0
                max_ticks = min(cycles if cycles > 0 else 10, 10)  # Max 10 ticks inline

                for _ in range(max_ticks):
                    if not self.autonomous.active:
                        break
                    tick_results = self.autonomous.tick()
                    if not tick_results:
                        break
                    tick_count += 1
                    for r in tick_results:
                        total_actions += 1
                        status = "OK" if r.get("success") else "FAIL"
                        lines.append(f"    [{tick_count}] {r['action']}: {status} — {r.get('result', '')[:60]}")

                lines.append(f"\n  Resumen: {tick_count} ticks, {total_actions} acciones ejecutadas")
                lines.append(f"  Usa /evolve status para ver el estado")
                return "\n".join(lines)

            else:
                # /evolve sin argumentos: ciclo completo rapido (JARVIS style)
                lines = [
                    "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "   GENESIS AUTONOMOUS EVOLUTION CYCLE",
                    "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    "",
                ]
                old_gen = self.evolution.get_generation()

                # 1. Investigar curiosidad
                lines.append("  [1/7] Investigando curiosidad...")
                r1 = self.autonomous.tick()
                for r in (r1 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 2. Aprender trending
                lines.append("  [2/7] Aprendiendo temas relevantes...")
                r2 = self.autonomous.tick()
                for r in (r2 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 3. Auto-evaluar
                lines.append("  [3/7] Auto-evaluando rendimiento...")
                r3 = self.autonomous.tick()
                for r in (r3 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 4. Ticks autonomos (curiosidad, web, consolidacion)
                lines.append("  [4/7] Ejecutando acciones autonomas...")
                r4 = self.autonomous.tick()
                for r in (r4 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                # 5. EVOLUCION DIRECTA DEL PROMPT — no depender de tick()
                lines.append("  [5/7] Mutando prompt de personalidad...")
                try:
                    feedback_fitness = self.feedback.get_fitness_from_feedback()
                    metrics_fitness = self.metrics.get_session_fitness()
                    real_fitness = int(feedback_fitness * 0.6 + metrics_fitness * 0.4)
                    feedback_ctx = self.feedback.get_learning_context()

                    evo_result = self.evolution.evolve(
                        self.brain,
                        real_fitness=real_fitness,
                        feedback_context=feedback_ctx,
                    )
                    if evo_result.get("evolved"):
                        lines.append(f"    MUTACION EXITOSA! Gen {old_gen} -> {evo_result['generation']}")
                        lines.append(f"    Fitness: {evo_result.get('previous_fitness')} -> {evo_result.get('fitness')}")
                        lines.append(f"    Candidatos evaluados: {evo_result.get('candidates_evaluated')}")
                        if evo_result.get("weaknesses"):
                            lines.append(f"    Debilidades corregidas: {evo_result['weaknesses'][:3]}")
                    else:
                        lines.append(f"    Sin mutacion: {evo_result.get('reason', 'prompt actual es superior')}")
                except (AttributeError, KeyError, TypeError, ValueError, RuntimeError) as e:
                    lines.append(f"    Error en evolucion: {str(e)[:100]}")

                # 6. MUTACION DE CODIGO FUENTE
                lines.append("  [6/7] Mutando codigo fuente...")
                try:
                    code_result = self._auto_mutate_code()
                    if code_result.get("mutated"):
                        lines.append(f"    CODIGO MUTADO: {code_result['file']}")
                        lines.append(f"    +{code_result.get('additions', 0)} / -{code_result.get('deletions', 0)} lineas")
                        lines.append(f"    Tests: PASARON (cambio aplicado)")
                    else:
                        lines.append(f"    Sin mutacion de codigo: {code_result.get('message', 'N/A')[:100]}")
                except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OSError) as e:
                    lines.append(f"    Error en mutacion de codigo: {str(e)[:100]}")

                # 7. Consolidar
                lines.append("  [7/7] Consolidando conocimiento...")
                r7 = self.autonomous.tick()
                for r in (r7 or []):
                    lines.append(f"    {r['action']}: {r.get('result', '')[:80]}")

                new_gen = self.evolution.get_generation()
                lines.append("")
                lines.append("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                if new_gen > old_gen:
                    lines.append(f"   EVOLUCION COMPLETADA — Gen {old_gen} -> {new_gen}")
                else:
                    lines.append(f"   CICLO COMPLETADO — Gen {new_gen} (estable)")
                lines.append(f"   Web: {self.web.total_learned} paginas | "
                           f"Embeddings: {self.embeddings.store.count()} docs")
                if code_result.get("mutated"):
                    lines.append(f"   CODIGO MUTADO: {code_result['file']} (auto-test passed)")
                lines.append("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                return "\n".join(lines)

        return ("  Uso:\n"
                "    /evolve           — Ciclo completo de evolucion\n"
                "    /evolve start [N] [Xm] — Iniciar evolucion continua\n"
                "    /evolve stop      — Detener evolucion\n"
                "    /evolve status    — Ver estado\n"
                "    /evolve once      — Un solo tick")

    def _cmd_confirm_evolution(self) -> str:
        """Confirma y ejecuta la evolucion pendiente con datos reales."""
        if not self.heartbeat.has_pending_evolution():
            return "No hay evolucion pendiente."

        print(f"  Evolucionando con datos reales... Gen {self.evolution.get_generation()} -> ", end="")

        # Calcular fitness real combinado
        feedback_fitness = self.feedback.get_fitness_from_feedback()
        metrics_fitness = self.metrics.get_session_fitness()
        real_fitness = int(feedback_fitness * 0.6 + metrics_fitness * 0.4)
        feedback_context = self.feedback.get_learning_context()

        result = self.heartbeat.confirm_evolution(
            self.brain,
            real_fitness=real_fitness,
            feedback_context=feedback_context,
        )

        if result.get("evolved"):
            return (f"Gen {self.evolution.get_generation()}\n"
                    f"  Fitness: {result.get('fitness', 'N/A')}\n"
                    f"  Candidatos evaluados: {result.get('candidates_evaluated', 0)}\n"
                    f"  Fortalezas: {result.get('strengths', [])}\n"
                    f"  Debilidades: {result.get('weaknesses', [])}")
        else:
            return f"sin cambios — {result.get('reason', 'desconocido')}"

    def _cmd_generate(self, command: str) -> str:
        """Genera un proyecto multi-archivo con la ultima respuesta del LLM."""
        parts = command.split(maxsplit=1)
        base_dir = ""

        if len(parts) > 1:
            base_dir = parts[1].strip()
        elif self.workspace.is_set():
            base_dir = self.workspace.data.get("path", "")
        else:
            return ("Uso: /generate <ruta_destino>\n"
                    "  O establece un workspace primero con /workspace <ruta>")

        # Obtener la ultima respuesta del LLM
        last_msgs = self.memory.short_term.get_last(2)
        last_response = ""
        for msg in reversed(last_msgs):
            if msg.get("role") == "assistant":
                last_response = msg.get("content", "")
                break

        if not last_response:
            return "No hay respuesta reciente para generar archivos."

        result = self.project_generator.generate(last_response, base_dir)
        return self.project_generator.format_result(result)

    def _cmd_rag_add(self, path: str) -> str:
        """Indexa un archivo o directorio en el RAG."""
        from pathlib import Path as P
        target = P(path).resolve()

        if target.is_file():
            result = self.rag.index_file(str(target))
            return f"RAG: {result['message']}"
        elif target.is_dir():
            result = self.rag.index_directory(str(target))
            msg = f"RAG: {result['files_processed']} archivos indexados, {result['chunks_total']} chunks creados"
            if result['errors']:
                msg += f"\n  Errores: {len(result['errors'])}"
                for err in result['errors'][:5]:
                    msg += f"\n    - {err}"
            return msg
        else:
            return f"Ruta no encontrada: {path}"

    def _cmd_rag_search(self, query: str) -> str:
        """Busca en el indice RAG."""
        results = self.rag.search(query, top_k=5)
        if not results:
            return "RAG: Sin resultados. Indexa archivos con /rag add <ruta>"

        lines = [f"RAG: {len(results)} resultados para '{query}':\n"]
        for i, r in enumerate(results, 1):
            from pathlib import Path as P
            source_name = P(r['source']).name
            score_pct = f"{r['score']:.0%}"
            snippet = r['text'][:150].replace('\n', ' ')
            lines.append(f"  [{i}] {source_name} ({score_pct})")
            lines.append(f"      {snippet}...")
            lines.append("")
        return "\n".join(lines)

    def _cmd_help(self) -> str:
        """Muestra ayuda de comandos."""
        return """
=== COMANDOS DE GENESIS ===

  FEEDBACK Y METRICAS:
  +              — Calificar ultima respuesta como BUENA
  -              — Calificar ultima respuesta como MALA
  /feedback      — Ver estadisticas de feedback y patrones aprendidos
  /metrics       — Ver metricas de rendimiento (sesion + historico)
  /report        — Reporte completo (fitness combinado)
  /errors        — Ver memoria de errores (errores conocidos y soluciones)

  CONTEXTO Y PLANIFICACION:
  /context       — Ver presupuesto de tokens y uso del contexto
  /plan          — Ver plan de trabajo activo
  /plan cancel   — Cancelar plan activo

  SUBSISTEMAS:
  /status        — Estado completo de todos los sistemas
  /memory        — Ver contenido de la memoria
  /evolution     — Ver estado de evolucion y prompt actual
  /debate        — Ver estado del debate interno
  /curiosity     — Ver preguntas pendientes de curiosidad
  /code_memory   — Ver soluciones de codigo guardadas

  WORKSPACE:
  /workspace     — Ver workspace activo
  /workspace <ruta> — Establecer proyecto activo
  /workspace scan — Re-escanear el proyecto
  /workspace clear — Limpiar workspace

  CONFIGURACION:
  /thinking      — Mostrar/ocultar proceso de pensamiento
  /stream        — Activar/desactivar streaming de tokens
  /debug         — Activar/desactivar logs en consola
  /debate toggle — Activar/desactivar debate interno

  EVOLUCION:
  /rollback      — Revertir a la generacion anterior
  /evolucionar   — Confirmar evolucion pendiente
  /rechazar      — Rechazar evolucion pendiente

  HEARTBEAT E INVESTIGACIÓN AUTÓNOMA:
  /heartbeat          — Ver estado del heartbeat
  /heartbeat on       — Activar despertar periodico
  /heartbeat off      — Desactivar heartbeat
  /heartbeat log      — Ver actividad del heartbeat
  /heartbeat findings — Ver hallazgos recientes
  /hallazgos          — Alias de /heartbeat findings
  /investigar <tema>  — Agregar tema a cola de investigación
  /research_loop      — Reporte completo del loop de investigación

  BACKUPS Y SESION:
  /backup        — Crear backup manual de todos los datos
  /backups       — Listar backups disponibles
  /export        — Exportar snapshot de personalidad
  /export <ruta> — Exportar a ruta especifica
  /import <ruta> — Importar snapshot de personalidad
  /logs          — Ver ultimos logs del sistema
  /timeout [seg] — Ver/cambiar timeout del LLM (default 180s)

  TOOLS CUSTOM:
  /tools             — Listar herramientas custom creadas
  /tool_delete <n>   — Eliminar herramienta custom
  /tool_toggle <n>   — Activar/desactivar herramienta

  KNOWLEDGE GRAPH:
  /knowledge         — Ver el grafo de conocimiento (top conceptos)
  /kg                — Atajo para /knowledge
  /kg_search <term>  — Buscar concepto y ver sus conexiones

  PLUGINS:
  /plugins           — Listar plugins instalados
  /plugin reload <n> — Recargar un plugin
  /plugin toggle <n> — Activar/desactivar un plugin

  AUTO-MODIFICACION:
  /mutate              — Mutar codigo fuente (elige archivo automaticamente)
  /mutate <archivo>    — Mutar archivo especifico (ej: core/tools.py)
  /mutate auto         — Genesis elige que mutar
  /mutate list         — Ver archivos mutables
  /self_status   — Ver estado del self-modifier
  /self_history  — Ver historial de auto-modificaciones
  /self_diff     — Ver diff del cambio pendiente
  /apply         — Aplicar cambio propuesto por /mutate
  /reject        — Rechazar cambio pendiente
  /self_rollback — Revertir ultima auto-modificacion

  PROMPT TEMPLATES:
  /templates         — Listar templates disponibles
  /template <nombre> — Activar template especifico
  /template auto     — Volver a seleccion automatica

  PROACTIVO:
  /proactive     — Activar/desactivar sugerencias proactivas

  GENERADOR DE PROYECTOS:
  /generate <ruta>   — Generar proyecto multi-archivo en ruta
                        (requiere que la ultima respuesta tenga archivos)

  RAG (RETRIEVAL AUGMENTED GENERATION):
  /rag               — Ver estado del sistema RAG
  /rag add <ruta>    — Indexar archivo o directorio completo
  /rag search <q>    — Buscar en documentos indexados
  /rag clear         — Limpiar todo el indice RAG

  MULTI-MODEL ROUTER:
  /models            — Listar modelos disponibles con detalles
  /model <nombre>    — Seleccionar modelo manualmente (dolphin/mistral/qwen)
  /model auto        — Volver a seleccion automatica por tarea

  VOZ:
  /voice             — Activar/desactivar voz
  /voice status      — Estado del sistema de voz
  /voice voices      — Listar voces disponibles
  /voice set <id>    — Cambiar voz por ID
  /voice rate <num>  — Cambiar velocidad (default: 175 wpm)

  SISTEMA MULTI-AGENTE:
  /agents            — Listar agentes disponibles con stats
  /agent toggle      — Activar/desactivar sistema multi-agente completo
  /agent toggle <n>  — Activar/desactivar agente especifico
  /delegate <tarea>  — Delegar tarea al agente mas adecuado (auto-detect)
  /delegate <agente> <tarea> — Delegar a agente especifico
  /agent history     — Ver historial de delegaciones

  WORKFLOWS:
  /workflows              — Listar workflows disponibles
  /workflow run <wf> <in> — Ejecutar workflow con input
  /workflow history       — Ver historial de ejecuciones

  SESIONES:
  /sessions                    — Listar todas las sesiones
  /session new <id> [tema]     — Crear nueva sesion
  /session switch <id>         — Cambiar a otra sesion
  /session delete <id>         — Eliminar sesion
  /session rename <id> <name>  — Renombrar sesion

  APRENDIZAJE ADAPTATIVO:
  /learn             — Ver insights de aprendizaje (patrones de feedback)
  /learn rules       — Ver reglas aprendidas
  /learn adjustments — Ver ajustes recomendados para agentes

  ANALYTICS:
  /analytics         — Reporte completo de conversacion
  /analytics gaps    — Ver gaps de conocimiento

  EXPERIMENTOS A/B:
  /experiments                — Listar experimentos de prompt
  /experiment create <n>|<base>|<var1>|<var2> — Crear experimento
  /experiment delete <nombre> — Eliminar experimento

  HEALTH MONITOR:
  /health            — Reporte de salud completo del sistema
  /health check      — Ejecutar todos los checks y mostrar reporte
  /health alerts     — Ver alertas activas
  /health ack <i>    — Reconocer alerta por indice
  /health ack all    — Reconocer todas las alertas

  RATE LIMITER:
  /ratelimit         — Reporte de uso de recursos y buckets
  /rate              — Atajo para /ratelimit
  /ratelimit toggle  — Activar/desactivar rate limiting
  /ratelimit reset   — Resetear todos los buckets

  PLUGIN MARKETPLACE:
  /marketplace               — Ver plugins disponibles
  /market                    — Atajo para /marketplace
  /marketplace search <q>    — Buscar plugins por nombre/tag
  /marketplace install <n>   — Instalar plugin del registry
  /marketplace uninstall <n> — Desinstalar plugin
  /marketplace create <n>    — Crear template de plugin nuevo
  /marketplace rate <n> <1-5> — Calificar plugin

  TASK SCHEDULER:
  /scheduler         — Reporte completo del scheduler
  /sched             — Atajo para /scheduler
  /scheduler tasks   — Listar tareas programadas
  /scheduler toggle  — Activar/desactivar scheduler
  /scheduler pause   — Pausar scheduler
  /scheduler resume  — Reanudar scheduler
  /scheduler run <n> — Ejecutar tarea inmediatamente
  /scheduler toggle <n> — Activar/desactivar tarea especifica
  /scheduler log     — Ver historial de ejecuciones

  CONFIG MANAGER:
  /config            — Listar perfiles guardados
  /config save <n>   — Guardar perfil con nombre
  /config load <n>   — Cargar y aplicar perfil
  /config delete <n> — Eliminar perfil
  /config compare <a> <b> — Comparar dos perfiles
  /config export <n> <ruta> — Exportar perfil a ruta
  /config import <ruta>     — Importar perfil desde ruta

  PERFORMANCE PROFILER:
  /profiler          — Reporte completo de performance
  /perf              — Atajo para /profiler
  /profiler toggle   — Activar/desactivar profiler
  /profiler reset    — Resetear datos del profiler
  /profiler bottlenecks — Ver top 10 subsistemas mas lentos
  /profiler slow     — Ver operaciones que superan threshold

  EMBEDDINGS ENGINE:
  /embeddings            — Reporte del motor de embeddings
  /emb                   — Atajo para /embeddings
  /embeddings add <id> <texto> — Agregar texto al vector store
  /embeddings search <query>   — Busqueda semantica
  /embeddings similar <id>     — Encontrar documentos similares
  /embeddings save             — Guardar vector store a disco
  /embeddings clear            — Limpiar vector store

  JARVIS MODE:
  /briefing              — Diagnostico completo estilo JARVIS (sistemas + hardware + autonomia)
  /brief                 — Atajo para /briefing
  /jarvis                — Atajo para /briefing

  DASHBOARD API:
  /dashboard             — Dashboard completo con metricas de todos los subsistemas
  /dash                  — Atajo para /dashboard
  /dashboard json        — Exportar snapshot como JSON
  /dashboard summary     — Resumen ejecutivo del sistema
  /dashboard categories  — Ver categorias y sus subsistemas
  /dashboard timeline <sub> <metrica> — Serie temporal de una metrica

  AUTONOMOUS MODE:
  /autonomous            — Reporte del modo autonomo
  /auto                  — Atajo para /autonomous
  /autonomous start [ciclos] [Xm] — Iniciar modo autonomo
  /autonomous stop       — Detener modo autonomo
  /autonomous pause      — Pausar modo autonomo
  /autonomous resume     — Reanudar modo autonomo
  /autonomous actions    — Ver acciones registradas
  /autonomous log        — Ver historial de acciones
  /autonomous tick       — Ejecutar un ciclo manual

  EVOLUCION AUTONOMA (Genesis evoluciona solo):
  /evolve                — Ejecutar ciclo completo de evolucion
  /evolve start [N] [Xm] — Iniciar evolucion continua (N ciclos o X minutos)
  /evolve stop           — Detener evolucion continua
  /evolve status         — Ver estado de la evolucion autonoma
  /evolve once           — Ejecutar un solo tick de evolucion

  WEB INTELLIGENCE (acceso a internet):
  /web                   — Reporte del modulo web
  /internet              — Atajo para /web
  /web search <query>    — Buscar en internet (DuckDuckGo)
  /web news <tema>       — Buscar noticias recientes
  /web read <url>        — Leer y extraer contenido de una URL
  /web learn <tema>      — Buscar + leer + indexar automaticamente
  /web recall <query>    — Buscar en conocimiento aprendido
  /web history           — Historial de busquedas
  /web learned           — Ver paginas aprendidas

  MEMORIA SEMANTICA:
  /memory semantic       — Reporte completo de la memoria semantica
                           (entradas indexadas, intents, recientes)

  INFERENCE OPTIMIZER:
  (Automatico) Optimiza cada respuesta reduciendo tokens innecesarios.
  Usa /thinking para ver los detalles de optimizacion en cada respuesta.

  SELF-EVALUATION:
  /evaluate          — Reporte completo de auto-evaluacion
  /eval              — Atajo para /evaluate
  (Automatico) Evalua calidad de cada respuesta y ajusta parametros.

  SKILL MEMORY:
  /skills            — Ver skills (procedimientos) aprendidos
  (Automatico) Detecta y almacena procedimientos de las respuestas.

  CHAIN ENGINE:
  /chain             — Ver estado del motor de cadenas
  /chain toggle      — Activar/desactivar razonamiento en cadena
  (Automatico) Descompone preguntas complejas en sub-preguntas.

  EPISODIC MEMORY:
  /episodes          — Ver episodios recientes y contexto temporal

  META-LEARNER:
  /metalearner       — Ver insights y patrones de meta-aprendizaje

  PERSONALITY:
  /personality       — Ver rasgos de personalidad y su evolucion

  GOAL MANAGER:
  /goals             — Ver metas activas, completadas y progreso

  REFLECTION ENGINE:
  /reflection        — Ver reflexiones, fortalezas y puntos ciegos

  CONTEXT ROUTER:
  /router            — Ver fuentes de contexto y estadisticas de routing

  CAUSAL REASONER:
  /causal            — Ver grafo causal, links y cadenas causa-efecto

  CONCEPT SYNTHESIZER:
  /synthesis         — Ver conceptos, analogias y sintesis cross-domain

  STRATEGIC PLANNER:
  /planner           — Ver plan activo, fases, milestones y progreso

  PATTERN PREDICTOR:
  /predictor         — Ver predicciones Markov, temporales y secuencias

  ANOMALY DETECTOR:
  /anomalies         — Ver streams, anomalias detectadas y alertas

  ADAPTIVE INTERFACE:
  /adaptive          — Ver preferencias aprendidas y directivas de estilo

  HYPOTHESIS ENGINE:
  /hypothesis        — Ver hipotesis activas, confirmadas y refutadas

  EXPLANATION ENGINE:
  /explanations      — Ver banco de explicaciones, calidad y uso

  DIALOGUE STRATEGIST:
  /dialogue          — Ver estrategias de dialogo y efectividad

  COGNITIVE MONITOR:
  /cognitive         — Ver carga cognitiva, metricas y sugerencias

  ABSTRACTION ENGINE:
  /abstraction       — Ver patrones abstractos, instancias y confianza

  LEARNING OPTIMIZER:
  /learning          — Ver dominios, mastery, gaps y estrategias

  UNIFIED MIND:
  /mind              — Ver estado de consciencia, mood, energy, focus

  DREAM ENGINE:
  /dream             — Ver fragmentos consolidados, memorias fuertes

  SELF-NARRATIVE:
  /narrative         — Ver diario, hitos, identidad y rasgos

  EMOTION READER:
  /emotions          — Ver emociones detectadas, tendencia, historial

  EMPATHY ENGINE:
  /empathy           — Ver estrategias de empatia y efectividad

  CONFLICT RESOLVER:
  /conflict          — Ver conflictos, resoluciones y patrones

  STORY GENERATOR:
  /stories           — Ver historias creadas, personajes y progreso

  CODE ARCHITECT:
  /architect         — Ver diseños de sistemas, componentes y decisiones

  IDEA BRAINSTORMER:
  /brainstorm        — Ver ideas, sesiones y scores de brainstorming

  IMAGE ANALYZER:
  /images            — Ver imagenes analizadas, cache y metadatos

  DIAGRAM GENERATOR:
  /diagrams          — Ver diagramas generados, tipos y Mermaid

  VOICE PERSONALITY:
  /voice             — Ver estilo vocal, adaptaciones y directivas

  PEER DEBATE:
  /peer_debate       — Ver debates entre perspectivas y argumentos

  CONSENSUS ENGINE:
  /consensus         — Ver rondas de consenso Delphi y resultados

  KNOWLEDGE SHARING:
  /knowledge         — Ver paquetes de conocimiento compartidos

  /last_debate   — Ver el ultimo debate interno completo
  /help          — Mostrar esta ayuda
  /exit          — Salir de Genesis (guarda sesion automaticamente)

=== HERRAMIENTAS (pedilas en lenguaje natural) ===

  Genesis puede:
  - Buscar en internet y traducir resultados
  - Investigacion profunda (multiples busquedas + lectura de paginas)
  - Leer y crear archivos en tu PC (con validacion de seguridad)
  - Ejecutar codigo Python (con sandbox de seguridad)
  - Ejecutar comandos del sistema (shell/cmd)
  - Analizar archivos sospechosos (malware/phishing)
  - Leer paginas web y traducirlas
  - Ver info del sistema (CPU, RAM, GPU, disco, red, procesos)
  - Leer y editar su propio codigo (auto-modificacion)
"""
