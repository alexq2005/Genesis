"""
GENESIS — Índice de carpetas (apertura instantánea de cualquier carpeta por nombre).

Escanea C: y el perfil del usuario + F: (profundidad acotada, saltando dirs
pesados/de sistema) UNA vez y cachea en data/folder_index.json como
{nombre_en_minúscula: [rutas...]}. Abrir "la carpeta X" pasa de un walk en vivo
(~2.5s) a un lookup en memoria (~1ms).

Mantenimiento automático:
  • Se refresca solo desde el heartbeat (re-escanea si el cache tiene >24h).
  • Prune-on-access: si un lookup encuentra una ruta que ya NO existe (la borraste),
    la elimina del índice en el momento. Las carpetas nuevas entran en el próximo
    re-escaneo (o forzando refresh()).
"""
import os
import json
import time

_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "folder_index.json")
_MAX_AGE = 10800          # 3h: re-escanea para captar carpetas nuevas seguido
                          # (las borradas se limpian al instante por prune-on-access;
                          #  las recién creadas que intentás abrir, por rescan-on-miss)
_MAX_DEPTH = 5            # niveles desde cada raíz
_MAX_ENTRIES = 80000      # tope de carpetas indexadas (backstop de memoria/disco)

_ROOTS = [
    os.environ.get("USERPROFILE", r"C:\Users\Lexus"),
    "F:\\",
    "D:\\",
]

# Dirs que NO vale la pena indexar (ruido, pesados, de sistema).
_SKIP = {
    "$recycle.bin", "system volume information", "msdownld.tmp", "config.msi",
    "recovery", "$winreagent", "$sysreset", "windows", "appdata", "node_modules",
    "venv", ".venv", ".git", "__pycache__", ".pytest_cache", "site-packages",
    "program files", "program files (x86)", "programdata", ".gradle", ".cache",
    ".npm", ".nuget", ".cargo", ".rustup", "$windows.~bt", "$windows.~ws",
    "intel", "perflogs", ".vscode-server",
}

_IDX = None      # {name_lower: [paths]}
_IDX_TS = 0
_DIRTY = False


def _norm(s: str) -> str:
    return (s or "").lower().strip()


def scan() -> dict:
    """Escanea las raíces y construye el índice. Guarda y devuelve {name: [paths]}."""
    idx = {}
    count = 0
    for root in _ROOTS:
        if not os.path.isdir(root) or count >= _MAX_ENTRIES:
            continue
        base_depth = root.rstrip("/\\").count(os.sep)
        for cur, dirs, _files in os.walk(root):
            depth = cur.count(os.sep) - base_depth
            if depth >= _MAX_DEPTH:
                dirs[:] = []
                continue
            # podar dirs a saltar (in-place para no descender)
            dirs[:] = [d for d in dirs
                       if d.lower() not in _SKIP and not d.startswith("$")]
            for d in dirs:
                key = d.lower()
                full = os.path.join(cur, d)
                idx.setdefault(key, [])
                if full not in idx[key]:
                    idx[key].append(full)
                    count += 1
                    if count >= _MAX_ENTRIES:
                        break
            if count >= _MAX_ENTRIES:
                break
    try:
        os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "folders": idx}, f, ensure_ascii=False)
    except Exception:
        pass
    global _IDX, _IDX_TS, _DIRTY
    _IDX, _IDX_TS, _DIRTY = idx, time.time(), False
    return idx


def get_index(force: bool = False) -> dict:
    """Índice cacheado (en memoria → archivo → re-escaneo si falta/viejo)."""
    global _IDX, _IDX_TS
    if not force and _IDX is not None and (time.time() - _IDX_TS) < _MAX_AGE:
        return _IDX
    if not force:
        try:
            with open(_CACHE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if (time.time() - data.get("ts", 0)) < _MAX_AGE and data.get("folders"):
                _IDX, _IDX_TS = data["folders"], data.get("ts", time.time())
                return _IDX
        except Exception:
            pass
    return scan()


def _save():
    global _DIRTY
    if _IDX is None:
        return
    try:
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump({"ts": _IDX_TS, "folders": _IDX}, f, ensure_ascii=False)
        _DIRTY = False
    except Exception:
        pass


def find(query: str):
    """Devuelve rutas existentes para una carpeta llamada `query`.
    Prune-on-access: descarta del índice las rutas que ya no existen en disco."""
    global _DIRTY
    idx = get_index()
    if not idx:
        return []
    q = _norm(query)
    if not q:
        return []
    keys = [q]
    if q.replace(" ", "") != q:
        keys.append(q.replace(" ", ""))
    paths = []
    for k in keys:
        paths.extend(idx.get(k, []))
    if not paths:  # match sin espacios contra claves (raro)
        qns = q.replace(" ", "")
        for k, v in idx.items():
            if k.replace(" ", "") == qns:
                paths.extend(v)
                break
    # dedup conservando orden
    seen, uniq = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    alive = [p for p in uniq if os.path.isdir(p)]
    if len(alive) != len(uniq):  # prune: algo se borró
        dead = set(uniq) - set(alive)
        for k in keys:
            if k in idx:
                idx[k] = [p for p in idx[k] if p not in dead]
                if not idx[k]:
                    idx.pop(k, None)
        _DIRTY = True
        _save()
    return alive


def refresh() -> int:
    """Fuerza un re-escaneo completo. Devuelve la cantidad de carpetas indexadas."""
    idx = scan()
    return sum(len(v) for v in idx.values())


def count() -> int:
    try:
        return sum(len(v) for v in get_index().values())
    except Exception:
        return 0
