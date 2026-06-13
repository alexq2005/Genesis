"""
GENESIS — Automatización de UI (control de menús y ventanas de CUALQUIER app).

Usa UI Automation de Windows (semántico: encuentra elementos por su NOMBRE, no por
píxeles → robusto ante movimientos/resolución) con pyautogui como fallback para
teclear y clicks por coordenadas.

Sin lista blanca: opera sobre cualquier aplicación abierta.
Freno de emergencia: pyautogui.FAILSAFE — mover el mouse a la esquina superior
izquierda (0,0) aborta cualquier acción en curso. No limita QUÉ puede hacer, es
solo un botón de pánico.

API principal:
  list_windows()                  -> títulos de ventanas abiertas
  focus_app(name)                 -> trae una app al frente
  inspect_ui(name)                -> menús/botones/items interactuables de la app
  open_menu(path, app)            -> navega "Archivo > Guardar" (o ['Archivo','Guardar'])
  click_element(name, app)        -> clickea un control por nombre
  type_text(text)                 -> escribe en el elemento con foco
  press_hotkey("ctrl+s")          -> manda una combinación de teclas
  click_xy(x, y)                  -> click por coordenadas (fallback)
"""
import re
import time

try:
    import uiautomation as auto
    _UIA = True
except Exception:
    _UIA = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True   # mouse a (0,0) = abortar (freno de pánico)
    pyautogui.PAUSE = 0.12
    _PAG = True
except Exception:
    _PAG = False

# Tipos de control que el usuario puede "clickear" / navegar.
_CLICKABLE = ("MenuItemControl", "ButtonControl", "TabItemControl",
              "ListItemControl", "TreeItemControl", "HyperlinkControl",
              "SplitButtonControl", "CheckBoxControl", "RadioButtonControl",
              "MenuItem", "Button")


def available() -> dict:
    return {"uiautomation": _UIA, "pyautogui": _PAG}


# ---------------------------------------------------------------- ventanas ---
def list_windows() -> list:
    """Lista las ventanas top-level abiertas (con título)."""
    if not _UIA:
        return []
    out = []
    try:
        root = auto.GetRootControl()
        for w in root.GetChildren():
            try:
                if w.ControlTypeName == "WindowControl" and (w.Name or "").strip():
                    out.append(w.Name)
            except Exception:
                continue
    except Exception:
        pass
    return out


def _find_window(name: str):
    """Ventana cuyo título contenga `name` (case-insensitive). None si no hay."""
    if not _UIA:
        return None
    nl = (name or "").lower().strip()
    if not nl:
        return None
    try:
        root = auto.GetRootControl()
        # 1. match por substring
        for w in root.GetChildren():
            try:
                if w.ControlTypeName == "WindowControl" and nl in (w.Name or "").lower():
                    return w
            except Exception:
                continue
        # 2. match por palabras (todas presentes)
        words = [x for x in nl.split() if x]
        for w in root.GetChildren():
            try:
                wn = (w.Name or "").lower()
                if w.ControlTypeName == "WindowControl" and wn and all(x in wn for x in words):
                    return w
            except Exception:
                continue
    except Exception:
        pass
    return None


def _active_window():
    """Ventana en primer plano."""
    if not _UIA:
        return None
    try:
        fg = auto.GetForegroundControl()
        return fg.GetTopLevelControl() if fg else None
    except Exception:
        return None


def focus_app(name: str) -> bool:
    """Trae una ventana al frente. True si lo logró."""
    if not _UIA:
        return False
    w = _find_window(name)
    if not w:
        return False
    try:
        if w.IsMinimize():
            w.Restore()
        w.SetActive()
        w.SetFocus()
        time.sleep(0.35)
        return True
    except Exception:
        try:
            w.SwitchToThisWindow()
            time.sleep(0.35)
            return True
        except Exception:
            return False


# ------------------------------------------------------------- inspección ---
def _walk(ctrl, depth, max_depth, acc, want_types, limit):
    if depth > max_depth or len(acc) >= limit:
        return
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for c in children:
        if len(acc) >= limit:
            return
        try:
            tn = c.ControlTypeName
            nm = (c.Name or "").strip()
            if nm and (want_types is None or tn in want_types):
                acc.append({"name": nm, "type": tn.replace("Control", "")})
        except Exception:
            pass
        _walk(c, depth + 1, max_depth, acc, want_types, limit)


