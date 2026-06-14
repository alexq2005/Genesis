"""
GENESIS — Reproducción REAL en Netflix vía CDP (Chrome DevTools Protocol).

Controla una ventana de Chrome real (con Widevine/DRM, así Netflix SÍ reproduce)
en un perfil dedicado de Genesis. Flujo de `play()`:
  1) abre/reusa la ventana (perfil dedicado, depuración remota)
  2) (opcional) cambia al perfil de Netflix por nombre (SwitchProfile)
  3) navega a la búsqueda del título
  4) extrae por JS el primer link reproducible (/watch/<ID>)
  5) navega a /watch/<ID>  → Netflix auto-reproduce

La PRIMERA vez hay que loguearse 1 sola vez en esa ventana (perfil propio de
Genesis, separado de tu Chrome). Después reproduce solo, a pedido del usuario.
"""
import os
import re
import json
import time
import subprocess

from core.music_player import _chrome_exe

_NETFLIX_PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "data", "chrome_netflix")
_CDP_PORT = 9224
_BASE = "https://www.netflix.com"


# ----------------------------------------------------------------- CDP ---
def _target():
    """Target 'page' de Netflix con depuración activa, o None."""
    try:
        import urllib.request
        data = json.load(urllib.request.urlopen(
            f"http://127.0.0.1:{_CDP_PORT}/json", timeout=4))
        for t in data:
            if t.get("type") == "page" and "netflix.com" in t.get("url", ""):
                return t
        # cualquier page (por si está en login)
        for t in data:
            if t.get("type") == "page":
                return t
    except Exception:
        pass
    return None


def _ws(target=None):
    """Abre un websocket al target CDP. None si no se puede."""
    t = target or _target()
    if not t:
        return None
    url = t.get("webSocketDebuggerUrl")
    if not url:
        return None
    try:
        import websocket
        return websocket.create_connection(url, timeout=10)
    except Exception:
        return None


def _eval(ws, expression, _id, await_promise=False):
    """Runtime.evaluate y devuelve el value (returnByValue). '' si falla."""
    try:
        ws.send(json.dumps({"id": _id, "method": "Runtime.evaluate", "params": {
            "expression": expression, "returnByValue": True,
            "awaitPromise": await_promise}}))
        ws.settimeout(8)
        deadline = time.time() + 9
        while time.time() < deadline:
            msg = json.loads(ws.recv())
            if msg.get("id") == _id:
                return (((msg.get("result") or {}).get("result") or {}).get("value")) or ""
    except Exception:
        pass
    return ""


def _navigate(ws, url, _id):
    """Page.navigate + acepta cualquier diálogo. No bloquea."""
    try:
        ws.send(json.dumps({"id": _id, "method": "Page.navigate", "params": {"url": url}}))
        ws.settimeout(3)
        deadline = time.time() + 4
        while time.time() < deadline:
            try:
                msg = json.loads(ws.recv())
            except Exception:
                break
            if msg.get("method") == "Page.javascriptDialogOpening":
                ws.send(json.dumps({"id": 999, "method": "Page.handleJavaScriptDialog",
                                    "params": {"accept": True}}))
            if msg.get("id") == _id:
                break
        return True
    except Exception:
        return False


def _wait_url(ws, must_contain, timeout=8.0):
    """Espera hasta que location.href contenga `must_contain` (confirma que la
    navegación SPA/real terminó y no leemos un DOM viejo). True si llegó."""
    end = time.time() + timeout
    _id = 700
    while time.time() < end:
        href = _eval(ws, "location.href", _id)
        _id += 1
        if must_contain in (href or ""):
            return True
        time.sleep(0.5)
    return False


def _launch(url):
    """Abre la ventana de Netflix (perfil dedicado) con depuración remota."""
    chrome = _chrome_exe()
    if not chrome:
        return False
    try:
        os.makedirs(_NETFLIX_PROFILE, exist_ok=True)
        subprocess.Popen([chrome, f"--user-data-dir={_NETFLIX_PROFILE}",
                          f"--remote-debugging-port={_CDP_PORT}",
                          "--remote-allow-origins=*", "--no-first-run",
                          "--no-default-browser-check",
                          "--autoplay-policy=no-user-gesture-required",
                          f"--app={url}"])
        return True
    except Exception:
        return False


