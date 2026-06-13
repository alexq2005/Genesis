"""
GENESIS — Control del sistema (volumen, energía, brillo, bloqueo).

Sin dependencias externas: usa teclas de sistema (keybd_event) para volumen y
comandos nativos de Windows para energía/brillo. Las acciones DESTRUCTIVAS
(apagar/reiniciar) van con confirmación desde el handler de genesis_tools.
"""
import os
import subprocess


# ---------------------------------------------------------------- volumen ---
def _vk(code: int, times: int = 1):
    import ctypes
    KEYEVENTF_KEYUP = 0x0002
    for _ in range(times):
        ctypes.windll.user32.keybd_event(code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)


def volume_up(steps: int = 4) -> str:
    _vk(0xAF, steps)   # VK_VOLUME_UP (~2% por paso)
    return f"🔊 Subí el volumen ({steps} pasos)."


def volume_down(steps: int = 4) -> str:
    _vk(0xAE, steps)   # VK_VOLUME_DOWN
    return f"🔉 Bajé el volumen ({steps} pasos)."


def volume_mute() -> str:
    _vk(0xAD, 1)       # VK_VOLUME_MUTE (toggle)
    return "🔇 Silencio (toggle)."


def set_volume(pct: int) -> str:
    """Volumen exacto 0-100. Usa pycaw si está; si no, aproxima con teclas."""
    pct = max(0, min(100, int(pct)))
    try:
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        from pycaw.pycaw import AudioUtilities
        AudioUtilities.GetSpeakers().EndpointVolume.SetMasterVolumeLevelScalar(pct / 100.0, None)
        return f"🔊 Volumen al {pct}%."
    except Exception:
        # Fallback sin pycaw: bajar todo y subir hasta ~pct (50 pasos ≈ 100%)
        _vk(0xAE, 50)
        _vk(0xAF, round(pct / 2))
        return f"🔊 Volumen ~{pct}% (aprox)."


# ----------------------------------------------------------------- energía ---
def lock() -> str:
    try:
        subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "🔒 Bloqueando la PC."
    except Exception as e:
        return f"[ERROR] No pude bloquear: {e}"


def sleep() -> str:
    try:
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return "😴 Suspendiendo la PC."
    except Exception as e:
        return f"[ERROR] No pude suspender: {e}"


def shutdown(seconds: int = 0) -> str:
    try:
        subprocess.Popen(["shutdown", "/s", "/t", str(seconds)])
        return f"🔌 Apagando la PC en {seconds}s. (Cancelá con «cancelá el apagado».)"
    except Exception as e:
        return f"[ERROR] No pude apagar: {e}"


def restart(seconds: int = 0) -> str:
    try:
        subprocess.Popen(["shutdown", "/r", "/t", str(seconds)])
        return f"🔄 Reiniciando la PC en {seconds}s. (Cancelá con «cancelá el apagado».)"
    except Exception as e:
        return f"[ERROR] No pude reiniciar: {e}"


def cancel_shutdown() -> str:
    try:
        subprocess.run(["shutdown", "/a"], capture_output=True)
        return "✋ Cancelé el apagado/reinicio programado."
    except Exception as e:
        return f"[ERROR] {e}"


def logoff() -> str:
    try:
        subprocess.Popen(["shutdown", "/l"])
        return "👋 Cerrando sesión."
    except Exception as e:
        return f"[ERROR] No pude cerrar sesión: {e}"


# ------------------------------------------------------------------ brillo ---
def get_monitors() -> list:
    """Lista los monitores como (x, y, w, h), ordenados de izquierda a derecha."""
    import ctypes
    from ctypes import wintypes
    mons = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                              ctypes.POINTER(wintypes.RECT), ctypes.c_double)

    def _cb(hMon, hdc, lprc, lp):
        r = lprc.contents
        mons.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return 1
    try:
        ctypes.windll.user32.EnumDisplayMonitors(0, 0, proc(_cb), 0)
    except Exception:
        pass
    mons.sort(key=lambda m: m[0])  # de izquierda a derecha
    return mons


def _chrome():
    # reusa el helper de music_player para encontrar chrome.exe
    try:
        from core.music_player import _chrome_exe
        return _chrome_exe()
    except Exception:
        return None


def open_on_screen(url: str, screen: int = 2, fullscreen: bool = True) -> str:
    """Abre una URL/app en la pantalla `screen` (1=primaria, 2=segunda...),
    en pantalla completa. Devuelve mensaje."""
    chrome = _chrome()
    if not chrome:
        return "🖥️ No encontré Chrome para abrir la ventana."
    mons = get_monitors()
    if not mons:
        return "🖥️ No pude detectar los monitores."
    idx = max(0, min(len(mons) - 1, int(screen) - 1))
    x, y, w, h = mons[idx]
    import subprocess
    args = [chrome, f"--app={url}", f"--window-position={x},{y}",
            f"--window-size={w},{h}", "--no-first-run", "--no-default-browser-check"]
    if fullscreen:
        args.append("--start-fullscreen")
    try:
        subprocess.Popen(args)
        n = len(mons)
        donde = f"pantalla {idx + 1} de {n}" if n > 1 else "la pantalla"
        return f"🖥️ Abierto en {donde} (en {x},{y})" + (" a pantalla completa." if fullscreen else ".")
    except Exception as e:
        return f"[ERROR] No pude abrir en esa pantalla: {e}"


def list_printers() -> str:
    """Lista las impresoras instaladas y marca la predeterminada."""
    try:
        ps = ("Get-Printer | Select-Object Name | ForEach-Object {$_.Name}")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=10)
        names = [n.strip() for n in (r.stdout or "").splitlines() if n.strip()]
        if not names:
            return "🖨️ No detecté impresoras instaladas."
        # default
        d = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-CimInstance Win32_Printer | Where-Object {$_.Default}).Name"],
                           capture_output=True, text=True, timeout=10)
        default = (d.stdout or "").strip()
        out = ["🖨️ Impresoras:"]
        for n in names:
            out.append(f"  • {n}" + ("  (predeterminada)" if n == default else ""))
        return "\n".join(out)
    except Exception as e:
        return f"[ERROR] No pude listar impresoras: {e}"


def print_document(path: str, printer: str = None) -> str:
    """Imprime un documento. Sin printer → impresora predeterminada.
    Soporta PDF, DOCX, TXT, imágenes (usa la app asociada al tipo de archivo)."""
    if not path or not os.path.isfile(path):
        return f"🖨️ No encontré el archivo: {path}"
    name = os.path.basename(path)
    try:
        if printer:
            # ShellExecute con verbo 'printto' a una impresora específica
            import win32api  # noqa
            win32api.ShellExecute(0, "printto", path, f'"{printer}"', ".", 0)
            return f"🖨️ Enviado «{name}» a la impresora «{printer}»."
        # Impresora predeterminada (verbo 'print')
        os.startfile(path, "print")
        return f"🖨️ Enviado «{name}» a la impresora predeterminada."
    except Exception as e:
        return f"[ERROR] No pude imprimir «{name}»: {e}"


def set_brightness(pct: int) -> str:
    """Brillo 0-100 (notebooks, vía WMI). Monitores de escritorio no siempre soportan."""
    pct = max(0, min(100, int(pct)))
    try:
        ps = (f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
              f".WmiSetBrightness(1,{pct})")
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return f"💡 Brillo al {pct}%."
        return ("💡 No pude ajustar el brillo (tu monitor/PC no expone control WMI; "
                "típico en monitores de escritorio).")
    except Exception as e:
        return f"[ERROR] Brillo: {e}"
