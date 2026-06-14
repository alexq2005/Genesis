"""Control de la ventana de la cabina de Genesis (PyWebView/WebView2).

IMPORTANTE: ESCONDER = MOVER la ventana fuera de pantalla, NUNCA minimizar.
Minimizar/restaurar una ventana WebView2 la deja en BLANCO al volver (Chromium
no repinta tras restaurar desde minimizado — verificado 2026-06-14). Mover fuera
de pantalla la mantiene "mostrada" (sigue renderizando) y al devolverla queda OK.

Comandos de voz: «Genesis minimiza/escondete» → hide(); «Genesis aparecé/mostrate»
→ show().
"""
import ctypes


def _cabin_hwnd():
    """HWND de la ventana de la cabina de Genesis, o None."""
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


def _win_origin(hwnd):
    """(left, top) de una ventana por HWND, o None."""
    try:
        from ctypes import wintypes
        r = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(r))
        return r.left, r.top
    except Exception:
        return None


def _move_window(hwnd, x, y):
    """Mueve una ventana a (x, y) sin cambiar tamaño / z-order / foco."""
    try:
        # SWP_NOSIZE|SWP_NOZORDER|SWP_NOACTIVATE = 0x0001|0x0004|0x0010
        ctypes.windll.user32.SetWindowPos(hwnd, 0, int(x), int(y), 0, 0, 0x0015)
    except Exception:
        pass


# Posición original de la cabina mientras está escondida: {hwnd: (left, top)}.
# Es estado de proceso (la cabina corre como un proceso de larga vida).
_PARKED = {}


def hide():
    """Esconde la cabina moviéndola fuera de pantalla (NO minimiza)."""
    h = _cabin_hwnd()
    if not h:
        return "🪟 No encontré la ventana de la cabina."
    if h in _PARKED:
        return "🪟 Ya estoy escondido. Decí «Genesis aparecé» para volver."
    xy = _win_origin(h)
    if not xy:
        return "🪟 No pude leer la posición de la cabina."
    _PARKED[h] = xy
    _move_window(h, xy[0], xy[1] + 3000)     # fuera de pantalla (abajo)
    return "🪟 Listo, me escondo. Decí «Genesis aparecé» (o «mostrate») para volver."


def show():
    """Devuelve la cabina a su posición original."""
    h = _cabin_hwnd()
    if not h:
        return "🪟 No encontré la ventana de la cabina."
    xy = _PARKED.pop(h, None)
    if not xy:
        return "🪟 Ya estoy a la vista. 🙂"
    _move_window(h, xy[0], xy[1])
    return "🪟 Acá estoy de nuevo. 👋"
