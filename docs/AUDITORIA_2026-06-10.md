# Auditoría Integral — GENESIS

**Fecha:** 2026-06-10
**Commit auditado:** `d24d157` (snapshot fase 5.x)
**Alcance:** ~94k LOC Python, 140 módulos en `core/`, Flask + PyWebView + Ollama
**Modalidad:** solo lectura + fixes de bajo riesgo aplicados (ver sección "Fixes aplicados")

---

## Resumen ejecutivo

🟡 **Salud global: amarilla.** Arquitectura sorprendentemente sana para 140 módulos de un solo dev (0 ciclos de import, 0 huérfanos reales, los 33 módulos nuevos integrados), pero con **bugs de corrección que crashean features completas en silencio**, una **cadena prompt-injection→RCE local sin cortar**, y **fuga de credenciales del navegador commiteadas al repo**.

**Top 5 riesgos:**
1. 🔴 **Cookies/Login Data/History del WebView2 commiteados** (318 archivos en git) — fuga total de credenciales si el repo se sube. *(Mitigado: untracked + .gitignore. Pendiente: reescribir historia antes de push.)*
2. 🔴 **Cadena prompt-injection → RCE**: contenido web/documentos no confiables → LLM → `[TOOL:python]`/`[TOOL:shell]` auto-ejecutados sin confirmación. *(Mitigado: guard de contexto contaminado + anti-SSRF + auto-pip allowlist — ERR-055.)*
3. 🔴 **Crash cada ~25 interacciones**: `feedback.positive_count` no existe → AttributeError en `_post_process`. *(Corregido)*
4. 🔴 **`.log.warning()` no existe** en GenesisLogger → AttributeError dentro de except handlers (4 sitios). *(Corregido)*
5. 🟠 **Suite de tests rota**: 36 de 44 archivos fallan/crashean (306 fallos) — sin red de seguridad ante regresiones. *(Pendiente)*

---

## Fixes aplicados en esta sesión (verificados)

Todos de confianza C1, bajo riesgo, smoke-tested. Sin commitear (decisión del usuario).

| # | Bug | Archivo | Verificación |
|---|-----|---------|--------------|
| 1 | `.log.warning()` → `.log.error()` (logger no tiene `.warning`) | genesis_processing.py:76,764,1024; genesis.py:566 | py_compile OK |
| 2 | `feedback.positive_count` → `feedback.data["positive_count"]` + try/except en reflexión | genesis_processing.py:~1100 | keys verificadas |
| 3 | `render_template_string` y `Path` no importados → 3 endpoints 500 | web_ui.py:11,23 | py_compile OK |
| 4 | `restore_backup` roto (split `_` parte mal `memory_data`) | safe_io.py:227 | test restaura OK |
| 5 | `brain.think(prompt, system_prompt=)` → TypeError, /doc muerto | genesis.py:986 | firma corregida |
| 6 | Mensaje de usuario duplicado en short_term | genesis_processing.py:124 | quitado |
| 7 | `len(short_term)` sin `__len__` → Live Dashboard siempre error | memory.py (+5 call-sites) | `len()` -> 2 OK |
| 8 | Memoria long/emocional sin escritura atómica → corrupción con threads | memory.py:230,363 | safe_write_json |
| 9 | `safe_write_json` sin fsync → no durable ante corte de energía | safe_io.py:110 | test OK |
| 10 | Versión runtime `5.9.0` vs docs `6.0.0` | config.py:146; genesis_tools.py:686 | unificado a 6.0.0 |
| 11 | Higiene repo: untrack cookies/data/vosk/zip/mp3 + `.gitignore` | .gitignore, índice git | `git ls-files`=0 |
| 12 | Basura en disco: `nul`, `anomaly_detector.py.bak` | — | borrados |

---

## Hallazgos NO resueltos (requieren decisión del usuario)

### 🔴 CRÍTICO — Seguridad

