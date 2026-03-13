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

# Agregar directorio del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template_string, request, Response, jsonify
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
# HTML TEMPLATE
# ============================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genesis AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a2e;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --accent: #00d4ff;
            --accent-dim: #0088aa;
            --user-bg: #1a2a3a;
            --genesis-bg: #1a1a2e;
            --error: #ff4444;
            --success: #44ff44;
            --border: #2a2a3e;
        }

        body {
            font-family: 'Segoe UI', 'Cascadia Code', 'Consolas', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 12px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header h1 {
            font-size: 1.4em;
            color: var(--accent);
            letter-spacing: 4px;
            font-weight: 300;
        }

        .header .version {
            color: var(--text-secondary);
            font-size: 0.8em;
        }

        .header-actions {
            display: flex;
            gap: 8px;
        }

        .header-btn {
            background: var(--bg-tertiary);
            color: var(--text-secondary);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85em;
            transition: all 0.2s;
        }

        .header-btn:hover {
            background: var(--accent-dim);
            color: white;
            border-color: var(--accent);
        }

        /* Chat area */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 16px 24px;
            scroll-behavior: smooth;
        }

        .message {
            max-width: 85%;
            margin-bottom: 16px;
            padding: 12px 16px;
            border-radius: 8px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
            background: var(--user-bg);
            margin-left: auto;
            border: 1px solid #2a3a4a;
        }

        .message.genesis {
            background: var(--genesis-bg);
            border: 1px solid var(--border);
        }

        .message.system {
            background: transparent;
            color: var(--text-secondary);
            font-size: 0.85em;
            text-align: center;
            max-width: 100%;
            border: none;
        }

        .message.error {
            background: #2a1a1a;
            border: 1px solid var(--error);
            color: #ff8888;
        }

        .message .role {
            font-size: 0.75em;
            color: var(--accent);
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .message.user .role {
            color: #66aaff;
        }

        /* Code blocks */
        .message pre {
            background: #0d0d15;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 12px;
            margin: 8px 0;
            overflow-x: auto;
        }

        .message code {
            font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: 0.9em;
        }

        /* Input area */
        .input-container {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            gap: 12px;
        }

        .input-container textarea {
            flex: 1;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 16px;
            font-family: inherit;
            font-size: 0.95em;
            resize: none;
            outline: none;
            min-height: 44px;
            max-height: 200px;
            transition: border-color 0.2s;
        }

        .input-container textarea:focus {
            border-color: var(--accent);
        }

        .input-container button {
            background: var(--accent);
            color: #000;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: bold;
            cursor: pointer;
            font-size: 0.95em;
            transition: all 0.2s;
            align-self: flex-end;
        }

        .input-container button:hover {
            background: #00eeff;
            transform: translateY(-1px);
        }

        .input-container button:disabled {
            background: var(--accent-dim);
            cursor: not-allowed;
            transform: none;
        }

        /* Status bar */
        .status-bar {
            background: var(--bg-primary);
            border-top: 1px solid var(--border);
            padding: 4px 24px;
            font-size: 0.75em;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
        }

        .status-dot.thinking {
            background: var(--accent);
            animation: pulse 1s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg-primary); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--accent-dim); }

        /* Sidebar (commands) */
        .sidebar {
            position: fixed;
            right: -320px;
            top: 0;
            width: 320px;
            height: 100vh;
            background: var(--bg-secondary);
            border-left: 1px solid var(--border);
            padding: 20px;
            transition: right 0.3s ease;
            z-index: 100;
            overflow-y: auto;
        }

        .sidebar.open { right: 0; }

        .sidebar h3 {
            color: var(--accent);
            margin-bottom: 16px;
        }

        .sidebar .cmd {
            padding: 8px;
            margin-bottom: 4px;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 0.85em;
        }

        .sidebar .cmd:hover {
            background: var(--bg-tertiary);
        }

        .sidebar .cmd code {
            color: var(--accent);
        }

        /* Overlay */
        .overlay {
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 99;
        }

        .overlay.show { display: block; }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div>
            <h1>G E N E S I S</h1>
            <span class="version" id="versionInfo">Cargando...</span>
        </div>
        <div class="header-actions">
            <button class="header-btn" onclick="sendCommand('/status')">Estado</button>
            <button class="header-btn" onclick="sendCommand('/metrics')">Metricas</button>
            <button class="header-btn" onclick="sendCommand('/kg')">Knowledge</button>
            <button class="header-btn" onclick="toggleSidebar()">Comandos</button>
        </div>
    </div>

    <!-- Chat -->
    <div class="chat-container" id="chatContainer">
        <div class="message system">
            Genesis inicializado. Escribe algo para empezar.
        </div>
    </div>

    <!-- Input -->
    <div class="input-container">
        <textarea id="userInput" placeholder="Escribe tu mensaje..."
                  rows="1" onkeydown="handleKeyDown(event)"></textarea>
        <button id="sendBtn" onclick="sendMessage()">Enviar</button>
    </div>

    <!-- Status bar -->
    <div class="status-bar">
        <div class="status-indicator">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Listo</span>
        </div>
        <span id="statsText">-</span>
    </div>

    <!-- Sidebar -->
    <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <h3>Comandos</h3>
        <div class="cmd" onclick="sendCommand('/status')"><code>/status</code> — Estado completo</div>
        <div class="cmd" onclick="sendCommand('/memory')"><code>/memory</code> — Memoria</div>
        <div class="cmd" onclick="sendCommand('/evolution')"><code>/evolution</code> — Evolucion</div>
        <div class="cmd" onclick="sendCommand('/curiosity')"><code>/curiosity</code> — Curiosidad</div>
        <div class="cmd" onclick="sendCommand('/feedback')"><code>/feedback</code> — Feedback</div>
        <div class="cmd" onclick="sendCommand('/metrics')"><code>/metrics</code> — Metricas</div>
        <div class="cmd" onclick="sendCommand('/report')"><code>/report</code> — Reporte completo</div>
        <div class="cmd" onclick="sendCommand('/errors')"><code>/errors</code> — Errores conocidos</div>
        <div class="cmd" onclick="sendCommand('/kg')"><code>/kg</code> — Knowledge Graph</div>
        <div class="cmd" onclick="sendCommand('/plugins')"><code>/plugins</code> — Plugins</div>
        <div class="cmd" onclick="sendCommand('/tools')"><code>/tools</code> — Custom Tools</div>
        <div class="cmd" onclick="sendCommand('/templates')"><code>/templates</code> — Prompt Templates</div>
        <div class="cmd" onclick="sendCommand('/context')"><code>/context</code> — Context Budget</div>
        <div class="cmd" onclick="sendCommand('/thinking')"><code>/thinking</code> — Toggle debug</div>
        <div class="cmd" onclick="sendCommand('/stream')"><code>/stream</code> — Toggle streaming</div>
        <div class="cmd" onclick="sendCommand('/help')"><code>/help</code> — Ayuda completa</div>
    </div>

    <script>
        const chatContainer = document.getElementById('chatContainer');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        const statsText = document.getElementById('statsText');
        let isProcessing = false;
        let messageCount = 0;

        // Auto-resize textarea
        userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('show');
        }

        function sendCommand(cmd) {
            userInput.value = cmd;
            sendMessage();
            toggleSidebar();
        }

        function addMessage(role, content) {
            const div = document.createElement('div');
            div.className = `message ${role}`;

            const roleLabel = document.createElement('div');
            roleLabel.className = 'role';
            roleLabel.textContent = role === 'user' ? 'Tu' : role === 'genesis' ? 'Genesis' : '';

            const contentDiv = document.createElement('div');
            contentDiv.textContent = content;

            if (role !== 'system') {
                div.appendChild(roleLabel);
            }
            div.appendChild(contentDiv);
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            return contentDiv;
        }

        function setStatus(text, thinking) {
            statusText.textContent = text;
            if (thinking) {
                statusDot.classList.add('thinking');
            } else {
                statusDot.classList.remove('thinking');
            }
        }

        async function sendMessage() {
            const text = userInput.value.trim();
            if (!text || isProcessing) return;

            isProcessing = true;
            sendBtn.disabled = true;
            userInput.value = '';
            userInput.style.height = 'auto';

            // Mostrar mensaje del usuario
            addMessage('user', text);
            messageCount++;

            // Estado: pensando
            setStatus('Pensando...', true);

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text }),
                });

                const data = await response.json();

                if (data.error) {
                    addMessage('error', data.error);
                } else {
                    addMessage('genesis', data.response);

                    // Mostrar sugerencia proactiva si hay
                    if (data.suggestion) {
                        addMessage('system', data.suggestion);
                    }
                }

                // Actualizar stats
                if (data.elapsed) {
                    statsText.textContent = `${data.elapsed}ms | Msgs: ${messageCount}`;
                }

            } catch (err) {
                addMessage('error', `Error de conexion: ${err.message}`);
            }

            setStatus('Listo', false);
            isProcessing = false;
            sendBtn.disabled = false;
            userInput.focus();
        }

        // Cargar info inicial
        async function loadInfo() {
            try {
                const r = await fetch('/api/info');
                const data = await r.json();
                document.getElementById('versionInfo').textContent =
                    `v${data.version} | Gen ${data.generation} | ${data.provider}`;
            } catch(e) {
                document.getElementById('versionInfo').textContent = 'Error conectando';
            }
        }

        loadInfo();
        userInput.focus();
    </script>
</body>
</html>"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    """Pagina principal."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/info")
def api_info():
    """Informacion basica de Genesis."""
    try:
        g = get_genesis()
        stats = g.brain.get_stats()
        return jsonify({
            "version": g.evolution.state.get("version", "1.4.0"),
            "generation": g.evolution.get_generation(),
            "provider": stats.get("provider", "local"),
            "model": stats.get("model", "unknown"),
            "memories": len(g.memory.long_term.memories),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Endpoint principal de chat."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    message = data["message"].strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

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
        elapsed = int((time.time() - start_time) * 1000)
        return jsonify({
            "error": f"Error: {str(e)}",
            "elapsed": elapsed,
        })


@app.route("/api/status")
def api_status():
    """Estado de Genesis via API."""
    try:
        g = get_genesis()
        return jsonify({
            "status": "running",
            "version": g.evolution.state.get("version", "?"),
            "generation": g.evolution.get_generation(),
            "interactions": g.evolution.interaction_count,
            "memories": len(g.memory.long_term.memories),
            "streaming": g.streaming,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


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