def inspect_ui(name: str = None, max_items: int = 60, max_depth: int = 7) -> list:
    """Elementos interactuables (menús, botones, tabs, items) de una app.

    Si `name` es None usa la ventana activa. Devuelve [{name, type}, ...].
    """
    if not _UIA:
        return []
    win = _find_window(name) if name else _active_window()
    if not win:
        return []
    acc = []
    _walk(win, 0, max_depth, acc, _CLICKABLE, max_items)
    # dedup conservando orden
    seen, out = set(), []
    for e in acc:
        k = (e["name"].lower(), e["type"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


# --------------------------------------------------------------- acciones ---
def _find_clickable(root, target, max_depth=8):
    """Busca un control clickeable cuyo nombre matchee `target`.
    Prioridad: exacto > startswith > substring. Devuelve el control o None."""
    tl = (target or "").lower().strip()
    if not tl:
        return None
    best, best_score = None, 0
    stack = [(root, 0)]
    while stack:
        ctrl, d = stack.pop()
        if d > max_depth:
            continue
        try:
            children = ctrl.GetChildren()
        except Exception:
            children = []
        for c in children:
            try:
                nm = (c.Name or "").lower().strip()
                tn = c.ControlTypeName
                if nm and tn in _CLICKABLE:
                    score = 0
                    if nm == tl:
                        return c  # exacto gana ya
                    elif nm.startswith(tl):
                        score = 3
                    elif tl in nm:
                        score = 2
                    elif all(w in nm for w in tl.split()):
                        score = 1
                    if score > best_score:
                        best, best_score = c, score
            except Exception:
                pass
            stack.append((c, d + 1))
    return best


def click_element(elem_name: str, app: str = None) -> str:
    """Clickea un control (botón, item, tab…) por nombre. Mensaje de resultado."""
    if not _UIA:
        return "UI Automation no disponible"
    if app and not focus_app(app):
        return f"No encontré la ventana de «{app}»"
    win = _find_window(app) if app else _active_window()
    if not win:
        return "No hay ventana activa"
    ctrl = _find_clickable(win, elem_name)
    if not ctrl:
        return f"No encontré «{elem_name}» en la ventana"
    try:
        ctrl.SetActive() if hasattr(ctrl, "SetActive") else None
    except Exception:
        pass
    try:
        ctrl.Click(simulateMove=False)
        return f"Cliqueé «{ctrl.Name}»"
    except Exception as e:
        try:
            ctrl.GetClickablePoint()
            ctrl.Click()
            return f"Cliqueé «{ctrl.Name}»"
        except Exception:
            return f"Encontré «{elem_name}» pero no pude clickearlo: {e}"


def open_menu(path, app: str = None) -> str:
    """Navega un menú paso a paso: 'Archivo > Guardar' o ['Archivo','Guardar'].

    Clickea cada nivel; tras cada click el submenú aparece como popup, así que
    re-busca desde la raíz del escritorio (los popups suelen colgar de ahí).
    """
    if not _UIA:
        return "UI Automation no disponible"
    steps = path if isinstance(path, list) else re.split(r"\s*[>/→\-]\s*", path)
    steps = [s.strip() for s in steps if s and s.strip()]
    if not steps:
        return "No me diste qué menú abrir"
    if app and not focus_app(app):
        return f"No encontré la ventana de «{app}»"
    win = _find_window(app) if app else _active_window()
    if not win:
        return "No hay ventana activa"
    done = []
    for i, step in enumerate(steps):
        # El primer nivel está dentro de la ventana; los submenús son popups
        # que cuelgan de la raíz del escritorio.
        scope = win if i == 0 else auto.GetRootControl()
        ctrl = _find_clickable(scope, step)
        if not ctrl and i > 0:
            ctrl = _find_clickable(win, step)  # por si el submenú quedó en la ventana
        if not ctrl:
            return (f"Abrí {' > '.join(done)} pero no encontré «{step}»"
                    if done else f"No encontré el menú «{step}»")
        try:
            ctrl.Click(simulateMove=False)
            done.append(ctrl.Name or step)
            time.sleep(0.35)
        except Exception as e:
            return f"No pude clickear «{step}»: {e}"
    return f"Menú abierto: {' > '.join(done)}"


def type_text(text: str) -> str:
    """Escribe texto en el elemento que tiene el foco."""
    if not text:
        return "Nada para escribir"
    if _UIA:
        try:
            auto.SendKeys("{Text}" + text if False else text, interval=0.01)
            return f"Escribí: {text[:60]}"
        except Exception:
            pass
    if _PAG:
        try:
            pyautogui.typewrite(text, interval=0.01)
            return f"Escribí: {text[:60]}"
        except Exception as e:
            return f"No pude escribir: {e}"
    return "Sin backend para escribir"


_KEY_ALIASES = {
    "control": "ctrl", "ctrl": "ctrl", "alt": "alt", "shift": "shift",
    "win": "win", "windows": "win", "enter": "enter", "intro": "enter",
    "esc": "esc", "escape": "esc", "tab": "tab", "espacio": "space",
    "supr": "delete", "suprimir": "delete", "del": "delete",
    "arriba": "up", "abajo": "down", "izquierda": "left", "derecha": "right",
}


def press_hotkey(combo: str) -> str:
    """Manda una combinación de teclas: 'ctrl+s', 'alt+f4', 'ctrl shift n'."""
    if not _PAG:
        return "pyautogui no disponible"
    parts = re.split(r"[+\s]+", (combo or "").lower().strip())
    keys = [_KEY_ALIASES.get(p, p) for p in parts if p]
    if not keys:
        return "No entendí la combinación"
    try:
        pyautogui.hotkey(*keys)
        return f"Apreté: {'+'.join(keys)}"
    except Exception as e:
        return f"No pude apretar {combo}: {e}"


def click_xy(x: int, y: int) -> str:
    """Click por coordenadas (fallback cuando no hay elemento nombrado)."""
    if not _PAG:
        return "pyautogui no disponible"
    try:
        pyautogui.click(int(x), int(y))
        return f"Cliqueé en ({x}, {y})"
    except Exception as e:
        return f"No pude clickear en ({x},{y}): {e}"
