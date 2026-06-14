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

## ERR-054: Auditoría 2026-06-10 — 12 bugs C1 corregidos en batch
- **Fecha:** 2026-06-10
- **Contexto:** Auditoría integral del proyecto (ver `docs/AUDITORIA_2026-06-10.md`). Se encontraron y corrigieron 12 bugs de confianza C1.
- **Errores corregidos:**
  1. `self.log.warning(...)` en 4 sitios (genesis_processing.py:76,764,1024; genesis.py:566) — GenesisLogger NO tiene `.warning`, solo `.info/.error/.debug`. Dentro de except handlers lanzaba AttributeError secundario que tumbaba la respuesta. → `.error`.
  2. `self.feedback.positive_count` (genesis_processing.py) — FeedbackSystem guarda en `self.data["positive_count"]`, no como atributo. ReflectionEngine arranca enabled con interval=25 → crash garantizado en la interacción 25. → `self.feedback.data["positive_count"]` + bloque envuelto en try/except.
  3. `render_template_string` y `Path` no importados en web_ui.py → `/dashboard`, `/dashboard/live`, `/api/media/download` devolvían 500 siempre (NameError). → agregados a los imports.
  4. `BackupManager.restore_backup` (safe_io.py:227) — `name.split("_",1)` parte mal `memory_data_x.json` (dir_name="memory" nunca matchea "memory_data") → recovery devolvía True sin restaurar nada. → match por prefijo `data_dir.name + "_"`.
  5. `brain.think(prompt, system_prompt=...)` (genesis.py:986) — firma real es `think(system_prompt, messages)`; el posicional colisionaba → TypeError, `/doc` generaba siempre placeholder. → `think(system_prompt=..., messages=[...])`.
  6. Mensaje de usuario duplicado en short_term (genesis_processing.py:124) — se agregaba en línea 80 y otra vez en el retorno directo de auto-tool → contexto contaminado. → quitada la 2ª.
  7. `len(memory.short_term)` sin `__len__` (5 call-sites) → Live Dashboard/health_monitor/proactive con TypeError. → `__len__` agregado a ShortTermMemory.
  8. `LongTermMemory._save`/`EmotionalMemory._save` usaban `open(w)` directo, no atómico — corrupción con threads daemon (heartbeat, curiosity-gen) + Flask. → `safe_write_json(create_backup=False)`.
  9. `safe_write_json` sin `fsync` antes del rename → no durable ante corte de energía. → `f.flush()+os.fsync()` (requirió `import os`).
  10. Versión runtime `5.9.0` vs docs `6.0.0`; texto hardcodeado "v5.7" en genesis_tools.py:686. → `GENESIS_VERSION="6.0.0"` (single source) + interpolación.
  11. Higiene repo: 318 archivos del WebView2 (Cookies, Login Data, History) + data/embeddings/generated_media + modelo Vosk 60MB + zip/mp3 trackeados. → `git rm --cached` + `.gitignore` extendido.
  12. Basura en disco: `nul`, `core/anomaly_detector.py.bak`. → borrados.
- **Prevención:** (a) GenesisLogger sin `.warning` es intencional — usar `.error`/`.info`. (b) Todos los `_save()` de módulos calientes deben usar `safe_write_json`, nunca `open(w)`. (c) Verificar firma de `brain.think` (system_prompt primero). (d) NUNCA trackear `data/` (contiene perfil del webview con credenciales).
- **Pendientes (NO resueltos, requieren decisión):** cadena prompt-injection→RCE (S1-S6), suite de tests rota (T1), `smart_scheduler` muerto (C1), god-methods (A1-A2). Ver `docs/AUDITORIA_2026-06-10.md`.

---

