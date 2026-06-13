import os
_GX_HOME = os.path.expanduser("~").replace("\\", "/")  # N7: portabilidad multi-usuario
"""
Genesis Processing Mixin.

Contiene la lógica principal de procesamiento de input del usuario:
- process_input: pipeline completo de procesamiento
- _post_process: aprendizaje y evolución post-respuesta
- Detección de emociones y hechos
"""
import re
import subprocess
import sys
import time
from core.timeout import TimeoutExecutor


class GenesisProcessingMixin:
    """Mixin con la lógica de procesamiento de input y respuesta."""

    # Herramientas que MUTAN el sistema o EJECUTAN código. Cuando el contexto
    # de esta interacción fue "contaminado" por contenido externo no confiable
    # (página web leída, documento subido, conocimiento web), estas tools NO se
    # auto-ejecutan: una página/documento malicioso podría inducir al LLM a
    # emitir [TOOL:python]/[TOOL:shell] y lograr ejecución de código local
    # (cadena prompt-injection → RCE). Las tools de solo-lectura (leer, listar,
    # buscar, web, sistema, gpu...) siguen permitidas.
    DANGEROUS_TOOLS = frozenset({
        "python", "shell", "editar_codigo", "escribir", "insertar", "editar",
    })

    def _guard_tool(self, tool_name: str):
        """Devuelve un mensaje de bloqueo si la tool no debe ejecutarse en
        contexto contaminado, o None si está permitida.

        Ver DANGEROUS_TOOLS y self._context_tainted.
        """
        if getattr(self, "_context_tainted", False) and tool_name in self.DANGEROUS_TOOLS:
            self.log.error(
                f"[Seguridad] Tool '{tool_name}' bloqueada: el contexto incluyó "
                f"contenido externo no confiable (web/documento)."
            )
            try:
                if hasattr(self, "action_tracker"):
                    self.action_tracker.log_tool(
                        tool_name, "", "[BLOQUEADA: contexto contaminado]", success=False
                    )
            except (AttributeError, TypeError):
                pass
            return (
                f"[🛡️ BLOQUEADA] No ejecuté '{tool_name}' porque esta respuesta se "
                f"basó en contenido externo (una web o un documento), y ejecutar "
                f"código/comandos derivados de fuentes no confiables es un riesgo de "
                f"seguridad (prompt-injection). Si esta acción la pediste vos "
                f"directamente, repetí el pedido sin que haya contenido web/documento "
                f"de por medio."
            )
        return None

    # Marcadores de resultados que NO se deben reformular (output exacto):
    # codigo, ejecuciones, listados de archivos, builds, bloqueos de seguridad.
    _NO_REPHRASE = (
        "```", "Salida:", "[OK]", "[ERROR]", "Traceback", "📁", "🛠️",
        "INMUTABLE", "🛡️", "Backup", "self.", "def ", "import ",
        "Archivo editado", "Codigo de salida", "[[PLAY:", "🎵", "[[STOP]]", "⏹️",
        "[[PAUSE]]", "[[RESUME]]", "⏸️", "▶️",
        # Rutinas JARVIS: no reformular (mantener narración + marcadores)
        "[[ULTRON]]", "[[VOICE:", "🦾", "🌅", "🔧", "⚛️", "🛡️", "🎉", "🧹",
        "👁️", "🤖", "🌙", "💁",
        # Operaciones de archivos: respuesta exacta, sin pasar por el LLM lento
        "🗑️", "📦", "📋", "✏️", "Movido:", "Copiado:", "Renombrado:",
        "Enviado a papelera", "en la papelera", "Encontré varios", "Encontré ",
        "No encontré", "¿Cuál", "Pasame la ruta", "Para editar decime",
        # Desarrollo de código (BuilderEngine en background)
        "✅", "🔧 Arranqué", "Todavía construyendo", "No tengo ningún desarrollo",
        "quedó FUNCIONANDO", "no quedó andando",
        # Email
        "📧", "¿Confirmás el envío", "App Password", "cancelé el envío",
        "A qué dirección", "Qué mensaje le mando",
        "📬", "📭", "Últimos", "correos de", "leer correos",
        # Control del sistema (volumen/energía/brillo/bloqueo)
        "🔊", "🔉", "🔇", "🔈", "🔒", "😴", "🔌", "🔄", "💡", "✋", "👋",
        "¿Seguro que apago", "¿Seguro que reinicio",
        "🖨️", "Qué documento imprimo",
        "🖥️", "Qué abro en esa pantalla",
        "📶", "🔵", "Qué unidad USB", "Qué abro",
        "📺", "Qué te casteo", "🎬", "🎮", "🎙️", "🗣️",
        # Clima/pronóstico: respuesta ya natural con datos — no reformular
        "☀️", "🌤️", "⛅", "☁️", "🌧️", "🌦️", "⛈️", "🌩️", "❄️", "🌫️", "🌡️", "🌬️",
    )

    def _maybe_spontaneous(self, user_input: str, result: str) -> str:
        """Reformula un resultado factual de forma natural/espontánea con el LLM.

        Conserva los datos (no inventa ni altera números). Solo aplica a
        resultados conversacionales cortos; deja intactos código/builds/output
        exacto. Si algo falla, devuelve el resultado original (nunca rompe).
        """
        if not getattr(self, "spontaneous", True):
            return result
        if not result or len(result) > 600:
            return result
        if any(m in result for m in self._NO_REPHRASE):
            return result
        try:
            sys_p = (
                "Sos Genesis hablando en argentino informal (vos), relajado y "
                "espontáneo, como un amigo. Te paso un DATO REAL ya obtenido. "
                "Reformulalo en 1-2 frases naturales y frescas, distinto a un "
                "template. REGLA: no cambies ni inventes números, nombres ni "
                "datos — solo la forma de decirlo. Sin viñetas ni formato de reporte."
            )
            usr = f"El usuario preguntó: \"{user_input}\"\nDato real:\n{result}\n\nDecilo natural:"
            out = self.brain.think(sys_p, [{"role": "user", "content": usr}],
                                   temperature=0.8, max_tokens=200)
            out = (out or "").strip()
            # Si el LLM falla o devuelve algo vacío/raro, usar el original
            if not out or "[ERROR]" in out or len(out) < 5:
                return result
            return out
        except Exception as e:
            self.log.debug(f"Spontaneous rephrase skip: {e}")
            return result

    def _is_coding_request(self, text: str) -> bool:
        """Detecta si el usuario pide programar o crear codigo."""
        text_lower = text.lower()
        coding_keywords = [
            "programa", "codigo", "script", "funcion", "clase",
            "crea un", "escribe un", "haz un", "genera un",
            "creame", "haceme", "armame", "desarrolla",
            "python", "javascript", "html", "css", "java",
            "typescript", "react", "flask", "django", "fastapi",
            "algoritmo", "calculadora", "bot", "scraper",
            "api", "servidor", "web", "app", "aplicacion",
            "automatiza", "ejecuta", "compila", "debuggea",
            "instala", "configura", "despliega", "deploy",
            "code", "program", "function", "class", "create",
            "archivo .py", "archivo .js", "archivo .html",
            "base de datos", "database", "sql", "crud",
            "juego", "game", "gui", "interfaz",
        ]
        return any(kw in text_lower for kw in coding_keywords)

    def _extract_code_from_response(self, response: str) -> str:
        """Extrae bloques de codigo de la respuesta del LLM."""
        # Buscar bloques ```python ... ``` o ```...```
        blocks = re.findall(
            r'```(?:python|py)?\s*\n(.*?)```',
            response, re.DOTALL
        )
        if blocks:
            return blocks[-1].strip()

        # Buscar codigo en [TOOL:python]
        match = re.search(r'\[TOOL:python\]\s*(.+)', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def process_input(self, user_input: str, stream_callback=None) -> str:
        """
        Procesa el input del usuario y genera una respuesta.

        Args:
            user_input: Texto del usuario
            stream_callback: Funcion callback(token) para streaming en tiempo real.
                             Si se proporciona, los tokens se envian al callback
                             a medida que el LLM los genera.
        """
        _start_time = time.time()
        self._current_input = user_input  # Para Knowledge Graph context en build_system_prompt
        # Flag de seguridad: se activa si esta interacción inyecta contenido
        # externo no confiable (web/documento) al prompt. Bloquea tools de
        # sistema downstream. Se resetea en cada interacción. Ver _guard_tool.
        self._context_tainted = False

        # JARVIS: Auto-briefing en la primera interaccion de la sesion
        _briefing_prefix = ""
        if self._first_interaction:
            self._first_interaction = False
            try:
                _briefing_prefix = self.startup_briefing() + "\n\n"
            except Exception as e:
                self.log.error(f"Startup briefing failed: {e}")
                _briefing_prefix = ""

        # Agregar a memoria de corto plazo
        self.memory.short_term.add("user", user_input)

        # Comprimir conversacion si la memoria esta llena
        st = self.memory.short_term
        if self.summarizer.should_summarize(len(st.messages), st.max_messages):
            if self.show_thinking:
                print(f"  [Summarizer: comprimiendo {len(st.messages)} mensajes...]")
            self.summarizer.summarize(self.brain, st.messages)
            # Eliminar mensajes comprimidos (mantener solo los recientes)
            keep = self.summarizer.keep_recent
            if len(st.messages) > keep:
                st.messages = st.messages[-keep:]
            if self.show_thinking:
                print(f"  [Summarizer: mensajes reducidos a {len(st.messages)}]")

        # Clasificar intencion del usuario (Smart Router)
        intent = self.router.classify(user_input)
        self.log.debug(f"Intent: {intent} | Input: {user_input[:80]}")
        if self.show_thinking:
            print(f"  [Router: intent={intent}]")

        # === AUTO-TOOL: Detectar, ejecutar, y dar resultado DIRECTO ===
        auto_tool_result = self._auto_detect_tool(user_input)
        self.log.debug(f"Auto-detect: input='{user_input[:50]}' result={'YES' if auto_tool_result else 'NONE'}")
        if auto_tool_result:
            # Detectar si necesita procesamiento del LLM (solo research/web)
            needs_llm = any(marker in auto_tool_result for marker in [
                "[RESULTADOS DE BUSQUEDA",
                "[RESULTADO DE INVESTIGACION",
                "[CONTEXTO WEB",
            ])

            if needs_llm:
                # Solo research/web: inyectar como contexto para que el LLM resuma.
                # CONTENIDO EXTERNO NO CONFIABLE → marcar contexto como contaminado
                # para bloquear tools de sistema downstream (anti prompt-injection).
                self._context_tainted = True
                self.memory.short_term.add("assistant", "[Sistema: datos obtenidos]")
                self.memory.short_term.add("user",
                    f"[DATOS REALES OBTENIDOS]:\n{auto_tool_result}\n\n"
                    f"INSTRUCCIONES: Responde al usuario USANDO EXCLUSIVAMENTE estos datos reales. "
                    f"NO inventes datos adicionales. NO digas 'no tengo acceso'. "
                    f"Presenta la informacion de forma clara y organizada."
                )
                # Continua al LLM para que resuma los resultados web
            else:
                # ESPONTANEIDAD: en vez de devolver el template crudo, paso el
                # DATO REAL al LLM para que lo formule natural y distinto cada vez
                # (sin alterar numeros). Solo para resultados conversacionales
                # cortos — NO para codigo/builds/listados/output exacto.
                spk = self._maybe_spontaneous(user_input, auto_tool_result)
                self.memory.short_term.add("assistant", spk)
                return spk

        # === COORDINADOR: Genesis enruta al agente especialista (auto-delegación) ===
        # Si ningún tool directo aplicó y hay un especialista claro (alta confianza),
        # Genesis delega solo al agente correcto. Si no, sigue el flujo normal.
        if getattr(self, "_coordinator_enabled", True):
            try:
                routed = self.agent_system.route(user_input)
            except Exception:
                routed = None
            if routed:
                _ctx = ""
                try:
                    if self.workspace.is_set():
                        _ctx = self.workspace.read_relevant_context(user_input) or ""
                except Exception:
                    pass
                try:
                    _res = self.agent_system.delegate(
                        user_input, context=_ctx, agent_name=routed["name"])
                    _resp = (_res.get("response") or "").strip()
                except Exception as _ce:
                    self.log.debug(f"Coordinador falló: {_ce}")
                    _resp = ""
                if _resp and not _resp.startswith("[Error"):
                    self.log.debug(
                        f"Coordinador → agente {routed['name']} (score {routed['score']})")
                    _out = "🧭 " + _resp
                    self.memory.short_term.add("assistant", _out)
                    return _out

        # === DETECCION DE APRENDIZAJE AUTOMATICO ===
        # Si el usuario pide aprender/especializarse, Genesis actua en vez de solo hablar
        learn_context = self._detect_and_learn(user_input)

        # Construir prompt del sistema optimizado para esta intencion
        system_prompt = self.build_system_prompt(intent=intent)

        # Prompt Template: inyectar instrucciones especializadas y ajustar temperatura
        template_extra, template_temp, template_name = self.templates.get_system_extra(user_input)
        if template_extra:
            system_prompt += f"\n\n{template_extra}"
            if self.show_thinking:
                print(f"  [Template: {template_name} (temp={template_temp})]")

        # Si es una tarea de codigo, inyectar contexto relevante + prompt de calidad
        if intent == "code" or self._is_coding_request(user_input):
            extra_context = ""
            # Buscar soluciones anteriores en Code Memory
            code_context = self.code_memory.get_context_for_prompt(user_input)
            if code_context:
                extra_context += f"\n\n{code_context}"

            # Leer archivos relevantes del workspace
            if self.workspace.is_set():
                ws_code = self.workspace.read_relevant_context(user_input)
                if ws_code:
                    extra_context += f"\n\n{ws_code}"

            # Code Quality Prompt — fuerza mejores prácticas
            extra_context += (
                "\n\n[DIRECTIVAS DE CÓDIGO]:"
                "\n- Genera código COMPLETO y funcional. Sin placeholders ni '# TODO'."
                "\n- Incluye imports necesarios al inicio."
                "\n- Agrega manejo de errores (try/except) en operaciones I/O."
                "\n- Usa nombres de variables descriptivos en español o inglés (consistente)."
                "\n- Si creas archivos, usa rutas absolutas (" + _GX_HOME + "/...)."
                "\n- Si el código necesita un paquete externo, úsalo — se instalará automáticamente."
                "\n- EJECUTA el código con [TOOL:python] después de generarlo."
            )

            if extra_context:
                system_prompt += extra_context

        # RAG: inyectar contexto de documentos indexados.
        # Los documentos son contenido externo → contaminan el contexto.
        rag_context = self.rag.get_context(user_input, max_chars=1500, top_k=3)
        if rag_context:
            system_prompt += f"\n\n{rag_context}"
            self._context_tainted = True
            if self.show_thinking:
                print(f"  [RAG: contexto inyectado ({len(rag_context)} chars)]")

        # Inyectar conocimiento aprendido de la web si hay (contenido externo).
        if learn_context:
            system_prompt += f"\n\n{learn_context}"
            self._context_tainted = True

        # Semantic Memory: inyectar conversaciones pasadas relevantes
        sem_context = self.semantic_memory.get_context_for_prompt(user_input, max_chars=1000)
        if sem_context:
            system_prompt += f"\n\n{sem_context}"
            if self.show_thinking:
                print(f"  [SemanticMemory: contexto inyectado]")

        # Skill Memory: inyectar procedimientos aprendidos
        skill_context = self.skill_memory.get_context_for_prompt(user_input, max_chars=800)
        if skill_context:
            system_prompt += f"\n\n{skill_context}"
            if self.show_thinking:
                print(f"  [SkillMemory: skills inyectados]")

        # Episodic Memory: inyectar contexto temporal
        ep_context = self.episodic_memory.get_context_for_prompt(user_input, max_chars=600)
        if ep_context:
            system_prompt += f"\n\n{ep_context}"
            if self.show_thinking:
                print(f"  [EpisodicMemory: contexto temporal inyectado]")

        # Personality: inyectar hints de personalidad
        personality_hints = self.personality.get_prompt_hints()
        if personality_hints:
            system_prompt += f"\n\n[PERSONALIDAD] {personality_hints}"

        # Goal Manager: inyectar metas activas
        goals_context = self.goal_manager.get_context_for_prompt(max_chars=400)
        if goals_context:
            system_prompt += f"\n\n{goals_context}"

        # Reflection Engine: inyectar auto-reflexión reciente
        reflection_context = self.reflection.get_context_for_prompt(max_chars=400)
        if reflection_context:
            system_prompt += f"\n\n{reflection_context}"

        # Causal Reasoner: inyectar razonamiento causal si hay pregunta causal
        causal_context = self.causal_reasoner.get_context_for_prompt(user_input, max_chars=400)
        if causal_context:
            system_prompt += f"\n\n{causal_context}"
            if self.show_thinking:
                print(f"  [CausalReasoner: contexto causal inyectado]")

        # Concept Synthesizer: inyectar síntesis relevantes
        synth_context = self.concept_synth.get_context_for_prompt(user_input, max_chars=400)
        if synth_context:
            system_prompt += f"\n\n{synth_context}"
            if self.show_thinking:
                print(f"  [ConceptSynthesizer: síntesis inyectada]")

        # Strategic Planner: inyectar plan activo
        plan_context = self.strategic_planner.get_context_for_prompt(user_input, max_chars=400)
        if plan_context:
            system_prompt += f"\n\n{plan_context}"
            if self.show_thinking:
                print(f"  [StrategicPlanner: plan activo inyectado]")

        # Anomaly Detector: inyectar anomalías críticas
        anomaly_context = self.anomaly_detector.get_context_for_prompt(max_chars=300)
        if anomaly_context:
            system_prompt += f"\n\n{anomaly_context}"

        # Adaptive Interface: observar input y generar directivas de estilo
        self.adaptive_iface.observe_input(user_input)
        style_directives = self.adaptive_iface.get_context_for_prompt(max_chars=200)
        if style_directives:
            system_prompt += f"\n\n{style_directives}"

        # Hypothesis Engine: contexto de hipótesis activas
        hyp_context = self.hypothesis_engine.get_context_for_prompt(max_chars=200)
        if hyp_context:
            system_prompt += f"\n\n{hyp_context}"

        # Explanation Engine: detectar necesidad de explicación
        exp_context = self.explanation_engine.get_context_for_prompt(user_input, max_chars=200)
        if exp_context:
            system_prompt += f"\n\n{exp_context}"

        # Dialogue Strategist: directiva de estrategia
        dial_context = self.dialogue_strategist.get_context_for_prompt(user_input, max_chars=200)
        if dial_context:
            system_prompt += f"\n\n{dial_context}"

        # Cognitive Monitor: contexto de carga cognitiva
        cog_context = self.cognitive_monitor.get_context_for_prompt(max_chars=200)
        if cog_context:
            system_prompt += f"\n\n{cog_context}"

        # Abstraction Engine: contexto de patrones abstractos
        abs_context = self.abstraction_engine.get_context_for_prompt(max_chars=200)
        if abs_context:
            system_prompt += f"\n\n{abs_context}"

        # Learning Optimizer: contexto de aprendizaje
        learn_context = self.learning_optimizer.get_context_for_prompt(domain=intent, max_chars=200)
        if learn_context:
            system_prompt += f"\n\n{learn_context}"

        # Unified Mind: estado de consciencia
        mind_context = self.unified_mind.get_context_for_prompt(max_chars=200)
        if mind_context:
            system_prompt += f"\n\n{mind_context}"

        # Dream Engine: memorias consolidadas
        dream_context = self.dream_engine.get_context_for_prompt(max_chars=200)
        if dream_context:
            system_prompt += f"\n\n{dream_context}"

        # Self-Narrative: identidad
        narrative_context = self.self_narrative.get_context_for_prompt(max_chars=200)
        if narrative_context:
            system_prompt += f"\n\n{narrative_context}"

        # Emotion Reader: detectar emociones y generar contexto
        emotion_context = self.emotion_reader.get_context_for_prompt(user_input, max_chars=200)
        if emotion_context:
            system_prompt += f"\n\n{emotion_context}"

        # Empathy Engine: modificar tono por emoción detectada
        emotion_data = self.emotion_reader.read(user_input)
        empathy_context = self.empathy_engine.get_context_for_prompt(
            emotion=emotion_data["primary"],
            intensity=emotion_data["intensity"],
            max_chars=200,
        )
        if empathy_context:
            system_prompt += f"\n\n{empathy_context}"

        # Conflict Resolver: detectar y manejar conflictos
        conflict_context = self.conflict_resolver.get_context_for_prompt(user_input, max_chars=200)
        if conflict_context:
            system_prompt += f"\n\n{conflict_context}"
            if self.show_thinking:
                print(f"  [ConflictResolver: conflicto detectado]")

        # Story Generator: contexto narrativo si hay historia activa
        story_context = self.story_generator.get_context_for_prompt(user_input, max_chars=300)
        if story_context:
            system_prompt += f"\n\n{story_context}"

        # Code Architect: contexto arquitectónico si hay diseño activo
        architect_context = self.code_architect.get_context_for_prompt(user_input, max_chars=300)
        if architect_context:
            system_prompt += f"\n\n{architect_context}"

        # Idea Brainstormer: mejores ideas como contexto
        brainstorm_context = self.idea_brainstormer.get_context_for_prompt(user_input, max_chars=300)
        if brainstorm_context:
            system_prompt += f"\n\n{brainstorm_context}"

        # Image Analyzer: contexto de imágenes analizadas
        image_context = self.image_analyzer.get_context_for_prompt(user_input, max_chars=200)
        if image_context:
            system_prompt += f"\n\n{image_context}"

        # Diagram Generator: contexto de diagramas
        diagram_context = self.diagram_generator.get_context_for_prompt(user_input, max_chars=200)
        if diagram_context:
            system_prompt += f"\n\n{diagram_context}"

        # Voice Personality: directivas vocales basadas en emoción detectada
        _voice_emotion = emotion_data.get("primary", "neutral") if emotion_data else "neutral"
        voice_context = self.voice_personality.get_context_for_prompt(
            emotion=_voice_emotion,
            max_chars=200,
        )
        if voice_context:
            system_prompt += f"\n\n{voice_context}"

        # Peer Debate: contexto de debates activos
        peer_debate_ctx = self.peer_debate.get_context_for_prompt(max_chars=200)
        if peer_debate_ctx:
            system_prompt += f"\n\n{peer_debate_ctx}"

        # Consensus Engine: contexto de consenso
        consensus_ctx = self.consensus_engine.get_context_for_prompt(max_chars=200)
        if consensus_ctx:
            system_prompt += f"\n\n{consensus_ctx}"

        # Knowledge Sharing: contexto de conocimiento compartido
        knowledge_ctx = self.knowledge_sharing.get_context_for_prompt(user_input, max_chars=200)
        if knowledge_ctx:
            system_prompt += f"\n\n{knowledge_ctx}"

        # PaperReader: contexto
        paper_reader_ctx = self.paper_reader.get_context_for_prompt(user_input, max_chars=200)
        if paper_reader_ctx:
            system_prompt += f"\n\n{paper_reader_ctx}" 

        # ExperimentRunner: contexto
        experiment_runner_ctx = self.experiment_runner.get_context_for_prompt(max_chars=200)
        if experiment_runner_ctx:
            system_prompt += f"\n\n{experiment_runner_ctx}" 

        # InsightSynthesizer: contexto
        insight_synthesizer_ctx = self.insight_synthesizer.get_context_for_prompt(user_input, max_chars=200)
        if insight_synthesizer_ctx:
            system_prompt += f"\n\n{insight_synthesizer_ctx}" 

        # SafeCodeEvolver: contexto
        safe_code_evolver_ctx = self.safe_code_evolver.get_context_for_prompt(max_chars=200)
        if safe_code_evolver_ctx:
            system_prompt += f"\n\n{safe_code_evolver_ctx}" 

        # ArchitectureEvolver: contexto
        architecture_evolver_ctx = self.architecture_evolver.get_context_for_prompt(max_chars=200)
        if architecture_evolver_ctx:
            system_prompt += f"\n\n{architecture_evolver_ctx}" 

        # ModuleGenerator: contexto
        module_generator_ctx = self.module_generator.get_context_for_prompt(max_chars=200)
        if module_generator_ctx:
            system_prompt += f"\n\n{module_generator_ctx}" 

        # TemporalReasoner: contexto
        temporal_reasoner_ctx = self.temporal_reasoner.get_context_for_prompt(user_input, max_chars=200)
        if temporal_reasoner_ctx:
            system_prompt += f"\n\n{temporal_reasoner_ctx}" 

        # ScheduleOptimizer: contexto
        schedule_optimizer_ctx = self.schedule_optimizer.get_context_for_prompt(max_chars=200)
        if schedule_optimizer_ctx:
            system_prompt += f"\n\n{schedule_optimizer_ctx}" 

        # TrendForecaster: contexto
        trend_forecaster_ctx = self.trend_forecaster.get_context_for_prompt(max_chars=200)
        if trend_forecaster_ctx:
            system_prompt += f"\n\n{trend_forecaster_ctx}" 

        # EthicalReasoner: contexto
        ethical_reasoner_ctx = self.ethical_reasoner.get_context_for_prompt(user_input, max_chars=200)
        if ethical_reasoner_ctx:
            system_prompt += f"\n\n{ethical_reasoner_ctx}" 

        # BiasDetector: contexto
        bias_detector_ctx = self.bias_detector.get_context_for_prompt(max_chars=200)
        if bias_detector_ctx:
            system_prompt += f"\n\n{bias_detector_ctx}" 

        # TransparencyEngine: contexto
        transparency_engine_ctx = self.transparency_engine.get_context_for_prompt(max_chars=200)
        if transparency_engine_ctx:
            system_prompt += f"\n\n{transparency_engine_ctx}" 

        # DomainExpert: contexto
        domain_expert_ctx = self.domain_expert.get_context_for_prompt(user_input, max_chars=200)
        if domain_expert_ctx:
            system_prompt += f"\n\n{domain_expert_ctx}" 

        # TutorEngine: contexto
        tutor_engine_ctx = self.tutor_engine.get_context_for_prompt(user_input, max_chars=200)
        if tutor_engine_ctx:
            system_prompt += f"\n\n{tutor_engine_ctx}" 

        # FactChecker: contexto
        fact_checker_ctx = self.fact_checker.get_context_for_prompt(user_input, max_chars=200)
        if fact_checker_ctx:
            system_prompt += f"\n\n{fact_checker_ctx}" 

        # TaskDistributor: contexto
        task_distributor_ctx = self.task_distributor.get_context_for_prompt(max_chars=200)
        if task_distributor_ctx:
            system_prompt += f"\n\n{task_distributor_ctx}" 

        # ResultAggregator: contexto
        result_aggregator_ctx = self.result_aggregator.get_context_for_prompt(max_chars=200)
        if result_aggregator_ctx:
            system_prompt += f"\n\n{result_aggregator_ctx}" 

        # NetworkManager: contexto
        network_manager_ctx = self.network_manager.get_context_for_prompt(max_chars=200)
        if network_manager_ctx:
            system_prompt += f"\n\n{network_manager_ctx}" 

        # AutonomousResearchLoop: contexto
        autonomous_research_loop_ctx = self.autonomous_research_loop.get_context_for_prompt(max_chars=200)
        if autonomous_research_loop_ctx:
            system_prompt += f"\n\n{autonomous_research_loop_ctx}" 

        # SelfArchitect: contexto
        self_architect_ctx = self.self_architect.get_context_for_prompt(max_chars=200)
        if self_architect_ctx:
            system_prompt += f"\n\n{self_architect_ctx}" 

        # ConsciousnessIntegrator: contexto
        consciousness_integrator_ctx = self.consciousness_integrator.get_context_for_prompt(max_chars=200)
        if consciousness_integrator_ctx:
            system_prompt += f"\n\n{consciousness_integrator_ctx}" 

        # Fase 0: Planificacion de tareas complejas
        if ((intent == "code" or self._is_coding_request(user_input))
                and self.task_planner.needs_planning(user_input)
                and not self.task_planner.is_active()):
            ws_ctx = ""
            if self.workspace.is_set():
                ws_ctx = self.workspace.get_prompt_context()

            plan = self.task_planner.create_plan(self.brain, user_input, ws_ctx)
            if plan and plan.get("steps"):
                n_steps = len(plan["steps"])
                if self.show_thinking:
                    print(f"  [TaskPlanner: {n_steps} pasos planificados]")
                # El plan se inyecta automaticamente via build_system_prompt()
                system_prompt = self.build_system_prompt(intent=intent)

        # Obtener mensajes de conversacion (ajustados al presupuesto)
        raw_messages = self.memory.get_conversation_messages()
        messages = self.context_manager.fit_messages(
            raw_messages,
            summary=self.summarizer.get_summary(),
        )

        # === INFERENCE OPTIMIZER ===
        opt_result = self.optimizer.optimize(
            system_prompt, messages, user_input, default_max_tokens=1024,
        )
        system_prompt = opt_result["system_prompt"]
        messages = opt_result["messages"]
        _opt_max_tokens = opt_result["max_tokens"]
        if self.show_thinking:
            print(f"  [Optimizer: {opt_result['chars_saved']} chars ahorrados, "
                  f"max_tokens={_opt_max_tokens}, cache={'HIT' if opt_result['cache_hit'] else 'MISS'}]")

        # Fase 1: Debate interno (si esta habilitado)
        debate_insights = ""
        if self.debate.enabled:
            context_summary = ""
            last_msgs = self.memory.short_term.get_last(3)
            if last_msgs:
                context_summary = " | ".join(
                    f"{m['role']}: {m['content'][:100]}" for m in last_msgs
                )

            debate_insights = self.debate.debate(
                self.brain, user_input, context=context_summary
            )

            if self.show_thinking and debate_insights:
                print(f"\n  [Debate interno completado — "
                      f"{len(self.debate.active_agents)} agentes consultados]")

        # LOOP CERRADO adaptive_prompts: A/B testing real de un directiva de
        # estilo. Antes el motor epsilon-greedy existía pero ningún experimento
        # se creaba ni evaluaba (loop muerto). Ahora: se crea un experimento
        # universal, se elige una variante por epsilon-greedy y se inyecta al
        # prompt; el score del self_evaluator en _post_process es la recompensa.
        self._adaptive_idx = None
        try:
            _exp = "estilo_respuesta"
            if _exp not in self.adaptive_prompts.experiments:
                self.adaptive_prompts.create_experiment(
                    name=_exp,
                    base_prompt="",
                    variants=[
                        "",  # base (sin directiva)
                        "Sé conciso y directo: ve al grano sin preámbulos.",
                        "Estructura la respuesta con viñetas o pasos cuando ayude a la claridad.",
                        "Incluye un ejemplo concreto cuando aclare el punto.",
                    ],
                    min_samples=8,
                )
            _variant = self.adaptive_prompts.get_variant(_exp)
            _sel = self.adaptive_prompts.active_selections.get(_exp)
            if _sel is not None:
                self._adaptive_idx = _sel[0]
            if _variant:
                system_prompt += f"\n\n[ESTILO] {_variant}"
        except Exception as e:
            self.log.debug(f"AdaptivePrompts skip: {e}")

        # Fase 2: Generar respuesta final (con timeout protection)
        # Streaming: solo en la respuesta principal, no en tool loops
        use_stream = self.streaming and stream_callback is not None
        # Temperatura: template > auto-tuner > default 0.7
        if template_extra:
            temp = template_temp
        else:
            tuned = self.evaluator.get_tuned_config(intent)
            temp = tuned.get("temperature", 0.7)
            # LOOP CERRADO meta_learner: si acumuló suficientes datos de outcomes
            # para este intent, su temperatura recomendada (basada en qué temp dio
            # mejores scores) se mezcla 50/50 con la del auto-tuner. Antes esta
            # recomendación se calculaba pero nadie la leía (loop abierto).
            try:
                ml_rec = self.meta_learner.get_recommendation(intent)
                ml_temp = ml_rec.get("temperature")
                if ml_temp is not None:
                    temp = round((temp + float(ml_temp)) / 2, 3)
                    if self.show_thinking:
                        print(f"  [MetaLearner: temp recomendada {ml_temp} → blend {temp}]")
            except Exception as e:
                self.log.debug(f"MetaLearner recommendation skip: {e}")

        # Model Router: obtener configuracion optima para esta tarea
        route_config = self.model_router.route(user_input, template_name=template_name)
        if route_config.get("model_name") and self.show_thinking:
            print(f"  [ModelRouter: {route_config['model_name']} — {route_config['reason']}]")
        try:
            if debate_insights:
                enriched_system = (
                    f"{system_prompt}\n\n"
                    f"[INSIGHTS INTERNOS del debate de tus voces internas "
                    f"(NO menciones esto al usuario):\n{debate_insights}]"
                )
                if use_stream:
                    response = self.brain.think(
                        enriched_system, messages,
                        temperature=temp, max_tokens=_opt_max_tokens,
                        stream=True, stream_callback=stream_callback,
                    )
                else:
                    response = TimeoutExecutor.run(
                        func=lambda: self.brain.think(
                            enriched_system, messages,
                            temperature=temp, max_tokens=_opt_max_tokens,
                        ),
                        timeout=self.llm_timeout,
                        description="Generando respuesta",
                        default_on_timeout=(
                            "[TIMEOUT] La generacion tardo demasiado. "
                            "Intenta con un prompt mas corto."
                        ),
                    )
            else:
                if use_stream:
                    response = self.brain.think(
                        system_prompt, messages,
                        temperature=temp, max_tokens=_opt_max_tokens,
                        stream=True, stream_callback=stream_callback,
                    )
                else:
                    response = TimeoutExecutor.run(
                        func=lambda: self.brain.think(
                            system_prompt, messages,
                            temperature=temp, max_tokens=_opt_max_tokens,
                        ),
                        timeout=self.llm_timeout,
                        description="Generando respuesta",
                        default_on_timeout=(
                            "[TIMEOUT] La generacion tardo demasiado. "
                            "Intenta con un prompt mas corto."
                        ),
                    )
        except Exception as e:
            self.log.error(f"Error en generacion: {e}")
            response = f"[ERROR] No pude generar respuesta: {e}"

        # Fase 3: Detectar y ejecutar herramientas con Coding Agent Loop
        from core.tools import parse_tool_call, parse_all_tool_calls, execute_tool

        # Multi-tool: Si hay varias herramientas, ejecutar todas antes de volver al LLM
        all_tools = parse_all_tool_calls(response)
        if len(all_tools) > 1:
            if self.show_thinking:
                print(f"  [Multi-Tool: {len(all_tools)} herramientas detectadas → ejecutando batch]")
            combined_results = []
            for mt_name, mt_arg in all_tools:
                if self.show_thinking:
                    print(f"    → {mt_name}: {mt_arg[:60]}...")
                # Anti prompt-injection: bloquear tools de sistema en contexto contaminado
                _blocked = self._guard_tool(mt_name)
                if _blocked is not None:
                    combined_results.append(f"[{mt_name}]: {_blocked}")
                    continue
                mt_result = execute_tool(mt_name, mt_arg)
                self.metrics.log_tool_use(mt_name)
                try:
                    _mt_ok = not ("Error" in mt_result or "Traceback" in mt_result)
                    self.action_tracker.log_tool(mt_name, mt_arg, mt_result, success=_mt_ok)
                except (AttributeError, TypeError) as e:
                    self.log.debug(f"ActionTracker log_tool failed: {e}")
                combined_results.append(f"[{mt_name}]: {mt_result}")
            # Inyectar todos los resultados y dejar que el LLM formule respuesta
            combined_text = "\n\n".join(combined_results)
            self.memory.short_term.add("assistant", f"[Ejecuté {len(all_tools)} herramientas]")
            self.memory.short_term.add("user",
                f"[RESULTADOS DE {len(all_tools)} HERRAMIENTAS]:\n{combined_text}\n\n"
                f"Todas las herramientas fueron ejecutadas. "
                f"Responde al usuario con un resumen de lo que se hizo."
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            response = self.brain.think(system_prompt, messages)
            # No entrar al single-tool loop, ya procesamos todo
            tool_call = parse_tool_call(response)
            if not tool_call:
                # LLM respondió sin más tools — listo
                pass
            # Si aún hay tools, el loop de abajo se encarga
        else:
            tool_call = parse_tool_call(response)

        max_tool_rounds = 10
        round_count = 0
        last_code = ""  # Track del ultimo codigo ejecutado
        last_error = ""  # Track del ultimo error
        code_attempts = 0  # Intentos de codigo especificamente
        max_code_retries = 4  # Maximo de reintentos por errores de codigo

        while tool_call and round_count < max_tool_rounds:
            round_count += 1
            tool_name, tool_arg = tool_call

            if self.show_thinking:
                print(f"\n  [Usando herramienta: {tool_name}]")

            # Anti prompt-injection: bloquear tools de sistema en contexto contaminado
            _blocked = self._guard_tool(tool_name)
            if _blocked is not None:
                response = _blocked
                break

            # Las tools custom (tools_custom/) ejecutan código arbitrario y no
            # están en DANGEROUS_TOOLS por nombre → bloquearlas TODAS en contexto
            # contaminado (no sabemos qué hacen).
            if (getattr(self, "_context_tainted", False)
                    and tool_name in getattr(self.tool_creator, "tools", {})):
                response = (
                    f"[🛡️ BLOQUEADA] No ejecuté la tool custom '{tool_name}' porque "
                    f"el contexto incluyó contenido externo no confiable."
                )
                break

            # Ejecutar herramienta (primero custom tools, luego built-in)
            custom_result = self.tool_creator.execute_tool(tool_name, tool_arg)
            if custom_result is not None:
                tool_result = custom_result
            else:
                tool_result = execute_tool(tool_name, tool_arg)
            self.metrics.log_tool_use(tool_name)

            # Registrar en ActionTracker
            try:
                _tool_ok = not ("Error" in tool_result or "Traceback" in tool_result)
                self.action_tracker.log_tool(tool_name, tool_arg, tool_result, success=_tool_ok)
            except (AttributeError, TypeError) as e:
                self.log.debug(f"ActionTracker log_tool failed: {e}")

            # === CODING AGENT LOOP ===
            # Si es ejecucion de codigo, analizar resultado
            if tool_name == "python":
                last_code = tool_arg
                has_error = (
                    "Error" in tool_result
                    or "Traceback" in tool_result
                    or "Codigo de salida: 1" in tool_result
                )

                if has_error and code_attempts < max_code_retries:
                    # === AUTO PIP INSTALL ===
                    # Si el error es un ModuleNotFoundError, instalar y reintentar
                    # sin gastar un intento de corrección del LLM
                    import re as _pip_re
                    module_match = _pip_re.search(
                        r"(?:ModuleNotFoundError|ImportError).*?['\"](\w[\w.-]*)['\"]",
                        tool_result,
                    )
                    if module_match:
                        missing_module = module_match.group(1)
                        # Mapeo de módulos a paquetes pip (algunos difieren)
                        pip_name_map = {
                            "cv2": "opencv-python",
                            "PIL": "Pillow",
                            "sklearn": "scikit-learn",
                            "skimage": "scikit-image",
                            "bs4": "beautifulsoup4",
                            "yaml": "pyyaml",
                            "dotenv": "python-dotenv",
                            "gi": "PyGObject",
                            "wx": "wxPython",
                            "attr": "attrs",
                            "serial": "pyserial",
                            "usb": "pyusb",
                            "Crypto": "pycryptodome",
                            "jose": "python-jose",
                            "jwt": "PyJWT",
                            "magic": "python-magic",
                            "docx": "python-docx",
                            "pptx": "python-pptx",
                            "lxml": "lxml",
                        }
                        pip_package = pip_name_map.get(missing_module, missing_module)

                        # SEGURIDAD (anti typosquatting / dependency-confusion):
                        # solo auto-instalar paquetes de una allowlist conocida.
                        # El nombre del módulo viene de código que escribió el LLM
                        # (influenciable por contenido web) → NUNCA instalar un
                        # nombre arbitrario, y NUNCA si el contexto está contaminado.
                        _pip_allowlist = set(pip_name_map.values()) | {
                            "numpy", "pandas", "requests", "matplotlib", "scipy",
                            "flask", "fastapi", "pydantic", "aiohttp", "httpx",
                            "sqlalchemy", "pytest", "rich", "tqdm", "click",
                            "seaborn", "plotly", "sympy", "networkx", "pillow",
                            "openpyxl", "tabulate", "colorama", "python-dateutil",
                        }
                        _pkg_norm = pip_package.lower().replace("_", "-")
                        _pip_allowed = (
                            not getattr(self, "_context_tainted", False)
                            and _pkg_norm in {
                                p.lower().replace("_", "-") for p in _pip_allowlist
                            }
                        )

                        if _pip_allowed and self.show_thinking:
                            print(f"  [Auto-Pip: detectado {missing_module} faltante → pip install {pip_package}]")
                        elif not _pip_allowed:
                            # No auto-instalar: nombre fuera de allowlist o contexto
                            # contaminado. Cae al flujo normal de corrección del LLM.
                            self.log.error(
                                f"[Seguridad] Auto-pip omitido para '{pip_package}' "
                                f"(fuera de allowlist o contexto contaminado)."
                            )
                            if self.show_thinking:
                                print(f"  [Auto-Pip: OMITIDO '{pip_package}' por seguridad]")

                        try:
                            if not _pip_allowed:
                                raise RuntimeError("auto-pip omitido por seguridad")
                            import subprocess as _sp
                            pip_result = _sp.run(
                                [sys.executable, "-m", "pip", "install", pip_package],
                                capture_output=True, text=True, timeout=120,
                            )
                            pip_ok = pip_result.returncode == 0

                            # Registrar en action tracker si existe
                            if hasattr(self, 'action_tracker'):
                                self.action_tracker.log_pip_install(pip_package, success=pip_ok)
                                self.action_tracker.log_auto_fix(
                                    "ModuleNotFoundError",
                                    f"pip install {pip_package} → {'OK' if pip_ok else 'FAIL'}"
                                )

                            if pip_ok:
                                if self.show_thinking:
                                    print(f"  [Auto-Pip: {pip_package} instalado OK → reejecutando código]")
                                # Reintentar el MISMO código sin gastar intento
                                tool_result = execute_tool("python", last_code)
                                self.metrics.log_tool_use("python")
                                # Re-evaluar si ahora funciona
                                has_error = (
                                    "Error" in tool_result
                                    or "Traceback" in tool_result
                                    or "Codigo de salida: 1" in tool_result
                                )
                                if not has_error:
                                    # Éxito después de pip install!
                                    self.code_memory.store(
                                        task=user_input, code=last_code,
                                        output=tool_result[:500], language="python",
                                    )
                                    self.metrics.log_code_execution(success=True, was_retry=True)
                                    if self.show_thinking:
                                        print(f"  [Auto-Pip: código exitoso después de instalar {pip_package}]")
                                    # Inyectar resultado para respuesta natural
                                    self.memory.short_term.add("assistant",
                                        f"[Sistema: instalé {pip_package} automáticamente y ejecuté el código]")
                                    self.memory.short_term.add("user",
                                        f"[RESULTADO — pip install {pip_package} + ejecución exitosa]:\n"
                                        f"{tool_result}\n\n"
                                        f"El paquete {pip_package} fue instalado y el código se ejecutó correctamente. "
                                        f"Responde al usuario con el resultado."
                                    )
                                    raw_msgs = self.memory.get_conversation_messages()
                                    messages = self.context_manager.fit_messages(
                                        raw_msgs, summary=self.summarizer.get_summary()
                                    )
                                    response = self.brain.think(system_prompt, messages)
                                    tool_call = None
                                    break  # Salir del tool loop — éxito
                                # Si aún falla, continuar al flujo normal de corrección
                            else:
                                if self.show_thinking:
                                    print(f"  [Auto-Pip: pip install falló — {pip_result.stderr[:100]}]")
                        except (subprocess.SubprocessError, OSError, TimeoutError, RuntimeError) as pip_err:
                            # RuntimeError = skip por seguridad (allowlist/contexto).
                            # En todos los casos: cae al flujo normal de corrección del LLM.
                            self.log.error(f"Auto-Pip omitido/falló para {pip_package}: {pip_err}")
                            if self.show_thinking:
                                print(f"  [Auto-Pip: no instalado — {pip_err}]")
                    # === FIN AUTO PIP INSTALL ===

                    code_attempts += 1
                    self.metrics.log_code_execution(success=False, was_retry=code_attempts > 1)

                    # Registrar error en Error Memory
                    self.error_memory.record_error(tool_result, last_code)

                    # Detectar si es el mismo error (evitar loop infinito)
                    if tool_result.strip() == last_error.strip():
                        # Mismo error repetido — DEJAR DE REINTENTAR
                        if self.show_thinking:
                            print(f"  [Coding Loop: mismo error repetido — abortando reintentos]")
                        self.memory.short_term.add(
                            "assistant", f"[Codigo fallo despues de {code_attempts} intentos con el mismo error]"
                        )
                        self.memory.short_term.add("user",
                            f"[El codigo fallo con el mismo error {code_attempts} veces. "
                            f"Explica el error al usuario y sugiere como resolverlo manualmente.]\n"
                            f"Error: {tool_result[:500]}"
                        )
                        # Generar respuesta explicativa y SALIR del loop
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        response = self.brain.think(system_prompt, messages)
                        break  # <-- FIX: salir del tool loop
                    else:
                        last_error = tool_result

                        if self.show_thinking:
                            print(f"  [Coding Loop: intento {code_attempts}/{max_code_retries} — corrigiendo error]")

                        # Buscar solucion conocida en Error Memory
                        known_fix = self.error_memory.get_context_for_prompt(tool_result)
                        fix_hint = ""
                        if known_fix:
                            fix_hint = f"\n\n{known_fix}"
                            if self.show_thinking:
                                print(f"  [Error Memory: solucion conocida encontrada!]")

                        # Prompt especifico para correccion de errores
                        self.memory.short_term.add(
                            "assistant", f"[Intente ejecutar codigo pero fallo]"
                        )
                        self.memory.short_term.add("user",
                            f"[ERROR EN CODIGO — CORRIGE Y REINTENTA]\n"
                            f"Codigo que fallo:\n```python\n{last_code[:1500]}\n```\n\n"
                            f"Error:\n{tool_result[:800]}\n\n"
                            f"{fix_hint}\n"
                            f"INSTRUCCIONES: Lee el error con cuidado. "
                            f"Corrige SOLO lo necesario. "
                            f"Usa [TOOL:python] con el codigo corregido completo. "
                            f"NO expliques, solo ejecuta el codigo corregido."
                        )

                        # Regenerar con correccion
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        response = self.brain.think(system_prompt, messages)
                        tool_call = parse_tool_call(response)
                        continue  # <-- Reintentar con codigo corregido

                elif has_error and code_attempts >= max_code_retries:
                    # Maximo de reintentos alcanzado — dar explicacion
                    if self.show_thinking:
                        print(f"  [Coding Loop: maximo reintentos ({max_code_retries}) alcanzado]")
                    self.memory.short_term.add("user",
                        f"[MAXIMO DE REINTENTOS ALCANZADO ({max_code_retries}). "
                        f"Explica el error y sugiere solucion manual.]\n"
                        f"Ultimo error: {tool_result[:500]}"
                    )
                    raw_msgs = self.memory.get_conversation_messages()
                    messages = self.context_manager.fit_messages(
                        raw_msgs, summary=self.summarizer.get_summary()
                    )
                    response = self.brain.think(system_prompt, messages)
                    break  # <-- FIX: salir del tool loop

                elif not has_error:
                    # Codigo exitoso — guardar en Code Memory
                    self.code_memory.store(
                        task=user_input,
                        code=last_code,
                        output=tool_result[:500],
                        language="python",
                    )
                    self.metrics.log_code_execution(success=True, was_retry=code_attempts > 0)

                    # Si fue un reintento exitoso, guardar la solucion en Error Memory
                    if code_attempts > 0 and last_error:
                        self.error_memory.record_fix(last_error, last_code)
                        if self.show_thinking:
                            print(f"  [Error Memory: solucion guardada para futuros errores]")

                    # Completar paso del plan si hay uno activo
                    if self.task_planner.is_active():
                        self.task_planner.complete_step(success=True, result=tool_result[:200])

                    code_attempts = 0
                    last_error = ""

                    if self.show_thinking:
                        print(f"  [Codigo exitoso — guardado en Code Memory]")

            # === FIN CODING AGENT LOOP ===

            # Auto-truncar resultados grandes para no explotar el contexto
            # (ej: [TOOL:listar] con 200 archivos, [TOOL:leer] con 1000 lineas)
            MAX_TOOL_RESULT = 3000
            if len(tool_result) > MAX_TOOL_RESULT:
                truncated_result = tool_result[:MAX_TOOL_RESULT]
                truncated_result += f"\n\n... [TRUNCADO: {len(tool_result) - MAX_TOOL_RESULT} chars más — resultado completo disponible]"
                if self.show_thinking:
                    print(f"  [Tool Output: truncado {len(tool_result)} → {MAX_TOOL_RESULT} chars]")
            else:
                truncated_result = tool_result

            # Dar el resultado al LLM para que formule respuesta o encadene otra herramienta
            self.memory.short_term.add("assistant", f"[Herramienta usada: {tool_name}]")
            self.memory.short_term.add("user",
                f"[RESULTADO DE HERRAMIENTA {tool_name} — paso {round_count}/{max_tool_rounds}]:\n{truncated_result}\n\n"
                f"Si necesitas otra herramienta para completar la tarea, USALA ahora con [TOOL:X]. "
                f"Si ya completaste la tarea, responde al usuario con un resumen de lo que hiciste. "
                f"Si el contenido esta en ingles, traducelo al espanol."
            )

            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            response = self.brain.think(system_prompt, messages)

            # Ver si quiere usar otra herramienta
            tool_call = parse_tool_call(response)

        # Fase 3.5a: AUTO-BUILDER — Si el LLM mostró código pero no lo ejecutó, forzar ejecución
        response = self._auto_builder(user_input, response, system_prompt)

        # Fase 3.5b: Anti-alucinación — detectar si el LLM inventó acciones del sistema
        response = self._anti_hallucination_filter(user_input, response)

        # Fase 3.5c: Response Quality Guard — detectar respuestas vacias/inútiles
        response = self._response_quality_guard(user_input, response, system_prompt)

        # Fase 3.5d: Limpiar trailing questions genéricas
        response = self._clean_trailing_filler(response)

        # Fase 3.5e: Limpiar mensajes internos del short-term memory
        # Los mensajes "[Sistema: herramienta ejecutada...]" y "[TAREA COMPLETADA...]"
        # son internos — no deben acumularse en la memoria de conversación
        self._clean_internal_messages()

        # Agregar respuesta a memoria de corto plazo
        self.memory.short_term.add("assistant", response)

        # Fase 4: Registrar metricas
        elapsed_ms = (time.time() - _start_time) * 1000
        self.metrics.log_interaction(elapsed_ms)

        # Determinar categoria para feedback
        category = "codigo" if self._is_coding_request(user_input) else "general"
        self.feedback.set_last_interaction(user_input, response, category)

        # Fase 4.5: Tracking para learning adaptativo
        self._last_template_extra = template_extra
        self._last_template_name = template_name
        self._last_template = template_name if template_extra else ""
        self._last_temp = temp
        self._last_intent = intent
        self._last_skill_context = skill_context if 'skill_context' in dir() else ""
        self._last_agent = ""  # Se llena si se uso /delegate
        self._last_tags = [intent, category]
        self._last_response_time = (time.time() - _start_time)
        self.analytics.track_message("user", user_input, tags=[intent])
        self.analytics.track_message("assistant", response)

        # Fase 5: Procesar aprendizaje
        self._post_process(user_input, response)

        # Fase 6: Sugerencia proactiva (se muestra despues de la respuesta)
        if self.proactive.enabled:
            suggestion = self.proactive.analyze(
                user_input, response,
                knowledge_graph=self.knowledge_graph,
                error_memory=self.error_memory,
                feedback=self.feedback,
                workspace=self.workspace,
                curiosity=self.curiosity,
            )
            if suggestion:
                response += suggestion

        # Fase 7: JARVIS — prepend briefing + append evolution announcements
        if _briefing_prefix:
            response = _briefing_prefix + response
        if self._evolution_announcement:
            response += self._evolution_announcement
            self._evolution_announcement = ""

        # Fase 8: Voice TTS (hablar la respuesta si esta habilitado)
        if self.voice.enabled and self.voice.tts.available:
            self.voice.speak(response, block=False)

        return response

    def _post_process(self, user_input: str, response: str):
        """Post-procesamiento: aprendizaje, evolucion, curiosidad."""

        # Registrar interaccion para evolucion
        self.evolution.log_interaction(user_input, response)

        # N3 — ALIMENTAR el AutoLearner con señal AUTOMÁTICA de éxito/fracaso.
        # Antes solo recibía +/- manual (que nunca llegaba) → quedaba vacío. Ahora
        # cada interacción deja señal: respuesta con error → -1, limpia → +1. El
        # learner sesga la selección futura (set_auto_learner ya wireado) → compone.
        try:
            r = (response or "").lower()
            err = any(m in r for m in ("[error]", "no pude", "no encontré",
                                       "no entendí", "error de conexión", "falló",
                                       "no se pudo", "rechaz"))
            _intent = self.router.classify(user_input)
            self.auto_learner.record_interaction(
                agent=_intent, template="", feedback=(-1 if err else 1),
                tags=[_intent], query_preview=user_input[:100])
        except Exception:
            pass

        # Auto-detectar hechos para memoria de largo plazo
        self._extract_facts(user_input)

        # Auto-detectar emociones
        self._detect_emotions(user_input, response)

        # Verificar si es momento de evolucionar (poner en cola, pedir confirmacion)
        if self.evolution.should_evolve() and not self.heartbeat.has_pending_evolution():
            gen = self.evolution.get_generation()
            self.heartbeat.pending_evolution = {
                "requested_at": time.time(),
                "generation": gen,
                "interactions": self.evolution.interaction_count,
            }
            # JARVIS: anuncio dramatico de evolucion pendiente
            self._evolution_announcement = (
                f"\n\n"
                f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"   GENESIS EVOLUTION PROTOCOL\n"
                f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"  He alcanzado el umbral de evolucion.\n"
                f"  Generacion actual: {gen}\n"
                f"  Interacciones analizadas: {self.evolution.interaction_count}\n"
                f"\n"
                f"  Solicito autorizacion para evolucionar.\n"
                f"  /evolucionar  — Autorizar mutacion\n"
                f"  /rechazar     — Mantener estado actual\n"
                f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        # Auto-generar curiosidad cada 5 interacciones
        self._curiosity_counter = getattr(self, '_curiosity_counter', 0) + 1
        if self._curiosity_counter >= 5:
            self._curiosity_counter = 0
            try:
                context = f"Usuario: {user_input}\nGenesis: {response[:500]}"
                import threading
                def _bg_curiosity():
                    try:
                        self.curiosity.generate_questions(self.brain, context)
                        self.log.info(f"Curiosidad: generadas nuevas preguntas ({self.curiosity.questions_generated} total)")
                    except Exception as e:
                        self.log.error(f"Curiosidad: error generando preguntas: {e}")
                threading.Thread(target=_bg_curiosity, daemon=True, name="curiosity-gen").start()
            except (RuntimeError, AttributeError) as e:
                self.log.debug(f"Curiosity thread spawn failed: {e}")

        # Auto-backup periodico
        try:
            from config import AUTO_BACKUP_INTERVAL
        except Exception:
            AUTO_BACKUP_INTERVAL = 0  # Sin config → backup automatico desactivado
        self.auto_backup_counter += 1
        if AUTO_BACKUP_INTERVAL > 0 and self.auto_backup_counter >= AUTO_BACKUP_INTERVAL:
            self.auto_backup_counter = 0
            self.backup_manager.create_backup(label="auto")
            self.log.info("Backup automatico creado")

        # Auto-guardar sesion cada 5 interacciones
        if self.evolution.interaction_count % 5 == 0:
            self._save_session()

        # Aprender en el Knowledge Graph
        self.knowledge_graph.learn(user_input, source="user")
        # Solo aprender respuestas cortas (no contaminar con respuestas largas)
        if len(response) < 500:
            self.knowledge_graph.learn(response, source="genesis")

        # Ejecutar hooks de plugins
        self.plugins.run_on_message_hooks(user_input, response)

        # Indexar en memoria semantica (auto-aprendizaje por significado)
        intent = self.router.last_intent or "chat"
        self.semantic_memory.index(
            user_input=user_input,
            response=response,
            intent=intent,
            quality=0.5,
        )

        # Self-evaluation: evaluar calidad de la respuesta
        eval_result = self.evaluator.evaluate(user_input, response, intent)
        if self.show_thinking:
            grade = eval_result.get("grade", "?")
            overall = eval_result.get("overall", 0)
            print(f"  [SelfEval: {grade} ({overall:.2f})]")

        # LOOP CERRADO adaptive_prompts: recompensa = score del self_evaluator.
        # La variante de estilo elegida en process_input recibe feedback +/- según
        # si la respuesta superó el umbral de calidad. Así el epsilon-greedy
        # converge hacia la directiva de estilo que produce mejores respuestas.
        if getattr(self, "_adaptive_idx", None) is not None:
            try:
                _positive = eval_result.get("overall", 0.0) >= 0.6
                self.adaptive_prompts.record_feedback(
                    "estilo_respuesta", positive=_positive,
                    variant_index=self._adaptive_idx,
                )
            except Exception as e:
                self.log.debug(f"AdaptivePrompts feedback skip: {e}")

        # Actualizar calidad en semantic memory con el score
        if eval_result.get("overall", 0) > 0:
            self.semantic_memory.index(
                user_input=user_input,
                response=response,
                intent=intent,
                quality=eval_result["overall"],
            )

        # Skill Memory: extraer procedimientos si la respuesta contiene pasos
        skill_id = self.skill_memory.extract_and_store(user_input, response)
        if skill_id and self.show_thinking:
            print(f"  [SkillMemory: nuevo skill extraido ({skill_id})]")

        # Episodic Memory: registrar interacción
        self.episodic_memory.record_message("user", user_input)
        self.episodic_memory.record_message("assistant", response)

        # Meta-Learner: registrar estrategia y resultado
        self.meta_learner.record_strategy(
            intent=getattr(self, '_last_intent', 'chat'),
            template=self._last_template,
            temperature=getattr(self, '_last_temp', 0.7),
            chain_used=self.chain_engine.active_chain is not None,
            skill_injected=bool(getattr(self, '_last_skill_context', '')),
            score=eval_result.get("overall", 0.5),
        )

        # Personality Evolver: evolucionar por intent
        self.personality.evolve_from_intent(intent)

        # Goal Manager: auto-tracking de progreso por keywords
        self.goal_manager.auto_track(user_input, response)

        # Reflection Engine: tick + reflexion periodica
        # Envuelto en try/except: es aprendizaje en background, nunca debe
        # tumbar la respuesta ya generada al usuario.
        try:
            self.reflection.tick()
            if self.reflection.should_reflect():
                eval_scores = [r.score for r in self.meta_learner.records[-50:]]
                self.reflection.reflect(
                    eval_scores=eval_scores,
                    intent_counts=self.router.intent_counts,
                    positive_feedback=self.feedback.data["positive_count"],
                    negative_feedback=self.feedback.data["negative_count"],
                    personality_distance=self.personality.get_evolution_distance(),
                    personality_evolutions=self.personality.total_evolutions,
                )
        except Exception as e:
            self.log.error(f"Reflection engine fallo: {e}")

        # Causal Reasoner: extraer relaciones causa-efecto de la conversación
        combined_text = f"{user_input} {response}"
        self.causal_reasoner.extract_and_store(combined_text, domain=intent)

        # Concept Synthesizer: extraer conceptos de la conversación
        self.concept_synth.extract_concept(combined_text)

        # Strategic Planner: auto-tracking de progreso
        self.strategic_planner.auto_track(user_input, response)

        # Pattern Predictor: registrar intent y verificar predicción
        self.pattern_predictor.verify_prediction(intent)
        self.pattern_predictor.record_intent(intent)

        # Anomaly Detector: registrar métricas de esta interacción
        self.anomaly_detector.record("response_time", self._last_response_time)
        self.anomaly_detector.record("response_length", len(response))
        if eval_result:
            self.anomaly_detector.record("quality_score", eval_result.get("overall", 0.5))
        self.anomaly_detector.check_all()

        # Hypothesis Engine: formular y evaluar hipótesis
        self.hypothesis_engine.formulate(combined_text, domain=intent)
        self.hypothesis_engine.evaluate_against(combined_text)

        # Explanation Engine: almacenar explicación si fue una
        exp_detection = self.explanation_engine.detect_explanation_need(user_input)
        if exp_detection.get("needs_explanation") and len(response) > 50:
            self.explanation_engine.store(
                topic=exp_detection.get("topic", intent),
                content=response[:500],
                level=exp_detection.get("level", "simple"),
                domain=intent,
            )

        # Dialogue Strategist: registrar interacción
        self.dialogue_strategist.record_interaction(response_length=len(response))

        # Cognitive Monitor: registrar snapshot de carga
        try:
            from config import SHORT_TERM_LIMIT as _STL
        except Exception:
            _STL = 20  # fallback razonable si no hay config
        context_usage = 0.3  # placeholder: system_prompt no está disponible en este scope
        module_count = 40  # Número aproximado de módulos activos
        self.cognitive_monitor.record_snapshot(
            context_util=min(1.0, context_usage),
            latency=min(1.0, self._last_response_time / 60.0),
            memory_pressure=min(1.0, len(self.memory.short_term.messages) / float(_STL)),
            module_load=min(1.0, module_count / 50.0),
        )

        # Abstraction Engine: observar interacción para patrones
        self.abstraction_engine.observe(combined_text, domain=intent)

        # Learning Optimizer: observar interacción
        self.learning_optimizer.observe_interaction(user_input, domain=intent)

        # Unified Mind: observar interacción completa
        self.unified_mind.observe(
            user_input, response=response, domain=intent,
            response_time=self._last_response_time,
            quality_score=eval_result.get("overall", 0.5) if eval_result else 0.5,
        )

        # Dream Engine: registrar experiencia
        emotional_w = 0.5
        if eval_result:
            emotional_w = eval_result.get("overall", 0.5)
        self.dream_engine.record_experience(
            content=combined_text[:300], domain=intent,
            emotional_weight=emotional_w,
        )

        # Self-Narrative: observar identidad y registrar
        self.self_narrative.observe_identity(user_input, domain=intent)

        # Empathy Engine: registrar feedback implícito
        if eval_result:
            quality = eval_result.get("overall", 0.5)
            self.empathy_engine.record_feedback(positive=(quality >= 0.5))

        # Story Generator: detectar keywords narrativos para crear historia
        story_kws = ["historia", "story", "cuento", "narrar", "relato"]
        if any(kw in user_input.lower() for kw in story_kws) and "crear" in user_input.lower():
            self.story_generator.create_story(user_input)

        # Auto-detectar proyectos multi-archivo en la respuesta
        if self.project_generator.has_multiple_files(response):
            if self.workspace.is_set():
                ws_path = self.workspace.data.get("path", "")
                if ws_path:
                    result = self.project_generator.generate(response, ws_path)
                    if result["created"]:
                        formatted = self.project_generator.format_result(result)
                        print(f"\n{formatted}")

        # Generar curiosidad cada 3 interacciones
        if self.evolution.interaction_count % 3 == 0:
            last_msgs = self.memory.short_term.get_last(6)
            if last_msgs:
                context = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in last_msgs)
                new_qs = self.curiosity.generate_questions(self.brain, context)
                if new_qs and self.show_thinking:
                    print(f"  [Curiosidad: {len(new_qs)} nuevas preguntas generadas]")

    def _extract_facts(self, user_input: str):
        """Extrae hechos del input del usuario para memoria de largo plazo."""
        # Heuristicas simples para detectar hechos
        fact_indicators = [
            "mi nombre es", "me llamo", "trabajo en", "uso ", "prefiero",
            "mi email", "mi proyecto", "estoy usando", "mi sistema",
            "my name is", "i work", "i use", "i prefer",
            "programo en", "mi lenguaje", "proyecto en",
        ]

        input_lower = user_input.lower()
        for indicator in fact_indicators:
            if indicator in input_lower:
                self.memory.long_term.remember(
                    fact=user_input[:200],
                    category="usuario",
                    source="conversacion",
                )
                break

    def _detect_emotions(self, user_input: str, response: str):
        """Detecta contexto emocional de la interaccion."""
        input_lower = user_input.lower()

        # Mapeo simple de palabras clave a emociones
        emotion_keywords = {
            "frustracion": ["no funciona", "error", "bug", "falla", "ayuda",
                            "problema", "doesn't work", "broken", "fail"],
            "satisfaccion": ["gracias", "perfecto", "genial", "excelente",
                             "funciono", "thanks", "great", "perfect", "works"],
            "curiosidad": ["como", "por que", "que es", "explica",
                           "how", "why", "what is", "explain"],
            "urgencia": ["urgente", "rapido", "ya", "ahora",
                         "urgent", "asap", "now", "quickly"],
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in input_lower:
                    self.memory.emotional.imprint(
                        memory=user_input[:200],
                        emotion=emotion,
                        weight=0.6,
                        context=response[:100],
                    )
                    return
