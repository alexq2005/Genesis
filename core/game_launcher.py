"""
GENESIS — Lanzador de juegos (Steam + Epic) por nombre/voz.

Escanea los juegos instalados (Steam appmanifest + Epic manifests) y los lanza
por nombre con coincidencia difusa. Lanza Steam vía `steam://rungameid/<appid>`
y Epic vía `com.epicgames.launcher://apps/<AppName>?action=launch`.
"""
import os
import re
import glob
import json
import difflib
import subprocess

_CACHE = {"games": [], "ts": 0.0}
_MAX_AGE = 600  # re-escanea la biblioteca cada 10 min

# Apps de Steam que NO son juegos (no ofrecerlas al lanzar).
_NOT_GAMES = {
    "steamworks common redistributables", "proton", "steam linux runtime",
    "steamvr", "spacewar",
}


def _steam_path():
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        p, _ = winreg.QueryValueEx(k, "SteamPath")
        return p.replace("/", "\\") if p else None
    except Exception:
        return None


def _steam_libraries(steam):
    libs = [os.path.join(steam, "steamapps")]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    try:
        txt = open(vdf, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'"path"\s+"([^"]+)"', txt):
            p = m.group(1).replace("\\\\", "\\")
            libs.append(os.path.join(p, "steamapps"))
    except Exception:
        pass
    # únicas
    seen, out = set(), []
    for li in libs:
        if li.lower() not in seen:
            seen.add(li.lower())
            out.append(li)
    return out


def _scan_steam():
    games = []
    steam = _steam_path()
    if not steam:
        return games
    for lib in _steam_libraries(steam):
        for acf in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
            try:
                c = open(acf, encoding="utf-8", errors="replace").read()
                appid = re.search(r'"appid"\s+"(\d+)"', c)
                name = re.search(r'"name"\s+"([^"]+)"', c)
                if appid and name:
                    nm = name.group(1).strip()
                    if nm.lower() in _NOT_GAMES:
                        continue
                    games.append({"name": nm, "id": appid.group(1), "source": "steam"})
            except Exception:
                continue
    return games


def _scan_epic():
    games = []
    d = os.path.join(os.environ.get("PROGRAMDATA", ""),
                     "Epic", "EpicGamesLauncher", "Data", "Manifests")
    for item in glob.glob(os.path.join(d, "*.item")):
        try:
            j = json.load(open(item, encoding="utf-8", errors="replace"))
            nm = j.get("DisplayName") or j.get("AppName")
            app = j.get("AppName") or j.get("MainGameAppName")
            if nm and app and j.get("bIsApplication", True):
                games.append({"name": nm.strip(), "id": app, "source": "epic"})
        except Exception:
            continue
    return games


def list_games(refresh=False):
    """Lista de juegos instalados [{name, id, source}], cacheada."""
    import time
    if not refresh and _CACHE["games"] and (time.time() - _CACHE["ts"]) < _MAX_AGE:
        return _CACHE["games"]
    games = _scan_steam() + _scan_epic()
    # dedup por nombre
    seen, out = set(), []
    for g in sorted(games, key=lambda x: x["name"].lower()):
        if g["name"].lower() not in seen:
            seen.add(g["name"].lower())
            out.append(g)
    _CACHE["games"] = out
    _CACHE["ts"] = time.time()
    return out


def list_text():
    games = list_games()
    if not games:
        return "🎮 No encontré juegos instalados (¿Steam/Epic instalados?)."
    out = ["🎮 Juegos instalados:"]
    for g in games:
        out.append(f"  • {g['name']}  ({g['source']})")
    return "\n".join(out)


def _match(query, games):
    """Mejor coincidencia difusa por nombre. Devuelve game o None."""
    q = query.lower().strip()
    if not q:
        return None
    # substring directo primero
    subs = [g for g in games if q in g["name"].lower()]
    if len(subs) == 1:
        return subs[0]
    if subs:
        # el más corto (más específico) entre los que contienen la query
        return min(subs, key=lambda g: len(g["name"]))
    # acrónimo: "cs2" -> Counter-Strike 2 ; "aoe" -> Age of Empires...
    qa = q.replace(" ", "").replace("-", "")
    if qa:
        for g in games:
            words = re.findall(r"[A-Za-z0-9]+", g["name"])
            acr = "".join(w[0] for w in words).lower()
            if qa == acr or (len(qa) >= 2 and acr.startswith(qa)):
                return g
    # difuso
    names = [g["name"].lower() for g in games]
    hit = difflib.get_close_matches(q, names, n=1, cutoff=0.6)
    if hit:
        for g in games:
            if g["name"].lower() == hit[0]:
                return g
    return None


def launch_game(query):
    """Lanza un juego por nombre (coincidencia difusa)."""
    games = list_games()
    if not games:
        return "🎮 No encontré juegos instalados para lanzar."
    g = _match(query, games)
    if not g:
        nombres = ", ".join(x["name"] for x in games[:8])
        return f"🎮 No encontré «{query}». Tenés: {nombres}."
    try:
        if g["source"] == "steam":
            uri = f"steam://rungameid/{g['id']}"
        else:
            uri = f"com.epicgames.launcher://apps/{g['id']}?action=launch"
        os.startfile(uri)  # noqa: protocolo del launcher
        return f"🎮 Lanzando **{g['name']}**… (vía {g['source']})"
    except Exception as e:
        return f"[ERROR] No pude lanzar {g['name']}: {str(e)[:120]}"
