"""
GENESIS Desktop App — Tipo Copilot
Ventana nativa lateral (sidebar) con hotkey global, system tray, barra custom y UX pulida.

Usa PyWebView (WebView2/Edge) — NO abre Chrome/Firefox.

Uso:
    python genesis_desktop.py           -> Sidebar derecha (default)
    python genesis_desktop.py --center  -> Ventana centrada
    python genesis_desktop.py --left    -> Sidebar izquierda

Hotkey: Ctrl+Shift+G  -> Toggle Genesis
"""
import sys
import os
import threading
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)


# ============================================================
# WEBVIEW2 PERMISSION PATCH — Habilitar microfono/camara
# ============================================================
def _patch_webview2_permissions():
    """
    Monkey-patch pywebview's WebView2 backend to auto-grant microphone
    and camera permissions. Without this, getUserMedia() and
    SpeechRecognition are silently denied in WebView2.
    """
    try:
        from webview.platforms import edgechromium
        _original_on_ready = edgechromium.EdgeChrome.on_webview_ready

        def _patched_on_webview_ready(self, sender, args):
            # Ejecutar el original primero
            _original_on_ready(self, sender, args)
            if not args.IsSuccess:
                return
            # Agregar handler de permisos para mic/cam
            try:
                from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState

                def _on_permission_requested(s, perm_args):
                    # Auto-grant microphone, camera y notifications
                    perm_args.State = CoreWebView2PermissionState.Allow

                sender.CoreWebView2.PermissionRequested += _on_permission_requested
                print("  [OK] WebView2: permisos de microfono/camara habilitados")
            except Exception as e:
                print(f"  [WARN] WebView2 permissions: {e}")

        edgechromium.EdgeChrome.on_webview_ready = _patched_on_webview_ready
    except Exception as e:
        print(f"  [WARN] No se pudo parchear WebView2 permisos: {e}")

# Aplicar patch al importar
_patch_webview2_permissions()

# ============================================================
# CONFIGURACION
# ============================================================
APP_TITLE = "Genesis AI"
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5100
SIDEBAR_WIDTH = 580
HOTKEY = "ctrl+shift+g"
STARTUP_TIMEOUT = 20
WINDOW_MODE = "right"

# ============================================================
# SPLASH HTML (se muestra mientras Flask arranca)
# ============================================================
SPLASH_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: linear-gradient(135deg, #0a0e1a 0%, #111827 50%, #0f172a 100%);
    height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    font-family: 'Segoe UI', system-ui, sans-serif;
    color: #e2e8f0; overflow: hidden;
  }
  .logo {
    width: 80px; height: 80px; border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 40px; font-weight: 700; color: white;
    box-shadow: 0 0 40px rgba(59,130,246,0.4);
    animation: pulse 2s ease-in-out infinite;
  }
  @keyframes pulse {
    0%,100% { box-shadow: 0 0 40px rgba(59,130,246,0.3); transform: scale(1); }
    50% { box-shadow: 0 0 60px rgba(139,92,246,0.5); transform: scale(1.05); }
  }
  .title { margin-top: 24px; font-size: 22px; font-weight: 600;
    background: linear-gradient(90deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .status { margin-top: 12px; font-size: 13px; color: #64748b; }
  .dots::after { content: ''; animation: dots 1.5s steps(4,end) infinite; }
  @keyframes dots {
    0% { content: ''; } 25% { content: '.'; } 50% { content: '..'; } 75% { content: '...'; }
  }
  .bar { margin-top: 32px; width: 200px; height: 3px; background: #1e293b;
    border-radius: 3px; overflow: hidden;
  }
  .bar-fill { height: 100%; width: 30%; border-radius: 3px;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    animation: loading 1.5s ease-in-out infinite;
  }
  @keyframes loading {
    0% { transform: translateX(-100%); } 100% { transform: translateX(400%); }
  }
</style></head><body>
  <div class="logo">G</div>
  <div class="title">Genesis AI</div>
  <div class="status">Iniciando motor<span class="dots"></span></div>
  <div class="bar"><div class="bar-fill"></div></div>
</body></html>
"""

# ============================================================
# CSS/JS inyectado en la UI para barra custom + UX
# ============================================================
INJECTED_CSS = """
/* =============================================
   GENESIS DESKTOP — SIDEBAR MODE CSS
   Adapta la UI full-screen al formato sidebar
   ============================================= */

/* --- BARRA DE TITULO CUSTOM --- */
#genesis-titlebar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 99999;
  height: 36px; display: flex; align-items: center;
  background: #0a0e1a;
  border-bottom: 1px solid rgba(59,130,246,0.25);
  -webkit-app-region: drag;
  user-select: none; padding: 0 10px;
}
#genesis-titlebar .tb-logo {
  width: 20px; height: 20px; border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: white; margin-right: 8px;
  flex-shrink: 0;
}
#genesis-titlebar .tb-title {
  font-size: 12px; font-weight: 600; color: #94a3b8;
  font-family: 'Segoe UI', system-ui, sans-serif;
  flex: 1; white-space: nowrap; overflow: hidden;
}
#genesis-titlebar .tb-provider {
  font-size: 9px; color: #60a5fa; margin-left: 4px;
  background: rgba(59,130,246,0.12); padding: 2px 6px;
  border-radius: 8px; border: 1px solid rgba(59,130,246,0.2);
  font-weight: 600; letter-spacing: 0.5px;
}
#genesis-titlebar .tb-buttons {
  display: flex; gap: 1px; margin-left: 6px;
  -webkit-app-region: no-drag;
}
#genesis-titlebar .tb-btn {
  width: 26px; height: 26px; border: none; background: transparent;
  color: #64748b; font-size: 13px; cursor: pointer;
  border-radius: 5px; display: flex; align-items: center;
  justify-content: center; transition: all 0.15s;
}
#genesis-titlebar .tb-btn:hover { background: rgba(255,255,255,0.08); color: #e2e8f0; }
#genesis-titlebar .tb-btn.close:hover { background: #ef4444; color: white; }

