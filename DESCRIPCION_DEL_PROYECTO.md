# GENESIS — Descripción del Proyecto

> Asistente de IA personal **100% local**. Piensa, ve, habla, crea y actúa sobre tu
> computadora — sin nube, sin API keys obligatorias, sin suscripciones. Tus datos
> nunca salen de tu máquina.

---

## 1. ¿Qué es GENESIS?

GENESIS es un asistente de inteligencia artificial de uso personal que corre
**íntegramente en la computadora del usuario**. A diferencia de los asistentes
comerciales (que envían cada conversación a servidores de terceros), GENESIS procesa
el lenguaje, genera imágenes, sintetiza voz y controla el sistema operativo **de forma
local y privada**, sobre tu propia GPU.

Está escrito en **Python** (~150 módulos), corre sobre modelos de lenguaje locales vía
**Ollama**, y se presenta como una **app de escritorio tipo "JARVIS"** con interfaz por
voz manos-libres.

**En una frase:** un "JARVIS" personal, local y bajo tu control.

---

## 2. ¿Qué hace? (capacidades)

| Área | Qué puede hacer |
|---|---|
| **Conversación** | Razonamiento local (Ollama: Llama 3.1 8B / Qwen 2.5 Coder 7B), sin censura, con memoria multinivel (corto/largo plazo, episódica, semántica) |
| **Voz** | Entrada manos-libres (decís «genesis…» sin tocar nada) con reconocimiento de **quién** habla; salida con voz clonada local (XTTS), neural (edge-tts) o 100% offline (Piper) |
| **Visión** | Describe tu pantalla, y la **cámara del celular** (el cel transmite por la red local vía QR/HTTPS, sin instalar app): ver, foto, modo monitoreo |
| **Creación** | Genera imágenes localmente (Stable Diffusion sd-turbo en GPU) |
| **Multimedia** | Música (YouTube Music), Netflix (busca y reproduce, mueve entre pantallas), Chromecast |
| **Control del sistema** | Volumen, brillo, energía, WiFi/Bluetooth/USB, multi-monitor, mover/snap ventanas, abrir apps y carpetas por nombre, manejo de archivos, impresión |
| **Productividad** | Email (Gmail), despertador con voz + música, notas, recordatorios, lanzador de juegos (Steam/Epic) |
| **Desarrollo** | Genera, ejecuta y corrige código real (BuilderEngine); puede auto-mejorar su propio código de forma segura (con guardrails) |
| **Agentes** | 6 especialistas (investigador, programador, analista, creativo, seguridad, planificador) con un coordinador que auto-delega |

---

## 3. Recursos necesarios

### Hardware (mínimo recomendado)

| Recurso | Requisito | Notas |
|---|---|---|
| **GPU** | **NVIDIA con 8 GB+ de VRAM** (ej. RTX 3060 Ti) | Imprescindible para correr el LLM, la voz clonada y la generación de imágenes en local |
| **CPU** | Moderna (ej. Intel i7-13700KF o similar) | — |
| **RAM** | **16 GB** | — |
| **Disco** | ~15-25 GB libres | Modelos de Ollama (~8 GB) + SD (~2.5 GB) + dependencias |
| **Sistema** | **Windows 11** | La app de escritorio usa PyWebView + WebView2 |

> **El techo de 8 GB de VRAM es una restricción de diseño central**: con 8 GB no entran
> simultáneamente el cerebro (LLM ~6 GB) + la voz clonada XTTS (~2 GB) + la generación de
> imágenes. GENESIS prioriza y degrada con elegancia (la voz cae a CPU/Piper si no hay
> lugar). Con más VRAM (16 GB) podrían convivir modelos más grandes.

### Software

