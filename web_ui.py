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
from pathlib import Path

# Agregar directorio del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template, render_template_string, request, Response, jsonify, redirect
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

_INTERACTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "interactions.jsonl")
_interactions_buffer = []  # ring en memoria para /api/monitor (rápido)


def _log_interaction(ip, request_text, response_text, elapsed_ms):
    """Registra una petición + respuesta para monitoreo (JSONL + buffer en RAM)."""
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "request": (request_text or "")[:500],
            "response": (response_text or "")[:1500],
            "ms": elapsed_ms,
        }
        _interactions_buffer.append(rec)
        if len(_interactions_buffer) > 200:
            del _interactions_buffer[:-200]
        os.makedirs(os.path.dirname(_INTERACTIONS_FILE), exist_ok=True)
        with open(_INTERACTIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass  # el monitoreo nunca debe romper el chat


_JARVIS_HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GENESIS // JARVIS</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.7.0/dist/tabler-icons.min.css">
<style>
*{box-sizing:border-box}
:root{--ga:#27e3ff;--gd:#0a1f2b;--panel:rgba(10,22,32,.55);--ink:#cfeff8;--mut:#5a8a99}
body{margin:0;font-family:ui-monospace,'Cascadia Code',Menlo,Consolas,monospace;background:#03060b;color:#a9e2ef;overflow-x:hidden;-webkit-font-smoothing:antialiased}
#hud{--ga:#27e3ff;min-height:100vh;padding:18px;position:relative;overflow:hidden;
 background:
  radial-gradient(120% 80% at 50% -10%, rgba(39,227,255,.10), transparent 55%),
  radial-gradient(100% 100% at 50% 120%, rgba(39,227,255,.06), transparent 60%),
  repeating-linear-gradient(rgba(39,227,255,.045) 0 1px,transparent 1px 34px),
  repeating-linear-gradient(90deg,rgba(39,227,255,.045) 0 1px,transparent 1px 34px),
  #03060b;}
#hud::after{content:"";position:absolute;inset:0;pointer-events:none;z-index:3;box-shadow:inset 0 0 160px rgba(0,0,0,.7),inset 0 0 40px rgba(39,227,255,.05)}
.corner{position:absolute;width:30px;height:30px;border:2px solid var(--ga);opacity:.55;z-index:2;border-radius:2px;box-shadow:0 0 12px rgba(39,227,255,.3)}
.scan{position:absolute;left:0;right:0;height:60px;z-index:1;pointer-events:none;
 background:linear-gradient(rgba(39,227,255,0),rgba(39,227,255,.10),rgba(39,227,255,0));
 animation:scan 7s cubic-bezier(.4,0,.6,1) infinite}
@keyframes scan{0%{top:-60px;opacity:0}12%{opacity:1}88%{opacity:1}100%{top:100%;opacity:0}}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes spinr{to{transform:rotate(-360deg)}}
@keyframes sweep{to{transform:rotate(360deg)}}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
@keyframes ring{0%{transform:scale(.35);opacity:.9}100%{transform:scale(2.6);opacity:0}}
@keyframes floatp{0%{transform:translateY(12px);opacity:0}25%{opacity:.7}100%{transform:translateY(-34px);opacity:0}}
@keyframes glow{0%,100%{text-shadow:0 0 12px rgba(39,227,255,.6)}50%{text-shadow:0 0 22px rgba(39,227,255,.95)}}
.S{transform-origin:center;animation:spin 16s linear infinite}.Sr{transform-origin:center;animation:spinr 26s linear infinite}.Sw{transform-origin:center;animation:sweep 3.4s linear infinite}
.p{position:absolute;border-radius:50%;background:var(--ga);animation:floatp linear infinite;pointer-events:none;box-shadow:0 0 4px var(--ga)}
.chip{border:1px solid rgba(39,227,255,.18);border-radius:12px;padding:10px 12px;background:var(--panel);backdrop-filter:blur(6px);box-shadow:inset 0 1px 0 rgba(255,255,255,.04),0 2px 10px rgba(0,0,0,.3);transition:border-color .25s,box-shadow .25s}
.chip:hover{border-color:rgba(39,227,255,.4);box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 0 18px rgba(39,227,255,.12)}
.bar{height:6px;background:rgba(39,227,255,.08);border-radius:6px;overflow:hidden}
.bar>i{display:block;height:6px;border-radius:6px;background:linear-gradient(90deg,rgba(39,227,255,.5),var(--ga));box-shadow:0 0 10px var(--ga);transition:width .6s ease}
.btn{cursor:pointer;font-family:inherit;letter-spacing:.08em;font-size:12px;color:var(--ga);border:1px solid rgba(39,227,255,.45);border-radius:9px;padding:9px 14px;background:linear-gradient(rgba(39,227,255,.06),rgba(39,227,255,.02));transition:all .2s;box-shadow:0 0 0 rgba(39,227,255,0)}
.btn:hover{background:rgba(39,227,255,.14);box-shadow:0 0 16px rgba(39,227,255,.3);transform:translateY(-1px)}
.btn:active{transform:translateY(0) scale(.98)}
input,select{font-family:inherit;background:rgba(6,12,20,.7);border:1px solid rgba(39,227,255,.2);color:var(--ink);border-radius:10px;padding:11px 13px;font-size:13px;outline:none;flex:1;transition:border-color .2s,box-shadow .2s}
input:focus,select:focus{border-color:var(--ga);box-shadow:0 0 14px rgba(39,227,255,.25)}
.feed div{animation:pulse 7s infinite;transition:transform .2s}
.feed div:hover{transform:translateX(3px)}
.rng{position:absolute;left:50%;top:50%;width:150px;height:150px;margin:-75px 0 0 -75px;border:2px solid var(--ga);border-radius:50%;pointer-events:none}
a{color:var(--ga);text-decoration:none}
::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:rgba(39,227,255,.25);border-radius:4px}
</style></head><body><div id="hud">
<div class="corner" style="top:6px;left:6px;border-right:0;border-bottom:0"></div>
<div class="corner" style="top:6px;right:6px;border-left:0;border-bottom:0"></div>
<div class="corner" style="bottom:6px;left:6px;border-right:0;border-top:0"></div>
<div class="corner" style="bottom:6px;right:6px;border-left:0;border-top:0"></div>
<div class="scan"></div>
<div id="parts" style="position:absolute;inset:0;z-index:1"></div>

<div style="position:relative;z-index:5;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #102a33;padding-bottom:10px">
 <div style="display:flex;align-items:center;gap:10px">
  <span style="width:10px;height:10px;border-radius:50%;background:var(--ga);box-shadow:0 0 10px var(--ga);animation:pulse 2s infinite"></span>
  <span style="color:var(--ga);letter-spacing:.18em;font-size:15px;font-weight:600;white-space:nowrap;animation:glow 3s ease-in-out infinite">GENESIS</span>
  <span id="vtag" style="font-size:11px;color:#4d7a86;letter-spacing:.14em">v6 · LOCAL</span>
 </div>
 <div style="display:flex;gap:8px">
  <button class="btn" onclick="seeScreen()"><i class="ti ti-eye"></i> Ver pantalla</button>
  <button class="btn" onclick="toggleUltron()"><i class="ti ti-flame"></i> <span id="mode">ULTRON</span></button>
 </div>
</div>

<div style="position:relative;z-index:5;display:grid;grid-template-columns:170px 1fr 220px;gap:14px;margin-top:14px">
 <div>
  <div style="font-size:10px;letter-spacing:.18em;color:#4d7a86;margin-bottom:8px">SISTEMA</div>
  <div id="tel"></div>
  <div class="chip" style="margin-top:12px">
   <div style="font-size:9px;color:#4d7a86;letter-spacing:.12em">SENTIDOS</div>
   <div style="font-size:11px;margin-top:6px;color:#7fbccb"><i class="ti ti-microphone"></i> oír · vosk</div>
   <div style="font-size:11px;margin-top:4px;color:#7fbccb"><i class="ti ti-volume"></i> hablar · edge-tts</div>
   <div style="font-size:11px;margin-top:4px;color:#7fbccb"><i class="ti ti-eye"></i> ver · llava</div>
  </div>
 </div>

 <div style="display:flex;flex-direction:column;align-items:center;position:relative">
  <div id="rings" style="position:absolute;inset:0"></div>
  <canvas id="plasma" width="250" height="250" style="position:absolute;top:0;left:50%;transform:translateX(-50%);width:250px;height:250px;pointer-events:none;opacity:0;transition:opacity .45s ease;mix-blend-mode:screen;z-index:1"></canvas>
  <svg viewBox="0 0 260 260" width="250" height="250" style="position:relative;z-index:2">
   <defs><clipPath id="cl"><circle cx="130" cy="130" r="100"/></clipPath></defs>
   <circle cx="130" cy="130" r="100" fill="none" stroke="#0e2a33"/>
   <g class="Sw" clip-path="url(#cl)"><path d="M130 130 L130 30 A100 100 0 0 1 215 80 Z" fill="var(--ga)" opacity=".12"/><line x1="130" y1="130" x2="130" y2="30" stroke="var(--ga)" stroke-width="1.5" opacity=".8"/></g>
   <g class="S"><circle cx="130" cy="130" r="96" fill="none" stroke="var(--ga)" stroke-width="2" stroke-dasharray="5 16" opacity=".7"/></g>
   <g class="Sr"><circle cx="130" cy="130" r="80" fill="none" stroke="var(--ga)" stroke-width="1" stroke-dasharray="2 11" opacity=".5"/><circle cx="130" cy="50" r="3.5" fill="var(--ga)"/></g>
   <circle cx="130" cy="130" r="62" fill="none" stroke="#103039" stroke-width="9"/>
   <circle id="evring" cx="130" cy="130" r="62" fill="none" stroke="var(--ga)" stroke-width="9" stroke-linecap="round" stroke-dasharray="390" stroke-dashoffset="120" transform="rotate(-90 130 130)"/>
   <text id="gen" x="130" y="118" text-anchor="middle" fill="var(--ga)" style="font-size:14px;letter-spacing:.12em">GEN —</text>
   <text id="osc" x="130" y="150" text-anchor="middle" fill="#dff6fc" style="font-size:30px">—</text>
   <text x="130" y="168" text-anchor="middle" fill="#4d7a86" style="font-size:9px;letter-spacing:.22em">EVOLUCIÓN</text>
  </svg>
  <div id="oscbars" style="display:none;gap:4px;align-items:center;height:60px;position:absolute;top:95px"></div>
  <div id="state" style="font-size:11px;letter-spacing:.16em;color:#4d7a86;margin-top:2px"><i class="ti ti-volume-3"></i> EN ESPERA</div>
 </div>

 <div>
  <div style="font-size:10px;letter-spacing:.18em;color:#4d7a86;margin-bottom:8px">ACTIVIDAD AUTÓNOMA</div>
  <div class="feed" id="feed" style="display:flex;flex-direction:column;gap:6px;font-size:11px"></div>
 </div>
</div>

<div style="position:relative;z-index:5;display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px">
 <div class="chip" style="text-align:center"><div style="font-size:9px;color:#4d7a86">MEMORIA</div><div id="s-mem" style="color:var(--ga);font-size:17px">—</div></div>
 <div class="chip" style="text-align:center"><div style="font-size:9px;color:#4d7a86">BUILDS OK</div><div id="s-build" style="color:var(--ga);font-size:17px">—</div></div>
 <div class="chip" style="text-align:center"><div style="font-size:9px;color:#4d7a86">CURIOSIDAD</div><div id="s-cur" style="color:var(--ga);font-size:17px">—</div></div>
 <div class="chip" style="text-align:center"><div style="font-size:9px;color:#4d7a86">INTERACC.</div><div id="s-int" style="color:var(--ga);font-size:17px">—</div></div>
</div>

<div id="player" style="position:relative;z-index:5;display:none;margin-top:12px;border:1px solid #102a33;border-radius:10px;overflow:hidden;background:#000">
 <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:#060c14">
  <span id="nowplaying" style="color:var(--ga);font-size:11px;letter-spacing:.08em"><i class="ti ti-music"></i> reproduciendo</span>
  <span onclick="stopPlayer()" style="cursor:pointer;color:#7fbccb;font-size:14px" title="cerrar"><i class="ti ti-x"></i></span>
 </div>
 <audio id="ap" style="width:100%;display:block" controls autoplay></audio>
 <div style="padding:4px 10px;background:#060c14"><a id="ytlink" href="#" target="_blank" style="color:#4d7a86;font-size:10px"><i class="ti ti-brand-youtube"></i> ver el video en YouTube</a></div>
</div>

<div id="sub" style="position:relative;z-index:5;min-height:24px;color:#dff6fc;font-size:14px;line-height:1.5;margin-top:12px;padding:10px 14px;max-height:240px;overflow-y:auto;text-align:left"></div>

<div style="position:relative;z-index:5;margin-top:10px;display:flex;align-items:center;gap:6px;font-size:11px;color:#4d7a86">
 <i class="ti ti-volume" style="color:var(--ga)"></i>
 <span>Voz:</span>
 <select id="voicesel" onchange="saveVoice()" style="flex:1;max-width:230px;background:#060c14;color:#cfeff8;border:1px solid #123440;border-radius:6px;padding:5px 6px;font-family:inherit;font-size:11px"></select>
 <button class="btn" style="padding:5px 10px;font-size:10px" onclick="previewVoice()"><i class="ti ti-player-play"></i> probar</button>
</div>

<div style="position:relative;z-index:5;margin-top:8px;display:flex;align-items:center;gap:8px;border:1px solid #102a33;border-radius:10px;padding:8px;background:#060c14">
 <span id="micbtn" onclick="toggleMic()" title="Hablar (click para grabar)" style="cursor:pointer;color:var(--ga);padding:4px 6px;border-radius:8px;transition:all .2s"><i class="ti ti-microphone" style="font-size:18px"></i></span>
 <input id="msg" placeholder="Habla o escribe una orden…" onkeydown="if(event.key==='Enter')sendChat()">
 <button class="btn" onclick="sendChat()"><i class="ti ti-send"></i></button>
</div>
</div>
<script>
var H=document.getElementById('hud');
function $(i){return document.getElementById(i)}
var parts='';for(var i=0;i<24;i++){var s=(1+Math.random()*2.5).toFixed(1);parts+='<span class="p" style="left:'+(Math.random()*100).toFixed(1)+'%;top:'+(Math.random()*100).toFixed(1)+'%;width:'+s+'px;height:'+s+'px;animation-duration:'+(3+Math.random()*4).toFixed(1)+'s;animation-delay:'+(Math.random()*4).toFixed(1)+'s;opacity:.5"></span>';}
$('parts').innerHTML=parts;
var ob=$('oscbars');for(i=0;i<11;i++){var b=document.createElement('i');b.style.cssText='width:4px;height:6px;background:var(--ga);border-radius:2px;box-shadow:0 0 6px var(--ga)';ob.appendChild(b);}
function tel(label,val,extra){return '<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:10px;color:#6fb6c6;margin-bottom:3px"><span>'+label+'</span><span>'+val+(extra||'')+'</span></div><div class="bar"><i style="width:'+Math.min(100,val)+'%"></i></div></div>';}
function pollSys(){fetch('/api/system').then(r=>r.json()).then(d=>{
 $('tel').innerHTML=tel('CPU',Math.round(d.cpu_percent||0),'%')+tel('RAM',Math.round(d.ram_percent||0),'%')+tel('GPU',Math.round(d.gpu_percent||0),'%')+tel('VRAM',Math.round((d.vram_used_mb||0)/(d.vram_total_mb||1)*100),'%');
}).catch(()=>{});}
function pollHud(){fetch('/api/hud').then(r=>r.json()).then(d=>{
 $('vtag').textContent='v'+(d.version||'6')+' · LOCAL';
 $('gen').textContent='GEN '+(d.generation||0);
 $('osc').textContent=(d.generation||0);
 var fill=390-Math.min(100,(d.interactions||0))/100*270;$('evring').setAttribute('stroke-dashoffset',fill);
 $('s-mem').textContent=d.memories||0;$('s-build').textContent=(d.builds_ok||0);$('s-cur').textContent=d.curiosity||0;$('s-int').textContent=d.interactions||0;
 var ic={INVESTIGANDO:'ti-world-search',HALLAZGO:'ti-bulb',CONSTRUCTOR:'ti-tool',BG_TASK:'ti-cpu',SELFIMPROVE_SKIP:'ti-dna',CICLO_COMPLETO:'ti-refresh',DESPERTAR:'ti-bolt',INICIO:'ti-power'};
 var f=(d.activity||[]).map(function(a,i){var k=(a.action||'').split(':')[0];return '<div style="border-left:2px solid var(--ga);padding:4px 8px;background:#070f17;animation-delay:'+(i*0.4)+'s"><div style="color:var(--ga);font-size:9px;letter-spacing:.1em"><i class="ti '+(ic[k]||'ti-point')+'"></i> '+(a.action||'').slice(0,22)+'</div><div style="color:#7fbccb;font-size:10px;margin-top:1px">'+(a.detail||'')+'</div></div>';}).join('');
 $('feed').innerHTML=f||'<div style="color:#3f6b77;font-size:10px">en reposo…</div>';
}).catch(()=>{});}
function setState(s,t){var m={idle:['ti-volume-3','EN ESPERA','#4d7a86'],think:['ti-brain','PENSANDO','var(--ga)'],speak:['ti-volume','HABLANDO','var(--ga)'],see:['ti-eye','MIRANDO','var(--ga)'],listen:['ti-microphone','ESCUCHANDO','var(--ga)']};var x=m[s]||m.idle;$('state').innerHTML='<i class="ti '+x[0]+'"></i> <span style="color:'+x[2]+'">'+(t||x[1])+'</span>';}
var ringT=null,oscT=null;
function startSpeakViz(){ob.style.display='flex';setState('speak');var bars=ob.querySelectorAll('i');
 ringT=setInterval(function(){var r=document.createElement('div');r.className='rng';r.style.animation='ring 1.8s ease-out forwards';$('rings').appendChild(r);setTimeout(function(){r.remove()},1800)},420);
 oscT=setInterval(function(){bars.forEach(function(b){b.style.height=(6+Math.round(Math.random()*52))+'px'})},95);}
function stopSpeakViz(){clearInterval(ringT);clearInterval(oscT);ob.style.display='none';plasmaStop();setState('idle');}
/* ---- Plasma reactivo: se enciende cuando Genesis habla y late con la voz real ---- */
var pAC=null,pAna=null,pFreq=null,plasmaRun=false,pSmooth=0;
var PCV=$('plasma'),PCTX=PCV?PCV.getContext('2d'):null,PR=2;
if(PCV){PCV.width=250*PR;PCV.height=250*PR;PCTX.scale(PR,PR);}
var PBLOBS=[];for(var _i=0;_i<6;_i++){PBLOBS.push({sp:.5+Math.random()*.7,fx:1+Math.random()*1.6,fy:1+Math.random()*1.6,ph:Math.random()*6.28,r:46+Math.random()*34,h:[ '80,235,255','40,150,255','120,255,235','60,120,255','170,240,255','30,200,255'][_i]});}
function drawPlasma(t,amp){
 if(!PCTX)return;PCTX.clearRect(0,0,250,250);PCTX.globalCompositeOperation='lighter';
 var cx=125,cy=125;
 for(var i=0;i<PBLOBS.length;i++){var b=PBLOBS[i];var a=t*b.sp+b.ph;
  var x=cx+Math.cos(a*b.fx)*(30+amp*42),y=cy+Math.sin(a*b.fy)*(30+amp*42);
  var r=b.r*(0.62+amp*0.95),al=0.30+amp*0.55;
  var g=PCTX.createRadialGradient(x,y,0,x,y,r);
  g.addColorStop(0,'rgba('+b.h+','+al+')');g.addColorStop(.45,'rgba('+b.h+','+(al*0.35).toFixed(3)+')');g.addColorStop(1,'rgba('+b.h+',0)');
  PCTX.fillStyle=g;PCTX.beginPath();PCTX.arc(x,y,r,0,6.2832);PCTX.fill();}
 /* núcleo brillante que pulsa */
 var cg=PCTX.createRadialGradient(cx,cy,0,cx,cy,30+amp*40);
 cg.addColorStop(0,'rgba(225,250,255,'+(0.35+amp*0.5)+')');cg.addColorStop(1,'rgba(120,230,255,0)');
 PCTX.fillStyle=cg;PCTX.beginPath();PCTX.arc(cx,cy,30+amp*40,0,6.2832);PCTX.fill();
 /* máscara circular: recorta al disco del orbe */
 PCTX.globalCompositeOperation='destination-in';
 var m=PCTX.createRadialGradient(cx,cy,30,cx,cy,116);
 m.addColorStop(0,'rgba(255,255,255,1)');m.addColorStop(.78,'rgba(255,255,255,1)');m.addColorStop(1,'rgba(255,255,255,0)');
 PCTX.fillStyle=m;PCTX.fillRect(0,0,250,250);PCTX.globalCompositeOperation='source-over';}
function plasmaLoop(){if(!plasmaRun)return;
 var amp=0.34;
 if(pAna){pAna.getByteFrequencyData(pFreq);var s=0;for(var i=2;i<pFreq.length;i++)s+=pFreq[i];amp=Math.min(1,(s/(pFreq.length-2))/95);}
 else{amp=0.3+0.22*Math.abs(Math.sin(performance.now()/170));}
 pSmooth+=(amp-pSmooth)*0.28;
 drawPlasma(performance.now()/1000,pSmooth);
 requestAnimationFrame(plasmaLoop);}
function plasmaStart(audio){if(!PCV)return;PCV.style.opacity='1';
 try{pAC=pAC||new(window.AudioContext||window.webkitAudioContext)();if(pAC.state==='suspended')pAC.resume();
  var src=pAC.createMediaElementSource(audio);pAna=pAC.createAnalyser();pAna.fftSize=64;pAna.smoothingTimeConstant=0.7;
  src.connect(pAna);pAna.connect(pAC.destination);pFreq=new Uint8Array(pAna.frequencyBinCount);
 }catch(e){pAna=null;}
 if(!plasmaRun){plasmaRun=true;plasmaLoop();}}
function plasmaStop(){plasmaRun=false;pAna=null;if(PCV)PCV.style.opacity='0';
 if(PCTX)setTimeout(function(){PCTX.clearRect(0,0,250,250);},460);}
function getVoice(){return $('voicesel').value||localStorage.getItem('gx_voice')||'es-ES-AlvaroNeural';}
function saveVoice(){localStorage.setItem('gx_voice',$('voicesel').value);}
function loadVoices(){fetch('/api/tts/voices?lang=es').then(r=>r.json()).then(d=>{var sel=$('voicesel');var saved=localStorage.getItem('gx_voice')||'es-AR-ElenaNeural';var vs=(d.voices||[]).sort(function(a,b){return (a.id||'').localeCompare(b.id||'')});sel.innerHTML=vs.map(function(v){var id=v.id;var g=(v.gender||'')[0]||'';var loc=(v.locale||'').replace('es-','');var nm=id.split('-').pop().replace('Neural','');return '<option value="'+id+'"'+(id===saved?' selected':'')+'>'+loc+' · '+nm+' ('+g+')</option>';}).join('');}).catch(function(){});}
function previewVoice(){speak('Hola, soy Genesis. Esta es mi voz, ¿te gusta?');}
function speak(text){fetch('/api/tts/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,voice:getVoice()})}).then(r=>r.ok?r.blob():null).then(b=>{if(!b){return;}var a=new Audio(URL.createObjectURL(b));startSpeakViz();plasmaStart(a);a.onended=stopSpeakViz;a.play().catch(stopSpeakViz);}).catch(stopSpeakViz);}
function playInApp(vid,label){var a=$('ap');a.src='/api/audio/'+vid;$('ytlink').href='https://www.youtube.com/watch?v='+vid;$('nowplaying').innerHTML='<i class="ti ti-music"></i> '+(label||'reproduciendo');$('player').style.display='block';a.play().catch(function(){});}
function pausePlayer(){try{$('ap').pause();}catch(e){}$('nowplaying').innerHTML='<i class="ti ti-player-pause"></i> en pausa';}
function resumePlayer(){if($('player').style.display==='none'&&$('ap').src){$('player').style.display='block';}try{$('ap').play();}catch(e){}$('nowplaying').innerHTML='<i class="ti ti-music"></i> reproduciendo';}
function stopPlayer(){var a=$('ap');try{a.pause();}catch(e){}a.src='';$('player').style.display='none';}
var micActive=false,micCtx=null,micProc=null,micStream=null,micBufs=[];
function toggleMic(){ micActive?micStop():micStart(); }
async function micStart(){
 try{
  micStream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16000,channelCount:1,echoCancellation:true,noiseSuppression:true}});
  micActive=true;micBufs=[];
  $('micbtn').style.background='var(--ga)';$('micbtn').style.color='#04070d';setState('listen');
  $('sub').innerHTML='<span style="color:var(--ga)"><i class="ti ti-microphone"></i> Escuchando… (click el mic para parar)</span>';
  micCtx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16000});
  var src=micCtx.createMediaStreamSource(micStream);
  micProc=micCtx.createScriptProcessor(4096,1,1);
  micProc.onaudioprocess=function(e){if(!micActive)return;var f=e.inputBuffer.getChannelData(0);var a=new Int16Array(f.length);for(var i=0;i<f.length;i++)a[i]=Math.max(-32768,Math.min(32767,Math.floor(f[i]*32768)));micBufs.push(a);};
  src.connect(micProc);micProc.connect(micCtx.destination);
  setTimeout(function(){if(micActive)micStop();},15000);
 }catch(err){micActive=false;$('micbtn').style.background='';$('micbtn').style.color='var(--ga)';setState('idle');$('sub').textContent='[micrófono denegado o no disponible]';}
}
function micStop(){
 if(!micActive)return;micActive=false;
 $('micbtn').style.background='';$('micbtn').style.color='var(--ga)';
 $('sub').innerHTML='<span style="color:#5a8a99">procesando audio…</span>';
 // Capturar el sampleRate REAL antes de cerrar (el navegador suele ignorar el pedido de 16000)
 var sr=(micCtx&&micCtx.sampleRate)?Math.round(micCtx.sampleRate):16000;
 if(micProc){micProc.disconnect();micProc=null;}if(micCtx){micCtx.close();micCtx=null;}if(micStream){micStream.getTracks().forEach(function(t){t.stop();});micStream=null;}
 var total=micBufs.reduce(function(s,b){return s+b.length;},0);
 if(!total){setState('idle');$('sub').textContent='no capté audio';return;}
 // NORMALIZAR: el mic suele captar bajísimo (peak ~268/32767). Subimos el
 // volumen para que vosk lo entienda. Buscamos el pico y amplificamos hasta
 // ~10000, con tope de 30x para no reventar el ruido de fondo.
 var peak=1;for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++){var a=Math.abs(b[i]);if(a>peak)peak=a;}}
 var gain=Math.min(30,Math.max(1,10000/peak));
 if(gain>1){for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++){b[i]=Math.max(-32768,Math.min(32767,Math.round(b[i]*gain)));}}}
 var buf=new ArrayBuffer(44+total*2),v=new DataView(buf);
 function ws(o,s){for(var i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));}
 ws(0,'RIFF');v.setUint32(4,36+total*2,true);ws(8,'WAVE');ws(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,sr,true);v.setUint32(28,sr*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);ws(36,'data');v.setUint32(40,total*2,true);
 var off=44;for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++){v.setInt16(off,b[i],true);off+=2;}}
 var fd=new FormData();fd.append('audio',new Blob([buf],{type:'audio/wav'}),'rec.wav');
 fetch('/api/stt',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){
  var txt=(d.text||d.transcript||'').trim();
  setState('idle');
  if(txt){$('msg').value=txt;sendChat();}else{$('sub').textContent='no entendí, probá de nuevo';}
 }).catch(function(){setState('idle');$('sub').textContent='[error transcribiendo]';});
}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function md(t){
 // bloques de codigo ```lang\n...```
 t=esc(t).replace(/```[a-zA-Z0-9+]*\n?([\s\S]*?)```/g,function(_,c){return '<pre style="background:#020912;border:1px solid rgba(39,227,255,.25);border-radius:8px;padding:10px;overflow-x:auto;margin:8px 0"><code style="color:#9fe9c9;font-family:ui-monospace,Consolas,monospace;font-size:12px;line-height:1.45">'+c.replace(/\n$/,'')+'</code></pre>';});
 t=t.replace(/`([^`]+)`/g,'<code style="background:rgba(39,227,255,.12);padding:1px 5px;border-radius:4px;color:#9fe9c9">$1</code>');
 t=t.replace(/\*\*([^*]+)\*\*/g,'<b style="color:#dff6fc">$1</b>');
 t=t.replace(/^[\-\*] (.+)$/gm,'<div style="padding-left:14px">• $1</div>');
 t=t.replace(/\n{2,}/g,'<br><br>').replace(/\n/g,'<br>');
 return t;
}
function showResp(html){$('sub').innerHTML=html;$('sub').scrollTop=0;}
function sendChat(){var m=$('msg').value.trim();if(!m)return;$('msg').value='';$('sub').innerHTML='<span style="color:#5a8a99">› '+esc(m)+'</span>';setState('think');
 fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})}).then(r=>r.json()).then(d=>{var t=d.response||d.error||'(sin respuesta)';
  if(t.indexOf('[[STOP]]')>=0){t=t.replace('[[STOP]]','').trim();stopPlayer();}
  if(t.indexOf('[[PAUSE]]')>=0){t=t.replace('[[PAUSE]]','').trim();pausePlayer();}
  if(t.indexOf('[[RESUME]]')>=0){t=t.replace('[[RESUME]]','').trim();resumePlayer();}
  if(t.indexOf('[[ULTRON]]')>=0){t=t.replace('[[ULTRON]]','').trim();if(getComputedStyle(H).getPropertyValue('--ga').trim()!=='#ff3b30')toggleUltron();}
  var vm=t.match(/\[\[VOICE:([\w:-]+)\]\]/);
  if(vm){t=t.replace(/\[\[VOICE:[\w:-]+\]\]/,'').trim();var vs=$('voicesel');if(vs){vs.value=vm[1];saveVoice();}}
  var pm=t.match(/\[\[PLAY:([\w-]+)\]\]/);
  if(pm){t=t.replace(/\[\[PLAY:[\w-]+\]\]/,'').trim();playInApp(pm[1],t.split('\n')[0].slice(0,60));}
  showResp(md(t));setState('idle');var spoken=t.replace(/```[\s\S]*?```/g,'. código en pantalla.').replace(/[`*#>]/g,'');speak(spoken.slice(0,500));pollHud();}).catch(()=>{$('sub').textContent='[error de conexión]';setState('idle');});}
