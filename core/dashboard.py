"""
GENESIS — Visual Dashboard
Genera el HTML del dashboard con graficos interactivos.

Usa Chart.js (CDN) para graficos y vis-network (CDN) para el knowledge graph.
Sin dependencias Python adicionales — todo es HTML/JS inline.

El dashboard muestra:
- Metricas de rendimiento (response times, interactions)
- Uso de templates (distribucion)
- Knowledge Graph interactivo (nodos y relaciones)
- Estado del sistema (subsistemas, modelos, RAG)
- Feedback (positivo/negativo)
"""


def get_dashboard_html() -> str:
    """Retorna el HTML completo del dashboard."""
    return DASHBOARD_TEMPLATE


DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Genesis Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        :root {
            --bg-primary: #0a0a0f;
            --bg-card: #12121a;
            --bg-card-hover: #1a1a2e;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --accent: #00d4ff;
            --accent-dim: #0088aa;
            --green: #44ff88;
            --red: #ff4466;
            --yellow: #ffaa44;
            --purple: #aa66ff;
            --border: #2a2a3e;
        }

        body {
            font-family: 'Segoe UI', 'Cascadia Code', 'Consolas', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }

        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 20px;
        }

        .dashboard-header h1 {
            color: var(--accent);
            font-size: 1.5em;
            font-weight: 300;
            letter-spacing: 3px;
        }

        .dashboard-header .nav-links a {
            color: var(--text-secondary);
            text-decoration: none;
            margin-left: 16px;
            padding: 6px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.85em;
            transition: all 0.2s;
        }
        .dashboard-header .nav-links a:hover {
            color: var(--accent);
            border-color: var(--accent);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: var(--accent-dim); }

        .card h2 {
            color: var(--accent);
            font-size: 1em;
            font-weight: 400;
            letter-spacing: 1px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }

        .card-full {
            grid-column: 1 / -1;
        }

        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .stat-label { color: var(--text-secondary); font-size: 0.9em; }
        .stat-value { color: var(--text-primary); font-weight: 500; }
        .stat-value.green { color: var(--green); }
        .stat-value.red { color: var(--red); }
        .stat-value.yellow { color: var(--yellow); }
        .stat-value.accent { color: var(--accent); }

        .mini-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }

        .mini-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            text-align: center;
        }
        .mini-card .number {
            font-size: 2em;
            font-weight: 300;
            color: var(--accent);
        }
        .mini-card .label {
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        #kg-container {
            height: 400px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-primary);
        }

        .chart-container {
            position: relative;
            height: 250px;
        }

        .loading {
            text-align: center;
            color: var(--text-secondary);
            padding: 40px;
        }

        @media (max-width: 768px) {
            .mini-stats { grid-template-columns: repeat(2, 1fr); }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>GENESIS DASHBOARD</h1>
        <div class="nav-links">
            <a href="/">Chat</a>
            <a href="/dashboard" class="active">Dashboard</a>
        </div>
    </div>

    <!-- Mini stats -->
    <div class="mini-stats">
        <div class="mini-card">
            <div class="number" id="stat-interactions">-</div>
            <div class="label">Interacciones</div>
        </div>
        <div class="mini-card">
            <div class="number" id="stat-chunks">-</div>
            <div class="label">RAG Chunks</div>
        </div>
        <div class="mini-card">
            <div class="number" id="stat-concepts">-</div>
            <div class="label">Conceptos KG</div>
        </div>
        <div class="mini-card">
            <div class="number" id="stat-model">-</div>
            <div class="label">Modelo Activo</div>
        </div>
    </div>

    <!-- Charts grid -->
    <div class="grid">
        <!-- Template Usage -->
        <div class="card">
            <h2>USO DE TEMPLATES</h2>
            <div class="chart-container">
                <canvas id="chart-templates"></canvas>
            </div>
        </div>

        <!-- Feedback -->
        <div class="card">
            <h2>FEEDBACK</h2>
            <div class="chart-container">
                <canvas id="chart-feedback"></canvas>
            </div>
        </div>

        <!-- System Status -->
        <div class="card">
            <h2>ESTADO DEL SISTEMA</h2>
            <div id="system-status">
                <div class="loading">Cargando...</div>
            </div>
        </div>

        <!-- Model Router -->
        <div class="card">
            <h2>MODELOS</h2>
            <div id="models-info">
                <div class="loading">Cargando...</div>
            </div>
        </div>

        <!-- Knowledge Graph -->
        <div class="card card-full">
            <h2>KNOWLEDGE GRAPH</h2>
            <div id="kg-container">
                <div class="loading" style="padding-top: 180px;">Cargando grafo...</div>
            </div>
        </div>
    </div>

<script>
// ============================================================
// Dashboard Data Loader
// ============================================================
const COLORS = {
    accent: '#00d4ff',
    green: '#44ff88',
    red: '#ff4466',
    yellow: '#ffaa44',
    purple: '#aa66ff',
    blue: '#4488ff',
    pink: '#ff66aa',
    orange: '#ff8844',
};

const CHART_COLORS = [
    COLORS.accent, COLORS.green, COLORS.yellow,
    COLORS.purple, COLORS.blue, COLORS.pink,
    COLORS.orange, COLORS.red,
];

// Global chart defaults
Chart.defaults.color = '#a0a0a0';
Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
Chart.defaults.font.family = "'Segoe UI', monospace";

async function fetchData(endpoint) {
    try {
        const res = await fetch(endpoint);
        return await res.json();
    } catch (e) {
        console.error(`Error fetching ${endpoint}:`, e);
        return null;
    }
}

async function fetchCommand(cmd) {
    try {
        const res = await fetch('/api/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: cmd})
        });
        const data = await res.json();
        return data.result || data.error || '';
    } catch (e) {
        return '';
    }
}

