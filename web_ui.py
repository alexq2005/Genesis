"""
GENESIS — Web UI
Interfaz web local para interactuar con Genesis desde el navegador.

Usa Flask + Server-Sent Events (SSE) para streaming en tiempo real.
NO requiere websockets — usa HTTP nativo.

Ejecutar: python web_ui.py
Abrir: http://localhost:5000
"""
import sys
import os
import json
import time
import threading
import queue
from collections import defaultdict

# Agregar directorio del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template, request, Response, jsonify
except ImportError:
    print("=" * 50)
    print("Flask no esta instalado.")
    print("Instalar con: pip install flask")
    print("=" * 50)
    sys.exit(1)

from genesis import Genesis
from config import GENESIS_VERSION
from core.dashboard import get_dashboard_html

# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__)

# --- Security Headers ---
@app.after_request
def add_security_headers(response):
    """Agrega headers de seguridad a todas las respuestas."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # CORS: solo localhost
    origin = request.headers.get('Origin', '')
    if origin and ('localhost' in origin or '127.0.0.1' in origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# --- Rate Limiter (in-memory, sin dependencias) ---
_rate_limits = defaultdict(list)  # ip -> [timestamps]
RATE_LIMIT_MAX = 30       # max requests
RATE_LIMIT_WINDOW = 60    # por ventana de N segundos
MAX_INPUT_LENGTH = 10000  # max chars en mensaje

def _check_rate_limit(ip: str) -> bool:
    """Retorna True si el IP excede el rate limit."""
    now = time.time()
    # Limpiar timestamps viejos
    _rate_limits[ip] = [t for t in _rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[ip]) >= RATE_LIMIT_MAX:
        return True
    _rate_limits[ip].append(now)
    return False

# Genesis instance (singleton)
_genesis = None
_genesis_lock = threading.Lock()


def get_genesis():
    """Obtiene o crea la instancia de Genesis (thread-safe)."""
    global _genesis
    if _genesis is None:
        with _genesis_lock:
            if _genesis is None:
                print("Inicializando Genesis...")
                _genesis = Genesis()
                print("Genesis listo!")
    return _genesis




# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    """Pagina principal."""
    return render_template('index.html', version=GENESIS_VERSION)


@app.route("/api/info")
def api_info():
    """Informacion basica de Genesis."""
    try:
        g = get_genesis()
        stats = g.brain.get_stats()
        return jsonify({
            "version": GENESIS_VERSION,
            "generation": g.evolution.get_generation(),
            "provider": stats.get("provider", "local"),
            "model": stats.get("model", "unknown"),
            "memories": len(g.memory.long_term.memories),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/health")
def api_health():
    """Health check endpoint para monitoreo."""
    try:
        g = get_genesis()
        return jsonify({
            "status": "healthy",
            "version": GENESIS_VERSION,
            "uptime_seconds": int(time.time() - _app_start_time),
        })
    except Exception:
        return jsonify({"status": "unhealthy"}), 503

_app_start_time = time.time()


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Endpoint principal de chat."""
    # Rate limiting
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded. Intenta en unos segundos."}), 429

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    message = data["message"].strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    # Input validation
    if len(message) > MAX_INPUT_LENGTH:
        return jsonify({"error": f"Message too long (max {MAX_INPUT_LENGTH} chars)"}), 400

    g = get_genesis()
    start_time = time.time()

    try:
        # Verificar si es un comando
        if message.startswith("/"):
            response = g.handle_command(message)
        else:
            response = g.process_input(message)

        elapsed = int((time.time() - start_time) * 1000)

        result = {
            "response": response,
            "elapsed": elapsed,
        }

        # Sugerencia proactiva si existe
        if hasattr(g, 'proactive') and g.proactive.enabled:
            suggestion = g.proactive.analyze(
                message, response,
                knowledge_graph=g.knowledge_graph,
                error_memory=g.error_memory,
                feedback=g.feedback,
                workspace=g.workspace,
                curiosity=g.curiosity,
            )
            if suggestion:
                result["suggestion"] = suggestion

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        elapsed = int((time.time() - start_time) * 1000)
        return jsonify({
            "error": "Error interno al procesar el mensaje.",
            "elapsed": elapsed,
        }), 500


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """
    Endpoint SSE para streaming de respuestas token por token.
    El frontend recibe tokens en tiempo real via Server-Sent Events.
    """
    # Rate limiting
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    message = data["message"].strip()
    if not message or len(message) > MAX_INPUT_LENGTH:
        return jsonify({"error": "Invalid message"}), 400

    g = get_genesis()

    def generate():
        start_time = time.time()
        token_queue = queue.Queue()
        response_complete = threading.Event()
        full_response = [""]

        def stream_callback(token):
            """Callback que recibe cada token del LLM."""
            token_queue.put(token)

        def run_genesis():
            """Ejecuta Genesis en un thread separado."""
            try:
                if message.startswith("/"):
                    result = g.handle_command(message)
                else:
                    result = g.process_input(message, stream_callback=stream_callback)
                full_response[0] = result
            except Exception as e:
                full_response[0] = f"[ERROR] {str(e)}"
            finally:
                response_complete.set()
                token_queue.put(None)  # Sentinel

        # Iniciar Genesis en background thread
        t = threading.Thread(target=run_genesis, daemon=True)
        t.start()

        # Enviar tokens via SSE a medida que llegan
        streamed_any = False
        while True:
            try:
                token = token_queue.get(timeout=0.1)
                if token is None:
                    break
                streamed_any = True
                # SSE format: data: <json>\n\n
                yield f"data: {json.dumps({'token': token})}\n\n"
            except queue.Empty:
                if response_complete.is_set():
                    break
                # Keepalive
                yield f": keepalive\n\n"

        # Si no se streamearon tokens (comando /), enviar respuesta completa
        elapsed = int((time.time() - start_time) * 1000)
        if not streamed_any:
            yield f"data: {json.dumps({'token': full_response[0]})}\n\n"

        # Evento final con metadata
        yield f"data: {json.dumps({'done': True, 'elapsed': elapsed})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/system")