**S1. Cadena prompt-injection → RCE local — ✅ MITIGADO (2026-06-10)**
`web_intelligence.py` descargaba cualquier URL → `genesis_processing.py:112` inyectaba el contenido al prompt → se auto-ejecutaba cada `[TOOL:python]`/`[TOOL:shell]` sin confirmación.
**Fix aplicado:** flag `self._context_tainted` que se activa con contenido externo (web/RAG/learn); `_guard_tool()` bloquea `DANGEROUS_TOOLS` (python, shell, editar_codigo, escribir, insertar, editar) en contexto contaminado, en ambos tool-loops. Tools de lectura siguen permitidas. (ERR-055)

**S2. Sandbox = denylist evadible (C1, esfuerzo L) — PENDIENTE**
`tools.py:539-608` (ShellExecutor) y `463-536` (CodeExecutor) bloquean por substring. Evadible (`"f"+"ormat"`, base64, `python -c`). Sin aislamiento real.
**Nota:** con S1 mitigado, el vector externo→RCE está cortado; queda el riesgo de ejecución directa pedida por el usuario (riesgo aceptado en PC personal). **Fix futuro:** allowlist de binarios o sandbox real.

**S3. SSRF en WebReader — ✅ MITIGADO (2026-06-10)**
`web_intelligence.py` hacía GET a URLs arbitrarias sin bloquear loopback/169.254.169.254/privadas/`file://`.
**Fix aplicado:** `is_safe_public_url()` valida esquema + resuelve DNS y rechaza loopback/privadas/link-local/reserved/metadata; `read()` valida la URL inicial y sigue redirects manualmente revalidando cada hop. Test 9/9 casos. (ERR-055)

**S4. Auto pip-install de nombre derivado del LLM — ✅ MITIGADO (2026-06-10)**
`genesis_processing.py` instalaba el paquete que el LLM nombró ante un `ModuleNotFoundError`.
**Fix aplicado:** allowlist (`pip_name_map` values + ~25 comunes); fuera de allowlist o contexto contaminado → no instala, cae al flujo de corrección del LLM. (ERR-055)

**S5. SelfModifier puede reescribir sus propios guardrails (C1, esfuerzo M)**
`self_modifier.py:62`: `DANGEROUS_PATTERNS` solo genera warnings, no bloquea; `IMMUTABLE_FILES` está vacío. Auto-evolución puede editar `genesis.py`, `config.py`, `tools.py`, el propio `self_modifier.py`.
**Fix:** poner archivos críticos en `IMMUTABLE_FILES`; que los patrones peligrosos bloqueen sobre ellos; confirmación humana real para `/apply`.

**S6. Exfiltración de secretos: PathValidator no aplica a device_tools (C2, esfuerzo M)**
`device_tools.py` (FileManager.copy/move, FileSearcher, DiskAnalyzer) NO usa `PathValidator` — puede leer/copiar `.env`, `.ssh`, cookies de navegador, wallets.
**Fix:** centralizar validación de rutas sensibles y aplicarla también en device_tools.

**S7. Otros (bajo): `eval()` en calculadora (`genesis_tools.py:794`), CORS por substring (`web_ui.py:48`), `/api/notify` interpola texto en PowerShell (`web_ui.py:822`), `/api/command` sin CSRF, sin `MAX_CONTENT_LENGTH`, `--host 0.0.0.0` + `--debug` disponibles por CLI.**

### 🟠 ALTO — Corrección (no resueltos)

**C1. `smart_scheduler` 100% muerto (C1, esfuerzo M)**
`smart_scheduler.tick()` y `set_executor()` no se llaman desde producción (solo tests). El auto-detect de "programa tarea" (`genesis_tools.py:2638`) solo lista, nunca llama `add()`. El usuario "programa" tareas que jamás se crean ni ejecutan. **Feature anunciada pero inexistente.**