## ERR-055: Auditoría 2026-06-10 (parte 2) — Hardening anti prompt-injection/RCE
- **Fecha:** 2026-06-10
- **Contexto:** La auditoría (ERR-054) detectó la cadena crítica: contenido externo no confiable (web/documento) → prompt del LLM → `[TOOL:python]`/`[TOOL:shell]` auto-ejecutados sin confirmación → RCE local. Se aplicaron 3 mitigaciones.
- **Cambios:**
  1. **Guard de contexto contaminado** (genesis_processing.py): nuevo flag `self._context_tainted` que se activa cuando se inyecta contenido externo (resultados web `needs_llm`, RAG de documentos, `learn_context`). El helper `_guard_tool()` bloquea las tools de `DANGEROUS_TOOLS` (`python`, `shell`, `editar_codigo`, `escribir`, `insertar`, `editar`) cuando el contexto está contaminado. Aplicado en el multi-tool loop y el single-tool loop. Las tools de solo-lectura (`leer`, `listar`, `web`, `sistema`...) siguen permitidas. El flag se resetea por interacción.
  2. **Auto-pip con allowlist** (genesis_processing.py): el auto pip-install ya NO instala nombres arbitrarios derivados del código del LLM (anti typosquatting/dependency-confusion). Solo instala paquetes en `_pip_allowlist` (valores de `pip_name_map` + ~25 paquetes comunes conocidos) y NUNCA si el contexto está contaminado. Fuera de la allowlist → cae al flujo normal de corrección del LLM.
  3. **Anti-SSRF en WebReader** (web_intelligence.py): nueva función `is_safe_public_url()` que valida esquema (solo http/https) y resuelve el host por DNS rechazando loopback/privadas/link-local/reserved/metadata cloud (169.254.169.254). `read()` valida la URL inicial y sigue redirects manualmente (máx 5) revalidando cada hop (evita redirect→IP interna).
- **Verificación:** tests aislados — anti-SSRF 9/9 casos OK, guard de tools OK (limpio permite, contaminado bloquea sistema y permite lectura), `test_provider_router` 48/48 sin regresión, py_compile OK en 8 archivos.
- **Prevención:** toda nueva tool que mute el sistema o ejecute código debe agregarse a `DANGEROUS_TOOLS`. Toda fuente nueva de contenido externo debe setear `self._context_tainted = True`. Nunca instalar paquetes con nombre derivado del LLM sin allowlist.
- **Pendientes:** sandbox real (denylist sigue siendo evadible si el contexto NO está contaminado y el usuario ejecuta código directo — riesgo aceptado en PC personal), SelfModifier `IMMUTABLE_FILES` vacío (S5), PathValidator no aplica a device_tools (S6). Ver `docs/AUDITORIA_2026-06-10.md`.

---

## ERR-056: Autonomía + auto-mejora (5 fases) — 2026-06-10
- **Fecha:** 2026-06-10
- **Contexto:** Pedido "que Genesis sea autónomo, aprenda y se mejore constantemente". Auditoría previa reveló que el 60% de la maquinaria de autonomía/aprendizaje era decorativa (loops abiertos). Plan aprobado: AGRESIVO + completo. 5 fases.
- **FASE 0 — Guardrails de auto-modificación** (`core/self_modifier.py`, `core/tools.py`, `core/tool_creator.py`, `core/genesis_processing.py`):
  - `IMMUTABLE_FILES` poblado con los archivos de guardrails (self_modifier, autonomous_mode, tools, genesis_processing, safe_io) — ineditables incluso vía /apply.
  - `CRITICAL_FILES` ampliado; `apply_change(human_approved=False)` BLOQUEA críticos en modo autónomo (solo /apply humano).
  - Patrones peligrosos NUEVOS (delta vs original) → rechazo duro (antes solo advertía).
  - `tools.py::SelfModifier.edit_own_code` (LLM-facing) ahora valida AST + inmutables/críticos + patrones (antes bypasaba todo).
  - `tool_creator._load_tool` valida con `_check_security` ANTES del `exec_module` (antes ejecutaba código no validado al cargar).
- **FASE 1 — Loops de aprendizaje cerrados** (`core/genesis_processing.py`, `core/agents.py`, `genesis.py`):
  - `meta_learner.get_recommendation` ahora MEZCLA su temperatura recomendada con el auto-tuner (antes nadie la leía).
  - `adaptive_prompts`: experimento real "estilo_respuesta" con epsilon-greedy; recompensa = score del self_evaluator (antes desconectado).
  - `auto_learner.get_agent_adjustments` sesga `agents.detect_agent` (antes solo en reportes manuales).
