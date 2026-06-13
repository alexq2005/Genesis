"""
GENESIS — Chromecast / Cast: descubrir y mandar contenido a la TV.

Usa pychromecast (mDNS). Descubre Chromecasts en la red y permite castear
YouTube, controlar volumen y detener. La primera detección tarda ~8s (escaneo).
"""
_CACHE = {"devices": [], "ts": 0}


def discover(timeout: int = 8) -> list:
    """Descubre Chromecasts en la red. Devuelve lista de dicts {name, model, host}."""
    try:
        import pychromecast
        ccs, browser = pychromecast.get_chromecasts(timeout=timeout)
        devs = []
        for cc in ccs:
            i = cc.cast_info
            devs.append({"name": i.friendly_name, "model": i.model_name,
                         "host": str(i.host), "port": i.port})
        try:
            pychromecast.discovery.stop_discovery(browser)
        except Exception:
            pass
        import time
        _CACHE["devices"] = devs
        _CACHE["ts"] = time.time()
        return devs
    except Exception:
        return []


def list_devices() -> str:
    devs = discover()
    if not devs:
        return ("📺 No encontré Chromecast/Google Cast en la red. ¿Está prendido y en "
                "la misma red WiFi?")
    out = ["📺 Dispositivos de cast en la red:"]
    for d in devs:
        out.append(f"  • {d['name']}  ({d['model']}) — {d['host']}")
    return "\n".join(out)


def _connect(device_name: str = None, timeout: int = 10):
    """Conecta a un Chromecast por nombre (o el primero/único). Devuelve el cast o None."""
    import pychromecast
    name = (device_name or "").strip().lower()
    # hosts cacheados aceleran el descubrimiento (evita re-escanear toda la red)
    known = [d["host"] for d in _CACHE["devices"] if d.get("host")] or None
    # match exacto del nombre completo desde la cache (ej: "dormitorio" -> "Dormitorio principal")
    full = None
    if name:
        for d in _CACHE["devices"]:
            if name in d["name"].lower():
                full = d["name"]
                break
    if full:
        ccs, browser = pychromecast.get_listed_chromecasts(
            friendly_names=[full], timeout=timeout, known_hosts=known)
    else:
        ccs, browser = pychromecast.get_chromecasts(
            timeout=timeout, known_hosts=known)
    target = None
    for cc in ccs:
        fn = cc.cast_info.friendly_name
        if not name or name in fn.lower():
            target = cc
            break
    if not target and ccs:
        target = ccs[0]
    if target:
        target.wait(timeout=timeout)
    try:
        pychromecast.discovery.stop_discovery(browser)
    except Exception:
        pass
    return target


def cast_youtube(query: str, device_name: str = None) -> str:
    """Castea un video/tema de YouTube al Chromecast (reproduce en la TV)."""
    try:
        from core.music_player import search_track
        info = search_track(query)
        vid = info.get("id")
        if not vid:
            return f"📺 No encontré «{query}» en YouTube."
        cc = _connect(device_name)
        if not cc:
            return "📺 No pude conectar al Chromecast (¿está prendido y en la red?)."
        from pychromecast.controllers.youtube import YouTubeController
        yt = YouTubeController()
        cc.register_handler(yt)
        yt.play_video(vid)
        return (f"📺 Reproduciendo **{info.get('title', query)}** en "
                f"«{cc.cast_info.friendly_name}» (TV).")
    except Exception as e:
        return f"[ERROR] No pude castear: {str(e)[:140]}"


def cast_stop(device_name: str = None) -> str:
    try:
        cc = _connect(device_name)
        if not cc:
            return "📺 No encontré el Chromecast."
        cc.quit_app()
        return f"📺 Detuve la reproducción en «{cc.cast_info.friendly_name}»."
    except Exception as e:
        return f"[ERROR] {str(e)[:120]}"


def cast_volume(pct: int, device_name: str = None) -> str:
    try:
        cc = _connect(device_name)
        if not cc:
            return "📺 No encontré el Chromecast."
        cc.set_volume(max(0, min(100, int(pct))) / 100.0)
        return f"📺 Volumen de «{cc.cast_info.friendly_name}» al {pct}%."
    except Exception as e:
        return f"[ERROR] {str(e)[:120]}"