/* --- LAYOUT GLOBAL SIDEBAR --- */
body { padding-top: 36px !important; margin: 0 !important; }
html {
  border-left: 1px solid rgba(59,130,246,0.2);
  box-shadow: -6px 0 24px rgba(0,0,0,0.5);
}

/* --- HEADER: compacto para sidebar --- */
.header {
  position: sticky !important; top: 0 !important;
  padding: 6px 10px !important; min-height: auto !important;
  flex-wrap: wrap !important; gap: 4px !important;
  z-index: 9998 !important;
}
.header h1 { font-size: 16px !important; }
.header h1 .sub { display: none !important; } /* Ocultar subtitle largo */
.header-left { gap: 6px !important; }
.header-logo { gap: 2px !important; }
.arc-reactor { width: 28px !important; height: 28px !important; }
.version { font-size: 9px !important; }

/* Botones del header: compactos en 2 filas */
.header-actions {
  display: flex !important; flex-wrap: wrap !important;
  gap: 3px !important; justify-content: flex-end !important;
}
.header-btn {
  padding: 3px 6px !important; font-size: 9px !important;
  min-width: auto !important;
}

/* --- TAB BAR: compacta --- */
.tab-bar { padding: 2px 8px !important; gap: 4px !important; }
.chat-tab { padding: 3px 10px !important; font-size: 10px !important; }
.tab-add { width: 22px !important; height: 22px !important; font-size: 14px !important; }