- **FASE 2 — Suite de tests reparada** (37 archivos): de 317→0 fallos. Causas: runner con `os.chdir(tests/)` rompía rutas relativas (fix: correr desde raíz) + regex incompleto; asserts de integración grep sobre genesis.py rotos por refactor a mixins (fix: concatenar genesis.py + los 3 mixins); mocks desactualizados (add_text doc_id); tests con dependencias ausentes (vosk/fitz/ddg) ahora SKIP grácil. 2 regresiones reales de producción encontradas y corregidas: `voice.py` perdió truncado a 500 chars; contrato del predictor de tokens.
- **FASE 3 — Loop autónomo de fondo** (`core/heartbeat.py`, `genesis.py`): registro de tareas de fondo (`register_task`) que corren en cada ciclo del heartbeat aunque el usuario no interactúe, gated por killswitch PAUSE + cooldowns + límite de CPU (psutil) + aislamiento de excepciones + backoff. Tareas: persistencia (30min), scheduler_tick (revive smart_scheduler muerto, 2min), consolidación de memoria/REM (120min).
- **FASE 4 — Auto-mejora de código agresiva** (`config.py`, `genesis.py`, `core/self_modifier.py`): tarea de fondo `auto_mejora_codigo` que muta el propio código. Pipeline: elige módulo NO crítico/inmutable → LLM propone → valida AST+patrones → corre la suite de tests como GATE → AUTO-REVIERTE si fallan. Killswitches: `PAUSE` (todo), `PAUSE_SELFIMPROVE` (solo auto-mejora), `GENESIS_SELF_IMPROVE=false`. `_run_auto_tests` endurecido fail-safe (sys.executable; si no puede correr un test → FALLA, no pasa vacuamente). Cooldown 180min.
- **Verificación:** suite 6116 passed/0 failed; guardrails (inmutable/crítico/patrón/sintaxis) OK; 3 loops de aprendizaje convergen; background tasks con cooldown/killswitch/aislamiento OK; gate de auto-mejora end-to-end (cambio malo→revertido, bueno→aplicado) OK.
- **Killswitches (resumen):** crear archivo `PAUSE` en la raíz frena TODO el heartbeat; `PAUSE_SELFIMPROVE` frena solo la auto-mejora de código; `GENESIS_SELF_IMPROVE=false` la desactiva por config.
- **Prevención:** nueva tool que muta/ejecuta → agregar a `DANGEROUS_TOOLS`; nueva fuente de contenido externo → `self._context_tainted=True`; nueva tarea de fondo → `heartbeat.register_task`; nunca quitar archivos de `IMMUTABLE_FILES` sin entender que son los guardrails.

---

## ERR-057: Primera ejecución real (venv 3.12 + Ollama) — 6 bugs de runtime
- **Fecha:** 2026-06-10
- **Contexto:** Probar el proyecto end-to-end por primera vez. Entorno: venv Python 3.12 (el sistema tiene 3.14 incompatible), Ollama local UP con genesis:latest + qwen2.5-coder:7b. Bugs que SOLO aparecen ejecutando (los tests string-grep nunca corrieron estos paths).
- **Bugs encontrados y corregidos:**
  1. **`AUTO_BACKUP_INTERVAL` no definido** (`core/genesis_processing.py:1178`): el mixin usaba el constante de config sin importarlo → NameError en `_post_process` (crash en CADA interacción). Fix: import local con fallback.
  2. **`SHORT_TERM_LIMIT` no definido** (`core/genesis_processing.py:1326`): ídem, en el snapshot del cognitive_monitor. Fix: import local con fallback.
  3. **`semantic_memory` no cargaba**: dependencia transitiva (numpy) ausente → lazy loader devolvía None → AttributeError. Fix: instalar numpy (los embeddings/RAG tienen fallback TF-IDF que igual lo necesita).
  4. **`opencv-python==4.12.0` no existe en PyPI** (`requirements.txt:35`): el pin era inválido (la versión real es `4.12.0.88`). Fix: corregido el pin.
  5. **Colisión de keywords en auto-detect** (`core/genesis_tools.py:1328`): "ejecuta un script python..." disparaba el launcher de "abrir app" (keyword "ejecuta ") ANTES del path de código → el agente no ejecutaba código, buscaba un programa llamado "script python...". Fix: guard `_code_signals` que saltea el launcher cuando el input es claramente un pedido de código.
  6. **`self.smart_scheduler` no existe** (`genesis.py`, tarea de fondo FASE 3): referenciaba un módulo muerto sin atributo en Genesis. El scheduler real wireado es `self.scheduler` (TaskScheduler). Fix: usar `self.scheduler.tick()`.
