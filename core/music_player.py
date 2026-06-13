"""
GENESIS Music Player — Reproducción REAL de música (no solo abrir búsquedas).

Usa yt-dlp para:
  1. BUSCAR el tema exacto en YouTube (sin API key).
  2. CONFIRMAR si existe (devuelve título, artista y duración reales).
  3. RAZONAR si el resultado coincide con lo pedido.
  4. REPRODUCIR el video EXACTO (abre la URL del track, que autoreproduce).

A diferencia del enfoque viejo (abrir una búsqueda genérica y esperar que el
usuario clickee), esto va al tema puntual y confirma que existe antes de afirmar
que lo reproduce. Honesto: si no lo encuentra, lo dice.
"""
import os
import re
import webbrowser

# --- Cookies para sortear el "Sign in to confirm you're not a bot" de YouTube ---
# Desde ~2025 YouTube exige autenticación para extraer streams desde IPs "frías".
# Estrategia (de más estable a menos):
#   1. Archivo data/youtube_cookies.txt (Netscape) → no requiere cerrar el navegador.
#   2. Cookies del navegador (brave/chrome/edge/firefox) → funciona si está cerrado
#      y sin App-Bound Encryption (Chromium <127).
# Se cachea la primera estrategia que funcione para no re-probar en cada tema.
_COOKIE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "youtube_cookies.txt")
_BROWSERS = ("brave", "chrome", "edge", "firefox")
_working_cookie = None  # cache: dict de opts que funcionó, o {} (sin cookies)


def _cookie_strategies():
    """Lista ordenada de opciones de cookies a intentar."""
    strats = []
    if os.path.exists(_COOKIE_FILE):
        strats.append({"cookiefile": _COOKIE_FILE})
    for b in _BROWSERS:
        strats.append({"cookiesfrombrowser": (b,)})
    strats.append({})  # último recurso: sin cookies
    return strats


def cookies_available() -> bool:
    """True si hay un archivo de cookies configurado."""
    return os.path.exists(_COOKIE_FILE)


def _fmt_dur(seconds) -> str:
    try:
        s = int(seconds or 0)
    except (TypeError, ValueError):
        return "?"
    return f"{s // 60}:{s % 60:02d}"


def search_track(query: str) -> dict:
    """Busca el tema en YouTube. Devuelve metadata real o {} si no existe."""
    try:
        import yt_dlp
    except ImportError:
        return {"error": "yt-dlp no instalado"}
    opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": True, "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(f"ytsearch1:{query}", download=False)
        entries = info.get("entries") or []
        if not entries:
            return {}
        e = entries[0]
        return {
            "id": e.get("id"),
            "title": e.get("title", ""),
            "uploader": e.get("uploader") or e.get("channel") or "",
            "duration": e.get("duration") or 0,
        }
    except Exception as ex:
        return {"error": str(ex)}


def get_audio_url(video_id: str) -> str:
    """Devuelve la URL de stream de AUDIO directa (bestaudio) de un video.

    Esto evita el bloqueo de embed de los videos oficiales: en vez de embeber
    el video (que muchos MVs prohíben), reproducimos el audio crudo en un
    <audio> nativo. La URL es de googlevideo, ligada a la IP del que pide;
    como server y navegador son la misma máquina (localhost), funciona.
    """
    global _working_cookie
    try:
        import yt_dlp
    except ImportError:
        return ""
    base = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        # Preferir m4a (AAC): trae duración y seek correctos en <audio> HTML5.
        # webm/opus a veces muestra 0:00 y no autoarranca bien.
        "format": "bestaudio[ext=m4a]/bestaudio[acodec^=mp4a]/bestaudio/best",
        # YouTube exige resolver un challenge JS (firma/n-sig) para entregar las
        # URLs de audio. yt-dlp lo resuelve con yt-dlp-ejs + un runtime JS; usamos
        # Node (ya instalado). Sin esto, solo devuelve storyboards (imágenes).
        # NO forzamos player_client: los clientes bypass (ios/android) NO soportan
        # cookies, así que dejamos que yt-dlp elija el cliente correcto (web/tv).
        "js_runtimes": {"node": {}},
    }

    def _extract(extra):
        opts = dict(base)
        opts.update(extra)
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False)
        if info.get("url"):
            return info["url"]
        fmts = info.get("formats", [])
        for f in reversed(fmts):  # preferir m4a con url directa
            if f.get("ext") == "m4a" and f.get("url"):
                return f["url"]
        for f in reversed(fmts):  # cualquier audio con url
            if f.get("acodec") not in (None, "none") and f.get("url"):
                return f["url"]
        return ""

    # 1. Probar primero la estrategia que ya funcionó (cache).
    if _working_cookie is not None:
        try:
            u = _extract(_working_cookie)
            if u:
                return u
        except Exception:
            _working_cookie = None  # dejó de servir → re-probar todo

    # 2. Probar estrategias en orden hasta que una resuelva el stream.
    for strat in _cookie_strategies():
        try:
            u = _extract(strat)
            if u:
                _working_cookie = strat  # recordar la que sirvió
                return u
        except Exception:
            continue
    return ""


