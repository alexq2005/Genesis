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

## 🚧 En progreso
- **Voz clonada vs VRAM (8GB)**: Ollama (6.2GB) + XTTS (2GB) no coexisten en GPU.
  Opciones en evaluación: XTTS en CPU (~8s/frase), descarga de LLM on-demand, o voz
  clonada "a pedido" con edge-tts en el día a día. *(Decisión pendiente del usuario.)*
- **N4 — Arquitectura de tools (function-calling)**: reemplazar el dispatcher por regex
  por una capa de tools declarativa. Diferido como capa aditiva, no reescritura.

---

## 🛣️ Backlog / próximas fases (abierto — el proyecto escala)

### Calidad de medios
- Voz: aislar muestras con **Demucs** (instalado), evaluar fine-tuning de XTTS.
- Imágenes: opción **SDXL-Turbo** (1024px) si la VRAM lo permite; mostrar imagen
  generada **dentro del hub** (hoy devuelve la ruta del archivo).

### Gestión de recursos (clave por el techo de 8GB VRAM)
- Orquestador de VRAM: cargar/descargar LLM, SD y XTTS según la tarea sin OOM.
- Telemetría de VRAM en vivo + políticas automáticas de fallback.

### Plataforma
- Capa de tools/function-calling (N4) como base para crecer sin frágiles regex.
- Más integraciones de dispositivos y servicios (a demanda del usuario).
- Persistencia de alarmas/recordatorios entre reinicios.

### Robustez / operación
- Garantizar **una sola instancia** de la cabina (evitar duplicados venv/sistema).
- Suite de tests creciente por capacidad.

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