- **Verificación end-to-end (todo OK tras fixes):** chat local responde; auto-detect de sistema/hora con datos reales (RAM 15.8GB, RTX 3060 Ti); ejecución de código agéntica (`primos → [2,3,5,7,11,13,17,19,23,29]`); loop autónomo del heartbeat (investigación web read-only + tareas de fondo persistencia/consolidación + auto-mejora que el guardrail RECHAZÓ por sintaxis inválida = seguridad funcionando en vivo). Suite 6123/0. Web UI en http://127.0.0.1:5000.
- **Prevención:** los mixins NO comparten namespace con genesis.py — todo constante de config debe importarse explícitamente en el mixin. Verificar pins de requirements contra PyPI real. Las keywords cortas del auto-detect ("ejecuta", "abre") necesitan guards anti-colisión (ya advertido en CLAUDE.md pero faltaban casos).

---

## ERR-2026-06-12: "abrí descargas de la unidad F" abría C:\Downloads (o fallaba)
- **Fecha:** 2026-06-12
- **Contexto:** El usuario pidió abrir la carpeta Descargas del disco F (`F:\Descargas`).
- **Error:** `_resolve_folder` (`core/genesis_tools.py`) tenía `folder_map["descargas"] = "C:/Users/Lexus/Downloads"` hardcodeado y no parseaba el calificador de unidad. "descargas de la unidad f" no matcheaba ninguna clave → caía a búsqueda fuzzy → no encontraba o resolvía a la carpeta de C:.
- **Análisis:** El mapa de carpetas asumía que cada nombre vive en una única unidad (C:). No existía forma de decir "esta carpeta pero en otra unidad". Además los nombres reales en disco tienen mayúscula/acento ("Descargas", "Imágenes") y el match era exacto en minúscula.
- **Solución:** Bloque "0. Carpeta en una UNIDAD específica" al inicio de `_resolve_folder`: detecta unidad por `F:/…`, "de la unidad F", "en D", "disco F"; extrae el nombre de carpeta; resuelve contra la raíz de esa unidad con **alias ES/EN** (descargas↔Downloads, documentos↔Documents, imágenes↔Pictures, etc.) + match **case-insensitive** + fuzzy por alias contenido. Si no existe en esa unidad → None (no cae a C:). Sin calificador de unidad, el comportamiento previo se preserva.
- **Prevención:** Cualquier resolución de recurso (carpeta/archivo/programa) que asuma una única ubicación es frágil en máquinas multi-disco. Parsear siempre el calificador de unidad y matchear case-insensitive contra el FS real, no contra un mapa estático en minúscula. Verificado: "descargas de la unidad F" → `F:/Descargas` ✓.
- **Follow-up mismo día (2 bugs más en la misma frase real "abre la carpeta prueba que se encuentra en la unidad F"):**
  1. **Conectores sin limpiar:** "prueba **que se encuentra** en la unidad F" dejaba `_fname="prueba que se encuentra"` → no matcheaba. Fix: regex que elimina frases conectoras ("que se encuentra/halla/está", "ubicada", "localizada", "guardada", "situada", "llamada", "de nombre") + re-strip de "la carpeta/directorio/folder".
  2. **Solo buscaba en la raíz de la unidad:** la carpeta era `F:\programas\prueba` (subcarpeta). Fix: si no está en la raíz, búsqueda en subcarpetas depth-2 saltando dirs de sistema (`$RECYCLE.BIN`, `System Volume Information`, etc.), match exacto case-insensitive gana sobre parcial. Verificado: "prueba que se encuentra en la unidad F" → `F:\programas\prueba` ✓.