// ============================================================
// Load Dashboard Data
// ============================================================
async function loadDashboard() {
    // Fetch status and info
    const [info, status] = await Promise.all([
        fetchData('/api/info'),
        fetchData('/api/status'),
    ]);

    // Also get specific command outputs
    const [templatesInfo, modelsInfo, ragInfo, kgInfo] = await Promise.all([
        fetchCommand('/templates'),
        fetchCommand('/models'),
        fetchCommand('/rag status'),
        fetchCommand('/kg'),
    ]);

    // Update mini stats
    if (info) {
        document.getElementById('stat-interactions').textContent =
            info.metrics?.total_interactions || 0;
        document.getElementById('stat-concepts').textContent =
            info.knowledge_graph?.concepts || 0;
    }

    // RAG chunks
    const ragMatch = ragInfo.match(/Chunks totales:\\s*(\\d+)/);
    document.getElementById('stat-chunks').textContent =
        ragMatch ? ragMatch[1] : '0';

    // Active model
    const modelMatch = modelsInfo.match(/\\[ACTIVO\\]/) ?
        modelsInfo.match(/(\\w+)\\s*\\[ACTIVO\\]/)?.[1] : 'default';
    document.getElementById('stat-model').textContent = modelMatch || '-';

    // Template usage chart
    renderTemplateChart(templatesInfo);

    // Feedback chart
    renderFeedbackChart(info);

    // System status
    renderSystemStatus(info, status);

    // Models info
    renderModelsInfo(modelsInfo);

    // Knowledge Graph
    renderKnowledgeGraph(info);
}

function renderTemplateChart(templatesInfo) {
    const ctx = document.getElementById('chart-templates');
    const templates = ['code', 'debug', 'creative', 'explain',
                       'analysis', 'research', 'summarize', 'security'];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: templates.map(t => t.charAt(0).toUpperCase() + t.slice(1)),
            datasets: [{
                data: templates.map(() => 1), // Equal distribution initially
                backgroundColor: CHART_COLORS,
                borderColor: '#0a0a0f',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { padding: 12, font: { size: 11 } }
                }
            }
        }
    });
}

function renderFeedbackChart(info) {
    const ctx = document.getElementById('chart-feedback');
    const pos = info?.feedback?.positive || 0;
    const neg = info?.feedback?.negative || 0;
    const neutral = Math.max(1, (info?.metrics?.total_interactions || 1) - pos - neg);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Positivo', 'Neutral', 'Negativo'],
            datasets: [{
                data: [pos, neutral, neg],
                backgroundColor: [COLORS.green, COLORS.accent, COLORS.red],
                borderRadius: 6,
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.03)' } },
                x: { grid: { display: false } }
            }
        }
    });
}

function renderSystemStatus(info, statusData) {
    const el = document.getElementById('system-status');
    if (!info) {
        el.innerHTML = '<div class="stat-row"><span class="stat-label">Sin datos</span></div>';
        return;
    }

    const items = [
        ['Version', info.version || '-', 'accent'],
        ['Proveedor LLM', info.provider || '-', ''],
        ['Modelo local', info.local_model || '-', ''],
        ['Memoria corto plazo', info.memory?.short_term || 0, ''],
        ['Memoria largo plazo', info.memory?.long_term || 0, ''],
        ['Errores recordados', info.error_memory?.patterns || 0, info.error_memory?.patterns > 0 ? 'yellow' : ''],
        ['Debate activo', info.debate_enabled ? 'SI' : 'NO', info.debate_enabled ? 'green' : ''],
        ['Heartbeat', info.heartbeat?.running ? 'Activo' : 'Inactivo', info.heartbeat?.running ? 'green' : ''],
        ['Evolution score', info.evolution?.fitness_score?.toFixed(2) || '-', 'accent'],
    ];

    el.innerHTML = items.map(([label, value, cls]) =>
        `<div class="stat-row">
            <span class="stat-label">${label}</span>
            <span class="stat-value ${cls}">${value}</span>
        </div>`
    ).join('');
}