def api_system():
    """
    Monitoreo de hardware en tiempo real para el HUD.
    Usado por el frontend para mostrar alertas JARVIS.
    """
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        result = {
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "ram_used_gb": round(ram.used / (1024**3), 1),
            "ram_total_gb": round(ram.total / (1024**3), 1),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 1),
        }

        # GPU stats (nvidia-smi)
        try:
            import subprocess
            gpu_out = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if gpu_out.returncode == 0:
                parts = gpu_out.stdout.strip().split(", ")
                if len(parts) >= 4:
                    result["gpu_percent"] = int(parts[0])
                    result["vram_used_mb"] = int(parts[1])
                    result["vram_total_mb"] = int(parts[2])
                    result["gpu_temp_c"] = int(parts[3])
        except Exception:
            pass

        # Alertas JARVIS
        alerts = []
        if cpu > 90:
            alerts.append({"level": "critical", "msg": f"CPU al {cpu}%"})
        elif cpu > 70:
            alerts.append({"level": "warning", "msg": f"CPU elevada: {cpu}%"})
        if ram.percent > 90:
            alerts.append({"level": "critical", "msg": f"RAM al {ram.percent}%"})
        elif ram.percent > 80:
            alerts.append({"level": "warning", "msg": f"RAM elevada: {ram.percent}%"})
        if disk.percent > 90:
            alerts.append({"level": "warning", "msg": f"Disco C: al {disk.percent}%"})
        if result.get("gpu_temp_c", 0) > 85:
            alerts.append({"level": "critical", "msg": f"GPU temperatura: {result['gpu_temp_c']}C"})
        if result.get("vram_used_mb", 0) > 0:
            vram_pct = (result["vram_used_mb"] / result["vram_total_mb"]) * 100
            if vram_pct > 95:
                alerts.append({"level": "critical", "msg": f"VRAM al {vram_pct:.0f}%"})

        result["alerts"] = alerts
        return jsonify(result)

    except ImportError:
        return jsonify({"error": "psutil not installed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status")
def api_status():
    """Estado de Genesis via API."""
    try:
        g = get_genesis()
        return jsonify({
            "status": "running",
            "version": GENESIS_VERSION,
            "generation": g.evolution.get_generation(),
            "interactions": g.evolution.interaction_count,
            "memories": len(g.memory.long_term.memories),
            "streaming": g.streaming,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """
    Upload de imagen para analisis.
    Acepta multipart/form-data con campo 'image'.
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    # Validar extension
    allowed = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        return jsonify({"error": f"Formato no soportado: {ext}"}), 400

    # Validar tamaño (10MB max)
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 10 * 1024 * 1024:
        return jsonify({"error": "Imagen muy grande (max 10MB)"}), 400

    g = get_genesis()
    start_time = time.time()

    try:
        # Guardar temporalmente
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext,
                                          dir=os.path.join(os.path.dirname(__file__), "memory_data"))
        file.save(tmp.name)
        tmp.close()

        # Analizar con image_analyzer si esta disponible
        message = request.form.get("message", "Analiza esta imagen")
        if hasattr(g, "image_analyzer"):
            analysis = g.image_analyzer.analyze(tmp.name)
            response = analysis if isinstance(analysis, str) else str(analysis)
        else:
            response = f"Imagen recibida: {file.filename} ({size // 1024}KB). Analisis de imagen no disponible."

        # Limpiar temporal
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        elapsed = int((time.time() - start_time) * 1000)
        return jsonify({"response": response, "elapsed": elapsed})

    except Exception as e:
        return jsonify({"error": f"Error al procesar imagen: {str(e)}"}), 500


@app.route("/api/document/upload", methods=["POST"])
def api_document_upload():
    """
    Upload de documento para procesamiento.
    Acepta multipart/form-data con campo 'document'.
    Soporta: PDF, DOCX, XLSX, CSV, TXT, imagenes.
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    if "document" not in request.files:
        return jsonify({"error": "No se recibio archivo. Usa campo 'document'."}), 400

    file = request.files["document"]
    if not file.filename:
        return jsonify({"error": "Nombre de archivo vacio"}), 400

    # Validar extension
    from core.document_processor import DocumentReader
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in DocumentReader.SUPPORTED_FORMATS:
        return jsonify({"error": f"Formato no soportado: {ext}. Soportados: PDF, DOCX, XLSX, CSV, TXT, imagenes"}), 400

    # Sin limite de tamano — procesar cualquier archivo

    g = get_genesis()

    try:
        import tempfile
        uploads_dir = os.path.join(os.path.dirname(__file__), "data", "document_processor", "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=uploads_dir)
        tmp.close()  # Cerrar ANTES de file.save() para evitar lock en Windows
        file.save(tmp.name)

        # Procesar documento SIN LLM (brain=None) para respuesta inmediata
        # El LLM (Gemini) puede tardar 30-120s o fallar con 429 — no bloquear upload
        result = g.doc_processor.process(tmp.name, brain=None, summarize=True, extract_entities=True)

        # Limpiar temporal
        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        if "error" in result:
            return jsonify({"error": result["error"]}), 500

        # Guardar en memoria de Genesis para que el chat pueda referenciarlo
        # cuando el usuario diga "resumen", "que dice el documento", etc.
        try:
            summary_preview = result.get("summary", "")[:2000]
            filename = result.get("filename", "documento")
            doc_context = (
                f"[Documento procesado: {filename} | "
                f"{result.get('pages', 0)} paginas | "
                f"{result.get('word_count', 0)} palabras]\n"
                f"{summary_preview}"
            )
            g.memory.short_term.add("user", f"[El usuario subio el archivo: {filename}]")
            g.memory.short_term.add("assistant", doc_context)
            # Guardar referencia al ultimo doc para acceso directo
            g._last_uploaded_doc = result
        except Exception:
            pass

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Error procesando documento: {str(e)}"}), 500


@app.route("/api/document/list", methods=["GET"])
def api_document_list():
    """Lista documentos procesados."""
    g = get_genesis()
    try:
        docs = []
        for doc_id, doc_data in g.doc_processor.processed_docs.items():
            docs.append({
                "doc_id": doc_id,
                "filename": doc_data.get("filename", ""),
                "format": doc_data.get("format", ""),
                "pages": doc_data.get("pages", 0),
                "word_count": doc_data.get("word_count", 0),
                "processed_at": doc_data.get("processed_at", ""),
            })
        return jsonify({"documents": docs, "total": len(docs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# TTS — Edge-TTS (voces neuronales de Azure, gratis)
# ============================================================
_tts_voices_cache = None
_tts_cache_time = 0


@app.route("/api/tts/voices", methods=["GET"])
def api_tts_voices():
    """Lista voces edge-tts disponibles (cacheadas 1 hora)."""
    import time as _time
    global _tts_voices_cache, _tts_cache_time

    # Cache por 1 hora
    if _tts_voices_cache and (_time.time() - _tts_cache_time < 3600):
        lang_filter = request.args.get("lang", "")
        if lang_filter:
            filtered = [v for v in _tts_voices_cache if v["locale"].startswith(lang_filter)]
            return jsonify({"voices": filtered, "total": len(filtered)})
        return jsonify({"voices": _tts_voices_cache, "total": len(_tts_voices_cache)})

    try:
        import edge_tts
        import asyncio

        async def _list():
            return await edge_tts.list_voices()

        # Ejecutar async en sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    voices_raw = pool.submit(lambda: asyncio.run(_list())).result(timeout=10)
            else:
                voices_raw = loop.run_until_complete(_list())
        except RuntimeError:
            voices_raw = asyncio.run(_list())

        voices = []
        for v in voices_raw:
            voices.append({
                "id": v["ShortName"],
                "name": v["ShortName"].replace("Neural", "").replace("-", " "),
                "locale": v["Locale"],
                "gender": v["Gender"],
                "friendly": v.get("FriendlyName", v["ShortName"]),
            })

        _tts_voices_cache = voices
        _tts_cache_time = _time.time()

        lang_filter = request.args.get("lang", "")
        if lang_filter:
            filtered = [v for v in voices if v["locale"].startswith(lang_filter)]
            return jsonify({"voices": filtered, "total": len(filtered)})

        return jsonify({"voices": voices, "total": len(voices)})

    except ImportError:
        return jsonify({"error": "edge-tts no instalado. Ejecuta: pip install edge-tts", "voices": []}), 500
    except Exception as e:
        return jsonify({"error": str(e), "voices": []}), 500


@app.route("/api/tts/speak", methods=["POST"])
def api_tts_speak():
    """Genera audio TTS con edge-tts. Retorna MP3 binario."""
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    voice = data.get("voice", "es-AR-ElenaNeural")
    rate = data.get("rate", "+0%")  # Formato: "+20%", "-10%", "+0%"
    pitch = data.get("pitch", "+0Hz")  # Formato: "+50Hz", "-20Hz"

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Limpiar texto para TTS (quitar markdown, codigo, URLs)
    import re
    clean = text
    clean = re.sub(r'```[\s\S]*?```', '. bloque de codigo omitido. ', clean)
    clean = re.sub(r'`[^`]+`', '', clean)
    clean = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', clean)
    clean = re.sub(r'#{1,6}\s*', '', clean)
    clean = re.sub(r'https?://\S+', ' enlace ', clean)
    clean = re.sub(r'[|_~>-]{2,}', '', clean)
    clean = re.sub(r'\n{2,}', '. ', clean)
    clean = re.sub(r'\n', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    if not clean or len(clean) < 2:
        return jsonify({"error": "Text too short after cleaning"}), 400

    # Limitar a 5000 chars para evitar timeouts
    if len(clean) > 5000:
        clean = clean[:5000]

    try:
        import edge_tts
        import asyncio
        import io

        async def _generate():
            communicate = edge_tts.Communicate(clean, voice, rate=rate, pitch=pitch)
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])
            audio_data.seek(0)
            return audio_data

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    audio = pool.submit(lambda: asyncio.run(_generate())).result(timeout=30)
            else:
                audio = loop.run_until_complete(_generate())
        except RuntimeError:
            audio = asyncio.run(_generate())

        from flask import send_file
        return send_file(audio, mimetype="audio/mpeg", download_name="tts.mp3")

    except ImportError:
        return jsonify({"error": "edge-tts no instalado"}), 500
    except Exception as e:
        return jsonify({"error": f"TTS error: {str(e)}"}), 500


@app.route("/api/screenshot", methods=["POST"])
def api_screenshot():
    """
    Captura de pantalla + analisis opcional via ImageAnalyzer.
    Devuelve path, thumbnail base64, y analisis de IA.
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json() or {}
    analyze = data.get("analyze", False)

    g = get_genesis()

    try:
        from core.device_tools import screen_capture
        from datetime import datetime as _dt
        import base64

        # Capturar pantalla
        timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(os.path.dirname(__file__), "memory_data", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        output_path = os.path.join(screenshot_dir, f"screen_{timestamp}.png")

        result = screen_capture.capture(output_path)

        if not os.path.exists(output_path):
            return jsonify({"error": f"Captura fallida: {result}"}), 500

        response_data = {
            "path": output_path,
            "result": result,
        }

        # Generar thumbnail base64 para preview en el chat
        try:
            from PIL import Image
            import io
            img = Image.open(output_path)
            img.thumbnail((400, 300))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=60)
            response_data["thumbnail"] = base64.b64encode(buffer.getvalue()).decode("ascii")
        except Exception:
            pass

        # Analisis con ImageAnalyzer
        if analyze and hasattr(g, "image_analyzer"):
            try:
                analysis = g.image_analyzer.analyze(
                    output_path,
                    prompt="Describe lo que ves en esta captura de pantalla. "
                           "Identifica aplicaciones abiertas, contenido visible, y cualquier detalle relevante."
                )
                response_data["analysis"] = analysis if isinstance(analysis, str) else str(analysis)
            except Exception as e:
                response_data["analysis"] = f"[Analisis no disponible: {str(e)}]"

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": f"Error en captura: {str(e)}"}), 500


@app.route("/api/stt/status", methods=["GET"])
def api_stt_status():
    """Verifica que el motor STT (vosk) este disponible y listo."""
    result = {"available": False, "engine": "vosk", "model": "vosk-model-small-es"}
    try:
        import vosk
        model_dir = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-es")
        if os.path.isdir(model_dir):
            # Intentar cargar modelo si no esta cacheado
            if not hasattr(app, '_vosk_model'):
                vosk.SetLogLevel(-1)
                app._vosk_model = vosk.Model(model_dir)
            result["available"] = True
            result["message"] = "Vosk STT listo — reconocimiento de voz offline disponible"
        else:
            result["message"] = f"Modelo no encontrado en {model_dir}"
    except ImportError:
        result["message"] = "vosk no instalado — ejecuta: pip install vosk"
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
    return jsonify(result)


@app.route("/api/stt", methods=["POST"])
def api_stt():
    """
    Speech-to-Text endpoint — recibe audio WAV del navegador y lo transcribe
    usando vosk (100% offline, sin internet).

    El frontend captura PCM Int16 16kHz mono y construye un WAV en JS.
    Acepta: multipart/form-data con campo 'audio' (WAV 16kHz mono)
    Retorna: {"text": "texto reconocido"} o {"error": "..."}
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    if 'audio' not in request.files:
        return jsonify({"error": "No se envio archivo de audio"}), 400

    audio_file = request.files['audio']

    try:
        import vosk
        import wave
        import tempfile

        # Ruta del modelo vosk (lazy-load, cachear en app)
        if not hasattr(app, '_vosk_model'):
            model_dir = os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-es")
            if not os.path.isdir(model_dir):
                return jsonify({"error": "Modelo vosk no encontrado en models/vosk-model-small-es"}), 500
            vosk.SetLogLevel(-1)
            app._vosk_model = vosk.Model(model_dir)

        # Guardar WAV temporal
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            audio_file.save(tmp)
            tmp_path = tmp.name

        # Transcribir con vosk
        full_text = ""
        try:
            wf = wave.open(tmp_path, "rb")
            rec = vosk.KaldiRecognizer(app._vosk_model, wf.getframerate())

            text_parts = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        text_parts.append(text)

            # Resultado final
            final = json.loads(rec.FinalResult())
            text = final.get("text", "").strip()
            if text:
                text_parts.append(text)

            wf.close()
            full_text = " ".join(text_parts)
        except Exception:
            full_text = ""

        # Cleanup
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if full_text:
            return jsonify({"text": full_text})
        else:
            return jsonify({"text": "", "error": "No se detecto voz — habla mas fuerte o acercate al mic"})

    except ImportError:
        return jsonify({"error": "vosk no instalado. Ejecuta: pip install vosk"}), 500
    except Exception as e:
        return jsonify({"error": f"Error STT: {str(e)}"}), 500


@app.route("/api/notify", methods=["POST"])
def api_notify():
    """
    Envia una notificacion del sistema operativo (Windows toast).
    Tambien puede usarse para notificaciones programaticas desde Genesis.
    """
    data = request.get_json() or {}
    title = data.get("title", "GENESIS")[:100]
    body = data.get("body", "")[:500]

    if not body:
        return jsonify({"error": "No notification body"}), 400

    try:
        # Windows toast via PowerShell (zero dependencies)
        import subprocess
        # Sanitizar: quitar comillas simples del titulo y body
        safe_title = title.replace("'", "").replace('"', '')
        safe_body = body.replace("'", "").replace('"', '').replace('\n', ' ')

        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName('text')
$textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) > $null
$textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_body}')) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Genesis AI').Show($toast)
"""
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )

        if proc.returncode == 0:
            return jsonify({"status": "sent", "method": "windows_toast"})
        else:
            # Fallback: BurntToast o simple MessageBox
            fallback_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.BalloonTipTitle = '{safe_title}'
$balloon.BalloonTipText = '{safe_body}'
$balloon.Visible = $true
$balloon.ShowBalloonTip(5000)
Start-Sleep -Seconds 6
$balloon.Dispose()
"""
            subprocess.Popen(
                ['powershell', '-NoProfile', '-Command', fallback_script],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return jsonify({"status": "sent", "method": "balloon_tip"})

    except Exception as e:
        return jsonify({"error": str(e), "status": "browser_only"})


@app.route("/api/proactive/execute", methods=["POST"])
def api_proactive_execute():
    """
    Ejecuta una accion proactiva real (no solo sugerencia).
    Acciones seguras: limpiar temp, abrir URL, optimizar memoria, etc.
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json() or {}
    action_id = data.get("action_id", "")

    g = get_genesis()

    try:
        if hasattr(g, 'proactive') and hasattr(g.proactive, 'execute_action'):
            result = g.proactive.execute_action(action_id, genesis=g)
            return jsonify(result)
        else:
            return jsonify({"error": "ProactiveEngine no soporta ejecucion"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/command", methods=["POST"])
def api_command():
    """Ejecutar un comando de Genesis."""
    data = request.get_json()
    cmd = data.get("command", "")
    if not cmd:
        return jsonify({"error": "No command"}), 400

    g = get_genesis()
    try:
        result = g.handle_command(cmd)
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/doc/generate", methods=["POST"])
def api_doc_generate():
    """
    Genera un documento en el formato especificado.
    Body JSON: {title, content, format, subtitle?, sections?}
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json() or {}
    title = data.get("title", "Documento")[:200]
    content = data.get("content", "")
    fmt = data.get("format", "pdf")
    subtitle = data.get("subtitle", "")
    sections = data.get("sections", [])

    g = get_genesis()

    try:
        result = g.doc_generator.generate(
            title=title,
            content=content,
            fmt=fmt,
            author="GENESIS AI",
            subtitle=subtitle,
            sections=sections,
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/doc/download/<path:filename>")
def api_doc_download(filename):
    """
    Descarga un documento generado.
    Solo permite descargar desde el directorio generated_docs.
    """
    from flask import send_file

    g = get_genesis()
    doc_dir = g.doc_generator.output_dir

    # Seguridad: solo servir archivos del directorio de docs
    filepath = (doc_dir / filename).resolve()
    if not str(filepath).startswith(str(doc_dir.resolve())):
        return jsonify({"error": "Ruta no permitida"}), 403

    if not filepath.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404

    # MIME types
    mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".html": "text/html",
        ".md": "text/markdown",
        ".txt": "text/plain",
    }
    ext = filepath.suffix.lower()
    mime = mime_types.get(ext, "application/octet-stream")

    return send_file(str(filepath), mimetype=mime, as_attachment=True,
                     download_name=filepath.name)


@app.route("/api/media/download/<path:filename>")
def api_media_download(filename):
    """
    Descarga un medio generado (imagen, audio, video).
    Solo permite descargar desde el directorio generated_media.
    """
    from flask import send_file

    base_dir = Path(os.path.dirname(__file__)) / "generated_media"
    filepath = (base_dir / filename).resolve()

    if not str(filepath).startswith(str(base_dir.resolve())):
        return jsonify({"error": "Ruta no permitida"}), 403

    if not filepath.exists():
        return jsonify({"error": "Archivo no encontrado"}), 404

    mime_types = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
        ".mp4": "video/mp4", ".webm": "video/webm", ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska", ".mov": "video/quicktime",
    }
    ext = filepath.suffix.lower()
    mime = mime_types.get(ext, "application/octet-stream")

    return send_file(str(filepath), mimetype=mime, as_attachment=True,
                     download_name=filepath.name)


@app.route("/api/doc/export", methods=["POST"])
def api_doc_export():
    """
    Exporta una respuesta o reporte como documento descargable.
    Body JSON: {content, title, format}
    """
    client_ip = request.remote_addr or "unknown"
    if _check_rate_limit(client_ip):
        return jsonify({"error": "Rate limit exceeded."}), 429

    data = request.get_json() or {}
    content = data.get("content", "")
    title = data.get("title", "Export Genesis")[:200]
    fmt = data.get("format", "pdf")

    if not content:
        return jsonify({"error": "No content to export"}), 400

    g = get_genesis()

    try:
        result = g.doc_generator.generate(
            title=title,
            content=content,
            fmt=fmt,
            author="GENESIS AI",
            subtitle=f"Exportado el {time.strftime('%Y-%m-%d %H:%M')}",
        )

        if "error" in result:
            return jsonify(result), 400

        # Devolver info + nombre para descarga
        filename = os.path.basename(result["path"])
        result["download_url"] = f"/api/doc/download/{filename}"
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/dashboard")
def dashboard():
    """Dashboard visual con graficos y metricas."""
    return render_template_string(get_dashboard_html())


@app.route("/dashboard/live")
def dashboard_live():
    """Dashboard en vivo con auto-refresh cada 3 segundos."""
    from core.live_dashboard import get_live_dashboard_html
    return render_template_string(get_live_dashboard_html())


@app.route("/api/live-dashboard")
def api_live_dashboard():
    """
    Endpoint JSON para el Live Dashboard.
    Retorna snapshot completo del sistema para visualizacion en tiempo real.
    """
    try:
        g = get_genesis()

        # GPU stats (safe import)
        gpu_data = {"available": False}
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = [p.strip() for p in result.stdout.strip().split(",")]
                if len(parts) >= 5:
                    gpu_data = {
                        "available": True,
                        "utilization": float(parts[0]),
                        "memory_used": float(parts[1]),
                        "memory_total": float(parts[2]),
                        "temperature": float(parts[3]),
                        "power": float(parts[4]),
                    }
        except Exception:
            pass

        # Brain stats
        brain_stats = g.brain.get_stats()

        # Evolution
        evo_data = {
            "generation": g.evolution.get_generation(),
            "interactions": g.evolution.interaction_count,
            "total_evolutions": g.evolution.state.get("total_evolutions", 0),
        }

        # Memory
        memory_data = {
            "long_term": len(g.memory.long_term.memories),
            "short_term": len(g.memory.short_term),
            "emotional": len(getattr(g.memory, 'emotional', type('', (), {'memories': []})()).memories)
                if hasattr(g.memory, 'emotional') and hasattr(g.memory.emotional, 'memories')
                else 0,
        }

        # Web Intelligence
        web_data = {
            "searches": g.web.total_searches,
            "pages_read": g.web.total_reads,
            "pages_learned": g.web.total_learned,
            "search_available": g.web.searcher.available,
        }

        # Semantic Memory
        sem_data = g.semantic_memory.get_stats()

        # Optimizer
        opt_data = g.optimizer.get_stats()

        # Autonomous Evolution
        auto_data = {
            "active": g.autonomous.active,
            "actions": len(g.autonomous.actions),
            "total_cycles": g.autonomous.total_cycles,
            "total_actions": g.autonomous.total_actions,
            "log": [
                {"action": r.get("action", "?"), "success": r.get("success", False),
                 "timestamp": r.get("timestamp", 0)}
                for r in getattr(g.autonomous, "execution_log", [])[-10:]
            ],
        }

        # Subsystems grid (quick health)
        subsystems = []
        sub_checks = [
            ("Brain", lambda: g.brain.is_available()),
            ("Memory", lambda: len(g.memory.long_term.memories) >= 0),
            ("Evolution", lambda: g.evolution.get_generation() >= 0),
            ("Curiosity", lambda: True),
            ("Debate", lambda: True),
            ("Heartbeat", lambda: True),
            ("Embeddings", lambda: g.embeddings.engine_type != "none"),
            ("Plugins", lambda: True),
            ("KnowledgeGraph", lambda: True),
            ("RAG", lambda: True),
            ("WebIntel", lambda: g.web.searcher.available),
            ("Agents", lambda: True),
            ("SemanticMem", lambda: True),
            ("Optimizer", lambda: True),
            ("Evaluator", lambda: True),
            ("SkillMemory", lambda: True),
            ("ChainEngine", lambda: True),
            ("EpisodicMemory", lambda: True),
            ("MetaLearner", lambda: True),
            ("Personality", lambda: True),
            ("GoalManager", lambda: True),
            ("Reflection", lambda: True),
            ("ContextRouter", lambda: True),
            ("CausalReasoner", lambda: True),
            ("ConceptSynth", lambda: True),
            ("StrategicPlanner", lambda: True),
            ("PatternPredictor", lambda: True),
            ("AnomalyDetector", lambda: True),
            ("AdaptiveIface", lambda: True),
            ("HypothesisEngine", lambda: True),
            ("ExplanationEngine", lambda: True),
            ("DialogueStrategist", lambda: True),
            ("CognitiveMonitor", lambda: True),
            ("AbstractionEngine", lambda: True),
            ("LearningOptimizer", lambda: True),
            ("UnifiedMind", lambda: True),
            ("DreamEngine", lambda: True),
            ("SelfNarrative", lambda: True),
            ("EmotionReader", lambda: True),
            ("EmpathyEngine", lambda: True),
            ("ConflictResolver", lambda: True),
            ("StoryGenerator", lambda: True),
            ("CodeArchitect", lambda: True),
            ("IdeaBrainstormer", lambda: True),
            ("ImageAnalyzer", lambda: True),
            ("DiagramGenerator", lambda: True),
            ("VoicePersonality", lambda: True),
            ("PeerDebate", lambda: True),
            ("ConsensusEngine", lambda: True),
            ("KnowledgeSharing", lambda: True),
            ("PaperReader", lambda: True),
            ("ExperimentRunner", lambda: True),
            ("InsightSynthesizer", lambda: True),
            ("SafeCodeEvolver", lambda: True),
            ("ArchitectureEvolver", lambda: True),
            ("ModuleGenerator", lambda: True),
            ("TemporalReasoner", lambda: True),
            ("ScheduleOptimizer", lambda: True),
            ("TrendForecaster", lambda: True),
            ("EthicalReasoner", lambda: True),
            ("BiasDetector", lambda: True),
            ("TransparencyEngine", lambda: True),
            ("DomainExpert", lambda: True),
            ("TutorEngine", lambda: True),
            ("FactChecker", lambda: True),
            ("TaskDistributor", lambda: True),
            ("ResultAggregator", lambda: True),
            ("NetworkManager", lambda: True),
            ("AutonomousResearchLoop", lambda: True),
            ("SelfArchitect", lambda: True),
            ("ConsciousnessIntegrator", lambda: True),
            ("Scheduler", lambda: True),
            ("Profiler", lambda: True),
        ]
        for name, check_fn in sub_checks:
            try:
                ok = check_fn()
                subsystems.append({"name": name, "status": "ok" if ok else "warn"})
            except Exception:
                subsystems.append({"name": name, "status": "error"})

        # Knowledge Graph sample
        kg_stats = g.knowledge_graph.get_stats()

        return jsonify({
            "timestamp": time.time(),
            "version": GENESIS_VERSION,
            "gpu": gpu_data,
            "brain": brain_stats,
            "evolution": evo_data,
            "memory": memory_data,
            "web": web_data,
            "semantic_memory": sem_data,
            "optimizer": opt_data,
            "evaluator": g.evaluator.get_stats(),
            "skill_memory": g.skill_memory.get_stats(),
            "chain_engine": g.chain_engine.get_stats(),
            "episodic_memory": g.episodic_memory.get_stats(),
            "meta_learner": g.meta_learner.get_stats(),
            "personality": g.personality.get_stats(),
            "goal_manager": g.goal_manager.get_stats(),
            "reflection": g.reflection.get_stats(),
            "context_router": g.context_router.get_stats(),
            "causal_reasoner": g.causal_reasoner.get_stats(),
            "concept_synth": g.concept_synth.get_stats(),
            "strategic_planner": g.strategic_planner.get_stats(),
            "pattern_predictor": g.pattern_predictor.get_stats(),
            "anomaly_detector": g.anomaly_detector.get_stats(),
            "adaptive_iface": g.adaptive_iface.get_stats(),
            "hypothesis_engine": g.hypothesis_engine.get_stats(),
            "explanation_engine": g.explanation_engine.get_stats(),
            "dialogue_strategist": g.dialogue_strategist.get_stats(),
            "cognitive_monitor": g.cognitive_monitor.get_stats(),
            "abstraction_engine": g.abstraction_engine.get_stats(),
            "learning_optimizer": g.learning_optimizer.get_stats(),
            "unified_mind": g.unified_mind.get_stats(),
            "dream_engine": g.dream_engine.get_stats(),
            "self_narrative": g.self_narrative.get_stats(),
            "emotion_reader": g.emotion_reader.get_stats(),
            "empathy_engine": g.empathy_engine.get_stats(),
            "conflict_resolver": g.conflict_resolver.get_stats(),
            "story_generator": g.story_generator.get_stats(),
            "code_architect": g.code_architect.get_stats(),
            "idea_brainstormer": g.idea_brainstormer.get_stats(),
            "image_analyzer": g.image_analyzer.get_stats(),
            "diagram_generator": g.diagram_generator.get_stats(),
            "voice_personality": g.voice_personality.get_stats(),
            "peer_debate": g.peer_debate.get_stats(),
            "consensus_engine": g.consensus_engine.get_stats(),
            "knowledge_sharing": g.knowledge_sharing.get_stats(),
            "paper_reader": g.paper_reader.get_stats(),
            "experiment_runner": g.experiment_runner.get_stats(),
            "insight_synthesizer": g.insight_synthesizer.get_stats(),
            "safe_code_evolver": g.safe_code_evolver.get_stats(),
            "architecture_evolver": g.architecture_evolver.get_stats(),
            "module_generator": g.module_generator.get_stats(),
            "temporal_reasoner": g.temporal_reasoner.get_stats(),
            "schedule_optimizer": g.schedule_optimizer.get_stats(),
            "trend_forecaster": g.trend_forecaster.get_stats(),
            "ethical_reasoner": g.ethical_reasoner.get_stats(),
            "bias_detector": g.bias_detector.get_stats(),
            "transparency_engine": g.transparency_engine.get_stats(),
            "domain_expert": g.domain_expert.get_stats(),
            "tutor_engine": g.tutor_engine.get_stats(),
            "fact_checker": g.fact_checker.get_stats(),
            "task_distributor": g.task_distributor.get_stats(),
            "result_aggregator": g.result_aggregator.get_stats(),
            "network_manager": g.network_manager.get_stats(),
            "autonomous_research_loop": g.autonomous_research_loop.get_stats(),
            "self_architect": g.self_architect.get_stats(),
            "consciousness_integrator": g.consciousness_integrator.get_stats(),
            "autonomous": auto_data,
            "subsystems": subsystems,
            "knowledge_graph": kg_stats,
            "streaming": g.streaming,
        })

    except Exception as e:
        return jsonify({"error": str(e), "timestamp": time.time()})


# ============================================================
# MAIN
# ============================================================
def main():
    """Inicia el servidor web."""
    import argparse
    parser = argparse.ArgumentParser(description="Genesis Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Puerto (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Modo debug de Flask")
    args = parser.parse_args()

    print("=" * 50)
    print(f"  GENESIS Web UI")
    print(f"  http://{args.host}:{args.port}")
    print("=" * 50)

    # Pre-inicializar Genesis
    get_genesis()

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True,
    )


if __name__ == "__main__":
    main()