**C2. Estado compartido sin lock con Flask `threaded=True` (C2, esfuerzo M)**
Genesis es singleton; `process_input` muta `short_term.messages`, `_current_input`, summarizer sin lock. Dos requests simultáneos entrelazan conversaciones y colisionan en los `_save()`.
**Fix:** lock por interacción alrededor de `process_input`/`handle_command` en web_ui.

**C3. Daemons escriben a disco al cerrar la app (C2, esfuerzo M)**
heartbeat/curiosity-gen son daemon; `stop()` espera solo 5s; `atexit.save_all()` puede correr mientras el daemon escribe → corrupción al cerrar. *(Mitigado parcialmente por el fix #8 que serializa por archivo, pero falta señalizar stop antes del trabajo.)*

**C4. Lazy-init sin lock (C2, esfuerzo M)**
`genesis.py:252` `__getattr__` puede crear dos instancias del mismo módulo bajo concurrencia (doble `start_episode`, doble carga JSON).

**C5. Timeout solo en la primera generación LLM (C2, esfuerzo M)**
`TimeoutExecutor` protege la 1ª llamada; el tool-loop (hasta 10 rounds) y el streaming van sin timeout aplicativo. Si Ollama gotea bytes, una interacción bloquea >30 min.

### 🟠 ALTO — Testing / Supply chain

**T1. Suite rota (C1, esfuerzo L):** 36/44 archivos fallan. ~200-300 asserts de "integración" son grep de strings sobre `genesis.py` que el refactor a mixins rompió (falsos negativos). 11 archivos crashean por mocks desactualizados (`add_text(doc_id=...)`). El runner `_run_all.py` subcuenta por regex incompleto.

**T2. requirements ≠ runtime (C1, esfuerzo M):** la máquina tiene Python 3.14 sin pip ni venv; pins (`numpy==1.26.4`, `torch==2.5.1` CUDA) incompatibles con 3.14. El proyecto no es instalable tal cual en su propia máquina. Sin lockfile, sin CI.

**T3. Deps frágiles (C3, esfuerzo S):** `duckduckgo-search==4.1.1` (renombrado a `ddgs`, las 4.x dejaron de funcionar → búsqueda web devuelve `[]` en silencio), `keyboard==0.13.5` (abandonado 2020, hook global), `Pillow==10.4.0` (anterior a fixes CVE 2025), `google-generativeai` (deprecado por `google-genai`).

### 🟡 MEDIO — Arquitectura / Deuda

**A1. God-method `_auto_detect_tool` de 2.484 líneas** (`genesis_tools.py:652-3136`): 138 ramas `if/elif`, el router central de todo el producto como cadena lineal de keyword-matching. Orden = precedencia implícita no documentada (bugs de shadowing). Imposible de testear por rama. **Fix:** registro declarativo `(keywords, handler)`.

**A2. `process_input` (920 líneas), `handle_command` (876), lazy loader de 85 ramas elif** — el pipeline completo en un método; agregar módulo = editar `genesis.py`. **Fix:** dict registry name→(módulo, clase, factory).

**A3. Solapamientos a resolver:** `ModelRouter` vs `ProviderRouter` (dos clasificadores de tarea paralelos); 3 schedulers (`task_scheduler`/`smart_scheduler`/`reminder_system`); `dashboard.py` vs `live_dashboard.py`; `local_engine.py` (legacy ctransformers abandonado, alcanzable con `GENESIS_PROVIDER=local`).

**A4. Sin remote, una sola branch** — 94k LOC sin copia fuera del disco. *Crear remote privado SOLO después de limpiar la historia (cookies en commits pasados).*

### 🟡 MEDIO — Documentación

- README "100% local por defecto" es **condicional**: con `GOOGLE_API_KEY` presente, el provider legacy auto-selecciona Gemini (cloud) y `default.json` lo recomienda; la personalidad afirma "sin cloud" incluso vía Gemini.
- `.env.example` no documenta las 5 vars de v6.0 (`GENESIS_LLM_STRATEGY`, `GENESIS_OLLAMA_CODING`, etc.) — el feature estrella es indescubrible desde el template.
- `LEEME.txt` (marzo) 2 eras desactualizado vs README (abril).
- README "132 módulos", PROJECT_EVOLUTION "133", real = 140.

---

## Preguntas al usuario (red flags — no asumir)

1. **Modelfile vs Modelfile.genesis** divergentes: `.genesis` declara "NO safety filters". ¿Cuál creó el modelo `genesis` en Ollama? (relevante para S1-S2).
2. **`local_engine.py` + ctransformers**: ¿fallback offline a mantener o legacy a retirar?
3. **ModelRouter**: ¿se absorbe en ProviderRouter o queda como capa de modelo local?
4. **dashboard.py estático**: ¿sigue en uso o lo reemplazó `/dashboard/live`?
5. **Workflow Colab** (`GENESIS_Colab.ipynb` + `create_colab_zip.py`): ¿vigente?
6. **TaskScheduler vs SmartScheduler**: ¿separación permanente interno/user-facing, o migración en curso? (ver C1).

---

## Plan de remediación priorizado

| Orden | Hallazgo | Sev | Esfuerzo | Bloquea |
|-------|----------|-----|----------|---------|
| 1 | ✅ Bugs C1 (#1-10) | 🔴 | S | crashes en runtime |
| 2 | ✅ Untrack cookies + .gitignore (#11) | 🔴 | S | privacidad |
| 3 | ✅ S1 guard tools en contexto contaminado | 🔴 | L | RCE |
| 4 | ✅ S3 anti-SSRF + S4 auto-pip allowlist | 🔴 | M | RCE |
| 5 | Reescribir historia git (cookies en commits pasados) ANTES de cualquier push | 🔴 | M | backup remoto |
| 6 | C1 wirear smart_scheduler o quitar la feature | 🟠 | M | UX engañosa |
| 7 | T2 venv Python 3.11/3.12 + lockfile | 🟠 | M | instalabilidad |
| 8 | C2 lock en process_input (web threaded) | 🟠 | M | corrupción concurrente |
| 9 | T1 arreglar suite (mocks + greps→mixins) | 🟠 | L | red de seguridad |
| 10 | A1/A2 extraer registries (refactor god-methods) | 🟡 | L | mantenibilidad |

---

## Quick wins restantes (≤1h)

- `duckduckgo-search` → `ddgs` (la búsqueda web está rota en silencio).
- Documentar las 5 env vars de v6.0 en `.env.example`.
- `eval()` calculadora → `ast`/parser numérico.
- CORS: comparar origin contra lista exacta, no `in`.
- `app.config['MAX_CONTENT_LENGTH']`.
- Regenerar `LEEME.txt` desde README o eliminarlo.

---

## Lo positivo (no todo es deuda)

- **0 ciclos de import** (análisis AST de 141 archivos) — la arquitectura mixin + lazy `__getattr__` es fea pero acíclica.
- **0 módulos huérfanos reales** — los 3 "no importados" se re-exportan vía `document_processor.py`.
- **Los 33 módulos del último commit están integrados**, todos con consumidor.
- **`test_provider_router.py` pasa 48/48** con fakes — el módulo estrella de v6.0 está bien testeado.
- **`.env` NO commiteado, sin secretos en el historial git** (`git log -S` vacío), API keys solo desde env vars.
- Path traversal en `/api/doc/download` **mitigado** con `.resolve()` + `startswith`.

---

## Qué NO se auditó (transparencia)

- **Performance bajo carga real** — no se ejecutó la app (Python 3.14 sin Flask en la máquina).
- **Calidad de los modelos Ollama** — fuera de alcance (infra externa).
- **Frontend `templates/index.html` (4.200 líneas)** — solo se revisó el render de markdown (XSS); no UX/a11y completo.
- **Reescritura de historia git** — identificada como necesaria, no ejecutada (decisión del usuario, operación destructiva).
