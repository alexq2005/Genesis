"""
Genesis Tools Mixin.

Contiene la lógica de auto-detección y ejecución de herramientas:
- _auto_detect_tool: mega-detector de intenciones (apps, web, archivos, sistema)
- _auto_builder: fuerza ejecución de código mostrado pero no ejecutado
- Filtros anti-alucinación y calidad de respuesta
"""
import json
import os
import re
import time
from pathlib import Path

_re = re  # Alias used throughout this module


class GenesisToolsMixin:
    """Mixin con auto-detección de herramientas y filtros de calidad."""

    # Patrones que indican que el usuario quiere que Genesis APRENDA
    LEARN_TRIGGERS = [
        "aprende sobre", "aprende de", "aprende acerca",
        "especialízate en", "especializate en", "especializa en",
        "estudia sobre", "estudia de",
        "investiga y aprende", "investiga sobre", "investiga de",
        "quiero que aprendas", "quiero que sepas",
        "aprende todo sobre", "aprende mas sobre",
        "capacítate en", "capacitate en",
        "entrénate en", "entrenate en",
        "enfócate en", "enfocate en",
        "domina el tema", "domina sobre",
        "conviértete en experto", "conviertete en experto",
        "vuelvete experto", "se experto en",
        "learn about", "specialize in", "study about",
    ]

    # Cache de programas descubiertos (se refresca cada 5 min)
    _installed_apps_cache = None
    _installed_apps_cache_time = 0

    def _auto_builder(self, user_input: str, response: str, system_prompt: str) -> str:
        """
        AUTO-BUILDER: Intercepta respuestas del LLM y fuerza ejecución cuando corresponde.

        Maneja 2 casos:
        1. LLM mostró código en bloques markdown pero no usó [TOOL:] → ejecutar el código
        2. LLM se rehusó ("no puedo", "lo siento") cuando sí puede → re-intentar con prompt forzado

        Esto compensa que llama3.1 8B tiende a "explicar/rechazar" en vez de "ejecutar".
        """
        import re
        from core.tools import parse_tool_call, execute_tool

        # Solo activar si NO hubo tool call en la respuesta
        if parse_tool_call(response) is not None:
            return response

        # Detectar intención de "crear/construir" del usuario
        build_keywords = [
            "crea", "crealo", "créalo", "hazlo", "construye", "genera", "generalo",
            "escribi", "escribime", "haceme", "armame", "arma", "programa",
            "desarrolla", "implementa", "codea", "codealo", "ejecuta", "ejecutalo",
            "corre", "correlo", "guarda", "guardalo", "instala", "instalalo",
        ]
        user_lower = user_input.lower().strip()
        is_build_request = any(kw in user_lower for kw in build_keywords)

        if not is_build_request:
            return response

        # === CASO 2: REFUSAL DETECTION ===
        # Si el LLM se rehusó pero el usuario pidió crear algo, reintentar
        refusal_patterns = [
            "no puedo cumplir", "no puedo crear", "no puedo generar",
            "no tengo la capacidad", "no es posible", "lo siento",
            "no me es posible", "fuera de mis capacidades",
            "no puedo hacer eso", "no soy capaz",
        ]
        response_lower = response.lower()
        is_refusal = any(p in response_lower for p in refusal_patterns)

        if is_refusal:
            if self.show_thinking:
                print(f"  [Auto-Builder: REFUSAL detectado — reintentando con prompt forzado]")

            # Reintentar con un prompt que NO permita rehusarse
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA — OVERRIDE] Tu respuesta anterior fue incorrecta. "
                f"Tu SI tienes herramientas para crear archivos y ejecutar código. "
                f"Usa [TOOL:escribir] para crear archivos o [TOOL:python] para ejecutar código. "
                f"El usuario pidió: '{user_input}'. "
                f"EJECUTA la acción usando herramientas. NO digas 'no puedo'. "
                f"Responde SOLO con la herramienta, ejemplo:\n"
                f"Creando el archivo...\n"
                f"[TOOL:python] <código que cumple lo pedido>"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            retry_response = self.brain.think(system_prompt, messages)

            # Verificar si el retry tiene tool call
            tc = parse_tool_call(retry_response)
            if tc:
                tool_name, tool_arg = tc
                if self.show_thinking:
                    print(f"  [Auto-Builder: retry exitoso — ejecutando {tool_name}]")
                tool_result = execute_tool(tool_name, tool_arg)
                self.metrics.log_tool_use(tool_name)

                # Dar resultado al LLM para respuesta final
                self.memory.short_term.add("assistant", f"[Herramienta usada: {tool_name}]")
                self.memory.short_term.add("user",
                    f"[RESULTADO DE HERRAMIENTA {tool_name}]:\n{tool_result}\n\n"
                    f"Responde al usuario confirmando que se completó la acción."
                )
                raw_msgs = self.memory.get_conversation_messages()
                messages = self.context_manager.fit_messages(
                    raw_msgs, summary=self.summarizer.get_summary()
                )
                return self.brain.think(system_prompt, messages)

            # Si el retry tampoco tiene tool call, intentar extraer código y ejecutar
            code_blocks = re.findall(r'```(?:python|py)?\s*\n(.*?)```', retry_response, re.DOTALL)
            if code_blocks:
                code = code_blocks[0].strip()
                tool_result = execute_tool("python", code)
                self.metrics.log_tool_use("python")
                return (
                    f"Ejecutado.\n\n"
                    f"```python\n{code}\n```\n\n"
                    f"Resultado:\n{tool_result[:1500]}"
                )

            # Último recurso: respuesta del retry es mejor que el refusal original
            return retry_response

        # === CASO 1: CÓDIGO MOSTRADO SIN EJECUTAR ===
        code_blocks = re.findall(
            r'```(?:python|py)?\s*\n(.*?)```',
            response,
            re.DOTALL
        )

        if not code_blocks:
            return response

        # Tenemos código Y pedido de build → AUTO-EJECUTAR
        code = code_blocks[0].strip()

        if self.show_thinking:
            print(f"  [Auto-Builder: LLM mostró código sin ejecutar → forzando ejecución]")
            print(f"  [Auto-Builder: código de {len(code)} chars]")

        if len(code) > 30:
            # Ejecutar el código con [TOOL:python]
            tool_result = execute_tool("python", code)
            self.metrics.log_tool_use("python")

            has_error = (
                "Error" in tool_result
                or "Traceback" in tool_result
                or "Codigo de salida: 1" in tool_result
            )

            if has_error:
                # Código falló — pedir al LLM que corrija
                if self.show_thinking:
                    print(f"  [Auto-Builder: código falló, pidiendo corrección]")

                self.memory.short_term.add("assistant", "[Ejecuté el código pero falló]")
                self.memory.short_term.add("user",
                    f"[AUTO-BUILDER: El código que generaste falló al ejecutarse]\n"
                    f"Error:\n{tool_result[:800]}\n\n"
                    f"Codigo:\n```python\n{code[:1500]}\n```\n\n"
                    f"Corrige el error y usa [TOOL:python] para ejecutar el código corregido."
                )
                raw_msgs = self.memory.get_conversation_messages()
                messages = self.context_manager.fit_messages(
                    raw_msgs, summary=self.summarizer.get_summary()
                )
                corrected = self.brain.think(system_prompt, messages)

                tc = parse_tool_call(corrected)
                if tc:
                    tool_name, tool_arg = tc
                    result2 = execute_tool(tool_name, tool_arg)
                    self.metrics.log_tool_use(tool_name)
                    return (
                        f"Ejecutado (con corrección).\n\n"
                        f"```python\n{tool_arg[:2000]}\n```\n\n"
                        f"Resultado:\n{result2[:1000]}"
                    )
                return corrected
            else:
                # Código exitoso
                if self.show_thinking:
                    print(f"  [Auto-Builder: código ejecutado exitosamente]")

                self.code_memory.store(
                    task=user_input,
                    code=code,
                    output=tool_result[:500],
                    language="python",
                )

                text_before = response.split('```')[0].strip()
                if not text_before or len(text_before) < 10:
                    text_before = "Hecho."

                return (
                    f"{text_before}\n\n"
                    f"```python\n{code}\n```\n\n"
                    f"**Ejecutado automáticamente.** Resultado:\n{tool_result[:1500]}"
                )

        return response

    def _anti_hallucination_filter(self, user_input: str, response: str) -> str:
        """
        Detecta si el LLM inventó acciones o datos del sistema que no realizó.
        Si detecta alucinación, reemplaza con datos reales o respuesta honesta.
        """
        resp_lower = response.lower()
        user_lower = user_input.lower()

        # === CAPA 1: Hardware fabricado ===
        # Si la respuesta contiene especificaciones de hardware que parecen inventadas,
        # reemplazar con datos reales del sistema
        hw_fabrication_indicators = [
            # CPUs inventados comunes (el LLM los fabrica con frecuencia)
            "i7-10700", "i7-11700", "i7-12700", "i7-13700", "i7-14700",
            "i9-10900", "i9-11900", "i9-12900", "i9-13900", "i9-14900",
            "ryzen 9", "ryzen 7 5800", "ryzen 7 3700",
            # RAM inventada
            "64 gb ddr", "128 gb ddr", "32 gb ddr4", "16 gb ddr5",
            # GPUs inventadas (no es la RTX 3060 Ti real)
            "rtx 3080", "rtx 3090", "rtx 4060", "rtx 4070", "rtx 4080", "rtx 4090",
            "rtx 3070 ti", "rtx 3080 ti",
            # Discos inventados
            "samsung 970", "samsung 980", "samsung 990",
            "wd black", "crucial p5",
            # Fechas absurdas
            "01/03/2023",
        ]
        # Contar cuántos indicadores de fabricación hay
        hw_fabrication_count = sum(1 for ind in hw_fabrication_indicators if ind in resp_lower)
        if hw_fabrication_count >= 2:
            # 2+ indicadores = claramente fabricado → reemplazar con datos reales
            self.log.info(f"Anti-hallucination: {hw_fabrication_count} indicadores de HW fabricado detectados")
            try:
                from core.tools import SystemInfoTool
                real_info = SystemInfoTool.get_system_info()
                return (f"⚠️ Detuve una respuesta incorrecta. Estos son tus datos reales:\n\n"
                        f"{real_info}")
            except (ImportError, AttributeError, OSError):
                return ("⚠️ Detecté que iba a darte datos incorrectos. "
                        "Pedime 'info del sistema' para obtener los datos reales de tu equipo.")

        # === CAPA 2: Refusal / negación de capacidades ===
        refusal_phrases = [
            "no puedo acceder directamente",
            "no tengo acceso directo",
            "no puedo acceder a tu sistema",
            "no puedo acceder a las aplicaciones",
            "no tengo la capacidad",
            "no puedo ejecutar aplicaciones",
            "no puedo abrir aplicaciones",
            "no tengo acceso físico",
            "no tengo acceso a tu sistema",
            "solo tengo una voz",
            "sólo tengo una voz",
            "una voz digitalizada",
            "una única voz",
            "no tengo múltiples voces",
        ]
        if any(rp in resp_lower for rp in refusal_phrases):
            self.log.info("Anti-hallucination: refusal de capacidades detectado")
            return ("Sí puedo hacer eso. Tengo acceso completo a tu sistema: "
                    "abrir apps, gestionar archivos, info de hardware, TTS con 22 voces, "
                    "y más. Pedímelo de forma directa, por ejemplo: "
                    "'abre excel', 'info del sistema', 'busca archivos de X'.")

        # === CAPA 3: Acciones fabricadas ===
        hallucination_patterns = [
            ("restaurando", "restaurar archivos"),
            ("he restaurado", "restaurar archivos"),
            ("ha sido restaurado", "restaurar archivos"),
            ("archivo restaurado", "restaurar archivos"),
            ("accediendo a", "acceder al sistema"),
            ("he accedido", "acceder al sistema"),
            ("eliminando el archivo", "eliminar archivos"),
            ("he eliminado", "eliminar archivos"),
            ("archivo eliminado", "eliminar archivos"),
            ("moviendo el archivo", "mover archivos"),
            ("he movido", "mover archivos"),
            ("copiando el archivo", "copiar archivos"),
            ("he copiado", "copiar archivos"),
            ("instalando", "instalar software"),
            ("he instalado", "instalar software"),
            ("descargando", "descargar archivos"),
            ("he descargado", "descargar archivos"),
            ("ejecutando el comando", "ejecutar comandos"),
            ("he ejecutado", "ejecutar comandos"),
        ]

        # Solo verificar si NO hubo tool call real en esta interacción
        from core.tools import parse_tool_call
        had_tool = parse_tool_call(response) is not None

        if not had_tool:
            for pattern, action in hallucination_patterns:
                if pattern in resp_lower:
                    fake_indicators = [
                        "informe de ventas", "fotos de vacaciones",
                        "confirmación de reserva", "proyecto de diseño",
                        "lista de compras", "documento.txt", "imagen.jpg",
                        "el archivo ha sido", "ahora muestra 0",
                        "se ha completado", "operación exitosa",
                    ]
                    if any(fi in resp_lower for fi in fake_indicators):
                        return (f"No pude {action} — esa acción requiere una "
                                f"herramienta que no se ejecutó. "
                                f"Intenta pedirlo de forma más específica.")

        # === CAPA 4: Incertidumbre detectada — auto-investigar ===
        # Si el LLM admite no saber o da una respuesta vaga/incierta,
        # buscar en internet y re-generar con datos reales
        uncertainty_phrases = [
            "no estoy seguro",
            "no tengo información",
            "no dispongo de",
            "no cuento con datos",
            "no tengo datos",
            "no tengo certeza",
            "podría estar equivocado",
            "no puedo confirmar",
            "no tengo acceso a esa información",
            "mi conocimiento llega hasta",
            "mis datos llegan hasta",
            "no tengo información actualizada",
            "no puedo verificar",
            "desconozco",
            "no sabría decirte",
            "no tengo forma de saber",
            "habría que verificar",
            "no me consta",
        ]
        if any(up in resp_lower for up in uncertainty_phrases):
            # El LLM admitió no saber — intentar buscar en la web
            try:
                if hasattr(self, 'web') and self.web and self.web.searcher.available:
                    # Extraer tema de la pregunta del usuario
                    topic = user_input.strip().rstrip("?.,!")
                    if self.show_thinking:
                        print(f"  [Anti-hallucination Capa 4: incertidumbre detectada — investigando '{topic}']")

                    results = self.web.searcher.search(topic, max_results=3)
                    if results:
                        search_ctx = f"[INVESTIGACIÓN AUTOMÁTICA — Genesis detectó que no tenía la respuesta y buscó en internet]:\n"
                        for i, r in enumerate(results[:3], 1):
                            title = r.get("title", "")
                            snippet = r.get("snippet", r.get("body", ""))
                            url = r.get("url", r.get("href", ""))
                            search_ctx += f"{i}. {title}\n   {snippet[:250]}\n   Fuente: {url}\n\n"

                        # Leer primera pagina para mas detalle
                        first_url = results[0].get("url", results[0].get("href", ""))
                        if first_url:
                            try:
                                page_text = self.web.reader.read_page(first_url)
                                if page_text and len(page_text) > 100:
                                    search_ctx += f"\n[CONTENIDO DETALLADO]:\n{page_text[:2000]}\n"
                            except (OSError, ValueError, AttributeError):
                                pass

                        search_ctx += (
                            "\nCon esta información REAL, responde la pregunta del usuario. "
                            "Cita las fuentes. NO inventes nada que no esté en los resultados."
                        )

                        # Re-generar respuesta con datos reales
                        self.memory.short_term.add("assistant", response)
                        self.memory.short_term.add("user", search_ctx)
                        raw_msgs = self.memory.get_conversation_messages()
                        messages = self.context_manager.fit_messages(
                            raw_msgs, summary=self.summarizer.get_summary()
                        )
                        # Usar system_prompt del build actual
                        sys_prompt = self.build_system_prompt()
                        new_response = self.brain.think(sys_prompt, messages, temperature=0.3)
                        if new_response and len(new_response) > len(response):
                            self.log.info("Anti-hallucination Capa 4: respuesta regenerada con datos web")
                            return new_response
            except Exception as e:
                if self.show_thinking:
                    print(f"  [Anti-hallucination Capa 4: error en investigación — {e}]")

        return response

    def _response_quality_guard(self, user_input: str, response: str,
                                 system_prompt: str) -> str:
        """
        Response Quality Guard — Detecta respuestas vacías, genéricas o inútiles
        y fuerza regeneración con prompt mejorado.

        Detecta:
        1. Respuestas demasiado cortas para la complejidad de la pregunta
        2. Respuestas genéricas que no aportan valor
        3. Contradicciones (dice "puedo" y luego "no puedo" en la misma respuesta)
        4. Respuestas en inglés cuando debería ser español
        """
        resp_lower = response.lower().strip()
        user_lower = user_input.lower().strip()

        # No aplicar si la respuesta ya contiene resultado de herramienta
        if "[RESULTADO" in response or "[TOOL:" in response:
            return response

        # 1. Respuesta demasiado corta para preguntas sustanciales
        is_complex_query = len(user_input) > 30 or any(
            w in user_lower for w in ["como", "cómo", "por que", "por qué",
                                       "explica", "investiga", "analiza"]
        )
        if is_complex_query and len(response.strip()) < 40:
            if self.show_thinking:
                print(f"  [QualityGuard: respuesta muy corta ({len(response)} chars) para query compleja — regenerando]")
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA: Tu respuesta anterior fue demasiado corta y genérica. "
                f"El usuario hizo una pregunta sustancial. "
                f"Responde con profundidad y detalle. "
                f"Mínimo 3-4 oraciones con información útil y específica.]"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.8)

        # 2. Respuestas genéricas/relleno
        generic_patterns = [
            "como asistente de ia",
            "como modelo de lenguaje",
            "no tengo la capacidad de",
            "estoy aqui para ayudarte",
            "¿en que puedo ayudarte",
            "¿como puedo ayudarte",
            "no dudes en preguntar",
            "si tienes alguna otra pregunta",
            "estoy a tu disposicion",
            "estaré encantado de ayudarte",
            "claro, con gusto",
            "por supuesto, con mucho gusto",
        ]
        has_generic = sum(1 for p in generic_patterns if p in resp_lower)
        if has_generic >= 2:
            # Demasiadas frases genéricas — regenerar
            if self.show_thinking:
                print(f"  [QualityGuard: {has_generic} frases genéricas detectadas — regenerando]")
            self.memory.short_term.add("assistant", response)
            self.memory.short_term.add("user",
                f"[SISTEMA: Tu respuesta usa frases genéricas de chatbot. "
                f"Eres Genesis, no un asistente corporativo. "
                f"Responde de forma directa, específica y con personalidad. "
                f"NO uses frases como 'estoy aqui para ayudarte' ni '¿como puedo ayudarte?'. "
                f"Responde la pregunta original: '{user_input[:200]}']"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.7)

        # 3. Contradición: dice "puedo" y "no puedo" sobre lo mismo
        can_do = any(w in resp_lower for w in ["puedo hacerlo", "si puedo", "soy capaz", "tengo la capacidad"])
        cant_do = any(w in resp_lower for w in ["no puedo", "no soy capaz", "fuera de mis capacidades", "no tengo la capacidad"])
        if can_do and cant_do:
            if self.show_thinking:
                print(f"  [QualityGuard: contradicción detectada (puedo + no puedo) — regenerando]")
            self.memory.short_term.add("assistant",
                "[Tu respuesta anterior se contradijo — dijiste que podías y no podías hacer lo mismo]")
            self.memory.short_term.add("user",
                f"[SISTEMA: COHERENCIA — NO te contradigas. "
                f"Si puedes hacer algo con herramientas, HAZLO. "
                f"Si genuinamente no puedes, di por qué y sugiere alternativa. "
                f"Pregunta original: '{user_input[:200]}']"
            )
            raw_msgs = self.memory.get_conversation_messages()
            messages = self.context_manager.fit_messages(
                raw_msgs, summary=self.summarizer.get_summary()
            )
            return self.brain.think(system_prompt, messages, temperature=0.5)

        return response

    def _clean_internal_messages(self):
        """
        Limpia mensajes internos del short-term memory que no son
        parte de la conversación real.

        Después del tool loop, la memoria se llena de mensajes como:
        - "[Sistema: herramienta ejecutada exitosamente]"
        - "[TAREA COMPLETADA — RESULTADO]: ..."
        - "[RESULTADO DE HERRAMIENTA python — paso 1/10]: ..."
        - "[ERROR EN CODIGO — CORRIGE Y REINTENTA]"

        Estos mensajes son útiles DURANTE el procesamiento pero no
        deberían persistir en la memoria de corto plazo. Los reemplazamos
        por versiones compactas.
        """
        st = self.memory.short_term
        if not st.messages:
            return

        internal_prefixes = [
            "[Sistema:", "[TAREA COMPLETADA", "[RESULTADO DE HERRAMIENTA",
            "[ERROR EN CODIGO", "[MAXIMO DE REINTENTOS", "[AUTO-BUILDER:",
            "[SISTEMA — OVERRIDE]", "[SISTEMA:",
        ]

        cleaned = []
        tool_results_summary = []

        for msg in st.messages:
            content = msg.get("content", "")
            is_internal = any(content.startswith(p) for p in internal_prefixes)

            if is_internal:
                # Extraer resumen compacto del resultado de herramienta
                if "RESULTADO" in content and "\n" in content:
                    # Mantener solo la primera línea del resultado
                    first_line = content.split("\n")[0][:150]
                    tool_results_summary.append(first_line)
                # No agregar el mensaje completo — se pierde
                continue
            else:
                cleaned.append(msg)

        # Si hubo tool results, agregar un resumen compacto
        if tool_results_summary and cleaned:
            summary = "[Resumen herramientas: " + "; ".join(tool_results_summary[-3:]) + "]"
            # Insertar antes del último mensaje si es del assistant
            if cleaned[-1].get("role") == "assistant":
                cleaned.insert(-1, {"role": "user", "content": summary})

        st.messages = cleaned

    def _clean_trailing_filler(self, response: str) -> str:
        """
        Elimina preguntas/frases genéricas al final de la respuesta.

        El LLM tiende a agregar "¿Quieres que te ayude con algo más?" o
        "¿Necesitas algo más?" al final, lo cual es robotico y prohibido
        por las CORE_RULES. Este método las limpia.
        """
        import re

        # Patrones de trailing filler (al final de la respuesta)
        trailing_patterns = [
            r'\n*¿(?:Quieres|Necesitas|Deseas|Te gustaría|Hay algo más).*?\?$',
            r'\n*¿(?:En qué|Cómo|Como) (?:más )?(?:puedo|te puedo) (?:ayudarte|ayudar|asistirte).*?\?$',
            r'\n*(?:Si necesitas|Si quieres|No dudes en) (?:algo más|preguntar|consultarme).*$',
            r'\n*(?:Estoy (?:aquí|a tu disposición|disponible) (?:para|si)).*$',
            r'\n*¿(?:Algo más|Algo otro|Otra cosa).*?\?$',
        ]

        cleaned = response.rstrip()
        for pattern in trailing_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE).rstrip()

        # Solo limpiar si no eliminamos demasiado (>70% del contenido)
        if len(cleaned) > len(response) * 0.3 and len(cleaned) > 20:
            return cleaned
        return response

    @staticmethod
    def _learn_app(filepath: str, current_map: dict, name: str, target: str):
        """Aprende una app/URL para la proxima vez que el usuario la pida."""
        try:
            current_map[name] = target
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(current_map, f, ensure_ascii=False, indent=2)
        except (OSError, TypeError, ValueError):
            pass

    def _discover_installed_app(self, query: str) -> str:
        """
        Busca un programa instalado escaneando los shortcuts del Menú Inicio.
        Retorna la ruta al .lnk/.url si encuentra match, o None.
        Cache se refresca cada 5 minutos para detectar nuevas instalaciones.
        Escanea tanto .lnk (apps normales) como .url (juegos Steam, etc).
        """
        import glob as _glob
        import time as _time

        # Refrescar cache cada 5 minutos o si no existe
        now = _time.time()
        if GenesisToolsMixin._installed_apps_cache is None or (now - GenesisToolsMixin._installed_apps_cache_time) > 300:
            GenesisToolsMixin._installed_apps_cache = {}
            GenesisToolsMixin._installed_apps_cache_time = now
            skip_words = ['uninstall', 'readme', 'sample', 'reference', 'license',
                          'help', 'release notes', 'documentation', 'manual',
                          'module docs', 'desinstala', 'faq', 'homepage',
                          'website', 'documentation']
            start_menu_dirs = [
                os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs'),
                os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
            ]
            for sdir in start_menu_dirs:
                try:
                    # Escanear .lnk (apps normales) y .url (juegos Steam, etc.)
                    for ext in ('*.lnk', '*.url'):
                        for shortcut_path in _glob.glob(os.path.join(sdir, '**', ext), recursive=True):
                            name = os.path.splitext(os.path.basename(shortcut_path))[0]
                            name_lower = name.lower()
                            if any(s in name_lower for s in skip_words):
                                continue
                            # Guardar con nombre en lowercase como clave
                            if name_lower not in GenesisToolsMixin._installed_apps_cache:
                                GenesisToolsMixin._installed_apps_cache[name_lower] = shortcut_path
                except OSError:
                    pass

        cache = GenesisToolsMixin._installed_apps_cache
        query = query.strip().lower()

        # 1. Match exacto
        if query in cache:
            return cache[query]

        # 2. Match parcial: query contenido en nombre o viceversa
        # Priorizar matches más cortos (más específicos)
        candidates = []
        for name, path in cache.items():
            if query in name or name in query:
                candidates.append((name, path))
            elif query.replace(" ", "") in name.replace(" ", ""):
                candidates.append((name, path))

        if candidates:
            # Preferir match más cercano en longitud al query
            candidates.sort(key=lambda x: abs(len(x[0]) - len(query)))
            return candidates[0][1]

        return None

    def _auto_detect_tool(self, user_input: str) -> str:
        """
        Auto-detecta si el usuario pide algo del sistema y ejecuta
        la herramienta correspondiente sin depender del LLM.
        Retorna el resultado o cadena vacia si no aplica.
        """
        inp = user_input.lower().strip()
        import re as _re

        # --- Capacidades de Genesis (voces, que puedes hacer, etc.) ---
        # NOTA: Estas secciones no requieren imports pesados, van primero para respuesta instantánea
        cap_keywords = ["cuantas voces", "cuántas voces", "que voces", "qué voces",
                        "cambiar la voz", "cambiar voz", "seleccionar voz",
                        "voces tienes", "voces tenes", "voces disponibles",
                        "una unica voz", "única voz", "una sola voz",
                        "solo una voz", "solo tienes una", "solo tenes una",
                        "no tienes voz", "no tenes voz", "cuantas voces",
                        "las voces", "tus voces", "elegir voz"]
        if any(k in inp for k in cap_keywords):
            return ("🎙️ VOCES DISPONIBLES\n\n"
                    "Tengo acceso a TODAS las voces instaladas en tu sistema "
                    "(actualmente ~22 voces en 5+ idiomas, incluyendo 5 en español).\n\n"
                    "Para cambiar la voz:\n"
                    "  1. Hacé click en el icono 🎙️ en la barra superior\n"
                    "  2. Se abre el panel con todas las voces agrupadas por idioma\n"
                    "  3. Probá cada voz con el botón ▶ Test\n"
                    "  4. Ajustá velocidad (0.5x - 2.0x) y tono (0.5 - 1.5)\n"
                    "  5. La voz seleccionada se guarda permanentemente\n\n"
                    "El TTS se activa con el botón TTS en la barra, o automáticamente al hablar por voz.")

        cap_general = ["que puedes hacer", "qué puedes hacer", "que podes hacer", "qué podés hacer",
                       "cuales son tus capacidades", "que capacidades", "que sabes hacer",
                       "para que sirves", "que funciones tienes", "tus habilidades"]
        if any(k in inp for k in cap_general):
            return ("🧠 CAPACIDADES DE GENESIS v5.7 — JARVIS Intelligence\n\n"
                    "▸ 🗣️ VOZ: Hablarme por micrófono (STT) y responder con audio (TTS) — 22 voces\n"
                    "▸ 🌐 INTERNET: Buscar en la web, leer páginas, investigar temas\n"
                    "▸ 📄 DOCUMENTOS: Procesar PDF, DOCX, XLSX, CSV, TXT — resúmenes y extracción\n"
                    "▸ 📂 ARCHIVOS: Buscar, listar, organizar, mover, eliminar archivos\n"
                    "▸ 💻 SISTEMA: Info real de hardware (CPU, RAM, GPU, disco)\n"
                    "▸ 🚀 APPS: Abrir cualquier programa instalado (143 detectados automáticamente)\n"
                    "▸ 🌍 WEBS: Abrir sitios web (50+ mapeados + descubrimiento automático)\n"
                    "▸ 🐍 CÓDIGO: Crear y ejecutar scripts Python, proyectos completos\n"
                    "▸ 📋 PORTAPAPELES: Historial, búsqueda, monitoreo automático\n"
                    "▸ 📸 CAPTURAS: Tomar screenshots del escritorio\n"
                    "▸ 🔧 PROCESOS: Listar y administrar procesos del sistema\n"
                    "▸ 🗑️ PAPELERA: Ver y restaurar archivos eliminados\n"
                    "▸ 📝 NOTAS: Sistema de notas rápidas persistentes (nota: tu texto)\n"
                    "▸ ⏰ RECORDATORIOS: Temporizadores con notificación desktop\n"
                    "▸ 📶 RED: Estado de conexión, WiFi, ping, velocidad\n"
                    "▸ 🧹 MANTENIMIENTO: Limpiar temporales, DNS, ver uptime\n"
                    "▸ 🔤 TEXTO: Mayúsculas, base64, hash, contar palabras, extraer emails/URLs\n"
                    "▸ 🔄 UNIDADES: Convertir distancia, peso, temperatura, datos, tiempo\n"
                    "▸ 🍅 POMODORO: Timer de productividad con ciclos trabajo/descanso\n"
                    "▸ 🪟 VENTANAS: Mover, snap, tile, maximizar, minimizar ventanas por voz\n"
                    "▸ 🔍 LAUNCHER: Búsqueda unificada en apps, archivos, notas, clipboard\n"
                    "▸ ☀️ BRIEFING: Resumen diario del sistema, notas, motivación\n"
                    "▸ ⚡ MACROS: Grabar y ejecutar secuencias de comandos\n"
                    "▸ 🧬 AUTO-EVOLUCIÓN: Aprender, mutar, evolucionar autónomamente")

        # --- Fecha, Hora, Datos basicos del sistema (respuesta instantanea) ---
        import datetime as _dt
        _now = _dt.datetime.now()

        time_keywords = ["que hora es", "qué hora es", "hora actual", "dime la hora",
                         "que hora tenemos", "hora es"]
        if any(k in inp for k in time_keywords):
            return f"🕐 Son las **{_now.strftime('%H:%M:%S')}** del {_now.strftime('%d/%m/%Y')}"

        date_keywords = ["que dia es", "qué día es", "que fecha", "qué fecha",
                         "fecha actual", "fecha de hoy", "dia de hoy", "día de hoy",
                         "dame la fecha", "dime la fecha", "en que fecha",
                         "que dia estamos", "qué día estamos", "a cuanto estamos"]
        if any(k in inp for k in date_keywords):
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                     "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            d = _now
            return (f"📅 **{dias[d.weekday()]} {d.day} de {meses[d.month]} de {d.year}**\n"
                    f"Hora: {d.strftime('%H:%M:%S')}")

        user_keywords = ["mi nombre de usuario", "mi usuario", "nombre de usuario",
                         "mi user", "mi username", "quien soy", "quién soy",
                         "como me llamo", "cómo me llamo", "mi nombre"]
        if any(k in inp for k in user_keywords):
            import os as _os
            username = _os.getenv("USERNAME", _os.getenv("USER", "desconocido"))
            hostname = _os.getenv("COMPUTERNAME", "desconocido")
            return (f"👤 **Usuario**: {username}\n"
                    f"💻 **Equipo**: {hostname}\n"
                    f"📁 **Home**: C:/Users/{username}")

        ip_keywords = ["mi ip", "cual es mi ip", "cuál es mi ip", "mi direccion ip",
                       "mi dirección ip", "ip local", "ip publica", "ip pública"]
        if any(k in inp for k in ip_keywords):
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except OSError:
                local_ip = "No disponible"
            hostname = socket.gethostname()
            result = f"🌐 **IP Local**: {local_ip}\n💻 **Hostname**: {hostname}"
            # Intentar obtener IP publica
            if "publica" in inp or "pública" in inp or "public" in inp:
                try:
                    import urllib.request
                    pub_ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
                    result += f"\n🌍 **IP Pública**: {pub_ip}"
                except (OSError, ValueError):
                    result += "\n🌍 **IP Pública**: No se pudo obtener"
            return result

        # --- Calculadora ---
        # Detectar expresiones matematicas simples
        math_keywords = ["cuanto es", "cuánto es", "calcula", "calculame", "calculá",
                         "resultado de", "cuanto da", "cuánto da"]
        if any(k in inp for k in math_keywords):
            # Extraer la expresion
            expr = inp
            for mk in math_keywords:
                if mk in expr:
                    expr = expr.split(mk, 1)[-1].strip()
                    break
            # Limpiar texto a expresion matematica
            expr = (expr.replace("x", "*").replace("×", "*").replace("÷", "/")
                    .replace("al cuadrado", "**2").replace("al cubo", "**3")
                    .replace("elevado a", "**").replace("^", "**")
                    .replace("raiz cuadrada de", "math.sqrt(").replace("raíz cuadrada de", "math.sqrt(")
                    .replace("por ciento de", "/100*").replace("% de", "/100*")
                    .replace(",", ".").strip().rstrip("?!."))
            # Solo permitir caracteres seguros
            import re as _re2
            if _re2.match(r'^[\d\s\+\-\*/\.\(\)math\.sqrtpiee]+$', expr.replace("math.sqrt(", "").replace(")", "")):
                try:
                    import math
                    # Cerrar parentesis abiertos
                    open_parens = expr.count("(") - expr.count(")")
                    if open_parens > 0:
                        expr += ")" * open_parens
                    result = eval(expr)
                    if isinstance(result, float):
                        # Formatear bonito
                        if result == int(result):
                            result = int(result)
                        else:
                            result = round(result, 6)
                    return f"🔢 **{expr}** = **{result}**"
                except (SyntaxError, NameError, TypeError, ValueError, ArithmeticError):
                    pass  # No es una expresion valida, continuar al LLM

        # --- Identidad de Genesis ---
        identity_keywords = ["que modelo eres", "qué modelo eres", "como te llamas",
                             "cómo te llamas", "que eres", "qué eres", "tu nombre",
                             "que ia eres", "qué ia eres", "eres chatgpt", "eres gpt",
                             "eres gemini", "eres siri", "eres alexa", "eres cortana"]
        if any(k in inp for k in identity_keywords):
            from config import LLM_PROVIDER, LLM_MODELS, GENESIS_VERSION
            model = LLM_MODELS.get(LLM_PROVIDER, "desconocido")
            provider_names = {
                "ollama": "Ollama (modelo local)",
                "gemini": "Google Gemini API",
                "openai": "OpenAI API",
                "anthropic": "Anthropic API",
            }
            provider_display = provider_names.get(LLM_PROVIDER, LLM_PROVIDER)
            return (f"🧬 Soy **Genesis v{GENESIS_VERSION}** — IA autónoma de escritorio.\n\n"
                    f"▸ Motor actual: **{model}** via {provider_display}\n"
                    f"▸ Corro 100% en tu máquina (Windows 11 Pro)\n"
                    f"▸ Tengo acceso real a tu sistema: archivos, apps, hardware, internet\n"
                    f"▸ 22 voces TTS, STT por micrófono, memoria persistente\n"
                    f"▸ Creado para ser un asistente funcional sin fabulación")

        # --- Contar archivos / tamano de carpeta ---
        count_keywords = ["cuantos archivos", "cuántos archivos", "cuantas carpetas",
                          "cuántas carpetas", "cantidad de archivos", "numero de archivos",
                          "cuantos elementos", "cuántos elementos"]
        size_keywords = ["cuanto pesa", "cuánto pesa", "cuanto ocupa", "cuánto ocupa",
                         "peso de la carpeta", "tamano de la carpeta", "tamaño de la carpeta",
                         "peso de ", "size de "]
        if any(k in inp for k in count_keywords + size_keywords):
            is_size = any(k in inp for k in size_keywords)
            # Extraer la carpeta mencionada
            _folder_map = {
                "escritorio": "C:/Users/Lexus/Desktop",
                "desktop": "C:/Users/Lexus/Desktop",
                "descargas": "C:/Users/Lexus/Downloads",
                "downloads": "C:/Users/Lexus/Downloads",
                "documentos": "C:/Users/Lexus/Documents",
                "documents": "C:/Users/Lexus/Documents",
                "genesis": os.path.dirname(os.path.abspath(__file__)),
            }
            # Detectar carpeta por nombre en la query
            target_dir = None
            for fname, fpath in _folder_map.items():
                if fname in inp:
                    target_dir = fpath
                    break
            if not target_dir:
                # Intentar con ruta
                _path_m = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
                if _path_m:
                    target_dir = _path_m.group(0)
            if target_dir and os.path.isdir(target_dir):
                try:
                    if is_size:
                        total = 0
                        file_count = 0
                        dir_count = 0
                        for dirpath, dirnames, filenames in os.walk(target_dir):
                            dir_count += len(dirnames)
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                try:
                                    total += os.path.getsize(fp)
                                    file_count += 1
                                except OSError:
                                    pass
                        # Formatear tamano
                        if total >= 1024**3:
                            size_str = f"{total/1024**3:.2f} GB"
                        elif total >= 1024**2:
                            size_str = f"{total/1024**2:.1f} MB"
                        elif total >= 1024:
                            size_str = f"{total/1024:.0f} KB"
                        else:
                            size_str = f"{total} bytes"
                        return (f"📂 **{os.path.basename(target_dir)}**\n"
                                f"  Peso total: **{size_str}**\n"
                                f"  Archivos: {file_count}\n"
                                f"  Subcarpetas: {dir_count}")
                    else:
                        items = os.listdir(target_dir)
                        files = [i for i in items if os.path.isfile(os.path.join(target_dir, i))]
                        dirs = [i for i in items if os.path.isdir(os.path.join(target_dir, i))]
                        return (f"📂 **{os.path.basename(target_dir)}**\n"
                                f"  Archivos: **{len(files)}**\n"
                                f"  Carpetas: **{len(dirs)}**\n"
                                f"  Total: **{len(items)}** elementos")
                except PermissionError:
                    return f"❌ Sin permisos para acceder a: {target_dir}"

        # --- Imports de herramientas (lazy, se cargan solo cuando se necesitan) ---
        from core.device_tools import (
            file_manager, file_searcher, file_organizer,
            disk_analyzer, duplicate_finder, process_manager,
            clipboard_manager, screen_capture, app_launcher,
        )
        from core.tools import FileTools, SystemInfoTool

        # --- Listar archivos ---
        list_keywords = ["lista", "muestra", "que hay en", "archivos en", "que tiene",
                         "contenido de", "ver carpeta", "mostrar archivos", "que archivos"]
        path_keywords = {
            "escritorio": "C:/Users/Lexus/Desktop",
            "desktop": "C:/Users/Lexus/Desktop",
            "descargas": "C:/Users/Lexus/Downloads",
            "downloads": "C:/Users/Lexus/Downloads",
            "documentos": "C:/Users/Lexus/Documents",
            "documents": "C:/Users/Lexus/Documents",
            "imagenes": "C:/Users/Lexus/Pictures",
            "pictures": "C:/Users/Lexus/Pictures",
            "musica": "C:/Users/Lexus/Music",
            "videos": "C:/Users/Lexus/Videos",
        }

        if any(k in inp for k in list_keywords):
            target_path = None
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    target_path = path
                    break
            # Detectar ruta explicita
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                target_path = path_match.group(0)
            if target_path:
                return FileTools.list_directory(target_path)

        # --- Programas de inicio (antes de sistema para evitar false match) ---
        startup_keywords = ["programas de inicio", "inicio de windows", "startup",
                           "que se ejecuta al inicio", "arranque", "ejecutan al inicio"]
        if any(k in inp for k in startup_keywords):
            from core.device_tools import startup_manager as sm
            return sm.list_startup()

        # --- Info del sistema ---
        sys_keywords = ["mi sistema", "mi cpu", " ram ", "mi memoria", "mi gpu",
                        "mi disco", "mi hardware",
                        "que computadora", "que pc", "especificaciones", "specs",
                        "info del sistema", "informacion del sistema",
                        "caracteristicas del sistema", "características del sistema",
                        "del sistema operativo", "datos del sistema",
                        "que procesador", "que tarjeta", "que grafica",
                        "componentes del", "mi equipo", "mi computadora", "mi pc",
                        "mi procesador", "mi tarjeta", "info de hardware",
                        "dime de mi sistema", "dime del sistema", "cuanta ram",
                        "cuanto disco", "cuantos nucleos",
                        "system info", "hardware info",
                        # Variantes de "dame datos del sistema / actualiza datos"
                        "datos sobre mi sistema", "datos de mi sistema",
                        "datos actuales", "datos actualizados", "datos reales",
                        "actualiza los datos", "actualiza datos", "actualiza mi sistema",
                        "datos del equipo", "datos del pc", "datos de mi pc",
                        "resumen del sistema", "resumen de mi sistema",
                        "analiza mi sistema", "analizar mi sistema", "escanea mi sistema",
                        "obten datos", "obtener datos", "obtengas datos",
                        "sobre mi sistema", "de mi sistema"]
        if any(k in inp for k in sys_keywords):
            if "gpu" in inp or "grafica" in inp or "tarjeta" in inp:
                return SystemInfoTool.get_gpu_status()
            if "disco" in inp or "almacenamiento" in inp or "espacio" in inp:
                return disk_analyzer.analyze()
            return SystemInfoTool.get_system_info()

        # --- Buscar archivos ---
        search_keywords = ["busca archivo", "encuentra archivo", "buscar archivo",
                           "donde esta el archivo", "donde estan los archivos",
                           "encontrar archivo", "encontra archivo",
                           "busca archivos de ", "busca documentos de ",
                           "busca archivos sobre ", "busca documentos sobre ",
                           "busca en mis archivos ", "busca en mi pc ",
                           "busca en mi computadora ", "tenes algo de ",
                           "tenes archivos de ", "hay archivos de ",
                           "hay algo de ", "hay algo sobre "]
        # "busca X" genérico (solo si NO es busca web: "busca en internet/google/web")
        web_search_pattern = _re.search(r'\bbusca\b\s+(en\s+)?(internet|google|la\s+web|online|web)', inp)
        is_generic_search = (inp.startswith("busca ") or inp.startswith("buscá ") or
                             inp.startswith("buscame ") or inp.startswith("buscá ")) and not web_search_pattern

        if any(k in inp for k in search_keywords) or is_generic_search:
            # Extraer lo que buscan
            query = ""
            for kw in sorted(search_keywords, key=len, reverse=True):
                if kw in inp:
                    query = inp.split(kw)[-1].strip()
                    break
            if not query and is_generic_search:
                for prefix in ["buscame ", "buscá ", "busca "]:
                    if inp.startswith(prefix):
                        query = inp[len(prefix):].strip()
                        break
            # Limpiar preposiciones
            for prep in ["el ", "la ", "los ", "las ", "un ", "una ",
                         "mis ", "mi ", "de ", "sobre ", "llamado ", "llamada "]:
                if query.startswith(prep):
                    query = query[len(prep):]
            query = query.strip().rstrip(".,;!?")
            if query and len(query) >= 2:
                return file_searcher.search(query)

        # --- Organizar ---
        organize_keywords = ["organiza", "ordena", "clasifica", "organizar"]
        if any(k in inp for k in organize_keywords):
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    # Primero simular
                    return file_organizer.organize(path, dry_run=True)
            return ""

        # --- Procesos ---
        process_keywords = ["procesos", "que esta corriendo", "que esta ejecutando",
                           "programas abiertos", "apps abiertas", "tareas",
                           "que programas hay", "que apps hay", "que aplicaciones"]
        if any(k in inp for k in process_keywords):
            return process_manager.list_processes()

        # --- Cerrar proceso/app ---
        close_keywords = ["cierra ", "cerrar ", "cerrá ", "cerrame ", "ciérralo",
                          "mata ", "matá ", "termina ", "terminá ",
                          "cierra el ", "cierra la ", "cierra lo "]
        if any(inp.startswith(k) for k in close_keywords):
            # Extraer nombre del proceso
            proc_target = inp
            for kw in sorted(close_keywords, key=len, reverse=True):
                if proc_target.startswith(kw):
                    proc_target = proc_target[len(kw):].strip()
                    break
            # Limpiar prefijos comunes
            for prep in ["el ", "la ", "lo ", "programa ", "aplicación ", "aplicacion ",
                          "app ", "juego ", "proceso "]:
                if proc_target.startswith(prep):
                    proc_target = proc_target[len(prep):]
            proc_target = proc_target.strip().rstrip(".,;!?")
            if proc_target and len(proc_target) >= 2:
                # Mapear nombres comunes a nombres de proceso
                proc_map = {
                    "chrome": "chrome.exe", "google chrome": "chrome.exe",
                    "firefox": "firefox.exe", "edge": "msedge.exe",
                    "brave": "brave.exe", "opera": "opera.exe",
                    "discord": "Discord.exe", "telegram": "Telegram.exe",
                    "spotify": "Spotify.exe", "steam": "steam.exe",
                    "excel": "EXCEL.EXE", "word": "WINWORD.EXE",
                    "powerpoint": "POWERPNT.EXE", "outlook": "OUTLOOK.EXE",
                    "notepad": "notepad.exe", "notepad++": "notepad++.exe",
                    "obs": "obs64.exe", "obs studio": "obs64.exe",
                    "vlc": "vlc.exe", "vscode": "Code.exe",
                    "visual studio code": "Code.exe",
                    "dota 2": "dota2.exe", "dota": "dota2.exe",
                    "valorant": "VALORANT.exe", "league of legends": "LeagueClient.exe",
                    "fortnite": "FortniteClient-Win64-Shipping.exe",
                    "minecraft": "javaw.exe",
                }
                # Soportar multi-target: "cierra excel y word" → ["excel", "word"]
                targets = [t.strip() for t in _re.split(r'\s+y\s+|\s*,\s*', proc_target) if t.strip()]
                closed = []
                failed = []
                for t in targets:
                    exe_name = proc_map.get(t.lower(), t)
                    # Solo agregar .exe si no lo tiene ya
                    if not exe_name.lower().endswith(".exe"):
                        exe_name = exe_name + ".exe"
                    result = process_manager.kill_process(exe_name)
                    # Contar si cerró o no
                    display_name = t.capitalize()
                    if "correcto" in result.lower() or "terminó" in result.lower() or "termin" in result.lower():
                        closed.append(display_name)
                    elif "error" in result.lower() or "no se encontr" in result.lower():
                        failed.append(display_name)
                    else:
                        closed.append(display_name)
                # Respuesta limpia
                parts = []
                if closed:
                    parts.append(f"✅ {'Cerrado' if len(closed) == 1 else 'Cerrados'}: {', '.join(closed)}")
                if failed:
                    parts.append(f"❌ No encontrado: {', '.join(failed)}")
                return "\n".join(parts) if parts else "No se pudo cerrar ningún programa."

        # --- Verificar si app está abierta ---
        check_running_patterns = [
            r"(?:esta|está)\s+(?:abierto|abierta|corriendo|ejecutando|ejecutándose|activo|activa)\s+(.+)",
            r"(?:se\s+)?(?:esta|está)\s+(?:ejecutando|corriendo)\s+(.+)",
            r"(?:tengo|hay)\s+(?:abierto|abierta)\s+(.+)",
            r"(.+?)\s+(?:esta|está)\s+(?:abierto|abierta|corriendo|ejecutando)",
        ]
        for pattern in check_running_patterns:
            match = _re.search(pattern, inp)
            if match:
                check_name = match.group(1).strip().rstrip(".,;!? ")
                # Limpiar
                for prep in ["el ", "la ", "lo "]:
                    if check_name.startswith(prep):
                        check_name = check_name[len(prep):]
                if check_name and len(check_name) >= 2:
                    # Buscar en procesos reales
                    import subprocess
                    try:
                        result = subprocess.run(
                            ["tasklist", "/fo", "csv", "/nh"],
                            capture_output=True, text=True, timeout=10
                        )
                        procs = result.stdout.lower()
                        check_lower = check_name.lower().replace(" ", "")
                        # Buscar coincidencias
                        found = []
                        for line in procs.split("\n"):
                            parts = line.strip().strip('"').split('","')
                            if parts and len(parts) >= 2:
                                pname = parts[0].strip('"').lower()
                                if check_lower in pname or pname.replace(".exe", "").startswith(check_lower[:4]):
                                    found.append(parts[0].strip('"'))
                        if found:
                            unique = list(set(found))
                            return f"✅ Sí, '{check_name}' está corriendo.\nProcesos encontrados: {', '.join(unique[:5])}"
                        else:
                            return f"❌ No, '{check_name}' NO está corriendo actualmente."
                    except Exception as e:
                        return f"Error al verificar procesos: {e}"

        # --- Portapapeles ---
        clip_keywords = ["portapapeles", "clipboard", "que copie", "que tengo copiado"]
        if any(k in inp for k in clip_keywords):
            return clipboard_manager.read()

        # --- Captura ---
        capture_keywords = ["captura", "screenshot", "pantallazo", "foto de pantalla"]
        if any(k in inp for k in capture_keywords):
            return screen_capture.capture()

        # --- Papelera de reciclaje ---
        from core.device_tools import recycle_bin
        recycle_keywords = ["papelera", "reciclaje", "recycle", "eliminados recientemente"]
        if any(k in inp for k in recycle_keywords):
            if any(w in inp for w in ["vaciar", "limpiar", "vacia", "limpia"]):
                return recycle_bin.empty()
            return recycle_bin.list_items()

        # --- Restaurar de papelera ---
        restore_keywords = ["restaura", "recupera", "restaurar", "recuperar"]
        if any(k in inp for k in restore_keywords):
            from core.device_tools import recycle_bin as rb
            # Extraer nombre del archivo a restaurar
            # Buscar nombre entre comillas o después del keyword
            quoted = _re.search(r'["\'](.+?)["\']', user_input)
            if quoted:
                return rb.restore(quoted.group(1))
            # Extraer la última palabra significativa
            for kw in restore_keywords:
                if kw in inp:
                    rest = inp.split(kw)[-1].strip()
                    # Limpiar preposiciones
                    for prep in ["el ", "la ", "lo ", "los ", "las ", "al ", "del "]:
                        if rest.startswith(prep):
                            rest = rest[len(prep):]
                    if rest and len(rest) > 1:
                        return rb.restore(rest.strip())
            return "[ERROR] Especifica que archivo restaurar. Ejemplo: 'restaura GCC'"

        # --- Duplicados ---
        dup_keywords = ["duplicados", "archivos repetidos", "archivos duplicados"]
        if any(k in inp for k in dup_keywords):
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    return duplicate_finder.find(path)
            return duplicate_finder.find("C:/Users/Lexus")

        # --- Helper: resolver nombre de carpeta a ruta ---
        def _resolve_folder(name: str) -> str:
            """Resuelve un nombre de carpeta a su ruta real. Retorna path o None."""
            _genesis_dir = os.path.dirname(os.path.abspath(__file__))
            folder_map = {
                # Carpetas del usuario
                "documentos": "C:/Users/Lexus/Documents",
                "documents": "C:/Users/Lexus/Documents",
                "mis documentos": "C:/Users/Lexus/Documents",
                "escritorio": "C:/Users/Lexus/Desktop",
                "desktop": "C:/Users/Lexus/Desktop",
                "mi escritorio": "C:/Users/Lexus/Desktop",
                "descargas": "C:/Users/Lexus/Downloads",
                "downloads": "C:/Users/Lexus/Downloads",
                "mis descargas": "C:/Users/Lexus/Downloads",
                "imagenes": "C:/Users/Lexus/Pictures",
                "pictures": "C:/Users/Lexus/Pictures",
                "fotos": "C:/Users/Lexus/Pictures",
                "mis imagenes": "C:/Users/Lexus/Pictures",
                "musica": "C:/Users/Lexus/Music",
                "music": "C:/Users/Lexus/Music",
                "mi musica": "C:/Users/Lexus/Music",
                "videos": "C:/Users/Lexus/Videos",
                "mis videos": "C:/Users/Lexus/Videos",
                # Carpetas del sistema
                "disco c": "C:/", "disco d": "D:/", "disco f": "F:/",
                "unidad c": "C:/", "c:": "C:/", "d:": "D:/", "f:": "F:/",
                "home": "C:/Users/Lexus",
                "mi carpeta": "C:/Users/Lexus",
                "mi usuario": "C:/Users/Lexus",
                "perfil": "C:/Users/Lexus",
                "appdata": "C:/Users/Lexus/AppData",
                "temp": "C:/Users/Lexus/AppData/Local/Temp",
                "temporal": "C:/Users/Lexus/AppData/Local/Temp",
                # Carpetas del proyecto
                "genesis": _genesis_dir,
                "mi proyecto": _genesis_dir,
                "proyecto genesis": _genesis_dir,
                # Programas
                "archivos de programa": "C:/Program Files",
                "program files": "C:/Program Files",
            }
            # Limpiar prefijos
            clean = name.lower().strip()
            for prefix in ["carpeta de ", "carpeta ", "folder de ", "folder ",
                           "directorio de ", "directorio "]:
                if clean.startswith(prefix):
                    clean = clean[len(prefix):]
            # 1. Buscar en mapa
            path = folder_map.get(clean) or folder_map.get(name.lower())
            if path and os.path.exists(path):
                return path
            # 2. Ruta directa (C:/...)
            if _re.match(r'^[A-Za-z]:[/\\]', name) and os.path.exists(name):
                return name
            # 3. Busqueda inteligente: buscar en Desktop, Documents, discos
            search_dirs = [
                "C:/Users/Lexus/Desktop", "C:/Users/Lexus/Documents",
                "C:/Users/Lexus/Downloads", "C:/Users/Lexus",
                "F:/programas", "F:/programas/playground",
                "D:/",
            ]
            for sd in search_dirs:
                try:
                    if not os.path.isdir(sd):
                        continue
                    for item in os.listdir(sd):
                        if item.lower() == clean or item.lower().replace(" ", "") == clean.replace(" ", ""):
                            full = os.path.join(sd, item)
                            if os.path.isdir(full):
                                return full
                except OSError:
                    pass
            # 4. Busqueda fuzzy parcial
            for sd in search_dirs:
                try:
                    if not os.path.isdir(sd):
                        continue
                    for item in os.listdir(sd):
                        if clean in item.lower() and os.path.isdir(os.path.join(sd, item)):
                            return os.path.join(sd, item)
                except OSError:
                    pass
            return None

        def _list_folder_contents(path: str, max_items: int = 50) -> str:
            """Lista el contenido de una carpeta de forma legible."""
            try:
                items = sorted(os.listdir(path))
            except PermissionError:
                return f"[Sin permisos para listar {path}]"
            except Exception as e:
                return f"[Error listando {path}: {e}]"
            if not items:
                return f"Carpeta vacía: {path}"
            dirs = []
            files = []
            for item in items:
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    dirs.append(f"  📁 {item}/")
                else:
                    try:
                        size = os.path.getsize(full)
                        if size >= 1024 * 1024:
                            sz = f"{size / (1024*1024):.1f} MB"
                        elif size >= 1024:
                            sz = f"{size / 1024:.1f} KB"
                        else:
                            sz = f"{size} B"
                        files.append(f"  📄 {item} ({sz})")
                    except OSError:
                        files.append(f"  📄 {item}")
            total = len(dirs) + len(files)
            lines = [f"📂 {path}", f"   {len(dirs)} carpetas, {len(files)} archivos\n"]
            shown = (dirs + files)[:max_items]
            lines.extend(shown)
            if total > max_items:
                lines.append(f"\n  ... y {total - max_items} elementos más")
            return "\n".join(lines)

        # --- Mostrar contenido de carpeta ---
        content_keywords = ["muestra contenido", "muestrame contenido", "muestra el contenido",
                           "muestra lo que hay", "que hay en ", "que tiene ",
                           "lista contenido", "listar contenido", "muestra la carpeta",
                           "muestrame la carpeta", "muestra los archivos",
                           "que archivos hay", "que archivos tiene", "listame ",
                           "contenido de ", "archivos de ", "archivos en "]
        if any(k in inp for k in content_keywords):
            # Extraer nombre de carpeta
            rest = inp
            for kw in sorted(content_keywords, key=len, reverse=True):
                if kw in rest:
                    rest = rest.split(kw)[-1].strip()
                    break
            # Limpiar preposiciones
            for prep in ["el ", "la ", "lo ", "los ", "las ", "mi ", "mis ", "de ", "en "]:
                if rest.startswith(prep):
                    rest = rest[len(prep):]
            rest = rest.strip().rstrip(".,;!?")
            if rest:
                folder_path = _resolve_folder(rest)
                if folder_path:
                    return _list_folder_contents(folder_path)
                return f"No encontré una carpeta llamada '{rest}'. Intenta con el nombre exacto o la ruta completa."

        # --- Abrir ---
        open_keywords = ["abre ", "abrir ", "ejecuta ", "lanza ", "abri ",
                         "abrí ", "abrilo", "abrila", "abrelo", "abrela",
                         "abrime ", "abrame ",
                         # Reproducción / media → abren la app/web correspondiente
                         "reproduce ", "reproducir ", "reproducí ",
                         "pon musica ", "pon música ", "pone musica ", "pone música ",
                         "escuchar ", "escucha ", "poneme ",
                         "quiero ver ", "quiero escuchar ",
                         "play ", "inicia "]
        if any(inp.startswith(k) or f" {k}" in inp for k in open_keywords):
            # Extraer que abrir
            for kw in open_keywords:
                if kw in inp:
                    target = inp.split(kw)[-1].strip()
                    # Limpiar preposiciones al inicio
                    for prep in ["el ", "la ", "lo ", "los ", "las ", "un ", "una ", "mi "]:
                        if target.startswith(prep):
                            target = target[len(prep):]
                    # Limpiar sustantivos genéricos: "aplicación X", "juego X", "programa X"
                    for generic in ["aplicación ", "aplicacion ", "juego ", "programa ",
                                    "app ", "game ", "carpeta ", "folder ",
                                    # Descriptores: "navegador de chrome" → "chrome"
                                    "navegador de ", "navegador ", "browser ",
                                    "pagina de ", "página de ", "pagina web de ",
                                    "sitio de ", "sitio web de ", "sitio web ",
                                    # Media: "música en youtube" → "youtube"
                                    "musica en ", "música en ", "musica de ", "música de ",
                                    "video de ", "videos de ", "video en ", "videos en ",
                                    "algo en ", "algo de "]:
                        if target.lower().startswith(generic):
                            target = target[len(generic):]
                    # Limpiar preposición "de" residual: "de dota 2" → "dota 2"
                    if target.lower().startswith("de "):
                        target = target[3:]
                    if target.lower().startswith("en "):
                        target = target[3:]
                    target = target.strip().rstrip(".,;!?")
                    if not target or len(target) > 80:
                        break

                    # --- Carpetas y rutas locales ---
                    # Limpiar sufijos comunes que contaminan el target
                    show_content = False
                    for suffix in [" y muestra su contenido", " y muestra contenido",
                                   " y muestrame su contenido", " y listame",
                                   " y muestrame que tiene", " y dime que tiene",
                                   " en explorador de archivos", " en el explorador de archivos",
                                   " en explorador", " en el explorador", " en explorer",
                                   " en file explorer", " en archivos",
                                   " por favor", " porfa", " porfavor"]:
                        if target.lower().endswith(suffix):
                            target = target[:len(target)-len(suffix)].strip()
                            if "contenido" in suffix or "listame" in suffix or "que tiene" in suffix:
                                show_content = True
                            break

                    folder_path = _resolve_folder(target)
                    if folder_path:
                        # Abrir en Explorer
                        app_launcher.open(folder_path)
                        # Mostrar contenido en el chat
                        content = _list_folder_contents(folder_path)
                        return f"Abriendo carpeta en Explorer.\n\n{content}"

                    # Si tiene ruta valida (C:/ o similar), abrir directo
                    if _re.match(r'^[A-Za-z]:[/\\]', target):
                        return app_launcher.open(target)

                    # Detectar patron "en chrome X" / "en el navegador X"
                    browser_prefix = _re.match(r'^en\s+(?:el\s+)?(?:chrome|navegador|firefox|edge|brave)\s+(.+)', target, _re.IGNORECASE)
                    if browser_prefix:
                        target = browser_prefix.group(1).strip()

                    # Mapa de sitios web comunes → URLs
                    web_map = {
                        "netflix": "https://www.netflix.com",
                        "youtube": "https://www.youtube.com",
                        "youtube music": "https://music.youtube.com",
                        "youtube studio": "https://studio.youtube.com",
                        "youtube kids": "https://www.youtubekids.com",
                        "gmail": "https://mail.google.com",
                        "google": "https://www.google.com",
                        "google docs": "https://docs.google.com",
                        "google sheets": "https://sheets.google.com",
                        "google slides": "https://slides.google.com",
                        "google calendar": "https://calendar.google.com",
                        "google photos": "https://photos.google.com",
                        "google translate": "https://translate.google.com",
                        "traductor": "https://translate.google.com",
                        "twitter": "https://twitter.com", "x": "https://twitter.com",
                        "facebook": "https://www.facebook.com",
                        "instagram": "https://www.instagram.com",
                        "whatsapp web": "https://web.whatsapp.com",
                        "telegram web": "https://web.telegram.org",
                        "github": "https://github.com",
                        "reddit": "https://www.reddit.com",
                        "twitch": "https://www.twitch.tv",
                        "amazon": "https://www.amazon.com",
                        "mercadolibre": "https://www.mercadolibre.com.ar",
                        "mercado libre": "https://www.mercadolibre.com.ar",
                        "chatgpt": "https://chat.openai.com",
                        "claude": "https://claude.ai",
                        "maps": "https://maps.google.com", "google maps": "https://maps.google.com",
                        "drive": "https://drive.google.com", "google drive": "https://drive.google.com",
                        "linkedin": "https://www.linkedin.com",
                        "tiktok": "https://www.tiktok.com",
                        "disney": "https://www.disneyplus.com", "disney+": "https://www.disneyplus.com",
                        "disney plus": "https://www.disneyplus.com",
                        "hbo": "https://www.max.com", "hbo max": "https://www.max.com", "max": "https://www.max.com",
                        "prime video": "https://www.primevideo.com",
                        "amazon prime": "https://www.primevideo.com",
                        "spotify web": "https://open.spotify.com",
                        "crunchyroll": "https://www.crunchyroll.com",
                        "pinterest": "https://www.pinterest.com",
                        "notion": "https://www.notion.so",
                        "canva": "https://www.canva.com",
                        "figma": "https://www.figma.com",
                        "stackoverflow": "https://stackoverflow.com",
                        "stack overflow": "https://stackoverflow.com",
                    }

                    target_lower = target.lower()

                    # 1. Cargar mapa aprendido (persistent)
                    from config import BASE_DIR as _BASE_DIR
                    learned_map_path = os.path.join(str(_BASE_DIR), "data", "learned_apps.json")
                    learned_map = {}
                    try:
                        if os.path.exists(learned_map_path):
                            with open(learned_map_path, "r", encoding="utf-8") as _f:
                                learned_map = json.loads(_f.read())
                    except (OSError, json.JSONDecodeError, ValueError):
                        pass

                    # 2. Buscar en mapa aprendido primero
                    if target_lower in learned_map:
                        learned_entry = learned_map[target_lower]
                        if learned_entry.startswith("http"):
                            import webbrowser
                            webbrowser.open(learned_entry)
                            return f"Abriendo {target}: {learned_entry} (aprendido)"
                        else:
                            return app_launcher.open(learned_entry)

                    # 3. Buscar en web_map estático
                    web_url = web_map.get(target_lower, None)

                    # Match parcial: "youtube music app" → matchea "youtube music"
                    if not web_url:
                        sorted_keys = sorted(web_map.keys(), key=len, reverse=True)
                        for wk in sorted_keys:
                            if target_lower.startswith(wk) or target_lower == wk:
                                web_url = web_map[wk]
                                break

                    if web_url:
                        import webbrowser
                        webbrowser.open(web_url)
                        # Aprender para la proxima
                        self._learn_app(learned_map_path, learned_map, target_lower, web_url)
                        return f"Abriendo {target} en el navegador: {web_url}"

                    # 4. Si es una URL directa
                    if _re.match(r'^https?://', target, _re.IGNORECASE) or _re.match(r'^www\.', target, _re.IGNORECASE):
                        url = target if target.startswith("http") else f"https://{target}"
                        import webbrowser
                        webbrowser.open(url)
                        self._learn_app(learned_map_path, learned_map, target_lower, url)
                        return f"Abriendo: {url}"

                    # 5. Mapear nombres comunes a ejecutables de escritorio
                    # IMPORTANTE: estos mapeos son SUGERENCIAS para fallback.
                    # El flujo prioriza _discover_installed_app (Start Menu), que funciona
                    # aunque el exe no esté en PATH. app_map solo se usa si discovery falla.
                    app_map = {
                        # Navegadores
                        "chrome": "chrome", "google chrome": "chrome",
                        "navegador": "chrome", "navegador web": "chrome",
                        "firefox": "firefox", "mozilla": "firefox", "mozilla firefox": "firefox",
                        "edge": "msedge", "microsoft edge": "msedge",
                        "brave": "brave", "brave browser": "brave",
                        "opera": "opera", "opera gx": "opera gx",
                        # Explorador / archivos
                        "explorador": "explorer", "explorador de archivos": "explorer",
                        "archivos": "explorer", "file explorer": "explorer",
                        "mis archivos": "explorer", "mi pc": "explorer",
                        # Editores de texto básicos
                        "bloc de notas": "notepad", "notepad": "notepad", "notepad++": "notepad++",
                        "wordpad": "wordpad", "write": "wordpad",
                        # Calculadora
                        "calculadora": "calc", "calc": "calc", "calculator": "calc",
                        # Terminales
                        "cmd": "cmd", "terminal": "cmd", "consola": "cmd",
                        "simbolo del sistema": "cmd", "símbolo del sistema": "cmd",
                        "powershell": "powershell", "ps": "powershell",
                        "windows terminal": "wt", "wt": "wt",
                        # Paint
                        "paint": "mspaint", "mspaint": "mspaint", "dibujo": "mspaint",
                        # Configuración / control
                        "panel de control": "control", "control": "control",
                        "configuracion": "ms-settings:", "configuración": "ms-settings:",
                        "settings": "ms-settings:", "ajustes": "ms-settings:",
                        "configuracion de windows": "ms-settings:",
                        "configuración de windows": "ms-settings:",
                        # Sistema
                        "administrador de tareas": "taskmgr", "task manager": "taskmgr",
                        "monitor de recursos": "resmon",
                        "editor de registro": "regedit", "regedit": "regedit",
                        "msconfig": "msconfig", "configuracion del sistema": "msconfig",
                        # IDEs / desarrollo
                        "vscode": "code", "visual studio code": "code", "code": "code",
                        "vs code": "code",
                        "visual studio": "devenv", "git bash": "git-bash",
                        "pycharm": "pycharm", "intellij": "idea", "idea": "idea",
                        "android studio": "studio",
                        # Office
                        "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
                        "outlook": "outlook", "onenote": "onenote", "access": "msaccess",
                        "teams": "teams", "microsoft teams": "teams",
                        # Media / comunicación
                        "spotify": "spotify", "vlc": "vlc", "media player": "wmplayer",
                        "discord": "discord", "slack": "slack", "zoom": "zoom",
                        "steam": "steam", "epic games": "epicgameslauncher",
                        "telegram": "telegram", "telegram desktop": "telegram",
                        "whatsapp": "whatsapp", "whatsap": "whatsapp",
                        "signal": "signal",
                        # Streaming / creación
                        "obs": "obs64", "obs studio": "obs64", "obes": "obs64",
                        "streamlabs": "streamlabs obs",
                        # Utilidades
                        "7zip": "7zfm", "7-zip": "7zfm", "winrar": "winrar",
                        "git": "git", "docker": "docker desktop",
                    }
                    # Normalizar números en español del speech-to-text
                    _num_words = {"uno": "1", "dos": "2", "tres": "3", "cuatro": "4",
                                  "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
                                  "nueve": "9", "diez": "10"}
                    _normalized = target_lower
                    for word, digit in _num_words.items():
                        _normalized = _normalized.replace(word, digit)
                    # Intentar con nombre original y normalizado
                    mapped = app_map.get(target_lower, None) or app_map.get(_normalized, None)

                    # 6. DESCUBRIMIENTO AUTOMATICO: escanear Start Menu (prioridad sobre cmd /c start)
                    # Los .lnk/.url del Start Menu funcionan siempre, cmd /c start solo si está en PATH
                    discovered = self._discover_installed_app(target_lower)
                    if not discovered and _normalized != target_lower:
                        discovered = self._discover_installed_app(_normalized)
                    if not discovered and mapped:
                        discovered = self._discover_installed_app(mapped)
                    if discovered:
                        try:
                            # Si es .lnk, verificar que apunta a un .exe existente antes de lanzar
                            # (evita "falso éxito" cuando el shortcut está roto)
                            if discovered.lower().endswith('.lnk'):
                                resolved_exe = app_launcher.resolve_lnk_target(discovered)
                                if resolved_exe is None:
                                    # No pudimos resolver — intentar igual con os.startfile (Windows
                                    # suele manejar .lnk rotos con diálogo, no silencioso)
                                    pass
                                elif not os.path.exists(resolved_exe):
                                    # Shortcut roto — no intentar, caer al siguiente método
                                    discovered = None
                            if discovered:
                                os.startfile(discovered)
                                self._learn_app(learned_map_path, learned_map, target_lower, discovered)
                                app_name = os.path.splitext(os.path.basename(discovered))[0]
                                return f"Abriendo {app_name}"
                        except (OSError, FileNotFoundError):
                            pass  # Continuar con fallback

                    # 7. Fallback: cmd /c start (solo funciona para apps en PATH: notepad, calc, etc.)
                    if mapped:
                        self._learn_app(learned_map_path, learned_map, target_lower, mapped)
                        return app_launcher.open(mapped)

                    # 7. APRENDIZAJE: Si no lo conozco, intentar construir URL
                    # "twitch" → https://www.twitch.com, "notion" → https://www.notion.com
                    if len(target.split()) <= 3 and len(target) <= 30:
                        # Construir URL candidata: quitar espacios, usar .com
                        clean_name = target_lower.replace(" ", "")
                        candidate_url = f"https://www.{clean_name}.com"
                        # Verificar si la URL existe (HEAD request rapido)
                        try:
                            import urllib.request
                            req = urllib.request.Request(candidate_url, method='HEAD')
                            req.add_header('User-Agent', 'Mozilla/5.0')
                            resp = urllib.request.urlopen(req, timeout=3)
                            if resp.status < 400:
                                import webbrowser
                                webbrowser.open(candidate_url)
                                # Aprender para la proxima!
                                self._learn_app(learned_map_path, learned_map, target_lower, candidate_url)
                                return f"Abriendo {target}: {candidate_url} (descubierto y aprendido)"
                        except (OSError, ValueError):
                            pass

                        # Intentar sin www
                        candidate_url2 = f"https://{clean_name}.com"
                        try:
                            req = urllib.request.Request(candidate_url2, method='HEAD')
                            req.add_header('User-Agent', 'Mozilla/5.0')
                            resp = urllib.request.urlopen(req, timeout=3)
                            if resp.status < 400:
                                import webbrowser
                                webbrowser.open(candidate_url2)
                                self._learn_app(learned_map_path, learned_map, target_lower, candidate_url2)
                                return f"Abriendo {target}: {candidate_url2} (descubierto y aprendido)"
                        except (OSError, ValueError):
                            pass

                    # 8. No se pudo resolver — sugerir alternativas del cache de Start Menu
                    suggestions = []
                    try:
                        cache = GenesisToolsMixin._installed_apps_cache or {}
                        if cache:
                            import difflib as _difflib
                            # Buscar matches fuzzy (cutoff 0.5 = al menos 50% similar)
                            close = _difflib.get_close_matches(
                                target_lower, list(cache.keys()), n=5, cutoff=0.5
                            )
                            # También buscar substring matches (ej: "outlook" en "Microsoft Outlook")
                            for name in cache.keys():
                                if len(suggestions) >= 5:
                                    break
                                if target_lower in name and name not in close:
                                    close.append(name)
                            # Capitalizar para mostrar (usar nombre del archivo original)
                            for match in close[:5]:
                                path = cache.get(match, "")
                                if path:
                                    pretty = os.path.splitext(os.path.basename(path))[0]
                                    suggestions.append(pretty)
                    except Exception:
                        pass

                    if suggestions:
                        hints = ", ".join(f"'{s}'" for s in suggestions)
                        return (f"No encontré '{target}' exactamente. ¿Quisiste decir alguno de estos? "
                                f"{hints}. Decime el nombre correcto y lo abro.")
                    return (f"No encontré '{target}' como programa instalado, carpeta, ni sitio web. "
                            f"Intentá con el nombre exacto o decime más sobre qué querés abrir.")

        # --- Instalar paquetes ---
        install_keywords = ["instala ", "instalame ", "instalar ", "instalá ",
                            "pip install", "npm install", "agrega el paquete ",
                            "necesito instalar", "quiero instalar"]
        if any(k in inp for k in install_keywords):
            # Extraer nombre del paquete
            package = ""
            for kw in install_keywords:
                if kw in inp:
                    package = inp.split(kw)[-1].strip().rstrip(".,;!?")
                    break

            if package:
                import subprocess as _sp
                # Detectar si es npm o pip
                if "npm" in inp or any(package.startswith(p) for p in ["react", "express", "next", "vue", "angular"]):
                    cmd = ["npm", "install", package]
                    pkg_type = "npm"
                else:
                    cmd = [sys.executable, "-m", "pip", "install", package]
                    pkg_type = "pip"

                if self.show_thinking:
                    print(f"  [Auto-Install: {pkg_type} install {package}]")

                try:
                    result = _sp.run(
                        cmd, capture_output=True, text=True, timeout=120,
                    )
                    output = result.stdout + result.stderr
                    success = result.returncode == 0

                    # Registrar en ActionTracker
                    try:
                        self.action_tracker.log_pip_install(package, success=success)
                    except (AttributeError, OSError):
                        pass

                    if success:
                        return (
                            f"Paquete '{package}' instalado exitosamente via {pkg_type}.\n\n"
                            f"{output[-500:]}"
                        )
                    else:
                        return (
                            f"Error instalando '{package}':\n{output[-800:]}"
                        )
                except _sp.TimeoutExpired:
                    return f"[TIMEOUT] La instalación de '{package}' tardó más de 2 minutos."
                except Exception as e:
                    return f"[ERROR] No se pudo instalar '{package}': {e}"

        # --- Procesar documento ---
        # Keywords que activan resumen nivel "study" (material de estudio)
        study_keywords = [
            "resumen para estudiar", "resumen de estudio", "resumen academico",
            "resumen para examen", "material de estudio", "resumen tipo estudio",
            "resumen con tablas", "resumen con datos", "resumen exhaustivo",
            "resumen completo para estudiar", "resumen detallado para estudiar",
            "quiero estudiar", "necesito estudiar", "para estudiar",
            "resumen con clasificaciones", "resumen con dosis",
            "resumen con definiciones", "resumelo para estudiar",
            "resumen tecnico", "resumen clinico", "resumen farmacologico",
            "resumen con formulas", "resumen con valores",
        ]
        is_study_request = any(k in inp for k in study_keywords)

        doc_keywords = ["analiza este documento", "analiza el documento", "procesa este documento",
                        "procesa el documento", "lee este pdf", "lee este archivo",
                        "resume este documento", "resumen de este", "resumir documento",
                        "resumir archivo", "que dice este", "que contiene este",
                        "extraer datos de", "extrae datos", "extrae entidades",
                        "extraer informacion de", "analiza este pdf", "lee este excel",
                        "procesa este pdf", "analiza el pdf", "lee el documento",
                        "resume el archivo", "resume este pdf", "resume este excel",
                        "realiza resumen", "realiza un resumen", "hazme un resumen",
                        "haz un resumen", "dame un resumen", "dame el resumen",
                        "resumelo", "resumen del documento", "resumen del pdf",
                        "resumen completo", "resumen mas completo", "resumen detallado",
                        "no procesa un resumen", "resumen incompleto",
                        "resume el pdf", "resume el documento", "resumir el pdf",
                        "resumir el documento", "genera un resumen", "genera resumen",
                        "necesito un resumen", "quiero un resumen", "quiero resumen"]
        if is_study_request or any(k in inp for k in doc_keywords):
            # Extraer ruta del archivo
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ \-]+\.\w{2,5}', user_input)
            if path_match:
                filepath = path_match.group(0)
                try:
                    if is_study_request and self.brain:
                        # Modo estudio: usar summarize_document con level="study"
                        summary = self.doc_processor.summarize_document(
                            filepath, brain=self.brain, level="study", is_text=False,
                        )
                        if summary and "[ERROR]" not in summary:
                            fname = os.path.basename(filepath)
                            return f"📄 **{fname}**\n\n📝 **Material de Estudio:**\n\n{summary}"
                        return summary
                    result = self.doc_processor.process(filepath, brain=self.brain)
                    if "error" not in result:
                        return result.get("formatted_output", str(result))
                    return f"[ERROR] {result['error']}"
                except Exception as e:
                    return f"[ERROR] Error procesando documento: {e}"
            elif hasattr(self, '_last_uploaded_doc') and self._last_uploaded_doc:
                # Sin ruta pero hay un documento recien subido — resumir con IA
                doc = self._last_uploaded_doc
                filename = doc.get("filename", "documento")
                pages = doc.get("pages", 0)
                words = doc.get("word_count", 0)

                # Obtener texto completo del cache del procesador
                doc_id = doc.get("doc_id", "")
                full_text = self.doc_processor.get_full_text(doc_id) if doc_id else ""

                if not full_text:
                    full_text = doc.get("summary", "")

                if not full_text.strip():
                    return f"📄 Documento **{filename}** procesado pero sin contenido de texto extraible."

                # Usar el sistema de resumen Map-Reduce del document_processor
                # Soporta documentos largos: chunking + resumen parcial + combinacion
                summary_level = "study" if is_study_request else "detailed"
                level_label = "Material de Estudio" if is_study_request else "Resumen"
                header = f"📄 **{filename}** ({pages} pag, {words} palabras)\n\n"

                if self.brain:
                    try:
                        summary = self.doc_processor.summarize_document(
                            full_text, brain=self.brain,
                            level=summary_level, is_text=True,
                        )
                        if summary and "[ERROR]" not in summary:
                            return header + f"📝 **{level_label}:**\n\n" + summary
                    except (AttributeError, OSError, ValueError):
                        pass

                # Fallback sin IA — vista previa del texto
                return header + f"📝 **Vista previa:**\n{full_text[:2000]}"

        # --- Crear archivo (Auto-Builder directo) ---
        create_file_keywords = ["crea un archivo", "crear un archivo", "crea archivo",
                                "creame un archivo", "haceme un archivo", "genera un archivo"]
        if any(k in inp for k in create_file_keywords):
            # Determinar ubicación
            target_dir = "C:/Users/Lexus/Desktop"
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    target_dir = path
                    break

            # Extraer nombre de archivo si se menciona
            name_match = _re.search(r'(?:llamado|nombre|que se llame)\s+["\']?(\S+)["\']?', inp)
            file_ext = ".txt"
            if name_match:
                fname = name_match.group(1)
                if '.' not in fname:
                    fname += file_ext
            else:
                fname = "archivo_genesis.txt"

            # Extraer contenido — buscar después de "que diga", "con", "contenido"
            content = ""
            content_match = _re.search(
                r'(?:que diga|que contenga|con el texto|con contenido|con)\s+["\']?(.+?)["\']?\s*$',
                inp
            )
            if content_match:
                content = content_match.group(1).strip()
            if not content:
                content = "Archivo creado por Genesis"

            full_path = f"{target_dir}/{fname}"
            from core.tools import FileTools
            result = FileTools.write_file(full_path, content)
            self.metrics.log_tool_use("escribir")
            return f"Archivo creado: `{full_path}`\nContenido: {content}\n\n{result}"

        # --- Crear script/programa (Auto-Builder con LLM) ---
        create_code_keywords = ["crea un script", "crea un programa", "creame un script",
                                "genera un script", "crea un bot", "crea una app",
                                "programa que", "script que", "haceme un programa"]
        if any(k in inp for k in create_code_keywords):
            # Dejar que el LLM genere el código, pero marcar para auto-ejecución
            # El _auto_builder post-LLM se encargará de ejecutarlo
            pass  # Fall through al LLM con flag implícito

        # --- Crear carpeta con proyecto multi-archivo (Auto-Builder Multi-Step) ---
        create_project_keywords = ["crea en mi", "crea una carpeta", "crear carpeta", "nueva carpeta"]
        has_multiple_files = any(w in inp for w in ["archivos", "archivo", ".py", ".js", ".html", ".md", ".txt", ".css"])
        if any(k in inp for k in create_project_keywords):
            # Determinar carpeta base
            base_dir = "C:/Users/Lexus/Desktop"
            for keyword, path in path_keywords.items():
                if keyword in inp:
                    base_dir = path
                    break

            # Extraer nombre de carpeta (entre comillas, o después de "carpeta")
            folder_name = None
            quoted = _re.search(r'["\u201c]([^"\u201d]+)["\u201d]', user_input)
            if quoted:
                folder_name = quoted.group(1).strip()
            if not folder_name:
                name_match = _re.search(r'(?:carpeta|llamada|nombre)\s+(\S+)', inp)
                if name_match:
                    folder_name = name_match.group(1).strip('"\'')
            if not folder_name:
                folder_name = "proyecto_genesis"

            project_dir = f"{base_dir}/{folder_name}"
            import os as _os
            _os.makedirs(project_dir, exist_ok=True)
            results = [f"Carpeta creada: `{project_dir}`"]

            # Si hay archivos mencionados, usar LLM para generar contenido
            if has_multiple_files:
                # Pedir al LLM que genere los archivos como JSON estructurado
                file_prompt = (
                    f"El usuario quiere crear un proyecto en {project_dir}.\n"
                    f"Solicitud original: {user_input}\n\n"
                    f"Genera SOLO un JSON con los archivos a crear. Formato exacto:\n"
                    f'{{"files": [{{"name": "main.py", "content": "print(\'hola mundo\')"}}, '
                    f'{{"name": "utils.py", "content": "def suma(a, b):\\n    return a + b"}}]}}\n\n'
                    f"SOLO el JSON, nada más."
                )
                try:
                    import json as _json
                    llm_response = self.brain.think(
                        "Eres un generador de archivos. Responde SOLO con JSON valido.",
                        [{"role": "user", "content": file_prompt}],
                        temperature=0.3, max_tokens=2048,
                    )
                    # Extraer JSON de la respuesta
                    json_match = _re.search(r'\{[\s\S]*\}', llm_response)
                    if json_match:
                        file_data = _json.loads(json_match.group(0))
                        files_list = file_data.get("files", [])
                        from core.tools import FileTools
                        for f_info in files_list:
                            f_name = f_info.get("name", "")
                            f_content = f_info.get("content", "")
                            if f_name:
                                f_path = f"{project_dir}/{f_name}"
                                # Crear subdirectorio si es necesario
                                f_dir = _os.path.dirname(f_path)
                                if f_dir and not _os.path.exists(f_dir):
                                    _os.makedirs(f_dir, exist_ok=True)
                                FileTools.write_file(f_path, f_content)
                                results.append(f"  Archivo creado: `{f_name}`")
                                self.metrics.log_tool_use("escribir")
                        results.append(f"\nProyecto creado: {len(files_list)} archivos en `{project_dir}`")
                        # Auto-set workspace al proyecto creado
                        try:
                            self.workspace.set_path(project_dir)
                            results.append(f"Workspace configurado: `{project_dir}`")
                        except (AttributeError, OSError, ValueError):
                            pass
                        # Registrar en ActionTracker
                        try:
                            self.action_tracker.log_project_created(
                                project_dir,
                                [f.get("name", "") for f in files_list],
                            )
                        except (AttributeError, OSError):
                            pass
                    else:
                        results.append("[WARN] No pude parsear archivos del LLM — carpeta creada vacía")
                except Exception as e:
                    results.append(f"[ERROR] Generación de archivos: {e}")
            else:
                # Solo crear carpeta sin archivos
                results.append("Carpeta vacía lista para usar")

            return "\n".join(results)

        # --- Mover archivos ---
        move_keywords = ["mueve", "mover", "mueva"]
        if any(k in inp for k in move_keywords) and ("a " in inp or "al " in inp or "hacia " in inp):
            return ""  # Dejar al LLM con herramientas

        # --- Eliminar ---
        delete_keywords = ["elimina ", "borra ", "borrar "]
        if any(k in inp for k in delete_keywords):
            # Extraer ruta/nombre del archivo
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                return file_manager.delete(path_match.group(0))
            # Buscar nombre de archivo
            for kw in delete_keywords:
                if kw in inp:
                    target = inp.split(kw)[-1].strip()
                    for prep in ["el ", "la ", "al ", "del "]:
                        if target.startswith(prep):
                            target = target[len(prep):]
                    if target:
                        # Buscar en escritorio por defecto
                        desktop = Path("C:/Users/Lexus/Desktop") / target
                        if desktop.exists():
                            return file_manager.delete(str(desktop))
                        return f"No encontre '{target}' en el escritorio."
            return ""

        # --- Disco / espacio ---
        disk_keywords = ["espacio en disco", "uso de disco", "cuanto espacio",
                         "archivos grandes", "que ocupa mas"]
        if any(k in inp for k in disk_keywords):
            return disk_analyzer.analyze()

        # --- Leer archivo ---
        read_keywords = ["lee ", "leer ", "muestra el contenido", "contenido del archivo",
                         "que dice el archivo", "abre el archivo"]
        if any(k in inp for k in read_keywords):
            from core.tools import FileTools
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                return FileTools.read_file(path_match.group(0))

        # --- Crear archivo ---
        create_file_keywords = ["crea un archivo", "crear archivo", "nuevo archivo",
                                "crea un documento", "crear documento"]
        if any(k in inp for k in create_file_keywords):
            # El LLM puede manejar esto con [TOOL:escribir] — no interceptar
            return ""

        # --- Info de archivo específico ---
        info_keywords = ["cuanto pesa", "tamaño de", "info de", "información de",
                         "detalles de"]
        if any(k in inp for k in info_keywords):
            path_match = _re.search(r'[A-Za-z]:[/\\][\w/\\._ -]+', user_input)
            if path_match:
                return file_manager.file_info(path_match.group(0))

        # =====================================================================
        # PHASE 19: Smart Productivity — Notas, Recordatorios, Red, Acciones
        # =====================================================================

        # --- Notas rápidas ---
        # "nota: comprar leche" → guarda nota
        # "mis notas" → lista notas
        # "busca en notas X" → busca
        # "elimina nota 3" → elimina
        note_save_kw = ["nota:", "anota:", "recuerda que ", "recordar que ",
                        "apunta:", "guarda nota:", "nota rapida:"]
        if any(inp.startswith(k) for k in note_save_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            content = inp
            for kw in note_save_kw:
                if inp.startswith(kw):
                    content = user_input[len(kw):].strip()
                    break
            # Detectar tag con #tag
            tag = ""
            tag_match = _re.search(r'#(\w+)', content)
            if tag_match:
                tag = tag_match.group(1)
                content = content.replace(f"#{tag}", "").strip()
            return self._quick_notes.add(content, tag)

        note_list_kw = ["mis notas", "ver notas", "lista notas", "mostrar notas",
                        "notas guardadas", "todas las notas", "muestra mis notas"]
        if any(k in inp for k in note_list_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            # Filtrar por tag si se menciona
            tag = ""
            tag_match = _re.search(r'#(\w+)', inp)
            if tag_match:
                tag = tag_match.group(1)
            return self._quick_notes.list_notes(tag=tag)

        note_search_kw = ["busca en notas", "buscar en notas", "busca nota",
                          "buscar nota"]
        if any(k in inp for k in note_search_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            query = inp
            for kw in note_search_kw:
                if kw in inp:
                    query = inp.split(kw)[-1].strip()
                    break
            return self._quick_notes.search(query)

        note_delete_kw = ["elimina nota", "borrar nota", "borra nota", "eliminar nota"]
        if any(k in inp for k in note_delete_kw):
            from core.quick_notes import QuickNotes
            if not hasattr(self, '_quick_notes'):
                self._quick_notes = QuickNotes()
            id_match = _re.search(r'(\d+)', inp)
            if id_match:
                return self._quick_notes.delete(int(id_match.group(1)))
            return "Indicá el número de nota a eliminar (ej: 'elimina nota 3')"

        # --- Recordatorios / Temporizadores ---
        # "recuerdame en 5 minutos que..." → timer + notificación
        # "pon timer de 30 segundos" → timer
        # "mis recordatorios" → lista activos
        # "cancela recordatorio 2" → cancela
        reminder_kw = ["recuerdame en ", "recuérdame en ", "recordame en ",
                       "avísame en ", "avisame en ", "pon timer ",
                       "pon un timer ", "timer de ", "alarma en ",
                       "pon alarma ", "temporizador "]
        if any(k in inp for k in reminder_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            # Extraer tiempo y mensaje
            text_after = inp
            for kw in reminder_kw:
                if kw in inp:
                    text_after = inp.split(kw, 1)[-1].strip()
                    break
            seconds = ReminderSystem.parse_time_expression(text_after)
            if seconds:
                # Extraer mensaje (lo que viene después de "que", "para", "de")
                message = text_after
                for sep in [" que ", " para ", " de que ", " - "]:
                    if sep in text_after:
                        message = text_after.split(sep, 1)[-1].strip()
                        break
                if message == text_after:
                    # Si no hay separador, el mensaje es genérico
                    message = "Recordatorio de Genesis"
                return self._reminders.add(message, seconds)
            return "No entendí el tiempo. Ejemplos: '5 minutos', '1 hora', '30 segundos'"

        reminder_list_kw = ["mis recordatorios", "recordatorios activos",
                            "que recordatorios", "timers activos", "mis timers",
                            "mis alarmas"]
        if any(k in inp for k in reminder_list_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            return self._reminders.list_active()

        reminder_cancel_kw = ["cancela recordatorio", "cancelar recordatorio",
                              "cancela timer", "cancelar timer",
                              "cancela alarma", "cancelar alarma"]
        if any(k in inp for k in reminder_cancel_kw):
            from core.reminder_system import ReminderSystem
            if not hasattr(self, '_reminders'):
                self._reminders = ReminderSystem()
            id_match = _re.search(r'(\d+)', inp)
            if id_match:
                return self._reminders.cancel(int(id_match.group(1)))
            return "Indicá el número de recordatorio a cancelar."

        # --- Estado de red / Conectividad ---
        net_check_kw = ["estoy conectado", "hay internet", "tengo internet",
                        "conexion a internet", "conexión a internet",
                        "estado de red", "estado de la red", "hay conexion",
                        "funciona internet", "funciona la red"]
        if any(k in inp for k in net_check_kw):
            from core.network_tools import network_tools
            return network_tools.check_connectivity()

        wifi_kw = ["info wifi", "información wifi", "mi wifi", "estado wifi",
                   "red wifi", "a que wifi", "a qué wifi", "nombre del wifi",
                   "señal wifi", "wifi conectado"]
        if any(k in inp for k in wifi_kw):
            from core.network_tools import network_tools
            return network_tools.get_wifi_info()

        ping_kw = ["haz ping", "hacé ping", "ping a ", "hacer ping"]
        if any(k in inp for k in ping_kw):
            from core.network_tools import network_tools
            # Extraer host
            host = "8.8.8.8"
            host_match = _re.search(r'ping (?:a\s+)?(\S+)', inp)
            if host_match:
                host = host_match.group(1).rstrip(".,;!?")
            return network_tools.ping(host)

        speed_kw = ["velocidad de internet", "velocidad de red", "test de velocidad",
                    "speed test", "speedtest", "que tan rapido", "qué tan rápido"]
        if any(k in inp for k in speed_kw):
            from core.network_tools import network_tools
            return network_tools.speed_test_quick()

        # --- Acciones rápidas del sistema ---
        if any(k in inp for k in ["limpiar temp", "limpia temp", "limpiar temporales",
                                   "limpia temporales", "borrar temporales",
                                   "vaciar temp", "limpiar archivos temporales"]):
            from core.system_actions import system_actions
            return system_actions.clean_temp()

        if any(k in inp for k in ["limpiar dns", "limpia dns", "flush dns",
                                   "vaciar cache dns", "limpiar cache dns"]):
            from core.system_actions import system_actions
            return system_actions.flush_dns()

        if any(k in inp for k in ["uptime", "hace cuanto esta encendido",
                                   "hace cuánto está encendido",
                                   "tiempo encendido", "desde cuando esta prendido"]):
            from core.system_actions import system_actions
            return system_actions.system_uptime()

        if any(k in inp for k in ["bateria", "batería", "nivel de bateria",
                                   "estado bateria", "cuanta bateria"]):
            from core.system_actions import system_actions
            return system_actions.battery_status()

        if any(k in inp for k in ["bloquea pantalla", "bloquear pantalla",
                                   "bloquea la pantalla", "bloquea el equipo",
                                   "bloquear equipo", "lock screen"]):
            from core.system_actions import system_actions
            return system_actions.lock_screen()

        if any(k in inp for k in ["abre configuracion", "abre configuración",
                                   "abrir configuracion", "abre ajustes",
                                   "configuracion de windows", "configuración de windows"]):
            from core.system_actions import system_actions
            # Detectar sección específica
            section = ""
            for s in ["wifi", "bluetooth", "pantalla", "sonido", "audio",
                      "notificaciones", "almacenamiento", "actualizaciones",
                      "apps", "privacidad", "hora", "idioma", "personalización",
                      "fondo", "energía"]:
                if s in inp:
                    section = s
                    break
            return system_actions.open_settings(section)

        if any(k in inp for k in ["cuantas apps instaladas", "cuántas apps instaladas",
                                   "aplicaciones instaladas", "programas instalados",
                                   "cuantos programas tengo"]):
            from core.system_actions import system_actions
            return system_actions.get_installed_apps_count()

        # =====================================================================
        # PHASE 20 — Smart Utilities
        # =====================================================================

        # --- Clipboard Manager ---
        clipboard_current_kw = ["que hay en el portapapeles", "qué hay en el portapapeles",
                                "contenido portapapeles", "portapapeles actual",
                                "que copié", "qué copié", "clipboard actual",
                                "mostrar portapapeles", "ver portapapeles"]
        if any(k in inp for k in clipboard_current_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.get_current()

        clipboard_hist_kw = ["historial portapapeles", "historial clipboard",
                             "historial de copiado", "lo que copié",
                             "que he copiado", "qué he copiado",
                             "mis copias", "portapapeles historial"]
        if any(k in inp for k in clipboard_hist_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.list_history()

        clipboard_search_kw = ["busca en portapapeles", "buscar en portapapeles",
                                "busca en clipboard", "buscar en clipboard"]
        if any(k in inp for k in clipboard_search_kw):
            from core.clipboard_manager import clipboard_manager
            query = inp
            for k in clipboard_search_kw:
                query = query.replace(k, "").strip()
            return clipboard_manager.search(query)

        clipboard_monitor_kw = ["monitorear portapapeles", "monitorea portapapeles",
                                 "activa clipboard", "monitor clipboard"]
        if any(k in inp for k in clipboard_monitor_kw):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.start_monitoring()

        if any(k in inp for k in ["detener monitor portapapeles", "para monitor clipboard",
                                   "desactiva clipboard"]):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.stop_monitoring()

        if any(k in inp for k in ["limpiar portapapeles", "limpia portapapeles",
                                   "vaciar portapapeles", "borrar historial portapapeles"]):
            from core.clipboard_manager import clipboard_manager
            return clipboard_manager.clear()

        # --- Text Transformer ---
        if any(k in inp for k in ["a mayusculas", "a mayúsculas", "convierte a mayusculas",
                                   "en mayusculas", "en mayúsculas", "pasa a mayusculas"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.to_upper(text)

        if any(k in inp for k in ["a minusculas", "a minúsculas", "convierte a minusculas",
                                   "en minusculas", "en minúsculas", "pasa a minusculas"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.to_lower(text)

        if any(k in inp for k in ["a titulo", "a título", "convierte a titulo",
                                   "formato titulo", "formato título"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.to_title(text)

        if any(k in inp for k in ["cuenta palabras", "contar palabras", "cuantas palabras",
                                   "cuántas palabras", "estadisticas de texto",
                                   "estadísticas de texto", "analiza texto"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.count_text(text)

        if any(k in inp for k in ["codifica base64", "codificar base64", "encode base64",
                                   "a base64", "en base64"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.encode_base64(text)

        if any(k in inp for k in ["decodifica base64", "decodificar base64", "decode base64",
                                   "desde base64", "de base64"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.decode_base64(text)

        if any(k in inp for k in ["hash del texto", "hash texto", "hashear", "hash md5",
                                   "hash sha", "genera hash", "generar hash"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.hash_text(text)

        if any(k in inp for k in ["extrae emails", "extraer emails", "busca emails",
                                   "encuentra emails", "sacar emails"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.extract_emails(text)

        if any(k in inp for k in ["extrae urls", "extraer urls", "busca urls",
                                   "encuentra urls", "sacar urls", "sacar links"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.extract_urls(text)

        if any(k in inp for k in ["extrae numeros", "extraer números", "busca numeros",
                                   "encuentra numeros", "sacar numeros"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.extract_numbers(text)

        if any(k in inp for k in ["formatea json", "formatear json", "prettify json",
                                   "json bonito", "json legible"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.to_json_pretty(text)

        if any(k in inp for k in ["ordena lineas", "ordena líneas", "ordenar lineas",
                                   "ordenar líneas", "sort lines"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.sort_lines(text)

        if any(k in inp for k in ["elimina duplicados", "quitar duplicados",
                                   "lineas unicas", "líneas únicas",
                                   "quita duplicados", "sin duplicados"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.remove_duplicates(text)

        if any(k in inp for k in ["invierte texto", "invertir texto", "texto invertido",
                                   "texto al reves", "texto al revés"]):
            from core.text_transformer import text_transformer
            from core.clipboard_manager import clipboard_manager
            text = clipboard_manager._get_clipboard()
            if not text:
                return "📋 Copiá un texto al portapapeles primero."
            return text_transformer.reverse_text(text)

        # --- Unit Converter ---
        unit_kw = ["convierte ", "convertir ", "cuantos ", "cuántos ",
                   "cuantas ", "cuántas ", "equivale ", "equivalen "]
        unit_suffix = [" a ", " en ", " son ", " es "]
        if (any(k in inp for k in unit_kw) and any(s in inp for s in unit_suffix)):
            # Verificar que no sea una conversión de texto (mayúsculas, base64, etc.)
            text_actions = ["mayuscula", "minuscula", "titulo", "base64", "camel", "snake", "kebab"]
            if not any(ta in inp for ta in text_actions):
                from core.unit_converter import unit_converter
                return unit_converter.convert(inp)

        if any(k in inp for k in ["unidades disponibles", "que unidades", "qué unidades",
                                   "lista unidades", "unidades soportadas"]):
            from core.unit_converter import unit_converter
            return unit_converter.list_categories()

        # --- Pomodoro Timer ---
        pomodoro_start_kw = ["inicia pomodoro", "iniciar pomodoro", "empieza pomodoro",
                             "empezar pomodoro", "arranca pomodoro",
                             "pomodoro start", "comenzar pomodoro",
                             "pon pomodoro", "pon un pomodoro",
                             "activa pomodoro", "start pomodoro"]
        if any(k in inp for k in pomodoro_start_kw):
            from core.pomodoro import pomodoro
            # Detectar tiempo personalizado
            import re as _re2
            m = _re2.search(r'(\d+)\s*(?:min|minuto)', inp)
            work_min = int(m.group(1)) if m else None
            return pomodoro.start(work_min)

        if any(k in inp for k in ["pausa pomodoro", "pausar pomodoro", "pomodoro pause",
                                   "para el pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.pause()

        if any(k in inp for k in ["reanuda pomodoro", "reanudar pomodoro", "continua pomodoro",
                                   "continúa pomodoro", "resume pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.resume()

        if any(k in inp for k in ["detener pomodoro", "para pomodoro", "detén pomodoro",
                                   "stop pomodoro", "cancela pomodoro",
                                   "termina pomodoro", "terminar pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.stop()

        if any(k in inp for k in ["salta pomodoro", "saltar pomodoro",
                                   "skip pomodoro", "siguiente pomodoro"]):
            from core.pomodoro import pomodoro
            return pomodoro.skip()

        if any(k in inp for k in ["estado pomodoro", "pomodoro status", "como va el pomodoro",
                                   "cómo va el pomodoro", "mi pomodoro", "pomodoro actual"]):
            from core.pomodoro import pomodoro
            return pomodoro.status()

        if any(k in inp for k in ["historial pomodoro", "pomodoro historial",
                                   "sesiones pomodoro", "mis pomodoros"]):
            from core.pomodoro import pomodoro
            return pomodoro.history()

        if any(k in inp for k in ["configura pomodoro", "configurar pomodoro",
                                   "ajustar pomodoro", "pomodoro config"]):
            from core.pomodoro import pomodoro
            import re as _re2
            work = _re2.search(r'trabajo\s*(\d+)', inp)
            short = _re2.search(r'descanso\s*(\d+)', inp)
            long = _re2.search(r'largo\s*(\d+)', inp)
            return pomodoro.configure(
                work=int(work.group(1)) if work else None,
                short_break=int(short.group(1)) if short else None,
                long_break=int(long.group(1)) if long else None
            )

        # =====================================================================
        # PHASE 21 — JARVIS Intelligence
        # =====================================================================

        # --- Window Manager ---
        window_action_kw = ["pon ", "snap ", "mueve la ventana"]
        window_targets = ["izquierda", "derecha", "left", "right", "arriba", "abajo"]
        if (any(k in inp for k in window_action_kw) and
            any(t in inp for t in window_targets)):
            from core.window_manager import window_manager
            return window_manager.parse_and_execute(inp)

        maximize_kw = ["maximiza ", "maximizar ", "maximizá ", "maximizá ", "maximices "]
        if any(k in inp for k in maximize_kw) or _re.search(r'\bmaxi\w*za\w*\b', inp):
            from core.window_manager import window_manager
            target = inp
            for prefix in maximize_kw + ["maximice ", "maximizame ", "maximizame "]:
                target = target.replace(prefix, "")
            for noise in ["el ", "la ", "al ", "a ", "por favor", "porfa",
                          "quiero que ", "podés ", "podes ", "me "]:
                target = target.replace(noise, "")
            target = _re.sub(r'\bmaxi\w+za\w*\s*', '', target).strip()
            if not target:
                return "🪟 ¿Qué ventana querés maximizar? Decime el nombre de la app."
            return window_manager.maximize(target)

        minimize_kw = ["minimiza ", "minimizar ", "minimizá ", "minimizá ", "minimices "]
        if any(k in inp for k in minimize_kw) or _re.search(r'\bminimi\w*\b', inp):
            from core.window_manager import window_manager
            target = inp
            # Limpiar todas las variantes del verbo y artículos
            for prefix in minimize_kw + ["minimice ", "minimizame ", "minimizame "]:
                target = target.replace(prefix, "")
            for noise in ["el ", "la ", "al ", "a ", "por favor", "porfa", "porfavor",
                          "quiero que ", "podés ", "podes ", "podrías ", "podrias ",
                          "puedes ", "me ", "che "]:
                target = target.replace(noise, "")
            target = _re.sub(r'\bminimi\w+\s*', '', target).strip()
            if not target or target in ("todo", "todas", "todas las ventanas", "all"):
                return window_manager.minimize_all()
            return window_manager.minimize(target)

        if any(k in inp for k in ["restaura ventana", "restaurar ventana"]):
            from core.window_manager import window_manager
            target = inp
            for prefix in ["restaura ventana ", "restaurar ventana ", "restaura ", "restaurar "]:
                target = target.replace(prefix, "")
            return window_manager.restore(target.strip())

        if any(k in inp for k in ["cambia a ", "cambiar a ", "enfoca ", "enfocar ",
                                   "ve a la ventana", "ir a "]):
            # Evitar colisión con "cambia a mayúsculas" etc.
            text_actions = ["mayuscula", "minuscula", "titulo", "base64", "camel", "snake", "kebab"]
            if not any(ta in inp for ta in text_actions):
                from core.window_manager import window_manager
                target = inp
                for prefix in ["cambia a ", "cambiar a ", "enfoca ", "enfocar ",
                               "ve a la ventana ", "ir a "]:
                    target = target.replace(prefix, "")
                return window_manager.focus(target.strip())

        if any(k in inp for k in ["ventanas abiertas", "listar ventanas", "lista ventanas",
                                   "mis ventanas", "que ventanas", "qué ventanas"]):
            from core.window_manager import window_manager
            return window_manager.list_windows()

        if any(k in inp for k in ["mostrar escritorio", "ver escritorio",
                                   "minimiza todo", "minimizar todo"]):
            from core.window_manager import window_manager
            return window_manager.minimize_all()

        if any(k in inp for k in ["info pantalla", "info monitor", "info monitores",
                                   "resolución pantalla", "resolucion pantalla"]):
            from core.window_manager import window_manager
            return window_manager.screen_info()

        # --- Smart Launcher ---
        if any(k in inp for k in ["busca todo ", "buscar todo ", "busca global ",
                                   "smart search ", "busqueda global",
                                   "búsqueda global"]):
            from core.smart_launcher import smart_launcher
            query = inp
            for prefix in ["busca todo ", "buscar todo ", "busca global ",
                          "smart search ", "busqueda global ", "búsqueda global "]:
                query = query.replace(prefix, "")
            return smart_launcher.search(query.strip())

        if any(k in inp for k in ["lanza ", "lanzar ", "launch "]):
            from core.smart_launcher import smart_launcher
            query = inp
            for prefix in ["lanza ", "lanzar ", "launch "]:
                query = query.replace(prefix, "")
            return smart_launcher.launch(query.strip())

        # --- Daily Briefing ---
        briefing_kw = ["buenos dias", "buenos días", "buen dia", "buen día",
                       "buenas tardes", "buenas noches",
                       "briefing", "resumen del dia", "resumen del día",
                       "como esta el sistema", "cómo está el sistema",
                       "estado general", "briefing diario",
                       "resumen matutino", "dame un resumen"]
        if any(k in inp for k in briefing_kw):
            from core.daily_briefing import daily_briefing
            return daily_briefing.generate()

        # --- Macro System ---
        # Crear macro: "macro trabajo: abre chrome, abre vscode, inicia pomodoro"
        if any(inp.startswith(k) for k in ["macro ", "crear macro ", "nueva macro "]):
            from core.macro_system import macro_system, MacroSystem
            parsed = MacroSystem.parse_macro_definition(inp)
            if parsed:
                name, commands = parsed
                return macro_system.create(name, commands)
            # Si no parseó como definición, ver si es un comando de gestión
            rest = inp
            for prefix in ["macro ", "crear macro ", "nueva macro "]:
                if rest.startswith(prefix):
                    rest = rest[len(prefix):]
                    break

        if any(k in inp for k in ["ejecuta macro ", "ejecutar macro ", "run macro ",
                                   "corre macro ", "correr macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["ejecuta macro ", "ejecutar macro ", "run macro ",
                          "corre macro ", "correr macro "]:
                name = name.replace(prefix, "")
            return macro_system.execute(name.strip())

        if any(k in inp for k in ["mis macros", "listar macros", "lista macros",
                                   "macros disponibles", "ver macros", "mostrar macros"]):
            from core.macro_system import macro_system
            return macro_system.list_macros()

        if any(k in inp for k in ["elimina macro ", "eliminar macro ", "borra macro ",
                                   "borrar macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["elimina macro ", "eliminar macro ", "borra macro ", "borrar macro "]:
                name = name.replace(prefix, "")
            return macro_system.delete(name.strip())

        if any(k in inp for k in ["detalle macro ", "detalles macro ", "ver macro ",
                                   "info macro "]):
            from core.macro_system import macro_system
            name = inp
            for prefix in ["detalle macro ", "detalles macro ", "ver macro ", "info macro "]:
                name = name.replace(prefix, "")
            return macro_system.show(name.strip())

        if any(k in inp for k in ["historial macros", "historial de macros",
                                   "ejecuciones macros"]):
            from core.macro_system import macro_system
            return macro_system.history()

        # =====================================================================
        # FIN PHASE 21
        # =====================================================================

        # =====================================================================
        # PHASE 22 — Autonomous Orchestration
        # =====================================================================

        # --- File Watcher: agregar regla ---
        if any(k in inp for k in ["vigila ", "vigilar ", "monitorea ", "monitorear ", "watch "]):
            if any(k in inp for k in ["carpeta", "directorio", "folder", "descargas", "downloads"]):
                from core.file_watcher import file_watcher
                return file_watcher.list_rules() + "\n\n💡 Para agregar una regla usá: 'vigila [carpeta] patrón [*.pdf] acción [move/copy/notify]'"

        # --- File Watcher: listar reglas ---
        if any(k in inp for k in ["reglas de vigilancia", "reglas del watcher", "reglas de archivo",
                                    "listar reglas", "mis reglas"]):
            from core.file_watcher import file_watcher
            return file_watcher.list_rules()

        # --- File Watcher: iniciar monitoreo ---
        if any(k in inp for k in ["iniciar monitoreo", "empezar a vigilar", "start watcher",
                                    "activar vigilancia", "activa el monitoreo"]):
            from core.file_watcher import file_watcher
            return file_watcher.start()

        # --- File Watcher: detener monitoreo ---
        if any(k in inp for k in ["detener monitoreo", "parar vigilancia", "stop watcher",
                                    "desactivar vigilancia", "detener vigilancia",
                                    "para el monitoreo", "deja de vigilar"]):
            from core.file_watcher import file_watcher
            return file_watcher.stop()

        # --- File Watcher: eventos recientes ---
        if any(k in inp for k in ["eventos del watcher", "eventos recientes del monitoreo",
                                    "qué pasó en las carpetas", "log de archivos"]):
            from core.file_watcher import file_watcher
            return file_watcher.events()

        # --- Smart Scheduler: programar tarea ---
        if any(k in inp for k in ["programa tarea", "programar tarea", "agenda tarea",
                                    "schedule ", "programa que cada"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.list_tasks() + "\n\n💡 Ejemplo: 'programa tarea backup cada 2 horas: respaldar notas'"

        # --- Smart Scheduler: listar tareas ---
        if any(k in inp for k in ["tareas programadas", "mis tareas", "lista de tareas programadas",
                                    "scheduled tasks", "qué tengo programado"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.list_tasks()

        # --- Smart Scheduler: historial ---
        if any(k in inp for k in ["historial de tareas", "historial del scheduler",
                                    "historial programado", "ejecuciones programadas"]):
            from core.smart_scheduler import smart_scheduler
            return smart_scheduler.history()

        # --- Habit Tracker: crear hábito ---
        if any(k in inp for k in ["nuevo hábito", "nuevo habito", "crear hábito", "crear habito",
                                    "agregar hábito", "agregar habito", "new habit"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:nuevo|crear|agregar|new)\s+h[aá]bit[o]?\s+(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.add(name)
            return "🎯 ¿Qué hábito querés crear? Ejemplo: 'nuevo hábito ejercicio'"

        # --- Habit Tracker: completar hábito ---
        if any(k in inp for k in ["completé ", "complete ", "hice ", "hice el hábito",
                                    "terminé ", "hábito hecho", "habito hecho",
                                    "marcar hábito", "marcar habito"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:complet[eé]|hice|termin[eé]|marcar)\s+(?:el\s+)?(?:h[aá]bito\s+)?(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.complete(name)
            return "🎯 ¿Qué hábito completaste? Ejemplo: 'completé ejercicio'"

        # --- Habit Tracker: hábitos de hoy ---
        if any(k in inp for k in ["hábitos de hoy", "habitos de hoy", "mis hábitos hoy",
                                    "hábitos pendientes", "habitos pendientes",
                                    "qué hábitos", "que habitos"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.today()

        # --- Habit Tracker: listar hábitos ---
        if any(k in inp for k in ["mis hábitos", "mis habitos", "lista de hábitos",
                                    "lista de habitos", "todos los hábitos",
                                    "todos los habitos", "listar hábitos"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.list_habits()

        # --- Habit Tracker: estadísticas ---
        if any(k in inp for k in ["estadísticas de hábitos", "estadisticas de habitos",
                                    "stats hábitos", "stats habitos",
                                    "rachas", "streaks", "mis rachas"]):
            from core.habit_tracker import habit_tracker
            return habit_tracker.stats()

        # --- Habit Tracker: eliminar hábito ---
        if any(k in inp for k in ["eliminar hábito", "eliminar habito", "borrar hábito",
                                    "borrar habito", "quitar hábito", "quitar habito"]):
            from core.habit_tracker import habit_tracker
            import re as _re
            m = _re.search(r'(?:eliminar|borrar|quitar)\s+(?:el\s+)?h[aá]bit[o]?\s+(.+)', inp)
            if m:
                name = m.group(1).strip().strip('"').strip("'")
                return habit_tracker.remove(name)
            return "🎯 ¿Qué hábito querés eliminar?"

        # --- Context Engine: comandos más usados ---
        if any(k in inp for k in ["comandos más usados", "comandos mas usados",
                                    "qué uso más", "que uso mas", "top comandos",
                                    "mis comandos frecuentes"]):
            from core.context_engine import context_engine
            return context_engine.top_commands()

        # --- Context Engine: patrones de uso ---
        if any(k in inp for k in ["patrones de uso", "análisis de uso", "analisis de uso",
                                    "cómo uso genesis", "como uso genesis",
                                    "mi actividad", "reporte de uso"]):
            from core.context_engine import context_engine
            return context_engine.full_report()

        # --- Context Engine: sugerencias ---
        if any(k in inp for k in ["qué sugerís", "que sugeris", "sugerencias",
                                    "qué me recomendás", "que me recomendas"]):
            from core.context_engine import context_engine
            suggestion = context_engine.suggest()
            if suggestion:
                return suggestion
            return "🧠 Aún no tengo suficientes datos para sugerencias. Seguí usando Genesis y aprenderé tus patrones."

        # --- Context Engine: borrar datos ---
        if any(k in inp for k in ["borrar datos de uso", "limpiar contexto",
                                    "borrar interacciones", "resetear patrones"]):
            from core.context_engine import context_engine
            return context_engine.clear()

        # =====================================================================
        # FIN PHASE 22
        # =====================================================================

        # =====================================================================
        # PHASE 23 — System Mastery
        # =====================================================================

        # --- Project Scaffolder: crear proyecto ---
        if any(k in inp for k in ["crea proyecto", "crear proyecto", "nuevo proyecto",
                                    "genera proyecto", "scaffold", "generar proyecto"]):
            from core.project_scaffolder import project_scaffolder
            import re as _re
            # Detectar template
            template = "python"
            for t in ["flask", "fastapi", "node", "react", "html"]:
                if t in inp:
                    template = t
                    break
            # Extraer nombre
            m = _re.search(r'(?:crea|crear|nuevo|genera|generar)\s+proyecto\s+(\S+)', inp)
            if m:
                name = m.group(1).strip('"').strip("'")
                return project_scaffolder.create(name, template=template)
            return "🏗️ ¿Qué proyecto querés crear? Ejemplo: 'crea proyecto mi-app con flask'"

        # --- Project Scaffolder: listar templates ---
        if any(k in inp for k in ["templates de proyecto", "plantillas de proyecto",
                                    "tipos de proyecto", "templates disponibles"]):
            from core.project_scaffolder import project_scaffolder
            return project_scaffolder.list_templates()

        # --- Project Scaffolder: historial ---
        if any(k in inp for k in ["proyectos generados", "historial de proyectos",
                                    "proyectos creados"]):
            from core.project_scaffolder import project_scaffolder
            return project_scaffolder.history()

        # --- Code Snippets: guardar ---
        if any(k in inp for k in ["guardar snippet", "guardar código", "guardar codigo",
                                    "nuevo snippet", "save snippet"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:guardar|nuevo|save)\s+(?:snippet|código|codigo)\s+(\S+)(?:\s*:\s*|\s+)(.+)', inp, _re.DOTALL)
            if m:
                name = m.group(1).strip()
                code = m.group(2).strip()
                return code_snippets.add(name, code)
            return "📎 Ejemplo: 'guardar snippet hello: print(\"hola mundo\")'"

        # --- Code Snippets: obtener ---
        if any(k in inp for k in ["snippet ", "mostrar snippet", "ver snippet",
                                    "dame el snippet"]):
            if any(k in inp for k in ["guardar", "nuevo", "save", "eliminar", "borrar", "buscar"]):
                pass  # Dejamos que lo manejen los otros bloques
            else:
                from core.code_snippets import code_snippets
                import re as _re
                m = _re.search(r'(?:snippet|mostrar snippet|ver snippet|dame el snippet)\s+(\S+)', inp)
                if m:
                    return code_snippets.get(m.group(1).strip())
                return code_snippets.list_snippets()

        # --- Code Snippets: buscar ---
        if any(k in inp for k in ["buscar snippet", "buscar código", "buscar codigo",
                                    "snippets de ", "snippets con tag"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:buscar|snippets de|snippets con tag)\s+(?:snippet\s+)?(\S+)', inp)
            if m:
                return code_snippets.search(m.group(1).strip())
            return code_snippets.list_snippets()

        # --- Code Snippets: listar ---
        if any(k in inp for k in ["mis snippets", "listar snippets", "lista de snippets",
                                    "todos los snippets"]):
            from core.code_snippets import code_snippets
            return code_snippets.list_snippets()

        # --- Code Snippets: eliminar ---
        if any(k in inp for k in ["eliminar snippet", "borrar snippet", "quitar snippet"]):
            from core.code_snippets import code_snippets
            import re as _re
            m = _re.search(r'(?:eliminar|borrar|quitar)\s+snippet\s+(\S+)', inp)
            if m:
                return code_snippets.remove(m.group(1).strip())
            return "📎 ¿Qué snippet querés eliminar?"

        # --- Template Engine: listar ---
        if any(k in inp for k in ["mis templates", "listar templates", "templates de texto",
                                    "plantillas de texto", "lista de plantillas"]):
            from core.template_engine import template_engine
            return template_engine.list_templates()

        # --- Template Engine: preview ---
        if any(k in inp for k in ["preview template", "ver template", "mostrar template",
                                    "ver plantilla", "mostrar plantilla"]):
            from core.template_engine import template_engine
            import re as _re
            m = _re.search(r'(?:preview|ver|mostrar)\s+(?:template|plantilla)\s+(\S+)', inp)
            if m:
                return template_engine.preview(m.group(1).strip())
            return template_engine.list_templates()

        # --- Template Engine: aplicar ---
        if any(k in inp for k in ["aplicar template", "usar template", "aplicar plantilla",
                                    "usar plantilla", "genera con template"]):
            from core.template_engine import template_engine
            import re as _re
            m = _re.search(r'(?:aplicar|usar|genera con)\s+(?:template|plantilla)\s+(\S+)', inp)
            if m:
                return template_engine.apply(m.group(1).strip())
            return template_engine.list_templates()

        # --- System Profiler: software instalado ---
        if any(k in inp for k in ["software instalado", "programas instalados",
                                    "qué tengo instalado", "que tengo instalado",
                                    "lista de programas", "apps instaladas"]):
            from core.system_profiler import system_profiler
            return system_profiler.installed_software()

        # --- System Profiler: programas de inicio ---
        if any(k in inp for k in ["programas de inicio", "startup programs",
                                    "qué se inicia con windows", "que se inicia con windows",
                                    "autostart", "arranque de windows"]):
            from core.system_profiler import system_profiler
            return system_profiler.startup_programs()

        # --- System Profiler: variables de entorno ---
        if any(k in inp for k in ["variables de entorno", "environment variables",
                                    "env vars", "mostrar path"]):
            from core.system_profiler import system_profiler
            return system_profiler.environment_vars()

        # --- System Profiler: uso de disco ---
        if any(k in inp for k in ["uso de disco por carpeta", "espacio por carpeta",
                                    "disk usage by folder", "carpetas más pesadas",
                                    "carpetas mas pesadas"]):
            from core.system_profiler import system_profiler
            return system_profiler.disk_usage()

        # --- System Profiler: conexiones de red ---
        if any(k in inp for k in ["conexiones de red", "conexiones activas",
                                    "network connections", "puertos abiertos"]):
            from core.system_profiler import system_profiler
            return system_profiler.network_connections()

        # --- System Profiler: servicios ---
        if any(k in inp for k in ["servicios del sistema", "servicios activos",
                                    "services running", "listar servicios"]):
            from core.system_profiler import system_profiler
            return system_profiler.services()

        # --- System Profiler: reporte completo ---
        if any(k in inp for k in ["reporte del sistema", "perfil del sistema",
                                    "system report", "auditoría del sistema",
                                    "auditoria del sistema"]):
            from core.system_profiler import system_profiler
            return system_profiler.full_report()

        # =====================================================================
        # FIN PHASE 23
        # =====================================================================

        # =====================================================================
        # WEATHER MODULE — Datos en tiempo real
        # =====================================================================

        # --- Clima actual ---
        if any(k in inp for k in ["clima", "tiempo en", "temperatura en",
                                    "weather", "clima en", "datos del clima",
                                    "cómo está el clima", "como esta el clima",
                                    "hace frio", "hace calor", "va a llover",
                                    "está lloviendo", "esta lloviendo"]):
            from core.weather import weather_service
            import re as _re
            # Extraer ubicación si la hay
            m = _re.search(r'(?:clima|tiempo|temperatura|weather)\s+(?:en|de|in|for)\s+(.+)', inp)
            if m:
                location = m.group(1).strip().rstrip("?").rstrip(".")
                return weather_service.current(location)
            # Sin ubicación explícita → usar default
            return weather_service.current()

        # --- Pronóstico ---
        if any(k in inp for k in ["pronóstico", "pronostico", "forecast",
                                    "clima mañana", "clima manana",
                                    "próximos días", "proximos dias",
                                    "va a llover mañana"]):
            from core.weather import weather_service
            import re as _re
            m = _re.search(r'(?:pronóstico|pronostico|forecast)\s+(?:en|de|in|for|para)\s+(.+?)(?:\s+(\d+)\s*d[ií]as?)?$', inp)
            if m:
                location = m.group(1).strip()
                days = int(m.group(2)) if m.group(2) else 3
                return weather_service.forecast(location, days)
            m2 = _re.search(r'(\d+)\s*d[ií]as?', inp)
            days = int(m2.group(1)) if m2 else 3
            return weather_service.forecast("", days)

        # --- Configurar ubicación por defecto ---
        if any(k in inp for k in ["ubicación por defecto", "ubicacion por defecto",
                                    "mi ciudad es", "vivo en", "estoy en"]):
            from core.weather import weather_service
            import re as _re
            m = _re.search(r'(?:ciudad es|vivo en|estoy en|defecto)\s+(.+)', inp)
            if m:
                return weather_service.set_default_location(m.group(1).strip())
            return "🌤️ Ejemplo: 'mi ciudad es Córdoba'"

        # =====================================================================
        # FIN WEATHER MODULE
        # =====================================================================

        # =====================================================================
        # MEDIA GENERATION — Crear imagenes, audio, video
        # =====================================================================
        import re as _re

        # --- Generar imagen ---
        img_patterns = [
            r'(?:genera|crea|dibuja|haz|hazme|creame|créame|genera(?:me)?)\s+(?:una?\s+)?(?:imagen|foto|dibujo|ilustraci[oó]n|wallpaper|fondo)\s+(?:de\s+|sobre\s+|con\s+)?(.+)',
            r'(?:imagen|foto|dibujo)\s+(?:de|sobre|con)\s+(.+)',
        ]
        for pat in img_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                prompt = m.group(1).strip().rstrip(".")
                # Detectar estilo
                style = ""
                style_map = {
                    "realista": "realistic", "anime": "anime", "pixel art": "pixel-art",
                    "acuarela": "watercolor", "oleo": "oil-painting", "3d": "3d-render",
                    "cartoon": "cartoon", "minimalista": "minimalist",
                    "cinematografico": "cinematic", "cinematográfico": "cinematic",
                    "digital": "digital-art", "retro": "retro",
                }
                for es, en in style_map.items():
                    if es in inp.lower():
                        style = en
                        prompt = prompt.replace(es, "").strip()
                        break

                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    result = gen.generate_image(prompt, style=style)
                    if result.get("success"):
                        path = result["path"]
                        return (
                            f"🖼️ **Imagen generada**\n\n"
                            f"**Prompt:** {prompt}\n"
                            f"{'**Estilo:** ' + style + chr(10) if style else ''}"
                            f"**Dimensiones:** {result.get('dimensions', '1024x1024')}\n"
                            f"**Metodo:** {result.get('method', 'unknown')}\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardada en: `{path}`\n\n"
                            f"{'⚠️ ' + result.get('warning', '') if result.get('warning') else ''}"
                        )
                    else:
                        return f"❌ Error generando imagen: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # --- Generar audio ---
        audio_patterns = [
            r'(?:genera|crea|graba|hazme|creame|créame)\s+(?:un\s+)?audio\s+(?:que diga|diciendo|con|de)\s+["\']?(.+?)["\']?\s*$',
            r'(?:convierte|pasa)\s+(?:a|en)\s+audio[\s:]+["\']?(.+?)["\']?\s*$',
            r'(?:lee|di|dime)\s+en\s+(?:voz\s+)?(?:alta|audio)[\s:]+["\']?(.+?)["\']?\s*$',
        ]
        for pat in audio_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                text = m.group(1).strip().strip("\"'")
                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    result = gen.generate_audio(text)
                    if result.get("success"):
                        return (
                            f"🎵 **Audio generado**\n\n"
                            f"**Texto:** {text[:100]}{'...' if len(text) > 100 else ''}\n"
                            f"**Metodo:** {result.get('method', 'unknown')}\n"
                            f"**Tamaño:** {result.get('size_kb', 0)} KB\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardado en: `{result['path']}`"
                        )
                    else:
                        return f"❌ Error generando audio: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # --- Generar video ---
        video_patterns = [
            r'(?:genera|crea|hazme|creame|créame)\s+(?:un\s+)?video\s+(?:de|sobre|con)\s+(.+)',
        ]
        for pat in video_patterns:
            m = _re.search(pat, inp, _re.IGNORECASE)
            if m:
                prompt = m.group(1).strip().rstrip(".")
                try:
                    from core.media_generator import MediaGenerator
                    gen = self.media_generator if hasattr(self, '_modules') and 'media_generator' in self._modules else MediaGenerator()
                    # Generar imagen + audio → video
                    result = gen.generate_video(text=prompt)
                    if result.get("success"):
                        return (
                            f"🎬 **Video generado**\n\n"
                            f"**Tema:** {prompt}\n"
                            f"**Duracion:** {result.get('duration_s', 0)}s\n"
                            f"**Resolucion:** {result.get('resolution', '1280x720')}\n"
                            f"**Tamaño:** {result.get('size_mb', 0)} MB\n"
                            f"**Tiene audio:** {'Si' if result.get('has_audio') else 'No'}\n"
                            f"**Tiempo:** {result.get('time_s', 0)}s\n\n"
                            f"📁 Guardado en: `{result['path']}`"
                        )
                    else:
                        return f"❌ Error generando video: {result.get('error', 'desconocido')}"
                except Exception as e:
                    return f"❌ Error: {e}"

        # =====================================================================
        # FIN MEDIA GENERATION
        # =====================================================================

        # --- Research Auto-Trigger ---
        # Detectar preguntas factuales donde el LLM podría inventar
        # y auto-buscar en la web para dar respuestas reales
        research_patterns = [
            (r'^(?:que|qué) (?:es|son|significa) ', "definición"),
            (r'^(?:como|cómo) funciona ', "explicación"),
            (r'^(?:como|cómo) se (?:hace|usa|instala|configura) ', "tutorial"),
            (r'^(?:cual|cuál) es (?:la|el|las|los) (?:mejor|mejores|diferencia) ', "comparación"),
            (r'(?:ultimo|última|ultimas|últimas|recientes?|noticias?) (?:versión|version|actualización|update)', "actualidad"),
            (r'^(?:quien|quién) (?:es|fue|creo|creó|invento|inventó) ', "investigación"),
            (r'^(?:cuando|cuándo) (?:se|fue|salio|salió) ', "fecha"),
            (r'^investiga ', "investigación"),
            (r'^busca (?:info|información|sobre|acerca) ', "investigación"),
            (r'^(?:dime|explicame|explícame) (?:sobre|acerca|que es|qué es) ', "explicación"),
        ]
        for pattern, query_type in research_patterns:
            if _re.search(pattern, inp):
                # Extraer el tema de búsqueda
                topic = inp
                for prefix in ["que es ", "qué es ", "que son ", "qué son ",
                                "como funciona ", "cómo funciona ",
                                "como se hace ", "cómo se hace ",
                                "como se usa ", "cómo se usa ",
                                "como se instala ", "cómo se instala ",
                                "como se configura ", "cómo se configura ",
                                "quien es ", "quién es ", "quien fue ", "quién fue ",
                                "cuando se ", "cuándo se ", "cuando fue ", "cuándo fue ",
                                "investiga ", "busca info sobre ", "busca información sobre ",
                                "dime sobre ", "explicame ", "explícame ",
                                "cual es la mejor ", "cuál es la mejor ",
                                "cual es el mejor ", "cuál es el mejor "]:
                    if inp.startswith(prefix):
                        topic = inp[len(prefix):].strip().rstrip("?.,!")
                        break

                if topic and len(topic) > 2:
                    try:
                        if self.web.searcher.available:
                            if self.show_thinking:
                                print(f"  [Research: buscando '{topic}' ({query_type})]")
                            results = self.web.searcher.search(topic, max_results=3)
                            if results:
                                # Formatear resultados como contexto
                                search_ctx = f"[RESULTADOS DE BÚSQUEDA WEB para '{topic}']:\n"
                                for i, r in enumerate(results[:3], 1):
                                    title = r.get("title", "")
                                    snippet = r.get("snippet", r.get("body", ""))
                                    url = r.get("url", r.get("href", ""))
                                    search_ctx += f"{i}. {title}\n   {snippet[:200]}\n   Fuente: {url}\n\n"

                                # Intentar leer la primera página para más detalle
                                first_url = results[0].get("url", results[0].get("href", ""))
                                if first_url:
                                    try:
                                        page_text = self.web.reader.read_page(first_url)
                                        if page_text and len(page_text) > 100:
                                            search_ctx += f"\n[CONTENIDO PRINCIPAL]:\n{page_text[:1500]}\n"
                                    except (OSError, ValueError, AttributeError):
                                        pass  # No pasa nada si no puede leer

                                search_ctx += (
                                    "\nUsa esta información REAL para responder. "
                                    "NO inventes datos. Cita las fuentes si es relevante."
                                )
                                return search_ctx
                    except Exception as web_err:
                        if self.show_thinking:
                            print(f"  [Research: error — {web_err}]")

        return ""

    def _detect_and_learn(self, user_input: str) -> str:
        """
        Detecta si el usuario pide aprender y ejecuta busquedas web reales.

        Retorna contexto aprendido para inyectar en el system prompt,
        o string vacio si no es un pedido de aprendizaje.
        """
        text = user_input.lower().strip()

        # Detectar si es un pedido de aprendizaje
        topic = ""
        for trigger in self.LEARN_TRIGGERS:
            if trigger in text:
                # Extraer el tema despues del trigger
                idx = text.index(trigger) + len(trigger)
                topic = user_input[idx:].strip().strip(".,;:!?")
                break

        if not topic:
            return ""

        # Verificar que el modulo web esta disponible
        if not self.web.searcher.available:
            self.log.info(f"Aprendizaje solicitado pero web no disponible: {topic}")
            return ""

        self.log.info(f"Aprendizaje automatico activado: {topic}")

        # Buscar y aprender de la web
        try:
            report = self.web.search_and_learn(topic, max_results=5, max_pages=3)

            # Agregar como curiosidad resuelta
            self.curiosity.add_question(
                f"Aprender sobre: {topic}", priority=1.0
            )
            for q in self.curiosity.questions:
                if topic.lower() in q["question"].lower():
                    q["explored"] = True
                    q["exploration_result"] = f"Web: {report.get('pages_read', 0)} paginas leidas"
                    break

            # Recuperar conocimiento aprendido relevante
            recall = self.web.recall(topic, top_k=5)

            if recall:
                context_parts = [
                    f"[CONOCIMIENTO APRENDIDO sobre '{topic}' — {len(recall)} fragmentos de la web]"
                ]
                for i, item in enumerate(recall[:5], 1):
                    text_snippet = item.get("text", "")[:500]
                    source = item.get("source", "web")
                    context_parts.append(f"\nFuente {i} ({source}):\n{text_snippet}")

                context_parts.append(
                    f"\n[Usa este conocimiento real para responder. "
                    f"Total aprendido: {self.web.total_learned} paginas.]"
                )
                learn_ctx = "\n".join(context_parts)
                self.log.info(f"Conocimiento inyectado: {len(learn_ctx)} chars sobre '{topic}'")
                return learn_ctx

        except Exception as e:
            self.log.error(f"Error en aprendizaje automatico: {e}")

        return ""