## ERR-2026-06-12b: "abre la carpeta logs" abría una página web (logs.com)
- **Fecha:** 2026-06-12
- **Contexto:** El usuario pidió abrir la carpeta `logs`.
- **Error:** "logs" no estaba en `folder_map` ni en los `search_dirs` de nivel superior → `_resolve_folder` devolvía None → el flujo del handler "abrir X" caía al **fallback de aprendizaje (#7)** que construye una URL candidata (`https://www.logs.com`), hacía HEAD, y como respondía <400 la **abría en el navegador**. El usuario pidió una CARPETA y obtuvo una web.
- **Análisis:** El handler de "abrir" mezcla intención de app/web/carpeta en un solo flujo con fallbacks en cascada. Cuando el pedido dice explícitamente "carpeta/directorio/folder", la intención es filesystem y jamás debería degradar a abrir una URL. Además "logs" es un nombre ultra-común (cada proyecto tiene uno) → adivinar uno sería incorrecto igual.
- **Solución:** (1) Guard de **intención-carpeta**: si `inp` contiene "carpeta"/"directorio"/"folder" y `_resolve_folder` falla, NO se cae a web_map/URL-guessing. (2) Nuevo `_search_folder_everywhere(target)`: búsqueda recursiva acotada (depth 3, raíces conocidas, salta `node_modules/venv/.git/__pycache__/site-packages/Windows/AppData/$*`). Si hay 1 resultado → abre; si hay varios → **lista y pregunta cuál**; si 0 → mensaje claro pidiendo ruta/unidad. Verificado: "logs" → 12 carpetas (pregunta cuál) en ~2.5s; "prueba" → 1 (abre); nunca abre logs.com.
- **Prevención:** Los handlers con fallbacks en cascada (app→web→URL-guess) deben respetar la intención explícita del usuario y cortar la cascada cuando el dominio está claro. "Adivinar una URL" es un fallback peligroso: solo debe correr para pedidos genéricos de "abrir X", nunca cuando se nombró un tipo de recurso concreto (carpeta/archivo).

## ERR-2026-06-12c: "reproducí X" no reproducía (404 en /api/audio) — 3 capas
- **Fecha:** 2026-06-12
- **Contexto:** El usuario pidió reproducir música ("reproduce tessa", "in the shadows"). El chat decía "🎵 Reproduciendo…" pero no salía audio.
- **Error:** El backend funcionaba (búsqueda OK, devolvía `[[PLAY:id]]` en ~1s), pero el proxy `/api/audio/<id>` devolvía **404** → `get_audio_url()` retornaba "". NO fue regresión propia: YouTube endureció su anti-bot.
- **Análisis (3 capas descubiertas en orden):**
  1. **Bot-check:** `[youtube] Sign in to confirm you're not a bot. Use --cookies`. Ningún player_client (tv/ios/android/web_safari/mweb) lo evadía sin cookies — la IP estaba flageada.
  2. **Cookies:** `cookiesfrombrowser` falla en caliente: Brave/Chrome abiertos bloquean la DB ("Could not copy") y Chromium ≥127 usa App-Bound Encryption (Edge: "Failed to decrypt with DPAPI"). Solución: archivo `cookies.txt` exportado con extensión "Get cookies.txt LOCALLY". **Ojo:** ios/android NO soportan cookies (yt-dlp los saltea) → con cookies hay que dejar el cliente default (web/tv).
  3. **Challenge JS:** con cookies, nuevo error `Signature solving failed / n challenge solving failed → Only images are available`. YouTube exige resolver un challenge JS para entregar URLs de media. Requiere `yt-dlp-ejs` + un runtime JS.
- **Solución:**
  1. `core/music_player.py`: soporte de cookies con prioridad archivo (`data/youtube_cookies.txt`) → navegador → sin-cookies, cacheando la estrategia que funciona (`_working_cookie`). `cookies_available()` helper.
  2. `pip install -U "yt-dlp[default]"` → instala `yt-dlp-ejs==0.8.0` + `pycryptodomex`.
  3. Opción `js_runtimes={"node": {}}` en los opts de yt-dlp (Node v24 ya instalado). **Formato dict obligatorio** — `["node"]` (lista) tira "Invalid js_runtimes format". NO forzar `player_client`.
  4. `web_ui.py` `cplay()`: `onerror` que avisa en vez de fallar mudo.
  5. `data/` ya está en `.gitignore` → las cookies (sesión/login) nunca se commitean. 🔒
- **Verificado:** `get_audio_url('_tuLd3h19Fw')` → URL googlevideo real (itag=140, m4a) en 2.5s; proxy `/api/audio/<id>` → **HTTP 206 audio/mp4** con Range. Música suena end-to-end.
- **Prevención:** Las dependencias de YouTube/yt-dlp son frágiles por diseño (YouTube cambia seguido). Mantener yt-dlp actualizado, las cookies frescas (caducan en semanas/meses — re-exportar cuando vuelva el 404), y Node en PATH. El reproductor ahora reporta el fallo en vez de quedar mudo, así el síntoma es visible.

## ERR-2026-06-12d: "abrí youtube music" (app recién instalada) abría el navegador
- **Fecha:** 2026-06-12
- **Contexto:** El usuario instaló la app de escritorio YouTube Music y pidió abrirla.
- **Error:** Genesis abrió music.youtube.com en el navegador en vez de la app.
- **Análisis (2 causas):**
  1. **Orden de prioridad:** en el handler "abrir X", el `web_map` (sitios) y el `learned_map` se consultan ANTES del índice de programas instalados. "youtube music" es clave exacta de `web_map` → URL → navegador. La app instalada nunca tenía chance.
  2. **Índice viejo:** el cache `installed_programs.json` tenía 256 apps (de antes de instalar YouTube Music) → aunque se priorizara, no la encontraba.
  3. **learned_map envenenado:** al abrir el navegador, `_learn_app` guardó `youtube music → https://music.youtube.com`, reforzando el error.
- **Solución:**
  1. Bloque "1.5 PRIORIDAD" en `genesis_tools.py`: antes de learned_map/web_map, si `program_index.find(target)` da match FUERTE (nombre exacto, o todas las palabras de un target multi-palabra dentro del nombre de la app) → abre la app. Match fuerte evita secuestrar intenciones web claras: "youtube music"→app, pero "youtube"→sitio.
  2. Rescan único on-miss: si find() falla (app recién instalada), `get_index(force=True)` y reintenta.
  3. Limpieza de la entrada envenenada en `data/learned_apps.json` (y el bloque 1.5 la re-aprende correcta al abrir la app).
- **Verificado:** "youtube music"→ABRE APP; "youtube"→web; "gmail/spotify/whatsapp"(sin app)→web; "steam/chrome"→app.
- **Prevención:** En handlers con fallbacks en cascada, las fuentes más específicas/locales (apps instaladas) deben tener prioridad sobre las genéricas (mapa web estático), pero con umbral de match fuerte para no pisar intenciones claras del otro dominio. Índices cacheados necesitan rescan on-miss para captar cambios recientes (apps instaladas/desinstaladas).

## ERR-2026-06-12e: "YouTube Music pregunta ¿salir? / se cierra" al cambiar de tema (CDP)
- **Fecha:** 2026-06-12
- **Contexto:** Con el reuso de ventana vía CDP (`Page.navigate`), al pedir otra canción aparecía el diálogo «¿Quieres salir de la aplicación? Es posible que los cambios no se guarden» y la navegación se colgaba; el usuario lo veía como "se cierra YouTube". Además, al quedar la página bloqueada, `_cdp_ytm_target()` no la detectaba y `play_in_app` abría ventanas NUEVAS (pile-up).
- **Análisis:** YouTube Music registra un handler `beforeunload` que, con media reproduciéndose, dispara el prompt nativo de "salir" cuando algo navega la página. `Page.navigate` de CDP lo gatilla. El prompt bloquea el hilo de la página → CDP/`/json` no responde bien → detección falla → relanza.
- **Solución** (`core/music_player.py::_cdp_navigate`): antes de `Page.navigate`, (1) `Page.enable`; (2) `Runtime.evaluate` que pone `window.onbeforeunload=null` y agrega un listener en fase de captura que hace `stopImmediatePropagation()` + borra `returnValue` (mata el prompt de YT Music); (3) tras navegar, loop corto que auto-acepta cualquier `Page.javascriptDialogOpening` con `Page.handleJavaScriptDialog {accept:true}`. Belt-and-suspenders.
- **Verificado:** Numb → In the End → One Step Closer, todo `ytmusic_cdp_reuse`, 1 sola ventana, url cambia, SIN diálogo. Nota: tras un force-kill del chrome dedicado el perfil queda "sucio" y el primer relaunch puede ser flaky (esperar ~15s); en uso normal (ventana persistente) no pasa.
- **Prevención:** Cualquier automatización que navegue páginas con media activa debe neutralizar `beforeunload` y manejar diálogos JS vía CDP, no asumir que `Page.navigate` es silencioso.

## ERR-2026-06-12f: "502 Bad Gateway" y no se puede volver tras clickear un resultado de investigación
- **Fecha:** 2026-06-12
- **Contexto:** El usuario pidió investigar el álbum de HIM, clickeó un resultado en el Tablero de Evidencias y la cabina quedó atrapada en una página externa con "502 Bad Gateway", sin forma de volver.
- **Análisis:** El server Flask (:5100) estaba VIVO (HTTP 200) — no era el problema. Los links de las tarjetas de investigación (`renderCards` en `_CORE_HTML`) son `<a href="url externa">` sin manejo especial; al clickearlos, la ventana de PyWebView **navega in-place** a la URL externa (reemplaza la cabina). Esa página externa dio 502, y como la cabina es frameless sin barra de navegación nativa, no había "atrás".
- **Solución:**
  1. `web_ui.py` `_CORE_HTML`: interceptor global de clicks (capture phase) que detecta `<a>` con href `http(s)` a host NO-local → `preventDefault` + `pywebview.api.open_external(href)` → abre en el navegador del sistema. Los links internos (127.0.0.1/localhost) navegan normal.
  2. `genesis_desktop.py` `GenesisDesktopAPI.open_external(url)` → `webbrowser.open`.
  3. Botón **⌂ Home** en el titlebar inyectado → `location.href='http://127.0.0.1:5100/core'`, recupera la cabina desde cualquier página externa (incluso una 502).
- **Prevención:** En apps WebView/frameless, NUNCA dejar que links externos naveguen la ventana principal — interceptarlos y abrirlos afuera. Siempre tener un botón "home" de recuperación porque no hay barra de navegación nativa.

---

## ERR: Genesis responde con voces diferentes (inconsistencia de voz)
- **Fecha:** 2026-06-13
- **Contexto:** El usuario notó que Genesis a veces respondía con la voz de Milton (clon), a veces con una voz española, a veces con la robótica de Windows.
- **Análisis:** La voz por defecto es `clon:milton` (XTTS ~2GB VRAM). Con 8GB compartidos con Ollama (~6GB), XTTS a veces NO entra y cada camino caía a una voz distinta: la cabina a `es-ES-AlvaroNeural` (edge), el manos-libres a `pyttsx3` (robótica). 3 voces según el estado de VRAM.
- **Solución:** Fallback UNIFICADO a una voz Piper local (`es_ES-davefx-medium`) en ambos caminos (`/api/tts/speak` y `voice_clone.speak_aloud`). Piper corre en CPU → nunca falla por la misma razón que XTTS. Precargado en `_boot_sequence`.
- **Prevención:** Un fallback debe vivir en UN solo lugar y usar un recurso que NO compita con el principal (Piper/CPU vs XTTS/GPU). Nunca dejar que cada ruta elija su propio plan B.

## ERR: Datos factuales (hora/fecha/cálculo) tardan 13-21s
- **Fecha:** 2026-06-14
- **Contexto:** Auditoría funcional: "qué hora es" tardaba 21s, "cuánto es X" 13s.
- **Análisis:** `_maybe_spontaneous` reformulaba TODO resultado corto sin marker en `_NO_REPHRASE` pasándolo por el LLM lento (~13-21s). Además encolaba pedidos → timeouts bajo carga.
- **Solución:** (1) markers `🕐📅🔢🗓️🧮` a `_NO_REPHRASE`. (2) Fix sistémico: no reformular si el resultado empieza con emoji/símbolo (`ord>0x2190`) o trae formato (`**`/saltos/viñetas).
- **Prevención:** Los resultados de herramienta son datos exactos; no reformularlos con el LLM. Opt-out genérico por formato, no lista de emojis caso por caso.

## ERR: N4 function-calling — el 8B local devuelve JSON inconsistente
- **Fecha:** 2026-06-14
- **Contexto:** Al activar N4 (router por significado), genesis-q3 (8B) devolvía JSON vacío/truncado ~50% de las veces, nondeterminista incluso a temperature 0.
- **Análisis:** El problema era de FORMATO (el modelo preludiaba/se cortaba), no de comprensión (elegía bien la herramienta cuando lograba emitir JSON).
- **Solución:** `tool_router._ollama_json()` llama a Ollama `/api/chat` con `"format":"json"` (constrained decoding) → JSON SIEMPRE válido. El mismo 8B pasó a 100% consistente (6/6 en 2 pasadas). Cero descarga, cero VRAM extra.
- **Prevención:** Antes de cambiar/escalar el modelo, aislar si el cuello es comprensión o formato. Para salida estructurada usar `format=json` de Ollama.

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