function seeScreen(){setState('see');$('sub').textContent='Mirando la pantalla…';
 fetch('/api/screenshot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analyze:true})}).then(r=>r.json()).then(d=>{var t=d.analysis||d.error||'(sin análisis)';showResp('👁 '+md(t));setState('idle');speak(t.replace(/[`*#>]/g,'').slice(0,500));}).catch(()=>{$('sub').textContent='[no pude capturar]';setState('idle');});}
function toggleUltron(){var u=getComputedStyle(H).getPropertyValue('--ga').trim()==='#ff3b30';if(u){H.style.setProperty('--ga','#27e3ff');H.style.background='#04070d';$('mode').textContent='ULTRON';}else{H.style.setProperty('--ga','#ff3b30');H.style.background='#0c0506';$('mode').textContent='JARVIS';}}
pollSys();pollHud();loadVoices();setInterval(pollSys,4000);setInterval(pollHud,5000);
</script></body></html>"""


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

        # Monitoreo: registrar petición + respuesta + latencia (JSONL)
        _log_interaction(client_ip, message, response, elapsed)

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
            _nw = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows: no parpadea consola
            gpu_out = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, creationflags=_nw,
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


@app.route("/api/hud")
def api_hud():
    """Datos en vivo consolidados para el HUD JARVIS (un solo poll)."""
    g = get_genesis()
    d = {"version": GENESIS_VERSION}
    try: d["generation"] = g.evolution.get_generation()
    except Exception: d["generation"] = 0
    try: d["interactions"] = g.evolution.interaction_count
    except Exception: d["interactions"] = 0
    try: d["memories"] = len(g.memory.long_term.memories)
    except Exception: d["memories"] = 0
    try:
        bs = g.builder_engine.get_stats()
        d["builds_ok"] = bs.get("successful", 0)
        d["builds_total"] = bs.get("total_builds", 0)
    except Exception:
        d["builds_ok"] = 0; d["builds_total"] = 0
    try: d["curiosity"] = len(g.curiosity.get_pending_questions(50))
    except Exception: d["curiosity"] = 0
    try:
        acts = g.heartbeat.log.get_recent(6)
        d["activity"] = [{"action": a.get("action", ""), "detail": (a.get("details", "") or "")[:64]}
                         for a in reversed(acts)]
    except Exception:
        d["activity"] = []
    return jsonify(d)


def _brand(html):
    """Reemplaza las marcas visibles GENESIS/JARVIS por el nombre configurado por
    el usuario. Solo toca MAYÚSCULAS (texto display) y la palabra capitalizada
    «Genesis» (tooltips); NO toca rutas/ids en minúscula (/jarvis, /core), que no
    aparecen en mayúscula. Si el nombre es el default 'Genesis', no cambia nada."""
    try:
        from core.assistant_identity import get_name
        name = get_name()
    except Exception:
        name = "Genesis"
    if name.strip().lower() == "genesis":
        return html
    import re
    up = name.upper()
    html = html.replace("GENESIS // JARVIS", up)
    html = html.replace("GENESIS", up).replace("JARVIS", up)
    html = re.sub(r"\bGenesis\b", lambda m: name, html)
    return html


@app.route("/jarvis")
def jarvis_hud():
    """Interfaz HUD tipo JARVIS, cableada a datos reales de Genesis."""
    return _brand(_JARVIS_HTML)


_CORE_HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS CORE</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.7.0/dist/tabler-icons.min.css">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:ui-monospace,'Cascadia Code',Consolas,monospace;background:#03070a;color:#a9f0d6;overflow-x:hidden;-webkit-font-smoothing:antialiased}
#core{--g:#2dffae;min-height:100vh;padding:16px;position:relative;overflow:hidden;
 background:radial-gradient(120% 70% at 50% -10%,rgba(45,255,174,.08),transparent 55%),#03070a}
#core::after{content:"";position:absolute;inset:0;pointer-events:none;box-shadow:inset 0 0 150px rgba(0,0,0,.7)}
@keyframes blink{0%,100%{opacity:.4}50%{opacity:1}}
@keyframes glow{0%,100%{text-shadow:0 0 10px rgba(45,255,174,.5)}50%{text-shadow:0 0 20px rgba(45,255,174,.9)}}
@keyframes scan{0%{top:-40px}100%{top:100%}}
.scan{position:absolute;left:0;right:0;height:40px;background:linear-gradient(rgba(45,255,174,0),rgba(45,255,174,.08),rgba(45,255,174,0));animation:scan 8s linear infinite;pointer-events:none}
.panel{border:1px solid rgba(45,255,174,.2);border-radius:10px;background:rgba(7,18,16,.55);backdrop-filter:blur(6px)}
.btn{cursor:pointer;font-family:inherit;letter-spacing:.1em;font-size:12px;color:var(--g);border:1px solid rgba(45,255,174,.45);border-radius:8px;padding:9px 14px;background:rgba(45,255,174,.06);transition:all .2s}
.btn:hover{background:rgba(45,255,174,.16);box-shadow:0 0 14px rgba(45,255,174,.3)}
input{font-family:inherit;background:rgba(5,14,12,.8);border:1px solid rgba(45,255,174,.25);color:#d6ffe9;border-radius:9px;padding:12px 13px;font-size:13px;outline:none;flex:1}
input:focus{border-color:var(--g);box-shadow:0 0 12px rgba(45,255,174,.25)}
.card{border:1px solid rgba(45,255,174,.2);border-left:3px solid var(--g);border-radius:8px;padding:10px 12px;background:rgba(7,18,16,.6);transition:transform .15s}
.card:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(45,255,174,.12)}
a{color:var(--g);text-decoration:none}
::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:rgba(45,255,174,.25);border-radius:4px}
.topbar{position:relative;z-index:6;display:flex;justify-content:space-between;align-items:center;padding:2px 4px}
.brand{display:flex;align-items:center;gap:9px;color:var(--g);letter-spacing:.2em;font-size:13px;font-weight:600;animation:glow 3s infinite}
.toprt{display:flex;align-items:center;gap:14px;font-size:10px;color:#4d8a76;letter-spacing:.14em}
.hero{position:relative;z-index:5;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;min-height:92vh;text-align:center;gap:8px;padding-top:6px}
.corecenter{flex:1;min-height:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;width:100%}
.statuslbl{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(45,255,174,.25);background:rgba(7,18,16,.6);border-radius:20px;padding:5px 16px;color:var(--g);font-size:11px;letter-spacing:.2em}
.orbwrap{position:relative;width:480px;height:480px;margin:2px 0}
.orbwrap canvas,.orbwrap svg{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:480px;height:480px}
.orbwrap canvas{filter:drop-shadow(0 0 16px rgba(30,120,150,.28)) drop-shadow(0 0 44px rgba(20,90,130,.16));animation:orbpulse 6s ease-in-out infinite}
@keyframes orbpulse{0%,100%{filter:drop-shadow(0 0 12px rgba(30,120,150,.18)) drop-shadow(0 0 32px rgba(20,90,130,.1))}50%{filter:drop-shadow(0 0 20px rgba(40,140,170,.28)) drop-shadow(0 0 46px rgba(25,100,140,.16))}}
.bubble{max-width:540px;border:1px solid rgba(45,255,174,.2);border-radius:12px;background:rgba(7,18,16,.7);backdrop-filter:blur(6px);padding:12px 16px;font-size:14px;line-height:1.5;text-align:left;max-height:230px;overflow-y:auto}
.dock{display:flex;gap:11px;flex-wrap:wrap;justify-content:center;margin-top:4px}
.dockbtn{width:80px;height:74px;border:1px solid rgba(45,255,174,.3);border-radius:14px;background:rgba(7,18,16,.55);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;cursor:pointer;transition:all .18s;color:#9fe9c9}
.dockbtn:hover{background:rgba(45,255,174,.14);box-shadow:0 0 18px rgba(45,255,174,.25);transform:translateY(-2px)}
.dockbtn i{font-size:22px;color:var(--g)}
.dockbtn span{font-size:9px;letter-spacing:.12em}
.modalbg{position:fixed;inset:0;z-index:30;background:rgba(2,6,8,.62);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center}
.mdlbox{width:450px;max-width:92vw;padding:18px 20px}
.mitem{border:1px solid rgba(45,255,174,.22);border-radius:10px;padding:11px 13px;margin-top:8px;cursor:pointer;color:#cfeede;font-size:13px;transition:all .15s}
.mitem:hover{background:rgba(45,255,174,.12);border-color:var(--g)}
.corner{position:fixed;bottom:14px;z-index:6;font-size:11px;color:#5a7a70;letter-spacing:.12em;cursor:pointer}
.corner:hover{color:var(--g)}
/* Accesibilidad: foco visible por teclado (antes no había ninguno) */
:focus-visible{outline:2px solid var(--g);outline-offset:3px;border-radius:8px}
/* Onboarding: tarjeta de bienvenida (primera vez) */
#tip{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:25;max-width:560px;width:92vw;
 background:rgba(8,20,16,.96);border:1px solid var(--g);border-radius:12px;padding:14px 16px;color:#dff5ea;
 font-size:13px;line-height:1.55;box-shadow:0 8px 30px rgba(0,0,0,.5),0 0 18px rgba(45,255,174,.15)}
#tip b{color:var(--g)}
#tip .x{float:right;cursor:pointer;color:#7fceb3;border:1px solid rgba(45,255,174,.3);border-radius:6px;padding:2px 8px;font-size:12px}
/* Responsive: usable en pantallas chicas / celular */
@media (max-width:640px){
 #core{padding:10px}
 .hero{min-height:83vh;padding-top:4px;gap:6px}
 .orbwrap{width:420px;height:420px}
 .orbwrap canvas,.orbwrap svg{width:420px!important;height:420px!important}
 #tablero{position:static!important;top:auto!important;right:auto!important;width:auto!important;max-width:none!important;max-height:24vh;margin:8px 0 0}
 .topbar{flex-wrap:wrap;gap:6px}
 .toprt{gap:6px;flex-wrap:wrap}
 .bubble{font-size:13px}
 #cplayer{width:94vw!important}
}
</style></head><body><div id="core">
<canvas id="stars" style="position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none"></canvas>

<div class="topbar">
 <div class="brand" onclick="openTip()" title="Cómo usar Genesis" style="cursor:help"><span style="width:8px;height:8px;border-radius:50%;background:var(--g);box-shadow:0 0 10px var(--g);animation:blink 2s infinite"></span> JARVIS · MARK 5</div>
 <div class="toprt">
  <span id="stats">GPU --% · CPU --%</span>
  <span onclick="location.href='/mission'" style="cursor:pointer;border:1px solid rgba(45,255,174,.3);border-radius:6px;padding:5px 9px;color:var(--g)">MISSION CONTROL ►</span>
 </div>
</div>

<div id="tablero" class="panel" style="position:absolute;top:58px;right:16px;width:236px;max-height:46vh;overflow:auto;padding:12px;z-index:6">
 <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
  <span style="color:var(--g);font-size:11px;letter-spacing:.14em"><i class="ti ti-clipboard-data"></i> TABLERO DE EVIDENCIAS</span>
  <span id="boardstatus" style="font-size:9px;color:#4d8a76">en espera</span>
 </div>
 <div id="board" style="color:#6aa78f;font-size:12px;line-height:1.6;text-align:center">
  Aquí aparecen tus investigaciones.<br><span style="color:#4d8a76">ej: <i>investigá el dólar</i></span>
 </div>
</div>

<div class="hero">
 <div class="corecenter">
 <div id="state" class="statuslbl"><span id="statedot" style="width:9px;height:9px;border-radius:50%;background:var(--g);box-shadow:0 0 8px var(--g)"></span><span id="statetxt">JARVIS · CALMADO</span></div>
 <div class="orbwrap">
  <canvas id="plasma" width="172" height="172"></canvas>
 </div>
 <div id="answer" class="bubble" style="display:none"></div>
 <div id="cplayer" class="panel" style="display:none;padding:8px 12px;width:540px;max-width:92vw">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><span id="cnow" style="color:var(--g);font-size:11px"><i class="ti ti-music"></i> reproduciendo</span><span onclick="cstop()" style="cursor:pointer;color:#7fceb3"><i class="ti ti-x"></i></span></div>
  <audio id="cap" style="width:100%" controls autoplay></audio>
 </div>
 </div><!-- /corecenter -->
 <div class="dock">
  <div class="dockbtn" onclick="openDock('buscar')"><i class="ti ti-search"></i><span>BUSCAR</span></div>
  <div class="dockbtn" onclick="openDock('webs')"><i class="ti ti-world"></i><span>WEBS</span></div>
  <div class="dockbtn" onclick="openDock('musica')"><i class="ti ti-music"></i><span>MÚSICA</span></div>
  <div class="dockbtn" onclick="openDock('crear')"><i class="ti ti-palette"></i><span>CREAR</span></div>
  <div class="dockbtn" onclick="openDock('ver')"><i class="ti ti-eye"></i><span>VER</span></div>
  <div class="dockbtn" onclick="nucleo()"><i class="ti ti-atom-2"></i><span>NÚCLEO</span></div>
 </div>
 <div style="display:flex;flex-direction:column;align-items:center;gap:7px;margin-top:4px;width:560px;max-width:94vw">
  <span id="micbtn" onclick="toggleMic()" style="cursor:pointer;width:54px;height:54px;border-radius:50%;border:1px solid rgba(45,255,174,.4);background:rgba(45,255,174,.06);display:flex;align-items:center;justify-content:center;color:var(--g);transition:all .2s"><i class="ti ti-microphone" style="font-size:22px"></i></span>
  <div style="font-size:10px;color:#4d8a76;letter-spacing:.18em">PULSE PARA CONVERSAR</div>
  <div style="display:flex;gap:8px;width:100%">
   <input id="msg" placeholder="o escribí aquí, señor…" onkeydown="if(event.key==='Enter')send()">
   <button class="btn" onclick="send()">ENVIAR</button>
  </div>
 </div>
</div>

<div id="camrow" class="corner" style="left:14px" onclick="toggleCam()"><i class="ti ti-camera-off"></i> CÁMARA · APAGADA</div>
<div class="corner" style="right:14px" onclick="openSettings()" title="Configuración (voz, correos, claves)"><i class="ti ti-settings" style="font-size:16px"></i></div>
<div id="tip" role="dialog" aria-label="Cómo usar Genesis" style="display:none">
 <span class="x" role="button" tabindex="0" onclick="closeTip()" aria-label="Cerrar ayuda">Entendido ✕</span>
 <div><b>👋 Hola, soy Genesis.</b> Podés interactuar de 3 formas:</div>
 <div style="margin-top:6px">🎙️ <b>Hablarme</b> (manos libres): decí «<b>genesis</b>» + tu pedido — ej: «<i>genesis, noticias</i>», «<i>genesis, estado del tiempo</i>».</div>
 <div>🔘 <b>Micrófono</b>: tocá el botón redondo y hablá.</div>
 <div>⌨️ <b>Escribir</b>: usá el campo de abajo. El <b>⚙️ engranaje</b> configura la voz.</div>
</div>
<div id="modal" class="modalbg" onclick="if(event.target===this)closeModal()"></div>
</div>
<script>
function $(i){return document.getElementById(i)}
var H=$('core');
/* La voz ahora se elige en el panel de Configuración de voz (engranaje). */
try{if(!localStorage.getItem('gx_voice'))localStorage.setItem('gx_voice','clon:milton');}catch(e){}
/* Los links EXTERNOS (resultados de investigación, etc.) abren en el navegador
   del sistema — nunca secuestran la cabina (antes te dejaba atrapado con 502). */
document.addEventListener('click',function(e){
 var a=e.target.closest?e.target.closest('a[href]'):null; if(!a)return;
 var h=a.getAttribute('href')||'';
 if(/^https?:\/\//i.test(h)&&h.indexOf('127.0.0.1')<0&&h.indexOf('localhost')<0){
  e.preventDefault();
  if(window.pywebview&&window.pywebview.api&&window.pywebview.api.open_external){window.pywebview.api.open_external(h);}
  else{window.open(h,'_blank');}
 }
},true);
function setState(s){var m={calm:['JARVIS · CALMADO','var(--g)'],proc:['JARVIS · PROCESANDO','#ffd24d'],talk:['JARVIS · HABLANDO','var(--g)'],listen:['JARVIS · ESCUCHANDO','#2dffae']};var x=m[s]||m.calm;$('statetxt').textContent=x[0];$('statedot').style.background=x[1];}
function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function md(t){t=esc(t).replace(/```[a-zA-Z0-9+]*\n?([\s\S]*?)```/g,function(_,c){return '<pre style="background:#021410;border:1px solid rgba(45,255,174,.25);border-radius:8px;padding:10px;overflow-x:auto;margin:8px 0"><code style="color:#9fe9c9;font-size:12px">'+c.replace(/\n$/,'')+'</code></pre>';});t=t.replace(/`([^`]+)`/g,'<code style="background:rgba(45,255,174,.12);padding:1px 5px;border-radius:4px">$1</code>');t=t.replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');t=t.replace(/\n/g,'<br>');return t;}
function speak(text){var v=localStorage.getItem('gx_voice')||'clon:milton';var rn=parseInt(localStorage.getItem('gx_rate')||'0',10)||0;var rs=(rn>=0?'+':'')+rn+'%';fetch('/api/tts/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:text,voice:v,rate:rs})}).then(r=>r.ok?r.blob():null).then(b=>{if(!b)return;setState('talk');var a=new Audio(URL.createObjectURL(b));plasmaSpeak(a);a.onended=function(){setState('calm');plasmaCalm();};a.play().catch(function(){setState('calm');plasmaCalm();});}).catch(function(){setState('calm');plasmaCalm();});}
function openVoiceCfg(){
 fetch('/api/voice/config').then(function(r){return r.json();}).then(function(d){
  var cur=localStorage.getItem('gx_voice')||(d.config&&d.config.voice)||'clon:milton';
  var rate=parseInt(localStorage.getItem('gx_rate'),10);if(isNaN(rate))rate=(d.config&&d.config.rate)||0;
  var opts=(d.voices||[]).map(function(v){return '<option value="'+v.id+'"'+(v.id===cur?' selected':'')+'>'+esc(v.label)+'</option>';}).join('');
  var h='<div class="panel" style="width:430px;max-width:94vw;padding:20px" onclick="event.stopPropagation()">';
  h+='<div style="color:var(--g);font-size:13px;letter-spacing:.12em;margin-bottom:14px"><i class="ti ti-microphone-2"></i> CONFIGURACIÓN DE VOZ</div>';
  h+='<div style="font-size:11px;color:#7fceb3;margin-bottom:5px">Tipo de voz</div>';
  h+='<select id="vcsel" style="width:100%;padding:9px;background:#06120e;color:#cfeee0;border:1px solid rgba(45,255,174,.3);border-radius:7px;font-size:13px">'+opts+'</select>';
  h+='<div style="font-size:11px;color:#7fceb3;margin:14px 0 5px">Velocidad: <b id="vcrl">'+(rate>=0?'+':'')+rate+'%</b></div>';
  h+='<input id="vcrate" type="range" min="-50" max="50" step="5" value="'+rate+'" style="width:100%" oninput="$(\'vcrl\').textContent=(this.value>=0?\'+\':\'\')+this.value+\'%\'">';
  h+='<div style="font-size:10px;color:#4d8a76;margin-top:4px">Milton (clon) ignora la velocidad. Las voces neurales necesitan internet.</div>';
  h+='<div style="display:flex;gap:8px;margin-top:18px">';
  h+='<button class="btn" style="flex:1" onclick="testVoiceCfg()"><i class="ti ti-player-play"></i> PROBAR</button>';
  h+='<button class="btn" style="flex:1" onclick="saveVoiceCfg()"><i class="ti ti-device-floppy"></i> GUARDAR</button>';
  h+='</div></div>';
  $('modal').innerHTML=h;$('modal').style.display='flex';
 }).catch(function(){});
}
function testVoiceCfg(){var v=$('vcsel').value;var rn=parseInt($('vcrate').value,10)||0;localStorage.setItem('gx_voice',v);localStorage.setItem('gx_rate',rn);speak('Hola, señor. Así sueno con esta voz. Sistemas en línea.');}
function saveVoiceCfg(){var v=$('vcsel').value;var rn=parseInt($('vcrate').value,10)||0;localStorage.setItem('gx_voice',v);localStorage.setItem('gx_rate',rn);
 fetch('/api/voice/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({voice:v,rate:rn})}).then(function(){closeModal();showAnswer('<i class="ti ti-check" style="color:var(--g)"></i> Voz guardada: '+esc($('vcsel').options[$('vcsel').selectedIndex].text));}).catch(function(){closeModal();});}
/* ===== HUB de configuración (engranaje): Voz + Correos + Claves + futuros ===== */
function openSettings(){
 fetch('/api/settings/integrations').then(function(r){return r.json();}).then(function(d){
  var h='<div class="panel" style="width:470px;max-width:94vw;max-height:88vh;overflow-y:auto;padding:20px" onclick="event.stopPropagation()">';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><span style="color:var(--g);font-size:13px;letter-spacing:.12em"><i class="ti ti-settings"></i> CONFIGURACIÓN</span><span onclick="closeModal()" style="cursor:pointer;color:#7fceb3"><i class="ti ti-x"></i></span></div>';
  h+='<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(45,255,174,.12)"><span style="color:#cfeee0;font-size:13px"><i class="ti ti-microphone-2"></i> Voz</span><button class="btn" onclick="openVoiceCfg()">Configurar</button></div>';
  (d.sections||[]).forEach(function(s){h+=renderSection(s);});
  h+='<div style="font-size:10px;color:#4d8a76;margin-top:14px;border-top:1px solid rgba(45,255,174,.12);padding-top:8px">🔒 Las claves se guardan en <b>.env</b> (local, nunca se suben a internet ni al repo). Se muestran enmascaradas; dejá un campo vacío para no cambiarlo.</div>';
  h+='</div>';
  $('modal').innerHTML=h;$('modal').style.display='flex';
 }).catch(function(){});
}
function renderSection(s){
 var soon=s.status==='soon';
 var h='<div style="margin-top:14px;opacity:'+(soon?'.55':'1')+'">';
 h+='<div style="color:var(--g);font-size:12px;letter-spacing:.08em;margin-bottom:3px"><i class="ti '+(s.icon||'')+'"></i> '+esc(s.title)+(soon?' <span style="color:#ffd24d;font-size:10px">· PRÓXIMAMENTE</span>':'')+'</div>';
 if(s.help)h+='<div style="font-size:10px;color:#4d8a76;margin-bottom:6px">'+esc(s.help)+'</div>';
 s.fields.forEach(function(f){
  h+='<div style="font-size:11px;color:#7fceb3;margin:7px 0 2px">'+esc(f.label)+(f.set?' <span style="color:var(--g)">✓</span>':'')+'</div>';
  var isSec=f.type==='secret';
  var val=isSec?'':esc(f.value||'');
  var ph=isSec?(f.set?esc(f.value):esc(f.ph||'')):esc(f.ph||'');
  h+='<input data-env="'+f.env+'" type="'+(isSec?'password':'text')+'"'+(soon?' disabled':'')+' value="'+val+'" placeholder="'+ph+'" style="width:100%;padding:8px;background:#06120e;color:#cfeee0;border:1px solid rgba(45,255,174,.25);border-radius:6px;font-size:12px;box-sizing:border-box">';
 });
 if(!soon)h+='<button class="btn" style="margin-top:9px" onclick="saveSection(this)"><i class="ti ti-device-floppy"></i> GUARDAR</button>';
 h+='</div>';
 return h;
}
function saveSection(btn){
 var box=btn.parentNode;var ins=box.querySelectorAll('input[data-env]');var p={};
 for(var i=0;i<ins.length;i++){var v=(ins[i].value||'').trim();if(v&&v.indexOf('•')<0)p[ins[i].getAttribute('data-env')]=v;}
 if(!Object.keys(p).length){showAnswer('Nada que guardar (los campos vacíos no cambian nada).');closeModal();return;}
 fetch('/api/settings/integrations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(function(r){return r.json();}).then(function(d){
  closeModal();
  if(d.ok)showAnswer('<i class="ti ti-check" style="color:var(--g)"></i> Guardado: '+((d.updated||[]).join(', ')||'sin cambios'));
  else showAnswer('No se pudo guardar: '+esc(d.error||'error'));
 }).catch(function(){closeModal();});}
/* ===== NÚCLEO 3D (WebGL): enana blanca por shader — superficie de ruido procedural,
   corona de filamentos, iluminación de limbo y rotación; reactiva a la voz ===== */
var pAC=null,pAna=null,pFreq=null,pSpeaking=false,pSmooth=0.12;
var POW=document.querySelector('.orbwrap');     // la esfera escala con la voz
var PCV=$('plasma'),GL=null,GPROG=null,GU={};
(function initGL(){
 if(!PCV)return;
 var DPR=Math.min(2,window.devicePixelRatio||1);
 function size(){var d=PCV.clientWidth||270;PCV.width=Math.round(d*DPR);PCV.height=Math.round(d*DPR);if(GL)GL.viewport(0,0,PCV.width,PCV.height);}
 try{GL=PCV.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true})||PCV.getContext('experimental-webgl');}catch(e){GL=null;}
 if(!GL)return;
 var VS='attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}';
 var FS=`precision highp float;uniform vec2 uRes;uniform float uTime;uniform float uAmp;
 float hash(vec3 p){p=fract(p*0.3183099+0.1);p*=17.0;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
 float noise(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.0-2.0*f);
  return mix(mix(mix(hash(i+vec3(0.,0.,0.)),hash(i+vec3(1.,0.,0.)),f.x),mix(hash(i+vec3(0.,1.,0.)),hash(i+vec3(1.,1.,0.)),f.x),f.y),
             mix(mix(hash(i+vec3(0.,0.,1.)),hash(i+vec3(1.,0.,1.)),f.x),mix(hash(i+vec3(0.,1.,1.)),hash(i+vec3(1.,1.,1.)),f.x),f.y),f.z);}
 float fbm(vec3 p){float s=0.0,a=0.55;for(int i=0;i<6;i++){s+=a*noise(p);p=p*2.03;a*=0.5;}return s;}
 mat3 rotY(float a){float c=cos(a),s=sin(a);return mat3(c,0.,s,0.,1.,0.,-s,0.,c);}
 void main(){
  vec2 uv=(gl_FragCoord.xy-0.5*uRes)/(0.5*uRes.y);
  float r=length(uv),t=uTime;
  float nflash=pow(0.5+0.5*sin(t*0.5)*sin(t*0.31+1.3),16.0);   // destello esporádico del núcleo
  float R=0.4*(0.96+uAmp*0.12+nflash*0.05);   // esfera más chica dentro del canvas (deja salir los jets)
  vec3 col=vec3(0.0);float al=0.0;mat3 rot=rotY(t*0.13);
  vec3 bc=vec3(0.16,0.5,0.6);
  if(r<R){
   float zz=sqrt(max(0.0,R*R-dot(uv,uv)));
   vec3 n=normalize(vec3(uv,zz));vec3 sp=rot*n;
   float surf=fbm(sp*3.2+vec3(0.,0.,t*0.16))+0.5*fbm(sp*7.5+vec3(t*0.22,0.,0.));
   float cells=fbm(sp*1.5+vec3(t*0.04,0.,t*0.03));            // celdas de convección
   surf=clamp(surf*0.7+0.16,0.0,1.0);surf*=mix(0.66,1.2,smoothstep(0.33,0.67,cells));surf=clamp(surf,0.0,1.0);
   float limb=pow(clamp(zz/R,0.0,1.0),0.32);
   vec3 cool=vec3(0.015,0.08,0.11),mid=vec3(0.05,0.26,0.34),hot=vec3(0.2,0.52,0.62);
   vec3 sc=mix(cool,mid,smoothstep(0.1,0.55,surf));sc=mix(sc,hot,smoothstep(0.55,0.95,surf));
   col=(sc*(0.4+0.55*surf)*limb+hot*pow(surf,3.0)*0.32)*(1.0+nflash*1.2);al=1.0;}
  float edge=smoothstep(R*2.6,R*0.95,r);float ang=atan(uv.y,uv.x);
  float fil=fbm(vec3(cos(ang)*3.0,sin(ang)*3.0,r*7.0-t*0.55))*0.6+fbm(vec3(ang*5.0,r*4.0,t*0.4))*0.4;
  float corona=pow(edge,1.7)*(0.22+0.7*fil)*(1.0+uAmp*0.5);
  if(r>=R){corona*=smoothstep(R*2.6,R,r);}
  col+=vec3(0.12,0.42,0.52)*corona;al=max(al,clamp(corona*1.1,0.0,0.85));
  // EXPLOSIONES SOLARES: llamaradas brillantes que erupcionan del borde
  for(int k=0;k<4;k++){float fk=float(k);
   float ph=fract(t*0.16+fk*0.27);                              // más rápidas
   float life=smoothstep(0.0,0.07,ph)*smoothstep(0.65,0.22,ph);
   float fang=fk*1.7+t*0.07+sin(fk*4.0)*2.0;
   float adiff=abs(mod(ang-fang+3.14159,6.2832)-3.14159);
   float beam=smoothstep(0.45,0.0,adiff);beam*=beam;            // haz angosto y brillante
   float ext=R*(1.0+life*1.0);                                  // menos alcance
   float prof=smoothstep(ext,R*0.88,r)*step(R*0.9,r);
   float flare=life*beam*prof;
   col+=vec3(0.75,0.95,1.0)*flare*3.0;al=max(al,clamp(flare*1.3,0.0,0.96));}
  // LLAMARADAS ENVOLVENTES: capa de fuego turbulento que rodea el núcleo y gira
  float band=smoothstep(R*1.5,R*0.95,r)*step(R*0.92,r);          // banda justo fuera del borde
  float aa=ang+t*0.35;                                           // rota alrededor (envolvente)
  float fe=fbm(vec3(cos(aa)*4.0,sin(aa)*4.0,r*7.0-t*1.0))*0.6+fbm(vec3(cos(aa*1.8)*6.0-t*0.6,sin(aa*1.8)*6.0,r*4.0))*0.5;
  float env=band*pow(clamp(fe,0.0,1.0),1.7)*(0.7+uAmp*0.7);
  col+=mix(vec3(0.22,0.62,0.85),vec3(0.7,0.95,1.0),env)*env*1.1;al=max(al,clamp(env*0.95,0.0,0.88));
  // ANILLOS ORBITALES 3D de plasma: planos inclinados que GIRAN en todo sentido
  // alrededor del núcleo; la esfera tapa la parte de atrás -> dan vuelta con cuerpo
  float Rs=R;float silh=dot(uv,uv);float frontZ=-sqrt(max(0.0001,Rs*Rs-min(silh,Rs*Rs)));
  for(int k=0;k<3;k++){float fk=float(k);
   float a1=t*(0.3+fk*0.13)+fk*1.3,a2=t*(0.21+fk*0.1)+fk*2.1;
   vec3 nrm=normalize(vec3(sin(a1)*cos(a2),sin(a2),cos(a1)*cos(a2)));   // normal del plano que rota
   if(abs(nrm.z)<0.1){nrm.z=nrm.z<0.0?-0.1:0.1;nrm=normalize(nrm);}
   float zr=-(uv.x*nrm.x+uv.y*nrm.y)/nrm.z;                            // z donde el rayo corta el plano del anillo
   vec3 P=vec3(uv,zr);float d3=length(P);
   float ringR=Rs*(1.06+fk*0.12);   // anillos pegados al núcleo
   float on=smoothstep(0.06,0.0,abs(d3-ringR));                        // cuerpo (tubo) del anillo
   float flow=clamp(fbm(P*5.0+vec3(t*0.6,fk*3.0,0.0)),0.0,1.0);        // plasma que fluye
   on*=(0.45+0.85*flow);
   float fb=clamp(0.5-zr*1.1,0.28,1.15);                              // frente más brillante (profundidad)
   float occl=(silh<Rs*Rs&&zr>frontZ)?0.0:1.0;                        // la esfera tapa el tramo de atrás
   float ri=on*fb*occl*(0.9+uAmp*0.6);
   col+=mix(vec3(0.3,0.7,0.95),vec3(0.92,0.98,1.0),flow)*ri*2.0;al=max(al,clamp(ri,0.0,0.9));}
  // BLOOM atmosférico (capas de glow renderizadas, no CSS) — destella con nflash
  float b1=smoothstep(R*1.5,R*0.2,r),b2=smoothstep(R*3.4,R*0.4,r);
  float bloom=(b1*b1*0.2+b2*b2*0.13)*(1.0+uAmp*0.9+nflash*1.6);
  col+=bc*bloom;al=max(al,clamp(bloom,0.0,0.9));
  // ONDA DE VOZ: anillo que se expande del núcleo al hablar
  float rr=R*(1.14+uAmp*0.55);float ring=smoothstep(0.07,0.0,abs(r-rr))*uAmp;
  col+=vec3(0.45,0.85,1.0)*ring*0.6;al=max(al,ring*0.7);
  col=col/(col+0.7);col=pow(col,vec3(1.05));
  gl_FragColor=vec4(col,clamp(al,0.0,1.0));}`;
 function sh(ty,src){var s=GL.createShader(ty);GL.shaderSource(s,src);GL.compileShader(s);if(!GL.getShaderParameter(s,GL.COMPILE_STATUS))console.warn('GL',GL.getShaderInfoLog(s));return s;}
 GPROG=GL.createProgram();GL.attachShader(GPROG,sh(GL.VERTEX_SHADER,VS));GL.attachShader(GPROG,sh(GL.FRAGMENT_SHADER,FS));GL.linkProgram(GPROG);GL.useProgram(GPROG);
 var buf=GL.createBuffer();GL.bindBuffer(GL.ARRAY_BUFFER,buf);GL.bufferData(GL.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),GL.STATIC_DRAW);
 var loc=GL.getAttribLocation(GPROG,'p');GL.enableVertexAttribArray(loc);GL.vertexAttribPointer(loc,2,GL.FLOAT,false,0,0);
 GU.res=GL.getUniformLocation(GPROG,'uRes');GU.time=GL.getUniformLocation(GPROG,'uTime');GU.amp=GL.getUniformLocation(GPROG,'uAmp');
 GL.enable(GL.BLEND);GL.blendFunc(GL.SRC_ALPHA,GL.ONE_MINUS_SRC_ALPHA);
 size();window.addEventListener('resize',size);
})();
function plasmaLoop(){var amp;
 if(pSpeaking&&pAna){pAna.getByteFrequencyData(pFreq);var s=0;for(var i=2;i<pFreq.length;i++)s+=pFreq[i];amp=Math.min(1,(s/(pFreq.length-2))/90);}
 else{amp=0.16+0.06*Math.sin(performance.now()/620);}
 pSmooth+=(amp-pSmooth)*0.25;
 if(GL&&GPROG){GL.useProgram(GPROG);GL.uniform2f(GU.res,PCV.width,PCV.height);GL.uniform1f(GU.time,performance.now()/1000);GL.uniform1f(GU.amp,pSmooth);GL.clearColor(0,0,0,0);GL.clear(GL.COLOR_BUFFER_BIT);GL.drawArrays(GL.TRIANGLES,0,3);}
 if(POW){var _sc=1+Math.max(0,pSmooth-0.15)*0.7;POW.style.transform='scale('+_sc.toFixed(3)+')';}
 requestAnimationFrame(plasmaLoop);}
function plasmaSpeak(audio){try{pAC=pAC||new(window.AudioContext||window.webkitAudioContext)();if(pAC.state==='suspended')pAC.resume();
  var src=pAC.createMediaElementSource(audio);pAna=pAC.createAnalyser();pAna.fftSize=64;pAna.smoothingTimeConstant=0.7;
  src.connect(pAna);pAna.connect(pAC.destination);pFreq=new Uint8Array(pAna.frequencyBinCount);
 }catch(e){pAna=null;}pSpeaking=true;}
function plasmaCalm(){pSpeaking=false;pAna=null;}
if(GL){plasmaLoop();}
function renderCards(q,cards){
 $('boardstatus').textContent=cards.length+' evidencias';
 if(!cards.length){$('board').style.display='flex';$('board').innerHTML='Sin evidencias para «'+esc(q)+'».';return;}
 $('board').style.display='block';$('board').style.alignItems='stretch';
 var html='<div style="font-size:11px;color:#4d8a76;margin-bottom:8px">Investigación: <b style="color:var(--g)">'+esc(q)+'</b></div><div style="display:grid;gap:8px">';
 html+=cards.map(function(c){var host='';try{host=new URL(c.url).hostname.replace('www.','');}catch(e){}return '<div class="card"><div style="color:var(--g);font-size:12px;font-weight:500">'+esc(c.title||'(sin título)')+'</div><div style="color:#9fceb3;font-size:11px;margin:4px 0">'+esc(c.snippet||'')+'</div><a href="'+esc(c.url)+'" style="font-size:10px;color:#4d8a76"><i class="ti ti-link"></i> '+esc(host)+'</a></div>';}).join('');
 html+='</div>';$('board').innerHTML=html;
}
function doResearch(q){
 setState('proc');$('boardstatus').textContent='investigando…';
 $('board').style.display='flex';$('board').innerHTML='<span style="color:var(--g)">⟳ investigando «'+esc(q)+'»…</span>';
 fetch('/api/research?q='+encodeURIComponent(q)).then(r=>r.json()).then(function(d){
  renderCards(d.query||q,d.cards||[]);setState('calm');
  speak(d.cards&&d.cards.length?('Encontré '+d.cards.length+' evidencias sobre '+q):('No encontré evidencias sobre '+q));
 }).catch(function(){$('board').innerHTML='Error en la investigación.';setState('calm');});
}
function showAnswer(html){$('answer').style.display='block';$('answer').innerHTML=html;$('answer').scrollTop=0;}
function send(){
 var m=$('msg').value.trim();if(!m)return;$('msg').value='';
 if(/^(investig|busc|research|averigu)/i.test(m)){var q=m.replace(/^(investig\w*|busc\w*|research|averigu\w*)\s+(sobre\s+|el\s+|la\s+|los\s+|las\s+)?/i,'').trim()||m;doResearch(q);return;}
 setState('proc');showAnswer('<span style="color:#4d8a76">› '+esc(m)+'</span>');
 fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})}).then(r=>r.json()).then(function(d){var t=d.response||d.error||'(sin respuesta)';
  if(t.indexOf('[[STOP]]')>=0){t=t.replace('[[STOP]]','').trim();cstop();}
  if(t.indexOf('[[PAUSE]]')>=0){t=t.replace('[[PAUSE]]','').trim();try{$('cap').pause();}catch(e){}}
  if(t.indexOf('[[RESUME]]')>=0){t=t.replace('[[RESUME]]','').trim();try{$('cap').play();}catch(e){}}
  var pm=t.match(/\[\[PLAY:([\w-]+)\]\]/);
  if(pm){t=t.replace(/\[\[PLAY:[\w-]+\]\]/,'').trim();cplay(pm[1],t.split('\n')[0].slice(0,55));}
  var vm=t.match(/\[\[VOICE:([\w:-]+)\]\]/);if(vm){t=t.replace(/\[\[VOICE:[\w:-]+\]\]/,'').trim();localStorage.setItem('gx_voice',vm[1]);}
  var doReload=t.indexOf('[[RELOAD]]')>=0;if(doReload)t=t.replace('[[RELOAD]]','').trim();
  t=t.replace('[[ULTRON]]','').trim();
  showAnswer(md(t));setState('calm');speak(t.replace(/```[\s\S]*?```/g,' código en pantalla ').replace(/[`*#>]/g,'').slice(0,500));
  if(doReload)setTimeout(function(){location.reload();},2600);}).catch(function(){showAnswer('[error de conexión]');setState('calm');});
}
function cplay(vid,label){var a=$('cap');a.onerror=function(){$('cnow').innerHTML='<i class="ti ti-alert-triangle" style="color:#ffd24d"></i> No pude bajar el audio: YouTube pide verificación anti-bot. Hay que configurar cookies (decime «configurar cookies»).';};a.src='/api/audio/'+vid;$('cnow').innerHTML='<i class="ti ti-music"></i> '+(label||'reproduciendo');$('cplayer').style.display='block';a.play().catch(function(){});}
function cstop(){var a=$('cap');try{a.pause();}catch(e){}a.src='';$('cplayer').style.display='none';}
function toggleCam(){var r=$('camrow');if(r.textContent.indexOf('APAGADA')>=0){r.innerHTML='<i class="ti ti-camera"></i> CÁMARA · ENCENDIDA';r.style.color='var(--g)';}else{r.innerHTML='<i class="ti ti-camera-off"></i> CÁMARA · APAGADA';r.style.color='#5a7a70';}}
var micActive=false,micCtx=null,micProc=null,micStream=null,micBufs=[];
function toggleMic(){micActive?micStop():micStart();}
async function micStart(){try{micStream=await navigator.mediaDevices.getUserMedia({audio:{sampleRate:16000,channelCount:1,echoCancellation:true,noiseSuppression:true}});micActive=true;micBufs=[];$('micbtn').style.background='var(--g)';$('micbtn').style.color='#03070a';setState('listen');micCtx=new(window.AudioContext||window.webkitAudioContext)({sampleRate:16000});var src=micCtx.createMediaStreamSource(micStream);micProc=micCtx.createScriptProcessor(4096,1,1);micProc.onaudioprocess=function(e){if(!micActive)return;var f=e.inputBuffer.getChannelData(0);var a=new Int16Array(f.length);for(var i=0;i<f.length;i++)a[i]=Math.max(-32768,Math.min(32767,Math.floor(f[i]*32768)));micBufs.push(a);};src.connect(micProc);micProc.connect(micCtx.destination);setTimeout(function(){if(micActive)micStop();},15000);}catch(e){micActive=false;$('micbtn').style.background='';$('micbtn').style.color='var(--g)';setState('calm');}}
function micStop(){if(!micActive)return;micActive=false;$('micbtn').style.background='';$('micbtn').style.color='var(--g)';setState('proc');var sr=(micCtx&&micCtx.sampleRate)?Math.round(micCtx.sampleRate):16000;if(micProc){micProc.disconnect();micProc=null;}if(micCtx){micCtx.close();micCtx=null;}if(micStream){micStream.getTracks().forEach(function(t){t.stop();});micStream=null;}var total=micBufs.reduce(function(s,b){return s+b.length;},0);if(!total){setState('calm');return;}var peak=1;for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++){var a=Math.abs(b[i]);if(a>peak)peak=a;}}var gain=Math.min(30,Math.max(1,10000/peak));if(gain>1){for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++)b[i]=Math.max(-32768,Math.min(32767,Math.round(b[i]*gain)));}}var buf=new ArrayBuffer(44+total*2),v=new DataView(buf);function ws(o,s){for(var i=0;i<s.length;i++)v.setUint8(o+i,s.charCodeAt(i));}ws(0,'RIFF');v.setUint32(4,36+total*2,true);ws(8,'WAVE');ws(12,'fmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,sr,true);v.setUint32(28,sr*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);ws(36,'data');v.setUint32(40,total*2,true);var off=44;for(var k=0;k<micBufs.length;k++){var b=micBufs[k];for(var i=0;i<b.length;i++){v.setInt16(off,b[i],true);off+=2;}}var fd=new FormData();fd.append('audio',new Blob([buf],{type:'audio/wav'}),'rec.wav');fetch('/api/stt',{method:'POST',body:fd}).then(r=>r.json()).then(function(d){var txt=(d.text||'').trim();setState('calm');if(txt){$('msg').value=txt;send();}}).catch(function(){setState('calm');});}
/* ===== DOCK + MODALES (todo desbloqueado en el local) ===== */
var DOCK={
 buscar:{ic:'ti-search',t:'BUSCAR E INVESTIGAR',d:'Investigo cualquier dato y te traigo las fuentes al tablero.',items:[
  {l:'Investigá el precio del dólar',c:'investigá el precio del dólar'},
  {l:'Buscá tutoriales de Arduino',c:'investigá tutoriales de Arduino'},
  {l:'Qué pasó hoy en tecnología',c:'investigá qué pasó hoy en tecnología'}]},
 webs:{ic:'ti-world',t:'ABRIR SITIOS WEB',d:'Indicame el sitio y lo abro al instante.',items:[
  {l:'Abrí YouTube',c:'abrí youtube'},{l:'Abrí Gmail',c:'abrí gmail'},{l:'Abrí Wikipedia',c:'abrí wikipedia'}]},
 musica:{ic:'ti-music',t:'MÚSICA',d:'Reproduzco lo que quieras en YouTube Music.',items:[
  {l:'Reproducí Bon Jovi',c:'reproducí bon jovi'},{l:'Poné música de los 80',c:'reproducí música de los 80'},{l:'Reproducí Coldplay',c:'reproducí coldplay'}]},
 crear:{ic:'ti-palette',t:'CREAR IMÁGENES',d:'Describime la imagen y la genero.',items:[
  {l:'Generá un dragón de fuego',c:'generá una imagen de un dragón de fuego'},{l:'Un atardecer en la playa',c:'generá una imagen de un atardecer en la playa'},{l:'Un robot futurista',c:'generá una imagen de un robot futurista'}]},
 ver:{ic:'ti-eye',t:'VER · CÁMARA Y PANTALLA',d:'Puedo ver tu pantalla o tu cámara.',items:[
  {l:'Encendé la cámara',c:'__cam__'},{l:'Qué hay en mi pantalla',c:'qué ves en mi pantalla'}]}
};
function openDock(k){var d=DOCK[k];if(!d)return;
 var h='<div class="mdlbox panel" onclick="event.stopPropagation()"><div style="display:flex;justify-content:space-between;align-items:center"><span style="color:var(--g);letter-spacing:.14em"><i class="ti '+d.ic+'"></i> '+d.t+'</span><span onclick="closeModal()" style="cursor:pointer;color:#7fceb3"><i class="ti ti-x"></i></span></div><div style="font-size:12px;color:#7fceb3;margin:8px 0 2px">'+d.d+'</div>';
 for(var i=0;i<d.items.length;i++){h+='<div class="mitem" onclick="dockRun(\''+k+'\','+i+')"><i class="ti ti-player-play" style="color:var(--g);margin-right:7px"></i>'+d.items[i].l+'</div>';}
 h+='</div>';$('modal').innerHTML=h;$('modal').style.display='flex';}
function closeModal(){$('modal').style.display='none';$('modal').innerHTML='';}
function dockRun(k,i){var c=DOCK[k].items[i].c;closeModal();if(c==='__cam__'){toggleCam();return;}$('msg').value=c;send();}
function nucleo(){showAnswer('Modo núcleo activado, señor. A su servicio.');speak('Modo núcleo activado, señor. A su servicio.');}
/* barra de stats arriba a la derecha */
function pollStats(){fetch('/api/system').then(r=>r.json()).then(function(d){var s=$('stats');if(s)s.textContent='GPU '+Math.round(d.gpu_percent||0)+'% · CPU '+Math.round(d.cpu_percent||0)+'%';}).catch(function(){});}
// --- Feed de voz (manos libres): mostrar en la cabina lo que pedís por voz ---
var _vseq=0,_vinit=false;
function pollVoice(){fetch('/api/voice/feed?since='+_vseq).then(function(r){return r.json();}).then(function(d){
 if(d.seq===undefined)return;
 if(!_vinit){_vinit=true;_vseq=Math.max(0,d.seq-1);} // al cargar, mostrar solo el último
 (d.events||[]).forEach(function(e){_vseq=e.seq;
  var t=(e.response||'').replace(/\[\[[^\]]*\]\]/g,'').trim();
  setState('proc');
  showAnswer('<div style="color:#4d8a76;margin-bottom:6px"><i class="ti ti-microphone"></i> '+esc(e.request)+'</div>'+md(t));
  setTimeout(function(){setState('calm');},700);
 });
 if(d.seq>_vseq)_vseq=d.seq;
}).catch(function(){});}
setInterval(pollStats,3000);pollStats();pollVoice();setInterval(pollVoice,1500);
// --- Starfield de fondo (estilo nave) ---
/* ===== CAMPO DE ESTRELLAS 3D (WebGL GL_POINTS): miles de puntos con glow real,
   profundidad/parallax, rotación diferencial alrededor del núcleo, reactivo a la voz ===== */
(function(){var sc=$('stars');if(!sc)return;
 var N=24000,DPR=Math.min(2,window.devicePixelRatio||1);
 var gl=null,prog=null,U={},W=0,H=0,cx=0,cy=0,maxR=0;
 try{gl=sc.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true})||sc.getContext('experimental-webgl');}catch(e){gl=null;}
 if(!gl)return;
 var VS='attribute vec2 aPolar;attribute vec3 aData;attribute float aCyan;'
  +'uniform vec2 uCenter;uniform vec2 uScale;uniform float uTime;uniform float uAmp;uniform float uMaxR;uniform float uPS;'
  +'varying float vB;varying float vC;'
  +'void main(){float depth=aData.x;'
  +'float ang=aPolar.x+uTime*(0.02+depth*0.05);'                   // GIRAN alrededor del núcleo (diferencial); nunca vuelven
  +'float rad=aPolar.y*uMaxR*(1.0+uAmp*0.16*(0.4+depth));'         // radio fijo (+ leve push con la voz)
  +'vec2 off=vec2(cos(ang)*uScale.x,sin(ang)*uScale.y)*rad;'
  +'gl_Position=vec4(uCenter+off,0.0,1.0);'
  +'float tw=0.6+0.4*sin(uTime*1.4+aData.z);'
  +'float fl=pow(0.5+0.5*sin(uTime*0.55+aData.z*5.0),42.0);'       // destello esporádico por estrella
  +'vB=aData.y*tw*(0.55+0.45*depth)*(1.0+uAmp*1.6)+fl*2.2;vC=aCyan;'
  +'gl_PointSize=(0.45+depth*1.1+fl*2.2)*uPS*(1.0+uAmp*0.7);}';    // puntos más chicos
 var FS='precision mediump float;varying float vB;varying float vC;'
  +'void main(){vec2 d=gl_PointCoord-0.5;float r=length(d);'
  +'float c=smoothstep(0.5,0.0,r);float a=(0.35*c+0.65*c*c)*vB*1.5;'
  +'vec3 col=mix(vec3(0.85,0.91,1.0),vec3(0.18,0.82,1.0),vC);'
  +'gl_FragColor=vec4(col,clamp(a,0.0,1.0));}';
 function sh(ty,s){var o=gl.createShader(ty);gl.shaderSource(o,s);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))console.warn('stars',gl.getShaderInfoLog(o));return o;}
 prog=gl.createProgram();gl.attachShader(prog,sh(gl.VERTEX_SHADER,VS));gl.attachShader(prog,sh(gl.FRAGMENT_SHADER,FS));gl.linkProgram(prog);gl.useProgram(prog);
 var data=new Float32Array(N*6);
 for(var i=0;i<N;i++){var o=i*6;
  data[o]=Math.random()*6.2832;data[o+1]=Math.random();  // ang, fase del flujo de salida (0..1)
  data[o+2]=Math.random();data[o+3]=0.2+Math.random()*0.8;              // depth, brillo
  data[o+4]=Math.random()*6.2832;data[o+5]=Math.random()<0.34?1.0:0.0;} // fase, cian
 var buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
 var FB=4,ST=6*FB,aP=gl.getAttribLocation(prog,'aPolar'),aD=gl.getAttribLocation(prog,'aData'),aC=gl.getAttribLocation(prog,'aCyan');
 gl.enableVertexAttribArray(aP);gl.vertexAttribPointer(aP,2,gl.FLOAT,false,ST,0);
 gl.enableVertexAttribArray(aD);gl.vertexAttribPointer(aD,3,gl.FLOAT,false,ST,2*FB);
 gl.enableVertexAttribArray(aC);gl.vertexAttribPointer(aC,1,gl.FLOAT,false,ST,5*FB);
 U.center=gl.getUniformLocation(prog,'uCenter');U.scale=gl.getUniformLocation(prog,'uScale');U.time=gl.getUniformLocation(prog,'uTime');U.amp=gl.getUniformLocation(prog,'uAmp');U.maxr=gl.getUniformLocation(prog,'uMaxR');U.ps=gl.getUniformLocation(prog,'uPS');
 gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);   // aditivo = glow
 function recompute(){W=sc.clientWidth||300;H=sc.clientHeight||300;sc.width=Math.round(W*DPR);sc.height=Math.round(H*DPR);gl.viewport(0,0,sc.width,sc.height);
  var sr=sc.getBoundingClientRect(),ob=document.querySelector('.orbwrap');
  if(ob){var r=ob.getBoundingClientRect();cx=r.left+r.width/2-sr.left;cy=r.top+r.height/2-sr.top;}else{cx=W/2;cy=H*0.32;}
  maxR=Math.min(W,H)*1.3;}     // radio del halo (puntos más alejados del núcleo)
 function frame(){if(!gl)return;
  var va=(typeof pSmooth!=='undefined'&&pSmooth>0.15)?(pSmooth-0.15)*1.5:0;if(va>1)va=1;
  gl.useProgram(prog);
  gl.uniform2f(U.center,cx/W*2.0-1.0,1.0-cy/H*2.0);gl.uniform2f(U.scale,H/W,1.0);
  gl.uniform1f(U.time,performance.now()/1000);gl.uniform1f(U.amp,va);gl.uniform1f(U.maxr,maxR*2.0/H);gl.uniform1f(U.ps,DPR);
  gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.POINTS,0,N);
  requestAnimationFrame(frame);}
 setTimeout(function(){recompute();frame();},120);window.addEventListener('resize',recompute);})();
// --- Onboarding (primera vez) ---
function closeTip(){var t=$('tip');if(t)t.style.display='none';try{localStorage.setItem('gx_seen_tip','1');}catch(e){}}
function openTip(){var t=$('tip');if(t)t.style.display='block';}
try{if(!localStorage.getItem('gx_seen_tip'))setTimeout(openTip,1200);}catch(e){}
// --- Accesibilidad: controles de ícono operables por teclado + etiquetas ARIA ---
document.querySelectorAll('.dockbtn,.corner,#micbtn,#tip .x').forEach(function(el){
 if(!el.getAttribute('role'))el.setAttribute('role','button');
 if(!el.hasAttribute('tabindex'))el.setAttribute('tabindex','0');
 if(!el.getAttribute('aria-label')){var s=el.querySelector('span');var lbl=(s?s.textContent:(el.getAttribute('title')||el.textContent||'')).trim();if(lbl)el.setAttribute('aria-label',lbl);}
 el.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();el.click();}});
});
</script></body></html>"""


@app.route("/core")
def core_ui():
    """Interfaz JARVIS CORE — Tablero de Evidencias (recreación)."""
    return _brand(_CORE_HTML)


_PLASMALAB_HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GENESIS // Plasma Lab</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#03060b;color:#cfeee0;font-family:ui-monospace,Consolas,monospace;padding:20px}
h1{font-size:17px;color:#2dffae;letter-spacing:.14em;font-weight:500;text-align:center}
.sub{text-align:center;color:#6aa78f;font-size:13px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px;max-width:1100px;margin:0 auto}
.card{background:#05100d;border:1px solid rgba(45,255,174,.22);border-radius:14px;padding:14px;text-align:center}
.card canvas{width:160px;height:160px}
.nm{color:#dff5ea;font-size:14px;margin:10px 0 2px}
.ds{color:#6aa78f;font-size:12px;line-height:1.45;min-height:34px}
.bt{margin-top:8px;background:rgba(45,255,174,.1);color:#bfeada;border:1px solid rgba(45,255,174,.5);border-radius:8px;padding:7px 10px;font-size:12px;cursor:pointer;width:100%}
.bt:hover{background:rgba(45,255,174,.2)}
</style></head><body>
<h1>GENESIS · PLASMA LAB</h1>
<div class="sub">6 diseños del núcleo (voz simulada). Decile a Genesis: «aplicá el diseño N».</div>
<div class="grid">
 <div class="card"><canvas id="pl1" width="320" height="320"></canvas><div class="nm">1 · Plasma actual</div><div class="ds">Metaball + chispas + borde de luz</div><button class="bt" onclick="pick(1)">Aplicar 1</button></div>
 <div class="card"><canvas id="pl2" width="320" height="320"></canvas><div class="nm">2 · Onda Siri</div><div class="ds">Cintas sinusoidales en capas</div><button class="bt" onclick="pick(2)">Aplicar 2</button></div>
 <div class="card"><canvas id="pl3" width="320" height="320"></canvas><div class="nm">3 · Espectro radial</div><div class="ds">Barras de frecuencia girando</div><button class="bt" onclick="pick(3)">Aplicar 3</button></div>
 <div class="card"><canvas id="pl4" width="320" height="320"></canvas><div class="nm">4 · Nebulosa</div><div class="ds">Esfera de partículas 3D</div><button class="bt" onclick="pick(4)">Aplicar 4</button></div>
 <div class="card"><canvas id="pl5" width="320" height="320"></canvas><div class="nm">5 · Blob líquido</div><div class="ds">Gradiente que se deforma</div><button class="bt" onclick="pick(5)">Aplicar 5</button></div>
 <div class="card"><canvas id="pl6" width="320" height="320"></canvas><div class="nm">6 · Malla wireframe</div><div class="ds">Globo de alambre rotando</div><button class="bt" onclick="pick(6)">Aplicar 6</button></div>
</div>
<script>
function pick(n){var names={1:'plasma actual',2:'onda Siri',3:'espectro radial',4:'nebulosa de particulas',5:'blob liquido',6:'malla wireframe'};
 try{localStorage.setItem('gx_plasma_choice',n);}catch(e){}
 alert('Diseno '+n+' ('+names[n]+') elegido.\\nDecile a Genesis: «aplica el diseño '+n+'».');}
var CT={};for(var i=1;i<=6;i++){var c=document.getElementById('pl'+i);if(c){var x=c.getContext('2d');x.scale(2,2);CT[i]=x;}}
var PC=80;
function clipc(x){x.save();x.beginPath();x.arc(PC,PC,76,0,6.2832);x.clip();}
function sph(n){var p=[],off=2/n,inc=Math.PI*(3-Math.sqrt(5));for(var i=0;i<n;i++){var y=i*off-1+off/2,r=Math.sqrt(1-y*y),ph=i*inc;p.push([Math.cos(ph)*r,y,Math.sin(ph)*r]);}return p;}
var NEB=sph(150),WIRE=sph(46);
function rot(p,a){var s=Math.sin(a),c=Math.cos(a);return [p[0]*c-p[2]*s,p[1],p[0]*s+p[2]*c];}
function d1(x,t,amp){x.clearRect(0,0,160,160);x.globalCompositeOperation='lighter';var sw=t*0.35;var col=['45,255,174','40,230,205','120,255,215','60,255,185','30,225,255'];
 for(var i=0;i<6;i++){var a=t*(.5+i*.13)+i;var bx=Math.cos(a*1.3)*(16+amp*40),by=Math.sin(a*1.1)*(16+amp*40);var px=PC+bx*Math.cos(sw)-by*Math.sin(sw),py=PC+bx*Math.sin(sw)+by*Math.cos(sw);var r=(40+i*4)*(0.66+amp);var g=x.createRadialGradient(px,py,0,px,py,r);g.addColorStop(0,'rgba('+col[i%5]+','+(0.28+amp*0.45)+')');g.addColorStop(.45,'rgba('+col[i%5]+','+(0.1+amp*0.15)+')');g.addColorStop(1,'rgba('+col[i%5]+',0)');x.fillStyle=g;x.beginPath();x.arc(px,py,r,0,6.2832);x.fill();}
 for(var s=0;s<8;s++){var sa=t*(s%2?1:-1)*0.8+s;var rr=(30+s*5)*(0.8+amp*0.6);var sx=PC+Math.cos(sa)*rr,sy=PC+Math.sin(sa)*rr;var sg=x.createRadialGradient(sx,sy,0,sx,sy,3);sg.addColorStop(0,'rgba(215,255,240,'+(0.5+amp*0.4)+')');sg.addColorStop(1,'rgba(120,255,215,0)');x.fillStyle=sg;x.beginPath();x.arc(sx,sy,3,0,6.2832);x.fill();}
 x.globalCompositeOperation='destination-in';var m=x.createRadialGradient(PC,PC,16,PC,PC,78);m.addColorStop(0,'#fff');m.addColorStop(.82,'#fff');m.addColorStop(1,'rgba(255,255,255,0)');x.fillStyle=m;x.fillRect(0,0,160,160);x.globalCompositeOperation='source-over';}
function d2(x,t,amp){x.clearRect(0,0,160,160);clipc(x);var cols=['rgba(45,255,174,.55)','rgba(60,200,255,.5)','rgba(160,255,220,.45)'];
 for(var k=0;k<3;k++){x.beginPath();x.moveTo(0,PC);for(var px=0;px<=160;px+=4){var env=Math.sin(px/160*Math.PI);var y=PC+Math.sin(px/22+t*(2+k)+k*2)*(6+amp*46)*env*(1-k*0.22);x.lineTo(px,y);}x.lineWidth=2.4;x.strokeStyle=cols[k];x.stroke();}
 x.restore();}
function d3(x,t,amp){x.clearRect(0,0,160,160);var N=52;for(var i=0;i<N;i++){var ang=i/N*6.2832+t*0.3;var v=(0.5+0.5*Math.sin(t*4+i*0.7));var ln=8+v*(10+amp*46);var r0=30,r1=r0+ln;var sx=PC+Math.cos(ang)*r0,sy=PC+Math.sin(ang)*r0,ex=PC+Math.cos(ang)*r1,ey=PC+Math.sin(ang)*r1;x.strokeStyle='rgba('+(45+v*80)+',255,'+(174+v*60)+','+(0.5+amp*0.4)+')';x.lineWidth=2.2;x.beginPath();x.moveTo(sx,sy);x.lineTo(ex,ey);x.stroke();}
 var cg=x.createRadialGradient(PC,PC,0,PC,PC,26);cg.addColorStop(0,'rgba(180,255,225,'+(0.5+amp*0.4)+')');cg.addColorStop(1,'rgba(45,255,174,0)');x.fillStyle=cg;x.beginPath();x.arc(PC,PC,26,0,6.2832);x.fill();}
function d4(x,t,amp){x.clearRect(0,0,160,160);x.globalCompositeOperation='lighter';var a=t*0.5;var sc=54*(0.9+amp*0.3);for(var i=0;i<NEB.length;i++){var p=rot(NEB[i],a);var z=(p[2]+1)/2;var px=PC+p[0]*sc,py=PC+p[1]*sc;var sz=0.6+z*2.0;x.fillStyle='rgba('+(45+z*120)+',255,'+(190+z*40)+','+(0.15+z*0.6)+')';x.beginPath();x.arc(px,py,sz,0,6.2832);x.fill();}x.globalCompositeOperation='source-over';}
function d5(x,t,amp){x.clearRect(0,0,160,160);x.beginPath();var N=48;for(var i=0;i<=N;i++){var ang=i/N*6.2832;var rr=46+amp*16+Math.sin(ang*3+t*1.2)*6+Math.sin(ang*5-t*0.8)*4;var px=PC+Math.cos(ang)*rr,py=PC+Math.sin(ang)*rr;if(i===0)x.moveTo(px,py);else x.lineTo(px,py);}x.closePath();var g=x.createRadialGradient(PC-10,PC-10,4,PC,PC,68);g.addColorStop(0,'rgba(200,255,235,'+(0.85)+')');g.addColorStop(.5,'rgba(60,230,200,.7)');g.addColorStop(1,'rgba(30,150,170,.45)');x.fillStyle=g;x.fill();}
function d6(x,t,amp){x.clearRect(0,0,160,160);var a=t*0.4;var sc=58*(0.92+amp*0.25);var pts=[];for(var i=0;i<WIRE.length;i++){var p=rot(WIRE[i],a);pts.push([PC+p[0]*sc,PC+p[1]*sc,(p[2]+1)/2]);}
 for(var i=0;i<pts.length;i++){for(var j=i+1;j<pts.length;j++){var dx=pts[i][0]-pts[j][0],dy=pts[i][1]-pts[j][1];var d=dx*dx+dy*dy;if(d<460){x.strokeStyle='rgba(45,255,174,'+(0.06+amp*0.12)*(pts[i][2])+')';x.lineWidth=0.6;x.beginPath();x.moveTo(pts[i][0],pts[i][1]);x.lineTo(pts[j][0],pts[j][1]);x.stroke();}}}
 for(var i=0;i<pts.length;i++){var z=pts[i][2];x.fillStyle='rgba('+(60+z*120)+',255,'+(190+z*40)+','+(0.25+z*0.6)+')';x.beginPath();x.arc(pts[i][0],pts[i][1],0.8+z*1.6,0,6.2832);x.fill();}}
var FN={1:d1,2:d2,3:d3,4:d4,5:d5,6:d6},t0=null;
function loop(ts){if(t0===null)t0=ts;var t=(ts-t0)/1000;var amp=0.22+0.2*Math.abs(Math.sin(t*0.9))+0.05*Math.sin(t*3.2);for(var i=1;i<=6;i++){if(CT[i])FN[i](CT[i],t,amp);}requestAnimationFrame(loop);}
requestAnimationFrame(loop);
</script></body></html>"""


@app.route("/plasma-lab")
def plasma_lab():
    """Laboratorio de diseños del núcleo de plasma (preview para elegir)."""
    return _brand(_PLASMALAB_HTML)


_MISSION_HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS · MISSION CONTROL</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.7.0/dist/tabler-icons.min.css">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:ui-monospace,'Cascadia Code',Consolas,monospace;background:#04070b;color:#9fb4c4;font-size:12px;-webkit-font-smoothing:antialiased}
#mc{--g:#2dffae;--w:#ffd24d;--r:#ff5d5d;min-height:100vh;padding:14px;background:radial-gradient(120% 60% at 50% -10%,rgba(45,255,174,.06),transparent 55%),repeating-linear-gradient(rgba(120,160,180,.03) 0 1px,transparent 1px 38px),#04070b}
.pan{border:1px solid rgba(45,255,174,.16);border-radius:9px;background:rgba(8,16,22,.6);padding:12px}
.h{font-size:10px;letter-spacing:.16em;color:#5a7d8c;margin-bottom:10px}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block}
@keyframes blink{0%,100%{opacity:.4}50%{opacity:1}}
.tab{cursor:pointer;padding:6px 11px;border-radius:6px;font-size:11px;letter-spacing:.06em;color:#5a7d8c}
.tab.on{color:var(--g);background:rgba(45,255,174,.1);border:1px solid rgba(45,255,174,.3)}
.bar{height:5px;background:rgba(120,160,180,.1);border-radius:3px;overflow:hidden}.bar>i{display:block;height:5px;background:var(--g);box-shadow:0 0 6px var(--g)}
.flt{cursor:pointer;font-size:9px;padding:3px 7px;border-radius:5px;color:#5a7d8c;border:1px solid rgba(120,160,180,.15)}
.flt.on{color:var(--g);border-color:rgba(45,255,174,.4)}
a{color:var(--g);text-decoration:none}
::-webkit-scrollbar{width:7px}::-webkit-scrollbar-thumb{background:rgba(45,255,174,.2);border-radius:4px}
</style></head><body><div id="mc">

<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(45,255,174,.14);padding-bottom:10px">
 <div style="display:flex;align-items:center;gap:12px">
  <span style="color:var(--g);letter-spacing:.2em;font-size:15px;font-weight:600">⛯ JARVIS</span>
  <span style="font-size:10px;color:#5a7d8c">MISSION CONTROL — Vista Táctica</span>
 </div>
 <div style="display:flex;align-items:center;gap:8px">
  <span class="tab on">Vista Táctica</span>
  <span class="tab" onclick="location.href='/core'">JARVIS Core</span>
  <span class="tab" onclick="location.href='/jarvis'">Cabina</span>
  <span id="utc" style="font-size:10px;color:#5a7d8c;margin-left:8px">--:--:-- UTC</span>
 </div>
</div>

<div style="display:grid;grid-template-columns:230px 1fr 240px;gap:12px;margin-top:12px">

 <div class="pan">
  <div class="h">MÓDULOS DEL SISTEMA</div>
  <div id="modules"></div>
 </div>

 <div style="display:flex;flex-direction:column;gap:12px">
  <div class="pan" style="text-align:center;padding:18px">
   <div style="font-size:10px;color:#5a7d8c;letter-spacing:.2em">CLASE OMEGA · ACCESO RAÍZ</div>
   <div id="gen" style="color:var(--g);font-size:34px;font-weight:600;margin:6px 0;text-shadow:0 0 16px rgba(45,255,174,.5)">GEN —</div>
   <div style="font-size:11px;color:#7fa3b4">JARVIS CORE · <span id="coreok" style="color:var(--g)">ESTADO ÓPTIMO</span></div>
   <div id="ident" style="font-size:10px;color:#5a7d8c;margin-top:6px">—</div>
  </div>
  <div class="pan" style="flex:1">
   <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span class="h" style="margin:0">BITÁCORA DEL SISTEMA</span>
    <div style="display:flex;gap:4px"><span class="flt on" data-f="ALL" onclick="setFlt('ALL')">TODOS</span><span class="flt" data-f="CORE" onclick="setFlt('CORE')">CORE</span><span class="flt" data-f="SYS" onclick="setFlt('SYS')">SYS</span><span class="flt" data-f="ALERTA" onclick="setFlt('ALERTA')">ALERTA</span></div>
   </div>
   <div id="log" style="display:flex;flex-direction:column;gap:5px;max-height:230px;overflow-y:auto;font-size:11px"></div>
  </div>
 </div>

 <div style="display:flex;flex-direction:column;gap:12px">
  <div class="pan">
   <div class="h">TELEMETRÍA</div>
   <div id="tel"></div>
  </div>
  <div class="pan">
   <div class="h">AGENTES COLABORATIVOS</div>
   <div id="agents"></div>
  </div>
 </div>
</div>
<div class="pan" style="margin-top:12px">
 <div class="h">ESTRUCTURA MULTI-AGENTE <span id="agcount" style="color:#5a7d8c;font-weight:400;font-size:9px"></span></div>
 <div id="agentstruct" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:10px;margin-top:4px"></div>
</div>
</div>
<script>
function $(i){return document.getElementById(i)}
function clk(){var d=new Date();$('utc').textContent=d.toISOString().substr(11,8)+' UTC';}
clk();setInterval(clk,1000);
var MODS=[['JARVIS Core','core'],['Memoria','mem'],['Evolución','evo'],['Visión · llava','vis'],['Voz · vosk/edge','voz'],['Loop Autónomo','auto'],['Builder · qwen','build'],['Red / Web','net']];
function tel(l,val,unit){return '<div style="margin-bottom:9px"><div style="display:flex;justify-content:space-between;font-size:10px;color:#7fa3b4;margin-bottom:3px"><span>'+l+'</span><span>'+val+(unit||'')+'</span></div><div class="bar"><i style="width:'+Math.min(100,val)+'%"></i></div></div>';}
function agColor(en){return en?'var(--g)':'#5a7d8c';}
function renderAgents(d){var ags=d.agents||[];var c=$('agcount');if(c)c.textContent='· '+(d.active||0)+'/'+(d.total||0)+' activos';
 $('agents').innerHTML=ags.map(function(a){var col=agColor(a.enabled);return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(120,160,180,.07)"><span class="dot" style="background:'+col+';box-shadow:0 0 6px '+col+'"></span><div style="flex:1"><div style="color:#aebfcb;font-size:11px">'+a.name+'</div><div style="font-size:9px;color:#5a7d8c">'+a.role+'</div></div><span style="font-size:9px;color:#5a7d8c">'+a.tasks_completed+'t</span></div>';}).join('');
 $('agentstruct').innerHTML=ags.map(function(a){var on=a.enabled;var col=agColor(on);
  var caps=(a.capabilities||[]).map(function(x){return '<span style="display:inline-block;background:rgba(45,255,174,.08);border:1px solid rgba(45,255,174,.2);border-radius:4px;padding:1px 6px;margin:2px 2px 0 0;font-size:9px;color:#9fe9c9">'+x+'</span>';}).join('');
  return '<div style="border:1px solid rgba(45,255,174,'+(on?'.25':'.1')+');border-radius:8px;padding:10px;background:rgba(7,18,16,.5)">'
   +'<div style="display:flex;justify-content:space-between;align-items:center"><span style="color:'+col+';font-size:13px;font-weight:600">'+a.name+'</span>'
   +'<span onclick="agToggle(\''+a.name+'\')" title="activar/desactivar" style="cursor:pointer;font-size:8px;letter-spacing:.1em;border:1px solid '+col+';border-radius:4px;padding:2px 6px;color:'+col+'">'+(on?'ON':'OFF')+'</span></div>'
   +'<div style="font-size:10px;color:#7fa3b4;margin:2px 0 6px">'+a.role+'</div><div style="margin-bottom:6px">'+caps+'</div>'
   +'<div style="display:flex;flex-wrap:wrap;gap:8px;font-size:9px;color:#5a7d8c;border-top:1px solid rgba(120,160,180,.08);padding-top:6px"><span>🌡 temp '+a.temperature+'</span><span>⬆ prioridad '+a.priority+'</span><span>✓ '+a.tasks_completed+' tareas</span><span>⏱ '+a.avg_time+'s</span></div></div>';}).join('');}
function pollAgents(){fetch('/api/agents').then(function(r){return r.json();}).then(renderAgents).catch(function(){});}
function agToggle(name){fetch('/api/agents/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name})}).then(function(r){return r.json();}).then(function(){pollAgents();}).catch(function(){});}
function renderStatic(){
 $('modules').innerHTML=MODS.map(function(m){return '<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid rgba(120,160,180,.07)"><span class="dot" style="background:var(--g);box-shadow:0 0 6px var(--g);animation:blink 3s infinite"></span><span style="color:#aebfcb;font-size:11px">'+m[0]+'</span><span style="margin-left:auto;font-size:9px;color:#5a7d8c">ONLINE</span></div>';}).join('');
}
renderStatic();
function pollSys(){fetch('/api/system').then(r=>r.json()).then(function(d){
 $('tel').innerHTML=tel('CPU',Math.round(d.cpu_percent||0),'%')+tel('RAM',Math.round(d.ram_percent||0),'%')+tel('GPU',Math.round(d.gpu_percent||0),'%')+tel('VRAM',Math.round((d.vram_used_mb||0)/(d.vram_total_mb||1)*100),'%')+'<div style="font-size:9px;color:#5a7d8c;margin-top:6px">GPU '+(d.gpu_temp_c||'?')+'°C · señal nominal · −82 dB</div>';
 var crit=(d.ram_percent>92)||(d.cpu_percent>90);
 $('coreok').textContent=crit?'CARGA CRÍTICA':'ESTADO ÓPTIMO';$('coreok').style.color=crit?'var(--r)':'var(--g)';
}).catch(function(){});}
var allLog=[];
function pollHud(){fetch('/api/hud').then(r=>r.json()).then(function(d){
 $('gen').textContent='GEN '+(d.generation||0);
 $('ident').textContent='Genesis v'+(d.version||'6')+' · '+(d.memories||0)+' memorias · '+(d.curiosity||0)+' en cola';
 allLog=(d.activity||[]).map(function(a){var act=(a.action||'');var cat=/INVESTIG|HALLAZGO|CICLO|DESPERTAR/.test(act)?'CORE':(/BG_TASK|CONSTRUCTOR|persist|schedul/.test(act)?'SYS':(/ERROR|SKIP|BLOQ/.test(act)?'ALERTA':'CORE'));return {act:act,det:a.detail||'',cat:cat};});
 drawLog();
}).catch(function(){});}
var flt='ALL';
function setFlt(f){flt=f;document.querySelectorAll('.flt').forEach(function(e){e.classList.toggle('on',e.dataset.f===f);});drawLog();}
function drawLog(){var rows=allLog.filter(function(x){return flt==='ALL'||x.cat===flt;});if(!rows.length){$('log').innerHTML='<div style="color:#3f5b6a">sin eventos</div>';return;}var col={CORE:'var(--g)',SYS:'#7fa3b4',ALERTA:'#ff5d5d'};$('log').innerHTML=rows.map(function(x){return '<div style="display:flex;gap:8px;border-left:2px solid '+(col[x.cat]||'#5a7d8c')+';padding:3px 8px;background:rgba(120,160,180,.03)"><span style="color:'+(col[x.cat]||'#5a7d8c')+';font-size:9px;min-width:46px">'+x.cat+'</span><span style="color:#9fb4c4;font-size:10px">'+(x.act+' '+x.det).slice(0,60)+'</span></div>';}).join('');}
pollSys();pollHud();pollAgents();setInterval(pollSys,4000);setInterval(pollHud,5000);setInterval(pollAgents,6000);
</script></body></html>"""


@app.route("/api/agents")
def api_agents():
    """Estructura real de los agentes (sistema multi-agente)."""
    try:
        agsys = get_genesis().agent_system
        agents = [a.to_dict() for a in agsys.agents.values()]
        agents.sort(key=lambda a: (-a.get("priority", 0), a.get("name", "")))
        return jsonify({"agents": agents, "total": len(agents),
                        "active": sum(1 for a in agents if a.get("enabled"))})
    except Exception as e:
        return jsonify({"agents": [], "total": 0, "active": 0, "error": str(e)[:120]})


@app.route("/api/agents/toggle", methods=["POST"])
def api_agents_toggle():
    """Activa/desactiva un agente por nombre."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip().lower()
    try:
        msg = get_genesis().agent_system.toggle_agent(name)
        return jsonify({"ok": True, "msg": msg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)[:120]}), 400


@app.route("/mission")
def mission_ui():
    """JARVIS Mission Control — Vista Táctica (recreación, datos reales)."""
    return _brand(_MISSION_HTML)


_audio_url_cache = {}  # vid -> (stream_url, ts) — googlevideo URLs duran horas


@app.route("/api/audio/<vid>")
def api_audio(vid):
    """PROXY del audio del video (reproducción in-app robusta).

    En vez de redirigir al navegador a googlevideo (que falla por CORS/headers
    en WebView2), el server descarga el stream y lo reenvía. El navegador solo
    habla con localhost → mismo origen, soporta Range/seek. Cachea la URL
    resuelta para no llamar a yt-dlp en cada request de rango.
    """
    import urllib.request
    try:
        from core.music_player import get_audio_url
        cached = _audio_url_cache.get(vid)
        if cached and (time.time() - cached[1]) < 3600:
            url = cached[0]
        else:
            url = get_audio_url(vid)
            if url:
                _audio_url_cache[vid] = (url, time.time())
        if not url:
            return jsonify({"error": "no se pudo resolver el audio"}), 404

        req_headers = {"User-Agent": "Mozilla/5.0"}
        rng = request.headers.get("Range")
        if rng:
            req_headers["Range"] = rng
        upstream = urllib.request.urlopen(
            urllib.request.Request(url, headers=req_headers), timeout=25)

        def _stream():
            try:
                while True:
                    chunk = upstream.read(65536)
                    if not chunk:
                        break
                    yield chunk
            finally:
                try:
                    upstream.close()
                except Exception:
                    pass

        resp_headers = {
            "Content-Type": upstream.headers.get("Content-Type", "audio/mp4"),
            "Accept-Ranges": "bytes",
        }
        for h in ("Content-Length", "Content-Range"):
            v = upstream.headers.get(h)
            if v:
                resp_headers[h] = v
        return Response(_stream(), status=upstream.status, headers=resp_headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/research")
def api_research():
    """Investigación web → tarjetas de evidencia (para el Tablero de Evidencias)."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"query": "", "cards": []})
    cards = []
    try:
        from core.web_intelligence import WebSearcher
        ws = WebSearcher()
        results = ws.search(q, max_results=6)
        for r in results:
            d = r.to_dict() if hasattr(r, "to_dict") else {}
            cards.append({
                "title": d.get("title", "")[:120],
                "url": d.get("url", ""),
                "snippet": d.get("snippet", "")[:280],
            })
    except Exception as e:
        return jsonify({"query": q, "cards": [], "error": str(e)})
    return jsonify({"query": q, "cards": cards})


@app.route("/api/monitor")
def api_monitor():
    """Devuelve las últimas peticiones + respuestas (monitoreo en vivo)."""
    try:
        n = int(request.args.get("n", 25))
    except Exception:
        n = 25
    recientes = _interactions_buffer[-n:][::-1]  # más nuevas primero
    return jsonify({
        "total": len(_interactions_buffer),
        "interactions": recientes,
    })


@app.route("/api/voice/feed")
def api_voice_feed():
    """Interacciones por voz (manos libres) para mostrarlas en la cabina.
    La UI hace polling con ?since=<seq> y recibe solo lo nuevo."""
    try:
        since = int(request.args.get("since", 0))
    except Exception:
        since = 0
    try:
        from core import handsfree
        return jsonify(handsfree.get_feed(since))
    except Exception:
        return jsonify({"seq": 0, "events": []})


@app.route("/api/settings/integrations", methods=["GET", "POST"])
def api_settings_integrations():
    """Configuración de integraciones (correos, claves API, futuros canales).
    GET → estado enmascarado + schema; POST → guarda en .env (sin loguear)."""
    from core import integrations_config as ic
    if request.method == "POST":
        return jsonify(ic.set_config(request.get_json(silent=True) or {}))
    return jsonify(ic.get_config())


@app.route("/api/voice/config", methods=["GET", "POST"])
def api_voice_config():
    """Configuración de voz (voz + velocidad), compartida cabina/manos-libres."""
    from core import voice_config
    if request.method == "POST":
        d = request.get_json() or {}
        cfg = voice_config.set(voice=d.get("voice"), rate=d.get("rate"))
        return jsonify({"ok": True, "config": cfg})
    return jsonify({"config": voice_config.get(), "voices": voice_config.all_voices()})


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
            analysis = g.image_analyzer.analyze(tmp.name, prompt=message)
            if isinstance(analysis, dict):
                response = analysis.get("description", "(sin descripción)")
            else:
                response = str(analysis)
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

    # === VOZ PIPER (TTS local, offline) — voice="piper:<nombre>" ===
    if voice.startswith("piper:"):
        try:
            from flask import Response
            from core import piper_tts as _pp
            _name = voice.split(":", 1)[1]
            _wav = _pp.synth_bytes(clean, _name)
            return Response(_wav, mimetype="audio/wav")
        except Exception:
            voice = "es-ES-AlvaroNeural"  # fallback edge si Piper falla

    # === VOZ CLONADA (XTTS local) — voice="clon:<nombre>" ===
    if voice.startswith("clon:"):
        try:
            import os as _os
            import tempfile as _tf
            from core import voice_clone as _vc
            _name = voice.split(":", 1)[1].strip() or "milton"
            _ref = _vc.ref_for(_name)
            _out = _os.path.join(_tf.gettempdir(),
                                 f"gx_clon_{_name}_{abs(hash(clean)) % 1000000}.wav")
            _r = _vc.clone_say_hq(clean, str(_ref), _out, temperature=0.5)
            if _r.get("ok") and _os.path.exists(_out):
                from flask import send_file
                return send_file(_out, mimetype="audio/wav", download_name="tts.wav")
            raise RuntimeError("xtts no disponible")
        except Exception:
            # XTTS falló/OOM → FALLBACK UNIFICADO a Piper (misma voz en cabina y
            # manos-libres; local, no usa VRAM, nunca queda mudo ni cambia)
            try:
                from flask import Response
                from core import piper_tts as _pp
                return Response(_pp.synth_bytes(clean, "es_ES-davefx-medium"),
                                mimetype="audio/wav")
            except Exception:
                voice = "es-ES-AlvaroNeural"  # último recurso si Piper falla

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
                    prompt="Describe detalladamente todo lo que aparece en esta imagen: "
                           "elementos, ventanas, textos, colores y disposición."
                )
                if isinstance(analysis, dict):
                    response_data["analysis"] = analysis.get("description", "(sin descripción)")
                else:
                    response_data["analysis"] = str(analysis)
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
