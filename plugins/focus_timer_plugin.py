"""
Plugin Focus Timer para Genesis.

Temporizador de enfoque tipo Pomodoro simplificado.
Notifica cuando termina el tiempo. Ideal para sesiones de trabajo.
"""
import time
import threading

PLUGIN_NAME = "Focus Timer"
PLUGIN_VERSION = "1.0"
PLUGIN_DESCRIPTION = "Temporizador de enfoque con notificaciones"

_timer = None
_timer_end = 0
_timer_label = ""
_genesis_ref = None


def on_load(genesis):
    global _genesis_ref
    _genesis_ref = genesis


def on_unload(genesis):
    global _timer
    if _timer:
        _timer.cancel()
        _timer = None


def register_commands():
    return {
        "/focus": {
            "handler": cmd_focus,
            "help": "Iniciar timer de enfoque. Ej: /focus 25 (minutos) o /focus 25 Estudiar Python",
        },
        "/timer": {
            "handler": cmd_timer_status,
            "help": "Ver estado del timer activo",
        },
        "/stopfocus": {
            "handler": cmd_stop_focus,
            "help": "Detener timer de enfoque",
        },
    }


def _on_timer_done():
    """Callback cuando el timer termina."""
    global _timer
    _timer = None
    msg = f"Timer completado: {_timer_label}" if _timer_label else "Timer de enfoque completado"

    # Intentar notificacion desktop
    try:
        from plyer import notification
        notification.notify(title="Genesis Focus Timer", message=msg, timeout=10)
    except Exception:
        try:
            import subprocess
            subprocess.run([
                "powershell", "-Command",
                f"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                f"[System.Windows.Forms.MessageBox]::Show('{msg}', 'Genesis Timer')"
            ], capture_output=True, timeout=5)
        except Exception:
            pass


def cmd_focus(genesis, args: str) -> str:
    global _timer, _timer_end, _timer_label

    if _timer:
        remaining = max(0, _timer_end - time.time())
        return f"Ya hay un timer activo ({remaining/60:.0f} min restantes). Usa /stopfocus para cancelar."

    if not args:
        return "Uso: /focus <minutos> [descripcion]\nEjemplo: /focus 25 Estudiar Python"

    parts = args.split(None, 1)
    try:
        minutes = int(parts[0])
    except ValueError:
        return "Error: el primer argumento debe ser un numero de minutos"

    if minutes < 1 or minutes > 180:
        return "Error: el timer debe ser entre 1 y 180 minutos"

    _timer_label = parts[1] if len(parts) > 1 else ""
    _timer_end = time.time() + minutes * 60
    _timer = threading.Timer(minutes * 60, _on_timer_done)
    _timer.daemon = True
    _timer.start()

    label_str = f" — {_timer_label}" if _timer_label else ""
    return f"Timer de {minutes} min iniciado{label_str}. Te aviso cuando termine."


def cmd_timer_status(genesis, args: str) -> str:
    if not _timer:
        return "No hay timer activo. Usa /focus <minutos> para iniciar uno."
    remaining = max(0, _timer_end - time.time())
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    label_str = f" — {_timer_label}" if _timer_label else ""
    return f"Timer activo{label_str}: {mins}:{secs:02d} restantes"


def cmd_stop_focus(genesis, args: str) -> str:
    global _timer
    if not _timer:
        return "No hay timer activo."
    _timer.cancel()
    _timer = None
    return "Timer detenido."