def _ensure_window(url, wait=18):
    """Garantiza ventana CDP viva. La reusa (navega) o la lanza.
    Devuelve (ws, target_id) o (None, None)."""
    t = _target()
    if t:
        ws = _ws(t)
        if ws:
            ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            _navigate(ws, url, 2)
            return ws, t.get("id")
    # no había → lanzar y esperar a que el endpoint de debug responda
    _launch(url)
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(1.0)
        t = _target()
        if t:
            ws = _ws(t)
            if ws:
                ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
                return ws, t.get("id")
    return None, None


def _move_to_screen(target_id, screen):
    """Mueve la ventana de Netflix al monitor `screen` (1=primaria) y fullscreen,
    vía Browser.setWindowBounds (CDP). Devuelve el nombre de la pantalla o None."""
    if not target_id:
        return None
    try:
        from core.system_control import get_monitors
        mons = get_monitors()
        if not mons:
            return None
        idx = max(0, min(len(mons) - 1, int(screen) - 1))
        x, y, w, h = mons[idx]
        import urllib.request
        import websocket
        ver = json.load(urllib.request.urlopen(
            f"http://127.0.0.1:{_CDP_PORT}/json/version", timeout=4))
        bws = ver.get("webSocketDebuggerUrl")
        if not bws:
            return None
        ws = websocket.create_connection(bws, timeout=8)
        ws.send(json.dumps({"id": 1, "method": "Browser.getWindowForTarget",
                            "params": {"targetId": target_id}}))
        win = None
        ws.settimeout(5)
        deadline = time.time() + 6
        while time.time() < deadline:
            m = json.loads(ws.recv())
            if m.get("id") == 1:
                win = (m.get("result") or {}).get("windowId")
                break
        if win is not None:
            # primero normal en el rect del monitor, después fullscreen
            ws.send(json.dumps({"id": 2, "method": "Browser.setWindowBounds", "params": {
                "windowId": win, "bounds": {"left": x, "top": y, "width": w,
                                            "height": h, "windowState": "normal"}}}))
            time.sleep(0.3)
            ws.send(json.dumps({"id": 3, "method": "Browser.setWindowBounds", "params": {
                "windowId": win, "bounds": {"windowState": "fullscreen"}}}))
            time.sleep(0.3)
        ws.close()
        n = len(mons)
        return f"pantalla {idx + 1} de {n}" if n > 1 else "la pantalla"
    except Exception:
        return None


# JS: en la página de RESULTADOS, devuelve [{sug,name}] de cada resultado en orden
# de ranking. `sug` = "Video:<ID>" o "Collection:<ID>"; `name` = título visible
# (.fallback-text). Python elige por COINCIDENCIA DE NOMBRE con lo pedido — NO el
# #1 a ciegas (eso reproducía "Los Vikingos" cuando se pidió "Vikingos").
_FIND_RESULTS = """
(function(){
  var out=[], seen={};
  // Netflix usa VARIOS formatos de link para los resultados según la query:
  //   suggestionId=Video:<ID>   (ej. 'vikingos')
  //   jbv=<ID>                  (ej. 'joven sheldon')
  // El nombre sale de .fallback-text, aria-label o alt (de la <a> o su <img>).
  var as=document.querySelectorAll('a[href*="suggestionId=Video"], a[href*="jbv="]');
  for(var i=0;i<as.length;i++){
    var a=as[i], h=a.getAttribute('href')||'';
    var m=h.match(/(?:suggestionId=Video(?:%3A|:)|jbv=)(\\d+)/);
    if(!m){continue;}
    var id=m[1];
    if(seen[id]){continue;}
    var fb=a.querySelector('.fallback-text, p, .title');
    var img=a.querySelector('img');
    var nm=((fb?fb.textContent:'') || a.getAttribute('aria-label') ||
            a.getAttribute('alt') || (img?img.getAttribute('alt'):'') ||
            a.textContent || '').trim();
    if(!nm){continue;}
    seen[id]=1;
    out.push({sug:'Video:'+id, name:nm.slice(0,80)});
    if(out.length>=15){break;}
  }
  return JSON.stringify(out);
})()
"""