_YTM_APP_ID = "cinhimbnkkaeohfgghhklpknlkffjgod"  # PWA de YouTube Music


def _chrome_exe():
    """Ruta a chrome.exe (para lanzar la PWA de YouTube Music). None si no está."""
    cands = [
        os.path.join(os.environ.get("PROGRAMFILES", ""),
                     r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""),
                     r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     r"Google\Chrome\Application\chrome.exe"),
    ]
    for c in cands:
        if c and os.path.exists(c):
            return c
    try:
        import winreg
        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        p, _ = winreg.QueryValueEx(k, "")
        if p and os.path.exists(p):
            return p
    except Exception:
        pass
    return None


def ytmusic_available() -> bool:
    """True si se puede usar la app de YouTube Music (Chrome instalado)."""
    return _chrome_exe() is not None


# --- Reuso REAL de la ventana vía CDP (Chrome DevTools Protocol) ---
# Perfil de Chrome dedicado a Genesis (separado del tuyo). Se abre UNA vez con
# depuración remota; después se NAVEGA esa misma ventana a cada nueva canción
# (Page.navigate) → sin abrir/cerrar, sin parpadeo. Requiere login 1 vez.
_YTM_PROFILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "chrome_ytm")
_CDP_PORT = 9222


def _cdp_ytm_target():
    """Target 'page' de YouTube Music con depuración activa, o None."""
    try:
        import json
        import urllib.request
        data = json.load(urllib.request.urlopen(
            f"http://127.0.0.1:{_CDP_PORT}/json", timeout=4))
        for t in data:
            if t.get("type") == "page" and "music.youtube.com" in t.get("url", ""):
                return t
    except Exception:
        pass
    return None


def _cdp_navigate(url: str) -> bool:
    """Navega la ventana CDP de YouTube Music a `url` (reuso real, sin reabrir).

    YouTube Music tiene un `beforeunload` que, con música sonando, muestra el
    diálogo «¿Quieres salir de la aplicación?» y bloquea la navegación. Acá lo
    neutralizamos ANTES de navegar y, por las dudas, auto-aceptamos cualquier
    diálogo que aparezca.
    """
    t = _cdp_ytm_target()
    if not t:
        return False
    ws_url = t.get("webSocketDebuggerUrl")
    if not ws_url:
        return False
    try:
        import json
        import time as _t
        import websocket
        ws = websocket.create_connection(ws_url, timeout=8)
        ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        # Matar el beforeunload de YouTube Music (sino pregunta «¿salir?»)
        ws.send(json.dumps({"id": 2, "method": "Runtime.evaluate", "params": {
            "expression": ("window.onbeforeunload=null;"
                           "try{window.addEventListener('beforeunload',"
                           "function(e){e.stopImmediatePropagation();"
                           "delete e['returnValue'];},true);}catch(_){}")}}))
        ws.send(json.dumps({"id": 3, "method": "Page.navigate",
                            "params": {"url": url}}))
        # Leer respuestas; si igual aparece un diálogo, aceptarlo (no bloquear).
        ws.settimeout(3)
        deadline = _t.time() + 4
        while _t.time() < deadline:
            try:
                msg = json.loads(ws.recv())
            except Exception:
                break
            if msg.get("method") == "Page.javascriptDialogOpening":
                ws.send(json.dumps({"id": 99, "method": "Page.handleJavaScriptDialog",
                                    "params": {"accept": True}}))
            if msg.get("id") == 3:  # navigate respondió
                break
        ws.close()
        return True
    except Exception:
        return False


def _launch_ytm_cdp(url: str) -> bool:
    """Abre la ventana de YouTube Music (perfil dedicado de Genesis) con
    depuración remota, para poder reusarla después vía CDP."""
    chrome = _chrome_exe()
    if not chrome:
        return False
    import subprocess
    try:
        os.makedirs(_YTM_PROFILE, exist_ok=True)
        subprocess.Popen([chrome, f"--user-data-dir={_YTM_PROFILE}",
                          f"--remote-debugging-port={_CDP_PORT}",
                          "--remote-allow-origins=*", "--no-first-run",
                          "--no-default-browser-check", f"--app={url}"])
        return True
    except Exception:
        return False