function renderModelsInfo(modelsInfo) {
    const el = document.getElementById('models-info');
    if (!modelsInfo) {
        el.innerHTML = '<div class="stat-row"><span class="stat-label">Sin datos</span></div>';
        return;
    }

    // Parse the models info text into structured data
    const lines = modelsInfo.split('\\n');
    let html = '';

    const modelRegex = /^\\s+(\\w+)(.*)/;
    const detailRegex = /^\\s{4}(\\w[^:]+):\\s*(.+)/;

    for (const line of lines) {
        const modelMatch = line.match(modelRegex);
        const detailMatch = line.match(detailRegex);

        if (line.includes('[ACTIVO]')) {
            html += `<div class="stat-row">
                <span class="stat-label">${line.trim()}</span>
                <span class="stat-value green">ACTIVO</span>
            </div>`;
        } else if (detailMatch) {
            html += `<div class="stat-row">
                <span class="stat-label">${detailMatch[1].trim()}</span>
                <span class="stat-value">${detailMatch[2].trim()}</span>
            </div>`;
        } else if (line.includes('Auto-routing')) {
            html += `<div class="stat-row">
                <span class="stat-label">Auto-routing</span>
                <span class="stat-value ${line.includes('SI') ? 'green' : 'yellow'}">${line.includes('SI') ? 'ON' : 'OFF'}</span>
            </div>`;
        }
    }

    el.innerHTML = html || '<div class="stat-row"><span class="stat-label">No hay modelos</span></div>';
}

function renderKnowledgeGraph(info) {
    const container = document.getElementById('kg-container');
    const kgData = info?.knowledge_graph;

    if (!kgData || kgData.concepts === 0) {
        container.innerHTML = '<div class="loading" style="padding-top:180px;">Knowledge Graph vacio. Interactua con Genesis para poblar el grafo.</div>';
        return;
    }

    // Fetch KG data from API
    fetch('/api/command', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: '/kg export'})
    })
    .then(r => r.json())
    .then(data => {
        const kgText = data.result || '';

        // Parse nodes and edges from KG export
        const nodes = [];
        const edges = [];
        const nodeSet = new Set();

        // Try to parse concept lines
        const conceptRegex = /([\\w\\s]+?)\\s*(?:->|--|\\()\\s*([\\w\\s]+)/g;
        let match;
        let id = 0;

        while ((match = conceptRegex.exec(kgText)) !== null) {
            const source = match[1].trim();
            const target = match[2].trim();

            if (!nodeSet.has(source)) {
                nodeSet.add(source);
                nodes.push({id: id++, label: source, color: COLORS.accent, font: {color: '#e0e0e0'}});
            }
            if (!nodeSet.has(target)) {
                nodeSet.add(target);
                nodes.push({id: id++, label: target, color: COLORS.purple, font: {color: '#e0e0e0'}});
            }

            const srcId = nodes.find(n => n.label === source)?.id;
            const tgtId = nodes.find(n => n.label === target)?.id;
            if (srcId !== undefined && tgtId !== undefined) {
                edges.push({from: srcId, to: tgtId, color: {color: '#2a2a3e', highlight: COLORS.accent}});
            }
        }

        // If no structured data, create placeholder nodes from concept count
        if (nodes.length === 0 && kgData.concepts > 0) {
            for (let i = 0; i < Math.min(kgData.concepts, 20); i++) {
                nodes.push({
                    id: i,
                    label: `Concepto ${i+1}`,
                    color: CHART_COLORS[i % CHART_COLORS.length],
                    font: {color: '#e0e0e0'}
                });
            }
        }

        if (nodes.length === 0) {
            container.innerHTML = '<div class="loading" style="padding-top:180px;">Sin datos de grafo</div>';
            return;
        }

        // Render with vis-network
        const network = new vis.Network(container, {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges),
        }, {
            nodes: {
                shape: 'dot',
                size: 16,
                borderWidth: 2,
                shadow: true,
            },
            edges: {
                width: 1,
                smooth: { type: 'continuous' },
            },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -30,
                    centralGravity: 0.005,
                    springLength: 150,
                },
                solver: 'forceAtlas2Based',
                stabilization: { iterations: 100 },
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
            },
        });
    })
    .catch(() => {
        container.innerHTML = '<div class="loading" style="padding-top:180px;">Error cargando Knowledge Graph</div>';
    });
}

// Load on page ready
document.addEventListener('DOMContentLoaded', loadDashboard);

// Auto-refresh every 30 seconds
setInterval(loadDashboard, 30000);
</script>
</body>
</html>"""
