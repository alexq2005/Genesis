"""Cámara de celular → GENESIS (100% local, sin app).

El celular abre `https://<ip-lan>:5443/movil?t=<token>` (se escanea por QR desde la
cabina), concede la cámara y sube frames JPEG a GENESIS por la red local. GENESIS
guarda el último frame y lo puede ver/analizar (llava).

Por qué HTTPS: los navegadores SOLO dan `getUserMedia` (cámara) en contexto seguro
(HTTPS o localhost). Como el cel entra por IP de LAN, servimos por HTTPS con un
certificado AUTOFIRMADO (se genera solo con `cryptography`). La 1ª vez el cel avisa
"sitio no seguro" → avanzar igual. El video NUNCA sale de la red local.
"""
import os
import io
import time
import socket
import secrets
import threading

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CERT_DIR = os.path.join(_BASE, "data", "certs")
PORT = 5443

# Estado compartido (lo leen tanto este server HTTPS como la cabina en :5100)
_LATEST = {"jpeg": None, "ts": 0.0, "w": 0, "h": 0}
_TOKEN = secrets.token_urlsafe(8)
_LOCK = threading.Lock()
_SERVER_UP = False
_MON = {"on": False, "interval": 10}   # modo monitoreo (auto-análisis periódico)


def token():
    return _TOKEN