# JS: en la página de TÍTULO (/title/<id>), devuelve {url,name} del botón de play.
# El billboardPlayButton apunta a /watch/<episodioID> reproducible (la serie
# pelada /watch/<serieID> sólo da la página de descripción, sin video).
_FIND_PLAY = """
(function(){
  // SÓLO el botón de play del título (data-uia con 'play'). El fallback genérico
  // a[href*="/watch/"] agarraba links stale de 'Seguir viendo' (ej. Vikingos) que
  // quedaban en el DOM → reproducía el título equivocado. Si aún no renderizó, se
  // devuelve '' y el poll de _play_chrome reintenta.
  var pb = document.querySelector('a[data-uia*="play"][href*="/watch/"]');
  if(!pb){return '';}
  var name = (document.querySelector('h1,[data-uia="title-card-title"]')||{}).textContent
             || (document.title||'').replace(/\\s*[—|-]\\s*Netflix.*/,'');
  return JSON.stringify({url: location.origin+pb.getAttribute('href'),
                         name: (name||'').trim().slice(0,80)});
})()
"""

_IS_LOGIN = """
(function(){var u=location.href;return (u.indexOf('/login')>=0||
 u.indexOf('/signup')>=0||document.querySelector('input[name=\"userLoginId\"]')!=null)?'1':'';})()
"""


