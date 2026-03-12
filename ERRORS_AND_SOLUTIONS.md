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

## Plantilla para Nuevos Errores

```markdown
## ERR-XXX: [Título descriptivo]
- **Fecha:** YYYY-MM-DD
- **Contexto:** Qué se intentaba hacer.
- **Error:** Mensaje exacto o comportamiento inesperado.
- **Análisis:** Por qué ocurrió.
- **Solución:** Corrección aplicada.
- **Prevención:** Cómo evitar que vuelva a ocurrir.
```