def _close_ytmusic_windows() -> int:
    """Cierra ventanas-app de YouTube Music ya abiertas (para no apilar
    reproductores). Excluye pestañas de navegador (Brave/Chrome/Edge/Firefox)."""
    try:
        import uiautomation as auto
    except Exception:
        return 0
    closed = 0
    try:
        for w in auto.GetRootControl().GetChildren():
            try:
                if w.ControlTypeName != "WindowControl":
                    continue
                nm = (w.Name or "").lower()
                if "youtube music" not in nm:
                    continue
                # No tocar pestañas de navegador (su título trae el nombre del browser)
                if any(b in nm for b in ("- brave", "google chrome", "- chrome",
                                         "- microsoft", "mozilla", "firefox",
                                         "- opera")):
                    continue
                try:
                    w.GetWindowPattern().Close()
                    closed += 1
                except Exception:
                    pass
            except Exception:
                continue
    except Exception:
        pass
    return closed


def play_in_app(query: str, profile: str = "Default") -> dict:
    """Reproduce en la ventana de YouTube Music de Genesis (perfil dedicado).

    REUSA la misma ventana: si ya está abierta, la NAVEGA al nuevo tema vía CDP
    (sin abrir/cerrar, sin parpadeo). Si no, la abre. Evita yt-dlp/cookies/anti-bot
    (es YouTube Music real). La primera vez hay que loguearse 1 vez en esa ventana.
    """
    info = search_track(query)
    if info.get("error"):
        return {"ok": False, "error": info["error"]}
    vid = info.get("id")
    if not vid:
        return {"ok": False, "error": "no encontré ese tema"}
    if not _chrome_exe():
        return {"ok": False, "error": "no encontré Chrome para abrir YouTube Music"}
    url = f"https://music.youtube.com/watch?v={vid}"
    base = {"title": info.get("title", ""), "uploader": info.get("uploader", ""),
            "duration": info.get("duration", 0), "id": vid, "url": url}
    # 1) ¿hay ventana CDP viva? → navegar EN EL LUGAR (reuso real)
    if _cdp_ytm_target() and _cdp_navigate(url):
        return {"ok": True, "method": "ytmusic_cdp_reuse", **base}
    # 2) primera vez / ventana cerrada → abrirla (con debug para reusarla luego)
    if _launch_ytm_cdp(url):
        return {"ok": True, "method": "ytmusic_cdp_launch", **base}
    return {"ok": False, "error": "no pude abrir YouTube Music"}


def _media_key(vk: int) -> bool:
    """Manda una tecla multimedia global (la procesa el reproductor activo, ej:
    YouTube Music en su ventana de app). No roba foco."""
    try:
        import ctypes
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def media_playpause() -> bool:
    return _media_key(0xB3)   # VK_MEDIA_PLAY_PAUSE (toggle)


def media_next() -> bool:
    return _media_key(0xB0)   # VK_MEDIA_NEXT_TRACK


def media_prev() -> bool:
    return _media_key(0xB1)   # VK_MEDIA_PREV_TRACK


def stop_app() -> int:
    """Detiene la música cerrando la ventana del reproductor de YouTube Music."""
    return _close_ytmusic_windows()


def _match_score(query: str, title: str) -> float:
    """Razonamiento simple: qué fracción de las palabras del pedido están en el título."""
    qs = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 2]
    if not qs:
        return 1.0
    t = title.lower()
    hits = sum(1 for w in qs if w in t)
    return hits / len(qs)


def play(query: str, platform: str = "youtube_music", open_browser: bool = False) -> dict:
    """Busca, confirma, razona y prepara la reproducción.

    Args:
        open_browser: si True abre el navegador externo; si False (default) NO
            abre nada y devuelve embed_url para reproducir DENTRO de la cabina.
    """
    track = search_track(query)
    if track.get("error"):
        return {"ok": False, "reason": "error", "detail": track["error"], "query": query}
    if not track:
        return {"ok": False, "reason": "not_found", "query": query}

    vid = track["id"]
    if platform == "youtube":
        url = f"https://www.youtube.com/watch?v={vid}"
    else:
        url = f"https://music.youtube.com/watch?v={vid}"
    embed_url = f"https://www.youtube.com/embed/{vid}?autoplay=1&enablejsapi=1"

    score = _match_score(query, track["title"])
    opened = True
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            opened = False

    return {
        "ok": opened,
        "reason": "playing" if opened else "open_failed",
        "query": query,
        "track": track,
        "video_id": vid,
        "duration_fmt": _fmt_dur(track["duration"]),
        "match": score,        # 1.0 = coincide perfecto; <0.5 = dudoso
        "url": url,
        "embed_url": embed_url,
        "platform": platform,
    }