def _norm_title(s: str) -> str:
    """Normaliza un título para comparar: minúsculas, sin acentos, sin
    puntuación ni espacios extra."""
    s = (s or "").strip().lower()
    acc = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    s = "".join(acc.get(c, c) for c in s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _choose_result(results, query):
    """Elige el resultado cuyo NOMBRE coincide EXACTO con lo pedido.
    Devuelve (result|None, exact:bool). Sólo auto-reproduce con match exacto:
    si se pide «vikingos» y el catálogo tiene «Los Vikingos» (otro título),
    NO se reproduce a ciegas — se devuelve None para preguntar al usuario.
    Excepción razonable: si hay UN ÚNICO resultado Video y su nombre EMPIEZA con
    lo pedido (ej. «stranger» → «Stranger Things»), se acepta."""
    q = _norm_title(query)
    if not q:
        return None, False
    vids = [r for r in results if r.get("sug", "").startswith("Video:")]
    # 1) match exacto de nombre (sobre cualquier tipo, pero preferir Video)
    for pool in (vids, results):
        for r in pool:
            if _norm_title(r.get("name", "")) == q:
                return r, True
    # 2) único Video cuyo nombre EMPIEZA con lo pedido → aceptable
    starts = [r for r in vids if _norm_title(r.get("name", "")).startswith(q + " ")]
    if len(starts) == 1:
        return starts[0], False
    return None, False


# --------------------------------------------------------------- API ---
# AppID de la app oficial de Netflix (Microsoft Store, WebView2).
_APP_ID = "4DF9E0F8.Netflix_mcm4njqhnhss8!Netflix.App"


def app_installed() -> bool:
    """True si la app de Netflix (Store) está instalada."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "if (Get-AppxPackage *Netflix*) {'1'} else {'0'}"],
            capture_output=True, text=True, timeout=10)
        return "1" in (r.stdout or "")
    except Exception:
        return False


def launch_app(profile: str = None) -> str:
    """Abre la app de Netflix. Si se indica `profile`, intenta entrar al primer
    perfil por teclado (la app WebView2 NO expone los tiles a la automatización,
    así que no se puede apuntar a uno por nombre — solo el primero/enfocado)."""
    try:
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{_APP_ID}"])
    except Exception as e:
        return f"[ERROR] No pude abrir la app de Netflix: {str(e)[:120]}"
    if not profile:
        return "🎬 Abriendo la app de Netflix."
    # Best-effort: esperar la carga y seleccionar el primer perfil con teclado.
    try:
        import uiautomation as auto
        time.sleep(7)
        nf = _find_window()
        if nf:
            nf.SetActive()
            time.sleep(0.8)
            auto.SendKeys("{Tab}")
            time.sleep(0.3)
            auto.SendKeys("{Enter}")
            return (f"🎬 Abrí Netflix y entré al primer perfil. Si «{profile}» no es "
                    f"el de la izquierda, elegilo vos — la app oculta los perfiles a "
                    f"la automatización y no puedo apuntar a uno por nombre.")
    except Exception:
        pass
    return f"🎬 Abrí Netflix. Elegí el perfil «{profile}» (no pude seleccionarlo solo)."


def _find_window():
    """Devuelve el WindowControl de la app de Netflix, o None."""
    import uiautomation as auto
    for w in auto.GetRootControl().GetChildren():
        try:
            if w.ControlTypeName == "WindowControl" and "netflix" in (w.Name or "").lower():
                return w
        except Exception:
            continue
    return None


def _find_menuitem(name, timeout=3.0):
    """Busca un MenuItem por nombre (substring) en cualquier popup, con espera."""
    import uiautomation as auto
    name_l = name.lower()
    end = time.time() + timeout
    while time.time() < end:
        try:
            for ctrl, _d in auto.WalkControl(auto.GetRootControl(), maxDepth=15):
                if ctrl.ControlTypeName == "MenuItemControl" and \
                        name_l in (ctrl.Name or "").lower():
                    return ctrl
        except Exception:
            pass
        time.sleep(0.4)
    return None


def app_playpause() -> str:
    """Pausa/reanuda la app de Netflix (foco + barra espaciadora)."""
    try:
        import uiautomation as auto
    except Exception:
        return "🎬 Falta uiautomation para controlar la app."
    nf = _find_window()
    if not nf:
        return "🎬 La app de Netflix no está abierta."
    try:
        nf.SetActive()
        time.sleep(0.4)
        auto.SendKeys(" ")
        return "🎬 Play/pausa en Netflix."
    except Exception as e:
        return f"[ERROR] {str(e)[:120]}"


def cast_app(device_name: str = None) -> str:
    """Castea la app de Netflix (Store, WebView2) a un Chromecast vía su menú
    «Configuración y más → Más herramientas → Transmitir contenido». Best-effort
    (automatización de UI): si no logra clickear el dispositivo, deja el selector
    abierto para que el usuario elija (1 click)."""
    try:
        import uiautomation as auto
    except Exception:
        return "📺 Falta uiautomation para manejar el menú de la app."
    nf = _find_window()
    if not nf:
        launch_app()        # abrirla y esperar a que cargue
        time.sleep(8)
        nf = _find_window()
    if not nf:
        return ("🎬 No pude abrir la app de Netflix. Abrila a mano y pedí de nuevo "
                "«casteá netflix a la tv».")
    try:
        nf.SetActive()
        time.sleep(0.6)
        # 1) botón "..." (Configuración y más)
        btn = nf.ButtonControl(AutomationId="view_1015")
        if not btn.Exists(2):
            btn = nf.ButtonControl(Name="Configuración y más (Alt+F)")
        if not btn.Exists(1):
            return "📺 No encontré el botón «...» de la app de Netflix."
        btn.Click(simulateMove=False)
        time.sleep(1.2)
        # 2) "Más herramientas" → el flyout se abre con HOVER. NO usar Expand()
        #    (toggle que cierra el submenú). Mantener el cursor encima.
        mas = _find_menuitem("herramientas", timeout=3)
        if not mas:
            auto.SendKeys("{Esc}")
            return "📺 No se abrió el menú «...» de la app. Reintentá en un momento."
        trans = None
        for _ in range(3):
            try:
                mas.MoveCursorToInnerPos(simulateMove=True)
            except Exception:
                pass
            time.sleep(1.2)
            trans = _find_menuitem("transmitir", timeout=0.6)  # "Transmitir contenido a un dispositivo"
            if trans:
                break
        if not trans:
            auto.SendKeys("{Esc}")
            return ("📺 No encontré «Transmitir contenido» en el submenú. Abrilo a mano: "
                    "«...» → Más herramientas → Transmitir contenido a un dispositivo.")
        # 3) abrir el selector de dispositivos (hover para desplegar el submenú de devices)
        try:
            trans.MoveCursorToInnerPos(simulateMove=True)
        except Exception:
            pass
        time.sleep(1.3)
        # 4) elegir dispositivo en el selector
        if device_name:
            name_l = device_name.lower()
            end = time.time() + 7
            while time.time() < end:
                # mantener el cursor sobre "Transmitir…" para que el submenú no se cierre
                for ctrl, _d in auto.WalkControl(auto.GetRootControl(), maxDepth=17):
                    try:
                        nm = (ctrl.Name or "").lower()
                        if name_l in nm and ctrl.ControlTypeName in (
                                "MenuItemControl", "ListItemControl", "ButtonControl",
                                "TextControl", "HyperlinkControl"):
                            try:
                                ctrl.GetInvokePattern().Invoke()
                            except Exception:
                                ctrl.Click(simulateMove=False)
                            return f"📺 Transmitiendo Netflix a «{device_name}»."
                    except Exception:
                        continue
                time.sleep(0.6)
            return (f"📺 Abrí «Transmitir contenido» pero no encontré «{device_name}» "
                    f"en la lista de dispositivos. Elegilo vos (1 click).")
        # sin device → invocar transmitir para que aparezca el selector
        try:
            trans.GetInvokePattern().Invoke()
        except Exception:
            pass
        return "📺 Abrí el selector de transmisión. Elegí tu dispositivo en la lista."
    except Exception as e:
        return f"[ERROR] Cast app: {str(e)[:140]}"


def play(query: str = "", profile: str = None, screen: int = None) -> str:
    """Reproduce en Netflix.
    - SIN título → abre la app de la Store (lo que el usuario quiere para 'abrí netflix').
    - CON título → ventana Chrome dedicada (CDP): busca en /search, extrae el primer
      /watch/<ID> y navega → Netflix auto-reproduce. Es la ÚNICA vía que realmente
      BUSCA y REPRODUCE sola (la app de la Store no se deja automatizar adentro:
      verificado 2026-06-14 — sin protocolo, sin app-URI-handler, su WebView2 ignora
      CDP, y los tiles no exponen nombre a UIA). Misma arquitectura que la música.
    Cae a la app Store si no hay Chrome."""
    if not query:
        return launch_app(profile)
    if not _chrome_exe():
        r = launch_app(profile)
        return r + (f"\nℹ️ Buscá **{query}** en la app — no encontré Chrome para "
                    f"reproducir solo.")
    return _play_chrome(query, profile=profile, screen=screen)


# Posiciones (fracción de la ventana maximizada) calibradas 2026-06-14 sobre la
# app de la Store a 1936x1048. Verificado end-to-end reproduciendo Vikingos.
_M_SEARCH = (0.830, 0.076)     # ícono de búsqueda (lupa, arriba-derecha)
_M_TILE1 = (0.100, 0.235)      # 1er resultado del grid (arriba-izquierda)
_M_PLAY = (0.296, 0.508)       # botón Reproducir/Reanudar del modal (triángulo)
_M_BACK = (0.030, 0.075)       # flecha Atrás (←) arriba-izquierda del player/modal


def _tess():
    """Configura y devuelve pytesseract, o None si no se puede importar."""
    try:
        import pytesseract
    except Exception:
        return None
    for c in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe")):
        if os.path.exists(c):
            pytesseract.pytesseract.tesseract_cmd = c
            break
    return pytesseract


def _search_results_visible(L, T, W, H):
    """True si la pantalla muestra RESULTADOS de búsqueda (no el home). Detecta por
    OCR el encabezado «Más contenido para explorar», que SÓLO aparece en la página
    de resultados (verificado: ausente en el home). Devuelve None si no hay OCR
    disponible (no se puede verificar → no bloquear)."""
    pt = _tess()
    if pt is None:
        return None
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(L, T + int(0.10 * H), L + W, T + int(0.18 * H)))
        txt = pt.image_to_string(img, lang="spa+eng").lower()
        return ("explorar" in txt) or ("contenido" in txt)
    except Exception:
        return None


def _cabin_hwnd():
    """HWND de la ventana de la cabina de Genesis. Está docked a la derecha y
    always-on-top → TAPA la lupa de Netflix (arriba-derecha). Hay que minimizarla
    durante el flujo por mouse y restaurarla después. None si no se encuentra."""
    try:
        import uiautomation as auto
        for w in auto.GetRootControl().GetChildren():
            try:
                nm = (w.Name or "").lower()
                if w.ControlTypeName == "WindowControl" and \
                        ("genesis" in nm or "jarvis" in nm):
                    return w.NativeWindowHandle
            except Exception:
                continue
    except Exception:
        pass
    return None


def play_store_mouse(query: str, profile: str = None) -> str:
    """Reproduce un título en la app de Netflix (Microsoft Store) por MOUSE +
    teclado (sin CDP, sin OCR). Clickea por posición RELATIVA a la ventana:
    buscador → tipea el título → 1er resultado → botón Reproducir/Reanudar.
    VENTAJA vs CDP: el grid visual rankea mejor (ej. «vikingos» → la serie, no la
    peli «Los Vikingos»). DESVENTAJA: frágil (depende de la ventana maximizada y
    al frente, y del layout de Netflix). Trae la app al frente (SetActive+Maximize)
    para que no la tape la cabina."""
    try:
        import pyautogui
    except Exception:
        return "🎬 Falta pyautogui para el control por mouse."
    nf = _find_window()
    if not nf:
        try:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{_APP_ID}"])
        except Exception as e:
            return f"[ERROR] No pude abrir Netflix: {str(e)[:100]}"
        time.sleep(9)
        nf = _find_window()
    if not nf:
        return "🎬 No pude encontrar la ventana de Netflix."
    pyautogui.FAILSAFE = True
    import ctypes
    cabin = _cabin_hwnd()                    # la cabina tapa la lupa → minimizarla
    try:
        if cabin:
            ctypes.windll.user32.ShowWindow(cabin, 6)     # SW_MINIMIZE
            time.sleep(0.7)
        nf.SetActive()
        try:
            nf.Maximize()
        except Exception:
            pass
        time.sleep(1.6)
        r = nf.BoundingRectangle
        L, T = r.left, r.top
        W, H = r.right - r.left, r.bottom - r.top

        def _click(frac, wait):
            pyautogui.click(int(L + frac[0] * W), int(T + frac[1] * H))
            time.sleep(wait)

        # Salir de cualquier player/modal abierto para volver a la vista CON
        # buscador (si hay un video corriendo, la lupa no está en pantalla). El
        # botón ATRÁS (flecha ←, arriba-izq) es más confiable que Esc; mover el
        # mouse revela los controles. Dos veces: player → título → grilla.
        for _ in range(2):
            pyautogui.moveTo(int(L + 0.5 * W), int(T + 0.45 * H))   # revela controles
            time.sleep(0.5)
            _click(_M_BACK, 1.6)                     # ← Atrás
        pyautogui.press("esc")                       # cerrar modal residual si quedó
        time.sleep(0.8)

        def _open_and_type(q):
            """Abre la búsqueda y tipea. Re-enfoca Netflix ANTES de escribir para
            que las teclas no se las robe otra ventana (la cabina compite por el
            foco en el flujo por voz → el campo quedaba vacío)."""
            _click(_M_SEARCH, 1.2)                   # abrir búsqueda
            try:
                nf.SetActive()                       # re-asegurar foco en Netflix
            except Exception:
                pass
            time.sleep(0.5)
            pyautogui.write(q, interval=0.06)
            time.sleep(2.8)                          # esperar resultados

        _open_and_type(query)
        # SEGURO: confirmar que abrió la búsqueda. Si seguimos en el HOME, clickear
        # play dispararía el destacado top-1 del billboard → NO reproducir.
        if _search_results_visible(L, T, W, H) is False:
            _open_and_type(query)                    # reintentar (foco + tipeo)
            if _search_results_visible(L, T, W, H) is False:
                return ("🎬 No pude abrir la búsqueda de Netflix (sigo en el inicio) "
                        "→ no reproduje nada para no poner el destacado equivocado. "
                        "Fijate que la app esté al frente y volvé a pedirlo.")
        _click(_M_TILE1, 3.0)                        # 1er resultado → modal
        _click(_M_PLAY, 2.5)                         # Reproducir/Reanudar
        return f"🎬 Reproduciendo **{query}** en la app de Netflix (por mouse)."
    except Exception as e:
        return f"[ERROR] Netflix mouse: {str(e)[:120]}"
    finally:
        if cabin:
            try:
                ctypes.windll.user32.ShowWindow(cabin, 9)     # SW_RESTORE cabina
            except Exception:
                pass


def _play_chrome(query: str, profile: str = None, screen: int = None) -> str:
    """Reproduce un título por CDP en la ventana-app de Chrome (modo --app).
    Flujo de DOS saltos: /search → ID del 1er resultado → /title/<id> →
    /watch/<episodioID> del botón de play → auto-reproduce. Confirma el nombre
    real del título antes de declarar éxito."""
    if not _chrome_exe():
        return "🎬 No encontré Chrome para abrir Netflix."
    import urllib.parse as up
    search_url = f"{_BASE}/search?q=" + up.quote(query)
    ws, tid = _ensure_window(search_url, wait=18)
    if not ws:
        return "🎬 No pude abrir la ventana de Netflix."
    try:
        # ¿está logueado?
        time.sleep(2.0)
        if _eval(ws, _IS_LOGIN, 10) == "1":
            ws.close()
            return ("🎬 Abrí la ventana de Netflix de Genesis, pero hay que **iniciar "
                    "sesión una sola vez** ahí (es un perfil propio, separado de tu "
                    "Chrome). Logueate y volvé a pedírmelo — después reproduzco solo.")
        # cambiar de perfil si lo pidieron
        if profile:
            _navigate(ws, f"{_BASE}/SwitchProfile?tprofileName=" + up.quote(profile.title()), 11)
            time.sleep(2.5)
        # navegación FRESCA a la búsqueda + esperar a que la URL llegue (evita leer
        # resultados viejos de una búsqueda anterior que aún están en el DOM)
        _navigate(ws, search_url, 12)
        _wait_url(ws, "/search", 8)
        time.sleep(1.2)
        # SALTO 1: esperar resultados y ELEGIR POR NOMBRE (no el #1 a ciegas)
        results = []
        for i in range(10):
            time.sleep(1.0)
            raw = _eval(ws, _FIND_RESULTS, 20 + i)
            if raw:
                try:
                    results = json.loads(raw)
                except Exception:
                    results = []
                if results:
                    break
        if not results:
            ws.close()
            return (f"🎬 Abrí Netflix buscando «{query}» pero no encontré resultados. "
                    f"¿Está en el catálogo? Dale play vos en la ventana.")
        chosen, exact = _choose_result(results, query)
        if not chosen:
            # sin match claro → no reproducir cualquier cosa; ofrecer opciones
            ws.close()
            opts = [r["name"] for r in results
                    if r.get("sug", "").startswith("Video:")][:5]
            lista = "\n".join(f"  • {o}" for o in opts)
            return (f"🎬 No encontré un título llamado exactamente «{query}» en el "
                    f"catálogo. Lo más parecido:\n{lista}\nDecime cuál ponés "
                    f"(ej: «reproducí {opts[0]} en netflix»).")
        m = re.search(r"(?:Video|Collection):(\d+)", chosen.get("sug", ""))
        title_id = m.group(1) if m else ""
        if not title_id:
            ws.close()
            return f"🎬 Encontré «{chosen.get('name', query)}» pero no pude abrirlo."
        # SALTO 2: ir a la página del título y sacar el link de play (episodio real)
        _navigate(ws, f"{_BASE}/title/{title_id}", 30)
        # Netflix redirige al ID canónico (/title/60022621 → /title/80170690), así
        # que esperamos a CUALQUIER /title/, no al id puntual.
        _wait_url(ws, "/title/", 8)
        time.sleep(1.2)
        watch_url, name = "", ""
        for i in range(10):
            time.sleep(1.0)
            raw = _eval(ws, _FIND_PLAY, 31 + i)
            if raw:
                try:
                    d = json.loads(raw)
                    watch_url, name = d.get("url", ""), d.get("name", "")
                except Exception:
                    watch_url = ""
                # rechazar páginas 'home' (si redirigió, name = 'Inicio'/'Home')
                if watch_url and name.strip().lower() not in (
                        "inicio", "inicio de netflix", "home", "netflix"):
                    break
                watch_url = ""
        if not watch_url:
            ws.close()
            return (f"🎬 Encontré «{query}» pero no pude arrancar la reproducción. "
                    f"Dale play vos en la ventana.")
        _navigate(ws, watch_url, 45)        # → Netflix auto-reproduce el episodio
        time.sleep(3.5)                     # dejar que el player commitee antes de cerrar
        ws.close()
        donde = ""
        if screen:
            scr = _move_to_screen(tid, screen)
            if scr:
                donde = f" en **{scr}** (pantalla completa)"
        shown = name or query           # nombre real confirmado del título
        return f"🎬 Reproduciendo **{shown}** en Netflix{donde}."
    except Exception as e:
        try:
            ws.close()
        except Exception:
            pass
        return f"[ERROR] Netflix: {str(e)[:140]}"


def play_pause() -> str:
    """Pausa/reanuda el video de Netflix."""
    ws = _ws()
    if not ws:
        return "🎬 No hay una ventana de Netflix activa."
    js = ("(function(){var v=document.querySelector('video');if(!v)return 'no';"
          "if(v.paused){v.play();return 'play';}else{v.pause();return 'pause';}})()")
    r = _eval(ws, js, 50)
    ws.close()
    if r == "pause":
        return "🎬 Pausé Netflix."
    if r == "play":
        return "🎬 Reanudé Netflix."
    return "🎬 No encontré un video en reproducción."


# JS: abre el selector de transmisión de Chrome.
#  1) botón de cast del reproductor de Netflix (DOM de la página), o
#  2) Remote Playback API del <video> (v.remote.prompt()).
_OPEN_CAST = """
(function(){
  var b=document.querySelector('[data-uia="control-cast"],button[aria-label*="ransmit"],'
        +'button[aria-label*="ast"]');
  if(b){b.click();return 'btn';}
  var v=document.querySelector('video');
  if(v&&v.remote){try{v.remote.prompt();return 'remote';}catch(e){return 'err:'+e.message;}}
  return 'none';
})()
"""


def _click_device_ui(device_name: str, tries: int = 3) -> bool:
    """Clickea el dispositivo por nombre en el bubble de cast de Chrome (UI Automation)."""
    try:
        import uiautomation as auto
    except Exception:
        return False
    name_l = (device_name or "").strip().lower()
    if not name_l:
        return False
    for _ in range(tries):
        time.sleep(1.2)
        try:
            for ctrl, _d in auto.WalkControl(auto.GetRootControl(), maxDepth=28):
                try:
                    nm = (ctrl.Name or "").lower()
                    if name_l in nm and ctrl.ControlTypeName in (
                            "ListItemControl", "ButtonControl", "MenuItemControl",
                            "TextControl", "HyperlinkControl"):
                        ctrl.Click(simulateMove=False)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
    return False


def cast(device_name: str = None) -> str:
    """Netflix = SOLO la app de la Store. Redirige a cast_app (no usa Chrome)."""
    return cast_app(device_name)


def _cast_chrome(device_name: str = None) -> str:
    """[DESHABILITADO] Cast vía Chrome. Reemplazado por cast_app (app de la Store)."""
    ws = _ws()
    if not ws:
        return ("🎬 No hay una ventana de Netflix activa. Pedí primero «reproducí X "
                "en netflix» y después «casteá a la tv».")
    r = _eval(ws, _OPEN_CAST, 60, await_promise=False)
    ws.close()
    if r == "none":
        return ("📺 No encontré el botón de transmitir en el reproductor. Abrí el menú "
                "de Chrome (⋮) → «Transmitir…» y elegí el dispositivo.")
    if r.startswith("err"):
        return ("📺 Netflix bloqueó la transmisión directa del video. Probá: menú de "
                "Chrome (⋮) → «Transmitir…» → «Transmitir pestaña» → elegí el Chromecast.")
    # se abrió el selector → intentar clickear el dispositivo
    if device_name:
        if _click_device_ui(device_name):
            return f"📺 Transmitiendo Netflix a «{device_name}» desde el navegador."
        return (f"📺 Abrí el selector de transmisión pero no pude clickear «{device_name}» "
                f"automáticamente. Elegilo en la lista (1 click) y empieza a transmitir.")
    return "📺 Abrí el selector de transmisión de Chrome. Elegí tu Chromecast en la lista."


def stop() -> str:
    """Detiene (pausa + vuelve al inicio)."""
    ws = _ws()
    if not ws:
        return "🎬 No hay una ventana de Netflix activa."
    try:
        _eval(ws, "var v=document.querySelector('video');if(v)v.pause();", 51)
        _navigate(ws, f"{_BASE}/", 52)
        ws.close()
        return "🎬 Detuve Netflix."
    except Exception:
        return "🎬 No pude detener Netflix."
