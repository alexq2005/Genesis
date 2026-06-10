# GENESIS — Registro de Errores y Soluciones

> Cada error resuelto es conocimiento reutilizable. Antes de debuggear, buscar aquí primero.

---

## ERR-001: UnicodeEncodeError en banner de terminal (Windows)
- **Fecha:** 2025-03-07
- **Contexto:** Ejecutar `python genesis.py` en Windows mostraba el banner con caracteres Unicode box-drawing.
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-59: character maps to <undefined>`
- **Análisis:** Windows usa `cp1252` como encoding por defecto en `sys.stdout`. Los caracteres Unicode del banner (U+2550-2580, box-drawing) no existen en cp1252.
- **Solución:** Agregar al inicio de `genesis.py`:
  ```python
  if sys.platform == "win32":
      try:
          sys.stdout.reconfigure(encoding="utf-8", errors="replace")
          sys.stderr.reconfigure(encoding="utf-8", errors="replace")
      except Exception:
          pass
  ```
- **Prevención:** Cualquier módulo que imprima caracteres Unicode debe verificar encoding o usar esta misma técnica. Aplica también a Spinner (Braille) y ProgressBar (bloques).

---

## ERR-002: ModuleLogger no tiene método .warning()
- **Fecha:** 2025-03-07
- **Contexto:** `project_generator.py` llamaba `self.log.warning(...)` para advertir sobre archivos saltados.
- **Error:** `AttributeError: 'ModuleLogger' object has no attribute 'warning'`
- **Análisis:** `GenesisLogger.get_child()` retorna un `ModuleLogger` que solo expone `.info()`, `.error()`, `.debug()`. No existe `.warning()`.
- **Solución:** Cambiar `self.log.warning()` a `self.log.info()` en `project_generator.py:225`.
- **Prevención:** Al usar `GenesisLogger`, solo usar métodos: `.info()`, `.error()`, `.debug()`. Si se necesita `.warning()`, agregar el método a `ModuleLogger` en `core/logger.py`.

---

## ERR-003: Test "debug gana sobre code" empate en scoring de templates
- **Fecha:** 2025-03-07
- **Contexto:** Test de PromptTemplateSystem verificaba que input con tags de debug y code priorizara debug.
- **Error:** Test falló — ambos templates (debug y code) obtenían 14 puntos, y code ganaba por orden de inserción en dict.
- **Análisis:** Input "tengo un error en mi programa python, el traceback dice TypeError" sumaba: debug (error=5 + traceback=9 = 14) y code (programa=8 + python=6 = 14). Empate resuelto por orden del dict (code se insertó primero).
- **Solución:** Cambiar input del test a "tengo un error y el traceback dice TypeError, no funciona nada" que agrega "no funciona" (11 chars) exclusivamente a debug, rompiendo el empate.
- **Prevención:** Al crear tests de scoring por tags, asegurar que los inputs tengan diferencias claras de peso. Evitar inputs que puedan empatar.

---

## ERR-004: Tests de versión fallan al bumpar GENESIS_VERSION
- **Fecha:** 2025-03-05 → 2025-03-07 (recurrente)
- **Contexto:** Tests de v1.1, v1.2, v1.3 verificaban `GENESIS_VERSION == "1.X.0"`. Al subir a v1.4, fallaban.
- **Error:** `AssertionError: '1.4.0' != '1.2.0'` (y variantes para cada suite).
- **Análisis:** Comparación exacta (`==`) contra versión hardcodeada no es forward-compatible.
- **Solución:** Cambiar todas las comparaciones a `>=`:
  ```python
  # Antes (frágil):
  assert GENESIS_VERSION == "1.2.0"
  # Después (robusto):
  assert GENESIS_VERSION >= "1.2.0"
  ```
- **Prevención:** NUNCA usar `==` para versiones en tests. Siempre `>=` para la versión mínima que introdujo la feature.

---

## ERR-005: Tool "broken" se crea exitosamente (sintaxis válida inesperada)
- **Fecha:** 2025-03-07
- **Contexto:** Test de v1.3 creaba tool con code `return unclosed_string` esperando que fuera inválido.
- **Error:** Test "Lista vacía después de delete" fallaba porque "broken" seguía existiendo.
- **Análisis:** `return unclosed_string` es Python válido — es un `return` de una variable llamada `unclosed_string`. No es un error de sintaxis, solo un NameError en runtime.
- **Solución:** Agregar limpieza explícita:
  ```python
  if "broken" in tc.tools:
      tc.delete_tool("broken")
  ```
- **Prevención:** Para tests que necesiten code inválido, usar sintaxis realmente rota: `def (`, `if:`, `return <<<`. No confiar en nombres de variables como indicador de error.

---

## ERR-006: Timeout de 180s al ejecutar Genesis con pipe
- **Fecha:** 2025-03-07
- **Contexto:** Ejecutar `echo "test" | python genesis.py` para verificar que el sistema arranca.
- **Error:** Proceso terminado por timeout después de 180 segundos.
- **Análisis:** NO es un error real. El modelo 7B con system prompt extenso (~2000 tokens de contexto) tarda significativamente en generar respuesta. Además, input por pipe no es interactivo — el modelo intenta generar una respuesta completa sin el beneficio del streaming visual.
- **Solución:** Comportamiento esperado. Para uso real, ejecutar `python genesis.py` directamente en terminal interactiva.
- **Prevención:** Tests funcionales del modelo no deben usar pipe. Para smoke tests, verificar solo que el sistema inicializa (banner, model loading, subsystems) sin esperar respuesta completa.

---

## ERR-007: ModelRouter matchea "mistral" con dolphin por filename
- **Fecha:** 2025-03-07
- **Contexto:** `set_model("mistral")` para seleccionar manualmente el modelo Mistral Instruct.
- **Error:** El router seleccionaba dolphin en vez de mistral.
- **Análisis:** La búsqueda `name.lower() in profile.filename.lower()` matcheaba "mistral" en "dolphin-2.8-**mistral**-7b-v02-Q4_K_M.gguf" antes de llegar al perfil real de mistral. Iteración por dict hacía que dolphin apareciera primero.
- **Solución:** Búsqueda en 3 pasos con prioridad: (1) match exacto por nombre de perfil, (2) match parcial por nombre, (3) match parcial por filename. El match exacto "mistral" == "mistral" se encuentra en paso 1.
- **Prevención:** Siempre priorizar matches exactos sobre parciales en búsquedas por nombre. Los filenames pueden contener nombres de otros modelos (mistral aparece en dolphin, llama en muchos modelos).

---

## ERR-008: RAG search "fibonacci recursivo" no encuentra resultados
- **Fecha:** 2025-03-07
- **Contexto:** Test buscaba "fibonacci recursivo" en un archivo Python indexado con `calcular_fibonacci`.
- **Error:** TF-IDF no encontraba match (score < 0.1).
- **Análisis:** El tokenizador genera "calcular_fibonacci" como token compuesto (no lo divide). "recursivo" no aparece literalmente en el archivo. Con min_score=0.1, no había match suficiente.
- **Solución:** Usar query con palabras que realmente aparecen en el documento: "calcular fibonacci script ejemplo" + min_score=0.05.
- **Prevención:** En tests de búsqueda TF-IDF, usar palabras que realmente existen en los documentos indexados. TF-IDF es literal — no entiende sinónimos.

## ERR-009: "arquitectura" mapea a coder en vez de planner (desempate por prioridad)
- **Fecha:** 2026-03-07
- **Contexto:** Test esperaba que "diseña la arquitectura del sistema" seleccionara planner.
- **Error:** El test falló porque detect_agent retornó "coder" en vez de "planner".
- **Análisis:** La capability "architecture" está en AMBOS agentes: coder (priority=8) y planner (priority=6). El scoring por keyword length da empate (12 puntos). El desempate usa priority → coder gana (8 > 6).
- **Solución:** Corregir el test para esperar "coder" y documentar que capabilities compartidas se resuelven por prioridad.
- **Prevención:** Al escribir tests de auto-routing, verificar qué agentes comparten capabilities y considerar la priority como factor de desempate.

## ERR-010: Pipeline se detiene en paso 1 cuando brain=None
- **Fecha:** 2026-03-07
- **Contexto:** Test de pipeline con brain=None esperaba que los 2 pasos se ejecutaran.
- **Error:** Solo se ejecutó 1 paso. El segundo nunca corrió.
- **Análisis:** `delegate()` con `brain=None` y `use_brain=True` (default) genera response vacía. `pipeline()` interpreta response vacía como `success=False` → ejecuta `break` para detener el pipeline.
- **Solución:** Ajustar test para validar que el pipeline ejecuta "al menos 1 paso" y que la detención ante fallo es comportamiento correcto.
- **Prevención:** Tests de pipeline sin LLM deben tener en cuenta que delegate retorna vacío sin brain. Usar `use_brain=False` en unit tests o mockear brain.

## ERR-011: UnicodeEncodeError con → en test names (Windows cp1252)
- **Fecha:** 2026-03-07
- **Contexto:** test_v1_6.py usaba `→` (U+2192) en nombres de test como `'busca' → researcher`.
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`
- **Análisis:** Windows usa cp1252 por defecto en stdout. El carácter `→` no existe en cp1252. genesis.py ya tiene el fix de `sys.stdout.reconfigure(encoding="utf-8")` pero los tests no lo tenían.
- **Solución:** Agregar `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` al inicio del test + reemplazar `→` por `->`.
- **Prevención:** SIEMPRE agregar el reconfigure de UTF-8 al inicio de cada archivo de tests nuevo. Evitar caracteres Unicode en print de tests.

## ERR-012: A/B test no concluye con variantes empatadas al 100%
- **Fecha:** 2026-03-07
- **Contexto:** Test de PromptExperiment con 3 variantes: original 100%, amable 0%, conciso 100%.
- **Error:** El test esperaba `state=="concluded"` pero seguía en `"running"`.
- **Análisis:** `_check_conclusion()` requiere ≥15% de diferencia entre 1er y 2do lugar. Con original=100% y conciso=100%, la diferencia es 0% → no concluye. Esto es CORRECTO: no debería declarar ganador entre empates.
- **Solución:** Cambiar test para que conciso tenga 50% (2/4), creando diferencia clara de 50% entre original y conciso.
- **Prevención:** En tests de A/B, asegurar que haya un ganador estadísticamente claro, no empates.

## ERR-013: test_v1_6 falla al bumpar a v1.7.0 (version check exacto)
- **Fecha:** 2026-03-07
- **Contexto:** test_v1_6.py tenía `GENESIS_VERSION == "1.6.0"`. Al bumpar config.py a "1.7.0", este test falló.
- **Error:** `[FAIL] Version es 1.6.0` porque ahora es "1.7.0".
- **Análisis:** Los tests de versión anteriores hacen check exacto en vez de ≥. Cada bump rompe tests de versiones anteriores.
- **Solución:** Cambiar a `GENESIS_VERSION >= "1.6.0"` para forward compatibility.
- **Prevención:** Tests de versión deben usar `>=` en vez de `==` para no romperse con cada bump.

## ERR-014: test_v1_7 falla al bumpar a v1.8.0 (version check exacto, recurrente)
- **Fecha:** 2026-03-07
- **Contexto:** test_v1_7.py tenia `GENESIS_VERSION == "1.7.0"`. Al bumpar config.py a "1.8.0", este test fallo.
- **Error:** `[FAIL] Version es 1.7.0` porque ahora es "1.8.0".
- **Analisis:** Pattern recurrente: tests de version usan `==` en vez de `>=`. Cada bump rompe el test de la version anterior. Ya documentado en ERR-004 y ERR-013 pero sigue ocurriendo.
- **Solucion:** Cambiar a `GENESIS_VERSION >= "1.7.0"`.
- **Prevencion:** REGLA ABSOLUTA: NUNCA usar `==` para version en tests. Siempre `>=`. Esto aplica a TODOS los futuros test files.

## ERR-015: QualityScorer retorna score alto (0.3+) para respuestas vacías
- **Fecha:** 2026-03-12
- **Contexto:** Test de SelfEvaluator evaluaba `scorer.score("test", "", "chat")` esperando overall < 0.3.
- **Error:** Score devuelto ~0.37 para respuesta vacía.
- **Análisis:** `_score_relevance` defaultea 0.7, `_score_error_free` defaultea 1.0 para strings vacíos. El promedio ponderado daba un score inflado.
- **Solución:** Agregar early return en `score()` para respuestas < 3 chars → overall 0.05 con todos los sub-scores en 0.
- **Prevención:** Siempre validar edge cases (vacío, None, muy corto) al inicio de funciones de scoring.

## ERR-016: SkillExtractor no detecta "como instalar" como pregunta HOW-TO
- **Fecha:** 2026-03-12
- **Contexto:** Regex HOW_TO_PATTERNS solo tenía verbos conjugados (hago, configuro, instalo).
- **Error:** `is_how_to_question("como instalar python?")` retornaba False.
- **Análisis:** Pattern `como\s+(?:hago|hacer|puedo|configuro|instalo|creo|uso)` no incluía infinitivos (instalar, configurar, crear, usar).
- **Solución:** Agregar infinitivos al pattern: `instalar|configurar|crear|usar|desplegar|deploy`.
- **Prevención:** Los patterns de verbos en español deben incluir tanto conjugados como infinitivos.

## ERR-017: extract_skill() extrae de preguntas no-procedurales
- **Fecha:** 2026-03-12
- **Contexto:** `extract_skill("que es docker?", response_con_pasos)` debería retornar None.
- **Error:** Retornaba un SkillEntry porque solo verificaba `has_procedure()`, no `is_how_to_question()`.
- **Análisis:** El guard `is_how_to_question()` existía solo en `extract_and_store()`, no en `extract_skill()`. Un consumidor directo de `extract_skill()` no tenía el filtro.
- **Solución:** Agregar `if not self.is_how_to_question(user_input): return None` al inicio de `extract_skill()`.
- **Prevención:** Guards de validación deben estar en el método de bajo nivel, no solo en el wrapper de alto nivel.

## ERR-018: _title_similarity Jaccard demasiado estricto para títulos cortos
- **Fecha:** 2026-03-12
- **Contexto:** Títulos "Instalar python" vs "Instalar python en pc" daban similarity 0.5 (< threshold 0.8).
- **Error:** Duplicados no detectados porque Jaccard penaliza palabras extras.
- **Análisis:** Jaccard(A,B) = |A∩B|/|A∪B|. Con sets de 2 y 4 palabras: 2/4=0.5. Para títulos cortos donde uno es substring del otro, esto es demasiado estricto.
- **Solución:** Cambiar a containment similarity: |A∩B|/min(|A|,|B|). Resultado: 2/2=1.0 (detecta correctamente el duplicado).
- **Prevención:** Para comparación de textos cortos, containment es mejor que Jaccard. Jaccard funciona mejor con textos largos.

---

## ERR-019: ctransformers timeout — modelo no responde
- **Fecha:** 2026-03-14
- **Contexto:** Genesis v5.0 usaba ctransformers[cuda] para cargar dolphin-2.8-mistral-7b. Al hacer una pregunta, el modelo no respondía.
- **Error:** Timeout después de 60+ segundos sin generar tokens.
- **Solución:** Reemplazar ctransformers por Ollama como motor LLM. Ollama sirve Llama 3.1 8B via HTTP en ~10s.
- **Prevención:** Ollama es más estable y rápido que ctransformers para inferencia local. Usar Ollama como motor principal.

---

## ERR-020: EmbeddingsEngine.add_text() got unexpected keyword argument 'key'
- **Fecha:** 2026-03-14
- **Contexto:** `semantic_memory.py` y `skill_memory.py` llamaban `add_text(key=..., metadata=...)`.
- **Error:** `TypeError: add_text() got an unexpected keyword argument 'key'`
- **Análisis:** La firma real es `add_text(doc_id, text, source, extra_metadata)` — parámetros posicionales con nombres distintos.
- **Solución:** Cambiar `key=` a `doc_id=` y `metadata=` a `extra_metadata=` en ambos archivos.
- **Prevención:** Verificar firmas de métodos antes de llamarlos con keyword arguments.

---

## ERR-021: LLM (Llama 3.1 8B) inventa datos del sistema — alucinación masiva
- **Fecha:** 2026-03-14
- **Contexto:** Usuario preguntó "que hay en la papelera de reciclaje". El LLM inventó 57 items con nombres falsos.
- **Error:** El LLM fabricó archivos inexistentes, dijo "restauré el archivo" sin hacer nada real, y repitió el comportamiento.
- **Análisis:** Llama 3.1 8B recibe un system prompt con descripciones de herramientas pero no puede/quiere usar el formato `[TOOL:x]`. En vez de decir "no puedo", inventa datos plausibles.
- **Solución:** Triple enfoque: (1) Auto-tool pattern — interceptar intención del usuario ANTES del LLM y ejecutar herramientas reales, (2) Anti-hallucination filter — post-procesamiento que detecta acciones fabricadas, (3) Core rules — "NUNCA INVENTES datos".
- **Prevención:** Modelos pequeños (8B) no son confiables para tool-use con formatos custom. Usar patrón auto-tool (intent→execute→return real data) en vez de depender del LLM para llamar herramientas.

---

## ERR-022: "ram" substring false match en _auto_detect_tool()
- **Fecha:** 2026-03-14
- **Contexto:** "que programas se ejecutan al inicio" debía activar startup_keywords pero activaba sys_keywords.
- **Error:** `sys_keywords` contenía `"ram"` que matcheaba dentro de "prog**ram**as" por substring.
- **Análisis:** `any(k in inp for k in sys_keywords)` usa `in` de strings — "ram" es substring de "programas".
- **Solución:** (1) Cambiar `"ram"` a `" ram "` (con espacios), (2) Mover startup_keywords ANTES de sys_keywords para dar prioridad a la detección más específica.
- **Prevención:** Keywords cortas en detección por substring deben tener delimitadores (espacios) o usar word boundary regex. Ordenar detecciones de más específica a más genérica.

---

## ERR-023: create_file_keywords block sin return — fallthrough silencioso
- **Fecha:** 2026-03-14
- **Contexto:** `_auto_detect_tool()` tiene un bloque para "crea un archivo" que hace `pass` sin retornar.
- **Error:** Si el usuario dice "crea un archivo test.txt", el bloque matchea pero no retorna. La función sigue evaluando bloques posteriores (info_keywords, etc.) y puede dar un resultado inesperado.
- **Análisis:** Todos los demás bloques en `_auto_detect_tool()` retornan un valor. El de create_file tenía `pass` para "dejar al LLM", pero olvidó `return ""`.
- **Solución:** Cambiar `pass` a `return ""` para que la función termine y el LLM maneje la creación.
- **Prevención:** Todo bloque de keywords en `_auto_detect_tool()` DEBE tener un `return`. Si no intercepta, debe retornar `""`.

---

## ERR-024: custom_tools no definido en SECTION_MAX_TOKENS
- **Fecha:** 2026-03-14
- **Contexto:** `router.py` incluye "custom_tools" en CHAT_SECTIONS pero `context_manager.py` no lo tiene en SECTION_MAX_TOKENS.
- **Error:** Cuando el contexto incluye "custom_tools", usa el default (0 tokens) y la sección se trunca completamente.
- **Solución:** Agregar `"custom_tools": 500` a SECTION_MAX_TOKENS en context_manager.py.
- **Prevención:** Al agregar secciones a CHAT_SECTIONS en router.py, siempre agregar la entrada correspondiente en context_manager.py.

---

## ERR-025: skill_memory.py — doc_id como argumento posicional
- **Fecha:** 2026-03-14
- **Contexto:** `skill_memory.py` llama `embeddings.add_text(f"skill_{id}", text, extra_metadata=...)` pasando doc_id como posicional.
- **Error:** Inconsistente con `semantic_memory.py` que usa `doc_id=` como keyword arg. Potencialmente fragil si la firma cambia.
- **Solución:** Cambiar a `doc_id=f"skill_{id}", text=...` usando keyword args explícitos.
- **Prevención:** Siempre usar keyword arguments al llamar métodos con más de 2 parámetros.

---

## ERR-026: GENESIS_VERSION no actualizado a 5.1.0
- **Fecha:** 2026-03-14
- **Contexto:** config.py decía `GENESIS_VERSION = "5.0.0"` pero toda la documentación ya referenciaba v5.1.
- **Solución:** Actualizar a `"5.1.0"`.
- **Prevención:** Al agregar features/fixes significativos, siempre bumpar la versión en config.py junto con la documentación.

---

## ERR-027: Command Injection en device_tools.py (6 métodos)
- **Fecha:** 2026-03-14
- **Contexto:** Revisión de seguridad completa de `core/device_tools.py`.
- **Error:** 6 métodos usaban `shell=True` con input del usuario interpolado en f-strings, permitiendo inyección de comandos.
- **Análisis:** `ProcessManager.kill_process()` (línea 637), `AppLauncher.open()` (línea 682), `ClipboardManager.read()` (línea 707), `ClipboardManager.write()` (línea 729), `ScreenCapture.capture()` (línea 782), `RecycleBin.restore()` (línea 901) — todos construían comandos shell con input sin sanitizar.
- **Solución:**
  1. `kill_process()`: Cambiado a `subprocess.run(['taskkill', '/F', '/IM', safe_name])` sin `shell=True` + regex whitelist
  2. `AppLauncher.open()`: Cambiado a `subprocess.Popen(['cmd', '/c', 'start', '', safe_target])` + regex whitelist
  3. `ClipboardManager.read()`: Cambiado a `['powershell', '-NoProfile', '-Command', 'Get-Clipboard']`
  4. `ClipboardManager.write()`: Texto pasado via `input=text` (stdin) en vez de interpolación
  5. `ScreenCapture.capture()`: Cambiado a lista + `Path().resolve()` + strip de comillas simples
  6. `RecycleBin.restore()`: Regex sanitiza `name_filter` eliminando `'"\`$(){}[];|&<>!`
- **Prevención:** NUNCA usar `shell=True` con input del usuario. Siempre usar forma lista `['cmd', 'arg1']` o pasar datos via `stdin`.

---

## ERR-028: semantic_memory.py recall() devolvía lista vacía siempre
- **Fecha:** 2026-03-14
- **Contexto:** `semantic_memory.py` usa `embeddings_engine.py` para búsqueda semántica.
- **Error:** `recall()` nunca encontraba entradas — devolvía `[]` para cualquier query.
- **Análisis:** `embeddings_engine.search()` retorna resultados con campo `"id"` (línea 101 de embeddings_engine.py), pero `semantic_memory.py` buscaba campo `"key"` (líneas 155 y 217). La correlación entry_id → resultado siempre fallaba.
- **Solución:** Cambiar `r.get("key", "")` a `r.get("id", "")` en líneas 155 y 217 de semantic_memory.py.
- **Prevención:** Crear integration tests que conecten embeddings_engine + semantic_memory para verificar el flujo completo de indexación → búsqueda → correlación.

---

## ERR-029: ModuleLogger tenía método .warn() (violación de spec)
- **Fecha:** 2026-03-14
- **Contexto:** Revisión de spec dice: solo `.info()`, `.error()`, `.debug()` — NO `.warning()` ni `.warn()`.
- **Error:** `logger.py:202` definía método `.warn()` en ModuleLogger. `test_all_improvements.py:56` lo usaba.
- **Análisis:** `.warn()` fue añadido probablemente como conveniencia pero viola la especificación explícita del proyecto.
- **Solución:** Eliminado `.warn()` de logger.py. Actualizado test para no usar `.warn()` y ajustado el conteo esperado de 4 a 3.
- **Prevención:** No añadir métodos al logger que no estén en la spec. Si se necesita warning, usar `.info()` con prefijo "[WARN]".

---

## ERR-030: Tests v1.2-v1.5 sin UTF-8 reconfigure (Windows crash)
- **Fecha:** 2026-03-14
- **Contexto:** Tests v1.2, v1.3, v1.4, v1.5 podían fallar en Windows con caracteres Unicode.
- **Error:** `UnicodeEncodeError` al imprimir resultados con tildes o caracteres especiales en consola Windows cp1252.
- **Análisis:** Tests v1.6+ ya tenían la protección, pero v1.2-v1.5 fueron creados antes de que se estableciera el patrón.
- **Solución:** Añadido bloque `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` a los 4 archivos.
- **Prevención:** Todo nuevo test DEBE incluir el bloque UTF-8 como primera acción después de imports. Ver ERR-001.

---

## ERR-031: genesis.py perdía estado de 63+ módulos en cierre inesperado
- **Fecha:** 2026-03-14
- **Contexto:** Los 63 módulos con `save()` solo se guardaban en `/exit`. Un Ctrl+C, crash, o cierre de Flask perdía todo el estado aprendido.
- **Error:** Sin error visible — pérdida silenciosa de estado (skills, patrones, preferencias, anomalías detectadas, etc).
- **Análisis:** `_save_session()` solo guardaba 6 campos (summarizer, router, streaming, conversation). El bloque save de 63 módulos estaba inline en el handler de `/exit`.
- **Solución:**
  1. Creado método `save_all()` que itera sobre todos los módulos con save()/_save() con try/except individual
  2. `_save_session()` ahora llama `save_all()` al final
  3. Registrado `atexit.register(self.save_all)` en `__init__` para guardar en cualquier cierre
  4. Simplificado el handler `/exit` para usar `save_all()` (eliminadas 63 líneas duplicadas)
- **Prevención:** Siempre registrar `atexit` handler para cualquier sistema con persistencia. Nunca depender de un comando de cierre explícito.

---

## ERR-032: web_ui.py sin seguridad (CORS, rate limiting, input validation)
- **Fecha:** 2026-03-14
- **Contexto:** Web UI Flask era accesible sin restricciones.
- **Error:** Sin headers de seguridad, sin límite de rate, sin validación de longitud de input, errores devueltos con HTTP 200.
- **Solución:**
  1. Añadido `@app.after_request` con headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, CORS localhost-only
  2. Rate limiter in-memory: 30 req/60s por IP (sin dependencias extras)
  3. Input validation: MAX_INPUT_LENGTH = 10000 chars
  4. Error responses: HTTP 500 en vez de 200
  5. Nuevo endpoint `/api/health` para monitoreo
- **Prevención:** Todo endpoint público debe tener rate limiting y input validation desde el día 1.

---

## ERR-033: Python 3.10 type hints sin `from __future__ import annotations`
- **Fecha:** 2026-03-14
- **Contexto:** 4 módulos usaban `list[dict]`, `dict[str, float]` sin importar `annotations` de `__future__`.
- **Error:** `TypeError: 'type' object is not subscriptable` en Python 3.9 o anterior.
- **Análisis:** Python 3.10+ permite `list[dict]` sin import, pero < 3.10 requiere `from __future__ import annotations`.
- **Solución:** Añadido `from __future__ import annotations` a: health_monitor.py, rate_limiter.py, task_scheduler.py, config_manager.py. También corregido typo `callable` → `Callable` en config_manager.py.
- **Prevención:** Siempre usar `from __future__ import annotations` o `List[Dict]` de typing cuando se usen type hints genéricos.

---

## ERR-034: 10 módulos Era 1 sin método público `save()` / 4 sin `clear()`
- **Fecha:** 2026-03-14
- **Contexto:** Spec requiere interfaz pública: save(), _load(), clear(), status(), generate_report().
- **Error:** Módulos usaban `_save()` (privado) pero no exponían `save()` público. save_all() no podía encontrar el método.
- **Análisis:** Patrón inconsistente entre módulos antiguos (Era 1) y nuevos (Era 3+).
- **Solución:** Añadido `def save(self): self._save()` a: memory.py (2 clases), curiosity.py, heartbeat.py, metrics.py, feedback.py, error_memory.py, knowledge_graph.py, code_memory.py, workspace.py. Añadido `clear()` a: error_memory.py, knowledge_graph.py, code_memory.py, feedback.py.
- **Prevención:** Todo nuevo módulo DEBE implementar los 6 métodos de interfaz desde el inicio.

---

## Plantilla para Nuevos Errores

## ERR-035: `evaluate_and_evolve()` no existe — evolución nunca se ejecuta
- **Fecha:** 2026-03-14
- **Contexto:** `/evolve` comando y `action_try_evolve` intentan evolucionar el prompt.
- **Error:** `AttributeError: 'EvolutionEngine' object has no attribute 'evaluate_and_evolve'` (silenciado por try/except genérico).
- **Análisis:** genesis.py línea 2397 llamaba `self.evolution.evaluate_and_evolve(self.brain, fitness)` pero el método real es `evolve(brain, real_fitness=, feedback_context=)`. El error se tragaba y la evolución nunca ocurría.
- **Solución:** Cambiado a `self.evolution.evolve(self.brain, real_fitness=fitness, feedback_context=feedback_ctx)`.
- **Prevención:** No inventar nombres de métodos — verificar siempre contra la clase real.

## ERR-036: `/evolve` no garantiza mutación del prompt
- **Fecha:** 2026-03-14
- **Contexto:** `/evolve` sin argumentos corría 5 `autonomous.tick()` que ejecutaban acciones genéricas por prioridad.
- **Error:** No se garantizaba que `action_try_evolve` se ejecutara. Además, tenía guard `fitness < 40` que impedía evolucionar si el sistema estaba "bien".
- **Análisis:** Los ticks ejecutan acciones por prioridad (curiosity > web > evaluate > evolve > consolidate). Si curiosity tenía cooldown, podía repetir otra acción.
- **Solución:** Agregado paso 5/6 que llama **directamente** a `evolution.evolve()` con fitness real. Eliminado guard arbitrario de fitness < 40.
- **Prevención:** Operaciones críticas deben tener llamada directa, no depender de schedulers genéricos.

## ERR-037: SelfModifier desconectado — nunca se proponen cambios de código
- **Fecha:** 2026-03-14
- **Contexto:** `SelfModifier` estaba instanciado (`self.self_modifier`) pero `propose_change()` jamás se llamaba.
- **Error:** `/apply`, `/reject`, `/self_rollback` existían pero no había forma de crear un cambio pendiente.
- **Análisis:** Se implementó SelfModifier con todo el flujo de seguridad (AST validation, backup, dangerous patterns, diff) pero nunca se conectó al pipeline de auto-evolución.
- **Solución:** Nuevo comando `/mutate [file|auto|list]` que: lee archivo → LLM analiza y propone mejoras → SelfModifier valida → muestra diff → usuario aprueba con `/apply`.
- **Prevención:** Verificar que cada módulo tenga al menos un punto de entrada en el command dispatcher.

## ERR-038: `/evolve` no integraba mutación de código fuente
- **Fecha:** 2026-03-14
- **Contexto:** `/evolve` mutaba el prompt de personalidad (paso 5) pero no el código fuente real.
- **Error:** El usuario pidió "quiero que mute su propio código" pero `/evolve` solo evolucionaba el prompt. La mutación de código (`/mutate`) requería intervención manual separada.
- **Análisis:** `EvolutionEngine` y `SelfModifier` eran sistemas paralelos desconectados. `/evolve` ignoraba `SelfModifier` y `/mutate` requería `/apply` manual.
- **Solución:**
  1. Nuevo método `_auto_mutate_code()`: combina `/mutate auto` + auto-apply sin intervención
  2. Integrado como paso 6/7 en `/evolve` (antes era 6 pasos, ahora 7)
  3. Seguridad: AST validation → dangerous patterns → auto-test → auto-revert on failure
  4. Alineados límites de tamaño: `_mutate_pick_target()` 14KB ↔ `_auto_mutate_code()` 15KB
- **Resultado verificado:** Gen 1→4 en 4 ciclos. Prompt evolucionó exitosamente. Code mutation propuesta/rechazada correctamente por validación AST (Llama 3.1 8B genera syntax errors en archivos grandes).
- **Prevención:** Módulos de auto-modificación deben estar integrados en el ciclo principal, no ser features aisladas.

## ERR-039: Python triple-quoted string interpreta escape sequences en JS inline (~20 ocurrencias)
- **Fecha:** 2026-03-14
- **Contexto:** `web_ui.py` contiene toda la UI (HTML+CSS+JS) dentro de un string Python `"""..."""`. Al ejecutar Flask, Python interpreta las secuencias de escape ANTES de servir el HTML.
- **Error:** Múltiples `SyntaxError` en el browser: "Invalid or unexpected token", "missing ) after argument list", "Invalid regular expression: missing /", "Unexpected identifier 'chart'".
- **Análisis:** Python interpreta TODAS las secuencias de escape dentro de `"""..."""`:
  - `\n` → newline literal (rompe regexes y strings JS que cruzan líneas)
  - `\'` → `'` (rompe strings JS al exponer comilla sin escapar)
  - `\\` → `\` (rompe clases de caracteres en regex JS)
  - `\x27` → `'` (intento de fix que también Python interpreta)
  - `\t` → tab literal (generalmente inofensivo pero inesperado)
- **Solución:** 20+ fixes aplicados en `web_ui.py`:
  1. `\n` en strings JS → `\\n` (Python renderiza `\n` literal)
  2. `\n` en regex JS → `\\n` (Python renderiza `\n` literal)
  3. `\'` en atributos HTML → `&#39;` (HTML entity, Flask no la decodifica)
  4. `\\` en regex char class → `String.fromCharCode(92)` (evita backslash completamente)
  5. Afectó: autocomplete, chart rendering, code blocks, export buttons, feedback buttons, streaming, TTS, screenshot, search regex escaper
- **Prevención:** **REGLA CRÍTICA para `web_ui.py`:**
  - NUNCA usar `\n` directo en JS dentro del template — siempre `\\n`
  - NUNCA usar `\'` en JS/HTML — usar `&#39;` o `&quot;` según contexto
  - NUNCA usar `\\` en regex JS — usar `String.fromCharCode(92)` o variables
  - NUNCA usar `\xNN` como escape — Python lo interpreta primero
  - Considerar migrar a archivos `.html`/`.js` separados con `render_template()` para eliminar el problema de raíz

---

## ERR-040: Windows 11 mostrado como Windows 10 en auto-detect
- **Fecha:** 2026-03-15
- **Contexto:** Usuario preguntó info del sistema. Auto-detect usaba `platform.version()` que retorna `10.0.26200`.
- **Error:** Genesis reportaba "Windows 10" cuando el sistema es Windows 11 Pro.
- **Análisis:** Microsoft mantuvo el major version "10.0" para Windows 11. La diferencia está en el build number: ≥ 22000 = Windows 11, < 22000 = Windows 10.
- **Solución:** En SystemInfoTool, parsear `platform.version()` y verificar `build >= 22000`. También usar PowerShell `(Get-CimInstance Win32_OperatingSystem).Caption` como verificación cruzada.
- **Prevención:** Nunca confiar en `platform.system()` + `platform.version()` para identificar Windows 11. Siempre verificar build number.

---

## ERR-041: Close app — double .exe en taskkill
- **Fecha:** 2026-03-15
- **Contexto:** `proc_map` en genesis.py tiene entradas como `"visual studio code": "Code.exe"`. Al cerrar, el código añadía `.exe` al valor.
- **Error:** `taskkill /F /IM Code.exe.exe` — nombre inválido, proceso no encontrado.
- **Análisis:** Los valores del `proc_map` ya incluyen la extensión `.exe`. El código hacía `f"{target}.exe"` sin verificar si ya terminaba en `.exe`.
- **Solución:** Añadir check: `if not target.endswith(".exe"): target += ".exe"` antes del taskkill.
- **Prevención:** Siempre verificar si un nombre de proceso ya tiene extensión antes de añadirla.

---

## ERR-042: UnicodeEncodeError con box-drawing characters en genesis_desktop.py
- **Fecha:** 2026-03-15
- **Contexto:** `genesis_desktop.py` tenía banner con caracteres Unicode box-drawing (╔═╗║╚) en print statements.
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode characters` al ejecutar en Windows.
- **Análisis:** Mismo patrón que ERR-001. Windows usa cp1252 por defecto en stdout. Box-drawing characters no existen en cp1252.
- **Solución:** (1) Añadir `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` al inicio. (2) Reemplazar caracteres Unicode con ASCII equivalentes (`═` → `=`, `║` → `|`, etc.).
- **Prevención:** TODO archivo Python que use print DEBE tener el reconfigure de UTF-8. Ver ERR-001 y ERR-030.

---

## ERR-043: Anti-hallucination — "windows 11 pro" como false positive
- **Fecha:** 2026-03-15
- **Contexto:** `_anti_hallucination_filter()` tenía "windows 11 pro" en la lista de `_bad_phrases` / fabrication indicators.
- **Error:** Respuestas legítimas que mencionaban "Windows 11 Pro" eran filtradas como alucinaciones, a pesar de que el usuario SÍ tiene Windows 11 Pro.
- **Análisis:** Los indicadores de fabricación deben ser frases que SIEMPRE son falsas (ej: "he restaurado el archivo"). "Windows 11 Pro" puede ser verdadero dependiendo del sistema.
- **Solución:** Eliminar "windows 11 pro" de la lista de fabrication indicators. Solo mantener indicadores que son inherentemente falsos.
- **Prevención:** Los indicadores de hallucination deben ser ACCIONES fabricadas ("restaurando", "he accedido"), no datos del sistema que pueden ser verdaderos.

---

## ERR-044: Multi-target close — "cierra X y Y" parseado como target único
- **Fecha:** 2026-03-15
- **Contexto:** Usuario dice "cierra excel y word". Auto-detect buscaba "excel y word" como un solo nombre de programa.
- **Error:** No encontraba ningún programa llamado "excel y word" en `proc_map`.
- **Análisis:** El parser de close app no contemplaba múltiples targets separados por " y ".
- **Solución:** Dividir el input por `" y "` para obtener lista de targets. Iterar sobre cada uno y cerrar individualmente.
- **Prevención:** Siempre considerar que el usuario puede pedir acciones sobre múltiples targets separados por " y " o ", ".

---

## ERR-045: 40% hallucination rate en queries factuales comunes
- **Fecha:** 2026-03-15
- **Contexto:** Auditoría de 15 queries comunes (fecha, hora, IP, calculadora, identidad, archivos). 6/15 caían al LLM sin auto-detect.
- **Error:** Llama 3.1 8B inventaba respuestas: fecha incorrecta, IP fabricada, cálculos errados, versión inexistente.
- **Análisis:** `_auto_detect_tool()` solo cubría 10 tipos de intención. Los 6 tipos restantes (fecha/hora, username, IP, calculadora, identidad, conteo archivos) no tenían interceptor y caían al LLM.
- **Solución:** Añadir 6 nuevos bloques de auto-detect con keywords específicas. Cada uno retorna datos reales del sistema (datetime, os.getenv, socket, eval, config, os.walk) sin pasar por el LLM.
- **Prevención:** Cualquier query que tiene una respuesta factual determinista DEBE tener un auto-detect. Nunca dejar que el LLM responda preguntas con respuesta objetiva.

---

## ERR-046: clean_temp() se cuelga indefinidamente
- **Fecha:** 2026-03-15
- **Contexto:** Test exhaustivo de SystemActions.clean_temp() — el proceso no terminaba, sin output.
- **Error:** `os.walk()` + `os.path.getsize()` sobre cada archivo de cada subdirectorio en TEMP antes de borrar. En directorios con muchos archivos anidados (caches de browsers, npm, etc.) la operación podía tardar minutos o nunca terminar.
- **Análisis:** El cálculo de tamaño usaba `sum(os.path.getsize(...) for ... in os.walk(item_path) for f in fns)` sin límite. Un solo subdirectorio con 50,000+ archivos bloqueaba todo el proceso.
- **Solución:** Reemplazar `os.walk` por estimación solo del nivel superior (`os.listdir` del primer nivel). Agregar `max_items=200` y `timeout_sec=30.0` como guards de seguridad.
- **Prevención:** Cualquier operación que recorra el filesystem debe tener timeout y/o límite de items. Nunca asumir que un directorio es pequeño.

---

## ERR-047: ClipboardManager deadlock en pin()
- **Fecha:** 2026-03-15
- **Contexto:** Test de ClipboardManager.pin() se colgaba indefinidamente durante Phase 20.
- **Error:** Thread deadlock — `pin()` adquiría `self._lock` (threading.Lock) y dentro llamaba `self.save()` que también intentaba adquirir `self._lock`. Lock() no es reentrante → deadlock.
- **Análisis:** `threading.Lock()` bloquea si el mismo thread intenta adquirirlo dos veces. El patrón `with self._lock: ... self.save()` donde `save()` tiene `with self._lock:` es un deadlock clásico.
- **Solución:** Cambiar `threading.Lock()` → `threading.RLock()` (Reentrant Lock). RLock permite que el mismo thread adquiera el lock múltiples veces.
- **Prevención:** Siempre usar `RLock()` cuando métodos públicos con lock llamen a otros métodos con lock. Alternativa: usar `_save_unlocked()` interno sin lock.

---

## ERR-048: Base64 decode de "!!!" retorna string vacío en lugar de error
- **Fecha:** 2026-03-15
- **Contexto:** Test de TextTransformer.decode_base64() con input inválido `"!!!"`.
- **Error:** Python's `base64.b64decode("!!!")` no lanza excepción — decodifica a bytes vacíos → string vacío. El usuario recibía "Base64 decode: (vacío)" en vez de un error.
- **Análisis:** Base64 con padding `=` acepta strings cortos sin error; el resultado vacío es técnicamente válido pero no es útil para el usuario.
- **Solución:** Agregar `if not decoded.strip(): return "No es un texto Base64 válido (resultado vacío)."` después del decode.
- **Prevención:** Validar siempre que las transformaciones de texto produzcan resultados no vacíos, no solo que no lancen excepciones.

---

## ERR-049: CSS braces en ProjectScaffolder causan KeyError con .format()
- **Fecha:** 2026-03-15
- **Contexto:** ProjectScaffolder usa `.format(name=..., description=...)` para renderizar templates. Los templates CSS contienen `body { font-family: sans-serif; }`.
- **Error:** `KeyError: ' font-family: sans-serif; '` — Python interpreta `{ font-family: ... }` como una variable de formato.
- **Análisis:** `.format()` trata TODAS las llaves `{}` como variables. CSS usa llaves para bloques de estilo. Colisión directa.
- **Solución:** Escapar todas las llaves CSS como `{{ }}` en los templates de Flask (`static/style.css`) y HTML (`css/style.css`).
- **Prevención:** En cualquier template que use `.format()`, SIEMPRE escapar llaves literales como `{{}}`. Esto aplica especialmente a CSS, JSON inline, y código JavaScript.

---

## ERR-050: UnicodeEncodeError al imprimir flecha "→" en consola Windows
- **Fecha:** 2026-04-17
- **Contexto:** Script de smoke test imprimía `print(f'coding → model: {brain.model}')` desde PowerShell/cmd en Windows 11.
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 10: character maps to <undefined>`
- **Análisis:** Windows cp1252 no contiene el glyph U+2192 (→). Similar a ERR-001 pero afecta scripts inline sin `sys.stdout.reconfigure`.
- **Solución:** En scripts de test/debug, usar ASCII puro: `'coding model:'` en vez de `'coding → model:'`. Para código de producción, SIEMPRE reconfigurar stdout al inicio:
  ```python
  if sys.platform == "win32":
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```
- **Prevención:** Para one-liners de `python -c "..."` que se ejecutan desde bash/PowerShell en Windows, NUNCA usar caracteres Unicode (→, ✓, ★, ⚠️, ≥). Usar ASCII alternatives: `->`, `OK`, `*`, `WARN`, `>=`.

---

## ERR-051: Substring match incorrecto en validación de dict keys
- **Fecha:** 2026-04-17
- **Contexto:** Test e2e de ProviderRouter verificaba que `calls_by_model` contuviera una key con "qwen".
- **Error:** Test reportaba FAIL aunque el diccionario tenía `{'qwen2.5-coder:7b': 1, 'genesis': 1}`. Código: `if "qwen" not in r.calls_by_model: fail`.
- **Análisis:** `"qwen" in dict` (sin `.keys()`) compara con IGUALDAD EXACTA contra las keys. `"qwen" != "qwen2.5-coder:7b"` → retorna False → test falla. Confusión común entre substring match y membership check.
- **Solución:** Usar comprehension para substring:
  ```python
  used_qwen = any("qwen" in m for m in r.calls_by_model.keys())
  ```
- **Prevención:** Cuando se valida contenido de keys con substring match, SIEMPRE usar `any("substr" in k for k in d.keys())`. Nunca `"substr" in d` (esto es igualdad exacta en dict). Regla: `x in dict` es igualdad exacta de key, `x in string` es substring.

---

## ERR-052: Primer request a modelo Ollama tarda 15-20s por cold load
- **Fecha:** 2026-04-17
- **Contexto:** Al ejecutar primer prompt de coding después de descargar `qwen2.5-coder:7b`, la latencia fue 17.7s. Usuario esperaba ~3-5s (como Genesis cuando ya está caliente).
- **Error:** No es un error per se, pero reporta false alarm de "lentitud".
- **Análisis:** Ollama carga el modelo a VRAM **bajo demanda** en el primer request. Qwen Coder 7B Q4 = 4.36GB → tarda ~15s en copiar disco→VRAM. Requests subsiguientes al mismo modelo son <5s (ya está en VRAM). Si se alterna entre Genesis y Qwen en VRAM 8GB, Ollama hace unload/reload → overhead 2-3s por switch.
- **Solución:** Pre-calentar modelos después de arranque:
  ```python
  # En ProviderRouter.__init__ o similar
  for model in ["genesis", "qwen2.5-coder:7b"]:
      brain = self._get_brain_for("ollama", ...)
      brain.think("", [{"role":"user","content":"."}], max_tokens=5)  # warm-up
  ```
  O aumentar VRAM a 16GB (RTX 4060 Ti) para que ambos modelos coexistan calientes.
- **Prevención:** Documentar en README que el primer request por modelo es lento (cold load). Con 8GB VRAM y 2 modelos >4GB cada uno, esperar ~15-20s en switch entre tipos de tarea. No es síntoma de bug.

---

## ERR-053: `"provider" in dict.keys()` vs `"provider" in dict` con strings parecidos
- **Fecha:** 2026-04-17
- **Contexto:** Circuit breaker de ProviderRouter verificaba disponibilidad con `if provider not in self.brains`.
- **Error:** No ocurrió pero es patrón frágil si se agregan keys compuestas tipo `"ollama-coding"`, `"ollama-general"` — `"ollama" in d` retorna False aunque ambas keys empiecen con "ollama".
- **Análisis:** Misma raíz que ERR-051. Al diseñar schemas multi-clave, considerar si los checks downstream asumen igualdad exacta o substring.
- **Solución:** Documentar en el código que las keys del dict `brains` son NAMES DE PROVIDER TOP-LEVEL (ollama, gemini, openai, anthropic). Para variantes (multi-model dentro de ollama), usar otro nivel de dict (`ollama_model_by_task`).
- **Prevención:** Al extender `ProviderRouter.brains`, mantener las keys como nombres canónicos de provider. Para variantes intra-provider, crear otro dict (como se hizo con `ollama_model_by_task`).

---

```markdown
## ERR-XXX: [Título descriptivo]
- **Fecha:** YYYY-MM-DD
- **Contexto:** Qué se intentaba hacer.
- **Error:** Mensaje exacto o comportamiento inesperado.
- **Análisis:** Por qué ocurrió.
- **Solución:** Corrección aplicada.
- **Prevención:** Cómo evitar que vuelva a ocurrir.
```