/* --- CHAT: maximizar espacio --- */
.chat-container {
  padding: 8px !important; gap: 8px !important;
  font-size: 13px !important;
  transition: margin-right 0.3s ease !important;
}
/* Cuando el sidebar esta abierto, el chat se reduce */
.sidebar.open ~ .overlay ~ .chat-container,
body:has(.sidebar.open) .chat-container {
  margin-right: 240px !important;
}
.message {
  padding: 10px 12px !important; font-size: 13px !important;
  border-radius: 10px !important; max-width: 100% !important;
  word-break: break-word !important;
  user-select: text !important; -webkit-user-select: text !important;
  cursor: text !important; position: relative !important;
}
.message code { font-size: 11px !important; user-select: text !important; }
.message pre { font-size: 11px !important; padding: 8px !important; overflow-x: auto !important; user-select: text !important; }
.chat-container { user-select: text !important; -webkit-user-select: text !important; }
/* Boton copiar en cada mensaje */
.copy-msg-btn {
  position: absolute !important; top: 4px !important; right: 4px !important;
  background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.15) !important;
  color: #94a3b8 !important; cursor: pointer !important; border-radius: 4px !important;
  padding: 2px 6px !important; font-size: 11px !important; opacity: 0 !important;
  transition: opacity 0.2s !important; z-index: 10 !important;
}
.message:hover .copy-msg-btn { opacity: 1 !important; }
.copy-msg-btn:hover { background: rgba(59,130,246,0.3) !important; color: #e2e8f0 !important; }
.copy-msg-btn.copied { background: rgba(34,197,94,0.3) !important; color: #4ade80 !important; }

/* --- INPUT: accesible y visible, siempre encima del sidebar --- */
.input-container {
  padding: 8px !important; gap: 6px !important;
  position: relative !important;
  z-index: 200 !important;
  background: var(--bg-primary, #0a0e1a) !important;
}
#userInput {
  font-size: 13px !important; padding: 10px 12px !important;
  min-height: 38px !important; border-radius: 10px !important;
}
#sendBtn {
  padding: 8px 12px !important; font-size: 11px !important;
  border-radius: 8px !important;
}
.mic-btn, .upload-btn {
  width: 32px !important; height: 32px !important;
  font-size: 16px !important;
}

/* --- STATUS BAR: compacta --- */
.status-bar {
  padding: 3px 10px !important; font-size: 10px !important;
}

/* --- SIDEBAR (Command Panel): ajustado para desktop --- */
.sidebar {
  width: 240px !important; max-width: 240px !important;
  padding: 10px !important;
  box-sizing: border-box !important;
  bottom: 70px !important;
  height: auto !important;
  top: 155px !important;
  overflow-y: auto !important;
}
.sidebar h3 {
  font-size: 0.75em !important;
  margin-bottom: 10px !important;
}
.sidebar .cmd {
  white-space: normal !important;
  word-break: break-word !important;
  padding: 5px 6px !important;
  font-size: 0.75em !important;
  line-height: 1.4 !important;
}
.sidebar .cmd code {
  font-size: 0.9em !important;
}
.sidebar .cmd-section-title {
  font-size: 0.6em !important;
}

/* --- SCROLLBAR estilizada --- */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* --- ANALYTICS PANEL: compacto --- */
.analytics-panel { font-size: 11px !important; right: 0 !important; width: 100% !important; }

/* --- VOICE SELECTOR: full width --- */
.voice-selector-panel { width: 100% !important; right: 0 !important; }

/* --- THINKING INDICATOR: centrado --- */
.thinking-indicator { font-size: 11px !important; }

/* --- SMOOTH transitions --- */
* { scroll-behavior: smooth; }
.message, .header-btn, #sendBtn { transition: all 0.15s ease !important; }
"""

INJECTED_JS = """
(function() {
  // No inyectar si ya existe
  if (document.getElementById('genesis-titlebar')) return;

  // Crear barra
  const bar = document.createElement('div');
  bar.id = 'genesis-titlebar';
  bar.innerHTML = `
    <div class="tb-logo">G</div>
    <span class="tb-title">Genesis AI</span>
    <span class="tb-provider" id="tb-provider-badge">LOCAL</span>
    <div class="tb-buttons">
      <button class="tb-btn home" id="tb-home" title="Volver a Genesis (inicio)">⌂</button>
      <button class="tb-btn pin" id="tb-pin" title="Siempre encima">📌</button>
      <button class="tb-btn minimize" id="tb-minimize" title="Minimizar">─</button>
      <button class="tb-btn maximize" id="tb-maximize" title="Maximizar / Pantalla completa">□</button>
      <button class="tb-btn close" id="tb-close" title="Cerrar">✕</button>
    </div>
  `;

  // Inyectar CSS
  const style = document.createElement('style');
  style.textContent = `""" + INJECTED_CSS.replace('`', '\\`').replace('\n', ' ') + """`;
  document.head.appendChild(style);
  document.body.prepend(bar);

  // Botones
  let pinned = true;
  document.getElementById('tb-pin').addEventListener('click', function() {
    pinned = !pinned;
    this.style.opacity = pinned ? '1' : '0.4';
    this.title = pinned ? 'Siempre encima (ON)' : 'Siempre encima (OFF)';
    // Comunicar a pywebview via API
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.toggle_pin(pinned);
    }
  });

  // Home: vuelve a la cabina aunque estemos atrapados en una página externa
  // (ej: clickeaste un resultado de investigación y querés volver).
  document.getElementById('tb-home').addEventListener('click', function() {
    window.location.href = 'http://127.0.0.1:""" + str(FLASK_PORT) + """/core';
  });

  document.getElementById('tb-minimize').addEventListener('click', function() {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.minimize_window();
    }
  });

  let maximized = false;
  document.getElementById('tb-maximize').addEventListener('click', function() {
    if (window.pywebview && window.pywebview.api) {
      var p = window.pywebview.api.toggle_maximize();
      Promise.resolve(p).then(function(isMax) {
        maximized = !!isMax;
        // ❐ = restaurar (cuando está maximizado), □ = maximizar
        document.getElementById('tb-maximize').textContent = maximized ? '❐' : '□';
        document.getElementById('tb-maximize').title = maximized
          ? 'Restaurar tamaño' : 'Maximizar';
      });
    }
  });

  // Pantalla completa REAL (inmersiva): F11 entra/sale, Esc sale.
  let fullscreen = false;
  document.addEventListener('keydown', function(e) {
    if (!window.pywebview || !window.pywebview.api) return;
    if (e.key === 'F11') {
      e.preventDefault();
      window.pywebview.api.toggle_fullscreen();
      fullscreen = !fullscreen;
    } else if (e.key === 'Escape' && fullscreen) {
      window.pywebview.api.toggle_fullscreen();
      fullscreen = false;
    }
  });

  document.getElementById('tb-close').addEventListener('click', function() {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.hide_to_tray();
    }
  });

  // Detectar provider (buscar en la pagina)
  setTimeout(() => {
    const badge = document.getElementById('tb-provider-badge');
    fetch('/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message: 'que modelo eres'})
    }).then(r => r.json()).then(data => {
      const resp = (data.response || '').toLowerCase();
      if (resp.includes('gemini')) badge.textContent = 'GEMINI';
      else if (resp.includes('ollama')) badge.textContent = 'OLLAMA';
      else if (resp.includes('openai') || resp.includes('gpt')) badge.textContent = 'GPT';
      else if (resp.includes('claude') || resp.includes('anthropic')) badge.textContent = 'CLAUDE';
      else badge.textContent = 'LOCAL';
    }).catch(() => { badge.textContent = 'LOCAL'; });
  }, 2000);

  // --- Boton COPIAR en cada mensaje ---
  function addCopyButtons() {
    document.querySelectorAll('.message:not([data-copy-added])').forEach(msg => {
      msg.setAttribute('data-copy-added', '1');
      const btn = document.createElement('button');
      btn.className = 'copy-msg-btn';
      btn.textContent = '📋';
      btn.title = 'Copiar mensaje';
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const text = msg.innerText.replace('📋', '').trim();
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = '✓';
          btn.classList.add('copied');
          setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 1500);
        }).catch(() => {
          // Fallback para WebView2
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.cssText = 'position:fixed;left:-9999px';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          btn.textContent = '✓';
          btn.classList.add('copied');
          setTimeout(() => { btn.textContent = '📋'; btn.classList.remove('copied'); }, 1500);
        });
      });
      msg.appendChild(btn);
    });
  }
  // Observar nuevos mensajes y agregar boton
  const obs = new MutationObserver(addCopyButtons);
  const chatEl = document.getElementById('chatContainer');
  if (chatEl) obs.observe(chatEl, { childList: true, subtree: true });
  setInterval(addCopyButtons, 2000); // fallback
})();
"""

# ============================================================
# API de Python expuesta a JavaScript (pywebview.api)
# ============================================================
class GenesisDesktopAPI:
    """API accesible desde JS via window.pywebview.api"""

    def __init__(self):
        self._window = None
        self._pinned = True

    def set_window(self, window):
        self._window = window

    def toggle_pin(self, pinned):
        self._pinned = pinned
        if self._window:
            self._window.on_top = pinned

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def toggle_maximize(self):
        """Maximiza a pantalla completa o restaura al tamaño anterior.
        Devuelve True si quedó maximizada, False si restaurada."""
        if not self._window:
            return False
        if getattr(self, "_maximized", False):
            try:
                self._window.restore()
            except Exception:
                pass
            self._maximized = False
        else:
            try:
                self._window.maximize()
            except Exception:
                pass
            self._maximized = True
        return self._maximized

    def toggle_fullscreen(self):
        """Pantalla completa real (inmersiva, sin barra). Toggle. Salir con F11/Esc."""
        if self._window:
            try:
                self._window.toggle_fullscreen()
            except Exception:
                pass

    def open_external(self, url):
        """Abre una URL en el navegador del sistema (no en la cabina).
        Evita que clickear un resultado de investigación secuestre la ventana."""
        try:
            import webbrowser
            if url and (url.startswith("http://") or url.startswith("https://")):
                webbrowser.open(url)
                return True
        except Exception:
            pass
        return False

    def hide_to_tray(self):
        if self._window:
            self._window.hide()
            self._window._genesis_hidden = True


# ============================================================
# FLASK SERVER
# ============================================================
_flask_started = threading.Event()

def _start_flask_server():
    import logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    from web_ui import app
    _flask_started.set()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False, use_reloader=False)

def _wait_for_server(timeout=STARTUP_TIMEOUT):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://{FLASK_HOST}:{FLASK_PORT}/")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ============================================================
# SYSTEM TRAY
# ============================================================
_tray_icon = None
_webview_window = None

def _create_tray_icon():
    global _tray_icon
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Gradiente simulado (circulo con borde)
    draw.ellipse([1, 1, size-1, size-1], fill=(99, 102, 241, 255))    # indigo
    draw.ellipse([3, 3, size-3, size-3], fill=(59, 130, 246, 255))    # blue
    try:
        font = ImageFont.truetype("arial.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "G", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
              "G", fill="white", font=font)

    def on_show(icon, item):
        if _webview_window:
            _webview_window.show()
            _webview_window._genesis_hidden = False

    def on_hide(icon, item):
        if _webview_window:
            _webview_window.hide()
            _webview_window._genesis_hidden = True

    def on_quit(icon, item):
        icon.stop()
        if _webview_window:
            _webview_window.destroy()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Mostrar Genesis", on_show, default=True),
        pystray.MenuItem("Minimizar al tray", on_hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Cerrar Genesis", on_quit),
    )

    _tray_icon = pystray.Icon("genesis", img, "Genesis AI — Ctrl+Shift+G", menu)
    _tray_icon.run()


# ============================================================
# HOTKEY GLOBAL
# ============================================================
def _setup_hotkey():
    try:
        import keyboard
        def toggle_window():
            if _webview_window:
                if getattr(_webview_window, '_genesis_hidden', False):
                    _webview_window.show()
                    _webview_window._genesis_hidden = False
                else:
                    _webview_window.hide()
                    _webview_window._genesis_hidden = True
        keyboard.add_hotkey(HOTKEY, toggle_window, suppress=False)
        print(f"  [OK] Hotkey {HOTKEY.upper()} registrado")
    except Exception as e:
        print(f"  [WARN] Hotkey: {e}")


# ============================================================
# VENTANA PRINCIPAL
# ============================================================
def _get_screen_size():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080

def _calculate_window_geometry(mode):
    screen_w, screen_h = _get_screen_size()
    taskbar_h = 48
    win_h = screen_h - taskbar_h

    if mode == "right":
        return screen_w - SIDEBAR_WIDTH, 0, SIDEBAR_WIDTH, win_h
    elif mode == "left":
        return 0, 0, SIDEBAR_WIDTH, win_h
    else:  # center
        win_w = min(900, screen_w - 100)
        win_h = min(750, screen_h - 100)
        return (screen_w - win_w) // 2, (screen_h - win_h) // 2, win_w, win_h


def _on_loaded(window):
    """Se ejecuta cuando la pagina termina de cargar — inyecta la UI custom."""
    time.sleep(0.5)
    try:
        window.evaluate_js(INJECTED_JS)
    except Exception:
        pass


def main():
    global _webview_window, WINDOW_MODE

    # Habilitar autoplay de audio en WebView2 (sino la voz/TTS no suena: la
    # política por defecto bloquea audio.play() tras un fetch asíncrono).
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
        os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
        + " --autoplay-policy=no-user-gesture-required"
    ).strip()

    if "--left" in sys.argv:
        WINDOW_MODE = "left"
    elif "--center" in sys.argv:
        WINDOW_MODE = "center"
    elif "--right" in sys.argv:
        WINDOW_MODE = "right"

    # Forzar UTF-8 en stdout
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    elif not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print()
    print("  ==========================================")
    print("         GENESIS Desktop App")
    print(f"    Modo: {WINDOW_MODE}  |  Hotkey: {HOTKEY.upper()}")
    print("  ==========================================")
    print()

    # 1. Crear API bridge
    api = GenesisDesktopAPI()

    # 2. Crear ventana con splash
    import webview
    x, y, w, h = _calculate_window_geometry(WINDOW_MODE)
    frameless = WINDOW_MODE in ("right", "left")

    _webview_window = webview.create_window(
        APP_TITLE,
        html=SPLASH_HTML,
        width=w, height=h, x=x, y=y,
        resizable=True,
        frameless=frameless,
        on_top=WINDOW_MODE != "center",
        min_size=(350, 400),
        js_api=api,
    )
    _webview_window._genesis_hidden = False
    api.set_window(_webview_window)

    # 3. Arrancar Flask + navegar cuando este listo (background)
    def _boot_sequence():
        global _webview_window
        print("  [1/3] Iniciando servidor...")
        flask_t = threading.Thread(target=_start_flask_server, daemon=True)
        flask_t.start()
        _flask_started.wait(timeout=5)

        print("  [2/3] Esperando servidor...")
        if _wait_for_server():
            print(f"  [OK]  Servidor listo — http://{FLASK_HOST}:{FLASK_PORT}/jarvis")
            # Navegar al HUD JARVIS (cabina nativa, sin navegador)
            _webview_window.load_url(f"http://{FLASK_HOST}:{FLASK_PORT}/core")
            # Esperar carga e inyectar UI custom
            time.sleep(2)
            _on_loaded(_webview_window)
            # Re-inyectar en cada navegacion
            _webview_window.events.loaded += lambda: _on_loaded(_webview_window)
        else:
            print("  [ERROR] Servidor no respondio.")
            _webview_window.evaluate_js(
                "document.body.innerHTML = '<div style=\"text-align:center;padding:40px;color:#ef4444;\">"
                "<h2>Error</h2><p>El servidor Genesis no pudo iniciar.</p></div>'")

        print("  [3/3] Registrando hotkey y tray...")
        threading.Thread(target=_create_tray_icon, daemon=True).start()
        threading.Thread(target=_setup_hotkey, daemon=True).start()

        # Pre-calentar la voz clonada (XTTS) en segundo plano: evita ~20s de
        # silencio en el primer enroll/verify/manos-libres (queda caliente en VRAM).
        def _warm_xtts():
            try:
                from core import voice_clone
                if voice_clone.available():
                    voice_clone._load()
                    print("  [OK]  Voz clonada (XTTS) precargada en VRAM")
            except Exception:
                pass
        threading.Thread(target=_warm_xtts, daemon=True).start()

        # Escucha pasiva (manos libres) auto al arrancar — obedece SOLO tu voz
        # si hay huella entrenada (voiceprint). Decí «genesis ...» sin tocar nada.
        def _autostart_handsfree():
            try:
                from web_ui import get_genesis
                from core import handsfree
                hf = handsfree.get(get_genesis())
                msg = hf.start()
                print(f"  [OK]  {msg.splitlines()[0][:70]}")
            except Exception as e:
                print(f"  [warn] manos libres no arrancó: {str(e)[:80]}")
        threading.Thread(target=_autostart_handsfree, daemon=True).start()

        print()
        print(f"  Genesis Desktop activo — {HOTKEY.upper()} para toggle")

    boot_thread = threading.Thread(target=_boot_sequence, daemon=True)
    boot_thread.start()

    # 4. Bloquea hasta que se cierre (webview.start es blocking)
    # private_mode=False: persistir localStorage (voz, tema, preferencias)
    # storage_path: directorio donde WebView2 guarda perfil/cache/localStorage
    storage_dir = os.path.join(os.path.dirname(__file__), "data", "webview_profile")
    os.makedirs(storage_dir, exist_ok=True)
    webview.start(debug=False, private_mode=False, storage_path=storage_dir)

    if _tray_icon:
        _tray_icon.stop()
    os._exit(0)


if __name__ == "__main__":
    main()
