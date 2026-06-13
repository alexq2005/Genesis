"""
GENESIS — Índice de programas instalados.

Escanea los programas instalados UNA vez (Start Menu + registro App Paths),
los guarda en data/installed_programs.json, y permite abrirlos al instante por
nombre con fuzzy match. Antes el launcher recorría el Start Menu en cada pedido
(lento: "abre steam" tardaba ~56s). Ahora es un lookup en memoria.

El índice se refresca solo: al primer uso, y periódicamente desde el heartbeat.
"""
import os
import json
import time
from pathlib import Path

_CACHE = Path(__file__).parent.parent / "data" / "installed_programs.json"
_MAX_AGE = 86400  # 24h: re-escanea si el índice es más viejo

_START_DIRS = [
    os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
]


def scan() -> dict:
    """Escanea programas instalados y guarda el índice. Retorna {nombre: ruta}."""
    progs = {}
    # 1. Accesos directos del Start Menu + Escritorio
    for d in _START_DIRS:
        if not d or not os.path.isdir(d):
            continue
        try:
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".lnk", ".url")):
                        name = os.path.splitext(f)[0].strip()
                        if name and name.lower() not in (n.lower() for n in progs):
                            progs[name] = os.path.join(root, f)
        except Exception:
            continue
    # 2. Registro App Paths (mapea nombre.exe -> ruta real)
    try:
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub = winreg.EnumKey(key, i)
                        sk = winreg.OpenKey(key, sub)
                        path, _ = winreg.QueryValueEx(sk, "")
                        name = os.path.splitext(sub)[0].strip()
                        if name and path and name.lower() not in (n.lower() for n in progs):
                            progs[name] = path
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass

    try:
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "programs": progs}, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return progs


def get_index(force: bool = False) -> dict:
    """Devuelve el índice cacheado; re-escanea si falta o está viejo."""
    if not force:
        try:
            with open(_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("ts", 0) < _MAX_AGE and data.get("programs"):
                return data["programs"]
        except Exception:
            pass
    return scan()


def find(query: str):
    """Fuzzy match contra el índice. Retorna (nombre, ruta) o None."""
    idx = get_index()
    if not idx:
        return None
    q = (query or "").lower().strip()
    if not q:
        return None
    best, best_score = None, 0
    qwords = [w for w in q.split() if w]
    for name, path in idx.items():
        n = name.lower()
        if q == n:
            return (name, path)
        score = 0
        if n.startswith(q):
            score = 4
        elif q in n:
            score = 3
        elif qwords and all(w in n for w in qwords):
            score = 2
        elif qwords and any(w in n for w in qwords if len(w) > 3):
            score = 1
        if score > best_score:
            best_score, best = score, (name, path)
    return best if best_score > 0 else None


def open_program(query: str):
    """Encuentra y abre un programa. Retorna el nombre abierto, o None."""
    r = find(query)
    if not r:
        return None
    name, path = r
    try:
        os.startfile(path)
        return name
    except Exception:
        return None


def count() -> int:
    try:
        return len(get_index())
    except Exception:
        return 0


def list_names(limit: int = 40) -> list:
    try:
        return sorted(get_index().keys())[:limit]
    except Exception:
        return []