def lan_ip():
    """IP de la PC en la red local (la que ve el celular)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def pair_url():
    return f"https://{lan_ip()}:{PORT}/movil?t={_TOKEN}"


def set_frame(jpeg_bytes, w=0, h=0):
    with _LOCK:
        _LATEST["jpeg"] = jpeg_bytes
        _LATEST["ts"] = time.time()
        if w:
            _LATEST["w"] = w
        if h:
            _LATEST["h"] = h


def get_frame():
    with _LOCK:
        return _LATEST["jpeg"], _LATEST["ts"]


def status():
    with _LOCK:
        ts = _LATEST["ts"]
        connected = bool(_LATEST["jpeg"]) and (time.time() - ts) < 6
        return {"connected": connected, "ts": round(ts, 0),
                "has_frame": bool(_LATEST["jpeg"]),
                "w": _LATEST["w"], "h": _LATEST["h"], "server_up": _SERVER_UP,
                "monitor": _MON["on"]}


def save_photo():
    """Guarda el último frame del celular como JPEG en el escritorio. Devuelve la ruta o None."""
    import datetime
    j, ts = get_frame()
    if not j or (time.time() - ts) > 8:
        return None
    cap = os.path.join(os.path.expanduser("~"), "Desktop", "GENESIS Capturas")
    os.makedirs(cap, exist_ok=True)
    fn = os.path.join(cap, "movil_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg")
    with open(fn, "wb") as f:
        f.write(j)
    return fn


def monitor_on():
    return _MON["on"]


def start_monitor(interval=10):
    """Arranca el modo monitoreo: cada `interval`s analiza el frame con llava y
    avisa por el feed de la cabina solo cuando la descripción cambia."""
    if _MON["on"]:
        return False
    _MON["on"] = True
    _MON["interval"] = max(5, int(interval))

    def _loop():
        import tempfile
        last = ""
        # da margen a que llegue el primer frame fresco
        while _MON["on"]:
            try:
                j, ts = get_frame()
                if j and (time.time() - ts) < 8:
                    p = os.path.join(tempfile.gettempdir(), "gx_movil_mon.jpg")
                    with open(p, "wb") as f:
                        f.write(j)
                    from core.image_analyzer import ImageAnalyzer
                    r = ImageAnalyzer().analyze(
                        p, prompt="Esta es la cámara del celular del usuario. En UNA frase corta, decí qué se ve ahora.")
                    d = (r.get("description") if isinstance(r, dict) else str(r)) or ""
                    d = d.strip()
                    if d and d != last:
                        last = d
                        try:
                            from core import handsfree
                            handsfree.push_feed("[monitor cámara cel]", "📱👁️ " + d)
                        except Exception:
                            pass
            except Exception:
                pass
            # dormir en pasos cortos para responder rápido al stop
            for _ in range(int(_MON["interval"] * 2)):
                if not _MON["on"]:
                    break
                time.sleep(0.5)

    threading.Thread(target=_loop, daemon=True).start()
    return True


def stop_monitor():
    was = _MON["on"]
    _MON["on"] = False
    return was


def ensure_cert():
    """Genera (si no existe) un certificado autofirmado para HTTPS. Devuelve (crt, key)."""
    os.makedirs(_CERT_DIR, exist_ok=True)
    crt = os.path.join(_CERT_DIR, "mobilecam.crt")
    key = os.path.join(_CERT_DIR, "mobilecam.key")
    if os.path.exists(crt) and os.path.exists(key):
        return crt, key
    import datetime
    import ipaddress
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    pk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ip = lan_ip()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "GENESIS Mobile Cam")])
    san = [x509.DNSName("localhost")]
    try:
        san.append(x509.IPAddress(ipaddress.ip_address(ip)))
    except Exception:
        pass
    now = datetime.datetime.utcnow()
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(pk.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san), critical=False)
            .sign(pk, hashes.SHA256()))
    with open(key, "wb") as f:
        f.write(pk.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()))
    with open(crt, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return crt, key


_MOVIL_HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>GENESIS · Cámara</title>
<style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#050a12;color:#cfe6f6;
 font-family:system-ui,'Segoe UI',sans-serif;overflow:hidden}
#wrap{position:fixed;inset:0;display:flex;flex-direction:column}
#vid{flex:1;width:100%;object-fit:cover;background:#000}
.bar{display:flex;align-items:center;gap:10px;padding:12px 16px;background:#06101c;border-bottom:1px solid rgba(70,217,255,.2)}
.dot{width:9px;height:9px;border-radius:50%;background:#ff5d5d;box-shadow:0 0 8px #ff5d5d}
.dot.on{background:#3ad88a;box-shadow:0 0 8px #3ad88a}
.ctr{display:flex;gap:10px;padding:14px 16px;background:#06101c;border-top:1px solid rgba(70,217,255,.2)}
button{flex:1;font-family:inherit;font-size:15px;padding:14px;border-radius:12px;border:1px solid rgba(70,217,255,.4);
 background:rgba(70,217,255,.1);color:#46d9ff;font-weight:600}
button:active{background:rgba(70,217,255,.25)}
#msg{font-size:12px;color:#7099b6}
</style></head><body>
<div id="wrap">
 <div class="bar"><span id="dot" class="dot"></span><b style="color:#46d9ff">GENESIS</b>
  <span id="msg" style="margin-left:auto">Iniciando cámara…</span></div>
 <video id="vid" autoplay playsinline muted></video>
 <div class="ctr"><button id="flip">↻ Cambiar cámara</button><button id="toggle">⏸ Pausar</button></div>
</div>
<script>
var q=new URLSearchParams(location.search),tok=q.get('t')||'';
var vid=document.getElementById('vid'),msg=document.getElementById('msg'),dot=document.getElementById('dot');
var stream=null,back=true,sending=true,timer=null;
var cv=document.createElement('canvas'),cx=cv.getContext('2d');
async function start(){
 if(stream){stream.getTracks().forEach(function(t){t.stop();});}
 try{
  stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:back?'environment':'user',width:{ideal:1280},height:{ideal:720}},audio:false});
  vid.srcObject=stream;msg.textContent='Transmitiendo a GENESIS';dot.className='dot on';
 }catch(e){msg.textContent='Sin permiso de cámara. Tocá el candado y permití la cámara.';dot.className='dot';}
}
function loop(){
 if(sending&&vid.videoWidth){
  cv.width=Math.min(960,vid.videoWidth);cv.height=cv.width*vid.videoHeight/vid.videoWidth;
  cx.drawImage(vid,0,0,cv.width,cv.height);
  cv.toBlob(function(b){if(b)fetch('/api/movil/frame?t='+encodeURIComponent(tok),{method:'POST',body:b}).catch(function(){});},'image/jpeg',0.55);
 }
 timer=setTimeout(loop,700);
}
document.getElementById('flip').onclick=function(){back=!back;start();};
document.getElementById('toggle').onclick=function(){sending=!sending;this.textContent=sending?'⏸ Pausar':'▶ Reanudar';msg.textContent=sending?'Transmitiendo a GENESIS':'En pausa';dot.className=sending?'dot on':'dot';};
start();loop();
</script></body></html>"""


def start_https_server():
    """Levanta el server HTTPS (puerto 5443) en un hilo. Sirve /movil y recibe frames."""
    global _SERVER_UP
    if _SERVER_UP:
        return
    try:
        from flask import Flask, request, Response
        crt, key = ensure_cert()
        app = Flask("genesis_mobilecam")
        app.logger.disabled = True

        @app.route("/movil")
        def _movil():
            return Response(_MOVIL_HTML, mimetype="text/html")

        @app.route("/api/movil/frame", methods=["POST"])
        def _frame():
            if request.args.get("t", "") != _TOKEN:
                return ("forbidden", 403)
            data = request.get_data()
            if data and len(data) > 200:
                set_frame(data)
            return ("ok", 200)

        @app.route("/api/movil/latest")
        def _latest():
            j, _ = get_frame()
            if not j:
                return ("no frame", 404)
            return Response(j, mimetype="image/jpeg")

        def _run():
            try:
                app.run(host="0.0.0.0", port=PORT, ssl_context=(crt, key),
                        threaded=True, debug=False, use_reloader=False)
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()
        _SERVER_UP = True
        return True
    except Exception:
        return False
