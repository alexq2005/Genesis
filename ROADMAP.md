# GENESIS — Roadmap

> **Documento vivo.** GENESIS sigue escalando: este roadmap se actualiza con cada hito.
> Última actualización: **2026-06-13**.

GENESIS es un asistente de IA **100% local** (corre sobre Ollama, ~140 módulos en Python)
con cabina de escritorio (PyWebView, puerto 5100). Privacidad total, sin nube obligatoria,
control real del sistema del usuario.

---

## 🧭 Visión
Un JARVIS personal que **piensa, aprende, evoluciona y actúa** sobre la máquina del usuario:
voz natural, generación de medios, control de apps/hardware, memoria persistente y
auto-mejora segura — todo offline y bajo control del usuario.

---

## ✅ Estado actual (capacidades operativas)

### Cerebro e inteligencia
- LLM local vía Ollama; router de modelos rápido/lento (`genesis` 8B / `genesis-q3`).
- Aprendizaje que compone (N3), memoria RAG semántica/episódica (N5), proactividad (N6).
- Auto-mejora de código **segura** (mutaciones quirúrgicas BUSCAR/REEMPLAZAR + guardrails).
- Loop autónomo de fondo; builder y evolución con qwen-coder + fitness por métricas.

### Capacidades (lo que hace)
- **Voz**: TTS edge-tts (22 voces) + **voz clonada local (XTTS-v2)** — voz JARVIS/Milton.
- **Imágenes**: generación local con **Stable Diffusion (sd-turbo) en GPU** (offline, ~0.6s warm).
- **Música**: reproducción en YouTube Music (CDP, reuso de ventana).
- **Netflix**: app de la Store (abrir/reproducir/castear vía menú) — unificado en una sola app.
- **Cast/TV**: Chromecast (YouTube) + cast de Netflix vía navegador.
- **Archivos**: gestión y desarrollo conversacional, papelera segura, búsqueda global.
- **Sistema**: volumen, brillo, energía, impresión, multi-monitor.
- **Conexiones**: WiFi, Bluetooth, USB.
- **Comunicación**: enviar/leer email (Gmail), despertador con voz + música.
- **Índices**: programas (abrir apps por nombre) y carpetas (con prune-on-access).

### Interfaz (hub)
- Cabina `/core` rediseñada estilo "JARVIS MARK 5": núcleo de plasma reactivo a la voz,
  dock de 6 botones (BUSCAR/WEBS/MÚSICA/CREAR/VER/NÚCLEO), tablero de evidencias,
  barra de stats GPU/CPU. **Todo desbloqueado** (sin gating PRO).

### Distribución
- Guía multi-usuario (`SETUP.md`); aislamiento de datos/secretos por `.gitignore`.

---

## 🔜 Próxima evolución — **v7.0 "Unbound" (Mente Orquestada)**
> En desarrollo. GENESIS rompe sus límites: usa todos sus recursos sin pelear, suma sentidos
> en tiempo real, actúa con autonomía y se controla desde cualquier lado. 4 tracks ordenados
> — **Track 1 desbloquea el resto**.

### 🎛️ Track 1 — Conductor (recursos + tools) · *base, primero*
- **`core/vram_manager.py`**: orquestador de VRAM — carga/descarga LLM/SD/XTTS según tarea,
  prioridades, anti-OOM, telemetría. Desbloquea **voz + imagen + LLM** juntos (techo de 8GB).
- **Voz clonada integrada al orquestador**: GPU si hay espacio → fallback CPU (~8s) → Álvaro.
  *(Resuelve el pendiente de v6.1.)*
- **N4 — capa de function-calling**: tools declarativas (registro/esquema/validación),
  migración aditiva sobre el dispatcher regex. Base para escalar sin fragilidad.

### 👁️ Track 2 — Sentidos en tiempo real
- Visión continua (cámara/pantalla en streaming → describe y reacciona).
- Mostrar la imagen generada **inline en el hub** (hoy devuelve ruta).
- Más integraciones de apps + automatización de UI más profunda.

### 🤖 Track 3 — Autonomía (agente)
- Agente multi-paso: planifica → ejecuta cadenas de tools (sobre Track 1) → verifica.
- Scheduling avanzado, proactividad fuerte, alarmas/recordatorios **persistentes**.

### 📱 Track 4 — Alcance (remoto / móvil)
- API segura + control desde el celular (web responsive / app liviana), push, sincronización.

**Orden**: Track 1 → (Tracks 2 y 3 en paralelo) → Track 4.

---

## 🌌 Más allá de v7.0 (ideas abiertas)
- Calidad de medios: fine-tuning de XTTS, SDXL-Turbo (1024px) cuando la VRAM lo permita.
- Migración a más VRAM (RTX 4060 Ti 16GB) → modelos calientes simultáneos.
- Garantizar **una sola instancia** de la cabina; suite de tests creciente por capacidad.

---

## 🧱 Principios de escalado (no romper al crecer)
1. **Local-first y privacidad**: nada sale a la nube sin pedirlo; secretos y datos del
   usuario nunca se versionan.
2. **Aislamiento**: cada capacidad en su módulo (`core/*.py`); el handler las orquesta.
3. **Guardrails de auto-modificación**: el builder/self-modifier no se auto-otorga red ni
   rompe el smoke test.
4. **Degradación grácil**: si una capacidad falla (OOM, servicio caído), caer a un fallback
   y avisar — nunca quedar mudo/roto.
5. **Audit-first**: verificar empíricamente antes de declarar "funciona".
6. **Regex tolerante al voseo/typos**: stems cortos (`repro\w*`, `caste\w*`).

---

*Para detalles de implementación y decisiones, ver `docs/` y la memoria del proyecto.*