| Componente | Versión | Para qué |
|---|---|---|
| **Python** | **3.11 o 3.12** | ⚠️ Con 3.13+ no hay *wheels* de numpy 1.26.4 / torch 2.5.1 — crear el venv con 3.11/3.12 |
| **Ollama** | última ([ollama.com](https://ollama.com)) | Motor de los LLMs locales |
| **PyTorch + CUDA** | torch 2.5.1 + cu121 | GPU para LLM/SD/voz |
| **Node.js** | ≥ 22 | Render de la cabina y resolución de challenges de YouTube |
| **(Opcional) Tesseract** | — | OCR de documentos/imágenes |
| **(Opcional) API keys** | Gemini/OpenAI/Anthropic | Solo como *fallback*; **no son necesarias** para uso 100% local |

---

## 4. Instalación

```bash
# 1) Crear el entorno virtual con Python 3.11 o 3.12 (NO 3.13+)
python -m venv venv
venv\Scripts\activate

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) PyTorch con CUDA (GPU NVIDIA)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 4) Instalar Ollama (https://ollama.com) y descargar los modelos locales
ollama pull llama3.1          # base conversacional (~4.7 GB)
ollama pull qwen2.5-coder:7b  # especializado en código (~4.4 GB)
ollama pull llava             # visión (describir pantalla / cámara) (~4.7 GB)

# 5) (Opcional) API keys de fallback
copy .env.example .env        # editar y agregar GOOGLE_API_KEY si se quiere

# 6) Ejecutar
python genesis_desktop.py --right
```

En Windows también podés usar el lanzador **`GENESIS_DESKTOP.bat`** (limpia la caché de
Python y arranca la app de escritorio).

> **Privacidad desde el día 1:** los secretos (`.env`) y los datos de usuario (`data/`,
> perfiles de navegador, certificados, cookies) están en `.gitignore` y **nunca se
> versionan ni se suben**.

---

## 5. Funcionamiento (cómo funciona)

### Arquitectura en capas

```
┌─────────────────────────────────────────────────────────┐
│  Cabina (PyWebView + WebView2)  ·  puerto 5100  ·  /core  │  ← lo que ves
│  núcleo de plasma reactivo a la voz · voz I/O · dock      │
├─────────────────────────────────────────────────────────┤
│  Backend Flask (web_ui.py)  ·  SSE streaming              │  ← orquesta
│  genesis_processing → detección de herramienta → respuesta│
├─────────────────────────────────────────────────────────┤
│  Cerebro: Ollama (LLM local)  +  ProviderRouter           │  ← piensa
│  Llama 3.1 8B / Qwen Coder 7B · fallback opcional cloud    │
├─────────────────────────────────────────────────────────┤
│  ~150 módulos en core/  (cada capacidad, aislada)         │  ← actúa
│  visión, voz, sistema, archivos, agentes, memoria, ...    │
└─────────────────────────────────────────────────────────┘
```

### Flujo de una interacción

1. **Entrada** — escribís en la cabina o decís «genesis…» (la escucha manos-libres
   detecta la *wake-word* con vosk y transcribe el comando con Whisper).
2. **Detección de herramienta** — el comando pasa primero por un *router* de reglas
   (instantáneo, ~90 % de los casos: «subí el volumen», «reproducí X», «mové la
   ventana…»). Si no matchea, un *router por significado* (LLM con salida JSON) elige la
   herramienta correcta.
3. **Acción real** — la herramienta se ejecuta de verdad (no la "alucina" el modelo):
   lee datos reales del sistema, controla apps, genera la imagen, etc.
4. **Respuesta** — texto en pantalla + voz (misma voz en cabina y manos-libres). Los
   resultados de herramienta se devuelven **verificados**, sin reformular con el LLM.

### Principios de diseño

- **Local-first y privacidad:** nada sale a la nube sin pedirlo.
- **Honestidad / anti-alucinación:** ante una pregunta con respuesta objetiva, se
  ejecuta una herramienta real en vez de dejar que el modelo invente.
- **Degradación grácil:** si una capacidad falla (OOM, servicio caído), cae a un
  *fallback* y avisa — nunca queda mudo o roto.
- **Auto-mejora segura:** las mutaciones de código pasan por validación AST + suite de
  tests como *gate*; si algo rompe, **auto-revierte**. Los archivos críticos requieren
  aprobación humana explícita.

---

## 6. Uso

### Comandos por voz (manos libres)

Decí **«genesis …»** seguido del comando:

```
genesis, reproducí <serie> en netflix      — busca y reproduce
genesis, mové netflix a la otra pantalla   — mueve la ventana entre monitores
genesis, conectá la cámara del celular     — muestra un QR para transmitir
genesis, qué ves en mi pantalla            — describe el monitor (visión)
genesis, generá una imagen de <…>          — Stable Diffusion local
genesis, jugá <juego>                      — lanza un juego de Steam/Epic
genesis, subí el volumen / salida jbl      — control del sistema
genesis, enviá un email a X que diga «…»   — Gmail (con confirmación)
genesis, entrená mi voz                    — registra tu huella («solo mi voz»)
```

### Vistas web (puerto 5100)

| Ruta | Qué es |
|---|---|
| `/core` | Cabina principal (núcleo de plasma + starfield) |
| `/jarvis` | HUD alternativo |
| `/mission` | Mission Control — estaciones de los 6 agentes |

---

## 7. Privacidad y seguridad

- **100 % local:** el lenguaje, la voz, las imágenes y la visión se procesan en tu GPU.
  Sin API keys, no hay tráfico a la nube.
- **El video de la cámara del celular nunca sale de la red local** (servidor HTTPS propio
  con certificado autofirmado; el cel se conecta por IP de LAN).
- **Secretos protegidos:** `.env`, perfiles de navegador, certificados y cookies están en
  `.gitignore`.
- **Guardrails de auto-modificación:** el sistema no se auto-otorga acceso a red ni rompe
  el *smoke test*; los cambios de código críticos necesitan tu aprobación.

---

## 8. Estructura del repositorio

```
GENESIS/
├── genesis_desktop.py      # App de escritorio (PyWebView)
├── genesis.py              # Motor principal (orquestador)
├── web_ui.py               # Backend Flask + cabina (HTML/CSS/JS)
├── config.py               # Configuración central
├── requirements.txt        # Dependencias
├── GENESIS_DESKTOP.bat     # Lanzador (Windows)
├── core/                   # ~150 módulos (una capacidad por archivo)
│   ├── brain.py · provider_router.py     # LLM + routing
│   ├── memory.py · embeddings_engine.py  # Memoria + RAG
│   ├── agents.py                         # 6 agentes + coordinador
│   ├── handsfree.py · stt.py · voiceprint.py · voice_clone.py  # Voz
│   ├── image_analyzer.py · mobile_cam.py # Visión + cámara del celular
│   ├── media_generator.py                # Imágenes (SD local)
│   ├── netflix.py · music_player.py · casting.py  # Multimedia
│   ├── window_manager.py · system_control.py · connections.py  # Sistema
│   └── ...
├── README.md               # Documentación técnica
├── ROADMAP.md              # Hoja de ruta
├── PROJECT_EVOLUTION.md    # Evolución versión por versión
├── ERRORS_AND_SOLUTIONS.md # Registro de errores y soluciones
└── LEGAL.md                # Licencia y aviso legal
```

---

## 9. Licencia

Software propietario. Ver [LEGAL.md](LEGAL.md). Proyecto personal de **Alex Quiñones**.

---

*Para detalles técnicos profundos, ver [README.md](README.md); para la hoja de ruta,
[ROADMAP.md](ROADMAP.md); para la historia del proyecto, [PROJECT_EVOLUTION.md](PROJECT_EVOLUTION.md).*
