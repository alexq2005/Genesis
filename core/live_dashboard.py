"""
GENESIS Live Dashboard — Dashboard en tiempo real.

Pagina HTML autocontenida con:
- Estado de los 38+ subsistemas en tiempo real (auto-refresh SSE)
- Metricas de GPU/CPU/RAM
- Knowledge Graph interactivo (D3.js force graph)
- Log de evolucion autonoma
- Grafico de rendimiento temporal
- Controlador de streaming y comandos rapidos

Se sirve como una sola pagina HTML sin archivos externos
(todo el CSS y JS embebido para maxima portabilidad).
"""


def get_live_dashboard_html():
    """Retorna el HTML completo del dashboard en vivo."""
    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GENESIS — Live Dashboard</title>
<style>
:root {
    --bg: #0a0e17;
    --card-bg: #111827;
    --border: #1f2937;
    --text: #e5e7eb;
    --text-dim: #6b7280;
    --accent: #10b981;
    --accent2: #6366f1;
    --danger: #ef4444;
    --warning: #f59e0b;
    --blue: #3b82f6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    min-height: 100vh;
}
.header {
    background: linear-gradient(135deg, #111827 0%, #1e1b4b 100%);
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.header h1 {
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(90deg, #10b981, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.header .meta { font-size: 12px; color: var(--text-dim); }
.status-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
}
.status-dot.on { background: var(--accent); }
.status-dot.off { background: var(--danger); }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    padding: 16px;
}
.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    transition: border-color 0.2s;
}
.card:hover { border-color: var(--accent); }
.card h3 {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-dim);
    margin-bottom: 8px;
}
.card .value {
    font-size: 24px;
    font-weight: 700;
    color: var(--accent);
}
.card .detail {
    font-size: 12px;
    color: var(--text-dim);
    margin-top: 4px;
}
.wide { grid-column: span 2; }
.full { grid-column: 1 / -1; }
.bar-container {
    background: #1f2937;
    border-radius: 4px;
    height: 8px;
    margin-top: 6px;
    overflow: hidden;
}
.bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}
.bar.green { background: linear-gradient(90deg, #10b981, #34d399); }
.bar.blue { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
.bar.red { background: linear-gradient(90deg, #ef4444, #f87171); }
.bar.yellow { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.subsystems {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 6px;
}
.sub-item {
    font-size: 11px;
    padding: 6px 8px;
    background: #0f172a;
    border-radius: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.sub-item .label { color: var(--text-dim); }
.sub-item .val { color: var(--accent); font-weight: 600; }
.log-area {
    background: #0f172a;
    border-radius: 6px;
    padding: 10px;
    max-height: 200px;
    overflow-y: auto;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 11px;
    line-height: 1.6;
}
.log-area .entry { color: var(--text-dim); }
.log-area .entry.ok { color: var(--accent); }
.log-area .entry.fail { color: var(--danger); }
.log-area .entry.info { color: var(--blue); }
.controls {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.btn {
    padding: 6px 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
}
.btn:hover { border-color: var(--accent); background: #1a2332; }
.btn.active { border-color: var(--accent); background: #064e3b; }
#kg-canvas {
    width: 100%;
    height: 300px;
    background: #0f172a;
    border-radius: 6px;
}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>GENESIS Live Dashboard</h1>
        <div class="meta">
            <span class="status-dot on" id="statusDot"></span>
            <span id="statusText">Conectando...</span> |
            Gen <span id="gen">?</span> |
            v<span id="version">?</span> |
            Uptime: <span id="uptime">0s</span>
        </div>
    </div>
    <div class="controls">
        <button class="btn" onclick="sendCmd('/evolve once')">Evolve Tick</button>
        <button class="btn" onclick="sendCmd('/stream')">Toggle Stream</button>
        <button class="btn" onclick="sendCmd('/status')">Status</button>
        <button class="btn" onclick="refresh()">Refresh</button>
    </div>
</div>

<div class="grid">
    <!-- GPU -->
    <div class="card">
        <h3>GPU</h3>
        <div class="value" id="gpuUtil">--%</div>
        <div class="bar-container"><div class="bar green" id="gpuBar" style="width:0%"></div></div>
        <div class="detail">
            VRAM: <span id="vram">--</span> MiB |
            Temp: <span id="gpuTemp">--</span>C |
            <span id="gpuPower">--</span>W
        </div>
    </div>

    <!-- Cerebro -->
    <div class="card">
        <h3>Cerebro (LLM)</h3>
        <div class="value" id="provider">--</div>
        <div class="detail">
            Modelo: <span id="model">--</span><br>
            Llamadas: <span id="calls">0</span> |
            Tokens: <span id="tokens">0</span>
        </div>
    </div>

    <!-- Evolucion -->
    <div class="card">
        <h3>Evolucion</h3>
        <div class="value">Gen <span id="genCard">1</span></div>
        <div class="detail">
            Interacciones: <span id="interactions">0</span><br>
            Fitness: <span id="fitness">--</span>/100
        </div>
    </div>

    <!-- Memoria -->
    <div class="card">
        <h3>Memoria</h3>
        <div class="value" id="memTotal">0</div>
        <div class="detail">
            Corto plazo: <span id="memShort">0</span> msgs |
            Largo plazo: <span id="memLong">0</span><br>
            Semantica: <span id="memSemantic">0</span> entradas
        </div>
    </div>

    <!-- Web Intelligence -->
    <div class="card">
        <h3>Web Intelligence</h3>
        <div class="value" id="webLearned">0</div>
        <div class="detail">
            Paginas aprendidas<br>
            Busquedas: <span id="webSearches">0</span> |
            Embeddings: <span id="embCount">0</span>
        </div>
    </div>

    <!-- Optimizador -->
    <div class="card">
        <h3>Inference Optimizer</h3>
        <div class="value" id="cacheRate">--%</div>
        <div class="detail">
            Cache hit rate<br>
            Tokens ahorrados: ~<span id="tokensSaved">0</span>
        </div>
    </div>

    <!-- Evolucion Autonoma -->
    <div class="card wide">
        <h3>Evolucion Autonoma</h3>
        <div class="detail" style="margin-bottom:8px">
            Estado: <span id="autoState" style="color:var(--accent)">--</span> |
            Acciones: <span id="autoActions">0</span> |
            Ciclos: <span id="autoCycles">0</span> |
            Ejecutadas: <span id="autoExec">0</span>
        </div>
        <div class="log-area" id="autoLog">
            <div class="entry info">Esperando datos...</div>
        </div>
    </div>

    <!-- Subsistemas -->
    <div class="card full">
        <h3>Subsistemas (38+)</h3>
        <div class="subsystems" id="subsystems">
            <div class="sub-item"><span class="label">Cargando...</span></div>
        </div>
    </div>

    <!-- Knowledge Graph -->
    <div class="card full">
        <h3>Knowledge Graph</h3>
        <div class="detail" style="margin-bottom:6px">
            Nodos: <span id="kgNodes">0</span> |
            Conexiones: <span id="kgEdges">0</span>
        </div>
        <canvas id="kg-canvas"></canvas>
    </div>
</div>

<script>
const API = '';  // mismo host
let refreshInterval = null;
let startTime = Date.now();

async function fetchData() {
    try {
        const [status, dashboard] = await Promise.all([
            fetch(API + '/api/status').then(r => r.json()),
            fetch(API + '/api/live-dashboard').then(r => r.json()),
        ]);

        // Status basico
        document.getElementById('statusDot').className = 'status-dot on';
        document.getElementById('statusText').textContent = 'Online';
        document.getElementById('gen').textContent = status.generation || '?';
        document.getElementById('version').textContent = dashboard.version || '?';
        document.getElementById('genCard').textContent = status.generation || '1';
        document.getElementById('interactions').textContent = status.interactions || '0';

        // GPU
        if (dashboard.gpu) {
            document.getElementById('gpuUtil').textContent = dashboard.gpu.utilization + '%';
            document.getElementById('gpuBar').style.width = dashboard.gpu.utilization + '%';
            document.getElementById('gpuBar').className = 'bar ' + (dashboard.gpu.utilization > 90 ? 'red' : dashboard.gpu.utilization > 60 ? 'yellow' : 'green');
            document.getElementById('vram').textContent = dashboard.gpu.vram_used;
            document.getElementById('gpuTemp').textContent = dashboard.gpu.temperature;
            document.getElementById('gpuPower').textContent = dashboard.gpu.power;
        }

        // Brain
        if (dashboard.brain) {
            document.getElementById('provider').textContent = dashboard.brain.provider;
            document.getElementById('model').textContent = dashboard.brain.model;
            document.getElementById('calls').textContent = dashboard.brain.calls;
            document.getElementById('tokens').textContent = dashboard.brain.tokens;
        }

        // Memoria
        if (dashboard.memory) {
            document.getElementById('memShort').textContent = dashboard.memory.short_term;
            document.getElementById('memLong').textContent = dashboard.memory.long_term;
            document.getElementById('memSemantic').textContent = dashboard.memory.semantic || 0;
            document.getElementById('memTotal').textContent =
                (dashboard.memory.short_term || 0) + (dashboard.memory.long_term || 0) + (dashboard.memory.semantic || 0);
        }

        // Fitness
        document.getElementById('fitness').textContent = dashboard.fitness || '--';

        // Web
        if (dashboard.web) {
            document.getElementById('webLearned').textContent = dashboard.web.learned;
            document.getElementById('webSearches').textContent = dashboard.web.searches;
        }

        // Embeddings
        document.getElementById('embCount').textContent = dashboard.embeddings_count || 0;

        // Optimizer
        if (dashboard.optimizer) {
            document.getElementById('cacheRate').textContent = dashboard.optimizer.cache_rate;
            document.getElementById('tokensSaved').textContent = dashboard.optimizer.tokens_saved;
        }

        // Autonomous
        if (dashboard.autonomous) {
            document.getElementById('autoState').textContent = dashboard.autonomous.state;
            document.getElementById('autoState').style.color = dashboard.autonomous.state === 'ACTIVO' ? 'var(--accent)' : 'var(--text-dim)';
            document.getElementById('autoActions').textContent = dashboard.autonomous.actions;
            document.getElementById('autoCycles').textContent = dashboard.autonomous.cycles;
            document.getElementById('autoExec').textContent = dashboard.autonomous.executed;
        }

        // Auto log
        if (dashboard.auto_log && dashboard.auto_log.length > 0) {
            const logEl = document.getElementById('autoLog');
            logEl.innerHTML = dashboard.auto_log.map(l => {
                const cls = l.success ? 'ok' : 'fail';
                return '<div class="entry ' + cls + '">[' + l.time + '] ' + l.action + ': ' + (l.success ? 'OK' : 'FAIL') + '</div>';
            }).join('');
            logEl.scrollTop = logEl.scrollHeight;
        }

        // Subsistemas
        if (dashboard.subsystems) {
            const el = document.getElementById('subsystems');
            el.innerHTML = dashboard.subsystems.map(s =>
                '<div class="sub-item"><span class="label">' + s.name + '</span><span class="val">' + s.value + '</span></div>'
            ).join('');
        }

        // Knowledge Graph
        if (dashboard.kg) {
            document.getElementById('kgNodes').textContent = dashboard.kg.nodes;
            document.getElementById('kgEdges').textContent = dashboard.kg.edges;
            drawKG(dashboard.kg.sample_nodes || [], dashboard.kg.sample_edges || []);
        }

        // Uptime
        let sec = Math.floor((Date.now() - startTime) / 1000);
        let min = Math.floor(sec / 60);
        document.getElementById('uptime').textContent = min > 0 ? min + 'm' : sec + 's';

    } catch(e) {
        document.getElementById('statusDot').className = 'status-dot off';
        document.getElementById('statusText').textContent = 'Desconectado';
    }
}

function drawKG(nodes, edges) {
    const canvas = document.getElementById('kg-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!nodes.length) return;

    // Layout circular simple
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const radius = Math.min(cx, cy) - 40;
    const positions = {};

    nodes.forEach((n, i) => {
        const angle = (2 * Math.PI * i) / nodes.length;
        positions[n.id] = {
            x: cx + radius * Math.cos(angle),
            y: cy + radius * Math.sin(angle),
        };
    });

    // Dibujar edges
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 0.5;
    edges.forEach(e => {
        const from = positions[e.from];
        const to = positions[e.to];
        if (from && to) {
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.stroke();
        }
    });

    // Dibujar nodos
    nodes.forEach(n => {
        const p = positions[n.id];
        const r = Math.min(8, 3 + (n.mentions || 1));

        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = n.mentions > 5 ? '#10b981' : n.mentions > 2 ? '#6366f1' : '#374151';
        ctx.fill();

        ctx.fillStyle = '#9ca3af';
        ctx.font = '9px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(n.label || n.id, p.x, p.y + r + 10);
    });
}

async function sendCmd(cmd) {
    try {
        const r = await fetch(API + '/api/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: cmd}),
        });
        const data = await r.json();
        if (data.result) alert(data.result.substring(0, 500));
        fetchData();
    } catch(e) {
        alert('Error: ' + e.message);
    }
}

function refresh() { fetchData(); }

// Auto-refresh cada 3 segundos
fetchData();
refreshInterval = setInterval(fetchData, 3000);
</script>
</body>
</html>"""
